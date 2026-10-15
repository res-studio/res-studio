"""Regression tests for automatic HTTP fallback and security boundaries."""
import os
import unittest
from unittest.mock import patch
from server import get

OK=(b'<html>ok</html>','text/html','https://example.com/')

class AutoTransportTests(unittest.TestCase):
    def test_fallback_for_http_404(self):
        with patch.dict(os.environ,{'RES_HTTP_ENGINE':'auto'}),patch('server.get_requests',side_effect=ValueError('HTTP 404: missing')),patch('curl_transport.get',return_value=OK) as curl:
            self.assertEqual(get('https://example.com/'),OK)
            curl.assert_called_once()
    def test_fallback_for_transport_failure(self):
        with patch.dict(os.environ,{'RES_HTTP_ENGINE':'auto'}),patch('server.get_requests',side_effect=ValueError('Falha de conexão em IPs públicos validados: timeout')),patch('curl_transport.get',return_value=OK) as curl:
            self.assertEqual(get('https://example.com/'),OK)
            curl.assert_called_once()
    def test_no_fallback_for_ssrf_rejection(self):
        with patch.dict(os.environ,{'RES_HTTP_ENGINE':'auto'}),patch('server.get_requests',side_effect=ValueError('Endereço privado/reservado bloqueado')),patch('curl_transport.get') as curl:
            with self.assertRaisesRegex(ValueError,'bloqueado'): get('https://example.com/')
            curl.assert_not_called()
    def test_no_fallback_for_size_limit(self):
        with patch.dict(os.environ,{'RES_HTTP_ENGINE':'auto'}),patch('server.get_requests',side_effect=ValueError('Arquivo excede 2 MB')),patch('curl_transport.get') as curl:
            with self.assertRaisesRegex(ValueError,'2 MB'): get('https://example.com/')
            curl.assert_not_called()
    def test_default_requests_success(self):
        with patch.dict(os.environ,{'RES_HTTP_ENGINE':'auto'}),patch('server.get_requests',return_value=OK),patch('curl_transport.get') as curl:
            self.assertEqual(get('https://example.com/'),OK)
            curl.assert_not_called()
    def test_force_requests(self):
        with patch.dict(os.environ,{'RES_HTTP_ENGINE':'requests'}),patch('server.get_requests',return_value=OK),patch('curl_transport.get') as curl:
            self.assertEqual(get('https://example.com/'),OK)
            curl.assert_not_called()
    def test_force_curl(self):
        with patch.dict(os.environ,{'RES_HTTP_ENGINE':'curl'}),patch('server.get_requests') as old,patch('curl_transport.get',return_value=OK):
            self.assertEqual(get('https://example.com/'),OK)
            old.assert_not_called()

if __name__=='__main__': unittest.main()
