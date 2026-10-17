import io
import json
import unittest
import zipfile

from bedrock_converter import convert_static
from bedrock_recipes import convert_recipe


class RecipePortTests(unittest.TestCase):
    def test_shapeless(self):
        result = convert_recipe({"type": "minecraft:crafting_shapeless",
            "ingredients": [{"item": "minecraft:stick"}],
            "result": {"item": "minecraft:torch", "count": 4}}, "res_import:demo")
        self.assertEqual(result["minecraft:recipe_shapeless"]["result"]["count"], 4)

    def test_shaped(self):
        result = convert_recipe({"type": "minecraft:crafting_shaped",
            "pattern": ["XX", " X"], "key": {"X": {"item": "minecraft:stone"}},
            "result": {"item": "minecraft:stick"}}, "res_import:demo")
        self.assertEqual(result["minecraft:recipe_shaped"]["pattern"], ["XX", " X"])

    def test_reject_modded_item(self):
        result = convert_recipe({"type": "minecraft:crafting_shapeless",
            "ingredients": [{"item": "example:magic"}],
            "result": {"item": "minecraft:stick"}}, "res_import:demo")
        self.assertIsNone(result)

    def test_addon_contains_behavior_pack(self):
        source = io.BytesIO()
        with zipfile.ZipFile(source, "w") as jar:
            jar.writestr("fabric.mod.json", '{"id":"demo"}')
            jar.writestr("data/demo/recipes/torch.json", json.dumps({
                "type": "minecraft:crafting_shapeless",
                "ingredients": [{"item": "minecraft:stick"}],
                "result": {"item": "minecraft:torch"}}))
        addon, report = convert_static(source.getvalue())
        self.assertEqual(report["conversion"]["recipes_converted"], 1)
        with zipfile.ZipFile(io.BytesIO(addon)) as result:
            with zipfile.ZipFile(io.BytesIO(result.read("RES_Java_Recipes.mcpack"))) as bp:
                self.assertIn("recipes/demo/torch.json", bp.namelist())


if __name__ == "__main__":
    unittest.main()
