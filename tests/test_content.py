"""Tests for the content digests shared by batching and the asset registry."""

import unittest
from unittest import mock

from keystone import content
from keystone.content import material_digest, mesh_digest
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.primitives import cube


class MeshDigestTest(unittest.TestCase):
    def test_equal_meshes_share_a_digest(self):
        self.assertEqual(mesh_digest(cube(1.0)), mesh_digest(cube(1.0)))

    def test_different_geometry_has_a_different_digest(self):
        self.assertNotEqual(mesh_digest(cube(1.0)), mesh_digest(cube(2.0)))

    def test_repeated_calls_reuse_the_cached_digest(self):
        mesh = cube(1.0)
        with mock.patch.object(content, "_hash_mesh", wraps=content._hash_mesh) as hashed:
            first = mesh_digest(mesh)
            second = mesh_digest(mesh)
        self.assertEqual(first, second)
        self.assertEqual(hashed.call_count, 1)

    def test_rejects_a_non_mesh(self):
        with self.assertRaises(TypeError):
            mesh_digest("cube")  # type: ignore[arg-type]


class MaterialDigestTest(unittest.TestCase):
    def test_equal_materials_share_a_digest(self):
        self.assertEqual(
            material_digest(Material(color=Vec3(0.2, 0.3, 0.4))),
            material_digest(Material(color=Vec3(0.2, 0.3, 0.4))),
        )

    def test_every_field_reaches_the_digest(self):
        base = Material(color=Vec3(0.2, 0.3, 0.4))
        changes = (
            Material(color=Vec3(0.4, 0.3, 0.2)),
            Material(color=base.color, specular=0.9),
            Material(color=base.color, shininess=8.0),
            Material(color=base.color, checker_scale=2.0),
            Material(color=base.color, metallic=0.8),
            Material(color=base.color, roughness=0.2),
            Material(color=base.color, emissive=Vec3(1.0, 0.0, 0.0)),
        )
        expected = material_digest(base)
        for changed in changes:
            with self.subTest(changed=changed):
                self.assertNotEqual(material_digest(changed), expected)

    def test_repeated_calls_reuse_the_cached_digest(self):
        material = Material(color=Vec3(0.2, 0.3, 0.4))
        with mock.patch.object(content, "_hash_material", wraps=content._hash_material) as hashed:
            first = material_digest(material)
            second = material_digest(material)
        self.assertEqual(first, second)
        self.assertEqual(hashed.call_count, 1)

    def test_rejects_a_non_material(self):
        with self.assertRaises(TypeError):
            material_digest("shiny")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
