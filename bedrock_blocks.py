"""Experimental static conversion of Java cross-plant models to Bedrock blocks.

Only explicit cross models with a single PNG are accepted; no Java logic is ported.
"""
import json
import re

MODEL = re.compile(r"assets/([a-z0-9_.-]+)/models/block/([a-z0-9_/-]+)\.json$")
MAX_BLOCKS = 150

def extract_blocks(source, textures):
    resources, behaviors, atlas = {}, {}, {}
    skipped = []
    names = []
    for entry in source.infolist():
        match = MODEL.fullmatch(entry.filename)
        if not match or len(behaviors) >= MAX_BLOCKS or entry.file_size > 131072:
            continue
        namespace, name = match.groups()
        if ".." in name.split("/"):
            continue
        try:
            model = json.loads(source.read(entry))
        except (ValueError, UnicodeError):
            continue
        if not isinstance(model, dict) or model.get("parent") not in ("minecraft:block/cross", "block/cross"):
            continue
        mapping = model.get("textures", {})
        if not isinstance(mapping, dict):
            continue
        texture = mapping.get("cross")
        if not isinstance(texture, str):
            continue
        if ":" in texture:
            texture_ns, texture_name = texture.split(":", 1)
        else:
            texture_ns, texture_name = namespace, texture
        if not re.fullmatch(r"[a-z0-9_.-]{1,64}", texture_ns) or not re.fullmatch(r"[a-z0-9_/-]+", texture_name):
            continue
        path = f"textures/java_import/{texture_ns}/{texture_name}.png"
        if path not in textures:
            skipped.append(entry.filename)
            continue
        key = f"res_plant_{namespace}_{name.replace('/', '_')}"
        identifier = f"res_import:{namespace}_{name.replace('/', '_')}_plant"
        if key in atlas:
            continue
        atlas[key] = {"textures": path.removesuffix(".png")}
        display = name.split("/")[-1].replace("_", " ").title()
        names.append(f"tile.{identifier}.name={display}")
        block = {
            "format_version": "1.21.0",
            "minecraft:block": {
                "description": {"identifier": identifier, "menu_category": {"category": "nature"}},
                "components": {
                    "minecraft:geometry": "geometry.res_cross_plant",
                    "minecraft:material_instances": {"*": {"texture": key, "render_method": "alpha_test"}},
                    "minecraft:collision_box": False,
                    "minecraft:selection_box": {"origin": [-4, 0, -4], "size": [8, 12, 8]},
                    "minecraft:destructible_by_mining": {"seconds_to_destroy": 0},
                    "minecraft:placement_filter": {"conditions": [{"allowed_faces": ["up"], "block_filter": ["minecraft:dirt", "minecraft:grass_block", "minecraft:farmland", "minecraft:podzol", "minecraft:coarse_dirt", "minecraft:rooted_dirt", "minecraft:moss_block"]}]}
                }
            }
        }
        behaviors[f"blocks/{namespace}/{name.replace('/', '_')}.json"] = json.dumps(block, indent=2).encode()
    if atlas:
        resources["texts/en_US.lang"] = ("\\n".join(names) + "\\n").replace("\\n", "\n").encode("utf-8")
        resources["texts/languages.json"] = json.dumps(["en_US"]).encode("utf-8")
        resources["textures/terrain_texture.json"] = json.dumps({
            "resource_pack_name": "RES Java asset import", "texture_name": "atlas.terrain", "texture_data": atlas
        }, indent=2).encode()
        # Two intersecting thin planes approximate the Java cross model.
        geometry = {"format_version": "1.12.0", "minecraft:geometry": [{
            "description": {"identifier": "geometry.res_cross_plant", "texture_width": 16, "texture_height": 16,
                            "visible_bounds_width": 2, "visible_bounds_height": 2, "visible_bounds_offset": [0, 0.5, 0]},
            "bones": [{"name": "plant", "pivot": [0, 0, 0], "cubes": [
                {"origin": [-7, 0, -0.05], "size": [14, 16, 0.1], "pivot": [0, 8, 0], "rotation": [0, 45, 0], "uv": [0, 0]},
                {"origin": [-7, 0, -0.05], "size": [14, 16, 0.1], "pivot": [0, 8, 0], "rotation": [0, -45, 0], "uv": [0, 0]}
            ]}]
        }]}
        resources["models/blocks/res_cross_plant.geo.json"] = json.dumps(geometry, indent=2).encode()
    return resources, behaviors, {"blocks_converted": len(behaviors), "block_models_missing_textures": len(skipped),
        "block_conversion_limitations": "Only explicit cross-model plants; visual placement must be verified in Bedrock"}
