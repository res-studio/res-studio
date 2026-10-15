"""Deterministic deep scan tests, without external network requests."""
import pathlib, sys, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import server
from deep_scan import discover

BASE='https://fixture.example'
DATA={
 BASE:(b'<html><script src="/app.js"></script><a href="/about">About</a></html>','text/html'),
 BASE+'/app.js':(b'import "./chunk.js";','application/javascript'),
 BASE+'/chunk.js':(b'export const ok = true;','application/javascript'),
 BASE+'/about':(b'<html><link rel="stylesheet" href="/main.css"></html>','text/html'),
 BASE+'/main.css':(b'@import "./theme.css";','text/css'),
 BASE+'/theme.css':(b'body { color: red }','text/css'),
}
def fetch(url):
 if url not in DATA: raise ValueError('not found')
 body,mime=DATA[url]
 return body,mime,url

class DeepScanTest(unittest.TestCase):
 def test_recursive_discovery(self):
  result=discover(BASE,fetch,max_assets=30,max_pages=3,max_depth=5)
  self.assertEqual({x['url'] for x in result['files']},set(DATA))
  self.assertEqual(result['pages'],2)
  self.assertFalse(result['truncated'])
 def test_asset_cap(self):
  result=discover(BASE,fetch,max_assets=2,max_pages=3,max_depth=5)
  self.assertEqual(len(result['files']),2)
  self.assertTrue(result['truncated'])
 def test_external_links_excluded(self):
  def external(url):
   if url==BASE:
    return b'<html><script src="https://elsewhere.example/code.js"></script></html>','text/html',url
   raise AssertionError('unexpected external fetch')
  result=discover(BASE,external,same_origin=True)
  self.assertEqual(len(result['files']),1)
 def test_api_deep_scan(self):
  with patch.object(server,'get',side_effect=fetch):
   result=TestClient(server.app).post('/api/scan-deep',json={'url':BASE,'max_assets':30,'max_pages':3,'max_depth':5})
  self.assertEqual(result.status_code,200,result.text)
  self.assertEqual(len(result.json()['files']),6)
  self.assertIn('token',result.json())
 def test_invalid_limits(self):
  response=TestClient(server.app).post('/api/scan-deep',json={'url':BASE,'max_assets':6000})
  self.assertEqual(response.status_code,400)
if __name__=='__main__':unittest.main()
