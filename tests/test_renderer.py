"""Headless OpenGL integration tests for the Keystone renderer."""

import tempfile
import unittest
from pathlib import Path

from keystone.geometry import Material
from keystone.gpu.context import GLContext, require_opengl_33
from keystone.gpu.renderer import Renderer
from keystone.gpu.shader import ShaderProgram
from keystone.math3d import Vec3
from keystone.primitives import cube
from keystone.scene import Node, Scene


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

    def test_render_fills_the_center_with_a_lit_surface(self):
        self.renderer.render(build_scene())
        pixels = self.renderer.read_pixels()
        self.assertEqual(len(pixels), 64 * 48 * 4)
        center = 24 * 64 * 4 + 32 * 4
        red, green, blue, alpha = pixels[center : center + 4]
        self.assertEqual(alpha, 255)
        self.assertGreater(red, 60)
        self.assertGreater(red, blue)

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
