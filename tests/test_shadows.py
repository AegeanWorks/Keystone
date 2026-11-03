"""Tests for deterministic directional shadow mapping (fixed 1024 map, PCF)."""

import unittest

from keystone.analysis import analyze_frame, compare_reports
from keystone.gpu.shadow import (
    SHADOW_BIAS,
    SHADOW_MAP_SIZE,
    light_view,
    light_vp,
    orthographic,
)
from keystone.math3d import Mat4, Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.scene import DirectionalLight, Scene, ShadowSettings
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


class ShadowMathTest(unittest.TestCase):
    def test_orthographic_is_deterministic(self):
        first = orthographic(-12.0, 12.0, -12.0, 12.0, 1.0, 40.0)
        second = orthographic(-12.0, 12.0, -12.0, 12.0, 1.0, 40.0)
        self.assertEqual(first.flat(), second.flat())
        with self.assertRaises(ValueError):
            orthographic(1.0, 1.0, -1.0, 1.0, 1.0, 2.0)

    def test_light_view_and_vp_are_deterministic(self):
        direction = Vec3(-0.45, -1.0, -0.35)
        self.assertEqual(light_view(direction).flat(), light_view(direction).flat())
        self.assertEqual(light_vp(direction).flat(), light_vp(direction).flat())
        with self.assertRaises(ValueError):
            light_view(Vec3())

    def test_light_vp_matches_manual_composition(self):
        direction = Vec3(-0.45, -1.0, -0.35)
        expected = orthographic(-12.0, 12.0, -12.0, 12.0, 1.0, 40.0) * light_view(direction)
        self.assertEqual(light_vp(direction).flat(), expected.flat())

    def test_parallel_up_vector_uses_fallback(self):
        straight_down = light_view(Vec3(0.0, -1.0, 0.0))
        self.assertIsInstance(straight_down, Mat4)

    def test_shadow_settings_default_enabled(self):
        scene = Scene()
        self.assertTrue(scene.shadow.enabled)
        scene.shadow = ShadowSettings(enabled=False)
        self.assertFalse(scene.shadow.enabled)

    def test_only_fixed_size_allowed(self):
        from keystone.gpu.shadow import ShadowMap

        with self.assertRaises(ValueError):
            ShadowMap(size=512)
        self.assertEqual(SHADOW_MAP_SIZE, 1024)
        self.assertAlmostEqual(SHADOW_BIAS, 0.005)


class ShadowContractsTest(unittest.TestCase):
    def test_describe_reports_shadows(self):
        self.assertTrue(describe_game(CubeDemo())["capabilities"]["shadows"])

    def test_report_includes_shadow_metadata_and_hash(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(report["schema"], 9)
        self.assertEqual(report["scene"]["shadows"], {"enabled": True, "size": 1024})
        scene.shadow = ShadowSettings(enabled=False)
        off = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        self.assertEqual(off["scene"]["shadows"], {"enabled": False, "size": 0})
        self.assertNotEqual(report["hash"], off["hash"])

    def test_compare_reports_diffs_shadows(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((0, 0, 0, 255)) * 4
        on = analyze_frame(scene, pixels, 2, 2)
        scene.shadow = ShadowSettings(enabled=False)
        off = analyze_frame(scene, pixels, 2, 2)
        diff = compare_reports(on, off)
        self.assertFalse(diff["same_report"])
        self.assertFalse(diff["same_shadows"])
        self.assertEqual(diff["shadows"]["before"], {"enabled": True, "size": 1024})
        self.assertEqual(diff["shadows"]["after"], {"enabled": False, "size": 0})
        same = compare_reports(on, analyze_frame(CubeDemo().build_scene(), pixels, 2, 2))
        self.assertTrue(same["same_shadows"])

    def test_compare_accepts_legacy_without_shadows(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        legacy = dict(report)
        legacy["schema"] = 5
        legacy["scene"] = dict(report["scene"])
        legacy["scene"].pop("shadows", None)
        diff = compare_reports(legacy, report)
        self.assertTrue(diff["same_shadows"])
        self.assertEqual(diff["schema"], 9)

    def test_snapshot_round_trips_shadow_flag(self):
        scene = CubeDemo().build_scene()
        scene.shadow = ShadowSettings(enabled=False)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertFalse(restored.shadow.enabled)
        legacy = scene_to_dict(CubeDemo().build_scene())
        legacy["environment"].pop("shadow", None)
        self.assertTrue(scene_from_dict(legacy).shadow.enabled)
        with self.assertRaises(TypeError):
            bad = scene_to_dict(scene)
            bad["environment"]["shadow"] = "on"
            scene_from_dict(bad)

    def test_scene_document_and_inspector_expose_shadows(self):
        from keystone.web.scene import scene_document

        document = scene_document(CubeDemo().build_scene())
        self.assertEqual(document["shadows"], {"enabled": True, "size": 1024})

    def test_shadow_light_helper_accepts_directional_light(self):
        from keystone.gpu.shadow import light_vp_for

        light = DirectionalLight(direction=Vec3(-0.45, -1.0, -0.35))
        self.assertEqual(light_vp_for(light).flat(), light_vp(light.direction).flat())


if __name__ == "__main__":
    unittest.main()
