"""End-to-end smoke test: synthetic Fabric JAR -> RES converter -> Bedrock addon."""
import io
import json
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib


def png_pixel():
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff"))
            + chunk(b"IEND", b""))


class EndToEndBedrockTest(unittest.TestCase):
    def test_sample_fabric_jar_to_mcaddon(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            jar = root / "sample-fabric.jar"
            addon = root / "sample.mcaddon"
            with zipfile.ZipFile(jar, "w") as z:
                z.writestr("fabric.mod.json", json.dumps({
                    "schemaVersion": 1, "id": "res_sample", "version": "1.0.0",
                    "name": "RES Conversion Sample"}))
                z.writestr("assets/res_sample/textures/item/sample.png", png_pixel())
                z.writestr("data/res_sample/recipes/torch.json", json.dumps({
                    "type": "minecraft:crafting_shapeless",
                    "ingredients": [{"item": "minecraft:stick"}],
                    "result": {"item": "minecraft:torch", "count": 1}}))
            result = subprocess.run([sys.executable, "bedrock_converter.py", str(jar), str(addon)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(addon.is_file())
            with zipfile.ZipFile(addon) as z:
                self.assertIn("RES_Java_Assets.mcpack", z.namelist())
                self.assertIn("RES_Java_Recipes.mcpack", z.namelist())
                report = json.loads(z.read("conversion-report.json"))
                self.assertEqual(report["conversion"]["textures_copied"], 1)
                self.assertEqual(report["conversion"]["recipes_converted"], 1)
                with zipfile.ZipFile(io.BytesIO(z.read("RES_Java_Assets.mcpack"))) as rp:
                    self.assertEqual(rp.read("textures/java_import/res_sample/item/sample.png"), png_pixel())
                with zipfile.ZipFile(io.BytesIO(z.read("RES_Java_Recipes.mcpack"))) as bp:
                    self.assertIn("recipes/res_sample/torch.json", bp.namelist())
                    recipe = json.loads(bp.read("recipes/res_sample/torch.json"))
                    self.assertIn("minecraft:recipe_shapeless", recipe)


if __name__ == "__main__":
    unittest.main()
