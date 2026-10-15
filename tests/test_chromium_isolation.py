"""Isolation boundary regressions: no direct browser network and no Docker privilege escalation."""
import pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import isolated_chromium,server
from fastapi.testclient import TestClient

class ChromiumIsolationTest(unittest.TestCase):
 def test_worker_docker_network_disabled(self):
  with patch.object(isolated_chromium.shutil,'which',return_value='/usr/bin/docker'):
   cmd=isolated_chromium.command('https://example.com')
  self.assertEqual(cmd[cmd.index('--network')+1],'none')
  self.assertIn('--read-only',cmd)
  self.assertIn('no-new-privileges',cmd)
  self.assertIn('ALL',cmd)
  self.assertNotIn('--privileged',cmd)
  self.assertNotIn('--network=host',cmd)
 def test_no_docker_fails_closed(self):
  with patch.object(isolated_chromium.shutil,'which',return_value=None):
   with self.assertRaises(RuntimeError):isolated_chromium.command('https://example.com')
 def test_dynamic_requires_isolation_opt_in(self):
  with patch.dict(server.os.environ,{},clear=True):
   response=TestClient(server.app).post('/api/scan-dynamic',json={'url':'https://example.com'})
  self.assertEqual(response.status_code,503)
 def test_dynamic_uses_isolated_controller(self):
  with patch.dict(server.os.environ,{'RES_ENABLE_ISOLATED_CHROMIUM':'1'}):
   with patch.object(isolated_chromium,'capture',return_value={'url':'https://example.com','assets':[{'type':'html','url':'https://example.com','size':12,'content':'<html></html>'}],'errors':[],'requests':[],'truncated':False}) as mocked:
    response=TestClient(server.app).post('/api/scan-dynamic',json={'url':'https://example.com'})
  self.assertEqual(response.status_code,200,response.text)
  mocked.assert_called_once()
if __name__=='__main__':unittest.main()
