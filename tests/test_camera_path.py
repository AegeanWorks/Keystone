"""Tests for deterministic camera paths."""

import json
import math
import unittest

from keystone.camera import MAX_PITCH, PerspectiveCamera
from keystone.camera_path import (
    CameraKey,
    CameraPath,
    CameraPathPlayer,
    CameraPose,
    camera_key_from_dict,
    camera_path_player_report,
    camera_path_report,
    camera_path_to_dict,
    insert_camera_key,
    remove_camera_key,
)
from keystone.math3d import Quat, Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _line_path(**player_options) -> tuple[CameraPath, CameraPathPlayer]:
    path = CameraPath(
        [
            CameraKey(0.0, Vec3(0.0, 0.0, 0.0)),
            CameraKey(2.0, Vec3(2.0, 0.0, 0.0)),
        ]
    )
    return path, CameraPathPlayer(path, **player_options)


class CameraPathTest(unittest.TestCase):
    def test_sample_matches_the_endpoint_keys(self):
        path = CameraPath(
            [
                CameraKey(0.0, Vec3(0.0, 1.0, 2.0)),
                CameraKey(2.0, Vec3(2.0, 1.0, 0.0)),
            ]
        )
        self.assertEqual(path.duration, 2.0)
        self.assertEqual(path.sample(0.0).position, Vec3(0.0, 1.0, 2.0))
        self.assertEqual(path.sample(2.0).position, Vec3(2.0, 1.0, 0.0))

    def test_two_key_position_is_linear(self):
        path, _player = _line_path()
        self.assertEqual(path.sample(0.5).position, Vec3(0.5, 0.0, 0.0))
        self.assertEqual(path.sample(1.0).position, Vec3(1.0, 0.0, 0.0))
        self.assertEqual(path.sample(1.5).position, Vec3(1.5, 0.0, 0.0))

    def test_multi_key_position_uses_a_catmull_rom_spline(self):
        path = CameraPath(
            [
                CameraKey(0.0, Vec3(0.0, 0.0, 0.0)),
                CameraKey(1.0, Vec3(0.0, 0.0, 1.0)),
                CameraKey(2.0, Vec3(1.0, 0.0, 1.0)),
            ]
        )
        position = path.sample(0.5).position
        self.assertAlmostEqual(position.x, -0.0625)
        self.assertAlmostEqual(position.y, 0.0)
        self.assertAlmostEqual(position.z, 0.5625)

    def test_rotation_slerps_between_keys(self):
        path = CameraPath(
            [
                CameraKey(0.0, Vec3(), Quat()),
                CameraKey(1.0, Vec3(), Quat.from_axis_angle(Vec3.UP, -math.pi / 2.0)),
            ]
        )
        forward = path.sample(0.5).forward()
        self.assertAlmostEqual(forward.x, math.sqrt(0.5), places=6)
        self.assertAlmostEqual(forward.y, 0.0, places=6)
        self.assertAlmostEqual(forward.z, -math.sqrt(0.5), places=6)
        self.assertAlmostEqual(path.sample(0.5).yaw, math.pi / 4.0, places=6)

    def test_fov_interpolates_linearly(self):
        path = CameraPath(
            [
                CameraKey(0.0, Vec3(), fov_y=60.0),
                CameraKey(1.0, Vec3(), fov_y=90.0),
            ]
        )
        self.assertEqual(path.sample(0.25).fov_y, 67.5)
        self.assertEqual(path.sample(0.5).fov_y, 75.0)

    def test_open_path_clamps_after_the_duration(self):
        path, _player = _line_path()
        pose = path.sample(99.0)
        self.assertEqual(pose.position, Vec3(2.0, 0.0, 0.0))

    def test_loop_wraps_and_closes_the_seam(self):
        path = CameraPath(
            [
                CameraKey(0.0, Vec3(0.0, 0.0, 0.0)),
                CameraKey(1.0, Vec3(1.0, 0.0, 0.0)),
                CameraKey(2.0, Vec3(1.0, 0.0, 1.0)),
                CameraKey(3.0, Vec3(0.0, 0.0, 1.0)),
            ],
            loop=True,
            duration=4.0,
        )
        self.assertEqual(path.duration, 4.0)
        self.assertEqual(path.sample(4.25).position, path.sample(0.25).position)
        before = path.sample(4.0 - 1e-6).position
        start = path.sample(0.0).position
        self.assertLess((before - start).length(), 1e-4)

    def test_loop_seam_keeps_position_and_velocity_continuous(self):
        path = CameraPath(
            [
                CameraKey(0.0, Vec3(0.0, 0.0, 0.0)),
                CameraKey(1.0, Vec3(1.0, 0.0, 0.0)),
                CameraKey(2.0, Vec3(1.0, 0.0, 1.0)),
                CameraKey(3.0, Vec3(0.0, 0.0, 1.0)),
            ],
            loop=True,
            duration=4.0,
        )
        epsilon = 1e-5
        incoming = (
            path.sample(4.0 - epsilon).position
            - path.sample(4.0 - 2.0 * epsilon).position
        ) / epsilon
        outgoing = (
            path.sample(epsilon).position - path.sample(0.0).position
        ) / epsilon
        self.assertLess((incoming - outgoing).length(), 1e-3)

    def test_player_advances_and_clamps(self):
        _path, player = _line_path()
        self.assertEqual(player.advance(0.5).position, Vec3(0.5, 0.0, 0.0))
        self.assertFalse(player.done)
        self.assertEqual(player.advance(0.5).position, Vec3(1.0, 0.0, 0.0))
        self.assertFalse(player.done)
        self.assertEqual(player.advance(2.0).position, Vec3(2.0, 0.0, 0.0))
        self.assertTrue(player.done)
        self.assertEqual(player.time, 2.0)
        self.assertEqual(player.advance(1.0).position, Vec3(2.0, 0.0, 0.0))
        self.assertTrue(player.done)

    def test_player_speed_scales_time(self):
        _path, player = _line_path(speed=2.0)
        self.assertEqual(player.advance(0.25).position, Vec3(0.5, 0.0, 0.0))
        self.assertEqual(player.time, 0.5)

    def test_player_seek_clamps_or_wraps(self):
        _path, player = _line_path()
        self.assertEqual(player.seek(1.5).position, Vec3(1.5, 0.0, 0.0))
        self.assertFalse(player.done)
        self.assertEqual(player.seek(99.0).position, Vec3(2.0, 0.0, 0.0))
        self.assertTrue(player.done)
        looped = CameraPathPlayer(
            CameraPath(
                [
                    CameraKey(0.0, Vec3()),
                    CameraKey(2.0, Vec3(2.0, 0.0, 0.0)),
                ],
                loop=True,
                duration=3.0,
            )
        )
        self.assertEqual(looped.seek(3.5).position, looped.path.sample(0.5).position)
        self.assertEqual(looped.time, 0.5)
        self.assertFalse(looped.done)

    def test_player_loop_can_override_the_path(self):
        path, _player = _line_path()
        once = CameraPathPlayer(path, loop=True)
        self.assertEqual(once.advance(2.5).position, Vec3(0.5, 0.0, 0.0))
        self.assertFalse(once.done)
        closed = CameraPath(
            [
                CameraKey(0.0, Vec3()),
                CameraKey(2.0, Vec3(2.0, 0.0, 0.0)),
            ],
            loop=True,
            duration=3.0,
        )
        single = CameraPathPlayer(closed, loop=False)
        self.assertEqual(single.advance(2.5).position, closed.sample(2.5).position)
        self.assertFalse(single.done)
        self.assertEqual(single.advance(2.5).position, Vec3())
        self.assertTrue(single.done)

    def test_player_reset_rewinds_the_clock(self):
        _path, player = _line_path()
        player.advance(2.0)
        player.reset()
        self.assertEqual(player.time, 0.0)
        self.assertFalse(player.done)
        self.assertEqual(player.sample().position, Vec3(0.0, 0.0, 0.0))

    def test_pose_builds_a_camera_without_mutating_the_base(self):
        rotation = Quat.from_axis_angle(Vec3.UP, -math.pi / 2.0)
        pose = CameraPose(Vec3(1.0, 2.0, 3.0), rotation, fov_y=55.0)
        base = PerspectiveCamera(near=0.5, far=250.0)
        camera = pose.to_camera(base)
        self.assertEqual(camera.position, Vec3(1.0, 2.0, 3.0))
        self.assertEqual(camera.fov_y, 55.0)
        self.assertEqual((camera.near, camera.far), (0.5, 250.0))
        self.assertAlmostEqual(camera.yaw, pose.yaw)
        self.assertAlmostEqual(camera.pitch, pose.pitch)
        self.assertLess((camera.forward() - pose.forward()).length(), 1e-6)
        self.assertEqual(base.position, Vec3())
        self.assertEqual(base.fov_y, 60.0)
        plain = pose.to_camera()
        self.assertEqual((plain.near, plain.far), (0.1, 1000.0))

    def test_pose_rejects_a_bad_base_camera(self):
        pose = CameraPose(Vec3(), Quat())
        with self.assertRaises(TypeError):
            pose.to_camera(object())  # type: ignore[arg-type]

    def test_look_at_keys_aim_at_their_targets(self):
        key = CameraKey.look_at(0.0, Vec3(), Vec3(1.0, 1.0, 0.0))
        pose = CameraPose(key.position, key.rotation, key.fov_y)
        expected = Vec3(1.0, 1.0, 0.0).normalized()
        self.assertLess((pose.forward() - expected).length(), 1e-6)
        self.assertAlmostEqual(pose.yaw, math.pi / 2.0, places=6)
        self.assertAlmostEqual(pose.pitch, math.pi / 4.0, places=6)
        with self.assertRaises(ValueError):
            CameraKey.look_at(0.0, Vec3(1.0, 0.0, 0.0), Vec3(1.0, 0.0, 0.0))

    def test_keys_and_poses_are_immutable(self):
        key = CameraKey(0.0, Vec3())
        with self.assertRaises(AttributeError):
            key.time = 1.0  # type: ignore[misc]
        pose = CameraPose(Vec3(), Quat())
        with self.assertRaises(AttributeError):
            pose.fov_y = 30.0  # type: ignore[misc]

    def test_validation(self):
        with self.assertRaises(ValueError):
            CameraKey(-1.0, Vec3())
        with self.assertRaises(ValueError):
            CameraKey(float("nan"), Vec3())
        with self.assertRaises(TypeError):
            CameraKey(True, Vec3())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            CameraKey(0.0, (0.0, 0.0, 0.0))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            CameraKey(0.0, Vec3(float("inf"), 0.0, 0.0))
        with self.assertRaises(TypeError):
            CameraKey(0.0, Vec3(), (1, 0, 0, 0))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            CameraKey(0.0, Vec3(), Quat(0.0, 0.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            CameraKey(0.0, Vec3(), Quat(float("nan"), 0.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            CameraKey(0.0, Vec3(), fov_y=0.0)
        with self.assertRaises(ValueError):
            CameraKey(0.0, Vec3(), fov_y=180.0)
        with self.assertRaises(ValueError):
            CameraPath([])
        with self.assertRaises(TypeError):
            CameraPath(42)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            CameraPath([Vec3()])  # type: ignore[list-item]
        with self.assertRaises(ValueError):
            CameraPath([CameraKey(1.0, Vec3())])
        with self.assertRaises(ValueError):
            CameraPath([CameraKey(0.0, Vec3()), CameraKey(0.0, Vec3())])
        with self.assertRaises(ValueError):
            CameraPath([CameraKey(0.0, Vec3()), CameraKey(2.0, Vec3()), CameraKey(1.0, Vec3())])
        with self.assertRaises(ValueError):
            CameraPath([CameraKey(0.0, Vec3())], loop=True)
        with self.assertRaises(ValueError):
            CameraPath(
                [CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))],
                loop=True,
            )
        with self.assertRaises(ValueError):
            CameraPath(
                [CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))],
                loop=True,
                duration=1.0,
            )
        with self.assertRaises(ValueError):
            CameraPath(
                [CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))],
                loop=True,
                duration=0.5,
            )
        with self.assertRaises(TypeError):
            CameraPath(
                [CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))],
                loop=True,
                duration=True,
            )
        with self.assertRaises(ValueError):
            CameraPath(
                [CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))],
                duration=2.0,
            )
        path = CameraPath([CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))])
        with self.assertRaises(ValueError):
            path.sample(-0.1)
        with self.assertRaises(TypeError):
            CameraPathPlayer(object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            CameraPathPlayer(path, loop=1)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            CameraPathPlayer(path, speed=0.0)
        with self.assertRaises(ValueError):
            CameraPathPlayer(path, speed=-1.0)
        with self.assertRaises(ValueError):
            CameraPathPlayer(path, speed=float("nan"))
        player = CameraPathPlayer(path)
        with self.assertRaises(ValueError):
            player.advance(-0.1)
        with self.assertRaises(ValueError):
            player.advance(float("nan"))
        with self.assertRaises(ValueError):
            player.seek(-0.1)
        with self.assertRaises(TypeError):
            CameraPose((0.0, 0.0, 0.0), Quat())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            CameraPose(Vec3(), Quat(), fov_y=200.0)

    def test_reports_are_json_safe(self):
        path, player = _line_path()
        player.advance(0.5)
        path_report = camera_path_report(path)
        self.assertEqual(path_report["schema"], 1)
        self.assertEqual(path_report["duration"], 2.0)
        self.assertFalse(path_report["loop"])
        self.assertEqual([key["time"] for key in path_report["keys"]], [0.0, 2.0])
        self.assertEqual(path_report["keys"][0]["rotation"], [1.0, 0.0, 0.0, 0.0])
        player_report = camera_path_player_report(player)
        self.assertEqual(player_report["schema"], 1)
        self.assertEqual(player_report["time"], 0.5)
        self.assertFalse(player_report["done"])
        self.assertEqual(player_report["pose"]["position"], [0.5, 0.0, 0.0])
        self.assertEqual(player_report["path"]["duration"], 2.0)
        json.dumps(path_report)
        json.dumps(player_report)
        with self.assertRaises(TypeError):
            camera_path_report(player)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            camera_path_player_report(path)  # type: ignore[arg-type]

    def test_reports_are_deterministic(self):
        _path, first = _line_path()
        _other, second = _line_path()
        for _step in range(4):
            self.assertEqual(first.advance(0.25), second.advance(0.25))
        self.assertEqual(
            camera_path_player_report(first), camera_path_player_report(second)
        )

    def test_discovery_advertises_camera_paths(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["camera_path"])
        self.assertTrue(capabilities["camera_path_player"])
        self.assertTrue(capabilities["camera_pose_blend"])


if __name__ == "__main__":
    unittest.main()


class CameraKeyEditingTest(unittest.TestCase):
    def test_from_camera_round_trips_heading_and_lens(self):
        for yaw in (0.0, 0.5, -1.2, 2.9):
            for pitch in (-0.4, 0.0, 0.35):
                with self.subTest(yaw=yaw, pitch=pitch):
                    camera = PerspectiveCamera(
                        position=Vec3(1.0, 2.0, 3.0),
                        yaw=yaw,
                        pitch=pitch,
                        fov_y=55.0,
                    )
                    key = CameraKey.from_camera(0.0, camera)
                    pose = CameraPose(key.position, key.rotation)
                    self.assertEqual(key.position, Vec3(1.0, 2.0, 3.0))
                    self.assertEqual(key.fov_y, 55.0)
                    self.assertAlmostEqual(
                        math.atan2(math.sin(pose.yaw - yaw), math.cos(pose.yaw - yaw)),
                        0.0,
                        places=6,
                    )
                    self.assertAlmostEqual(pose.pitch, pitch, places=6)
                    self.assertLess(
                        (pose.forward() - camera.forward()).length(), 1e-6
                    )

    def test_from_view_clamps_pitch_like_a_camera(self):
        key = CameraKey.from_view(0.0, Vec3(), 0.0, 10.0)
        self.assertAlmostEqual(CameraPose(key.position, key.rotation).pitch, MAX_PITCH)
        falling = CameraKey.from_view(0.0, Vec3(), 0.0, -10.0)
        self.assertAlmostEqual(
            CameraPose(falling.position, falling.rotation).pitch, -MAX_PITCH
        )

    def test_from_camera_rejects_other_objects(self):
        with self.assertRaises(TypeError):
            CameraKey.from_camera(0.0, object())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            CameraKey.from_view(0.0, Vec3(), float("nan"), 0.0)
        with self.assertRaises(TypeError):
            CameraKey.from_view(0.0, (0.0, 0.0, 0.0), 0.0, 0.0)  # type: ignore[arg-type]

    def test_insert_starts_a_one_shot_path(self):
        created, replaced = insert_camera_key(None, CameraKey(0.0, Vec3(1.0, 0.0, 0.0)))
        self.assertFalse(replaced)
        self.assertEqual(len(created.keys), 1)
        self.assertFalse(created.loop)
        self.assertEqual(created.duration, 0.0)
        with self.assertRaises(ValueError):
            insert_camera_key(None, CameraKey(1.0, Vec3()))

    def test_insert_sorts_keys_and_replaces_near_duplicates(self):
        path = CameraPath(
            [
                CameraKey(0.0, Vec3()),
                CameraKey(2.0, Vec3(2.0, 0.0, 0.0)),
            ]
        )
        grown, replaced = insert_camera_key(path, CameraKey(1.0, Vec3(1.0, 0.0, 0.0)))
        self.assertFalse(replaced)
        self.assertEqual([key.time for key in grown.keys], [0.0, 1.0, 2.0])
        hits, replaced = insert_camera_key(
            grown, CameraKey(1.0 + 1e-9, Vec3(5.0, 0.0, 0.0))
        )
        self.assertTrue(replaced)
        self.assertEqual(len(hits.keys), 3)
        self.assertEqual(hits.keys[1].time, 1.0)
        self.assertEqual(hits.keys[1].position, Vec3(5.0, 0.0, 0.0))

    def test_insert_replacing_the_anchor_keeps_time_zero(self):
        path = CameraPath([CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))])
        updated, replaced = insert_camera_key(
            path, CameraKey(1e-9, Vec3(3.0, 0.0, 0.0))
        )
        self.assertTrue(replaced)
        self.assertEqual(updated.keys[0].time, 0.0)
        self.assertEqual(updated.keys[0].position, Vec3(3.0, 0.0, 0.0))

    def test_insert_respects_a_loop_duration(self):
        loop = CameraPath(
            [CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))],
            loop=True,
            duration=3.0,
        )
        grown, replaced = insert_camera_key(loop, CameraKey(2.0, Vec3(2.0, 0.0, 0.0)))
        self.assertFalse(replaced)
        self.assertEqual(grown.duration, 3.0)
        self.assertTrue(grown.loop)
        with self.assertRaises(ValueError):
            insert_camera_key(loop, CameraKey(3.0, Vec3()))
        with self.assertRaises(ValueError):
            insert_camera_key(loop, CameraKey(4.0, Vec3()))

    def test_insert_validates_inputs(self):
        path = CameraPath([CameraKey(0.0, Vec3())])
        with self.assertRaises(TypeError):
            insert_camera_key(object(), CameraKey(0.0, Vec3()))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            insert_camera_key(path, object())  # type: ignore[arg-type]
        for epsilon in (0.0, -1.0, float("nan"), True):
            with self.subTest(epsilon=epsilon), self.assertRaises((TypeError, ValueError)):
                insert_camera_key(path, CameraKey(1.0, Vec3()), epsilon=epsilon)

    def test_remove_deletes_by_time_and_keeps_constraints(self):
        path = CameraPath(
            [
                CameraKey(0.0, Vec3()),
                CameraKey(1.0, Vec3(1.0, 0.0, 0.0)),
                CameraKey(3.0, Vec3(3.0, 0.0, 0.0)),
            ]
        )
        trimmed, removed = remove_camera_key(path, 1.0 + 1e-9)
        self.assertEqual(removed, 1)
        self.assertEqual([key.time for key in trimmed.keys], [0.0, 3.0])
        self.assertEqual(trimmed.duration, 3.0)
        last, removed = remove_camera_key(trimmed, 3.0)
        self.assertEqual(removed, 1)
        self.assertEqual(last.duration, 0.0)
        same, removed = remove_camera_key(last, 5.0)
        self.assertEqual(removed, 0)
        self.assertEqual(same.keys, last.keys)

    def test_remove_refuses_to_unanchor_or_empty_a_path(self):
        path = CameraPath([CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))])
        with self.assertRaises(ValueError):
            remove_camera_key(path, 0.0)
        single = CameraPath([CameraKey(0.0, Vec3())])
        with self.assertRaises(ValueError):
            remove_camera_key(single, 0.0)

    def test_remove_keeps_loop_shape(self):
        loop = CameraPath(
            [CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0)), CameraKey(2.0, Vec3())],
            loop=True,
            duration=4.0,
        )
        trimmed, removed = remove_camera_key(loop, 1.0)
        self.assertEqual(removed, 1)
        self.assertTrue(trimmed.loop)
        self.assertEqual(trimmed.duration, 4.0)
        self.assertEqual([key.time for key in trimmed.keys], [0.0, 2.0])

    def test_remove_validates_inputs(self):
        path = CameraPath([CameraKey(0.0, Vec3()), CameraKey(1.0, Vec3(1.0, 0.0, 0.0))])
        with self.assertRaises(TypeError):
            remove_camera_key(object(), 0.0)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            remove_camera_key(path, -1.0)
        with self.assertRaises(ValueError):
            remove_camera_key(path, float("nan"))
        with self.assertRaises(ValueError):
            remove_camera_key(path, 1.0, epsilon=0.0)

    def test_key_document_round_trips_through_the_parser(self):
        key = CameraKey.from_view(0.0, Vec3(1.0, 2.0, 3.0), 0.7, 0.2, fov_y=42.0)
        document = camera_path_to_dict(CameraPath([key]))["keys"][0]
        self.assertEqual(camera_key_from_dict(document), key)
        with self.assertRaises(ValueError):
            camera_key_from_dict({"time": 0.0})
        with self.assertRaises(ValueError):
            camera_key_from_dict({"position": [0.0, 0.0, 0.0]})
        with self.assertRaises(ValueError):
            camera_key_from_dict({"time": 0.0, "position": [0.0, 0.0, 0.0], "yaw": 0.0})
        with self.assertRaises(TypeError):
            camera_key_from_dict([])  # type: ignore[arg-type]


class CameraPoseBlendTest(unittest.TestCase):
    def _pose(self, yaw: float = 0.0, fov_y: float = 60.0) -> CameraPose:
        rotation = Quat.from_axis_angle(Vec3.UP, -yaw)
        return CameraPose(Vec3(2.0, 1.5, 0.0), rotation, fov_y)

    def test_blend_endpoints_return_each_pose(self):
        start = self._pose()
        end = CameraPose(
            Vec3(6.0, 3.5, 4.0),
            Quat.from_axis_angle(Vec3.UP, -math.pi / 2.0),
            90.0,
        )
        self.assertEqual(start.blend(end, 0.0), start)
        self.assertEqual(start.blend(end, 1.0), end)

    def test_blend_midpoint_lerps_position_and_lens_and_slerps_heading(self):
        start = self._pose()
        end = CameraPose(
            Vec3(6.0, 3.5, 4.0),
            Quat.from_axis_angle(Vec3.UP, -math.pi / 2.0),
            90.0,
        )
        middle = start.blend(end, 0.5)
        self.assertEqual(middle.position, Vec3(4.0, 2.5, 2.0))
        self.assertEqual(middle.fov_y, 75.0)
        self.assertAlmostEqual(middle.yaw, math.pi / 4.0, places=6)
        self.assertAlmostEqual(middle.pitch, 0.0, places=6)
        forward = middle.forward()
        self.assertAlmostEqual(forward.x, math.sqrt(0.5), places=6)
        self.assertAlmostEqual(forward.z, -math.sqrt(0.5), places=6)

    def test_blend_takes_the_shortest_arc_for_mirrored_quaternions(self):
        start = self._pose()
        mirrored = Quat(-1.0, 0.0, 0.0, 0.0)
        target = CameraPose(start.position, mirrored, start.fov_y)
        halfway = start.blend(target, 0.5)
        self.assertLess((halfway.forward() - start.forward()).length(), 1e-9)
        self.assertEqual(halfway.position, start.position)

    def test_blend_validates_its_arguments(self):
        pose = self._pose()
        with self.assertRaises(TypeError):
            pose.blend(object(), 0.5)  # type: ignore[arg-type]
        for factor in (-0.1, 1.1, float("nan"), float("inf")):
            with self.subTest(factor=factor), self.assertRaises(ValueError):
                pose.blend(pose, factor)
        with self.assertRaises(TypeError):
            pose.blend(pose, True)  # type: ignore[arg-type]

    def test_blend_composes_with_a_camera_and_stays_immutable(self):
        start = self._pose()
        end = self._pose(math.pi / 2.0, 90.0)
        base = start.to_camera()
        blended = start.blend(end, 0.25).to_camera(base)
        self.assertEqual((blended.near, blended.far), (base.near, base.far))
        self.assertEqual(start.position, Vec3(2.0, 1.5, 0.0))
        self.assertEqual(start.fov_y, 60.0)
        self.assertEqual(start.rotation, Quat())
