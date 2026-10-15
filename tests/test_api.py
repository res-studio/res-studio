import unittest
from fastapi.testclient import TestClient
import server

class APIContract(unittest.TestCase):
    def setUp(self): self.client = TestClient(server.app)
    def test_home(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn('html',response.text.lower())
    def test_engines(self):
        response=self.client.get('/api/engines')
        self.assertEqual(response.status_code,200)
        self.assertIn('webcrack',response.json()['engines'])
    def test_invalid_token(self):
        response=self.client.post('/api/decompile/invalid/0',json={'engine':'webcrack'})
        self.assertEqual(response.status_code,404)
    def test_reject_local_ip(self):
        with self.assertRaises(ValueError): server.safe_url('http://127.0.0.1/')
    def test_reject_non_http(self):
        with self.assertRaises(ValueError): server.safe_url('file:///etc/passwd')

if __name__=='__main__': unittest.main()
