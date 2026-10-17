import io
import json
import unittest
import zipfile

from bedrock_converter import convert_static
from java_mod_analyzer import InvalidMod


def make_jar(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, value in files.items():
            z.writestr(name, value)
    return out.getvalue()


class BedrockConverterTests(unittest.TestCase):
    def test_texture_export(self):
        source = make_jar({
            "fabric.mod.json": b'{"id":"demo"}',
            "assets/demo/textures/item/sword.png": b"PNG",
            "com/demo/Example.class": b"JAVA",
        })
        addon, report = convert_static(source)
        self.assertEqual(report["conversion"]["textures_copied"], 1)
        with zipfile.ZipFile(io.BytesIO(addon)) as outer:
            self.assertIn("RES_Java_Assets.mcpack", outer.namelist())
            with zipfile.ZipFile(io.BytesIO(outer.read("RES_Java_Assets.mcpack"))) as inner:
                self.assertIn("manifest.json", inner.namelist())
                self.assertEqual(inner.read("textures/java_import/demo/item/sword.png"), b"PNG")
                manifest = json.loads(inner.read("manifest.json"))
                self.assertEqual(manifest["modules"][0]["type"], "resources")

    def test_no_code_translation_claim(self):
        source = make_jar({"fabric.mod.json": b"{}", "Example.class": b"x"})
        _, report = convert_static(source)
        self.assertEqual(report["conversion"]["status"], "partial-assets-only")
        self.assertEqual(report["conversion"]["textures_copied"], 0)

    def test_invalid_input(self):
        with self.assertRaises(InvalidMod):
            convert_static(b"not a jar")


if __name__ == "__main__":
    unittest.main()
