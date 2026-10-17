"""Bounded, read-only binary inspection API.

POST /api/binary/inspect with application/octet-stream body.
No uploaded program is executed.
"""
import hashlib
import struct
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

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

@router.post("/api/binary/decompile")
async def decompile_upload(request: Request):
    """Optional local Ghidra backend; never execute uploaded programs.

    This does NOT provide a security sandbox. Use only in a dedicated
    isolated worker for untrusted executables.
    """
    if os.environ.get("RES_ENABLE_GHIDRA") != "1":
        raise HTTPException(503, "Ghidra desabilitado; configure RES_ENABLE_GHIDRA=1 em ambiente isolado")
    executable = os.environ.get("RES_GHIDRA_ANALYZE_HEADLESS", "")
    if not executable or not Path(executable).is_file():
        raise HTTPException(503, "Configure RES_GHIDRA_ANALYZE_HEADLESS")
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/octet-stream":
        raise HTTPException(415, "Use application/octet-stream")
    chunks = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_UPLOAD:
            raise HTTPException(413, "Binary exceeds 16 MiB limit")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(400, "Empty binary")
    metadata = inspect_bytes(data)
    if metadata["format"] not in ("PE", "ELF", "Mach-O"):
        raise HTTPException(422, "Formato não suportado pelo modo Ghidra")
    scripts = Path(__file__).resolve().parent / "ghidra_scripts"
    with tempfile.TemporaryDirectory(prefix="res-ghidra-") as folder:
        root = Path(folder)
        sample = root / "sample.bin"
        output = root / "pseudocode.txt"
        sample.write_bytes(data)
        cmd = [executable, str(root / "project"), "RESBinary",
               "-import", str(sample), "-scriptPath", str(scripts),
               "-postScript", "RESDecompile.java", str(output),
               "-deleteProject"]
        try:
            subprocess.run(cmd, cwd=str(root), timeout=120, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except subprocess.TimeoutExpired:
            raise HTTPException(504, "Tempo de descompilação excedido")
        except (OSError, subprocess.CalledProcessError):
            raise HTTPException(422, "Ghidra não conseguiu analisar o arquivo")
        if not output.is_file():
            raise HTTPException(422, "Ghidra não produziu pseudocódigo")
        with output.open("rb") as stream:
            pseudocode = stream.read(512_001)
        if len(pseudocode) > 512_000:
            raise HTTPException(413, "Saída de pseudocódigo excedeu 500 KiB")
        return {"metadata": metadata, "pseudocode": pseudocode.decode("utf-8", "replace"),
                "note": "Pseudocódigo aproximado; não é o código-fonte original"}
