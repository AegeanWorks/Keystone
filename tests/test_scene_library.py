"""Tests for file-backed scene libraries."""

import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from keystone.assets import AssetRegistry
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.primitives import cube
from keystone.scene import Node, Scene
from keystone.scene_library import SceneLibrary


@dataclass
class Health:
    value: int


class SceneLibraryTest(unittest.TestCase):
    def _fixture(self, directory):
        registry = AssetRegistry()
        mesh = cube()
        material = Material(color=Vec3(0.2, 0.4, 0.6))
        registry.register("mesh.hero", mesh)
        registry.register("material.hero", material)
        scene = Scene()
        scene.background = Vec3(0.1, 0.2, 0.3)
        scene.camera.position = Vec3(1.0, 2.0, 3.0)
        hero = Node("hero", id="hero", mesh=mesh, material=material)
        hero.add_component(Health(7))
        scene.add(hero)
        scene.add(Node("child", id="child"))
        library = SceneLibrary(
            Path(directory) / "scenes",
            registry=registry,
            component_types={"Health": Health},
        )
        return library, registry, scene

    def test_save_load_and_describe(self):
        with tempfile.TemporaryDirectory() as directory:
            library, registry, scene = self._fixture(directory)
            entry = library.save("level", scene)
            self.assertEqual(entry.name, "level")
            self.assertEqual(entry.node_count, 2)
            self.assertTrue(entry.path.is_file())
            self.assertEqual(entry.path, library.path_for("level"))

            loaded = library.load("level")
            self.assertEqual(loaded.background, scene.background)
            self.assertEqual(loaded.camera.position, scene.camera.position)
            hero = loaded.find_by_id("hero")
            self.assertIsNotNone(hero)
            self.assertEqual(hero.require_component(Health), Health(7))
            self.assertIs(hero.mesh, registry.require("mesh.hero").payload)

            reopened = SceneLibrary(
                Path(directory) / "scenes",
                registry=registry,
                component_types={"Health": Health},
            )
            entries = reopened.entries()
            self.assertEqual([item.name for item in entries], ["level"])
            self.assertIsNone(entries[0].error)
            self.assertEqual(entries[0].node_count, 2)
            self.assertEqual(
                reopened.describe(),
                [
                    {
                        "name": "level",
                        "node_count": 2,
                        "source": entry.path.as_posix(),
                        "error": None,
                    }
                ],
            )
            json.dumps(reopened.describe())

    def test_load_into_preserves_the_scene_object(self):
        with tempfile.TemporaryDirectory() as directory:
            library, _, scene = self._fixture(directory)
            library.save("level", scene)
            target = Scene()
            target.background = Vec3(9.0, 9.0, 9.0)
            target.add(Node("old", id="old"))
            result = library.load_into("level", target)
            self.assertIs(result, target)
            self.assertIsNone(target.find_by_id("old"))
            self.assertIsNotNone(target.find_by_id("hero"))
            self.assertEqual(target.find_by_id("hero").require_component(Health), Health(7))
            self.assertEqual(target.background, scene.background)
            self.assertEqual(target.camera.position, scene.camera.position)

    def test_describe_reports_corrupt_and_invalid_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "scenes"
            root.mkdir()
            (root / "broken.kscene").write_text("{not json", encoding="utf-8")
            (root / "bad name.kscene").write_text("{}", encoding="utf-8")
            library = SceneLibrary(root)
            entries = library.entries()
            self.assertEqual([item.name for item in entries], ["bad name", "broken"])
            self.assertIsNotNone(entries[0].error)
            self.assertIn("letters, digits", entries[0].error)
            self.assertIsNotNone(entries[1].error)
            self.assertIn("could not read scene", entries[1].error)
            json.dumps(library.describe())

    def test_names_and_missing_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            library, _, _scene = self._fixture(directory)
            for bad in ("", " ", "../escape", "a/b", "a b", ".hidden"):
                with self.assertRaises(ValueError):
                    library.path_for(bad)
            with self.assertRaises(KeyError):
                library.load("missing")
            with tempfile.TemporaryDirectory() as empty:
                self.assertEqual(SceneLibrary(Path(empty) / "absent").entries(), ())
            with self.assertRaises(TypeError):
                library.save("level", object())  # type: ignore[arg-type]

    def test_load_requires_assets_and_component_types(self):
        with tempfile.TemporaryDirectory() as directory:
            library, registry, scene = self._fixture(directory)
            library.save("level", scene)
            missing_assets = SceneLibrary(
                Path(directory) / "scenes", component_types={"Health": Health}
            )
            with self.assertRaises(ValueError):
                missing_assets.load("level")
            self.assertIsNotNone(missing_assets.entry("level").error)
            missing_types = SceneLibrary(Path(directory) / "scenes", registry=registry)
            with self.assertRaises(ValueError):
                missing_types.load("level")
            self.assertIn("component_types", missing_types.entry("level").error)


if __name__ == "__main__":
    unittest.main()
