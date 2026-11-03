"""Tests for the deterministic bloom glow (in-shader luminance threshold)."""

import unittest

from keystone.analysis import analyze_frame, compare_reports
from keystone.gpu.bloom import (
    BLOOM_INTENSITY,
    BLOOM_KNEE,
    BLOOM_THRESHOLD,
    bloom_color,
    bloom_factor,
)
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.scene import BloomSettings, Scene
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


class BloomMathTest(unittest.TestCase):
    def test_constants_are_fixed(self):
        self.assertAlmostEqual(BLOOM_THRESHOLD, 0.72)
        self.assertAlmostEqual(BLOOM_KNEE, 0.12)
        self.assertAlmostEqual(BLOOM_INTENSITY, 0.35)

    def test_dark_has_no_bloom_and_bright_saturates(self):
        self.assertAlmostEqual(bloom_factor(0.0), 0.0)
        self.assertAlmostEqual(bloom_factor(0.5), 0.0)
        self.assertAlmostEqual(bloom_factor(1.0), 1.0)
        mid = bloom_factor(BLOOM_THRESHOLD + BLOOM_KNEE / 2.0)
        self.assertGreater(mid, 0.0)
        self.assertLess(mid, 1.0)

    def test_bloom_adds_proportionally_and_clamps(self):
        dark = bloom_color((0.1, 0.1, 0.1))
        self.assertAlmostEqual(dark[0], 0.1, places=6)
        bright = bloom_color((0.9, 0.9, 0.9))
        self.assertGreater(bright[0], 0.9)
        clamped = bloom_color((1.0, 1.0, 1.0))
        self.assertLessEqual(clamped[0], 1.0)


class BloomContractsTest(unittest.TestCase):
    def test_bloom_settings_default_enabled(self):
        scene = Scene()
        self.assertTrue(scene.bloom.enabled)
        scene.bloom = BloomSettings(enabled=False)
        self.assertFalse(scene.bloom.enabled)

    def test_describe_reports_bloom(self):
        self.assertTrue(describe_game(CubeDemo())["capabilities"]["bloom"])

    def test_report_includes_bloom_metadata_and_hash(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(report["schema"], 9)
        self.assertEqual(report["scene"]["bloom"], {"enabled": True})
        scene.bloom = BloomSettings(enabled=False)
        off = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(off["scene"]["bloom"], {"enabled": False})
        self.assertNotEqual(report["hash"], off["hash"])

    def test_compare_reports_diffs_bloom(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((0, 0, 0, 255)) * 4
        on = analyze_frame(scene, pixels, 2, 2)
        scene.bloom = BloomSettings(enabled=False)
        off = analyze_frame(scene, pixels, 2, 2)
        diff = compare_reports(on, off)
        self.assertFalse(diff["same_report"])
        self.assertFalse(diff["same_bloom"])
        self.assertEqual(diff["bloom"], {"before": {"enabled": True}, "after": {"enabled": False}})
        same = compare_reports(on, analyze_frame(CubeDemo().build_scene(), pixels, 2, 2))
        self.assertTrue(same["same_bloom"])
        self.assertEqual(diff["schema"], 9)

    def test_compare_accepts_legacy_without_bloom(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        legacy = dict(report)
        legacy["schema"] = 8
        legacy["scene"] = dict(report["scene"])
        legacy["scene"].pop("bloom", None)
        diff = compare_reports(legacy, report)
        self.assertTrue(diff["same_bloom"])
        self.assertEqual(diff["schema"], 9)

    def test_snapshot_round_trips_bloom_flag(self):
        scene = CubeDemo().build_scene()
        scene.bloom = BloomSettings(enabled=False)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertFalse(restored.bloom.enabled)
        legacy = scene_to_dict(CubeDemo().build_scene())
        legacy["environment"].pop("bloom", None)
        self.assertTrue(scene_from_dict(legacy).bloom.enabled)
        with self.assertRaises(TypeError):
            bad = scene_to_dict(scene)
            bad["environment"]["bloom"] = "on"
            scene_from_dict(bad)

    def test_scene_document_and_inspector_expose_bloom(self):
        from keystone.web.scene import scene_document

        document = scene_document(CubeDemo().build_scene())
        self.assertEqual(document["bloom"], {"enabled": True})


if __name__ == "__main__":
    unittest.main()
