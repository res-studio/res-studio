"""Background job regression tests with synthetic public assets."""
import pathlib, sys, tempfile, time, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import deep_jobs, server

BASE='https://fixture.example'
DATA={
 BASE:(b'<html><script src="/app.js"></script></html>','text/html'),
 BASE+'/app.js':(b'console.log(1)','application/javascript')
}
def fake_fetch(url):
 body,mime=DATA[url]
 return body,mime,url

class BackgroundJobTest(unittest.TestCase):
 def test_background_job_pagination(self):
  with tempfile.TemporaryDirectory() as tmp:
   with patch.object(deep_jobs,'ROOT',pathlib.Path(tmp)):
    with patch.object(server,'get',side_effect=fake_fetch):
     with patch.object(server,'safe_url',return_value=BASE):
      client=TestClient(server.app)
      response=client.post('/api/jobs/deep',json={'url':BASE,'max_assets':10})
      self.assertEqual(response.status_code,200,response.text)
      token=response.json()['token']
      for _ in range(100):
       state=client.get('/api/jobs/'+token).json()
       if state['status']!='running': break
       time.sleep(.02)
      self.assertEqual(state['status'],'completed',state)
      result=client.get('/api/jobs/'+token+'/assets?limit=1').json()
      self.assertEqual(len(result['assets']),1)
      self.assertEqual(state['count'],2)
      asset=client.get('/api/jobs/'+token+'/assets/1')
      self.assertEqual(asset.status_code,200)
      self.assertIn('console.log',asset.json()['content'])
      deep_jobs.JOBS.pop(token,None)
 def test_invalid_pagination(self):
  response=TestClient(server.app).get('/api/jobs/notfound/assets?limit=9999')
  self.assertEqual(response.status_code,400)
if __name__=='__main__': unittest.main()
