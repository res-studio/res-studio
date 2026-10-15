import base64
import unittest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

class HarImportTests(unittest.TestCase):
    def test_import_and_discard_sensitive_metadata(self):
        har={'log':{'entries':[{'request':{'url':'https://example.com/','headers':[{'name':'Cookie','value':'secret'}]},
            'response':{'status':200,'content':{'mimeType':'text/html','text':'<html>OK</html>'}}}]}}
        response=client.post('/api/import-har',json=har)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['files'][0]['type'],'html')
        self.assertNotIn('secret',response.text)
    def test_invalid_har(self):
        self.assertEqual(client.post('/api/import-har',content=b'{}').status_code,400)
    def test_no_response_body(self):
        har={'log':{'entries':[{'request':{'url':'https://example.com/'},'response':{'status':200,'content':{'mimeType':'text/html'}}}]}}
        self.assertEqual(client.post('/api/import-har',json=har).status_code,422)
    def test_base64(self):
        har={'log':{'entries':[{'request':{'url':'https://example.com/a.js'},'response':{'status':200,'content':{'mimeType':'application/javascript','encoding':'base64','text':base64.b64encode(b'let a=1').decode()}}}]}}
        self.assertEqual(client.post('/api/import-har',json=har).status_code,200)
if __name__=='__main__':unittest.main()
