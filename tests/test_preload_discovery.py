import unittest
from deep_scan import PageLinks, discover

class PreloadDiscoveryTests(unittest.TestCase):
    def test_preloads_and_modulepreloads(self):
        parser=PageLinks()
        parser.feed('<link rel="preload" as="script" href="/a.js"><link rel="preload" as="style" href="/a.css"><link rel="modulepreload" href="/b.js">')
        self.assertIn(('js','/a.js'),parser.assets)
        self.assertIn(('css','/a.css'),parser.assets)
        self.assertIn(('js','/b.js'),parser.assets)

    def test_bounded_discovery(self):
        urls=[]
        def fetch(url):
            urls.append(url)
            if url.endswith('/'):
                return b'<link rel="preload" as="script" href="/a.js">','text/html',url
            return b'const x=1','application/javascript',url
        result=discover('https://example.com/',fetch,max_assets=3,max_pages=1)
        self.assertEqual(len(result['files']),2)
        self.assertEqual(len(urls),2)

if __name__=='__main__':
    unittest.main()
