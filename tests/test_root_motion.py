"""Tests for root-motion extraction and in-place pose baking."""

import math
import unittest

from keystone.animation import AnimationClip, Track
from keystone.math3d import Quat, Vec3
from keystone.plugin import describe_game
from keystone.root_motion import (
    RootMotion,
    extract_root_motion,
    in_place_pose,
    root_motion_report,
)
from keystone.samples import CubeDemo
from keystone.scene import Transform


def _clip(
    positions: tuple[Vec3, Vec3] = (Vec3(), Vec3(0.0, 0.0, 2.0)),
    rotations: tuple[Quat, Quat] | None = None,
) -> AnimationClip:
    kwargs = {
        "name": "walk",
        "position_tracks": (("root", Track(times=(0.0, 1.0), values=positions)),),
    }
    if rotations is not None:
        kwargs["rotation_tracks"] = (("root", Track(times=(0.0, 1.0), values=rotations)),)
    return AnimationClip(**kwargs)


class ExtractRootMotionTest(unittest.TestCase):
    def test_a_full_clip_reports_its_position_delta(self):
        motion = extract_root_motion(_clip(), "root", 0.0, 1.0)
        self.assertEqual(motion.position, Vec3(0.0, 0.0, 2.0))
        self.assertEqual(motion.rotation, Quat())

    def test_a_subrange_reports_part_of_the_delta(self):
        motion = extract_root_motion(_clip(), "root", 0.25, 0.75)
        self.assertAlmostEqual(motion.position.z, 1.0)

    def test_planar_mode_drops_vertical_motion(self):
        clip = _clip(positions=(Vec3(), Vec3(1.0, 2.0, 3.0)))
        motion = extract_root_motion(clip, "root", 0.0, 1.0, planar=True)
        self.assertEqual(motion.position, Vec3(1.0, 0.0, 3.0))

    def test_rotation_delta_and_yaw(self):
        turn = Quat.from_axis_angle(Vec3(0.0, 1.0, 0.0), math.pi / 2)
        motion = extract_root_motion(_clip(rotations=(Quat(), turn)), "root", 0.0, 1.0)
        self.assertAlmostEqual(motion.yaw, math.pi / 2, places=6)
        facing = motion.rotation.rotate(Vec3(0.0, 0.0, -1.0))
        self.assertAlmostEqual(facing.x, -1.0, places=6)

    def test_an_empty_interval_is_identity(self):
        motion = extract_root_motion(_clip(), "root", 0.5, 0.5)
        self.assertEqual(motion.position, Vec3())
        self.assertEqual(motion.rotation, Quat())

    def test_times_clamp_to_the_clip_duration(self):
        self.assertEqual(
            extract_root_motion(_clip(), "root", 0.0, 5.0),
            extract_root_motion(_clip(), "root", 0.0, 1.0),
        )

    def test_missing_nodes_and_bad_arguments_are_rejected(self):
        clip = _clip()
        with self.assertRaises(TypeError):
            extract_root_motion(object(), "root")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            extract_root_motion(clip, " ")
        with self.assertRaises(ValueError):
            extract_root_motion(clip, "missing")
        with self.assertRaises(ValueError):
            extract_root_motion(clip, "root", -1.0, 1.0)
        with self.assertRaises(ValueError):
            extract_root_motion(clip, "root", 0.5, 0.25)
        with self.assertRaises(ValueError):
            extract_root_motion(clip, "root", 0.0, float("nan"))
        with self.assertRaises(TypeError):
            extract_root_motion(clip, 3)  # type: ignore[arg-type]


class InPlacePoseTest(unittest.TestCase):
    def test_the_root_is_reset_and_the_original_is_untouched(self):
        pose = {
            "root": Transform(position=Vec3(4.0, 0.0, 9.0), rotation=Quat.from_axis_angle(Vec3(0.0, 1.0, 0.0), 1.0)),
            "arm": Transform(position=Vec3(0.0, 1.0, 0.0)),
        }
        in_place = in_place_pose(pose, "root")
        self.assertEqual(in_place["root"].position, Vec3())
        self.assertEqual(in_place["root"].rotation, Quat())
        self.assertEqual(in_place["root"].scale, Vec3(1.0, 1.0, 1.0))
        self.assertEqual(pose["root"].position, Vec3(4.0, 0.0, 9.0))
        self.assertIsNot(pose, in_place)
        self.assertEqual(in_place["arm"], pose["arm"])

    def test_a_reference_transform_is_honoured(self):
        pose = {"root": Transform(position=Vec3(1.0, 0.0, 0.0))}
        reference = Transform(position=Vec3(2.0, 3.0, 4.0), scale=Vec3(2.0, 2.0, 2.0))
        in_place = in_place_pose(pose, "root", reference)
        self.assertEqual(in_place["root"].position, Vec3(2.0, 3.0, 4.0))
        self.assertEqual(in_place["root"].scale, Vec3(2.0, 2.0, 2.0))

    def test_validation(self):
        with self.assertRaises(TypeError):
            in_place_pose(["root"], "root")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            in_place_pose({}, "root")
        with self.assertRaises(TypeError):
            in_place_pose({"root": Transform()}, "root", object())  # type: ignore[arg-type]


class RootMotionReportTest(unittest.TestCase):
    def test_report_is_json_safe(self):
        report = root_motion_report(extract_root_motion(_clip(), "root", 0.0, 1.0))
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["position"], [0.0, 0.0, 2.0])
        self.assertEqual(report["yaw"], 0.0)
        self.assertEqual(len(report["rotation"]), 4)

    def test_report_rejects_a_non_motion(self):
        with self.assertRaises(TypeError):
            root_motion_report({"position": [0, 0, 0]})  # type: ignore[arg-type]

    def test_motion_is_immutable(self):
        motion = RootMotion(Vec3(), Quat())
        with self.assertRaises(AttributeError):
            motion.position = Vec3(1.0, 0.0, 0.0)  # type: ignore[misc]

    def test_describe_advertises_root_motion(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["root_motion"])


if __name__ == "__main__":
    unittest.main()
