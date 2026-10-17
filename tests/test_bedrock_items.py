import io
import json
import unittest
import zipfile

from bedrock_converter import convert_static


def jar_with_item(parent="item/generated", layer="demo:item/gem"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("fabric.mod.json", json.dumps({
            "schemaVersion": 1, "id": "demo", "version": "1.0.0",
            "name": "Demo", "environment": "*"
        }))
        z.writestr("assets/demo/models/item/gem.json", json.dumps({
            "parent": parent, "textures": {"layer0": layer}
        }))
        z.writestr("assets/demo/textures/item/gem.png",
                   bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082"))
    return buffer.getvalue()


class ItemConversionTest(unittest.TestCase):
    def test_generated_item_packaged(self):
        addon, report = convert_static(jar_with_item())
        self.assertEqual(report["conversion"]["items_converted"], 1)
        with zipfile.ZipFile(io.BytesIO(addon)) as archive:
            resource = archive.read("RES_Java_Assets.mcpack")
            behavior = archive.read("RES_Java_Recipes.mcpack")
        with zipfile.ZipFile(io.BytesIO(resource)) as rp:
            atlas = json.loads(rp.read("textures/item_texture.json"))
            self.assertIn("res_demo_gem", atlas["texture_data"])
            self.assertIn("textures/java_import/demo/item/gem.png", rp.namelist())
        with zipfile.ZipFile(io.BytesIO(behavior)) as bp:
            item = json.loads(bp.read("items/demo/gem.json"))
            self.assertEqual(item["minecraft:item"]["description"]["identifier"], "res_import:demo_gem")

    def test_unsupported_parent_skipped(self):
        addon, report = convert_static(jar_with_item(parent="minecraft:block/cube_all"))
        self.assertEqual(report["conversion"]["items_converted"], 0)

    def test_missing_texture_skipped(self):
        addon, report = convert_static(jar_with_item(layer="demo:item/missing"))
        self.assertEqual(report["conversion"]["items_converted"], 0)


if __name__ == "__main__":
    unittest.main()
