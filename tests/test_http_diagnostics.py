"""HTTP diagnostics: a response code alone cannot establish anti-bot blocking."""
import unittest
from unittest.mock import patch
import os
from server import get

class FakeResponse:
    headers={}
    def __init__(self,status): self.status_code=status
    def __enter__(self): return self
    def __exit__(self,*args): return False

class FakeSession:
    trust_env=False
    def mount(self,*args): pass
    def get(self,*args,**kwargs): return FakeResponse(self.status)
    def close(self): pass

class HttpDiagnosticTests(unittest.TestCase):
    def test_http_error_messages(self):
        for code,word in [(401,'Autenticação'),(403,'Acesso negado'),(404,'não encontrada'),(429,'Limite')]:
            with self.subTest(code=code):
                session=FakeSession()
                session.status=code
                with patch.dict(os.environ, {'RES_HTTP_ENGINE':'requests'}),patch('server.resolve_public',return_value=('example.com',['93.184.215.14'])),patch('server.requests.Session',return_value=session):
                    with self.assertRaisesRegex(ValueError,word):
                        get('https://example.com/')

if __name__=='__main__':
    unittest.main()
