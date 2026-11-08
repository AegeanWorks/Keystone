"""Tests for deterministic prefab capture, persistence and instantiation."""

import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from keystone.assets import AssetRegistry
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.prefab import PREFAB_SCHEMA_VERSION, Prefab
from keystone.primitives import cube
from keystone.scene import Node, PrefabLink, Scene, Transform


@dataclass
class Health:
    value: int


class Counter:
    """A component with an explicit codec."""

    def __init__(self, value: int = 0) -> None:
        self.value = value

    def to_dict(self) -> dict:
        return {"value": self.value}

    @classmethod
    def from_dict(cls, data: dict) -> "Counter":
        return cls(data["value"])


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

    def test_capture_and_instantiate_strip_instance_links(self):
        scene = self._scene()
        hero = scene.find_by_id("hero")
        hero.prefab_link = PrefabLink("hero-template", "p1")
        prefab = Prefab.from_node(hero, name="hero-copy")
        self.assertIsNone(prefab.roots[0].prefab_link)
        target = Scene()
        root = prefab.instantiate(target, instance="copy")[0]
        self.assertIsNone(root.prefab_link)

    def test_capture_several_roots_and_strip_instance_prefixes(self):
        left = Node("left", id="p1:left", prefab_link=PrefabLink("pair", "p1"))
        right = Node("right", id="p1:right", prefab_link=PrefabLink("pair", "p1"))
        prefab = Prefab.from_nodes([left, right], name="pair")
        self.assertEqual([root.id for root in prefab.roots], ["left", "right"])
        self.assertEqual([root.prefab_link for root in prefab.roots], [None, None])
        target = Scene()
        roots = prefab.instantiate(target, instance="p2")
        self.assertEqual([root.id for root in roots], ["p2:left", "p2:right"])
        with self.assertRaises(ValueError):
            Prefab.from_nodes([], name="pair")

    def test_nested_capture_and_instantiation_rebase_prefixes(self):
        scene = Scene()
        outer = Node("outer", id="outer-1:outer")
        nested = Node(
            "nested",
            id="outer-1.inner-1:nested",
            prefab_link=PrefabLink("inner", "outer-1.inner-1"),
        )
        nested.add_child(Node("blade", id="outer-1.inner-1:blade"))
        deep = Node(
            "deep",
            id="outer-1.inner-1.deep-1:deep",
            prefab_link=PrefabLink("leaf", "outer-1.inner-1.deep-1"),
        )
        deep.add_child(Node("tip", id="outer-1.inner-1.deep-1:tip"))
        nested.add_child(deep)
        outer.add_child(nested)
        outer.prefab_link = PrefabLink("outer", "outer-1")
        scene.add(outer)

        prefab = Prefab.from_node(outer, name="outer")
        root = prefab.roots[0]
        self.assertIsNone(root.prefab_link)
        self.assertEqual(root.id, "outer")
        nested_template = root.children[0]
        self.assertEqual(nested_template.id, "nested")
        self.assertEqual(
            nested_template.prefab_link, PrefabLink("inner", "inner-1")
        )
        self.assertEqual(nested_template.children[0].id, "blade")
        self.assertEqual(
            nested_template.children[1].prefab_link,
            PrefabLink("leaf", "deep-1"),
        )
        self.assertEqual(nested_template.children[1].id, "deep")
        self.assertEqual(nested_template.children[1].children[0].id, "tip")

        target = Scene()
        created = prefab.instantiate(target, instance="copy")[0]
        self.assertEqual(created.id, "copy:outer")
        nested_copy = target.find_by_id("copy.inner-1:nested")
        self.assertIsNotNone(nested_copy)
        self.assertEqual(
            nested_copy.prefab_link, PrefabLink("inner", "copy.inner-1")
        )
        self.assertIsNotNone(target.find_by_id("copy.inner-1:blade"))
        deep_copy = target.find_by_id("copy.inner-1.deep-1:deep")
        self.assertIsNotNone(deep_copy)
        self.assertEqual(
            deep_copy.prefab_link, PrefabLink("leaf", "copy.inner-1.deep-1")
        )
        self.assertIsNotNone(target.find_by_id("copy.inner-1.deep-1:tip"))

        auto = Scene()
        auto_root = prefab.instantiate(auto)[0]
        self.assertEqual(auto_root.id, "prefab:outer")
        self.assertEqual(
            auto.find_by_id("prefab.inner-1:nested").prefab_link,
            PrefabLink("inner", "prefab.inner-1"),
        )
        self.assertEqual(
            auto.find_by_id("prefab.inner-1.deep-1:deep").prefab_link,
            PrefabLink("leaf", "prefab.inner-1.deep-1"),
        )

    def test_nested_links_round_trip_and_schema_one_migrates(self):
        outer = Node("outer", id="outer")
        outer.add_child(
            Node(
                "nested",
                id="nested",
                prefab_link=PrefabLink("inner", "inner-1"),
            )
        )
        prefab = Prefab("outer", (outer,))
        document = prefab.to_dict()
        self.assertEqual(document["schema"], 2)
        self.assertEqual(
            document["roots"][0]["children"][0]["prefab_link"],
            {"name": "inner", "instance": "inner-1"},
        )
        loaded = Prefab.from_dict(document)
        self.assertEqual(
            loaded.roots[0].children[0].prefab_link,
            PrefabLink("inner", "inner-1"),
        )

        legacy = {
            "schema": 1,
            "name": "legacy",
            "roots": [
                {
                    "id": "root",
                    "name": "root",
                    "visible": True,
                    "tags": [],
                    "layer": "default",
                    "transform": {},
                    "mesh": None,
                    "material": None,
                    "components": [],
                    "children": [],
                }
            ],
        }
        migrated = Prefab.from_dict(legacy)
        self.assertIsNone(migrated.roots[0].prefab_link)

    def test_prefab_rejects_root_links_and_self_references(self):
        with self.assertRaises(ValueError):
            Prefab(
                "loop",
                (Node("loop", id="loop", prefab_link=PrefabLink("other", "p")),),
            )
        outer = Node("outer", id="outer")
        outer.add_child(
            Node("child", id="child", prefab_link=PrefabLink("outer", "p"))
        )
        with self.assertRaises(ValueError):
            Prefab("outer", (outer,))
        with self.assertRaises(ValueError):
            Prefab.from_node(outer, name="outer")

    def test_describe_is_json_safe(self):
        prefab = Prefab.from_scene(self._scene(), name="level")
        payload = prefab.describe()
        self.assertEqual(payload["schema"], PREFAB_SCHEMA_VERSION)
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

    def _registered_scene(self):
        scene = self._scene()
        registry = AssetRegistry()
        sword = scene.find_by_id("sword")
        registry.register("mesh.sword", sword.mesh)
        registry.register("material.steel", sword.material)
        return scene, registry

    def test_dict_round_trip_resolves_registered_assets(self):
        scene, registry = self._registered_scene()
        prefab = Prefab.from_node(scene.find_by_id("hero"), name="hero-prefab")
        document = prefab.to_dict(registry)
        self.assertEqual(document["schema"], PREFAB_SCHEMA_VERSION)
        self.assertIsNone(document["roots"][0]["mesh"])
        sword_document = document["roots"][0]["children"][0]
        self.assertEqual(sword_document["mesh"], "mesh.sword")
        self.assertEqual(sword_document["material"], "material.steel")
        json.dumps(document, allow_nan=False)

        loaded = Prefab.from_dict(document, registry, {"Health": Health})
        self.assertEqual(loaded.name, "hero-prefab")
        self.assertEqual(loaded.node_count, 2)
        hero = loaded.roots[0]
        self.assertEqual(hero.id, "hero")
        self.assertEqual(hero.tags, {"player"})
        self.assertEqual(hero.layer, "actors")
        self.assertEqual(hero.require_component(Health), Health(100))
        sword = hero.children[0]
        self.assertIs(sword.mesh, registry.require("mesh.sword").payload)
        self.assertIs(sword.material, registry.require("material.steel").payload)
        target = Scene()
        loaded.instantiate(target, instance="copy")
        self.assertIsNotNone(target.find_by_id("copy:hero"))

    def test_save_and_load_versioned_file(self):
        scene, registry = self._registered_scene()
        hero = scene.find_by_id("hero")
        hero.add_component(Counter(3))
        prefab = Prefab.from_node(hero, name="hero-prefab")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hero.kprefab"
            self.assertEqual(prefab.save(path, registry), path)
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["schema"], PREFAB_SCHEMA_VERSION)
            loaded = Prefab.load(path, registry, {"Health": Health, "Counter": Counter})
            self.assertEqual(loaded.roots[0].require_component(Counter).value, 3)
            self.assertEqual(loaded.roots[0].children[0].mesh, hero.children[0].mesh)
            self.assertEqual([item.name for item in Path(directory).iterdir()], ["hero.kprefab"])

    def test_load_errors_are_explicit(self):
        scene, registry = self._registered_scene()
        document = Prefab.from_node(scene.find_by_id("hero"), name="hero-prefab").to_dict(registry)
        with self.assertRaises(ValueError):
            Prefab.from_dict({**document, "schema": 99}, registry, {"Health": Health})
        without_schema = {key: value for key, value in document.items() if key != "schema"}
        with self.assertRaises(ValueError):
            Prefab.from_dict(without_schema, registry, {"Health": Health})
        with self.assertRaises(ValueError):
            Prefab.from_dict(document, registry)
        with self.assertRaises(ValueError):
            Prefab.from_dict(document, registry, {"Other": Health})
        with self.assertRaises(KeyError):
            Prefab.from_dict(document, AssetRegistry(), {"Health": Health})
        wrong_kind = json.loads(json.dumps(document))
        wrong_kind["roots"][0]["children"][0]["mesh"] = "material.steel"
        with self.assertRaises(ValueError):
            Prefab.from_dict(wrong_kind, registry, {"Health": Health})
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            Prefab.load(Path(directory) / "missing.kprefab", registry)

    def test_unregistered_payloads_cannot_be_serialized(self):
        scene = self._scene()
        prefab = Prefab.from_node(scene.find_by_id("hero"), name="hero-prefab")
        with self.assertRaises(ValueError):
            prefab.to_dict(None)
        with self.assertRaises(ValueError):
            prefab.asset_ids(AssetRegistry())
        registry = AssetRegistry()
        registry.register("mesh.sword", scene.find_by_id("sword").mesh)
        with self.assertRaises(ValueError):
            prefab.to_dict(registry)

    def test_json_primitive_components_round_trip(self):
        node = Node("data", id="data")
        node.add_component([1, 2, 3])
        node.add_component((4, 5))
        node.add_component({"hp": 6})
        prefab = Prefab.from_node(node, name="data")
        document = prefab.to_dict()
        loaded = Prefab.from_dict(document, component_types={"list": list, "tuple": tuple, "dict": dict})
        restored = loaded.roots[0]
        self.assertEqual(restored.require_component(list), [1, 2, 3])
        self.assertEqual(restored.require_component(tuple), (4, 5))
        self.assertEqual(restored.require_component(dict), {"hp": 6})


if __name__ == "__main__":
    unittest.main()
