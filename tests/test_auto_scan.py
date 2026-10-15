import unittest
from unittest.mock import patch
from fastapi import HTTPException
from server import Scan, scan_auto

class AutoScanTests(unittest.TestCase):
    def test_http_success(self):
        with patch('server.scan', return_value={'files':[], 'errors':[]}) as http:
            result=scan_auto(Scan(url='https://example.com'))
        self.assertEqual(result['mode'],'auto-http')
        http.assert_called_once()
    def test_disabled_fallback_explains(self):
        with patch('server.scan',side_effect=HTTPException(400,'HTTP 404')),patch.dict('os.environ',{'RES_ENABLE_ISOLATED_CHROMIUM':'0'}):
            with self.assertRaises(HTTPException) as ctx:
                scan_auto(Scan(url='https://example.com'))
        self.assertEqual(ctx.exception.status_code,422)
        self.assertIn('HTTP 404',str(ctx.exception.detail))
    def test_browser_fallback(self):
        with patch('server.scan',side_effect=HTTPException(400,'HTTP 404')),patch.dict('os.environ',{'RES_ENABLE_ISOLATED_CHROMIUM':'1'}),patch('server.scan_dynamic',return_value={'files':[{'id':0}],'errors':[]}) as browser:
            result=scan_auto(Scan(url='https://example.com'))
        self.assertEqual(result['mode'],'auto-browser')
        browser.assert_called_once()
    def test_both_fail_explains(self):
        with patch('server.scan',side_effect=HTTPException(400,'HTTP 404')),patch.dict('os.environ',{'RES_ENABLE_ISOLATED_CHROMIUM':'1'}),patch('server.scan_dynamic',side_effect=HTTPException(400,'HTTP 404')):
            with self.assertRaises(HTTPException) as ctx:
                scan_auto(Scan(url='https://example.com'))
        self.assertIn('mesmo 404',str(ctx.exception.detail))
if __name__=='__main__': unittest.main()
