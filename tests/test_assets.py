"""Unit tests for the asset registry: identity, digests and dependencies."""

import json
import unittest
from pathlib import Path

import keystone
from keystone.assets import ASSET_KINDS, AssetRegistry
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.primitives import cube, sphere
from keystone.texture import TextureData


class AssetRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = AssetRegistry()

    def test_register_infers_kind_and_preserves_order(self):
        mesh = cube()
        material = Material(color=Vec3(0.2, 0.4, 0.6))
        texture = TextureData.checker(8, cell=4, name="grid")
        mesh_record = self.registry.register("mesh.cube", mesh)
        material_record = self.registry.register("material.blue", material)
        texture_record = self.registry.register("texture.grid", texture)
        self.assertEqual(ASSET_KINDS, ("mesh", "material", "texture"))
        self.assertEqual(mesh_record.kind, "mesh")
        self.assertEqual(material_record.kind, "material")
        self.assertEqual(texture_record.kind, "texture")
        self.assertEqual(self.registry.ids(), ("mesh.cube", "material.blue", "texture.grid"))
        self.assertEqual(self.registry.ids("texture"), ("texture.grid",))
        self.assertIs(self.registry.get("mesh.cube"), mesh_record)
        self.assertIn("material.blue", self.registry)
        self.assertEqual(len(self.registry), 3)
        self.assertEqual([record.id for record in self.registry], ["mesh.cube", "material.blue", "texture.grid"])
        self.assertEqual(self.registry.require("mesh.cube").payload, mesh)
        with self.assertRaises(KeyError) as caught:
            self.registry.require("missing")
        self.assertIn("missing", str(caught.exception))

    def test_register_rejects_bad_ids_kinds_and_payloads(self):
        for bad_id in ("", "   ", 7):
            with self.assertRaises((TypeError, ValueError)):
                self.registry.register(bad_id, cube())
        with self.assertRaises(TypeError):
            self.registry.register("mesh", cube(), kind="texture")
        with self.assertRaises(ValueError):
            self.registry.register("mesh", cube(), kind="audio")
        with self.assertRaises(TypeError):
            self.registry.register("unknown", object())

    def test_duplicate_id_requires_replace(self):
        first = cube()
        second = sphere()
        self.registry.register("shape", first)
        with self.assertRaises(ValueError):
            self.registry.register("shape", second)
        record = self.registry.register("shape", second, replace=True)
        self.assertEqual(record.payload, second)
        self.assertEqual(self.registry.ids(), ("shape",))

    def test_digest_is_content_based_and_duplicates_are_reported(self):
        first = self.registry.register("a", cube())
        second = self.registry.register("b", cube())
        third = self.registry.register("c", sphere())
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(len(first.sha256), 64)
        self.assertNotEqual(first.sha256, third.sha256)
        self.assertEqual(self.registry.duplicates(), (("a", "b"),))
        self.assertEqual([record.id for record in self.registry.find_by_digest(first.sha256)], ["a", "b"])

    def test_texture_and_material_digests_follow_their_content(self):
        texture = TextureData.checker(8, cell=4, name="grid")
        texture_record = self.registry.register("texture.grid", texture)
        plain = self.registry.register("material.plain", Material())
        textured = self.registry.register("material.textured", Material(texture=texture))
        self.assertEqual(texture_record.sha256, texture.sha256())
        self.assertNotEqual(plain.sha256, textured.sha256)

    def test_dependencies_are_sorted_and_missing_ones_reported(self):
        self.registry.register("texture.grid", TextureData.checker(8))
        record = self.registry.register(
            "material.floor",
            Material(),
            dependencies=("texture.missing", "texture.grid", "texture.grid"),
        )
        self.assertEqual(record.dependencies, ("texture.grid", "texture.missing"))
        self.assertEqual(self.registry.missing_dependencies(), (("material.floor", "texture.missing"),))
        with self.assertRaises(ValueError):
            self.registry.register("selfish", Material(), dependencies=("selfish",))
        with self.assertRaises(ValueError):
            self.registry.register("blank", Material(), dependencies=("",))
        with self.assertRaises(TypeError):
            self.registry.register("string", Material(), dependencies="texture.grid")

    def test_stats_and_describe_are_json_safe(self):
        texture = TextureData.checker(8)
        self.registry.register("b.texture", texture, source=Path("textures") / "grid.png")
        self.registry.register("a.mesh", cube())
        self.assertEqual(
            self.registry.stats(),
            {"total": 2, "kinds": {"mesh": 1, "material": 0, "texture": 1}},
        )
        document = self.registry.describe()
        self.assertEqual(document["schema"], 1)
        self.assertEqual([entry["id"] for entry in document["assets"]], ["a.mesh", "b.texture"])
        self.assertEqual(document["assets"][1]["source"], "textures/grid.png")
        self.assertEqual(document["assets"][1]["sha256"], texture.sha256())
        self.assertEqual(document["stats"], self.registry.stats())
        json.dumps(document)

    def test_public_package_exports_the_registry(self):
        self.assertIs(keystone.AssetRegistry, AssetRegistry)

    def test_remove_and_clear_dispose_records(self):
        record = self.registry.register("a", cube())
        self.assertEqual(self.registry.remove("a"), record)
        self.assertEqual(self.registry.stats()["total"], 0)
        with self.assertRaises(KeyError):
            self.registry.remove("a")
        self.registry.register("b", cube())
        self.registry.clear()
        self.assertEqual(self.registry.ids(), ())


if __name__ == "__main__":
    unittest.main()
