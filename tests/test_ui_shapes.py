"""Tests for line and frame drawing on the UI canvas."""

import unittest

from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.ui.canvas import Canvas

RED = (1.0, 0.0, 0.0, 1.0)


class CanvasLineTest(unittest.TestCase):
    def test_a_horizontal_line_records_one_quad_per_pixel(self):
        canvas = Canvas(32, 16)
        canvas.line(2, 5, 7, 5, RED)
        self.assertEqual(len(canvas.quads), 6)
        self.assertEqual([quad[0] for quad in canvas.quads], [2, 3, 4, 5, 6, 7])
        self.assertTrue(all(quad[1] == 5 for quad in canvas.quads))

    def test_a_diagonal_line_advances_both_axes(self):
        canvas = Canvas(32, 16)
        canvas.line(0, 0, 4, 4, RED)
        self.assertEqual(len(canvas.quads), 5)
        self.assertEqual([quad[0] for quad in canvas.quads], [0, 1, 2, 3, 4])

    def test_thickness_draws_more_pixels(self):
        thin = Canvas(32, 16)
        thick = Canvas(32, 16)
        thin.line(2, 5, 7, 5, RED)
        thick.line(2, 5, 7, 5, RED, thickness=3)
        self.assertEqual(len(thick.quads), len(thin.quads))
        self.assertEqual(thin.quads[0][2], 1)
        self.assertEqual(thick.quads[0][2], 3)

    def test_a_zero_length_line_draws_one_point(self):
        canvas = Canvas(16, 16)
        canvas.line(4, 4, 4, 4, RED)
        self.assertEqual(len(canvas.quads), 1)

    def test_lines_clip_at_the_canvas_edge(self):
        canvas = Canvas(10, 10)
        canvas.line(-5, 5, 20, 5, RED)
        for x, _y, width, _height, _color in canvas.quads:
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x + width, 10)

    def test_thin_lines_become_vertex_quads(self):
        canvas = Canvas(16, 16)
        canvas.line(0, 0, 3, 0, RED)
        self.assertEqual(len(canvas.vertices()), 4 * 6 * 6)

    def test_validation(self):
        canvas = Canvas(16, 16)
        with self.assertRaises(TypeError):
            canvas.line("a", 0, 1, 0, RED)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            canvas.line(0, 0, float("nan"), 0, RED)
        with self.assertRaises(ValueError):
            canvas.line(0, 0, 1, 0, RED, thickness=0)


class CanvasFrameTest(unittest.TestCase):
    def test_a_frame_records_four_sides(self):
        canvas = Canvas(32, 24)
        canvas.frame(2, 3, 20, 12, RED)
        self.assertEqual(len(canvas.quads), 4)

    def test_a_thick_frame_overlaps_the_corners(self):
        canvas = Canvas(32, 24)
        canvas.frame(2, 3, 20, 12, RED, thickness=2)
        self.assertEqual(len(canvas.quads), 4)
        for _x, _y, _width, _height, color in canvas.quads:
            self.assertEqual(color, RED)

    def test_frames_clip_and_drop_when_outside(self):
        canvas = Canvas(10, 10)
        canvas.frame(-4, -4, 8, 8, RED)
        for x, y, width, height, _color in canvas.quads:
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + width, 10)
            self.assertLessEqual(y + height, 10)
        empty = Canvas(10, 10)
        empty.frame(20, 20, 5, 5, RED)
        self.assertEqual(empty.quads, [])

    def test_validation(self):
        canvas = Canvas(16, 16)
        with self.assertRaises(ValueError):
            canvas.frame(0, 0, 0, 4, RED)
        with self.assertRaises(ValueError):
            canvas.frame(0, 0, 4, 4, RED, thickness=0)

    def test_describe_advertises_ui_shapes(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["ui_shapes"])


if __name__ == "__main__":
    unittest.main()
