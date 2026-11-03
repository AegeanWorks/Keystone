"""Tests for the deterministic post color-grade (in-shader exposure + vignette)."""

import unittest

from keystone.analysis import analyze_frame, compare_reports
from keystone.gpu.post import POST_EXPOSURE, POST_VIGNETTE, grade_color, vignette_factor
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.scene import PostSettings, Scene
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


class PostMathTest(unittest.TestCase):
    def test_constants_are_fixed(self):
        self.assertAlmostEqual(POST_EXPOSURE, 1.12)
        self.assertAlmostEqual(POST_VIGNETTE, 0.28)

    def test_vignette_center_is_one_and_corners_dim(self):
        self.assertAlmostEqual(vignette_factor(0.5, 0.5), 1.0)
        corner = vignette_factor(0.0, 0.0)
        self.assertLess(corner, 1.0)
        self.assertGreaterEqual(corner, 0.0)
        self.assertAlmostEqual(corner, 1.0 - POST_VIGNETTE)

    def test_grade_applies_exposure_then_vignette(self):
        center = grade_color((0.5, 0.5, 0.5), 0.5, 0.5)
        self.assertAlmostEqual(center[0], min(1.0, 0.5 * POST_EXPOSURE), places=6)
        corner = grade_color((0.5, 0.5, 0.5), 0.0, 0.0)
        self.assertLess(corner[0], center[0])
        clamped = grade_color((1.0, 1.0, 1.0), 0.5, 0.5)
        self.assertLessEqual(clamped[0], 1.0)


class PostContractsTest(unittest.TestCase):
    def test_post_settings_default_enabled(self):
        scene = Scene()
        self.assertTrue(scene.post.enabled)
        scene.post = PostSettings(enabled=False)
        self.assertFalse(scene.post.enabled)

    def test_describe_reports_post(self):
        self.assertTrue(describe_game(CubeDemo())["capabilities"]["post"])

    def test_report_includes_post_metadata_and_hash(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(report["schema"], 9)
        self.assertEqual(report["scene"]["post"], {"enabled": True})
        scene.post = PostSettings(enabled=False)
        off = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(off["scene"]["post"], {"enabled": False})
        self.assertNotEqual(report["hash"], off["hash"])

    def test_compare_reports_diffs_post(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((0, 0, 0, 255)) * 4
        on = analyze_frame(scene, pixels, 2, 2)
        scene.post = PostSettings(enabled=False)
        off = analyze_frame(scene, pixels, 2, 2)
        diff = compare_reports(on, off)
        self.assertFalse(diff["same_report"])
        self.assertFalse(diff["same_post"])
        self.assertEqual(diff["post"], {"before": {"enabled": True}, "after": {"enabled": False}})
        same = compare_reports(on, analyze_frame(CubeDemo().build_scene(), pixels, 2, 2))
        self.assertTrue(same["same_post"])
        self.assertEqual(diff["schema"], 9)

    def test_compare_accepts_legacy_without_post(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        legacy = dict(report)
        legacy["schema"] = 7
        legacy["scene"] = dict(report["scene"])
        legacy["scene"].pop("post", None)
        diff = compare_reports(legacy, report)
        self.assertTrue(diff["same_post"])
        self.assertEqual(diff["schema"], 9)

    def test_snapshot_round_trips_post_flag(self):
        scene = CubeDemo().build_scene()
        scene.post = PostSettings(enabled=False)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertFalse(restored.post.enabled)
        legacy = scene_to_dict(CubeDemo().build_scene())
        legacy["environment"].pop("post", None)
        self.assertTrue(scene_from_dict(legacy).post.enabled)
        with self.assertRaises(TypeError):
            bad = scene_to_dict(scene)
            bad["environment"]["post"] = "on"
            scene_from_dict(bad)

    def test_scene_document_and_inspector_expose_post(self):
        from keystone.web.scene import scene_document

        document = scene_document(CubeDemo().build_scene())
        self.assertEqual(document["post"], {"enabled": True})


if __name__ == "__main__":
    unittest.main()
