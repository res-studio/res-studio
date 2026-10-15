import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import deep_jobs
from server import deep_export
from fastapi import HTTPException


class DeepExportTests(unittest.TestCase):
    def test_export_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            token='testtoken'
            db=Path(tmp)/token/'assets.sqlite3'
            db.parent.mkdir()
            with sqlite3.connect(db) as conn:
                conn.execute('CREATE TABLE assets (id INTEGER PRIMARY KEY, url TEXT, type TEXT, size INTEGER, content TEXT)')
                conn.execute('INSERT INTO assets VALUES (0, ?, ?, ?, ?)',('https://example.com/','html',12,'<h1>Hi</h1>'))
                conn.execute('INSERT INTO assets VALUES (1, ?, ?, ?, ?)',('https://example.com/a.js','js',8,'var x=1;'))
            with patch.object(deep_jobs,'ROOT',Path(tmp)), patch.object(deep_jobs,'status',return_value={'status':'completed','errors':[],'truncated':False}):
                for mode in ('original','analyzed','reconstructed'):
                    response=deep_export(token,mode)
                    import asyncio
                    async def collect():
                        return b''.join([part async for part in response.body_iterator])
                    data=asyncio.run(collect())
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        names=archive.namelist()
                        self.assertIn('report.json',names)
                        self.assertIn('assets/0000.html',names)
                        self.assertIn('assets/0001.js',names)
                        self.assertEqual(json.loads(archive.read('report.json'))['mode'],mode)
                        self.assertEqual('analyzed/0001.js' in names,mode!='original')
                        self.assertEqual('README.txt' in names,mode=='reconstructed')
                with self.assertRaises(HTTPException):
                    deep_export(token,'invalid')


if __name__=='__main__':
    unittest.main()
