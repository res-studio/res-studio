"""Safe, dependency-free static metadata inspection of executable files.

This module never executes uploaded bytes.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

MAX_FILE_SIZE = 64 * 1024 * 1024


class BinaryAnalysisError(ValueError):
    pass


def inspect_binary(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise BinaryAnalysisError("Expected a regular, non-symlink file")
    size = path.stat().st_size
    if size > MAX_FILE_SIZE:
        raise BinaryAnalysisError("File exceeds 64 MiB limit")
    data = path.read_bytes()
    if len(data) != size:
        raise BinaryAnalysisError("File changed during reading")
    result = {
        "format": "unknown",
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "architecture": "unknown",
    }
    if data.startswith(b"MZ") and len(data) >= 0x40:
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if pe_offset <= len(data) - 6 and data[pe_offset:pe_offset + 4] == b"PE\\0\\0":
            machine = struct.unpack_from("<H", data, pe_offset + 4)[0]
            result.update(format="PE", architecture={
                0x14c: "x86", 0x8664: "x86_64", 0xaa64: "arm64",
            }.get(machine, f"machine_0x{machine:04x}"))
    elif data.startswith(b"\x7fELF") and len(data) >= 20:
        endian = "<" if data[5] == 1 else ">" if data[5] == 2 else None
        if endian and data[4] in (1, 2):
            machine = struct.unpack_from(endian + "H", data, 18)[0]
            result.update(format="ELF", bits=32 if data[4] == 1 else 64,
                          architecture={3: "x86", 62: "x86_64", 40: "arm", 183: "arm64"}.get(machine, f"machine_{machine}"))
    elif len(data) >= 4:
        magic = data[:4]
        mach = {
            b"\xfe\xed\xfa\xce": ("Mach-O", 32),
            b"\xce\xfa\xed\xfe": ("Mach-O", 32),
            b"\xfe\xed\xfa\xcf": ("Mach-O", 64),
            b"\xcf\xfa\xed\xfe": ("Mach-O", 64),
            b"\xca\xfe\xba\xbe": ("Mach-O universal", None),
            b"\xbe\xba\xfe\xca": ("Mach-O universal", None),
        }.get(magic)
        if mach:
            result["format"] = mach[0]
            if mach[1]:
                result["bits"] = mach[1]
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Inspect executable metadata without running it")
    parser.add_argument("file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = inspect_binary(args.file)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
