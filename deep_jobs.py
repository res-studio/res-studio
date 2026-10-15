"""Disk-backed deep scan jobs with bounded concurrency and TTL cleanup."""
import json, os, pathlib, secrets, sqlite3, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from deep_scan import discover

ROOT=pathlib.Path(os.environ.get('RES_JOB_DIR', pathlib.Path(tempfile.gettempdir())/'res-studio-jobs'))
EXECUTOR=ThreadPoolExecutor(max_workers=2,thread_name_prefix='res-deep')
LOCK=threading.RLock()
JOBS={}
TTL=3600
MAX_JOBS=12

def _db(token):
    return ROOT/token/'assets.sqlite3'

def _initialize(token):
    path=_db(token)
    path.parent.mkdir(parents=True,exist_ok=False)
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE assets (id INTEGER PRIMARY KEY, url TEXT, type TEXT, size INTEGER, content TEXT)')
        conn.execute('CREATE INDEX idx_assets_url ON assets(url)')

def _run(token,url,fetch,settings):
    try:
        with LOCK:
            JOBS[token]['status']='running'
        def save(asset):
            with sqlite3.connect(_db(token)) as conn:
                conn.execute('INSERT INTO assets(id,url,type,size,content) VALUES(?,?,?,?,?)',
                             (asset['id'],asset['url'],asset['type'],asset['size'],asset['content']))
            with LOCK:
                JOBS[token]['count']+=1
                JOBS[token]['bytes']+=asset['size']
        result=discover(url,fetch,on_asset=save,retain_content=False,**settings)
        with LOCK:
            JOBS[token].update(status='completed',errors=result['errors'][:100],
                               truncated=result['truncated'],pages=result['pages'],
                               discovered_urls=result['discovered_urls'])
    except Exception as exc:
        with LOCK:
            JOBS[token].update(status='failed',errors=[str(exc)[:300]])

def submit(url,fetch,settings):
    with LOCK:
        now=time.monotonic()
        for token,job in list(JOBS.items()):
            if now-job['created']>TTL and job['status'] not in ('running','queued'):
                JOBS.pop(token,None)
                import shutil
                shutil.rmtree(ROOT/token,ignore_errors=True)
        if len(JOBS)>=MAX_JOBS: raise ValueError('Fila cheia; tente mais tarde')
        token=secrets.token_hex(16)
        _initialize(token)
        JOBS[token]={'status':'queued','created':now,'count':0,'bytes':0,
                     'errors':[],'truncated':False,'pages':0,'discovered_urls':0}
        EXECUTOR.submit(_run,token,url,fetch,settings)
        return token

def status(token):
    with LOCK:
        if token not in JOBS: raise KeyError(token)
        return {'token':token,**JOBS[token]}

def assets(token,limit=100,offset=0):
    status(token)
    with sqlite3.connect(_db(token)) as conn:
        conn.row_factory=sqlite3.Row
        return [dict(row) for row in conn.execute(
            'SELECT id,url,type,size FROM assets ORDER BY id LIMIT ? OFFSET ?',(limit,offset))]

def asset(token,fid):
    status(token)
    with sqlite3.connect(_db(token)) as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute('SELECT * FROM assets WHERE id=?',(fid,)).fetchone()
        if row is None: raise KeyError(fid)
        return dict(row)
