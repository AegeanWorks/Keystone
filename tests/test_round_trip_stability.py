"""Regression: a document must not change after one load/save cycle."""

import json
import unittest
from dataclasses import dataclass

from keystone.animation import AnimationClip, Track
from keystone.math3d import Quat, Vec3
from keystone.scene import Node, Scene, Transform
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


@dataclass(frozen=True)
class Health:
    value: int = 100


def _document(value):
    return json.dumps(value, sort_keys=True)


class RoundTripStabilityTest(unittest.TestCase):
    """Vec3/Quat accept ints, so serializers must normalize them to floats.

    Without that, a document written before a load differs textually from the
    same document written after it, which breaks hash and diff comparisons.
    """

    def test_scene_snapshot_is_stable_across_one_load(self):
        scene = Scene()
        node = scene.add(Node("n", id="n"))
        node.transform = Transform(
            position=Vec3(1, 2, 3), scale=Vec3(2, 2, 2)
        )
        first = scene_to_dict(scene)
        second = scene_to_dict(scene_from_dict(first))
        self.assertEqual(_document(first), _document(second))

    def test_scene_snapshot_lights_are_stable(self):
        from keystone.scene import DirectionalLight, PointLight

        scene = Scene()
        scene.light = DirectionalLight(direction=Vec3(-1, -1, 0))
        scene.point_light = PointLight(position=Vec3(3, 4, 2))
        first = scene_to_dict(scene)
        second = scene_to_dict(scene_from_dict(first))
        self.assertEqual(_document(first), _document(second))

    def test_animation_clip_is_stable_across_one_load(self):
        clip = AnimationClip(
            name="c",
            position_tracks=(
                ("n", Track(times=(0.0, 1.0), values=(Vec3(0, 0, 0), Vec3(1, 2, 3)))),
            ),
            rotation_tracks=(
                ("n", Track(times=(0.0, 1.0), values=(Quat(1, 0, 0, 0), Quat(1, 0, 0, 0)))),
            ),
        )
        first = clip.to_dict()
        second = AnimationClip.from_dict(json.loads(json.dumps(first))).to_dict()
        self.assertEqual(_document(first), _document(second))

    def test_serialized_vectors_are_floats(self):
        clip = AnimationClip(
            name="c",
            position_tracks=(
                ("n", Track(times=(0.0, 1.0), values=(Vec3(0, 0, 0), Vec3(1, 2, 3)))),
            ),
        )
        key = clip.to_dict()["position"]["n"]["keys"][0]
        self.assertTrue(all(isinstance(component, float) for component in key["v"]))

        scene = Scene()
        scene.add(Node("n", id="n")).transform = Transform(position=Vec3(7, 8, 9))
        position = scene_to_dict(scene)["nodes"][0]["transform"]["position"]
        self.assertTrue(all(isinstance(component, float) for component in position))


if __name__ == "__main__":
    unittest.main()
