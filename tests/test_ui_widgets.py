"""Tests for the HUD layout widgets and right-edge safety."""

import unittest

from keystone.ui.canvas import Canvas
from keystone.ui.font import line_height, text_width
from keystone.ui.overlay import HudState, HumanOverlay
from keystone.ui.widgets import (
    ACCENT,
    badge,
    label_row,
    progress_bar,
    table,
)


def _right_edge_margin(element, width: int) -> float:
    return width - (element.x + text_width(element.text, element.scale))


class LabelRowTest(unittest.TestCase):
    def test_label_and_value_sit_at_opposite_edges(self):
        canvas = Canvas(320, 90)
        row_height = label_row(canvas, 10, 12, 300, "health", "96", scale=2)
        label, value = canvas.text_elements
        self.assertEqual(label.text, "HEALTH")
        self.assertEqual(value.text, "96")
        self.assertEqual(label.x, 10)
        self.assertEqual(value.x + text_width(value.text, 2), 310)
        self.assertEqual(row_height, line_height(2))

    def test_label_is_trimmed_before_it_collides_with_the_value(self):
        canvas = Canvas(200, 40)
        label_row(canvas, 0, 0, 200, "a very long status label", "999", scale=2)
        label, value = canvas.text_elements
        self.assertLess(label.x + text_width(label.text, 2), value.x)
        self.assertEqual(value.x + text_width(value.text, 2), 200)

    def test_rows_stay_inside_a_narrow_viewport(self):
        canvas = Canvas(390, 844)
        label_row(canvas, 12, 20, 900, "culling", "23 offscreen", scale=2)
        for element in canvas.text_elements:
            with self.subTest(element=element.text):
                self.assertGreaterEqual(_right_edge_margin(element, 390), 0)
                self.assertGreaterEqual(element.x, 0)

    def test_non_positive_width_draws_nothing(self):
        canvas = Canvas(80, 40)
        self.assertEqual(label_row(canvas, 0, 0, 0, "a", "b", scale=2), 0)
        self.assertEqual(canvas.text_elements, [])

    def test_text_is_not_tracked_when_the_row_cannot_fit_one_glyph(self):
        canvas = Canvas(40, 40)
        label_row(canvas, 36, 0, 4, "score", "88", scale=2)
        for element in canvas.text_elements:
            self.assertLessEqual(element.x + text_width(element.text, 2), 40)


class TableTest(unittest.TestCase):
    def test_rows_stack_and_report_total_height(self):
        canvas = Canvas(320, 200)
        height = table(
            canvas,
            8,
            8,
            304,
            (("fps", "60"), ("draws", "11"), ("tris", "432")),
            scale=2,
            gap=4,
        )
        self.assertEqual(len(canvas.text_elements), 6)
        self.assertEqual([element.y for element in canvas.text_elements], [8, 8, 26, 26, 44, 44])
        self.assertEqual(height, 3 * line_height(2) + 2 * 4)

    def test_empty_table_draws_nothing(self):
        canvas = Canvas(64, 64)
        self.assertEqual(table(canvas, 0, 0, 64, (), scale=2), 0)
        self.assertEqual(canvas.text_elements, [])


class ProgressBarTest(unittest.TestCase):
    def test_fill_tracks_the_clamped_value(self):
        canvas = Canvas(200, 20)
        progress_bar(canvas, 0, 0, 200, 10, 0.5, scale=2)
        fills = [quad for quad in canvas.quads if quad[4] == ACCENT]
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(fills[-1][2], 100.0)

    def test_values_are_clamped_to_the_bar(self):
        low, high = Canvas(200, 20), Canvas(200, 20)
        progress_bar(low, 0, 0, 200, 10, -3.0, scale=2)
        progress_bar(high, 0, 0, 200, 10, 9.0, scale=2)
        self.assertEqual([quad for quad in low.quads if quad[4] == ACCENT], [])
        high_fill = [quad for quad in high.quads if quad[4] == ACCENT][-1]
        self.assertEqual(high_fill[2], 200.0)

    def test_bar_clips_at_the_canvas_edge(self):
        canvas = Canvas(100, 20)
        progress_bar(canvas, 80, 0, 60, 10, 1.0, scale=2)
        for x, _y, width, _height, _color in canvas.quads:
            self.assertLessEqual(x + width, 100)

    def test_rejects_an_unknown_value(self):
        with self.assertRaises(ValueError):
            progress_bar(Canvas(20, 20), 0, 0, 10, 4, float("nan"), scale=2)


class BadgeTest(unittest.TestCase):
    def test_badge_measures_itself_and_draws_the_label(self):
        canvas = Canvas(200, 40)
        width = badge(canvas, 10, 10, "new", scale=2)
        self.assertEqual(width, text_width("NEW", 2) + 8)
        self.assertEqual(canvas.labels, ["NEW"])
        self.assertEqual(canvas.text_elements[0].x, 14)

    def test_badge_clips_at_the_canvas_edge(self):
        canvas = Canvas(60, 20)
        badge(canvas, 50, 0, "overflow", scale=2)
        for x, _y, width, _height, _color in canvas.quads:
            self.assertLessEqual(x + width, 60)


class OverlaySafetyTest(unittest.TestCase):
    def _state(self, width: int, height: int) -> HudState:
        return HudState(
            game="a very long game title",
            status="status text that is fairly long",
            fps=60.0,
            frame=42,
            elapsed=1.5,
            width=width,
            height=height,
            draw_calls=12,
            triangles=432,
            shadow_calls=1,
            post_enabled=1,
            bloom_enabled=1,
            audio_voices=3,
            anim_clips=2,
            particles=64,
            sprites=64,
            culled=23,
        )

    def test_right_panel_fits_a_phone_viewport(self):
        for width, height in ((960, 540), (390, 844), (320, 200), (100, 140)):
            with self.subTest(width=width, height=height):
                canvas = HumanOverlay().build(self._state(width, height))
                for element in canvas.text_elements:
                    self.assertLessEqual(
                        element.x + text_width(element.text, element.scale),
                        width,
                        element.text,
                    )
                    self.assertGreaterEqual(element.x, 0, element.text)


if __name__ == "__main__":
    unittest.main()
