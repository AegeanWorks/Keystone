"""Unit tests for versioned scene snapshots."""

import json
import unittest
from dataclasses import dataclass, replace

from keystone.assets import AssetRegistry
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.primitives import cube, plane
from keystone.scene import (
    DirectionalLight,
    Node,
    PointLight,
    PrefabLink,
    Scene,
    SceneGroup,
    Transform,
)
from keystone.scene_snapshot import (
    SCENE_SNAPSHOT_VERSION,
    scene_from_dict,
    scene_to_dict,
)


@dataclass
class Health:
    value: int


class SceneSnapshotTest(unittest.TestCase):
    def _scene(self):
        scene = Scene()
        scene.background = Vec3(0.1, 0.2, 0.3)
        scene.add(Node("floor", id="floor", mesh=plane(4.0), material=Material(color=Vec3(1, 1, 1)), visible=True))
        parent = Node("parent", id="parent")
        child = Node("child", id="child", visible=False)
        child.add_tag("marker")
        child.layer = "props"
        parent.add_child(child)
        scene.add(parent)
        scene.camera.position = Vec3(1.0, 2.0, 3.0)
        scene.camera.yaw = 0.5
        scene.camera.pitch = -0.25
        return scene

    def test_round_trip_preserves_structure_and_transforms(self):
        scene = self._scene()
        child = next(node for node in scene.traverse() if node.id == "child")
        child.transform = replace(child.transform, position=Vec3(1.5, 0.0, -2.0))
        document = scene_to_dict(scene)
        self.assertEqual(document["schema"], SCENE_SNAPSHOT_VERSION)
        restored = scene_from_dict(document)
        self.assertEqual([node.id for node in restored.traverse() if node is not restored.root], ["floor", "parent", "child"])
        restored_child = next(node for node in restored.traverse() if node.id == "child")
        self.assertEqual(restored_child.transform.position, Vec3(1.5, 0.0, -2.0))
        self.assertFalse(restored_child.visible)
        self.assertEqual(restored_child.tags, {"marker"})
        self.assertEqual(restored_child.layer, "props")
        self.assertEqual(restored.camera.position, Vec3(1.0, 2.0, 3.0))
        self.assertEqual(restored.camera.yaw, 0.5)
        self.assertEqual(restored.camera.pitch, -0.25)
        self.assertEqual(restored.background, Vec3(0.1, 0.2, 0.3))
        json.dumps(document)

    def test_prefab_links_round_trip_and_older_snapshots_default_to_none(self):
        scene = Scene()
        scene.add(
            Node(
                "hero",
                id="hero",
                prefab_link=PrefabLink("hero-template", "copy"),
            )
        )
        document = scene_to_dict(scene)
        self.assertEqual(
            document["nodes"][0]["prefab_link"],
            {"name": "hero-template", "instance": "copy"},
        )
        restored = scene_from_dict(document)
        self.assertEqual(
            restored.find_by_id("hero").prefab_link,
            PrefabLink("hero-template", "copy"),
        )
        document["schema"] = 2
        document["nodes"][0].pop("prefab_link")
        self.assertIsNone(scene_from_dict(document).find_by_id("hero").prefab_link)

    def test_scene_groups_round_trip_and_older_snapshots_default_to_none(self):
        scene = Scene()
        group = Node("level", id="level", scene_group=SceneGroup("level"))
        group.add_child(Node("child", id="child"))
        scene.add(group)
        document = scene_to_dict(scene)
        self.assertEqual(document["nodes"][0]["scene_group"], {"name": "level"})
        restored = scene_from_dict(document)
        self.assertEqual(
            restored.find_by_id("level").scene_group, SceneGroup("level")
        )
        document["schema"] = 3
        document["nodes"][0].pop("scene_group")
        self.assertIsNone(
            scene_from_dict(document).find_by_id("level").scene_group
        )

    def test_round_trip_preserves_typed_components(self):
        scene = self._scene()
        child = next(node for node in scene.traverse() if node.id == "child")
        child.add_component(Health(4))
        document = scene_to_dict(scene)
        entry = next(node for node in document["nodes"] if node["id"] == "child")
        self.assertEqual(entry["components"], [{"type": "Health", "data": {"value": 4}}])
        json.dumps(document, allow_nan=False)
        with self.assertRaises(ValueError):
            scene_from_dict(document)
        restored = scene_from_dict(document, component_types={"Health": Health})
        restored_child = next(node for node in restored.traverse() if node.id == "child")
        self.assertEqual(restored_child.require_component(Health), Health(4))

    def test_components_require_a_type_map_and_supported_codec(self):
        class Unsupported:
            pass

        node = Node("data", id="data")
        node.add_component(Health(1))
        scene = Scene()
        scene.add(node)
        document = scene_to_dict(scene)
        with self.assertRaises(ValueError):
            scene_from_dict(document)
        with self.assertRaises(ValueError):
            scene_from_dict(document, component_types={"Other": Health})
        node.add_component(Unsupported())
        with self.assertRaises(TypeError):
            scene_to_dict(scene)

    def test_round_trip_preserves_camera_lens_and_environment(self):
        scene = self._scene()
        scene.camera.near = 0.25
        scene.camera.far = 250.0
        scene.ambient = Vec3(0.2, 0.3, 0.4)
        scene.sky = Vec3(0.5, 0.6, 0.7)
        scene.fog_density = 0.045
        scene.light = DirectionalLight(
            direction=Vec3(0.0, -1.0, 0.0), color=Vec3(0.9, 0.8, 0.7), intensity=2.5
        )
        scene.point_light = PointLight(
            position=Vec3(1.0, 2.0, 3.0), color=Vec3(0.4, 0.5, 0.6), intensity=1.5, radius=9.0
        )
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertEqual(restored.camera.near, 0.25)
        self.assertEqual(restored.camera.far, 250.0)
        self.assertEqual(restored.ambient, Vec3(0.2, 0.3, 0.4))
        self.assertEqual(restored.sky, Vec3(0.5, 0.6, 0.7))
        self.assertEqual(restored.fog_density, 0.045)
        self.assertEqual(restored.light, scene.light)
        self.assertEqual(restored.point_light, scene.point_light)

    def test_older_schema_one_documents_keep_engine_defaults(self):
        scene = self._scene()
        document = scene_to_dict(scene)
        del document["environment"]
        del document["camera"]["near"]
        del document["camera"]["far"]
        restored = scene_from_dict(document)
        self.assertIsNone(restored.point_light)
        self.assertEqual(restored.camera.near, Scene().camera.near)
        self.assertEqual(restored.camera.far, Scene().camera.far)

    def test_rejects_duplicate_node_ids(self):
        document = {
            "schema": SCENE_SNAPSHOT_VERSION,
            "nodes": [{"id": "dup"}, {"id": "dup"}],
        }
        with self.assertRaises(ValueError):
            scene_from_dict(document)

    def test_rejects_unknown_parent_reference(self):
        document = {
            "schema": SCENE_SNAPSHOT_VERSION,
            "nodes": [{"id": "child", "parent_id": "absent"}],
        }
        with self.assertRaises(ValueError):
            scene_from_dict(document)

    def test_rejects_asset_kind_mismatch(self):
        registry = AssetRegistry()
        registry.register("material.only", Material(color=Vec3(1.0, 0.0, 0.0)))
        document = {
            "schema": SCENE_SNAPSHOT_VERSION,
            "nodes": [{"id": "node", "mesh": "material.only"}],
        }
        with self.assertRaises(ValueError):
            scene_from_dict(document, registry=registry)

    def test_rejects_non_string_node_ids_and_asset_references(self):
        with self.assertRaises(TypeError):
            scene_from_dict({"schema": SCENE_SNAPSHOT_VERSION, "nodes": [{"id": 5}]})
        with self.assertRaises(TypeError):
            scene_from_dict(
                {
                    "schema": SCENE_SNAPSHOT_VERSION,
                    "nodes": [{"id": "node", "mesh": 5}],
                }
            )
        with self.assertRaises(TypeError):
            scene_from_dict(
                {
                    "schema": SCENE_SNAPSHOT_VERSION,
                    "nodes": [{"id": "node", "name": 5}],
                }
            )

    def test_rejects_non_mapping_camera_and_transform(self):
        with self.assertRaises(TypeError):
            scene_from_dict({"schema": SCENE_SNAPSHOT_VERSION, "camera": [], "nodes": []})
        with self.assertRaises(TypeError):
            scene_from_dict(
                {
                    "schema": SCENE_SNAPSHOT_VERSION,
                    "nodes": [{"id": "node", "transform": []}],
                }
            )

    def test_rejects_unknown_version(self):
        document = scene_to_dict(self._scene())
        document["schema"] = 99
        with self.assertRaises(ValueError):
            scene_from_dict(document)

    def test_asset_registry_round_trip_attaches_mesh_and_material(self):
        scene = Scene()
        mesh = cube(1.2)
        material = Material(color=Vec3(0.2, 0.4, 0.6))
        registry = AssetRegistry()
        registry.register("mesh.cube", mesh)
        registry.register("material.cube", material)
        scene.add(Node("cube", id="cube", mesh=mesh, material=material))
        document = scene_to_dict(scene, registry=registry)
        cube_entry = next(entry for entry in document["nodes"] if entry["id"] == "cube")
        self.assertEqual(cube_entry["mesh"], "mesh.cube")
        self.assertEqual(cube_entry["material"], "material.cube")
        restored = scene_from_dict(document, registry=registry)
        restored_cube = next(node for node in restored.traverse() if node.id == "cube")
        self.assertIs(restored_cube.mesh, mesh)
        self.assertIs(restored_cube.material, material)

    def test_rejects_non_finite_transform_on_save(self):
        with self.assertRaises(ValueError):
            Transform(position=Vec3(float("nan"), 0.0, 0.0))
        scene = Scene()
        node = scene.add(Node("n", id="n"))
        node.transform = None  # type: ignore[assignment]
        with self.assertRaises(TypeError):
            scene_to_dict(scene)

    def test_rejects_zero_quaternion_on_load(self):
        document = {"schema": 1, "nodes": [{"id": "n", "transform": {"rotation": [0, 0, 0, 0]}}]}
        with self.assertRaises(ValueError):
            scene_from_dict(document)

    def test_preserves_root_transform_visibility_and_next_id(self):
        scene = Scene()
        scene.root.transform = Transform(position=Vec3(5, 0, 0))
        scene.root.visible = False
        scene.add(Node("removed"))
        removed = next(node for node in scene.traverse() if node.name == "removed")
        scene.root.remove_child(removed)
        scene.add(Node("child", id="child"))
        restored = scene_from_dict(scene_to_dict(scene))
        restored_child = restored.find_by_id("child")
        self.assertEqual(restored_child.world_matrix().transform_point(Vec3()), Vec3(5, 0, 0))
        self.assertFalse(restored_child.world_visible())
        self.assertEqual(restored.add(Node("next")).id, "node-2")

    def test_clamps_camera_pitch_and_rejects_bad_framing(self):
        restored = scene_from_dict({"schema": 1, "nodes": [], "camera": {"pitch": 3.0}})
        self.assertLessEqual(abs(restored.camera.pitch), 1.5533430342759533 + 1e-12)
        with self.assertRaises(ValueError):
            scene_from_dict({"schema": 1, "nodes": [], "camera": {"near": 0.0}})
        with self.assertRaises(ValueError):
            scene_from_dict({"schema": 1, "nodes": [], "camera": {"fov_y": float("nan")}})

    def test_strict_snapshot_scalars(self):
        with self.assertRaises(TypeError):
            scene_from_dict({"schema": 1, "nodes": [{"id": "n", "visible": "false"}]})
        with self.assertRaises(ValueError):
            scene_from_dict({"schema": True, "nodes": []})
        with self.assertRaises(ValueError):
            scene_from_dict({"schema": 1.0, "nodes": []})
        with self.assertRaises(ValueError):
            scene_from_dict({"schema": SCENE_SNAPSHOT_VERSION})


if __name__ == "__main__":
    unittest.main()
