"""Tests for textured HUD images on the canvas and UI renderer."""

import unittest

from OpenGL import GL

from keystone.gpu.context import GLContext
from keystone.gpu.ui_renderer import UiRenderer
from keystone.texture import TextureData
from keystone.ui.canvas import Canvas

RED = (1.0, 0.0, 0.0, 1.0)
BLUE = (0.0, 0.0, 1.0, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)


def _solid(red: int, green: int, blue: int, size: int = 2) -> TextureData:
    return TextureData(size, size, bytes([red, green, blue, 255] * size * size), "solid")


def _rows(*rows: tuple[int, int, int]) -> TextureData:
    payload = b"".join(bytes((*row, 255)) for row in rows)
    return TextureData(1, len(rows), payload, "rows")


class CanvasImageTest(unittest.TestCase):
    def test_an_image_inside_the_canvas_records_full_uvs(self):
        canvas = Canvas(64, 48)
        texture = _solid(255, 0, 0)
        canvas.image(10, 12, 20, 16, texture, WHITE)
        self.assertEqual(len(canvas.images), 1)
        element = canvas.images[0]
        self.assertEqual((element.x, element.y, element.width, element.height), (10, 12, 20, 16))
        self.assertEqual((element.u0, element.v0, element.u1, element.v1), (0.0, 0.0, 1.0, 1.0))

    def test_an_image_is_clipped_with_adjusted_uvs(self):
        canvas = Canvas(64, 48)
        canvas.image(-8, 0, 16, 8, _solid(255, 0, 0))
        element = canvas.images[0]
        self.assertEqual((element.x, element.width), (0.0, 8.0))
        self.assertAlmostEqual(element.u0, 0.5)
        self.assertAlmostEqual(element.u1, 1.0)

    def test_a_fully_outside_image_is_dropped(self):
        canvas = Canvas(20, 20)
        canvas.image(40, 40, 10, 10, _solid(255, 0, 0))
        self.assertEqual(canvas.images, [])

    def test_malformed_images_are_rejected(self):
        canvas = Canvas(32, 32)
        texture = _solid(255, 0, 0)
        with self.assertRaises(TypeError):
            canvas.image(0, 0, 8, 8, "texture")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            canvas.image(0, 0, 0, 8, texture)
        with self.assertRaises(ValueError):
            canvas.image(0, 0, 8, 8, texture, u0=0.8, u1=0.2)
        with self.assertRaises(TypeError):
            canvas.image(0, 0, 8, 8, texture, color=(1.0, 1.0, 1.0))
        with self.assertRaises(ValueError):
            canvas.image(0, 0, 8, 8, texture, color=(1.0, 1.0, float("nan"), 1.0))
        with self.assertRaises(TypeError):
            canvas.image(0, 0, 8, 8, texture, color="white")  # type: ignore[arg-type]


class UiImageRenderTest(unittest.TestCase):
    def setUp(self):
        self.context = GLContext(64, 48, visible=False)
        self.addCleanup(self.context.close)
        GL.glViewport(0, 0, 64, 48)
        self.ui = UiRenderer()
        self.addCleanup(self.ui.release)

    def _draw(self, canvas: Canvas) -> None:
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self.ui.draw(canvas)

    def _pixel(self, x: int, screen_y: int) -> tuple[int, int, int, int]:
        pixels = bytes(GL.glReadPixels(0, 0, 64, 48, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE))
        index = ((47 - screen_y) * 64 + x) * 4
        return tuple(pixels[index : index + 4])  # type: ignore[return-value]

    def test_a_solid_texture_draws_at_its_rect(self):
        canvas = Canvas(64, 48)
        canvas.image(16, 8, 32, 32, _solid(255, 0, 0))
        self._draw(canvas)
        red, green, blue, _alpha = self._pixel(32, 24)
        self.assertGreater(red, 200)
        self.assertLess(green, 60)
        self.assertLess(blue, 60)

    def test_the_texture_is_not_vertically_flipped(self):
        canvas = Canvas(64, 48)
        canvas.image(16, 8, 32, 32, _rows((255, 0, 0), (0, 0, 255)))
        self._draw(canvas)
        top = self._pixel(32, 10)
        bottom = self._pixel(32, 38)
        self.assertGreater(top[0], 200)
        self.assertLess(top[2], 60)
        self.assertGreater(bottom[2], 200)
        self.assertLess(bottom[0], 60)

    def test_uv_subrects_select_part_of_the_texture(self):
        canvas = Canvas(64, 48)
        texture = TextureData(2, 1, bytes((255, 0, 0, 255, 0, 0, 255, 255)), "strip")
        canvas.image(0, 0, 64, 48, texture, u0=0.5, u1=1.0)
        self._draw(canvas)
        red, _green, blue, _alpha = self._pixel(32, 24)
        self.assertGreater(blue, 200)
        self.assertLess(red, 60)

    def test_images_draw_after_colored_quads(self):
        canvas = Canvas(64, 48)
        canvas.rect(0, 0, 64, 48, RED)
        canvas.image(16, 16, 32, 16, _solid(0, 0, 255))
        self._draw(canvas)
        red, _green, blue, _alpha = self._pixel(32, 24)
        self.assertGreater(blue, 200)
        self.assertLess(red, 60)

    def test_zero_alpha_and_empty_canvases_draw_nothing(self):
        canvas = Canvas(64, 48)
        canvas.image(0, 0, 64, 48, _solid(255, 0, 0), color=(1.0, 1.0, 1.0, 0.0))
        self._draw(canvas)
        self.assertEqual(self._pixel(32, 24), (0, 0, 0, 255))
        self.ui.draw(Canvas(64, 48))


if __name__ == "__main__":
    unittest.main()
