"""Tests for the root-motion player."""

import math
import unittest

from keystone.animation import AnimationClip, Track
from keystone.math3d import Quat, Vec3
from keystone.plugin import describe_game
from keystone.root_motion import RootMotionPlayer
from keystone.samples import CubeDemo


def _walk() -> AnimationClip:
    return AnimationClip(
        name="walk",
        position_tracks=(
            ("root", Track(times=(0.0, 1.0), values=(Vec3(), Vec3(0.0, 0.0, 2.0)))),
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


class RootMotionPlayerTest(unittest.TestCase):
    def test_each_step_returns_its_own_delta(self):
        player = RootMotionPlayer(_walk(), "root", loop=False)
        motions = []
        for _ in range(4):
            pose, motion = player.advance(0.25)
            motions.append(motion)
        for motion in motions:
            self.assertAlmostEqual(motion.position.z, 0.5)
        self.assertAlmostEqual(pose["root"].position.z, 2.0)
        self.assertAlmostEqual(pose["arm"].position.y, 1.0)

    def test_a_loop_wrap_composes_the_tail_and_head(self):
        player = RootMotionPlayer(_walk(), "root")
        player.advance(0.9)
        pose, motion = player.advance(0.2)
        self.assertAlmostEqual(motion.position.z, 0.4)
        self.assertTrue(player.looped)
        self.assertAlmostEqual(pose["root"].position.z, 0.2)

    def test_multiple_wraps_count_full_cycles(self):
        player = RootMotionPlayer(_walk(), "root")
        player.advance(0.9)
        _pose, motion = player.advance(2.5)
        self.assertAlmostEqual(motion.position.z, 5.0)
        self.assertFalse(player.done)

    def test_rotation_wraps_compose(self):
        player = RootMotionPlayer(_turn(), "root")
        player.advance(0.9)
        _pose, motion = player.advance(0.2)
        self.assertAlmostEqual(motion.yaw, math.pi / 10.0, places=6)

    def test_non_looping_playback_clamps_and_reports_done(self):
        player = RootMotionPlayer(_walk(), "root", loop=False)
        pose, motion = player.advance(2.0)
        self.assertAlmostEqual(motion.position.z, 2.0)
        self.assertTrue(player.done)
        pose, motion = player.advance(1.0)
        self.assertEqual(motion.position, Vec3())
        self.assertTrue(player.done)
        self.assertAlmostEqual(pose["root"].position.z, 2.0)

    def test_planar_mode_drops_vertical_motion(self):
        clip = AnimationClip(
            name="hop",
            position_tracks=(("root", Track(times=(0.0, 1.0), values=(Vec3(), Vec3(1.0, 2.0, 0.0)))),),
        )
        player = RootMotionPlayer(clip, "root", planar=True)
        _pose, motion = player.advance(1.0)
        self.assertEqual(motion.position, Vec3(1.0, 0.0, 0.0))

    def test_speed_scales_clip_time(self):
        player = RootMotionPlayer(_walk(), "root", speed=2.0, loop=False)
        _pose, motion = player.advance(0.25)
        self.assertAlmostEqual(motion.position.z, 1.0)

    def test_reset_returns_to_the_start(self):
        player = RootMotionPlayer(_walk(), "root", loop=False)
        player.advance(0.5)
        player.reset()
        _pose, motion = player.advance(0.25)
        self.assertAlmostEqual(motion.position.z, 0.5)
        self.assertFalse(player.done)

    def test_validation(self):
        clip = _walk()
        with self.assertRaises(TypeError):
            RootMotionPlayer(object(), "root")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            RootMotionPlayer(clip, 3)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            RootMotionPlayer(clip, "missing")
        with self.assertRaises(ValueError):
            RootMotionPlayer(clip, "root", speed=0.0)
        with self.assertRaises(ValueError):
            RootMotionPlayer(clip, "root", speed=-1.0)
        with self.assertRaises(ValueError):
            RootMotionPlayer(clip, "root", speed=float("nan"))
        with self.assertRaises(TypeError):
            RootMotionPlayer(clip, "root", loop=1)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            RootMotionPlayer(clip, "root", planar=1)  # type: ignore[arg-type]
        player = RootMotionPlayer(clip, "root")
        with self.assertRaises(ValueError):
            player.advance(-0.1)
        with self.assertRaises(ValueError):
            player.advance(float("nan"))
        with self.assertRaises(ValueError):
            RootMotionPlayer(clip, "root").advance(1e9)

    def test_report_is_json_safe(self):
        player = RootMotionPlayer(_walk(), "root")
        _pose, motion = player.advance(0.5)
        report = player.report(motion)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["clip"], "walk")
        self.assertEqual(report["node"], "root")
        self.assertAlmostEqual(report["time"], 0.5)
        self.assertAlmostEqual(report["motion"]["position"][2], 1.0)

    def test_describe_advertises_the_player(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["root_motion_player"])


if __name__ == "__main__":
    unittest.main()
