"""Tests for camera-relative overlay drawing and metric separation."""

import unittest

from keystone.batch import merge_batches, plan_batches
from keystone.camera import PerspectiveCamera
from keystone.camera_rig import CameraRig
from keystone.geometry import Material
from keystone.gpu.context import GLContext
from keystone.gpu.instancing import group_instances, plan_instanced
from keystone.gpu.renderer import Renderer
from keystone.math3d import Vec3
from keystone.primitives import cube
from keystone.scene import OVERLAY_LAYER, Node, Scene, Transform


def _metric_scene() -> Scene:
    """One world cube and one overlay cube with equal payloads."""
    scene = Scene()
    scene.add(Node("wall", id="wall", mesh=cube(1.0), material=Material()))
    overlay = Node(
        "viewmodel",
        id="viewmodel",
        mesh=cube(1.0),
        material=Material(),
        layer=OVERLAY_LAYER,
    )
    scene.add(overlay)
    return scene


def _render_scene() -> tuple[Scene, CameraRig, Node]:
    """A red wall at -3 and a rig holding a blue part at -1."""
    scene = Scene()
    scene.background = Vec3(0.02, 0.02, 0.03)
    scene.camera = PerspectiveCamera(position=Vec3(0.0, 0.0, 0.0))
    scene.add(
        Node(
            "wall",
            transform=Transform(position=Vec3(0.0, 0.0, -3.0)),
            mesh=cube(2.0),
            material=Material(color=Vec3(1.0, 0.05, 0.05), specular=0.0),
        )
    )
    rig = CameraRig(scene.camera)
    part = rig.attach(
        "viewmodel",
        position=Vec3(0.0, 0.0, -1.0),
        mesh=cube(0.5),
        material=Material(color=Vec3(0.05, 0.05, 1.0), specular=0.0),
    )
    return scene, rig, part


def _centre(pixels: bytes, width: int, height: int) -> tuple[int, int, int, int]:
    index = ((height // 2) * width + width // 2) * 4
    return tuple(pixels[index : index + 4])  # type: ignore[return-value]


class OverlayMetricTest(unittest.TestCase):
    def test_plans_exclude_overlay_nodes(self):
        scene = _metric_scene()
        plan = plan_batches(scene)
        self.assertEqual(plan["node_draws"], 1)
        self.assertEqual(plan["groups"], 1)
        self.assertEqual(plan["overlay_calls"], 1)
        self.assertEqual(plan["overlay_triangles"], 12)
        merged = merge_batches(scene)
        self.assertEqual(merged["merged_calls"], 1)
        self.assertEqual(merged["saved_calls"], 0)
        self.assertEqual(merged["overlay_calls"], 1)
        instanced = plan_instanced(scene)
        self.assertEqual(instanced["draw_calls"], 1)
        self.assertEqual(instanced["overlay_calls"], 1)

    def test_group_instances_filters_by_layer(self):
        scene = _metric_scene()
        world = group_instances(scene, exclude_layer=OVERLAY_LAYER)
        overlay = group_instances(scene, layer=OVERLAY_LAYER)
        self.assertEqual(len(world), 1)
        self.assertEqual(world[0]["node_keys"], ["wall"])
        self.assertEqual(len(overlay), 1)
        self.assertEqual(overlay[0]["node_keys"], ["viewmodel"])
        self.assertEqual(len(group_instances(scene)), 1)
        self.assertEqual(group_instances(scene)[0]["node_keys"], ["viewmodel", "wall"])


class OverlayRenderTest(unittest.TestCase):
    def setUp(self):
        self.context = GLContext(64, 48, visible=False)
        self.addCleanup(self.context.close)
        self.renderer = Renderer(64, 48)
        self.addCleanup(self.renderer.release)

    def test_overlay_draws_after_a_depth_clear(self):
        """The wall is closer to the camera's line of sight than nothing else."""
        scene, rig, _part = _render_scene()
        self.renderer.render(scene)
        red, _green, blue, _alpha = _centre(self.renderer.read_pixels(), 64, 48)
        self.assertGreater(red, blue)
        rig.attach_to(scene)
        rig.sync()
        stats = self.renderer.render(scene)
        red, _green, blue, _alpha = _centre(self.renderer.read_pixels(), 64, 48)
        self.assertGreater(blue, red, "the overlay part must cover the wall")
        self.assertEqual(stats["overlay_calls"], 1)
        self.assertEqual(stats["overlay_nodes"], 1)
        self.assertEqual(stats["overlay_triangles"], 12)
        self.assertEqual(stats["draw_calls"], 1)

    def test_hidden_overlay_leaves_the_world_frame(self):
        scene, rig, part = _render_scene()
        rig.attach_to(scene)
        part.visible = False
        rig.sync()
        stats = self.renderer.render(scene)
        red, _green, blue, _alpha = _centre(self.renderer.read_pixels(), 64, 48)
        self.assertGreater(red, blue)
        self.assertEqual(stats["overlay_calls"], 0)
        self.assertEqual(stats["overlay_nodes"], 0)

    def test_overlay_does_not_cast_a_shadow(self):
        scene, rig, _part = _render_scene()
        rig.attach_to(scene)
        rig.sync()
        stats = self.renderer.render(scene)
        self.assertEqual(stats["shadows_enabled"], 1)
        self.assertEqual(stats["shadow_calls"], 1)


if __name__ == "__main__":
    unittest.main()
