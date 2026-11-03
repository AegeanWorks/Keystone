"""Tests for the deterministic sRGB-correct linear pipeline (in-shader, pow 2.2)."""

import unittest

from keystone.analysis import analyze_frame, compare_reports
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.scene import ColorSettings, Scene
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


class SrgbContractsTest(unittest.TestCase):
    def test_color_settings_default_enabled(self):
        scene = Scene()
        self.assertTrue(scene.color.enabled)
        scene.color = ColorSettings(enabled=False)
        self.assertFalse(scene.color.enabled)

    def test_describe_reports_srgb(self):
        self.assertTrue(describe_game(CubeDemo())["capabilities"]["srgb"])

    def test_report_includes_color_metadata_and_hash(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(report["schema"], 8)
        self.assertEqual(report["scene"]["color"], {"enabled": True})
        scene.color = ColorSettings(enabled=False)
        off = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(off["scene"]["color"], {"enabled": False})
        self.assertNotEqual(report["hash"], off["hash"])

    def test_compare_reports_diffs_color(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((0, 0, 0, 255)) * 4
        on = analyze_frame(scene, pixels, 2, 2)
        scene.color = ColorSettings(enabled=False)
        off = analyze_frame(scene, pixels, 2, 2)
        diff = compare_reports(on, off)
        self.assertFalse(diff["same_report"])
        self.assertFalse(diff["same_color"])
        self.assertEqual(diff["color"], {"before": {"enabled": True}, "after": {"enabled": False}})
        same = compare_reports(on, analyze_frame(CubeDemo().build_scene(), pixels, 2, 2))
        self.assertTrue(same["same_color"])
        self.assertEqual(diff["schema"], 8)

    def test_compare_accepts_legacy_without_color(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        legacy = dict(report)
        legacy["schema"] = 6
        legacy["scene"] = dict(report["scene"])
        legacy["scene"].pop("color", None)
        diff = compare_reports(legacy, report)
        self.assertTrue(diff["same_color"])
        self.assertEqual(diff["schema"], 8)

    def test_snapshot_round_trips_color_flag(self):
        scene = CubeDemo().build_scene()
        scene.color = ColorSettings(enabled=False)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertFalse(restored.color.enabled)
        legacy = scene_to_dict(CubeDemo().build_scene())
        legacy["environment"].pop("color", None)
        self.assertTrue(scene_from_dict(legacy).color.enabled)
        with self.assertRaises(TypeError):
            bad = scene_to_dict(scene)
            bad["environment"]["color"] = "on"
            scene_from_dict(bad)

    def test_scene_document_and_snapshot_expose_color(self):
        from keystone.web.scene import scene_document

        document = scene_document(CubeDemo().build_scene())
        self.assertEqual(document["color"], {"enabled": True})


if __name__ == "__main__":
    unittest.main()
