"""Ensure alternative public IPs are attempted only for transport failures."""
import unittest
from unittest.mock import patch
import requests
from server import get

class Response:
    status_code=200
    headers={'content-type':'text/html'}
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def iter_content(self,size): yield b'<html>ok</html>'

class FakeSession:
    def __init__(self,attempts): self.attempts=attempts;self.trust_env=True
    def mount(self,prefix,adapter): self.address=adapter._addresses[0]
    def get(self,*args,**kwargs):
        self.attempts.append((self.address,self.trust_env,kwargs['allow_redirects']))
        if self.address=='93.184.215.14': raise requests.ConnectionError('unreachable')
        return Response()
    def close(self): pass

class IpFallbackTests(unittest.TestCase):
    def test_retry_only_validated_addresses(self):
        attempts=[]
        with patch('server.resolve_public',return_value=('example.com',['93.184.215.14','93.184.215.15'])),patch('server.requests.Session',side_effect=lambda:FakeSession(attempts)):
            raw,mime,url=get('https://example.com/')
        self.assertEqual(raw,b'<html>ok</html>')
        self.assertEqual([a[0] for a in attempts],['93.184.215.14','93.184.215.15'])
        self.assertTrue(all(not a[1] and not a[2] for a in attempts))
    def test_dns_failure_does_not_fallback_to_unvalidated_dns(self):
        with patch('server.resolve_public',side_effect=ValueError('DNS sem endereço público')),patch('server.requests.Session') as session:
            with self.assertRaisesRegex(ValueError,'DNS sem endereço público'):
                get('https://example.com/')
            session.assert_not_called()

if __name__=='__main__':unittest.main()
