"""Tests for scene overlap queries."""

import unittest

from keystone.math3d import Vec3
from keystone.physics import AABB, Sphere
from keystone.picking import SceneOverlap, overlap_report, overlap_scene
from keystone.plugin import describe_game
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import OVERLAY_LAYER, Node, Scene, Transform


def _cube(scene: Scene, name: str, x: float, z: float = 0.0, **kwargs) -> Node:
    node = Node(
        name,
        id=name,
        transform=Transform(position=Vec3(x, 0.0, z)),
        mesh=cube(1.0),
        **kwargs,
    )
    scene.add(node)
    return node


class OverlapSceneTest(unittest.TestCase):
    def test_a_sphere_returns_every_overlapping_visible_mesh(self):
        scene = Scene()
        _cube(scene, "near", 1.0)
        _cube(scene, "edge", 1.9)
        _cube(scene, "far", 6.0)
        hits = overlap_scene(scene, Sphere(Vec3(0.0, 0.0, 0.0), 1.5))
        self.assertEqual([hit.node_id for hit in hits], ["near", "edge"])

    def test_a_box_returns_overlapping_meshes(self):
        scene = Scene()
        _cube(scene, "inside", 0.0)
        _cube(scene, "touching", 1.5)
        _cube(scene, "outside", 4.0)
        hits = overlap_scene(scene, AABB(Vec3(0.0, 0.0, 0.0), Vec3(1.0, 1.0, 1.0)))
        self.assertEqual([hit.node_id for hit in hits], ["inside", "touching"])

    def test_hidden_and_overlay_nodes_never_overlap(self):
        scene = Scene()
        _cube(scene, "hidden", 0.0, visible=False)
        _cube(scene, "viewmodel", 0.2, layer=OVERLAY_LAYER)
        _cube(scene, "solid", 0.4)
        hits = overlap_scene(scene, Sphere(Vec3(0.0, 0.0, 0.0), 2.0))
        self.assertEqual([hit.node_id for hit in hits], ["solid"])

    def test_layer_filter_and_ignore_lists(self):
        scene = Scene()
        _cube(scene, "wall", 1.0, layer="walls")
        _cube(scene, "prop", 0.2)
        self.assertEqual([hit.node_id for hit in overlap_scene(scene, Sphere(Vec3(), 2.0), layer="props")], [])
        hits = overlap_scene(scene, Sphere(Vec3(), 2.0), ignore={"prop"})
        self.assertEqual([hit.node_id for hit in hits], ["wall"])
        hits = overlap_scene(scene, Sphere(Vec3(), 2.0), ignore={"wall"})
        self.assertEqual([hit.node_id for hit in hits], ["prop"])

    def test_results_are_sorted_by_distance_then_id(self):
        scene = Scene()
        _cube(scene, "b", 1.0)
        _cube(scene, "a", 1.0)
        _cube(scene, "close", 0.0)
        hits = overlap_scene(scene, Sphere(Vec3(0.0, 0.0, 0.5), 3.0))
        self.assertEqual([hit.node_id for hit in hits], ["close", "a", "b"])
        self.assertEqual([hit.distance for hit in hits], sorted(hit.distance for hit in hits))

    def test_misses_return_no_hits(self):
        scene = Scene()
        _cube(scene, "far", 20.0)
        self.assertEqual(overlap_scene(scene, Sphere(Vec3(), 1.0)), ())
        self.assertEqual(overlap_scene(Scene(), AABB(Vec3(), Vec3(1.0, 1.0, 1.0))), ())

    def test_malformed_arguments_are_rejected(self):
        with self.assertRaises(TypeError):
            overlap_scene(object(), Sphere(Vec3(), 1.0))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            overlap_scene(Scene(), {"center": Vec3()})  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            overlap_scene(Scene(), Sphere(Vec3(), 1.0), layer=2)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            overlap_scene(Scene(), Sphere(Vec3(), 1.0), layer=" ")
        with self.assertRaises(TypeError):
            overlap_scene(Scene(), Sphere(Vec3(), 1.0), ignore=3)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            overlap_scene(Scene(), Sphere(Vec3(), 1.0), ignore="prop")  # type: ignore[arg-type]

    def test_a_hit_is_immutable(self):
        scene = Scene()
        _cube(scene, "near", 0.0)
        hit = overlap_scene(scene, Sphere(Vec3(), 2.0))[0]
        self.assertIsInstance(hit, SceneOverlap)
        with self.assertRaises(AttributeError):
            hit.node_id = "other"  # type: ignore[misc]


class OverlapReportTest(unittest.TestCase):
    def test_report_is_json_safe_and_sorted(self):
        scene = Scene()
        _cube(scene, "b", 1.0)
        _cube(scene, "a", 0.0)
        report = overlap_report(overlap_scene(scene, Sphere(Vec3(), 3.0)))
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["count"], 2)
        self.assertEqual([entry["node_id"] for entry in report["nodes"]], ["a", "b"])
        self.assertEqual(report["nodes"][0]["distance"], 0.0)

    def test_empty_report_counts_zero(self):
        report = overlap_report(())
        self.assertEqual(report["nodes"], [])
        self.assertEqual(report["count"], 0)

    def test_report_rejects_a_non_sequence(self):
        with self.assertRaises(TypeError):
            overlap_report({"nodes": []})  # type: ignore[arg-type]

    def test_describe_advertises_scene_overlap(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["scene_overlap"])


if __name__ == "__main__":
    unittest.main()
