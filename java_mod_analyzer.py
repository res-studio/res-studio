"""Read-only Minecraft Java mod JAR inspection; never executes mod code."""
from __future__ import annotations
import io
import json
import re
import zipfile

MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_ENTRIES = 12000
MAX_UNCOMPRESSED = 128 * 1024 * 1024
MAX_ENTRY_BYTES = 2 * 1024 * 1024

class InvalidMod(ValueError):
    pass

def analyze_jar(data: bytes) -> dict:
    if not isinstance(data, bytes) or len(data) > MAX_ARCHIVE_BYTES:
        raise InvalidMod("JAR exceeds 32 MiB or is not bytes")
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise InvalidMod("Not a valid ZIP/JAR archive")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES:
            raise InvalidMod("Too many archive entries")
        if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED:
            raise InvalidMod("Archive expands beyond 128 MiB")
        names = []
        for entry in entries:
            path = entry.filename.replace("\\", "/")
            if (path.startswith("/") or re.match(r"^[A-Za-z]:", path)
                    or any(part == ".." for part in path.split("/"))):
                raise InvalidMod("Unsafe archive path")
            if entry.flag_bits & 1:
                raise InvalidMod("Encrypted entries are unsupported")
            names.append(path)
        paths = set(names)
        loader = ("fabric" if "fabric.mod.json" in paths else
                  "quilt" if "quilt.mod.json" in paths else
                  "forge/neoforge" if any(n.endswith("META-INF/mods.toml") or
                     n.endswith("META-INF/neoforge.mods.toml") for n in names) else "unknown")
        metadata = {}
        for filename in ("fabric.mod.json", "quilt.mod.json", "mcmod.info"):
            if filename in paths:
                info = archive.getinfo(filename)
                if info.file_size > MAX_ENTRY_BYTES:
                    raise InvalidMod("Metadata too large")
                try:
                    metadata[filename] = json.loads(archive.read(filename).decode("utf-8"))
                except (UnicodeError, ValueError):
                    metadata[filename] = {"error": "invalid JSON"}
        return {
            "format": "minecraft-java-mod",
            "loader": loader,
            "class_count": sum(n.endswith(".class") for n in names),
            "assets": sorted(n for n in names if n.startswith("assets/") and not n.endswith("/"))[:500],
            "data_files": sorted(n for n in names if n.startswith("data/") and not n.endswith("/"))[:500],
            "metadata": metadata,
            "entries": len(entries),
            "conversion": {
                "status": "analysis-only",
                "note": "Java bytecode cannot run in Bedrock; conversion requires explicit behavior mapping."
            }
        }
