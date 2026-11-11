"""Tests for scene picking and ray queries."""

import unittest

from keystone.math3d import Vec3
from keystone.physics import Ray
from keystone.picking import SceneHit, hit_report, raycast_scene
from keystone.plugin import describe_game
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import OVERLAY_LAYER, Node, Scene, Transform


def _cube(scene: Scene, name: str, x: float, *, node_id: str | None = None, **kwargs) -> Node:
    node = Node(
        name,
        id=name if node_id is None else node_id,
        transform=Transform(position=Vec3(x, 0.0, 0.0)),
        mesh=cube(1.0),
        **kwargs,
    )
    scene.add(node)
    return node


def _ray(direction: Vec3 | None = None, origin: Vec3 | None = None) -> Ray:
    return Ray(Vec3() if origin is None else origin, Vec3(1.0, 0.0, 0.0) if direction is None else direction)


class RaycastSceneTest(unittest.TestCase):
    def test_returns_the_nearest_visible_mesh(self):
        scene = Scene()
        _cube(scene, "near", 2.0, node_id="near-id")
        _cube(scene, "far", 5.0)
        hit = raycast_scene(scene, _ray())
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.node_id, "near-id")
        self.assertEqual(hit.node_name, "near")
        self.assertAlmostEqual(hit.distance, 1.5)
        self.assertEqual(hit.point, Vec3(1.5, 0.0, 0.0))
        self.assertEqual(hit.box.center, Vec3(2.0, 0.0, 0.0))

    def test_hidden_and_overlay_nodes_do_not_block(self):
        scene = Scene()
        _cube(scene, "hidden", 0.8, visible=False)
        _cube(scene, "viewmodel", 1.0, layer=OVERLAY_LAYER)
        _cube(scene, "solid", 3.0)
        hit = raycast_scene(scene, _ray())
        assert hit is not None
        self.assertEqual(hit.node_id, "solid")
        self.assertAlmostEqual(hit.distance, 2.5)

    def test_layer_filter_and_ignore_lists(self):
        scene = Scene()
        _cube(scene, "wall", 1.5, layer="walls")
        _cube(scene, "prop", 4.0, node_id="prop-id")
        filtered = raycast_scene(scene, _ray(), layer="props")
        self.assertIsNone(filtered)
        by_id = raycast_scene(scene, _ray(), ignore={"prop-id"})
        assert by_id is not None
        self.assertEqual(by_id.node_id, "wall")
        by_name = raycast_scene(scene, _ray(), ignore={"prop"})
        assert by_name is not None
        self.assertEqual(by_name.node_id, "wall")

    def test_max_distance_cuts_the_query(self):
        scene = Scene()
        _cube(scene, "far", 5.0)
        self.assertIsNone(raycast_scene(scene, _ray(), max_distance=2.0))
        hit = raycast_scene(scene, _ray(), max_distance=5.0)
        assert hit is not None
        self.assertAlmostEqual(hit.distance, 4.5)

    def test_a_non_normalized_direction_keeps_world_distance(self):
        scene = Scene()
        _cube(scene, "near", 2.0)
        hit = raycast_scene(scene, Ray(Vec3(), Vec3(2.0, 0.0, 0.0)))
        assert hit is not None
        self.assertAlmostEqual(hit.distance, 1.5)
        self.assertEqual(hit.point, Vec3(1.5, 0.0, 0.0))

    def test_ties_break_on_node_id(self):
        scene = Scene()
        _cube(scene, "b-node", 2.0, node_id="b")
        _cube(scene, "a-node", 2.0, node_id="a", layer="props")
        first = raycast_scene(scene, _ray())
        second = raycast_scene(scene, _ray())
        assert first is not None and second is not None
        self.assertEqual(first, second)
        self.assertEqual(first.node_id, "a")

    def test_empty_scene_and_misses_return_none(self):
        self.assertIsNone(raycast_scene(Scene(), _ray()))
        scene = Scene()
        _cube(scene, "behind", -3.0)
        self.assertIsNone(raycast_scene(scene, _ray()))

    def test_malformed_arguments_are_rejected(self):
        with self.assertRaises(TypeError):
            raycast_scene(object(), _ray())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            raycast_scene(Scene(), {"origin": Vec3()})  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            raycast_scene(Scene(), _ray(), layer=2)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            raycast_scene(Scene(), _ray(), layer=" ")
        with self.assertRaises(TypeError):
            raycast_scene(Scene(), _ray(), ignore=3)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            raycast_scene(Scene(), _ray(), max_distance=-1.0)
        with self.assertRaises(ValueError):
            raycast_scene(Scene(), _ray(), max_distance=float("nan"))


class HitReportTest(unittest.TestCase):
    def test_a_hit_report_is_json_safe(self):
        scene = Scene()
        _cube(scene, "near", 2.0, node_id="near-id")
        report = hit_report(raycast_scene(scene, _ray()))
        self.assertEqual(report["schema"], 1)
        self.assertTrue(report["hit"])
        self.assertEqual(report["node_id"], "near-id")
        self.assertEqual(report["node_name"], "near")
        self.assertEqual(report["distance"], 1.5)
        self.assertEqual(report["point"], [1.5, 0.0, 0.0])

    def test_a_miss_report_has_no_node(self):
        report = hit_report(None)
        self.assertFalse(report["hit"])
        self.assertIsNone(report["node_id"])
        self.assertIsNone(report["distance"])

    def test_report_rejects_a_non_hit(self):
        with self.assertRaises(TypeError):
            hit_report({"node_id": "x"})  # type: ignore[arg-type]

    def test_a_hit_is_immutable(self):
        scene = Scene()
        _cube(scene, "near", 2.0)
        hit = raycast_scene(scene, _ray())
        self.assertIsInstance(hit, SceneHit)
        with self.assertRaises(AttributeError):
            hit.node_id = "other"  # type: ignore[misc]

    def test_describe_advertises_scene_raycast(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["scene_raycast"])


if __name__ == "__main__":
    unittest.main()
