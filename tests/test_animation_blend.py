"""Unit tests for deterministic 1D animation blend spaces."""

import json
import unittest

from keystone.animation import AnimationClip, Track
from keystone.animation_blend import BlendSample, BlendSpace1D
from keystone.math3d import Vec3


def _clip(name: str, x: float) -> AnimationClip:
    return AnimationClip(
        name=name,
        position_tracks=(
            (
                "node",
                Track(
                    times=(0.0, 1.0),
                    values=(Vec3(x, 0.0, 0.0), Vec3(x, 1.0, 0.0)),
                ),
            ),
        ),
    )


class BlendSpaceTest(unittest.TestCase):
    def test_samples_and_clamps_parameter(self):
        space = BlendSpace1D(
            (
                BlendSample(_clip("walk", 0.0), 0.0),
                BlendSample(_clip("run", 10.0), 10.0),
            )
        )
        self.assertEqual(space.thresholds, (0.0, 10.0))
        self.assertEqual(
            space.sample(0.0, 0.5)["node"].position, Vec3(0.0, 0.5, 0.0)
        )
        self.assertEqual(
            space.sample(5.0, 0.5)["node"].position, Vec3(5.0, 0.5, 0.0)
        )
        self.assertEqual(
            space.sample(10.0, 0.5)["node"].position, Vec3(10.0, 0.5, 0.0)
        )
        self.assertEqual(
            space.sample(-5.0, 0.5)["node"].position, Vec3(0.0, 0.5, 0.0)
        )
        self.assertEqual(
            space.sample(25.0, 0.5)["node"].position, Vec3(10.0, 0.5, 0.0)
        )

    def test_single_sample_and_reverse_order(self):
        walk = _clip("walk", 0.0)
        run = _clip("run", 10.0)
        self.assertEqual(
            BlendSpace1D((BlendSample(walk, 3.0),)).thresholds, (3.0,)
        )
        space = BlendSpace1D(
            (BlendSample(run, 10.0), BlendSample(walk, 0.0))
        )
        self.assertEqual(space.thresholds, (0.0, 10.0))
        self.assertEqual(
            space.sample(5.0, 0.0)["node"].position, Vec3(5.0, 0.0, 0.0)
        )

    def test_round_trip_and_report(self):
        space = BlendSpace1D(
            (
                BlendSample(_clip("walk", 0.0), 0.0),
                BlendSample(_clip("run", 10.0), 10.0),
            )
        )
        document = space.to_dict()
        self.assertEqual(document["schema"], 1)
        json.dumps(document)
        restored = BlendSpace1D.from_dict(document)
        self.assertEqual(restored.to_dict(), document)
        report = restored.report()
        self.assertEqual(
            [item["clip"] for item in report["samples"]], ["walk", "run"]
        )
        self.assertEqual(report["thresholds"], [0.0, 10.0])
        self.assertEqual(report["duration"], 1.0)

    def test_validation(self):
        walk = _clip("walk", 0.0)
        with self.assertRaises(ValueError):
            BlendSpace1D(())
        with self.assertRaises(TypeError):
            BlendSpace1D((object(),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            BlendSample(object(), 0.0)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            BlendSample(walk, float("nan"))
        with self.assertRaises(ValueError):
            BlendSpace1D(
                (BlendSample(walk, 1.0), BlendSample(walk, 1.0))
            )
        space = BlendSpace1D((BlendSample(walk, 0.0),))
        with self.assertRaises(ValueError):
            space.sample(float("nan"), 0.0)
        with self.assertRaises(ValueError):
            space.sample(0.0, float("inf"))
        with self.assertRaises(ValueError):
            BlendSpace1D.from_dict({"schema": 2, "samples": []})
        with self.assertRaises(ValueError):
            BlendSpace1D.from_dict({"schema": 1, "samples": []})
        with self.assertRaises(ValueError):
            BlendSpace1D.from_dict({"schema": 1, "samples": [], "extra": 1})
        with self.assertRaises(ValueError):
            BlendSample.from_dict({"clip": walk.to_dict(), "extra": 1})
        with self.assertRaises(ValueError):
            BlendSample.from_dict({})


if __name__ == "__main__":
    unittest.main()
