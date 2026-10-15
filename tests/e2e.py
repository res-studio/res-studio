"""End-to-end: actual RES UI -> FastAPI -> public test site -> assets -> export."""
import json, os, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright
from urllib.request import urlopen

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPORT=ROOT/'e2e-report.json'
BASE='http://127.0.0.1:8765'
report={'test_url':'https://example.com','checks':{},'errors':[]}
server=subprocess.Popen([sys.executable,'-m','uvicorn','server:app','--host','127.0.0.1','--port','8765'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
try:
    for _ in range(50):
        if server.poll() is not None:
            raise RuntimeError('Server exited before ready: '+server.stderr.read().decode('utf-8','replace')[-2000:])
        try:
            with urlopen(BASE+'/api/engines',timeout=1) as response:
                report['checks']['backend_ready']=response.status==200
                break
        except Exception: time.sleep(.2)
    else: raise RuntimeError('FastAPI not ready after 10 seconds')
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1366,'height':900},accept_downloads=True)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(BASE,wait_until='domcontentloaded')
        report['checks']['ui_loaded']=page.title()=='RES Studio'
        page.locator('#url').fill('https://example.com')
        page.locator('#scan').click()
        page.wait_for_function("() => document.querySelector('#files .item') || document.querySelector('#status').textContent.toLowerCase().includes('erro')",timeout=35000)
        report['checks']['assets_rendered']=page.locator('#files .item').count()>0
        report['status']=page.locator('#status').inner_text()
        if not report['checks']['assets_rendered']:
            raise AssertionError('No assets rendered: '+report['status'])
        page.locator('#files .item').first.click()
        page.wait_for_function("() => document.querySelector('#code').textContent.length > 25",timeout=5000)
        report['checks']['file_content_rendered']=len(page.locator('#code').inner_text())>25
        page.screenshot(path=str(ROOT/'e2e-desktop.png'),full_page=True)
        with page.expect_download(timeout=15000) as download:
            page.locator('#export').click()
        report['checks']['zip_export']=download.value.suggested_filename.endswith('.zip')
        report['checks']['no_page_errors']=not errors
        report['page_errors']=errors
        browser.close()
except Exception as exc:
    report['errors'].append(str(exc))
finally:
    server.terminate()
    try: server.wait(timeout=5)
    except subprocess.TimeoutExpired: server.kill()
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps(report,indent=2,ensure_ascii=False))
if report['errors'] or not all(report['checks'].values()):
    sys.exit(1)
