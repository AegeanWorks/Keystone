"""Headless OpenGL integration tests for the Keystone renderer."""

import tempfile
import unittest
from pathlib import Path

from keystone.geometry import Material
from keystone.gpu.context import GLContext, require_opengl_33
from keystone.gpu.renderer import Renderer
from keystone.gpu.shader import ShaderProgram
from keystone.math3d import Vec3
from keystone.primitives import cube, plane
from keystone.scene import DirectionalLight, Node, PointLight, Scene
from keystone.texture import TextureData


def build_scene() -> Scene:
    scene = Scene()
    scene.background = Vec3(0.02, 0.02, 0.03)
    scene.camera.position = Vec3(0.0, 0.0, 4.0)
    scene.add(
        Node(
            "cube",
            mesh=cube(1.5),
            material=Material(color=Vec3(1.0, 0.45, 0.15), specular=0.5),
        )
    )
    return scene


class RendererIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.context = GLContext(64, 48, visible=False)
        self.addCleanup(self.context.close)
        self.renderer = Renderer(64, 48)
        self.addCleanup(self.renderer.release)

    def test_zero_scale_node_does_not_abort_the_render(self):
        from keystone.scene import Transform

        scene = build_scene()
        scene.add(
            Node(
                "collapsed",
                transform=Transform(scale=Vec3(0.0, 0.0, 0.0)),
                mesh=cube(1.0),
                material=Material(color=Vec3(1.0, 0.0, 0.0)),
            )
        )
        stats = self.renderer.render(scene)
        self.assertGreater(stats["draw_calls"], 0)

    def test_render_fills_the_center_with_a_lit_surface(self):
        self.renderer.render(build_scene())
        pixels = self.renderer.read_pixels()
        self.assertEqual(len(pixels), 64 * 48 * 4)
        center = 24 * 64 * 4 + 32 * 4
        red, _green, blue, alpha = pixels[center : center + 4]
        self.assertEqual(alpha, 255)
        self.assertGreater(red, 60)
        self.assertGreater(red, blue)

    def test_empty_scene_draws_a_vertical_sky_gradient(self):
        scene = Scene()
        scene.sky = Vec3(0.7, 0.1, 0.1)
        scene.background = Vec3(0.05, 0.1, 0.3)
        self.renderer.render(scene)
        pixels = self.renderer.read_pixels()
        bottom = pixels[0:4]
        top = pixels[(47 * 64) * 4 : (47 * 64) * 4 + 4]
        self.assertGreater(top[0], bottom[0])
        self.assertGreater(bottom[2], top[2])

    def test_point_light_lights_a_surface_when_the_sun_is_off(self):
        scene = Scene()
        scene.ambient = Vec3(0.0, 0.0, 0.0)
        scene.light = DirectionalLight(intensity=0.0)
        scene.point_light = PointLight(
            position=Vec3(0.0, 0.0, 3.0),
            color=Vec3(1.0, 0.0, 0.0),
            intensity=2.0,
            radius=10.0,
        )
        scene.camera.position = Vec3(0.0, 0.0, 4.0)
        scene.add(Node("cube", mesh=cube(1.5), material=Material(color=Vec3(1.0, 1.0, 1.0))))
        self.renderer.render(scene)
        pixels = self.renderer.read_pixels()
        center = 24 * 64 * 4 + 32 * 4
        red, _green, blue, _alpha = pixels[center : center + 4]
        self.assertGreater(red, 80)
        self.assertGreater(red, blue)

    def test_textured_plane_samples_the_texture(self):
        scene = Scene()
        scene.ambient = Vec3(1.0, 1.0, 1.0)
        scene.light = DirectionalLight(intensity=0.0)
        scene.fog_density = 0.0
        scene.background = Vec3(0.0, 0.0, 0.0)
        scene.sky = Vec3(0.0, 0.0, 0.0)
        scene.camera.position = Vec3(0.0, 3.0, 4.0)
        scene.camera.look_at(Vec3(0.0, 0.0, 0.0))
        texture = TextureData(1, 1, bytes((0, 255, 0, 255)), "solid-green")
        scene.add(
            Node(
                "plane",
                mesh=plane(10.0),
                material=Material(color=Vec3(1.0, 1.0, 1.0), specular=0.0, texture=texture),
            )
        )
        self.renderer.render(scene)
        pixels = self.renderer.read_pixels()
        center = 24 * 64 * 4 + 32 * 4
        red, green, blue, alpha = pixels[center : center + 4]
        self.assertEqual(alpha, 255)
        self.assertGreater(green, 200)
        self.assertLess(red, 40)
        self.assertLess(blue, 40)

    def test_screenshot_is_a_real_png(self):
        self.renderer.render(build_scene())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.png"
            self.renderer.save_png(path)
            data = path.read_bytes()
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater(len(data), 100)

    def test_shader_compile_error_explains_why_and_fix(self):
        with self.assertRaises(ValueError) as caught:
            ShaderProgram("#version 330 core\nvoid main() { not_valid(); }", "")
        message = str(caught.exception)
        self.assertIn("Why:", message)
        self.assertIn("Fix:", message)

    def test_repeated_meshes_render_instanced_with_fewer_calls(self):
        from keystone.gpu.instancing import plan_instanced
        from keystone.scene import Transform

        scene = Scene()
        scene.background = Vec3(0.02, 0.02, 0.03)
        scene.camera.position = Vec3(0.0, 2.0, 10.0)
        mesh = cube(1.0)
        material = Material(color=Vec3(0.8, 0.3, 0.2), specular=0.4)
        for index in range(6):
            scene.add(
                Node(
                    f"box-{index}",
                    transform=Transform(position=Vec3((index - 2.5) * 1.6, 0.0, 0.0)),
                    mesh=mesh,
                    material=material,
                )
            )
        plan = plan_instanced(scene)
        self.assertEqual(plan["groups"], 1)
        self.assertEqual(plan["saved_calls"], 5)
        self.renderer.render(scene)
        pixels = self.renderer.read_pixels()
        stats = dict(self.renderer.last_stats)
        self.assertEqual(stats["draw_calls"], 1)
        self.assertEqual(stats["instanced_calls"], 1)
        self.assertEqual(stats["instances"], 6)
        self.assertEqual(len(pixels), 64 * 48 * 4)
        self.assertGreater(sum(pixels[0::4]) / (len(pixels) // 4), 5.0)

    def test_single_nodes_keep_plain_path_and_stats(self):
        scene = build_scene()
        self.renderer.render(scene)
        stats = dict(self.renderer.last_stats)
        self.assertEqual(stats["draw_calls"], 1)
        self.assertEqual(stats["instanced_calls"], 0)
        self.assertEqual(stats["instances"], 0)


class VersionGateTest(unittest.TestCase):
    def test_rejects_old_opengl(self):
        with self.assertRaises(RuntimeError) as caught:
            require_opengl_33("2.1 Mesa")
        self.assertIn("Why:", str(caught.exception))
        self.assertIn("Fix:", str(caught.exception))

    def test_accepts_33_and_newer(self):
        require_opengl_33("3.3.0 Core Profile Context")
        require_opengl_33("4.6.0 NVIDIA")


if __name__ == "__main__":
    unittest.main()
