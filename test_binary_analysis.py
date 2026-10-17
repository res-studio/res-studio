import os
import struct
import tempfile
import unittest
from pathlib import Path

from binary_analysis import BinaryAnalysisError, inspect_binary, MAX_FILE_SIZE


class BinaryAnalysisTests(unittest.TestCase):
    def inspect_data(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.bin"
            path.write_bytes(data)
            return inspect_binary(path)

    def test_pe_x64(self):
        data = bytearray(128)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 64)
        data[64:68] = b"PE\0\0"
        struct.pack_into("<H", data, 68, 0x8664)
        result = self.inspect_data(data)
        self.assertEqual((result["format"], result["architecture"]), ("PE", "x86_64"))

    def test_elf_arm64(self):
        data = bytearray(64)
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", data, 18, 183)
        result = self.inspect_data(data)
        self.assertEqual((result["format"], result["architecture"], result["bits"]), ("ELF", "arm64", 64))

    def test_macho(self):
        result = self.inspect_data(b"\xcf\xfa\xed\xfe" + bytes(40))
        self.assertEqual((result["format"], result["bits"]), ("Mach-O", 64))

    def test_unknown(self):
        self.assertEqual(self.inspect_data(b"hello")["format"], "unknown")

    def test_truncated_pe(self):
        data = bytearray(64)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 0xFFFFFFFF)
        self.assertEqual(self.inspect_data(data)["format"], "unknown")

    def test_missing_file(self):
        with self.assertRaises(BinaryAnalysisError):
            inspect_binary("/path/that/does/not/exist")

    def test_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            link = Path(directory) / "link"
            source.write_bytes(b"test")
            link.symlink_to(source)
            with self.assertRaises(BinaryAnalysisError):
                inspect_binary(link)

    def test_size_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized"
            with path.open("wb") as stream:
                stream.truncate(MAX_FILE_SIZE + 1)
            with self.assertRaises(BinaryAnalysisError):
                inspect_binary(path)


if __name__ == "__main__":
    unittest.main()
