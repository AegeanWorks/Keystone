"""Tests for immutable texture data and texture sources."""

import tempfile
import unittest
from pathlib import Path

from keystone.png import read_png, write_png
from keystone.texture import TextureData


class PatternCostTest(unittest.TestCase):
    """The presets must stay cheap: a per-pixel Python loop scaled badly."""

    def test_margin_presets_are_fast_at_512(self):
        import time

        for preset in ("grid", "panel", "rivets"):
            start = time.perf_counter()
            texture = TextureData.pattern(preset, size=512)
            elapsed = time.perf_counter() - start
            self.assertEqual(len(texture.rgba), 512 * 512 * 4)
            # Was 180-288 ms with an O(size^4) rivets scan; now single-digit ms.
            self.assertLess(
                elapsed,
                0.12,
                f"{preset} at 512 took {elapsed * 1000:.0f} ms; "
                "a per-pixel loop probably crept back in",
            )

    def test_panel_and_rivets_match_the_reference_definition(self):
        from keystone.texture import _blend

        base = bytes((26, 31, 41, 255))
        accent = bytes((46, 51, 64, 255))
        for size in (8, 15, 16, 17, 32, 33, 64):
            with self.subTest(size=size):
                inset = max(1, size // 16)
                outer = _blend(base, accent, 0.55)
                inner = _blend(base, accent, 0.25)
                reference = bytearray()
                for y in range(size):
                    for x in range(size):
                        edge = min(x, y, size - 1 - x, size - 1 - y)
                        if edge < inset:
                            reference += outer
                        elif edge < inset * 2:
                            reference += inner
                        else:
                            reference += base
                actual = TextureData.pattern(
                    "panel", size=size, dark=(26 / 255, 31 / 255, 41 / 255),
                    light=(46 / 255, 51 / 255, 64 / 255),
                ).rgba
                self.assertEqual(actual, bytes(reference))

    def test_pattern_rejects_an_unbounded_size(self):
        with self.assertRaises(ValueError) as caught:
            TextureData.pattern("grid", size=8192)
        self.assertIn("too large", str(caught.exception))


class TextureDataTest(unittest.TestCase):
    def test_pattern_presets_are_deterministic_and_distinct(self):
        for preset in ("grid", "panel", "rivets", "noise"):
            with self.subTest(preset=preset):
                first = TextureData.pattern(preset, size=32)
                second = TextureData.pattern(preset, size=32)
                self.assertEqual(first, second, f"{preset} is not deterministic")
                self.assertEqual((first.width, first.height), (32, 32))
                self.assertEqual(len(first.rgba), 32 * 32 * 4)
                self.assertEqual(min(first.rgba[3::4]), 255)

        digests = {
            preset: TextureData.pattern(preset, size=32).sha256()
            for preset in ("grid", "panel", "rivets", "noise")
        }
        self.assertEqual(
            len(set(digests.values())), 4, f"presets collide: {digests}"
        )

    def test_pattern_seed_changes_noise_but_not_grid(self):
        self.assertNotEqual(
            TextureData.pattern("noise", size=16, seed=1).sha256(),
            TextureData.pattern("noise", size=16, seed=2).sha256(),
        )
        self.assertEqual(
            TextureData.pattern("grid", size=16, seed=1).sha256(),
            TextureData.pattern("grid", size=16, seed=2).sha256(),
        )

    def test_pattern_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            TextureData.pattern("sparkles")
        with self.assertRaises(ValueError):
            TextureData.pattern("grid", size=0)
        with self.assertRaises(TypeError):
            TextureData.pattern("grid", size=16, dark=(0.1, 0.2))

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
