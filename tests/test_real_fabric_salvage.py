"""Integration test against a real, independently published Fabric mod release.

Requires network access. Does not run the mod or Minecraft.
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

RELEASE = ("https://github.com/SpaceBod/spacebod-mods/releases/download/"
           "salvage-v0.1.0/salvage-0.1.0%2Bmc26.1.jar")


class RealModTest(unittest.TestCase):
    def test_salvage_release(self):
        request = urllib.request.Request(RELEASE, headers={"User-Agent": "RES-real-mod-integration-test"})
        with urllib.request.urlopen(request, timeout=40) as response:
            jar_bytes = response.read(2 * 1024 * 1024 + 1)
        self.assertLessEqual(len(jar_bytes), 2 * 1024 * 1024)
        with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jar:
            names = jar.namelist()
            self.assertIn("fabric.mod.json", names)
            print("REAL_JAR_ENTRIES:", len(names))
            print("REAL_JAR_RECIPE_PATHS:", [n for n in names if "/recipe" in n][:15])
        with tempfile.TemporaryDirectory() as tmp:
            jar_path = pathlib.Path(tmp) / "salvage.jar"
            addon_path = pathlib.Path(tmp) / "salvage.mcaddon"
            jar_path.write_bytes(jar_bytes)
            result = subprocess.run(
                [sys.executable, "bedrock_converter.py", str(jar_path), str(addon_path)],
                capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(addon_path) as addon:
                report = json.loads(addon.read("conversion-report.json"))
                conversion = report["conversion"]
                print("REAL_MOD_CONVERSION_REPORT:", json.dumps(conversion, indent=2))
                self.assertIn("RES_Java_Assets.mcpack", addon.namelist())
                self.assertGreater(conversion["recipes_converted"], 0,
                    "Real Salvage mod recipes were not converted; inspect path/format compatibility")
                self.assertIn("RES_Java_Recipes.mcpack", addon.namelist())


if __name__ == "__main__":
    unittest.main()
