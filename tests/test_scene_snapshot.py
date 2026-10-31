"""Unit tests for versioned scene snapshots."""

import json
import unittest
from dataclasses import replace

from keystone.assets import AssetRegistry
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.primitives import cube, plane
from keystone.scene import Node, Scene
from keystone.scene_snapshot import (
    SCENE_SNAPSHOT_VERSION,
    scene_from_dict,
    scene_to_dict,
)


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
        json.dumps(document)

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


if __name__ == "__main__":
    unittest.main()
