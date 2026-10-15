"""Real engine/browser checks on CI; no external target site needed."""
import json, pathlib, subprocess, tempfile, sys, asyncio
ROOT=pathlib.Path(__file__).resolve().parents[1]
report={}
with tempfile.TemporaryDirectory() as tmp:
    base=pathlib.Path(tmp)
    sample=base/'input.js';sample.write_text('function add(a,b){return a+b};console.log(add(1,2));')
    out=base/'out.json'
    proc=subprocess.run(['node',str(ROOT/'engine.mjs'),'webcrack',str(sample),str(out)],cwd=ROOT,capture_output=True,text=True,timeout=60)
    data=json.loads(out.read_text()) if out.exists() else {}
    report['webcrack']={'passed':proc.returncode==0 and bool(data.get('code')),'error':data.get('error') or proc.stderr[-300:]}
    # Wakaru is a library package in this setup, not necessarily a CLI binary.
    package=ROOT/'node_modules'/'@wakaru'/'cli'/'package.json'
    report['wakaru_package']={'passed':package.is_file(),'error':'' if package.is_file() else 'Wakaru npm package missing'}
    report['wakaru_integration']={'status':'pending','reason':'Actual CLI invocation and transformed output are not yet validated'}
    for name in ['synchrony']:
        path=ROOT/'node_modules'/'.bin'/name
        if not path.exists():
            report[name]={'passed':False,'error':'CLI binary missing after npm install'}
            continue
        help_proc=subprocess.run([str(path),'--help'],cwd=ROOT,capture_output=True,text=True,timeout=20)
        report[name]={'passed':help_proc.returncode==0,'error':help_proc.stderr[-300:]}
    async def browser_test():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True)
            page=await browser.new_page()
            await page.goto('data:text/html,<title>RES Smoke</title><h1>OK</h1>')
            title=await page.title()
            await browser.close()
            return title=='RES Smoke'
    try: report['playwright']={'passed':asyncio.run(browser_test())}
    except Exception as exc: report['playwright']={'passed':False,'error':str(exc)}
(ROOT/'test-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
print(json.dumps(report,indent=2,ensure_ascii=False))
if not all(item['passed'] for item in report.values() if 'passed' in item): sys.exit(1)
