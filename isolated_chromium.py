"""Launch a network-disconnected Docker Chromium worker and broker approved GETs."""
import base64, json, os, select, shutil, subprocess, time
from urllib.parse import urlparse

IMAGE=os.environ.get('RES_CHROMIUM_WORKER_IMAGE','res-studio-chromium:local')
TIMEOUT=60
MAX_BROKER_REQUESTS=150
MAX_BROKER_BYTES=12_000_000

def command(url):
    if not shutil.which('docker'):
        raise RuntimeError('Docker não instalado; captura isolada indisponível')
    if not IMAGE or any(c.isspace() for c in IMAGE):
        raise RuntimeError('Imagem Docker inválida')
    return ['docker','run','--rm','-i','--network','none',
            '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--pids-limit','128','--memory','768m','--cpus','1',
            '--tmpfs','/tmp:rw,nosuid,nodev,size=128m',
            '--user','10001:10001',IMAGE,'python','/app/chromium_worker.py',url]

def capture(url,fetch,validator):
    validator(url)
    proc=subprocess.Popen(command(url),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL,text=True,bufsize=1)
    deadline=time.monotonic()+TIMEOUT
    count=0
    total=0
    try:
        while time.monotonic()<deadline:
            ready,_,_=select.select([proc.stdout],[],[],min(1,max(.01,deadline-time.monotonic())))
            if not ready:
                if proc.poll() is not None:break
                continue
            line=proc.stdout.readline()
            if not line:break
            if len(line)>2_000_000:raise RuntimeError('Mensagem do worker excessiva')
            if line.startswith('RESREQ '):
                count+=1
                answer={}
                try:
                    if count>MAX_BROKER_REQUESTS:raise ValueError('Limite de requisições do navegador')
                    target=json.loads(line[7:])['url']
                    validator(target)
                    data,mime,final=fetch(target)
                    validator(final)
                    if total+len(data)>MAX_BROKER_BYTES:raise ValueError('Limite de dados do navegador')
                    total+=len(data)
                    answer={'body':base64.b64encode(data).decode('ascii'),'mime':mime,'final':final}
                except Exception as exc:answer={'error':str(exc)[:160]}
                proc.stdin.write('RESRSP '+json.dumps(answer)+'\n')
                proc.stdin.flush()
            elif line.startswith('RESRESULT '):
                result=json.loads(line[10:])
                validator(result['url'])
                return result
            elif line.startswith('RESERROR '):
                raise RuntimeError(json.loads(line[9:]).get('error','Falha no navegador'))
        raise RuntimeError('Captura isolada encerrada ou excedeu 60 segundos')
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=5)
