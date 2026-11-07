"""Tests for deterministic prefab capture and instantiation."""

import json
import unittest
from dataclasses import dataclass

from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.prefab import Prefab
from keystone.primitives import cube
from keystone.scene import Node, Scene, Transform


@dataclass
class Health:
    value: int


class PrefabTest(unittest.TestCase):
    def _scene(self):
        scene = Scene()
        parent = Node("hero", id="hero", tags={"player"}, layer="actors")
        parent.add_component(Health(100))
        child = Node(
            "sword",
            id="sword",
            transform=Transform(position=Vec3(0.0, 1.0, 0.0)),
            mesh=cube(0.2),
            material=Material(),
        )
        parent.add_child(child)
        scene.add(parent)
        scene.add(Node("floor", id="floor"))
        return scene

    def test_capture_and_instantiate_a_subtree(self):
        scene = self._scene()
        prefab = Prefab.from_node(scene.find_by_id("hero"), name="hero-prefab")
        self.assertEqual(prefab.name, "hero-prefab")
        self.assertEqual(prefab.node_count, 2)
        self.assertEqual(prefab.describe()["nodes"][0]["components"], ["Health"])

        target = Scene()
        roots = prefab.instantiate(target, instance="p1")
        self.assertEqual([node.id for node in roots], ["p1:hero"])
        hero = target.find_by_id("p1:hero")
        self.assertIsNotNone(hero)
        self.assertEqual(hero.name, "hero")
        self.assertEqual(hero.tags, {"player"})
        self.assertEqual(hero.layer, "actors")
        self.assertEqual(hero.require_component(Health), Health(100))
        sword = target.find_by_id("p1:sword")
        self.assertIsNotNone(sword)
        self.assertIs(sword.parent, hero)
        self.assertEqual(sword.transform.position, Vec3(0.0, 1.0, 0.0))

    def test_instances_are_isolated_and_ids_are_unique(self):
        prefab = Prefab.from_scene(self._scene(), name="level")
        scene = Scene()
        prefab.instantiate(scene, instance="a")
        prefab.instantiate(scene, instance="b")
        self.assertIsNotNone(scene.find_by_id("a:hero"))
        self.assertIsNotNone(scene.find_by_id("b:hero"))
        scene.find_by_id("a:hero").require_component(Health).value = 1
        self.assertEqual(scene.find_by_id("b:hero").require_component(Health).value, 100)
        with self.assertRaises(ValueError):
            prefab.instantiate(scene, instance="a")

    def test_auto_ids(self):
        prefab = Prefab.from_node(self._scene().find_by_id("hero"))
        scene = Scene()
        roots = prefab.instantiate(scene)
        self.assertEqual(len(roots), 1)
        self.assertTrue(roots[0].id.startswith("node-"))

    def test_describe_is_json_safe(self):
        prefab = Prefab.from_scene(self._scene(), name="level")
        payload = prefab.describe()
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(payload["name"], "level")
        self.assertEqual(payload["node_count"], 3)
        json.dumps(payload, allow_nan=False)

    def test_validation(self):
        with self.assertRaises(ValueError):
            Prefab("", ())
        with self.assertRaises(ValueError):
            Prefab("x", ())
        with self.assertRaises(ValueError):
            Prefab.from_node(self._scene().find_by_id("hero"), name="")
        with self.assertRaises(ValueError):
            Prefab.from_node(self._scene().find_by_id("hero")).instantiate(Scene(), instance="")


if __name__ == "__main__":
    unittest.main()
