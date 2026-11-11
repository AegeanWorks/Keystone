"""Tests for retargeting a clip onto another node id."""

import unittest

from keystone.animation import AnimationClip, AnimationController, Track
from keystone.math3d import Quat, Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _vec_track(first: Vec3, second: Vec3) -> Track:
    return Track(times=(0.0, 1.0), values=(first, second))


def _subject_clip() -> AnimationClip:
    return AnimationClip(
        name="spin",
        position_tracks=(("subject", _vec_track(Vec3(0.0, 0.0, 0.0), Vec3(0.0, 1.0, 0.0))),),
        rotation_tracks=(
            ("subject", Track(times=(0.0, 1.0), values=(Quat(), Quat.from_axis_angle(Vec3.UP, 1.0)))),
        ),
        scale_tracks=(("subject", _vec_track(Vec3(1.0, 1.0, 1.0), Vec3(2.0, 2.0, 2.0))),),
        events=((0.5, "mid"),),
    )


class ClipBindingTest(unittest.TestCase):
    def test_bind_moves_every_channel_to_the_target(self):
        bound = _subject_clip().bind({"subject": "enemy-07"})
        self.assertEqual(bound.node_ids(), ["enemy-07"])
        self.assertEqual([node_id for node_id, _ in bound.position_tracks], ["enemy-07"])
        self.assertEqual([node_id for node_id, _ in bound.rotation_tracks], ["enemy-07"])
        self.assertEqual([node_id for node_id, _ in bound.scale_tracks], ["enemy-07"])
        self.assertEqual(bound.events, _subject_clip().events)

    def test_bound_pose_keeps_the_sampled_values(self):
        clip = _subject_clip()
        bound = clip.bind({"subject": "enemy-07"})
        self.assertEqual(bound.sample(0.5), {"enemy-07": clip.sample(0.5)["subject"]})

    def test_bind_leaves_the_source_clip_untouched(self):
        clip = _subject_clip()
        clip.bind({"subject": "enemy-07"})
        self.assertEqual(clip.node_ids(), ["subject"])

    def test_unmapped_tracks_are_retained(self):
        clip = AnimationClip(
            name="mixed",
            position_tracks=(
                ("subject", _vec_track(Vec3(), Vec3(1.0, 0.0, 0.0))),
                ("prop", _vec_track(Vec3(), Vec3(0.0, 1.0, 0.0))),
            ),
        )
        bound = clip.bind({"subject": "enemy-03"})
        self.assertEqual(bound.node_ids(), ["enemy-03", "prop"])

    def test_bind_can_rename_the_clip(self):
        bound = _subject_clip().bind({"subject": "enemy-07"}, name="spin@enemy-07")
        self.assertEqual(bound.name, "spin@enemy-07")

    def test_a_binding_can_fill_a_controller_per_slot(self):
        controller = AnimationController()
        clip = _subject_clip()
        for slot in range(3):
            target = f"enemy-{slot:02d}"
            controller.add(clip.bind({"subject": target}, name=f"spin@{target}"))
        self.assertEqual(sorted(controller.clips), ["spin@enemy-00", "spin@enemy-01", "spin@enemy-02"])
        self.assertIn("enemy-01", controller.clips["spin@enemy-01"].sample(0.0))

    def test_unknown_source_names_the_ids_it_knows(self):
        with self.assertRaises(ValueError) as caught:
            _subject_clip().bind({"subjekt": "enemy-07"})
        message = str(caught.exception)
        self.assertIn("subjekt", message)
        self.assertIn("subject", message)

    def test_a_collision_with_a_retained_id_is_rejected(self):
        clip = AnimationClip(
            name="mixed",
            position_tracks=(
                ("subject", _vec_track(Vec3(), Vec3(1.0, 0.0, 0.0))),
                ("prop", _vec_track(Vec3(), Vec3(0.0, 1.0, 0.0))),
            ),
        )
        with self.assertRaises(ValueError):
            clip.bind({"subject": "prop"})

    def test_bind_rejects_malformed_input(self):
        clip = _subject_clip()
        with self.assertRaises(TypeError):
            clip.bind(["subject", "enemy-07"])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            clip.bind({"": "enemy-07"})
        with self.assertRaises(ValueError):
            clip.bind({"subject": " "})
        with self.assertRaises(ValueError):
            clip.bind({"subject": 7})  # type: ignore[dict-item]
        with self.assertRaises(ValueError):
            clip.bind({"subject": "enemy-07"}, name=" ")

    def test_describe_advertises_binding(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["animation_binding"])


if __name__ == "__main__":
    unittest.main()
