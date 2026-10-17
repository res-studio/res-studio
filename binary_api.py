"""Bounded, read-only binary inspection API.

POST /api/binary/inspect with application/octet-stream body.
No uploaded program is executed.
"""
import hashlib
import struct

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()
MAX_UPLOAD = 16 * 1024 * 1024


def inspect_bytes(data: bytes) -> dict:
    result = {"format": "unknown", "size": len(data),
              "sha256": hashlib.sha256(data).hexdigest(), "architecture": "unknown"}
    if data.startswith(b"MZ") and len(data) >= 0x40:
        offset = struct.unpack_from("<I", data, 0x3C)[0]
        if offset <= len(data) - 6 and data[offset:offset + 4] == b"PE\0\0":
            machine = struct.unpack_from("<H", data, offset + 4)[0]
            result.update(format="PE", architecture={
                0x14c: "x86", 0x8664: "x86_64", 0xaa64: "arm64"
            }.get(machine, f"machine_0x{machine:04x}"))
    elif data.startswith(b"\x7fELF") and len(data) >= 20:
        endian = "<" if data[5] == 1 else ">" if data[5] == 2 else None
        if endian and data[4] in (1, 2):
            machine = struct.unpack_from(endian + "H", data, 18)[0]
            result.update(format="ELF", bits=32 if data[4] == 1 else 64,
                          architecture={3: "x86", 62: "x86_64", 40: "arm",
                                        183: "arm64"}.get(machine, f"machine_{machine}"))
    elif len(data) >= 4:
        formats = {
            b"\xfe\xed\xfa\xce": ("Mach-O", 32),
            b"\xce\xfa\xed\xfe": ("Mach-O", 32),
            b"\xfe\xed\xfa\xcf": ("Mach-O", 64),
            b"\xcf\xfa\xed\xfe": ("Mach-O", 64),
            b"\xca\xfe\xba\xbe": ("Mach-O universal", None),
            b"\xbe\xba\xfe\xca": ("Mach-O universal", None),
        }
        matched = formats.get(data[:4])
        if matched:
            result["format"] = matched[0]
            if matched[1]:
                result["bits"] = matched[1]
    return result


@router.post("/api/binary/inspect")
async def inspect_upload(request: Request):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/octet-stream":
        raise HTTPException(415, "Use application/octet-stream")
    length = request.headers.get("content-length")
    if length:
        try:
            parsed_length = int(length)
        except ValueError:
            raise HTTPException(400, "Invalid content length")
        if parsed_length > MAX_UPLOAD:
            raise HTTPException(413, "Binary exceeds 16 MiB limit")
    chunks = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_UPLOAD:
            raise HTTPException(413, "Binary exceeds 16 MiB limit")
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(400, "Empty binary")
    return inspect_bytes(b"".join(chunks))
