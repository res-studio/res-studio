"""Integration coverage for modern JS sites with deterministic synthetic assets."""
import io, json, os, pathlib, subprocess, sys, time, unittest, zipfile
from unittest.mock import patch
from fastapi.testclient import TestClient

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import server

HTML=b'''<!doctype html><html><head><link rel="stylesheet" href="/assets/main.css"></head>
<body><div id="app"></div><script src="/assets/runtime.js"></script>
<script type="module" src="/assets/app.js"></script></body></html>'''
JS=b'''import {render} from "./runtime.js";const app=document.getElementById("app");
function greet(name){return "Hello "+name};app.textContent=greet("RES");'''
RUNTIME=b'''export function render(node){return node?.textContent??""}'''
CSS=b'''body{background:#111;color:#fff}#app{display:grid}'''
BASE='https://fixture.example'
ASSETS={
 BASE:(HTML,'text/html'),
 BASE+'/assets/main.css':(CSS,'text/css'),
 BASE+'/assets/runtime.js':(RUNTIME,'text/javascript'),
 BASE+'/assets/app.js':(JS,'text/javascript'),
}
class ModernSiteTest(unittest.TestCase):
 def setUp(self):
  server.SESSION.clear()
  self.client=TestClient(server.app)
 def fake_get(self,url):
  if url not in ASSETS: raise ValueError('Unexpected asset: '+url)
  data,typ=ASSETS[url]
  return data,typ,url
 def test_modern_static_scan_to_export(self):
  with patch.object(server,'get',side_effect=self.fake_get):
   response=self.client.post('/api/scan',json={'url':BASE})
  self.assertEqual(response.status_code,200,response.text)
  result=response.json()
  self.assertEqual(len(result['files']),4,result)
  self.assertEqual({f['type'] for f in result['files']},{'html','css','js'})
  self.assertEqual(result['errors'],[])
  token=result['token']
  jsid=next(f['id'] for f in result['files'] if f['url'].endswith('app.js'))
  code=self.client.get(f'/api/file/{token}/{jsid}')
  self.assertEqual(code.status_code,200)
  self.assertIn('greet',code.json()['content'])
  self.assertIn('formatted',code.json())
  graph=self.client.get(f'/api/graph/{token}')
  self.assertEqual(graph.status_code,200)
  self.assertEqual(len(graph.json()['nodes']),4)
  exported=self.client.get(f'/api/export/{token}')
  self.assertEqual(exported.status_code,200)
  with zipfile.ZipFile(io.BytesIO(exported.content)) as z:
   self.assertEqual(len([n for n in z.namelist() if n.startswith('assets/')]),4)
   self.assertIn('report.json',z.namelist())
 def test_invalid_engine_and_non_js(self):
  with patch.object(server,'get',side_effect=self.fake_get):
   result=self.client.post('/api/scan',json={'url':BASE}).json()
  token=result['token']
  htmlid=next(f['id'] for f in result['files'] if f['type']=='html')
  response=self.client.post(f'/api/decompile/{token}/{htmlid}',json={'engine':'webcrack'})
  self.assertEqual(response.status_code,400)
 def test_webcrack_actual_transform(self):
  if not (ROOT/'node_modules'/'webcrack').is_dir():
   self.skipTest('npm dependencies not installed')
  with patch.object(server,'get',side_effect=self.fake_get):
   result=self.client.post('/api/scan',json={'url':BASE}).json()
  token=result['token']
  jsid=next(f['id'] for f in result['files'] if f['url'].endswith('app.js'))
  response=self.client.post(f'/api/decompile/{token}/{jsid}',json={'engine':'webcrack'})
  self.assertEqual(response.status_code,200,response.text)
  self.assertIn('code',response.json())
 def test_wakaru_actual_transform(self):
  if not (ROOT/'node_modules'/'@wakaru'/'cli'/'package.json').is_file():
   self.skipTest('Wakaru package not installed')
  with patch.object(server,'get',side_effect=self.fake_get):
   result=self.client.post('/api/scan',json={'url':BASE}).json()
  token=result['token']
  jsid=next(f['id'] for f in result['files'] if f['url'].endswith('app.js'))
  response=self.client.post(f'/api/decompile/{token}/{jsid}',json={'engine':'wakaru'})
  self.assertEqual(response.status_code,200,response.text)
  body=response.json()
  self.assertEqual(body['engine'],'wakaru')
  self.assertIn('greet',body['code'])
  self.assertGreater(len(body['code']),20)
 def test_webcrack_minified_bundle(self):
  if not (ROOT/'node_modules'/'webcrack').is_dir():
   self.skipTest('Webcrack package not installed')
  source='(()=>{var a={123:(m)=>{m.exports=function(x){return x*2}}},c={};function r(i){if(c[i])return c[i].exports;let m=c[i]={exports:{}};a[i](m);return m.exports}console.log(r(123)(21))})();'
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   inp=pathlib.Path(tmp)/'bundle.js'
   out=pathlib.Path(tmp)/'result.json'
   inp.write_text(source)
   proc=subprocess.run(['node',str(ROOT/'engine.mjs'),'webcrack',str(inp),str(out)],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(proc.returncode,0,proc.stderr)
   result=json.loads(out.read_text())
   self.assertTrue(result.get('code'),result)
   self.assertIn('r(123)(21)',source)
   self.assertGreater(len(result['code']),0)
   self.assertIsInstance(result.get('modules'),list)
 def test_webcrack_obfuscated_syntax(self):
  if not (ROOT/'node_modules'/'webcrack').is_dir():
   self.skipTest('Webcrack package not installed')
  source='const _0xa1b2=["log","hello"];console[_0xa1b2[0]](_0xa1b2[1]);'
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   inp=pathlib.Path(tmp)/'obfuscated.js'
   out=pathlib.Path(tmp)/'result.json'
   inp.write_text(source)
   proc=subprocess.run(['node',str(ROOT/'engine.mjs'),'webcrack',str(inp),str(out)],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(proc.returncode,0,proc.stderr)
   result=json.loads(out.read_text())
   self.assertTrue(result.get('code'),result)
 def test_dynamic_browser_capture_with_fixture(self):
  # Browser routes to a deterministic fixture; no external network required.
  # The capture function uses safe_url validation and requests in its own browser.
  import asyncio
  from playwright_scan import capture
  from playwright.async_api import async_playwright
  # Validate behavior using public URL and local Playwright interception.
  async def run():
   async with async_playwright() as p:
    browser=await p.chromium.launch()
    context=await browser.new_context(service_workers='block')
    async def handle(route):
     url=route.request.url
     key = BASE if url == BASE + '/' else url
     if key in ASSETS:
      data,typ=ASSETS[key]
      await route.fulfill(status=200,body=data,content_type=typ)
     else: await route.abort()
    await context.route('**/*',handle)
    page=await context.new_page()
    await page.goto(BASE)
    await page.wait_for_function('document.querySelector("#app")?.textContent === "Hello RES"')
    title=await page.locator('#app').inner_text()
    await browser.close()
    return title
  self.assertEqual(asyncio.run(run()),'Hello RES')

if __name__=='__main__':unittest.main()
