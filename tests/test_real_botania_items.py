"""End-to-end static conversion of a real, publicly released Fabric mod.

This downloads the pinned Botania 1.20.1-456 Fabric JAR and NEVER executes it.
The test validates generated archive structure, not in-game Bedrock behavior.
"""
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import urllib.request
import zipfile

URL = "https://github.com/VazkiiMods/Botania/releases/download/release-1.20.1-456/Botania-1.20.1-456-FABRIC.jar"
MAX_BYTES = 32 * 1024 * 1024


class BotaniaItemsIntegration(unittest.TestCase):
    def test_real_fabric_items(self):
        req = urllib.request.Request(URL, headers={"User-Agent": "RES-static-mod-integration-test"})
        with urllib.request.urlopen(req, timeout=90) as response:
            raw = response.read(MAX_BYTES + 1)
        self.assertLessEqual(len(raw), MAX_BYTES, "mod download exceeds static analysis limit")
        with zipfile.ZipFile(io.BytesIO(raw)) as jar:
            names = jar.namelist()
            models = [p for p in names if "/models/item/" in p and p.endswith(".json")]
            textures = [p for p in names if "/textures/item/" in p and p.endswith(".png")]
            print("BOTANIA_JAR_ENTRIES:", len(names), flush=True)
            print("BOTANIA_ITEM_MODELS:", len(models), flush=True)
            print("BOTANIA_ITEM_TEXTURES:", len(textures), flush=True)
            self.assertGreater(len(models), 0, "real JAR has no item model JSON")
        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / "botania.jar"
            out = pathlib.Path(tmp) / "botania.mcaddon"
            src.write_bytes(raw)
            run = subprocess.run([sys.executable, "bedrock_converter.py", str(src), str(out)],
                                 capture_output=True, text=True, timeout=120)
            print("RES_STDOUT:", run.stdout[:10000], flush=True)
            print("RES_STDERR:", run.stderr[:3000], flush=True)
            self.assertEqual(run.returncode, 0, "RES conversion process failed")
            self.assertTrue(out.is_file())
            with zipfile.ZipFile(out) as addon:
                report = json.loads(addon.read("conversion-report.json"))
                result = report["conversion"]
                print("BOTANIA_CONVERSION:", json.dumps(result, indent=2)[:15000], flush=True)
                print("BOTANIA_BLOCKS_CONVERTED:", result.get("blocks_converted", 0), flush=True)
                self.assertGreater(result.get("items_converted", 0), 0,
                                   "No real Java item models converted")
                self.assertIn("RES_Java_Assets.mcpack", addon.namelist())
                self.assertIn("RES_Java_Recipes.mcpack", addon.namelist())
                with zipfile.ZipFile(io.BytesIO(addon.read("RES_Java_Assets.mcpack"))) as rp:
                    atlas = json.loads(rp.read("textures/item_texture.json"))
                    self.assertGreater(len(atlas["texture_data"]), 0)
                with zipfile.ZipFile(io.BytesIO(addon.read("RES_Java_Recipes.mcpack"))) as bp:
                    item_files = [x for x in bp.namelist() if x.startswith("items/") and x.endswith(".json")]
                    self.assertEqual(len(item_files), result["items_converted"])
                    block_files = [x for x in bp.namelist() if x.startswith("blocks/") and x.endswith(".json")]
                    self.assertEqual(len(block_files), result.get("blocks_converted", 0))
                    for block_path in block_files:
                        block = json.loads(bp.read(block_path))
                        self.assertIn("minecraft:block", block)
                    for item_path in item_files:
                        item = json.loads(bp.read(item_path))
                        self.assertIn("minecraft:item", item)
            # Save the converted add-on as an Actions artifact for manual game import.
            artifact_dir = pathlib.Path("integration-artifacts")
            artifact_dir.mkdir(exist_ok=True)
            (artifact_dir / "botania-static.mcaddon").write_bytes(out.read_bytes())
            (artifact_dir / "conversion-report.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    unittest.main()
