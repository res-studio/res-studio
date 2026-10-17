import struct
import unittest

from fastapi.testclient import TestClient
from server import app


class BinaryAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_pe_upload(self):
        sample = bytearray(128)
        sample[:2] = b"MZ"
        struct.pack_into("<I", sample, 0x3C, 64)
        sample[64:68] = b"PE\0\0"
        struct.pack_into("<H", sample, 68, 0x8664)
        response = self.client.post("/api/binary/inspect", content=bytes(sample),
                                    headers={"content-type": "application/octet-stream"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["architecture"], "x86_64")

    def test_wrong_content_type(self):
        response = self.client.post("/api/binary/inspect", content=b"abc",
                                    headers={"content-type": "text/plain"})
        self.assertEqual(response.status_code, 415)

    def test_empty_upload(self):
        response = self.client.post("/api/binary/inspect", content=b"",
                                    headers={"content-type": "application/octet-stream"})
        self.assertEqual(response.status_code, 400)

    def test_oversize_header(self):
        response = self.client.post("/api/binary/inspect", content=b"abc",
                                    headers={"content-type": "application/octet-stream",
                                             "content-length": str(17 * 1024 * 1024)})
        self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main()
