"""Tests for immutable texture data and texture sources."""

import tempfile
import unittest
from pathlib import Path

from keystone.png import read_png, write_png
from keystone.texture import TextureData


class TextureDataTest(unittest.TestCase):
    def test_checker_is_deterministic_and_has_expected_shape(self):
        first = TextureData.checker(8, cell=4, name="grid")
        second = TextureData.checker(8, cell=4, name="grid")
        self.assertEqual(first, second)
        self.assertEqual((first.width, first.height), (8, 8))
        self.assertEqual(len(first.rgba), 8 * 8 * 4)
        self.assertEqual(len(first.sha256()), 64)
        self.assertEqual(first.rgba[3], 255)

    def test_png_round_trip_keeps_pixels(self):
        pixels = bytes(
            (
                10, 20, 30, 255,
                40, 50, 60, 255,
                70, 80, 90, 255,
                100, 110, 120, 255,
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "swatch.png"
            write_png(path, 2, 2, pixels)
            expected = read_png(path)[2]
            texture = TextureData.from_png(path)
            self.assertEqual((texture.width, texture.height), (2, 2))
            self.assertEqual(texture.rgba, expected)
            self.assertEqual(texture.name, "swatch")

    def test_bad_texture_data_is_rejected(self):
        with self.assertRaises(ValueError):
            TextureData(0, 1, b"")
        with self.assertRaises(ValueError):
            TextureData(2, 2, b"\x00")
        with self.assertRaises(ValueError):
            TextureData.checker(0)
        with self.assertRaises(ValueError):
            TextureData.checker(8, cell=0)

    def test_sha256_distinguishes_shapes(self):
        first = TextureData(2, 2, b"\x00" * 16, "a")
        second = TextureData(4, 1, b"\x00" * 16, "b")
        self.assertNotEqual(first.sha256(), second.sha256())

    def test_checker_rejects_bad_channel_counts(self):
        with self.assertRaises(TypeError):
            TextureData.checker(8, dark=(0.1, 0.2))
        with self.assertRaises(TypeError):
            TextureData.checker(8, light=(0.1, 0.2, 0.3, 0.4))

    def test_texture_rejects_non_bytes_payload(self):
        with self.assertRaises(TypeError):
            TextureData(1, 1, [0, 0, 0, 255])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
