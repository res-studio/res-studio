"""Conservative Bedrock custom-item generation from Java item model JSON.

Only simple generated/handheld models with a single layer0 PNG are supported.
No Java code, behavior, or complex model geometry is translated.
"""
from __future__ import annotations

import json
import re
import zipfile

NS = r"[a-z0-9_.-]{1,64}"
PATH = r"[a-z0-9_./-]+"
MODEL = re.compile(rf"^assets/({NS})/models/item/({PATH})\.json$")
TEXTURE = re.compile(rf"^({NS}):({PATH})$")
MAX_ITEMS = 200
MAX_MODEL_BYTES = 128 * 1024


def extract_items(source: zipfile.ZipFile, textures: dict[str, bytes]):
    """Return resource files, behavior files, and a conversion report."""
    resources, behaviors, skipped = {}, {}, []
    atlas = {}
    count = 0
    for entry in source.infolist():
        match = MODEL.fullmatch(entry.filename)
        if not match:
            continue
        count += 1
        if count > MAX_ITEMS:
            skipped.append({"path": entry.filename, "reason": "item limit"})
            break
        namespace, name = match.groups()
        if any(part in ("", ".", "..") for part in name.split("/")):
            skipped.append({"path": entry.filename, "reason": "unsafe item name"})
            continue
        if entry.file_size > MAX_MODEL_BYTES or entry.is_dir():
            skipped.append({"path": entry.filename, "reason": "oversized model"})
            continue
        try:
            model = json.loads(source.read(entry))
        except (ValueError, UnicodeError):
            model = None
        if not isinstance(model, dict) or model.get("parent") not in (
                "minecraft:item/generated", "item/generated",
                "minecraft:item/handheld", "item/handheld"):
            skipped.append({"path": entry.filename, "reason": "unsupported model parent"})
            continue
        layers = model.get("textures")
        if not isinstance(layers, dict) or not isinstance(layers.get("layer0"), str):
            skipped.append({"path": entry.filename, "reason": "missing layer0 texture"})
            continue
        if any(key.startswith("layer") and key != "layer0" for key in layers):
            skipped.append({"path": entry.filename, "reason": "multilayer model unsupported"})
            continue
        texture_id = layers["layer0"]
        if ":" not in texture_id:
            texture_id = namespace + ":" + texture_id
        texture_match = TEXTURE.fullmatch(texture_id)
        if not texture_match:
            skipped.append({"path": entry.filename, "reason": "invalid texture reference"})
            continue
        texture_ns, texture_name = texture_match.groups()
        if any(part in ("", ".", "..") for part in texture_name.split("/")):
            skipped.append({"path": entry.filename, "reason": "unsafe texture reference"})
            continue
        texture_path = f"textures/java_import/{texture_ns}/{texture_name}.png"
        if texture_path not in textures:
            skipped.append({"path": entry.filename, "reason": "texture not extracted"})
            continue
        safe_name = name.replace("/", "_")
        identifier = f"res_import:{namespace}_{safe_name}"
        icon = f"res_{namespace}_{safe_name}"
        if icon in atlas:
            skipped.append({"path": entry.filename, "reason": "duplicate item identifier"})
            continue
        atlas[icon] = {"textures": texture_path.removesuffix(".png")}
        item = {
            "format_version": "1.20.50",
            "minecraft:item": {
                "description": {"identifier": identifier, "menu_category": {"category": "items"}},
                "components": {
                    "minecraft:icon": {"texture": icon},
                    "minecraft:display_name": {"value": name.replace("_", " ").replace("/", " ").title()},
                },
            },
        }
        behaviors[f"items/{namespace}/{name}.json"] = json.dumps(item, indent=2).encode()
    if atlas:
        resources["textures/item_texture.json"] = json.dumps({
            "resource_pack_name": "RES Java asset import",
            "texture_name": "atlas.items",
            "texture_data": atlas,
        }, indent=2).encode()
    return resources, behaviors, {
        "items_converted": len(behaviors),
        "items_skipped": skipped,
        "item_conversion_limitations": "Only single-layer generated/handheld models; no Java behavior or 3D geometry",
    }
