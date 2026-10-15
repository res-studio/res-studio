"""RES Studio: local-only, read-only web asset analyzer."""
import io, json, re, socket, ipaddress, zipfile, hashlib, os, subprocess, tempfile, shutil, secrets, asyncio, time, threading
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title='RES Studio', version='0.1.0')
MAX_FILE=2_000_000
MAX_TOTAL=12_000_000
MAX_ASSETS=35
SESSION={}
SESSION_CREATED={}
SESSION_LOCK=threading.RLock()
SESSION_TTL=1800
MAX_SESSIONS=20
# Set RES_API_KEY to require a secret for all API routes. Non-loopback clients
# are denied unless a key is configured. Never trust forwarded IP headers.
API_KEY=os.environ.get('RES_API_KEY','')
RATE_LIMIT=60
RATE_WINDOW=60
RATE_STATE={}
RATE_LOCK=threading.Lock()

@app.middleware('http')
async def protect_api(request:Request, call_next):
    from fastapi.responses import JSONResponse
    if request.url.path.startswith('/api/'):
        peer=request.client.host if request.client else ''
        local=peer in ('127.0.0.1','::1','testclient')
        if not local and not API_KEY:
            return JSONResponse({'detail':'Configure RES_API_KEY para acesso remoto'},status_code=403)
        if API_KEY and not secrets.compare_digest(request.headers.get('x-api-key',''),API_KEY):
            return JSONResponse({'detail':'Chave de API inválida'},status_code=401)
        identity=hashlib.sha256((peer+'|'+request.headers.get('x-api-key','')).encode()).hexdigest()
        now=time.monotonic()
        with RATE_LOCK:
            for key,(start,count) in list(RATE_STATE.items()):
                if now-start>=RATE_WINDOW: RATE_STATE.pop(key,None)
            start,count=RATE_STATE.get(identity,(now,0))
            if now-start>=RATE_WINDOW: start,count=now,0
            if count>=RATE_LIMIT:
                return JSONResponse({'detail':'Limite de requisições atingido'},status_code=429,headers={'Retry-After':'60'})
            RATE_STATE[identity]=(start,count+1)
    return await call_next(request)

def process_limits():
    # POSIX only; child process memory/CPU caps, independent of wall timeout.
    if os.name!='posix': return
    import resource
    # Node/V8 reserves virtual address space well beyond its resident memory.
    # RLIMIT_AS=1 GiB causes false OOMs; cap physical data/CPU/output instead.
    resource.setrlimit(resource.RLIMIT_DATA,(4*1024*1024*1024,4*1024*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(50,50))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))

def run_engine(cmd,*,timeout,cwd):
    kwargs={'capture_output':True,'text':True,'timeout':timeout,'cwd':cwd}
    if os.name=='posix': kwargs['preexec_fn']=process_limits
    return subprocess.run(cmd,**kwargs)

def store_session(files):
    now=time.monotonic()
    with SESSION_LOCK:
        for key in list(SESSION):
            if now-SESSION_CREATED.get(key,0)>=SESSION_TTL:
                SESSION.pop(key,None)
                SESSION_CREATED.pop(key,None)
        while len(SESSION)>=MAX_SESSIONS:
            oldest=min(SESSION,key=lambda key: SESSION_CREATED.get(key,0))
            SESSION.pop(oldest,None)
            SESSION_CREATED.pop(oldest,None)
        token=secrets.token_hex(16)
        SESSION[token]=files
        SESSION_CREATED[token]=now
        return token

class Scan(BaseModel):
    url:str

def safe_url(url):
    p=urlparse(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
        raise ValueError('URL HTTP(S) inválida')
    if p.port not in (None,80,443): raise ValueError('Porta não permitida')
    if p.fragment: raise ValueError('Fragmentos não permitidos')
    if not p.hostname or len(p.hostname)>253: raise ValueError('Hostname inválido')
    if p.hostname.endswith('.local') or p.hostname.endswith('.internal') or p.hostname.endswith('.localhost'):
        raise ValueError('Hostname interno bloqueado')
    for result in socket.getaddrinfo(p.hostname,None,type=socket.SOCK_STREAM):
        ip=ipaddress.ip_address(result[4][0])
        if not ip.is_global: raise ValueError('Endereço privado/reservado bloqueado')
    return url

def get(url):
    # No automatic redirects; validate every hop to prevent SSRF.
    for _ in range(5):
        safe_url(url)
        try:
            with requests.get(url, timeout=(4,12), allow_redirects=False, stream=True, headers={'User-Agent':'RES-Studio/0.1 (read-only analysis)'}) as r:
                if r.status_code in (301,302,303,307,308):
                    url=urljoin(url,r.headers.get('Location',''))
                    continue
                r.raise_for_status()
                data=bytearray()
                for chunk in r.iter_content(65536):
                    data.extend(chunk)
                    if len(data)>MAX_FILE: raise ValueError('Arquivo excede 2 MB')
                return bytes(data),r.headers.get('content-type',''),url
        except requests.RequestException as e: raise ValueError(str(e))
    raise ValueError('Redirecionamentos excessivos')

class Assets(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='script' and a.get('src'): self.urls.append(('js',a['src']))
        if tag=='link' and a.get('rel','').lower() in ('stylesheet','modulepreload') and a.get('href'): self.urls.append(('css' if a['rel'].lower()=='stylesheet' else 'js',a['href']))

def format_js(src):
    # Basic formatter only, not a semantic decompiler.
    out=[]; indent=0; quote=None; esc=False; linecomment=False; blockcomment=False
    for c in src:
        if quote:
            out.append(c)
            if esc: esc=False
            elif c=='\\': esc=True
            elif c==quote: quote=None
            continue
        if c in ('"',"'",'`'): quote=c;out.append(c)
        elif c=='{': out.append(' {\n');indent+=1;out.append('  '*indent)
        elif c=='}': indent=max(0,indent-1);out.append('\n'+'  '*indent+'}')
        elif c==';': out.append(';\n'+'  '*indent)
        else: out.append(c)
    return ''.join(out)

def analyze(name,txt):
    patterns={'imports':r'\bimport\s*(?:\(|[\w*{])','exports':r'\bexport\s+(?:default|const|function|class|\{)','functions':r'\b(?:function\s+[\w$]+|(?:const|let)\s+[\w$]+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)','endpoints':r'''(?:fetch\s*\(|axios\.(?:get|post|put|delete)\s*\()'''}
    result={k:len(re.findall(v,txt)) for k,v in patterns.items()}
    result['frameworks']=[k for k,p in {'React':r'react(?:-dom)?|__REACT_DEVTOOLS','Vue':r'vue(?:\.runtime)?|__VUE__','Svelte':r'svelte/internal|svelte\.','Angular':r'@angular/|ng-version','Next.js':r'__NEXT_DATA__|/_next/','Webpack':r'__webpack_require__|webpackChunk','Vite':r'__vite__|/assets/index-'}.items() if re.search(p,txt,re.I)]
    return result

@app.get('/',response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__),'index.html'),encoding='utf-8') as f: return f.read()

@app.post('/api/scan')
def scan(s:Scan):
    try:
        raw,typ,final=get(s.url)
        if 'html' not in typ and not raw.lstrip().lower().startswith((b'<!doctype html',b'<html')): raise ValueError('URL não retornou HTML')
        html=raw.decode('utf-8','replace');parser=Assets();parser.feed(html)
        entries=[('html',final)]+[(t,urljoin(final,u)) for t,u in parser.urls]
        files=[];total=0;seen=set();errors=[]
        for kind,url in entries[:MAX_ASSETS]:
            if url in seen: continue
            seen.add(url)
            try:
                if kind=='html': data=raw
                else: data,_,_=get(url)
                total+=len(data)
                if total>MAX_TOTAL: errors.append('Limite total de 12 MB atingido');break
                content=data.decode('utf-8','replace')
                files.append({'id':len(files),'type':kind,'url':url,'size':len(data),'content':content,'analysis':analyze(url,content)})
            except Exception as e: errors.append(url+': '+str(e)[:130])
        if not files: raise ValueError('Nenhum arquivo recuperado')
        token=store_session(files)
        return {'token':token,'url':final,'files':[{k:v for k,v in f.items() if k!='content'} for f in files], 'errors':errors,'truncated':len(entries)>MAX_ASSETS}
    except Exception as e: raise HTTPException(400,str(e))

@app.post('/api/scan-dynamic')
def scan_dynamic(s:Scan):
    try:
        try:
            from playwright_scan import capture
        except ImportError:
            raise HTTPException(503, 'Instale Playwright: pip install -r requirements.txt && python -m playwright install chromium')
        result=asyncio.run(capture(s.url,safe_url))
        files=[]
        for asset in result['assets']:
            content=asset['content']
            files.append({'id':len(files),'type':asset['type'],'url':asset['url'], 'size':asset['size'], 'content':content,'analysis':analyze(asset['url'],content)})
        if not files: raise ValueError('Nenhum recurso coletado. Verifique bloqueios e permissões do site.')
        token=store_session(files)
        return {'token':token,'url':result['url'],'files':[{k:v for k,v in f.items() if k!='content'} for f in files], 'errors':result['errors'],'truncated':result['truncated'], 'requests':result['requests'], 'mode':'dynamic'}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(400,str(exc)[:500])

class Decompile(BaseModel):
    engine: str = 'webcrack'

@app.get('/api/engines')
def engines():
    root=os.path.dirname(__file__)
    return {'node':shutil.which('node') is not None,
            'webcrack_installed':os.path.isdir(os.path.join(root,'node_modules','webcrack')),
            'wakaru_installed':os.path.isfile(os.path.join(root,'node_modules','@wakaru','cli','package.json')), 'synchrony_installed':os.path.isfile(os.path.join(root,'node_modules','.bin','synchrony')), 'engines':['webcrack','wakaru','synchrony'], 'note':'Instale as dependências npm para habilitar os motores.'}

@app.post('/api/decompile/{token}/{fid}')
def decompile(token:str,fid:int,config:Decompile):
    if token not in SESSION or not 0<=fid<len(SESSION[token]):
        raise HTTPException(404,'Arquivo não encontrado')
    f=SESSION[token][fid]
    if f['type']!='js': raise HTTPException(400,'Apenas JavaScript')
    if config.engine not in ('webcrack','wakaru','synchrony'): raise HTTPException(400,'Motor não integrado')
    root=os.path.dirname(__file__)
    if config.engine=='webcrack' and not os.path.isdir(os.path.join(root,'node_modules','webcrack')):
        raise HTTPException(503,'Instale Webcrack com npm install')
    synchrony_bin=os.path.join(root,'node_modules','.bin','synchrony')
    if config.engine=='synchrony' and not os.path.isfile(synchrony_bin):
        raise HTTPException(503,'Instale Synchrony com npm install')
    wakaru_bin=os.path.join(root,'node_modules','.bin','wakaru')
    if config.engine=='wakaru' and not os.path.isfile(os.path.join(root,'node_modules','@wakaru','cli','package.json')):
        raise HTTPException(503,'Instale Wakaru com npm install')
    with tempfile.TemporaryDirectory() as tmp:
        inp=os.path.join(tmp,'input.js');out=os.path.join(tmp,'output.json')
        with open(inp,'w',encoding='utf8') as handle:handle.write(f['content'])
        try:
            if config.engine=='synchrony':
                proc=run_engine([synchrony_bin,'deobfuscate',inp],timeout=45,cwd=tmp)
                if proc.returncode!=0: raise HTTPException(422,(proc.stderr or proc.stdout)[:500])
                cleaned=os.path.join(tmp,'input.cleaned.js')
                if not os.path.isfile(cleaned): raise HTTPException(500,'Synchrony não gerou input.cleaned.js')
                with open(cleaned,encoding='utf8') as handle: code=handle.read()
                if len(code)>12_000_000: raise HTTPException(413,'Saída muito grande')
                return {'engine':'synchrony','code':code,'modules':[]}
            if config.engine=='wakaru':
                recovered=os.path.join(tmp,'recovered.js')
                # Invoke the locally installed package only; never fetch code at request time.
                # Resolve the executable from the installed package manifest.
                # npm exec may pick an unrelated binary name or fail for scoped packages.
                package_root=os.path.join(root,'node_modules','@wakaru','cli')
                with open(os.path.join(package_root,'package.json'),encoding='utf8') as manifest:
                    package=json.load(manifest)
                bins=package.get('bin')
                if isinstance(bins,str):
                    executable=bins
                elif isinstance(bins,dict) and bins:
                    executable=bins.get('wakaru') or next(iter(bins.values()))
                else:
                    raise HTTPException(503,'Pacote Wakaru não declara executável CLI')
                from pathlib import Path
                package_dir=Path(package_root).resolve()
                executable_path=(package_dir / executable).resolve()
                if not executable_path.is_relative_to(package_dir) or not executable_path.is_file():
                    raise HTTPException(503,'Executável Wakaru não encontrado no pacote')
                if executable_path.suffix in ('.js','.mjs','.cjs'):
                    cmd=['node',str(executable_path),inp,'-o',recovered,'--level','standard']
                else:
                    cmd=[str(executable_path),inp,'-o',recovered,'--level','standard']
                proc=run_engine(cmd,timeout=45,cwd=root)
                if proc.returncode!=0: raise HTTPException(422,(proc.stderr or proc.stdout)[:500])
                if not os.path.isfile(recovered): raise HTTPException(500,'Wakaru não gerou arquivo de saída')
                with open(recovered,encoding='utf8') as handle: code=handle.read()
                if len(code)>12_000_000: raise HTTPException(413,'Saída muito grande')
                return {'engine':'wakaru','code':code,'modules':[]}
            proc=run_engine(['node',os.path.join(root,'engine.mjs'),'webcrack',inp,out],timeout=45,cwd=root)
        except subprocess.TimeoutExpired: raise HTTPException(504,'Limite de 45 segundos')
        if not os.path.isfile(out): raise HTTPException(500,proc.stderr[:300])
        with open(out,encoding='utf8') as handle:result=json.load(handle)
        if result.get('error'): raise HTTPException(422,result['error'])
        return result

@app.post('/api/bundle/{token}/{fid}')
def bundle(token:str,fid:int):
    if token not in SESSION or not 0<=fid<len(SESSION[token]):
        raise HTTPException(404,'Arquivo não encontrado')
    f=SESSION[token][fid]
    if f['type']!='js': raise HTTPException(400,'Selecione JavaScript')
    root=os.path.dirname(__file__)
    if not shutil.which('node') or not os.path.isdir(os.path.join(root,'node_modules','webcrack')):
        raise HTTPException(503,'Instale Node.js e execute npm install')
    with tempfile.TemporaryDirectory() as tmp:
        inp=os.path.join(tmp,'bundle.js');out=os.path.join(tmp,'result.json')
        with open(inp,'w',encoding='utf8') as h:h.write(f['content'])
        try:
            proc=run_engine(['node',os.path.join(root,'engine.mjs'),'webcrack',inp,out],timeout=60,cwd=root)
        except subprocess.TimeoutExpired:
            raise HTTPException(504,'Tempo limite de 60 segundos')
        if not os.path.isfile(out):raise HTTPException(422,(proc.stderr or 'Falha no motor')[:500])
        with open(out,encoding='utf8') as h: result=json.load(h)
    if result.get('error'):raise HTTPException(422,str(result['error'])[:500])
    modules=result.get('modules') or []
    if not isinstance(modules,list):raise HTTPException(422,'Formato inesperado de módulos')
    modules=[{'name':str(m.get('name',i))[:200], 'code':str(m.get('code',''))[:500000]} for i,m in enumerate(modules[:200])]
    f['bundle_modules']=modules
    return {'count':len(modules),'modules':[{'id':i,'name':m['name'],'size':len(m['code'])} for i,m in enumerate(modules)],
            'note':'Extração heurística via Webcrack; nem todo bundle pode ser separado.'}

@app.get('/api/bundle/{token}/{fid}/{mid}')
def bundle_module(token:str,fid:int,mid:int):
    if token not in SESSION or not 0<=fid<len(SESSION[token]):raise HTTPException(404,'Arquivo não encontrado')
    modules=SESSION[token][fid].get('bundle_modules',[])
    if not 0<=mid<len(modules):raise HTTPException(404,'Módulo não encontrado; execute Separar bundle')
    return modules[mid]

@app.get('/api/bundle-export/{token}/{fid}')
def bundle_export(token:str,fid:int):
    if token not in SESSION or not 0<=fid<len(SESSION[token]):raise HTTPException(404,'Arquivo não encontrado')
    modules=SESSION[token][fid].get('bundle_modules',[])
    if not modules:raise HTTPException(404,'Nenhum módulo recuperado')
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',zipfile.ZIP_DEFLATED) as z:
        manifest=[]
        for i,m in enumerate(modules):
            filename=f'modules/module_{i:04d}.js'
            z.writestr(filename,m['code'])
            manifest.append({'file':filename,'original_id':m['name'],'bytes':len(m['code'].encode())})
        z.writestr('manifest.json',json.dumps(manifest,indent=2,ensure_ascii=False))
    mem.seek(0)
    return StreamingResponse(mem,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="res-bundle-modules.zip"'})

@app.get('/api/graph/{token}')
def graph(token:str):
    if token not in SESSION: raise HTTPException(404,'Sessão não encontrada')
    files=SESSION[token]
    nodes=[{'id':f['id'],'label':f['url'],'type':f['type']} for f in files]
    edges=[]
    urlids={f['url']:f['id'] for f in files}
    pattern=r"(?:import\s+(?:[^'\"\n]*?\s+from\s*)?|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]"
    for f in files:
        if f['type']!='js':continue
        for spec in re.findall(pattern,f['content']):
            target=urljoin(f['url'],spec)
            if target in urlids: edges.append({'source':f['id'],'target':urlids[target]})
    return {'nodes':nodes,'edges':edges,'note':'Grafo parcial baseado em imports explícitos.'}

@app.get('/api/file/{token}/{fid}')
def file(token:str,fid:int):
    if token not in SESSION or not 0<=fid<len(SESSION[token]): raise HTTPException(404,'Arquivo não encontrado')
    f=SESSION[token][fid]
    return {'content':f['content'],'formatted':format_js(f['content']) if f['type']=='js' else f['content']}

@app.get('/api/export/{token}')
def export(token:str):
    if token not in SESSION: raise HTTPException(404,'Sessão não encontrada')
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',zipfile.ZIP_DEFLATED) as z:
        report=[]
        for f in SESSION[token]:
            name=f"assets/{f['id']:03d}.{f['type']}"
            z.writestr(name,f['content'])
            report.append({k:v for k,v in f.items() if k!='content'})
        z.writestr('report.json',json.dumps(report,ensure_ascii=False,indent=2))
    mem.seek(0)
    return StreamingResponse(mem,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="res-analysis.zip"'})
