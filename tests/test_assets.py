"""Unit tests for the asset registry: identity, digests and dependencies."""

import json
import os
import tempfile
import unittest
from pathlib import Path

import keystone
from keystone.assets import ASSET_KINDS, AssetRegistry
from keystone.geometry import Material, MeshData
from keystone.math3d import Vec3
from keystone.png import read_png, write_png
from keystone.primitives import cube, sphere
from keystone.texture import TextureData

FIRST_PIXELS = bytes((10, 20, 30, 255, 40, 50, 60, 255, 70, 80, 90, 255, 100, 110, 120, 255))
SECOND_PIXELS = bytes((1, 2, 3, 255, 4, 5, 6, 255, 7, 8, 9, 255, 10, 11, 12, 255))
OBJ_TEXT = """v 0 0 0
v 1 0 0
v 0 1 0
vn 0 0 1
f 1//1 2//1 3//1
"""


def _touch(path: Path) -> None:
    status = path.stat()
    os.utime(path, ns=(status.st_atime_ns, status.st_mtime_ns + 1_000_000_000))


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


class AssetFileSourceTest(unittest.TestCase):
    def test_register_file_uses_suffix_and_records_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            png_path = root / "grid.png"
            obj_path = root / "mesh.obj"
            write_png(png_path, 2, 2, FIRST_PIXELS)
            obj_path.write_text(OBJ_TEXT, encoding="utf-8")
            registry = AssetRegistry()
            texture = registry.register_file("texture.grid", png_path)
            mesh = registry.register_file("mesh.sample", obj_path)
            self.assertEqual(texture.kind, "texture")
            self.assertIsInstance(texture.payload, TextureData)
            self.assertEqual(mesh.kind, "mesh")
            self.assertIsInstance(mesh.payload, MeshData)
            self.assertEqual(texture.source, png_path)
            sources = {entry["id"]: entry for entry in registry.describe()["sources"]}
            self.assertEqual(sources["texture.grid"]["error"], None)
            self.assertEqual(sources["texture.grid"]["path"], png_path.as_posix())
            self.assertEqual(registry.refresh().checked, 2)

    def test_register_file_requires_kind_or_known_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "unknown.json"
            data.write_text("{}", encoding="utf-8")
            registry = AssetRegistry()
            with self.assertRaises(ValueError):
                registry.register_file("unknown", data)
            with self.assertRaises(ValueError):
                registry.register_file("material", data, kind="material")
            with self.assertRaises(FileNotFoundError):
                registry.register_file("missing", root / "nope.png")
            with self.assertRaises(TypeError):
                registry.register_file("wrong", data, kind="texture", loader=lambda path: cube())
            registry.register_file(
                "first", data, kind="texture", loader=lambda path: TextureData.checker(2)
            )
            with self.assertRaises(ValueError):
                registry.register_file(
                    "first", data, kind="texture", loader=lambda path: TextureData.checker(2)
                )

    def test_refresh_reports_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.png"
            write_png(path, 2, 2, FIRST_PIXELS)
            registry = AssetRegistry()
            registry.register_file("texture.grid", path)
            report = registry.refresh()
            self.assertEqual(report.checked, 1)
            self.assertEqual(report.unchanged, ("texture.grid",))
            self.assertEqual(report.reloaded, ())
            self.assertEqual(report.failed, ())
            self.assertEqual(report.missing, ())
            self.assertTrue(report.ok)
            json.dumps(report.describe())

    def test_refresh_reloads_changed_texture(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.png"
            write_png(path, 2, 2, FIRST_PIXELS)
            registry = AssetRegistry()
            registry.register_file("texture.grid", path)
            write_png(path, 2, 2, SECOND_PIXELS)
            _touch(path)
            report = registry.refresh()
            self.assertEqual(report.reloaded, ("texture.grid",))
            self.assertEqual(registry.require("texture.grid").payload.rgba, read_png(path)[2])

    def test_refresh_failure_keeps_last_good_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.png"
            write_png(path, 2, 2, FIRST_PIXELS)
            calls = {"count": 0}

            def flaky(path):
                calls["count"] += 1
                if calls["count"] == 1:
                    return TextureData.from_png(path)
                raise RuntimeError("boom")

            registry = AssetRegistry()
            registry.register_file("texture.grid", path, loader=flaky)
            original = registry.require("texture.grid").payload
            _touch(path)
            path.write_bytes(b"not a png")
            _touch(path)
            report = registry.refresh()
            self.assertEqual(report.failed[0][0], "texture.grid")
            self.assertIn("RuntimeError: boom", report.failed[0][1])
            self.assertEqual(registry.require("texture.grid").payload, original)
            self.assertFalse(report.ok)
            report2 = registry.refresh()
            self.assertEqual(report2.failed[0][0], "texture.grid")
            self.assertIn("RuntimeError: boom", report2.failed[0][1])

    def test_refresh_missing_then_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.png"
            write_png(path, 2, 2, FIRST_PIXELS)
            registry = AssetRegistry()
            registry.register_file("texture.grid", path)
            original = registry.require("texture.grid").payload
            path.unlink()
            report = registry.refresh()
            self.assertEqual(report.missing, ("texture.grid",))
            self.assertEqual(registry.require("texture.grid").payload, original)
            self.assertFalse(report.ok)
            write_png(path, 2, 2, SECOND_PIXELS)
            _touch(path)
            report2 = registry.refresh()
            self.assertEqual(report2.reloaded, ("texture.grid",))
            self.assertEqual(registry.require("texture.grid").payload.rgba, read_png(path)[2])

    def test_refresh_reports_loader_type_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.png"
            write_png(path, 2, 2, FIRST_PIXELS)
            calls = {"count": 0}

            def flaky_type(path):
                calls["count"] += 1
                if calls["count"] == 1:
                    return TextureData.from_png(path)
                return cube()

            registry = AssetRegistry()
            registry.register_file("texture.grid", path, loader=flaky_type)
            _touch(path)
            path.write_bytes(b"not a png")
            _touch(path)
            report = registry.refresh()
            self.assertEqual(report.failed[0][0], "texture.grid")
            self.assertTrue(report.failed[0][1].startswith("TypeError"))

    def test_dependencies_survive_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.png"
            write_png(path, 2, 2, FIRST_PIXELS)
            registry = AssetRegistry()
            registry.register_file("texture.grid", path)
            registry.register(
                "material.floor",
                Material(texture=registry.require("texture.grid").payload),
                dependencies=("texture.grid",),
            )
            write_png(path, 2, 2, SECOND_PIXELS)
            _touch(path)
            report = registry.refresh()
            self.assertEqual(report.reloaded, ("texture.grid",))
            self.assertEqual(registry.require("material.floor").dependencies, ("texture.grid",))
            self.assertEqual(registry.missing_dependencies(), ())

    def test_clear_and_remove_drop_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.png"
            write_png(path, 2, 2, FIRST_PIXELS)
            registry = AssetRegistry()
            registry.register_file("texture.grid", path)
            self.assertEqual(registry.refresh().checked, 1)
            registry.remove("texture.grid")
            self.assertEqual(registry.refresh().checked, 0)
            registry.register_file("texture.grid", path)
            registry.clear()
            self.assertEqual(registry.refresh().checked, 0)


if __name__ == "__main__":
    unittest.main()

