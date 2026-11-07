"""Tests for glTF/GLB prefab import and project attachment."""

import base64
import json
import struct
import tempfile
import unittest
from pathlib import Path

from keystone.assets import AssetRegistry
from keystone.gltf_import import import_gltf_prefab, is_gltf_asset
from keystone.prefab_library import PrefabLibrary
from keystone.project import (
    ProjectManifest,
    attach_project_assets,
    load_project,
    save_project,
)
from keystone.samples import CubeDemo


def _triangle_gltf():
    positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    data = struct.pack("<9f", *positions)
    uri = "data:application/octet-stream;base64," + base64.b64encode(data).decode()
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "tri", "mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "material": 0}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(data), "target": 34962}
        ],
        "buffers": [{"uri": uri, "byteLength": len(data)}],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.2, 0.4, 0.6, 1.0],
                    "roughnessFactor": 0.25,
                }
            }
        ],
    }


class GltfPrefabImportTest(unittest.TestCase):
    def test_import_registers_assets_and_saves_a_prefab(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "model.gltf"
            path.write_text(json.dumps(_triangle_gltf()), encoding="utf-8")
            registry = AssetRegistry()
            library = PrefabLibrary(root / "prefabs", registry=registry)

            prefab = import_gltf_prefab(path, registry, library)
            self.assertEqual(prefab.name, "model")
            self.assertEqual(prefab.node_count, 1)
            self.assertIn("gltf.model.mesh.0", registry.ids())
            self.assertIn("gltf.model.material.0", registry.ids())
            self.assertTrue(library.path_for("model").is_file())
            self.assertIsNone(library.entry("model").error)

            loaded = library.load("model")
            self.assertIs(
                loaded.roots[0].mesh, registry.require("gltf.model.mesh.0").payload
            )
            self.assertIn("gltf.model.mesh.0", loaded.asset_ids(registry))
            self.assertTrue(is_gltf_asset(path))
            self.assertTrue(is_gltf_asset("model.GLB"))
            self.assertFalse(is_gltf_asset("model.obj"))

    def test_import_replaces_derived_assets_on_reimport(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "model.gltf"
            path.write_text(json.dumps(_triangle_gltf()), encoding="utf-8")
            registry = AssetRegistry()
            library = PrefabLibrary(root / "prefabs", registry=registry)
            import_gltf_prefab(path, registry, library)
            prefab = import_gltf_prefab(path, registry, library)
            self.assertEqual(prefab.name, "model")
            self.assertEqual(registry.ids("mesh"), ("gltf.model.mesh.0",))

    def test_import_rejects_bad_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = AssetRegistry()
            library = PrefabLibrary(root / "prefabs", registry=registry)
            with self.assertRaises(FileNotFoundError):
                import_gltf_prefab(root / "missing.gltf", registry, library)
            obj = root / "model.obj"
            obj.write_text("v 0 0 0", encoding="utf-8")
            with self.assertRaises(ValueError):
                import_gltf_prefab(obj, registry, library)
            path = root / "model.gltf"
            path.write_text(json.dumps(_triangle_gltf()), encoding="utf-8")
            with self.assertRaises(TypeError):
                import_gltf_prefab(path, object(), library)
            with self.assertRaises(TypeError):
                import_gltf_prefab(path, registry, object())
            with self.assertRaises(ValueError):
                import_gltf_prefab(path, registry, library, name="bad name")


class ProjectGltfAttachmentTest(unittest.TestCase):
    def test_project_attachment_imports_gltf_prefab_and_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            assets = root / "assets"
            assets.mkdir(parents=True)
            (assets / "model.gltf").write_text(
                json.dumps(_triangle_gltf()), encoding="utf-8"
            )
            manifest = ProjectManifest(
                name="gltf-project",
                game="keystone.samples:CubeDemo",
                assets=("assets/model.gltf",),
            )
            save_project(root, manifest)
            game = CubeDemo()
            records = attach_project_assets(game, load_project(root))
            self.assertEqual(records, ())
            self.assertIn("gltf.model.mesh.0", game.assets.ids())
            self.assertTrue((root / "prefabs" / "model.kprefab").is_file())
            loaded = PrefabLibrary(
                root / "prefabs", registry=game.assets
            ).load("model")
            self.assertIs(
                loaded.roots[0].mesh, game.assets.require("gltf.model.mesh.0").payload
            )


if __name__ == "__main__":
    unittest.main()
