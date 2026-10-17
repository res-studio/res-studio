import io
import json
import unittest
import zipfile

from bedrock_blocks import extract_blocks


class CrossPlantTests(unittest.TestCase):
    def test_cross_plant_creates_block_and_geometry(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("assets/demo/models/block/flower.json", json.dumps({
                "parent": "minecraft:block/cross", "textures": {"cross": "demo:block/flower"}
            }))
        with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as archive:
            resources, blocks, report = extract_blocks(
                archive, {"textures/java_import/demo/block/flower.png": b"png"})
        self.assertEqual(report["blocks_converted"], 1)
        self.assertIn("models/blocks/res_cross_plant.geo.json", resources)
        self.assertIn("blocks/demo/flower.json", blocks)
        data = json.loads(blocks["blocks/demo/flower.json"])
        self.assertIn("minecraft:placement_filter", data["minecraft:block"]["components"])

    def test_missing_texture_is_not_converted(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("assets/demo/models/block/flower.json", json.dumps({
                "parent": "block/cross", "textures": {"cross": "demo:block/missing"}
            }))
        with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as archive:
            resources, blocks, report = extract_blocks(archive, {})
        self.assertEqual(report["blocks_converted"], 0)
        self.assertEqual(resources, {})
        self.assertEqual(blocks, {})


if __name__ == "__main__":
    unittest.main()
