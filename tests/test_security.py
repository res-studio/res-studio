"""Security regression tests: SSRF, redirects, file limits, and engine isolation."""
import io, pathlib, sys, unittest, time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import server

class SecurityTest(unittest.TestCase):
 def setUp(self):
  server.SESSION.clear()
  self.client=TestClient(server.app)
 def test_block_private_and_unsafe_urls(self):
  for url in ['file:///etc/passwd','http://127.0.0.1','http://[::1]/',
              'http://localhost','http://169.254.169.254/latest/meta-data/',
              'http://10.0.0.1','http://192.168.1.1','http://user:pass@example.com',
              'http://example.com:8080','ftp://example.com']:
   with self.subTest(url=url):
    with self.assertRaises(ValueError):server.safe_url(url)
 def test_reject_dns_resolving_to_private_address(self):
  fake=[(2,1,6,'',('127.0.0.1',0))]
  with patch.object(server.socket,'getaddrinfo',return_value=fake):
   with self.assertRaises(ValueError):server.safe_url('https://public.example')
 def test_redirect_to_private_address_blocked(self):
  response=MagicMock()
  response.__enter__.return_value=response
  response.status_code=302
  response.headers={'Location':'http://127.0.0.1/secret'}
  with patch.object(server,'resolve_public',side_effect=[('example.com',['93.184.215.14']),ValueError('private')]) as validator:
   with patch.object(server.requests.Session,'get',return_value=response):
    with self.assertRaises(ValueError):server.get('https://example.com')
    self.assertEqual(validator.call_count,2)
 def test_streaming_file_size_limit(self):
  response=MagicMock()
  response.__enter__.return_value=response
  response.status_code=200
  response.headers={'content-type':'text/html'}
  response.iter_content.return_value=[b'x'*(server.MAX_FILE+1)]
  with patch.object(server,'resolve_public',return_value=('example.com',['93.184.215.14'])):
   with patch.object(server.requests.Session,'get',return_value=response):
    with self.assertRaisesRegex(ValueError,'2 MB'):
     server.get('https://example.com')
 def test_pinned_connection_uses_validated_address(self):
  adapter=server.PinnedAdapter('example.com',['93.184.215.14'])
  pool=adapter.get_connection('https://example.com/path')
  self.assertEqual(pool.host,'93.184.215.14')
  self.assertEqual(pool.conn_kw['server_hostname'],'example.com')
  with self.assertRaises(ValueError):
   adapter.get_connection('https://other.example/path')
 def test_pinned_connection_requests_232_path(self):
  from requests import Request
  adapter=server.PinnedAdapter('example.com',['93.184.215.14'])
  prepared=Request('GET','https://example.com/path').prepare()
  pool=adapter.get_connection_with_tls_context(prepared,True)
  self.assertEqual(pool.host,'93.184.215.14')
  self.assertEqual(pool.conn_kw['server_hostname'],'example.com')
  with self.assertRaises(ValueError):
   adapter.get_connection_with_tls_context(Request('GET','https://other.example/').prepare(),True)
 def test_proxy_environment_disabled(self):
  response=MagicMock()
  response.__enter__.return_value=response
  response.status_code=200
  response.headers={'content-type':'text/html'}
  response.iter_content.return_value=[b'ok']
  with patch.object(server,'resolve_public',return_value=('example.com',['93.184.215.14'])):
   with patch.object(server.requests.Session,'get',return_value=response) as fetch:
    self.assertEqual(server.get('https://example.com')[0],b'ok')
    self.assertFalse(fetch.call_args.kwargs['allow_redirects'])
 def test_non_js_rejected_and_invalid_token(self):
  server.SESSION['t']=[{'type':'html','content':'<h1>test</h1>'}]
  self.assertEqual(self.client.post('/api/decompile/t/0',json={'engine':'wakaru'}).status_code,400)
  self.assertEqual(self.client.get('/api/export/invalid').status_code,404)
 def test_session_cache_bounded(self):
  with patch.object(server,'MAX_SESSIONS',3):
   for i in range(5):
    server.store_session([{'id':i}])
  self.assertEqual(len(server.SESSION),3)
 def test_session_expiration(self):
  server.SESSION['expired']=[]
  server.SESSION_CREATED['expired']=time.monotonic()-server.SESSION_TTL-1
  server.store_session([])
  self.assertNotIn('expired',server.SESSION)
 def test_remote_api_requires_key(self):
  with patch.object(server,'API_KEY',''):
   with TestClient(server.app,client=('203.0.113.10',50000)) as client:
    response=client.get('/api/engines')
   self.assertEqual(response.status_code,403)
 def test_api_key_authentication(self):
  with patch.object(server,'API_KEY','test-secret'):
   self.assertEqual(self.client.get('/api/engines').status_code,401)
   self.assertEqual(self.client.get('/api/engines',headers={'x-api-key':'test-secret'}).status_code,200)
 def test_api_rate_limit(self):
  with patch.object(server,'RATE_LIMIT',1):
   server.RATE_STATE.clear()
   self.assertEqual(self.client.get('/api/engines').status_code,200)
   self.assertEqual(self.client.get('/api/engines').status_code,429)
   server.RATE_STATE.clear()
 def test_reject_internal_dns_suffixes(self):
  for host in ['service.local','metadata.internal','anything.localhost']:
   with self.subTest(host=host):
    with self.assertRaises(ValueError):
     server.safe_url('https://'+host)
 def test_dynamic_capture_disabled_without_isolation(self):
  with patch.dict(server.os.environ,{},clear=True):
   response=self.client.post('/api/scan-dynamic',json={'url':'https://example.com'})
  self.assertEqual(response.status_code,503)
  self.assertIn('desabilitada',response.json()['detail'])
 def test_reject_fragment(self):
  with self.assertRaises(ValueError):
   server.safe_url('https://example.com/#secret')
 def test_invalid_engine_never_executes(self):
  server.SESSION['t']=[{'type':'js','content':'alert(1)'}]
  with patch.object(server.subprocess,'run') as runner:
   response=self.client.post('/api/decompile/t/0',json={'engine':'anything'})
  self.assertEqual(response.status_code,400)
  runner.assert_not_called()

if __name__=='__main__':unittest.main()
