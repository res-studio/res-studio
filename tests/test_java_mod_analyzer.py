import io
import json
import unittest
import zipfile

from java_mod_analyzer import analyze_jar, InvalidMod

def jar(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, value in files.items():
            z.writestr(name, value)
    return out.getvalue()

class JavaModAnalyzerTests(unittest.TestCase):
    def test_fabric(self):
        data = jar({"fabric.mod.json": json.dumps({"id": "example"}),
                    "com/example/Mod.class": b"bytecode",
                    "assets/example/textures/block/a.png": b"png"})
        result = analyze_jar(data)
        self.assertEqual(result["loader"], "fabric")
        self.assertEqual(result["class_count"], 1)
        self.assertEqual(result["conversion"]["status"], "analysis-only")

    def test_invalid(self):
        with self.assertRaises(InvalidMod):
            analyze_jar(b"not a jar")

    def test_traversal(self):
        with self.assertRaises(InvalidMod):
            analyze_jar(jar({"../evil": b"x"}))

    def test_archive_bomb_limit(self):
        with self.assertRaises(InvalidMod):
            analyze_jar(jar({f"item-{i}": b"x" for i in range(5001)}))

if __name__ == "__main__":
    unittest.main()
