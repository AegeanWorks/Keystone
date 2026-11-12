"""Tests for composing camera shake with a base camera pose."""

import math
import unittest

from keystone.camera import PerspectiveCamera
from keystone.camera_shake import CameraShake
from keystone.camera_shaker import CameraShaker, camera_shaker_report
from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


class CameraShakerTest(unittest.TestCase):
    def test_zero_trauma_leaves_the_base_pose(self):
        base = PerspectiveCamera(position=Vec3(1.0, 2.0, 3.0), yaw=0.4, pitch=0.2)
        shaker = CameraShaker(base, CameraShake())
        pose = shaker.pose()
        self.assertEqual(pose.position, base.position)
        self.assertEqual(pose.yaw, base.yaw)
        self.assertEqual(pose.pitch, base.pitch)

    def test_the_base_camera_is_never_mutated(self):
        base = PerspectiveCamera(position=Vec3(1.0, 2.0, 3.0), yaw=0.4, pitch=0.2)
        shaker = CameraShaker(base, CameraShake())
        shaker.shake.add(1.0)
        shaker.update(0.1)
        shaker.pose()
        self.assertEqual(base.position, Vec3(1.0, 2.0, 3.0))
        self.assertEqual(base.yaw, 0.4)
        self.assertEqual(base.pitch, 0.2)

    def test_shake_offsets_appear_in_the_composed_pose(self):
        base = PerspectiveCamera()
        shaker = CameraShaker(base, CameraShake(amplitude=0.5, rotation_amplitude=0.2))
        shaker.shake.add(1.0)
        pose = shaker.pose()
        self.assertNotEqual(pose.position, Vec3())
        self.assertNotEqual((pose.yaw, pose.pitch), (0.0, 0.0))

    def test_camera_local_translation_follows_the_base_orientation(self):
        base = PerspectiveCamera(yaw=math.pi / 2)
        shaker = CameraShaker(base, CameraShake(rotation_amplitude=0.0))
        shaker.shake.trauma = 1.0
        shaker.shake.elapsed = 0.0
        # Force a known forward offset by sampling through the internal noise.
        pose = shaker.pose()
        self.assertEqual(pose.position, base.position + shaker.shake.sample().position)
        self.assertIsNot(pose.position, base.position)

    def test_local_mode_uses_the_camera_basis(self):
        base = PerspectiveCamera(yaw=math.pi / 2)
        shaker = CameraShaker(base, CameraShake(rotation_amplitude=0.0), local=True)
        shaker.shake.trauma = 1.0
        offset = shaker.shake.sample().position
        expected = base.position + base.right() * offset.x + base.up() * offset.y + base.forward() * offset.z
        self.assertLess((shaker.pose().position - expected).length(), 1e-9)

    def test_update_decays_and_pose_reflects_zero(self):
        base = PerspectiveCamera()
        shaker = CameraShaker(base, CameraShake(decay=4.0))
        shaker.shake.add(0.5)
        shaker.update(0.25)
        self.assertEqual(shaker.pose().position, Vec3())

    def test_report_is_json_safe(self):
        base = PerspectiveCamera(position=Vec3(1.0, 2.0, 3.0), yaw=0.5)
        shaker = CameraShaker(base, CameraShake())
        report = camera_shaker_report(shaker)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["base"]["position"], [1.0, 2.0, 3.0])
        self.assertEqual(report["pose"]["position"], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(report["pose"]["yaw"] % math.tau, 0.5, places=6)
        self.assertEqual(report["shake"]["trauma"], 0.0)
        shaker.shake.add(0.5)
        moved = camera_shaker_report(shaker)
        self.assertNotEqual(moved["pose"]["position"], moved["base"]["position"])
        self.assertIn("shake", report)

    def test_validation(self):
        base = PerspectiveCamera()
        with self.assertRaises(TypeError):
            CameraShaker(object(), CameraShake())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            CameraShaker(base, object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            CameraShaker(base, CameraShake(), local=1)  # type: ignore[arg-type]
        shaker = CameraShaker(base, CameraShake())
        with self.assertRaises(ValueError):
            shaker.update(-1.0)
        with self.assertRaises(TypeError):
            camera_shaker_report(object())  # type: ignore[arg-type]

    def test_describe_advertises_the_shaker(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["camera_shaker"])


if __name__ == "__main__":
    unittest.main()
