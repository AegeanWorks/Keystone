"""Tests for word wrapping and multi-line paragraph drawing."""

import unittest

from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.ui.canvas import Canvas
from keystone.ui.font import line_height, text_width, wrap_text

WHITE = (1.0, 1.0, 1.0, 1.0)


class WrapTextTest(unittest.TestCase):
    def test_wraps_at_word_boundaries(self):
        limit = text_width("HELLO WORLD", 1)
        self.assertEqual(wrap_text("hello world again", limit), ("hello world", "again"))

    def test_keeps_explicit_newlines(self):
        self.assertEqual(wrap_text("first\nsecond", 1000), ("first", "second"))
        self.assertEqual(wrap_text("first\n", 1000), ("first", ""))

    def test_a_long_word_is_truncated_to_fit(self):
        limit = text_width("ABCDE", 1)
        lines = wrap_text("abcdefghij", limit)
        self.assertEqual(lines, ("abcde",))
        self.assertLessEqual(text_width(lines[0], 1), limit)

    def test_empty_text_wraps_to_no_lines(self):
        self.assertEqual(wrap_text("", 100), ())
        self.assertEqual(wrap_text("   ", 100), ("",))

    def test_every_line_fits_the_limit(self):
        text = "the quick brown fox jumps over the lazy dog"
        limit = 80
        for line in wrap_text(text, limit, 2):
            self.assertLessEqual(text_width(line, 2), limit)

    def test_wrapping_is_deterministic(self):
        text = "alpha beta gamma delta"
        self.assertEqual(wrap_text(text, 60), wrap_text(text, 60))

    def test_malformed_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            wrap_text("a", 0)
        with self.assertRaises(ValueError):
            wrap_text("a", 10, 0)
        with self.assertRaises(TypeError):
            wrap_text("a", "wide")  # type: ignore[arg-type]


class ParagraphTest(unittest.TestCase):
    def test_draws_one_text_element_per_wrapped_line(self):
        canvas = Canvas(320, 120)
        limit = text_width("ALPHA BETA", 2)
        height = canvas.paragraph(4, 6, limit, "alpha beta gamma", WHITE, scale=2)
        self.assertEqual(canvas.labels, ["ALPHA BETA", "GAMMA"])
        self.assertEqual([element.y for element in canvas.text_elements], [6, 6 + line_height(2)])
        self.assertEqual(height, 2 * line_height(2))

    def test_line_gap_extends_the_reported_height(self):
        canvas = Canvas(320, 120)
        height = canvas.paragraph(0, 0, 1000, "one\ntwo", WHITE, scale=2, line_gap=4)
        self.assertEqual(height, 2 * line_height(2) + 4)

    def test_blank_lines_consume_height(self):
        canvas = Canvas(320, 120)
        height = canvas.paragraph(0, 0, 1000, "one\n\ntwo", WHITE, scale=2)
        self.assertEqual(height, 3 * line_height(2))
        self.assertEqual(canvas.labels, ["ONE", "TWO"])

    def test_empty_text_draws_nothing(self):
        canvas = Canvas(40, 40)
        self.assertEqual(canvas.paragraph(0, 0, 30, "", WHITE, scale=2), 0)
        self.assertEqual(canvas.text_elements, [])

    def test_non_positive_width_draws_nothing(self):
        canvas = Canvas(40, 40)
        self.assertEqual(canvas.paragraph(0, 0, 0, "text", WHITE, scale=2), 0)
        self.assertEqual(canvas.text_elements, [])

    def test_every_drawn_line_stays_inside_the_width(self):
        canvas = Canvas(96, 96)
        canvas.paragraph(0, 0, 90, "a long hud message that wraps", WHITE, scale=1)
        for element in canvas.text_elements:
            self.assertLessEqual(element.x + text_width(element.text, element.scale), 90)

    def test_malformed_arguments_are_rejected(self):
        canvas = Canvas(40, 40)
        with self.assertRaises(ValueError):
            canvas.paragraph(0, 0, 30, "text", WHITE, scale=2, line_gap=-1)
        with self.assertRaises(ValueError):
            canvas.paragraph(0, 0, 30, "text", WHITE, scale=0)

    def test_describe_advertises_paragraph_text(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["ui_text_wrap"])


if __name__ == "__main__":
    unittest.main()
