"""Tests for file-backed material libraries."""

import tempfile
import unittest
from pathlib import Path

from keystone.assets import AssetRegistry
from keystone.geometry import Material
from keystone.material_library import MaterialLibrary
from keystone.math3d import Vec3
from keystone.texture import TextureData


class MaterialLibraryTest(unittest.TestCase):
    def test_save_load_register_and_texture(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = AssetRegistry()
            texture = TextureData.checker(
                4,
                (0.0, 0.0, 0.0),
                (1.0, 1.0, 1.0),
                2,
                "checker",
            )
            registry.register("texture.checker", texture, kind="texture")
            library = MaterialLibrary(Path(directory) / "materials", registry)
            material = Material(
                color=Vec3(1.0, 0.8, 0.2),
                metallic=1.0,
                roughness=0.3,
                texture=texture,
            )
            entry = library.save("gold", material)
            self.assertEqual(entry.name, "gold")
            self.assertEqual(entry.texture, "texture.checker")
            loaded = library.load("gold")
            self.assertEqual(loaded.color, material.color)
            self.assertEqual(loaded.texture, texture)
            self.assertEqual(library.entries()[0].metallic, 1.0)
            self.assertEqual(library.register_all(registry), 1)
            record = registry.require("material.gold")
            self.assertEqual(record.kind, "material")
            self.assertEqual(record.payload.metallic, 1.0)

    def test_invalid_names_and_missing_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            library = MaterialLibrary(directory)
            with self.assertRaises(ValueError):
                library.save("../escape", Material())
            with self.assertRaises(KeyError):
                library.load("missing")


if __name__ == "__main__":
    unittest.main()
