"""Conservative Java-mod to Bedrock starter conversion.

Only static texture assets are packaged. Java code is never translated or run.
Optional Vineflower output is for manual porting, not automatic conversion.
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import subprocess
import tempfile
import uuid
import zipfile

from java_mod_analyzer import analyze_jar, InvalidMod

MAX_TEXTURE = 4 * 1024 * 1024
MAX_TEXTURES = 500
MOD_ID = re.compile(r"^[a-z0-9_.-]{1,64}$")


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")


def _pack(files: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in sorted(files.items()):
            z.writestr(name, content)
    return out.getvalue()


def convert_static(data: bytes) -> tuple[bytes, dict]:
    report = analyze_jar(data)
    if report["loader"] == "unknown":
        raise InvalidMod("Unrecognized Minecraft mod loader")
    textures = {}
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        for entry in source.infolist():
            match = re.fullmatch(r"assets/([a-z0-9_.-]+)/textures/(.+[.]png)", entry.filename)
            if not match:
                continue
            namespace, relative = match.groups()
            if not MOD_ID.fullmatch(namespace) or entry.file_size > MAX_TEXTURE:
                continue
            if len(textures) >= MAX_TEXTURES:
                break
            # These are copied as candidates, not guaranteed to be usable by Bedrock.
            target = f"textures/java_import/{namespace}/{relative}"
            textures[target] = source.read(entry)
    rp_header = {
        "name": "RES Java asset import",
        "description": "Unverified assets extracted from Java mod; manual mapping required",
        "uuid": str(uuid.uuid4()),
        "version": [1, 0, 0],
        "min_engine_version": [1, 20, 0],
    }
    manifest = {"format_version": 2, "header": rp_header,
                "modules": [{"type": "resources", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}]}
    report["conversion"] = {
        "status": "partial-assets-only",
        "textures_copied": len(textures),
        "limitations": [
            "No Java logic or classes translated",
            "Textures require Bedrock entity/block/item mappings",
            "Models, animations, recipes and gameplay require manual porting",
        ],
    }
    rp = _pack({"manifest.json": _json(manifest), **textures})
    addon = _pack({"RES_Java_Assets.mcpack": rp, "conversion-report.json": _json(report)})
    return addon, report


def decompile_vineflower(jar_path: str, vineflower_jar: str, output_dir: str) -> None:
    """Explicit opt-in. Run only on trusted mods in an isolated environment."""
    with open(jar_path, "rb") as source:
        analyze_jar(source.read())
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    subprocess.run(["java", "-jar", vineflower_jar, jar_path, output_dir],
                   check=True, timeout=120)


def main():
    parser = argparse.ArgumentParser(description="RES Minecraft Java asset converter")
    parser.add_argument("input", help="Minecraft Java mod JAR")
    parser.add_argument("output", help="Destination .mcaddon")
    parser.add_argument("--vineflower", help="Optional local Vineflower JAR for manual source review")
    parser.add_argument("--sources-dir", help="Directory for decompiled sources")
    args = parser.parse_args()
    if args.vineflower and not args.sources_dir:
        parser.error("--sources-dir required with --vineflower")
    data = pathlib.Path(args.input).read_bytes()
    addon, report = convert_static(data)
    pathlib.Path(args.output).write_bytes(addon)
    if args.vineflower:
        decompile_vineflower(args.input, args.vineflower, args.sources_dir)
    print(json.dumps(report["conversion"], indent=2))


if __name__ == "__main__":
    main()
