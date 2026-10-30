"""Tests for the dependency-free human UI primitives and overlay."""

import unittest

from keystone.ui.canvas import Canvas
from keystone.ui.font import GLYPH_HEIGHT, GLYPH_WIDTH, glyph, line_height, text_width
from keystone.ui.overlay import HudState, HumanOverlay


class FontTest(unittest.TestCase):
    def test_metrics_match_the_bitmap_grid(self):
        self.assertEqual(len(glyph("A")), GLYPH_HEIGHT)
        self.assertEqual({len(row) for row in glyph("A")}, {GLYPH_WIDTH})
        self.assertEqual(text_width("AB", 2), 22)
        self.assertEqual(line_height(2), 14)

    def test_lowercase_and_unknown_characters_are_supported(self):
        self.assertEqual(glyph("a"), glyph("A"))
        self.assertEqual(len(glyph("\u00a7")), GLYPH_HEIGHT)


class CanvasTest(unittest.TestCase):
    def test_rect_is_clipped_to_canvas_bounds(self):
        canvas = Canvas(10, 8)
        canvas.rect(-4, -4, 20, 20, (1.0, 0.0, 0.0, 1.0))
        self.assertEqual(len(canvas.quads), 1)
        x, y, width, height, _ = canvas.quads[0]
        self.assertEqual((x, y, width, height), (0.0, 0.0, 10.0, 8.0))
        self.assertEqual(len(canvas.vertices()), 36)

    def test_text_records_labels_and_stays_inside_the_canvas(self):
        canvas = Canvas(40, 20)
        canvas.text(30, 0, "AB", (1.0, 1.0, 1.0, 1.0), scale=2)
        self.assertEqual(canvas.labels, ["AB"])
        vertices = canvas.vertices()
        self.assertGreater(len(vertices), 0)
        self.assertLessEqual(max(vertices[0::6]), 40)
        self.assertLessEqual(max(vertices[1::6]), 20)

    def test_invalid_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            Canvas(0, 10)
        with self.assertRaises(ValueError):
            Canvas(10, 10).rect(0, 0, 0, 4, (1.0, 1.0, 1.0, 1.0))


def state(**overrides):
    values = {
        "game": "cube-demo",
        "status": "ready",
        "fps": 60.0,
        "frame": 12,
        "elapsed": 0.2,
        "width": 960,
        "height": 540,
    }
    values.update(overrides)
    return HudState(**values)


class OverlayTest(unittest.TestCase):
    def test_overlay_shows_game_status_and_metrics(self):
        canvas = HumanOverlay().build(state())
        joined = " ".join(canvas.labels)
        self.assertIn("KEYSTONE", joined)
        self.assertIn("CUBE-DEMO", joined)
        self.assertIn("FPS 60", joined)
        self.assertIn("960X540", joined)
        self.assertIn("P PAUSE", joined)

    def test_pause_banner_and_hidden_overlay(self):
        overlay = HumanOverlay()
        paused = overlay.build(state(paused=True))
        self.assertIn("PAUSED", paused.labels)
        overlay.toggle()
        self.assertFalse(overlay.visible)
        self.assertEqual(overlay.build(state()).quads, [])

    def test_compact_layout_uses_smaller_text(self):
        canvas = HumanOverlay().build(state(width=400, height=240))
        self.assertIn("KEYSTONE", canvas.labels)
        self.assertTrue(all(x + width <= 400 for x, _, width, _, _ in canvas.quads))

    def test_tiny_canvas_is_clipped_without_errors(self):
        canvas = HumanOverlay().build(state(width=10, height=10, paused=True))
        self.assertIn("PAUSED", canvas.labels)
        self.assertTrue(all(x + width <= 10 and y + height <= 10 for x, y, width, height, _ in canvas.quads))
