"""Strict, data-driven port of Java crafting recipes to Bedrock.

This module does not translate arbitrary Java bytecode.
Only vanilla-item crafting recipes with explicit item IDs are supported.
"""
from __future__ import annotations

import json
import re
import zipfile

NAME = re.compile(r"^[a-z0-9_.-]+$")
RECIPE_PATH = re.compile(r"^data/([a-z0-9_.-]+)/recipes?/([a-z0-9_./-]+)[.]json$")
MAX_RECIPE_SIZE = 128 * 1024
MAX_RECIPES = 300


def _item(value):
    if isinstance(value, str):
        name = value
    elif isinstance(value, dict) and isinstance(value.get("item"), str):
        name = value["item"]
    else:
        return None
    if ":" not in name:
        name = "minecraft:" + name
    namespace, _, path = name.partition(":")
    if namespace != "minecraft" or not NAME.fullmatch(path):
        return None
    return name


def _result(value):
    if isinstance(value, str):
        value = {"item": value}
    if not isinstance(value, dict):
        return None
    item = _item(value)
    count = value.get("count", 1)
    if item is None or type(count) is not int or not 1 <= count <= 64:
        return None
    return {"item": item, "count": count}


def convert_recipe(value, identifier):
    if not isinstance(value, dict):
        return None
    kind = value.get("type")
    result = _result(value.get("result"))
    if result is None:
        return None
    description = {"identifier": identifier}
    if kind == "minecraft:crafting_shapeless":
        ingredients = value.get("ingredients")
        if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 9:
            return None
        mapped = [_item(v) for v in ingredients]
        if any(v is None for v in mapped):
            return None
        return {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
            "description": description, "tags": ["crafting_table"],
            "ingredients": [{"item": v} for v in mapped], "result": result}}
    if kind == "minecraft:crafting_shaped":
        pattern, key = value.get("pattern"), value.get("key")
        if not isinstance(pattern, list) or not 1 <= len(pattern) <= 3 or not isinstance(key, dict):
            return None
        if any(not isinstance(row, str) or not 1 <= len(row) <= 3 for row in pattern):
            return None
        width = len(pattern[0])
        if any(len(row) != width for row in pattern):
            return None
        symbols = set("".join(pattern)) - {" "}
        if any(len(k) != 1 for k in key) or set(key) != symbols:
            return None
        mapped = {k: _item(key[k]) for k in symbols}
        if any(v is None for v in mapped.values()):
            return None
        return {"format_version": "1.20.10", "minecraft:recipe_shaped": {
            "description": description, "tags": ["crafting_table"],
            "pattern": pattern, "key": {k: {"item": v} for k, v in mapped.items()},
            "result": result}}
    return None


def extract_recipes(source: zipfile.ZipFile):
    """Return (Bedrock JSON files, report); no custom mod items are invented."""
    output, skipped = {}, []
    candidates = 0
    for entry in source.infolist():
        match = RECIPE_PATH.fullmatch(entry.filename)
        if not match:
            continue
        candidates += 1
        if candidates > MAX_RECIPES:
            skipped.append({"path": entry.filename, "reason": "recipe limit"})
            break
        namespace, name = match.groups()
        if any(part in ("", ".", "..") for part in name.split("/")):
            skipped.append({"path": entry.filename, "reason": "unsafe recipe path"})
            continue
        if entry.file_size > MAX_RECIPE_SIZE or entry.is_dir():
            skipped.append({"path": entry.filename, "reason": "oversized"})
            continue
        try:
            parsed = json.loads(source.read(entry))
            result = convert_recipe(parsed, f"res_import:{namespace}_{name.replace('/', '_')}")
        except (ValueError, UnicodeError, KeyError, TypeError):
            result = None
        if result is None:
            skipped.append({"path": entry.filename, "reason": "unsupported recipe or modded ingredient"})
            continue
        output[f"recipes/{namespace}/{name}.json"] = json.dumps(result, indent=2).encode()
    return output, {"recipes_converted": len(output), "recipes_skipped": skipped}
