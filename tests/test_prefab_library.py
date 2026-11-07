"""Tests for file-backed prefab libraries."""

import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from keystone.assets import AssetRegistry
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.prefab import Prefab
from keystone.prefab_library import PrefabLibrary
from keystone.primitives import cube
from keystone.scene import Node


@dataclass
class Health:
    value: int


class PrefabLibraryTest(unittest.TestCase):
    def _fixture(self, directory):
        registry = AssetRegistry()
        mesh = cube()
        material = Material(color=Vec3(0.2, 0.4, 0.6))
        registry.register("mesh.hero", mesh)
        registry.register("material.hero", material)
        node = Node("hero", id="hero", mesh=mesh, material=material)
        node.add_component(Health(4))
        prefab = Prefab.from_node(node, name="hero-template")
        library = PrefabLibrary(
            Path(directory) / "prefabs",
            registry=registry,
            component_types={"Health": Health},
        )
        return library, registry, prefab

    def test_save_load_and_describe(self):
        with tempfile.TemporaryDirectory() as directory:
            library, registry, prefab = self._fixture(directory)
            entry = library.save("hero-template", prefab)
            self.assertEqual(entry.name, "hero-template")
            self.assertEqual(entry.node_count, 1)
            self.assertTrue(entry.path.is_file())
            self.assertEqual(entry.path, library.path_for("hero-template"))

            loaded = library.load("hero-template")
            self.assertEqual(loaded.name, "hero-template")
            self.assertEqual(loaded.node_count, 1)
            self.assertEqual(loaded.roots[0].require_component(Health), Health(4))
            self.assertIs(loaded.roots[0].mesh, registry.require("mesh.hero").payload)

            reopened = PrefabLibrary(
                Path(directory) / "prefabs",
                registry=registry,
                component_types={"Health": Health},
            )
            entries = reopened.entries()
            self.assertEqual([item.name for item in entries], ["hero-template"])
            self.assertIsNone(entries[0].error)
            self.assertEqual(entries[0].node_count, 1)
            self.assertEqual(
                reopened.describe(),
                [
                    {
                        "name": "hero-template",
                        "node_count": 1,
                        "source": entry.path.as_posix(),
                        "error": None,
                    }
                ],
            )
            json.dumps(reopened.describe())

    def test_describe_reports_corrupt_and_invalid_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "prefabs"
            root.mkdir()
            (root / "broken.kprefab").write_text("{not json", encoding="utf-8")
            (root / "bad name.kprefab").write_text("{}", encoding="utf-8")
            library = PrefabLibrary(root)
            entries = library.entries()
            self.assertEqual([item.name for item in entries], ["bad name", "broken"])
            self.assertIsNotNone(entries[0].error)
            self.assertIn("letters, digits", entries[0].error)
            self.assertIsNotNone(entries[1].error)
            self.assertIn("could not load prefab", entries[1].error)
            json.dumps(library.describe())

    def test_names_are_safe_and_must_match_the_prefab(self):
        with tempfile.TemporaryDirectory() as directory:
            library, _, prefab = self._fixture(directory)
            for bad in ("", " ", "../escape", "a/b", "a b", ".hidden"):
                with self.assertRaises(ValueError):
                    library.path_for(bad)
            with self.assertRaises(ValueError):
                library.save("other-name", prefab)
            with self.assertRaises(KeyError):
                library.load("missing")
            with tempfile.TemporaryDirectory() as empty:
                self.assertEqual(PrefabLibrary(Path(empty) / "absent").entries(), ())

    def test_rename_and_delete_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            library, registry, prefab = self._fixture(directory)
            library.save("hero-template", prefab)
            renamed = library.rename("hero-template", "hero-alt")
            self.assertEqual(renamed.name, "hero-alt")
            self.assertFalse(library.path_for("hero-template").exists())
            self.assertTrue(library.path_for("hero-alt").is_file())
            loaded = library.load("hero-alt")
            self.assertEqual(loaded.name, "hero-alt")
            self.assertIs(loaded.roots[0].mesh, registry.require("mesh.hero").payload)

            library.path_for("other").write_bytes(library.path_for("hero-alt").read_bytes())
            with self.assertRaises(FileExistsError):
                library.rename("hero-alt", "other")
            with self.assertRaises(KeyError):
                library.rename("missing", "new")
            self.assertEqual(library.rename("hero-alt", "hero-alt").name, "hero-alt")

            path = library.delete("hero-alt")
            self.assertFalse(path.exists())
            with self.assertRaises(KeyError):
                library.delete("hero-alt")

    def test_duplicate_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            library, _, prefab = self._fixture(directory)
            library.save("hero-template", prefab)
            copied = library.duplicate("hero-template", "hero-copy")
            self.assertEqual(copied.name, "hero-copy")
            self.assertTrue(library.path_for("hero-template").exists())
            self.assertTrue(library.path_for("hero-copy").exists())
            loaded = library.load("hero-copy")
            self.assertEqual(loaded.name, "hero-copy")
            self.assertEqual(loaded.node_count, 1)
            with self.assertRaises(FileExistsError):
                library.duplicate("hero-template", "hero-copy")
            with self.assertRaises(KeyError):
                library.duplicate("missing", "new")
            with self.assertRaises(ValueError):
                library.duplicate("hero-template", "hero-template")

    def test_delete_moves_to_trash_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            library, _, prefab = self._fixture(directory)
            library.save("hero-template", prefab)
            path = library.delete("hero-template")
            self.assertFalse(path.exists())
            entries = library.trash()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["name"], "hero-template")
            restored = library.restore(entries[0]["trash"])
            self.assertEqual(restored.name, "hero-template")
            self.assertTrue(library.path_for("hero-template").is_file())
            self.assertEqual(library.trash(), [])
            with self.assertRaises(KeyError):
                library.restore(entries[0]["trash"])

            library.save("hero-template", prefab)
            library.delete("hero-template")
            library.save("hero-template", prefab)
            with self.assertRaises(FileExistsError):
                library.restore(library.trash()[0]["trash"])

    def test_load_requires_assets_and_component_types(self):
        with tempfile.TemporaryDirectory() as directory:
            library, registry, prefab = self._fixture(directory)
            library.save("hero-template", prefab)

            missing_assets = PrefabLibrary(
                Path(directory) / "prefabs", component_types={"Health": Health}
            )
            with self.assertRaises(ValueError):
                missing_assets.load("hero-template")
            self.assertIsNotNone(missing_assets.entry("hero-template").error)

            missing_types = PrefabLibrary(Path(directory) / "prefabs", registry=registry)
            with self.assertRaises(ValueError):
                missing_types.load("hero-template")
            self.assertIn("component_types", missing_types.entry("hero-template").error)


if __name__ == "__main__":
    unittest.main()
