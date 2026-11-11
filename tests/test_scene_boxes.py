"""Tests for deriving collision boxes from scene geometry."""

import unittest

from keystone.math3d import Vec3
from keystone.nav_authoring import grid_from_boxes, scene_boxes
from keystone.pathfinding import find_path
from keystone.primitives import cube
from keystone.scene import OVERLAY_LAYER, Node, Scene, Transform


def _wall(name: str, x: float, z: float, *, size: float = 1.0, **node_kwargs) -> Node:
    node_kwargs.setdefault(
        "transform", Transform(position=Vec3(x, 0.5, z), scale=Vec3(size, 1.0, 1.0))
    )
    return Node(name, id=name, mesh=cube(1.0), **node_kwargs)


class SceneBoxesTest(unittest.TestCase):
    def test_each_visible_mesh_becomes_one_world_aabb(self):
        scene = Scene()
        scene.add(_wall("wall-a", 2.0, 0.0))
        scene.add(_wall("wall-b", 0.0, 3.0, size=2.0))
        boxes = scene_boxes(scene)
        self.assertEqual(len(boxes), 2)
        first = boxes[0]
        self.assertEqual(first.center, Vec3(2.0, 0.5, 0.0))
        self.assertEqual(first.half_extents, Vec3(0.5, 0.5, 0.5))
        self.assertEqual(boxes[1].half_extents, Vec3(1.0, 0.5, 0.5))

    def test_hidden_nodes_and_overlay_nodes_are_skipped(self):
        scene = Scene()
        scene.add(_wall("solid", 0.0, 0.0))
        scene.add(_wall("hidden", 1.0, 0.0, visible=False))
        scene.add(_wall("viewmodel", 2.0, 0.0, layer=OVERLAY_LAYER))
        self.assertEqual([box.center.x for box in scene_boxes(scene)], [0.0])

    def test_a_layer_filter_keeps_only_that_layer(self):
        scene = Scene()
        scene.add(_wall("floor", 0.0, 0.0, layer="floor"))
        scene.add(_wall("wall", 2.0, 0.0, layer="walls"))
        walls = scene_boxes(scene, layer="walls")
        self.assertEqual(len(walls), 1)
        self.assertEqual(walls[0].center.x, 2.0)

    def test_a_hierarchy_translates_the_box(self):
        scene = Scene()
        parent = Node("hall", id="hall", transform=Transform(position=Vec3(10.0, 0.0, 0.0)))
        scene.add(parent)
        _wall("wall", 0.0, 0.0, parent=parent, transform=Transform(position=Vec3(0.0, 0.5, 0.0)))
        box = scene_boxes(scene)[0]
        self.assertEqual(box.center, Vec3(10.0, 0.5, 0.0))

    def test_nodes_without_meshes_are_skipped(self):
        scene = Scene()
        scene.add(Node("empty", id="empty"))
        self.assertEqual(scene_boxes(scene), ())

    def test_the_order_follows_scene_traversal(self):
        scene = Scene()
        for index in range(3):
            scene.add(_wall(f"wall-{index}", float(index), 0.0))
        self.assertEqual([box.center.x for box in scene_boxes(scene)], [0.0, 1.0, 2.0])

    def test_malformed_arguments_are_rejected(self):
        with self.assertRaises(TypeError):
            scene_boxes(object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            scene_boxes(Scene(), layer=3)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            scene_boxes(Scene(), layer="  ")


class SceneToRouteTest(unittest.TestCase):
    def test_a_wall_in_the_scene_reaches_the_router(self):
        scene = Scene()
        scene.add(_wall("pillar", 2.5, 2.5))
        grid = grid_from_boxes(5, 5, scene_boxes(scene), cell_size=1.0)
        self.assertEqual(grid.blocked, frozenset({(2, 2)}))
        result = find_path(grid, (0, 2), (4, 2))
        self.assertTrue(result.found)
        self.assertTrue(all(cell != (2, 2) for cell in result.path))
        self.assertTrue((2, 1) in result.path or (2, 3) in result.path)


if __name__ == "__main__":
    unittest.main()
