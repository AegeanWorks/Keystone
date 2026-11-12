"""Tests for driving a character body from a root-motion clip."""

import math
import unittest

from keystone.animation import AnimationClip, Track
from keystone.character import CharacterBody, CharacterController
from keystone.math3d import Quat, Vec3
from keystone.physics import AABB
from keystone.plugin import describe_game
from keystone.root_motion_body import RootMotionBody, root_motion_body_report
from keystone.samples import CubeDemo


def _walk(units: float = 2.0) -> AnimationClip:
    return AnimationClip(
        name="walk",
        position_tracks=(
            ("root", Track(times=(0.0, 1.0), values=(Vec3(), Vec3(0.0, 0.0, units)))),
            ("arm", Track(times=(0.0, 1.0), values=(Vec3(), Vec3(0.0, 1.0, 0.0)))),
        ),
    )


def _turn() -> AnimationClip:
    return AnimationClip(
        name="turn",
        rotation_tracks=(
            ("root", Track(times=(0.0, 1.0), values=(Quat(), Quat.from_axis_angle(Vec3(0.0, 1.0, 0.0), math.pi / 2)))),
        ),
    )


def _rig(clip=None, **kwargs) -> RootMotionBody:
    return RootMotionBody(
        clip or _walk(),
        "root",
        CharacterController(gravity=0.0),
        CharacterBody(position=Vec3()),
        **kwargs,
    )


class RootMotionBodyTest(unittest.TestCase):
    def test_a_forward_clip_moves_the_body_at_clip_speed(self):
        rig = _rig()
        pose, motion = rig.step(0.5)
        self.assertAlmostEqual(rig.body.position.z, 1.0)
        self.assertAlmostEqual(motion.position.z, 1.0)
        self.assertEqual(pose["root"].position, Vec3())
        self.assertAlmostEqual(pose["arm"].position.y, 0.5)

    def test_steps_compose_across_loop_wraps(self):
        rig = _rig()
        for _ in range(4):
            rig.step(0.5)
        self.assertAlmostEqual(rig.body.position.z, 4.0)
        self.assertTrue(rig.player.looped)

    def test_turning_accumulates_yaw(self):
        rig = _rig(_turn())
        for _ in range(4):
            rig.step(0.25)
        self.assertAlmostEqual(rig.yaw, math.pi / 2, places=6)
        self.assertAlmostEqual(rig.body.position.z, 0.0)

    def test_a_wall_blocks_the_body_without_teleporting(self):
        rig = _rig()
        wall = AABB(Vec3(0.0, 0.0, 1.5), Vec3(1.0, 1.0, 0.5))
        for _ in range(20):
            rig.step(0.25, [wall])
        self.assertLess(rig.body.position.z, 1.0)
        self.assertGreater(rig.body.position.z, 0.0)

    def test_in_place_pose_keeps_the_root_clamped(self):
        rig = _rig()
        pose, _motion = rig.step(0.5)
        self.assertEqual(pose["root"].position, Vec3())
        self.assertEqual(pose["root"].rotation, Quat())
        self.assertEqual(pose["arm"].position.y, 0.5)

    def test_non_loop_playback_finishes(self):
        rig = _rig(loop=False)
        rig.step(1.0)
        self.assertTrue(rig.done)
        _pose, motion = rig.step(1.0)
        self.assertEqual(motion.position, Vec3())
        self.assertAlmostEqual(rig.body.position.z, 2.0)

    def test_planar_mode_ignores_vertical_root_motion(self):
        clip = AnimationClip(
            name="hop",
            position_tracks=(("root", Track(times=(0.0, 1.0), values=(Vec3(), Vec3(1.0, 3.0, 0.0)))),),
        )
        rig = _rig(clip, planar=True)
        rig.step(1.0)
        self.assertAlmostEqual(rig.body.position.x, 1.0)
        self.assertAlmostEqual(rig.body.position.y, 0.0)

    def test_reset_rewinds_the_rig(self):
        rig = _rig(loop=False)
        rig.step(0.5)
        rig.reset()
        self.assertEqual(rig.yaw, 0.0)
        self.assertFalse(rig.done)

    def test_report_is_json_safe(self):
        rig = _rig()
        rig.step(0.5)
        report = root_motion_body_report(rig)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["clip"], "walk")
        self.assertEqual(report["node"], "root")
        self.assertAlmostEqual(report["position"][2], 1.0)
        self.assertAlmostEqual(report["yaw"], 0.0)
        self.assertIn("motion", report)

    def test_validation(self):
        with self.assertRaises(TypeError):
            RootMotionBody(object(), "root", CharacterController(), CharacterBody())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            RootMotionBody(_walk(), "root", object(), CharacterBody())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            RootMotionBody(_walk(), "root", CharacterController(), object())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            RootMotionBody(_walk(), "missing", CharacterController(), CharacterBody(position=Vec3()))
        rig = _rig()
        with self.assertRaises(ValueError):
            rig.step(0.0)
        with self.assertRaises(ValueError):
            rig.step(-0.1)
        with self.assertRaises(TypeError):
            rig.step("soon")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            rig.step(1.0, [object()])  # type: ignore[list-item]
        with self.assertRaises(TypeError):
            root_motion_body_report(object())  # type: ignore[arg-type]

    def test_describe_advertises_root_motion_bodies(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["root_motion_body"])


if __name__ == "__main__":
    unittest.main()
