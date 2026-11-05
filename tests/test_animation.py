"""Tests for deterministic animation clips, controllers and pose application."""

import unittest

from keystone.animation import (
    AnimationClip,
    AnimationController,
    Track,
    animation_report,
    apply_pose,
    blend_poses,
)
from keystone.batch import merge_batches
from keystone.geometry import Material
from keystone.math3d import Quat, Vec3
from keystone.primitives import cube
from keystone.scene import Node, Scene, Transform


def _vec_track(pairs: list[tuple[float, Vec3]]) -> Track:
    return Track(times=tuple(t for t, _ in pairs), values=tuple(v for _, v in pairs))


class TrackTest(unittest.TestCase):
    def test_linear_interpolation(self):
        track = _vec_track([(0.0, Vec3(0.0, 0.0, 0.0)), (1.0, Vec3(2.0, 0.0, 0.0))])
        mid = track.sample(0.5)
        assert isinstance(mid, Vec3)
        self.assertAlmostEqual(mid.x, 1.0)
        self.assertEqual(track.sample(-1.0), Vec3(0.0, 0.0, 0.0))
        self.assertEqual(track.sample(5.0), Vec3(2.0, 0.0, 0.0))

    def test_step_interpolation(self):
        track = Track(times=(0.0, 1.0), values=(Vec3(1.0, 0.0, 0.0), Vec3(9.0, 0.0, 0.0)), interpolation="step")
        self.assertEqual(track.sample(0.5), Vec3(1.0, 0.0, 0.0))
        self.assertEqual(track.sample(1.0), Vec3(9.0, 0.0, 0.0))

    def test_validation(self):
        with self.assertRaises(ValueError):
            Track(times=(1.0, 0.0), values=(Vec3(), Vec3()))
        with self.assertRaises(ValueError):
            Track(times=(), values=())
        with self.assertRaises(TypeError):
            Track(times=(0.0,), values=(object(),))
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                Track(times=(bad,), values=(Vec3(),))

    def test_quat_slerp_endpoints(self):
        first, second = Quat(), Quat.from_axis_angle(Vec3(0.0, 1.0, 0.0), 3.14159)
        track = Track(times=(0.0, 1.0), values=(first, second))
        self.assertEqual(track.sample(0.0), first)
        self.assertEqual(track.sample(1.0), second)

    def test_json_round_trip(self):
        track = _vec_track([(0.0, Vec3(1.0, 2.0, 3.0)), (0.5, Vec3(4.0, 5.0, 6.0))])
        restored = Track.from_dict(track.to_dict())
        self.assertEqual(restored.times, track.times)
        self.assertEqual(restored.values, track.values)


class ClipControllerTest(unittest.TestCase):
    def _clip(self) -> AnimationClip:
        return AnimationClip(
            name="bob",
            position_tracks=(("cube", _vec_track([(0.0, Vec3(0.0, 0.0, 0.0)), (1.0, Vec3(0.0, 2.0, 0.0))])),),
        )

    def test_clip_sample_and_duration(self):
        clip = self._clip()
        self.assertAlmostEqual(clip.duration(), 1.0)
        pose = clip.sample(0.5)
        self.assertAlmostEqual(pose["cube"].position.y, 1.0)
        restored = AnimationClip.from_dict(clip.to_dict())
        self.assertEqual(restored.name, "bob")
        self.assertAlmostEqual(restored.duration(), 1.0)

    def test_controller_loops_and_applies(self):
        controller = AnimationController()
        controller.add(self._clip())
        controller.play("bob")
        pose = controller.advance(0.5)
        self.assertAlmostEqual(pose["cube"].position.y, 1.0)
        pose = controller.advance(0.75)
        self.assertAlmostEqual(pose["cube"].position.y, 0.5)
        with self.assertRaises(ValueError):
            controller.advance(-0.1)
        scene = Scene()
        scene.add(Node("cube", id="cube", mesh=cube(1.0)))
        updated = apply_pose(scene, controller.clips["bob"].sample(1.0))
        self.assertEqual(updated, ["cube"])
        node = scene.find_by_id("cube")
        assert node is not None
        self.assertAlmostEqual(node.transform.position.y, 2.0)
        report = animation_report(controller)
        self.assertEqual(report["current"], "bob")
        self.assertEqual(report["clips"], ["bob"])

    def test_zero_time_event_fires_on_first_advance_only(self):
        clip = AnimationClip(name="fx", events=((0.0, "start"), (1.0, "end")))
        controller = AnimationController()
        controller.add(clip)
        controller.play("fx")
        _, fired = controller.advance_with_events(0.25)
        self.assertEqual(fired, ["start"])
        _, fired = controller.advance_with_events(0.0)
        self.assertEqual(fired, [])
        _, fired = controller.advance_with_events(0.25)
        self.assertEqual(fired, [])

    def test_crossfade_from_empty_clip_completes(self):
        empty = AnimationClip(name="empty")
        target = AnimationClip(
            name="target",
            position_tracks=(("cube", _vec_track([(0.0, Vec3(4.0, 0.0, 0.0)), (1.0, Vec3(4.0, 0.0, 0.0))])),),
        )
        controller = AnimationController(loop=False)
        controller.add(empty)
        controller.add(target)
        controller.play("empty")
        controller.crossfade("target", 1.0)
        self.assertTrue(controller.blending)
        pose = controller.advance(1.0)
        self.assertFalse(controller.blending)
        self.assertAlmostEqual(pose["cube"].position.x, 4.0)

    def test_unknown_clip_rejected(self):
        controller = AnimationController()
        with self.assertRaises(KeyError):
            controller.play("missing")

    def test_events_fire_once_per_crossing(self):
        clip = AnimationClip(name="fx", events=((0.5, "hit"), (1.0, "end")))
        controller = AnimationController()
        controller.add(clip)
        controller.play("fx")
        _, fired = controller.advance_with_events(0.25)
        self.assertEqual(fired, [])
        _, fired = controller.advance_with_events(0.5)
        self.assertEqual(fired, ["hit"])
        restored = AnimationClip.from_dict(clip.to_dict())
        self.assertEqual(restored.events, clip.events)
        with self.assertRaises(ValueError):
            AnimationClip(name="bad", events=((-0.1, "x"),))

    def test_crossfade_blends_deterministically(self):
        first = AnimationClip(
            name="a",
            position_tracks=(("cube", _vec_track([(0.0, Vec3(0.0, 0.0, 0.0)), (1.0, Vec3(0.0, 0.0, 0.0))])),),
        )
        second = AnimationClip(
            name="b",
            position_tracks=(("cube", _vec_track([(0.0, Vec3(10.0, 0.0, 0.0)), (1.0, Vec3(10.0, 0.0, 0.0))])),),
        )
        controller = AnimationController(loop=False)
        controller.add(first)
        controller.add(second)
        controller.play("a")
        controller.crossfade("b", 1.0)
        pose, _ = controller.advance_with_events(0.5)
        self.assertAlmostEqual(pose["cube"].position.x, 5.0)
        self.assertTrue(controller.blending)
        pose = controller.advance(0.5)
        self.assertAlmostEqual(pose["cube"].position.x, 10.0)
        self.assertFalse(controller.blending)
        blended = blend_poses({"n": Transform(position=Vec3(0, 0, 0))}, {"n": Transform(position=Vec3(4, 0, 0))}, 0.25)
        self.assertAlmostEqual(blended["n"].position.x, 1.0)


class MergeTest(unittest.TestCase):
    def test_merge_bakes_static_groups(self):
        scene = Scene()
        mesh = cube(1.0)
        material = Material(color=Vec3(1.0, 0.0, 0.0))
        for index in range(3):
            scene.add(Node(f"b-{index}", id=f"b-{index}",
                           transform=Transform(position=Vec3(float(index) * 2.0, 0.0, 0.0)),
                           mesh=mesh, material=material))
        result = merge_batches(scene)
        self.assertEqual(result["groups"], 1)
        self.assertEqual(result["merged_calls"], 1)
        self.assertEqual(result["saved_calls"], 2)
        self.assertEqual(result["merged"][0]["triangles"], mesh.triangle_count() * 3)

    def test_merge_excludes_animated_nodes(self):
        scene = Scene()
        mesh = cube(1.0)
        material = Material()
        scene.add(Node("still", id="still", mesh=mesh, material=material))
        scene.add(Node("hero", id="hero", mesh=mesh, material=material))
        result = merge_batches(scene, exclude={"hero"})
        self.assertEqual(result["merged"][0]["nodes"], ["still"])


class ClipDurationTest(unittest.TestCase):
    def test_duration_ignores_far_event_when_tracks_exist(self):
        from keystone.animation import Track
        track = Track(times=(0.0, 1.0), values=(Vec3(0, 0, 0), Vec3(1, 0, 0)))
        clip = AnimationClip(
            name="b",
            position_tracks=(("x", track),),
            events=((10.0, "far"),),
        )
        self.assertEqual(clip.duration(), 1.0)

    def test_event_only_clip_keeps_event_duration(self):
        clip = AnimationClip(name="fx", events=((0.5, "hit"), (1.0, "end")))
        self.assertEqual(clip.duration(), 1.0)

    def test_duplicate_keyframe_times_rejected(self):
        with self.assertRaises(ValueError):
            Track(times=(0.0, 0.0), values=(Vec3(0, 0, 0), Vec3(9, 0, 0)))


if __name__ == "__main__":
    unittest.main()
