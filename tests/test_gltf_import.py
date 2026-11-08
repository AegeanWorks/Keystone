"""Tests for glTF/GLB prefab import and project attachment."""

import base64
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from keystone.assets import AssetRegistry
from keystone.gltf_import import import_gltf_prefab, is_gltf_asset
from keystone.prefab import Prefab
from keystone.prefab_library import PrefabLibrary
from keystone.project import (
    ProjectManifest,
    attach_project_assets,
    create_project,
    import_project_gltf,
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


class ProjectGltfEditorImportTest(unittest.TestCase):
    def test_project_gltf_import_updates_manifest_and_prefab_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="gltf-editor")
            assets = root / "assets"
            assets.mkdir()
            (assets / "model.gltf").write_text(
                json.dumps(_triangle_gltf()), encoding="utf-8"
            )
            registry = AssetRegistry()
            library = PrefabLibrary(root / "prefabs", registry=registry)
            report = import_project_gltf(
                load_project(root), registry, library, "assets/model.gltf"
            )
            self.assertEqual(report["path"], "assets/model.gltf")
            self.assertEqual(report["prefab"], "model")
            self.assertEqual(
                report["assets"],
                ["gltf.model.material.0", "gltf.model.mesh.0"],
            )
            self.assertEqual(report["asset_count"], 2)
            self.assertFalse(report["duplicate"])
            self.assertFalse(report["replaced_prefab"])
            self.assertEqual(report["count"], 1)
            self.assertEqual(
                load_project(root).manifest.assets, ("assets/model.gltf",)
            )
            self.assertTrue((root / "prefabs" / "model.kprefab").is_file())
            loaded = library.load("model")
            self.assertIs(
                loaded.roots[0].mesh,
                registry.require("gltf.model.mesh.0").payload,
            )

            again = import_project_gltf(
                load_project(root), registry, library, "./assets/model.gltf"
            )
            self.assertTrue(again["duplicate"])
            self.assertTrue(again["replaced_prefab"])
            self.assertEqual(again["count"], 1)

    def test_project_gltf_import_rejects_bad_sources_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="gltf-editor")
            assets = root / "assets"
            assets.mkdir()
            registry = AssetRegistry()
            library = PrefabLibrary(root / "prefabs", registry=registry)
            context = load_project(root)
            (assets / "cube.obj").write_text("v 0 0 0", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not a glTF"):
                import_project_gltf(
                    context, registry, library, "assets/cube.obj"
                )
            with self.assertRaises(ValueError):
                import_project_gltf(
                    context, registry, library, "../escape.gltf"
                )
            with self.assertRaises(FileNotFoundError):
                import_project_gltf(
                    context, registry, library, "assets/missing.glb"
                )
            bad = assets / "bad.gltf"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises((TypeError, ValueError)):
                import_project_gltf(
                    context, registry, library, "assets/bad.gltf"
                )
            self.assertEqual(load_project(root).manifest.assets, ())
            self.assertFalse((root / "prefabs" / "bad.kprefab").exists())
            self.assertEqual(registry.ids(), ())

            (assets / "named.gltf").write_text(
                json.dumps(_triangle_gltf()), encoding="utf-8"
            )
            named = import_project_gltf(
                context,
                registry,
                library,
                "assets/named.gltf",
                "custom-name",
            )
            self.assertEqual(named["prefab"], "custom-name")
            self.assertTrue(
                (root / "prefabs" / "custom-name.kprefab").is_file()
            )

    def test_project_gltf_reimport_failure_restores_replaced_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(root, name="gltf-rollback")
            assets = root / "assets"
            assets.mkdir()
            source = assets / "model.gltf"
            source.write_text(
                json.dumps(_triangle_gltf()), encoding="utf-8"
            )
            registry = AssetRegistry()
            library = PrefabLibrary(root / "prefabs", registry=registry)
            context = load_project(root)
            import_project_gltf(
                context, registry, library, "assets/model.gltf"
            )
            before = {record.id: record for record in registry}
            old_prefab = library.load("model")

            changed = _triangle_gltf()
            changed["materials"][0]["pbrMetallicRoughness"][
                "baseColorFactor"
            ] = [0.9, 0.1, 0.1, 1.0]
            source.write_text(json.dumps(changed), encoding="utf-8")
            with patch.object(
                Prefab,
                "from_scene",
                side_effect=RuntimeError("prefab build failed"),
            ), self.assertRaises(RuntimeError):
                import_project_gltf(
                    context, registry, library, "assets/model.gltf"
                )

            self.assertEqual(
                {record.id for record in registry}, set(before)
            )
            for asset_id, record in before.items():
                restored = registry.require(asset_id)
                self.assertIs(restored.payload, record.payload)
                self.assertEqual(restored.sha256, record.sha256)
            loaded = library.load("model")
            self.assertIs(
                loaded.roots[0].mesh,
                registry.require("gltf.model.mesh.0").payload,
            )
            self.assertIs(
                old_prefab.roots[0].mesh, loaded.roots[0].mesh
            )


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
