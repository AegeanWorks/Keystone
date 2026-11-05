"""Tests for deterministic GPU point-sprite particle rendering."""

import unittest

from keystone.analysis import REPORT_SCHEMA, analyze_frame, compare_reports
from keystone.gpu.sprites import (
    SPRITE_ATTEN,
    SPRITE_COLOR,
    SPRITE_MAX_SIZE,
    SPRITE_MIN_SIZE,
    billboard_corners,
    soft_alpha,
    sprite_alpha,
    sprite_scale,
)
from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.scene import Scene, SpriteSettings
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


class SpriteMathTest(unittest.TestCase):
    def test_constants_are_fixed(self):
        self.assertAlmostEqual(SPRITE_ATTEN, 180.0)
        self.assertAlmostEqual(SPRITE_MAX_SIZE, 64.0)
        self.assertAlmostEqual(SPRITE_MIN_SIZE, 1.0)
        self.assertEqual(SPRITE_COLOR, (1.0, 0.9, 0.7))

    def test_scale_attenuates_and_clamps(self):
        self.assertAlmostEqual(sprite_scale(180.0, 1.0), 1.0)
        self.assertGreater(sprite_scale(10.0, 1.0), sprite_scale(100.0, 1.0))
        self.assertEqual(sprite_scale(0.01, 100.0), SPRITE_MAX_SIZE)
        self.assertEqual(sprite_scale(100000.0, 0.001), SPRITE_MIN_SIZE)
        with self.assertRaises(ValueError):
            sprite_scale(float("nan"), 1.0)

    def test_soft_alpha_center_and_edge(self):
        self.assertAlmostEqual(soft_alpha(0.5, 0.5), 1.0)
        self.assertAlmostEqual(soft_alpha(0.0, 0.0), 0.0)
        self.assertAlmostEqual(soft_alpha(1.0, 0.5), 0.0)
        mid = soft_alpha(0.75, 0.5)
        self.assertGreater(mid, 0.0)
        self.assertLess(mid, 1.0)
        with self.assertRaises(ValueError):
            soft_alpha(float("inf"), 0.5)

    def test_sprite_alpha_combines_fade_and_soft(self):
        self.assertAlmostEqual(sprite_alpha(0.0, 1.0), 1.0)
        self.assertAlmostEqual(sprite_alpha(1.0, 1.0), 0.0)
        self.assertAlmostEqual(sprite_alpha(0.5, 1.0), 0.5, places=5)
        self.assertAlmostEqual(sprite_alpha(0.0, 1.0, 0.0, 0.0), 0.0)
        with self.assertRaises(ValueError):
            sprite_alpha(0.0, 0.0)
        with self.assertRaises(ValueError):
            sprite_alpha(float("nan"), 1.0)

    def test_billboard_corners_are_symmetric(self):
        corners = billboard_corners(Vec3(1.0, 2.0, 3.0), Vec3(1.0, 0.0, 0.0), Vec3(0.0, 1.0, 0.0), 2.0)
        self.assertEqual(len(corners), 4)
        center = Vec3(
            sum(point.x for point in corners) / 4.0,
            sum(point.y for point in corners) / 4.0,
            sum(point.z for point in corners) / 4.0,
        )
        self.assertAlmostEqual(center.x, 1.0)
        self.assertAlmostEqual(center.y, 2.0)
        self.assertAlmostEqual(center.z, 3.0)
        with self.assertRaises(ValueError):
            billboard_corners(Vec3(), Vec3(1, 0, 0), Vec3(0, 1, 0), -1.0)


class SpriteSceneTest(unittest.TestCase):
    def test_scene_defaults_to_sprites_enabled(self):
        self.assertTrue(Scene().sprite.enabled)
        self.assertTrue(SpriteSettings().enabled)

    def test_snapshot_round_trips_sprites(self):
        scene = Scene()
        scene.sprite = SpriteSettings(enabled=False)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertFalse(restored.sprite.enabled)
        scene.sprite = SpriteSettings(enabled=True)
        restored = scene_from_dict(scene_to_dict(scene))
        self.assertTrue(restored.sprite.enabled)

    def test_snapshot_rejects_non_mapping_sprites(self):
        document = scene_to_dict(Scene())
        document["environment"]["sprites"] = [True]
        with self.assertRaises(TypeError):
            scene_from_dict(document)


class SpriteReportTest(unittest.TestCase):
    def test_schema_is_11_with_sprites_and_fx(self):
        self.assertEqual(REPORT_SCHEMA["version"], 11)
        self.assertIn("sprites", REPORT_SCHEMA["fields"]["scene"])
        self.assertIn("fx", REPORT_SCHEMA["fields"])

    def test_analyze_frame_reports_sprites_and_fx(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((10, 12, 16, 255)) * 4
        report = analyze_frame(scene, pixels, 2, 2, None, None, {"alive": 64, "drawn": 64, "enabled": True})
        self.assertEqual(report["schema"], 11)
        self.assertTrue(report["scene"]["sprites"]["enabled"])
        self.assertEqual(report["fx"], {"alive": 64, "drawn": 64, "enabled": True})

    def test_no_sprites_changes_report_hash(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((10, 12, 16, 255)) * 4
        enabled = analyze_frame(scene, pixels, 2, 2, None, None, {"alive": 64, "drawn": 64, "enabled": True})
        scene.sprite = SpriteSettings(enabled=False)
        disabled = analyze_frame(scene, pixels, 2, 2, None, None, {"alive": 64, "drawn": 0, "enabled": False})
        self.assertNotEqual(enabled["hash"], disabled["hash"])
        diff = compare_reports(enabled, disabled)
        self.assertFalse(diff["same_report"])
        self.assertFalse(diff["same_sprites"])
        self.assertFalse(diff["same_fx"])

    def test_compare_accepts_schema_9_baseline(self):
        scene = CubeDemo().build_scene()
        pixels = bytes((10, 12, 16, 255)) * 4
        current = analyze_frame(scene, pixels, 2, 2, None, None, {"alive": 0, "drawn": 0, "enabled": True})
        baseline = dict(current)
        baseline["schema"] = 9
        del baseline["scene"]["sprites"]
        del baseline["fx"]
        diff = compare_reports(baseline, current)
        self.assertTrue(diff["same_image"])
        self.assertEqual(diff["sprites"]["before"], {"enabled": True})

    def test_describe_reports_sprites_capability(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["sprites"])
        self.assertEqual(REPORT_SCHEMA["version"], 11)


class SpriteSampleTest(unittest.TestCase):
    def test_fountain_is_deterministic_and_outside_snapshot(self):
        first = CubeDemo()
        first.build_scene()
        second = CubeDemo()
        second.build_scene()
        for _ in range(5):
            first.update(1 / 60, type("Actions", (), {"forward": 0.0, "right": 0.0, "up": 0.0, "look_yaw": 0.0, "look_pitch": 0.0})())
            second.update(1 / 60, type("Actions", (), {"forward": 0.0, "right": 0.0, "up": 0.0, "look_yaw": 0.0, "look_pitch": 0.0})())
        self.assertEqual(len(first.particles.particles), len(second.particles.particles))
        self.assertGreater(len(first.particles.particles), 0)
        for one, two in zip(first.particles.particles, second.particles.particles):
            self.assertAlmostEqual(one.position.x, two.position.x)
            self.assertAlmostEqual(one.position.y, two.position.y)
        snapshot = first.snapshot()
        self.assertNotIn("particles", snapshot)
        self.assertIn("time", snapshot)


if __name__ == "__main__":
    unittest.main()
