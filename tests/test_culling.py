"""Tests for deterministic CPU view-frustum culling (color pass only)."""

import unittest

from keystone.analysis import REPORT_SCHEMA, analyze_frame, compare_reports
from keystone.culling import (
    aabb_visible,
    cull_scene,
    culling_enabled,
    extract_planes,
    node_visible,
    world_bounds,
)
from keystone.geometry import MeshData
from keystone.math3d import Mat4, Vec3
from keystone.plugin import describe_game
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import CullingSettings, Node, Scene, Transform
from keystone.scene_snapshot import scene_from_dict, scene_to_dict

IDENTITY_16 = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)

UNIT_BOX = (
    (1.0, 0.0, 0.0, 1.0),
    (-1.0, 0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0, 1.0),
    (0.0, -1.0, 0.0, 1.0),
    (0.0, 0.0, 1.0, 1.0),
    (0.0, 0.0, -1.0, 1.0),
)


def _scene_with_cubes() -> Scene:
    scene = Scene()
    scene.camera.position = Vec3(0.0, 0.0, 0.0)
    mesh = cube(1.0)
    scene.add(Node("front", transform=Transform(position=Vec3(0.0, 0.0, -5.0)), mesh=mesh))
    scene.add(Node("behind", transform=Transform(position=Vec3(0.0, 0.0, 5.0)), mesh=mesh))
    scene.add(Node("far-left", transform=Transform(position=Vec3(-30.0, 0.0, -5.0)), mesh=mesh))
    return scene


def _skinned_quad() -> MeshData:
    positions = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0))
    normals = ((0.0, 0.0, 1.0),) * 4
    return MeshData(
        positions=positions,
        normals=normals,
        indices=(0, 1, 2, 0, 2, 3),
        joints=((0,),) * 4,
        weights=((1.0,),) * 4,
        skin_joints=("j0",),
        skin_inverse_bind=(IDENTITY_16,),
    )


class CullingMathTest(unittest.TestCase):
    def test_planes_are_deterministic(self):
        scene = Scene()
        first = extract_planes(scene.camera.view_projection(16 / 9))
        second = extract_planes(scene.camera.view_projection(16 / 9))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 6)

    def test_degenerate_frustum_raises(self):
        with self.assertRaises(ValueError):
            extract_planes(Mat4((0.0,) * 16))

    def test_aabb_touching_plane_is_visible(self):
        self.assertTrue(
            aabb_visible(Vec3(1.0, -0.5, -0.5), Vec3(2.0, 0.5, 0.5), UNIT_BOX),
        )
        self.assertTrue(
            aabb_visible(Vec3(-0.5, -0.5, -0.5), Vec3(0.5, 0.5, 0.5), UNIT_BOX),
        )
        self.assertFalse(
            aabb_visible(Vec3(1.5, -0.5, -0.5), Vec3(2.5, 0.5, 0.5), UNIT_BOX),
        )

    def test_world_bounds_follow_translation(self):
        mesh = cube(2.0)
        low, high = world_bounds(mesh, Mat4.translation(10.0, 0.0, 0.0))
        self.assertAlmostEqual(low.x, 9.0)
        self.assertAlmostEqual(high.x, 11.0)

    def test_skinned_nodes_are_always_visible(self):
        scene = Scene()
        node = Node(
            "rig",
            transform=Transform(position=Vec3(0.0, 0.0, 50.0)),
            mesh=_skinned_quad(),
        )
        scene.add(node)
        planes = extract_planes(scene.camera.view_projection(16 / 9))
        self.assertTrue(node_visible(node, planes))


class CullingSceneTest(unittest.TestCase):
    def test_front_visible_behind_and_offside_culled(self):
        scene = _scene_with_cubes()
        planes = extract_planes(scene.camera.view_projection(16 / 9))
        by_name = {node.name: node for node in scene.traverse() if node.name}
        self.assertTrue(node_visible(by_name["front"], planes))
        self.assertFalse(node_visible(by_name["behind"], planes))
        self.assertFalse(node_visible(by_name["far-left"], planes))

    def test_cull_scene_keeps_front_only(self):
        scene = _scene_with_cubes()
        visible = cull_scene(scene, 960, 540)
        names = {node.name for node in scene.traverse() if id(node) in visible and node.name}
        self.assertIn("front", names)
        self.assertNotIn("behind", names)
        self.assertNotIn("far-left", names)

    def test_disabled_culling_returns_everything(self):
        scene = _scene_with_cubes()
        scene.culling = CullingSettings(enabled=False)
        self.assertFalse(culling_enabled(scene))
        visible = cull_scene(scene, 960, 540)
        names = {node.name for node in scene.traverse() if id(node) in visible and node.name}
        self.assertIn("behind", names)
        self.assertIn("far-left", names)

    def test_default_enabled(self):
        self.assertTrue(culling_enabled(Scene()))

    def test_cull_scene_rejects_bad_size(self):
        with self.assertRaises(ValueError):
            cull_scene(Scene(), 0, 48)


class CullingGroupingAgreementTest(unittest.TestCase):
    def test_group_instances_planes_match_cull_scene(self):
        from keystone.gpu.instancing import group_instances

        scene = _scene_with_cubes()
        planes = extract_planes(scene.camera.view_projection(16 / 9))
        grouped = {id(node) for group in group_instances(scene, planes) for node in group["nodes"]}
        expected = cull_scene(scene, 960, 540)
        mesh_expected = {
            node_id
            for node_id in expected
            for node in scene.traverse()
            if id(node) == node_id and isinstance(node.mesh, MeshData) and node.world_visible()
        }
        self.assertEqual(grouped, mesh_expected)
        self.assertNotIn("behind", {node.name for group in group_instances(scene, planes) for node in group["nodes"]})

    def test_group_instances_without_planes_is_legacy(self):
        from keystone.gpu.instancing import group_instances

        scene = _scene_with_cubes()
        names = {node.name for group in group_instances(scene) for node in group["nodes"]}
        self.assertIn("behind", names)
        self.assertIn("far-left", names)


class CullingContractsTest(unittest.TestCase):
    def test_describe_reports_culling(self):
        self.assertTrue(describe_game(CubeDemo())["capabilities"]["culling"])

    def test_public_api_exports_culling_helpers(self):
        import keystone
        import keystone.culling

        for name in keystone.culling.__all__:
            self.assertIn(name, keystone.__all__)
            self.assertIs(getattr(keystone, name), getattr(keystone.culling, name))

    def test_report_includes_culling_metadata_and_hash(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(report["schema"], REPORT_SCHEMA["version"])
        self.assertEqual(report["scene"]["culling"], {"enabled": True})
        scene.culling = CullingSettings(enabled=False)
        off = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(off["scene"]["culling"], {"enabled": False})
        self.assertNotEqual(report["hash"], off["hash"])

    def test_compare_reports_diffs_culling(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((0, 0, 0, 255)) * 4
        on = analyze_frame(scene, pixels, 2, 2)
        scene.culling = CullingSettings(enabled=False)
        off = analyze_frame(scene, pixels, 2, 2)
        diff = compare_reports(on, off)
        self.assertFalse(diff["same_report"])
        self.assertFalse(diff["same_culling"])
        same = compare_reports(on, analyze_frame(CubeDemo().build_scene(), pixels, 2, 2))
        self.assertTrue(same["same_culling"])

    def test_compare_accepts_legacy_without_culling(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        legacy = analyze_frame(CubeDemo().build_scene(), bytes((0, 0, 0, 255)) * 4, 2, 2)
        legacy["scene"].pop("culling", None)
        diff = compare_reports(legacy, report)
        self.assertTrue(diff["same_culling"])

    def test_compare_accepts_schema_10_baseline(self):
        scene = CubeDemo().build_scene()
        current = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        baseline = analyze_frame(CubeDemo().build_scene(), bytes((0, 0, 0, 255)) * 4, 2, 2)
        baseline["schema"] = 10
        baseline["scene"].pop("culling", None)
        diff = compare_reports(baseline, current)
        self.assertTrue(diff["same_culling"])

    def test_snapshot_round_trips_culling_flag(self):
        scene = CubeDemo().build_scene()
        scene.culling = CullingSettings(enabled=False)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertFalse(restored.culling.enabled)
        legacy = scene_to_dict(CubeDemo().build_scene())
        legacy["environment"].pop("culling", None)
        self.assertTrue(scene_from_dict(legacy).culling.enabled)


if __name__ == "__main__":
    unittest.main()
