"""Tests for deterministic camera shake."""

import unittest

from keystone.camera_shake import CameraShake, ShakeOffset, shake_report
from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


class CameraShakeTest(unittest.TestCase):
    def test_no_trauma_produces_no_offset(self):
        shake = CameraShake()
        offset = shake.sample()
        self.assertEqual(offset.position, Vec3())
        self.assertEqual(offset.yaw, 0.0)
        self.assertEqual(offset.pitch, 0.0)

    def test_trauma_produces_a_deterministic_offset(self):
        first = CameraShake(seed=7)
        second = CameraShake(seed=7)
        first.add(0.8)
        second.add(0.8)
        self.assertEqual(first.sample(), second.sample())
        self.assertNotEqual(first.sample().position, Vec3())

    def test_seeds_diverge(self):
        left = CameraShake(seed=1)
        right = CameraShake(seed=2)
        left.add(1.0)
        right.add(1.0)
        self.assertNotEqual(left.sample(), right.sample())

    def test_trauma_is_clamped_and_decays(self):
        shake = CameraShake(decay=2.0)
        shake.add(5.0)
        self.assertEqual(shake.trauma, 1.0)
        shake.update(0.25)
        self.assertAlmostEqual(shake.trauma, 0.5)
        shake.update(0.5)
        self.assertEqual(shake.trauma, 0.0)
        self.assertEqual(shake.sample().position, Vec3())

    def test_amplitude_scales_the_offset(self):
        small = CameraShake(amplitude=0.1, rotation_amplitude=0.0)
        large = CameraShake(amplitude=2.0, rotation_amplitude=0.0)
        small.add(1.0)
        large.add(1.0)
        self.assertGreater(large.sample().position.length(), small.sample().position.length() * 10.0)

    def test_rotation_channels_move(self):
        shake = CameraShake(amplitude=0.0, rotation_amplitude=0.5)
        shake.add(1.0)
        offset = shake.sample()
        self.assertEqual(offset.position, Vec3())
        self.assertNotEqual((offset.yaw, offset.pitch), (0.0, 0.0))

    def test_reset_clears_the_state(self):
        shake = CameraShake()
        shake.add(1.0)
        shake.update(0.1)
        shake.reset()
        self.assertEqual(shake.trauma, 0.0)
        self.assertEqual(shake.elapsed, 0.0)

    def test_validation(self):
        with self.assertRaises(TypeError):
            CameraShake(seed=True)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            CameraShake(amplitude=-0.1)
        with self.assertRaises(ValueError):
            CameraShake(rotation_amplitude=-0.1)
        with self.assertRaises(ValueError):
            CameraShake(frequency=0.0)
        with self.assertRaises(ValueError):
            CameraShake(decay=0.0)
        shake = CameraShake()
        with self.assertRaises(ValueError):
            shake.add(-0.1)
        with self.assertRaises(ValueError):
            shake.add(float("nan"))
        with self.assertRaises(ValueError):
            shake.update(-0.1)
        with self.assertRaises(ValueError):
            shake.update(float("nan"))

    def test_report_is_json_safe(self):
        shake = CameraShake()
        shake.add(0.5)
        report = shake_report(shake)
        self.assertEqual(report["schema"], 1)
        self.assertAlmostEqual(report["trauma"], 0.5)
        self.assertEqual(len(report["position"]), 3)
        self.assertIn("yaw", report)
        self.assertIn("pitch", report)

    def test_report_rejects_other_objects(self):
        with self.assertRaises(TypeError):
            shake_report({"trauma": 1.0})  # type: ignore[arg-type]

    def test_offset_is_immutable(self):
        offset = ShakeOffset(Vec3(), 0.0, 0.0)
        with self.assertRaises(AttributeError):
            offset.yaw = 1.0  # type: ignore[misc]

    def test_describe_advertises_camera_shake(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["camera_shake"])


if __name__ == "__main__":
    unittest.main()
