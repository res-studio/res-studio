"""Chromium worker: no network namespace; parent supplies validated HTTP bodies over stdio."""
import asyncio, base64, json, sys, threading
from playwright.async_api import async_playwright

io_lock=threading.Lock()
def broker(url):
    with io_lock:
        sys.stdout.write('RESREQ '+json.dumps({'url':url})+'\n')
        sys.stdout.flush()
        line=sys.stdin.readline()
        if not line.startswith('RESRSP '):
            raise RuntimeError('Broker response missing')
        answer=json.loads(line[7:])
        if 'error' in answer: raise RuntimeError(answer['error'])
        return base64.b64decode(answer['body']),answer['mime'],answer['final']

async def capture(url):
    assets=[]; errors=[]; requests=[]; seen=set(); nonlocal_total=[0]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--disable-background-networking','--disable-extensions','--disable-quic','--no-first-run'])
        try:
            context=await browser.new_context(accept_downloads=False,service_workers='block',permissions=[])
            page=await context.new_page()
            async def handler(route):
                target=route.request.url
                try:
                    if route.request.method not in ('GET','HEAD') or route.request.resource_type in ('websocket','media','font','image','eventsource'):
                        await route.abort();return
                    body,mime,final=await asyncio.to_thread(broker,target)
                    await route.fulfill(status=200,body=body if route.request.method=='GET' else b'',content_type=mime or 'application/octet-stream')
                    if target not in seen and len(assets)<35 and nonlocal_total[0]+len(body)<=12_000_000:
                        kind={'document':'html','script':'js','stylesheet':'css'}.get(route.request.resource_type)
                        if kind:
                            seen.add(target)
                            nonlocal_total[0]+=len(body)
                            assets.append({'type':kind,'url':final,'content':body.decode('utf-8','replace'),'size':len(body)})
                except Exception as exc:
                    if len(errors)<40:errors.append(str(exc)[:180])
                    await route.abort()
            await context.route('**/*',handler)
            page.on('request',lambda r:requests.append({'method':r.method,'type':r.resource_type,'url':r.url}) if len(requests)<150 else None)
            try:
                await page.goto(url,wait_until='domcontentloaded',timeout=20000)
                await page.wait_for_timeout(1500)
                # Capture the rendered DOM as a separate artifact: useful for SPAs
                # whose initial HTML is only an empty application shell.
                rendered=await page.content()
                encoded=rendered.encode('utf-8')
                if encoded and len(encoded)<=2_000_000 and nonlocal_total[0]+len(encoded)<=12_000_000 and len(assets)<35:
                    nonlocal_total[0]+=len(encoded)
                    assets.append({'type':'html','url':page.url,'content':rendered,'size':len(encoded),'rendered':True})
            except Exception as exc:errors.append('Navegação: '+str(exc)[:200])
            return {'url':page.url if page.url.startswith(('http://','https://')) else url,'assets':assets,'errors':errors,'requests':requests,'truncated':len(assets)>=35}
        finally:await browser.close()

if __name__=='__main__':
    try:
        url=sys.argv[1]
        if not url.startswith(('https://','http://')):raise ValueError('Invalid URL')
        result=asyncio.run(capture(url))
        sys.stdout.write('RESRESULT '+json.dumps(result)+'\n');sys.stdout.flush()
    except Exception as exc:
        sys.stdout.write('RESERROR '+json.dumps({'error':str(exc)[:300]})+'\n');sys.stdout.flush()
        sys.exit(1)
