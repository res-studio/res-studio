"""Optional dynamic capture with Playwright; local, read-only, public hosts only."""
import asyncio
from server import get
from urllib.parse import urlparse
from playwright.async_api import async_playwright

MAX_CAPTURE = 35
MAX_BYTES = 12_000_000
MAX_ITEM = 2_000_000

async def capture(url, validator):
    validator(url)
    assets = []
    errors = []
    seen = set()
    total = 0
    requests_log = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={'server':'http://127.0.0.1:9'},
            args=['--no-first-run','--disable-background-networking','--disable-extensions',
                  '--disable-sync','--disable-quic','--no-pings','--disable-features=WebRtcHideLocalIpsWithMdns'])
        try:
            context = await browser.new_context(accept_downloads=False, service_workers='block', ignore_https_errors=False, permissions=[])
            page = await context.new_page()
            async def route_handler(route):
                target = route.request.url
                try:
                    validator(target)
                    if route.request.method not in ('GET', 'HEAD'):
                        await route.abort(); return
                    if route.request.resource_type in ('websocket', 'media', 'font', 'image', 'eventsource'):
                        await route.abort(); return
                    # Chromium is configured with a dead-end proxy. Fetch approved
                    # resources in Python and fulfill the intercepted request.
                    # This avoids browser DNS resolution for ordinary HTTP requests.
                    body,mime,final=await asyncio.to_thread(get,target)
                    if final != target:
                        validator(final)
                    await route.fulfill(status=200,body=body if route.request.method=='GET' else b'',content_type=mime or 'application/octet-stream')
                except Exception:
                    await route.abort()
            await context.route('**/*', route_handler)
            async def response_handler(response):
                nonlocal total
                if len(assets) >= MAX_CAPTURE: return
                req = response.request
                if req.resource_type not in ('document', 'script', 'stylesheet'): return
                if response.status >= 400: return
                target = response.url
                if target in seen: return
                seen.add(target)
                try:
                    mime = response.headers.get('content-type','').lower()
                    kind = ('js' if req.resource_type == 'script' else 'css' if req.resource_type == 'stylesheet' else 'html')
                    if kind == 'js' and not any(x in mime for x in ('javascript','ecmascript','text/plain','application/octet-stream')): return
                    if kind == 'css' and 'css' not in mime: return
                    if kind == 'html' and 'html' not in mime: return
                    length = int(response.headers.get('content-length','0') or '0')
                    if length > MAX_ITEM: return
                    body = await response.body()
                    if len(body) > MAX_ITEM or total + len(body) > MAX_BYTES: return
                    total += len(body)
                    assets.append({'type':kind,'url':target,'content':body.decode('utf-8','replace'),'size':len(body)})
                except Exception as exc:
                    errors.append(f'{target}: {str(exc)[:100]}')
            page.on('response', lambda r: asyncio.create_task(response_handler(r)))
            page.on('request', lambda r: requests_log.append({'method':r.method,'type':r.resource_type,'url':r.url}) if len(requests_log)<150 else None)
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_timeout(2000)
                await page.wait_for_timeout(500)
            except Exception as exc:
                errors.append('Navegação: '+str(exc)[:200])
            final = page.url
            if final.startswith('http'): validator(final)
            return {'url':final,'assets':assets,'requests':requests_log,'errors':errors,'truncated':len(assets)>=MAX_CAPTURE}
        finally:
            await browser.close()
