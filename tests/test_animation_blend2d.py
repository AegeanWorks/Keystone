"""Tests for deterministic 2D (bilinear grid) animation blend spaces."""

import json
import unittest

from keystone.animation import AnimationClip, Track
from keystone.animation_blend import BlendSample2D, BlendSpace2D
from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _clip(name: str, x: float) -> AnimationClip:
    return AnimationClip(
        name=name,
        position_tracks=(("node", Track(times=(0.0, 1.0), values=(Vec3(x, 0.0, 0.0), Vec3(x, 1.0, 0.0)))),),
    )


def _grid() -> BlendSpace2D:
    return BlendSpace2D(
        (
            BlendSample2D(_clip("bl", 0.0), 0.0, 0.0),
            BlendSample2D(_clip("br", 10.0), 1.0, 0.0),
            BlendSample2D(_clip("tl", 20.0), 0.0, 1.0),
            BlendSample2D(_clip("tr", 30.0), 1.0, 1.0),
        )
    )


class BlendSpace2DTest(unittest.TestCase):
    def test_grid_axes_are_sorted(self):
        space = _grid()
        self.assertEqual(space.xs, (0.0, 1.0))
        self.assertEqual(space.ys, (0.0, 1.0))

    def test_corners_return_their_samples(self):
        space = _grid()
        self.assertEqual(space.sample(0.0, 0.0, 0.5)["node"].position, Vec3(0.0, 0.5, 0.0))
        self.assertEqual(space.sample(1.0, 0.0, 0.5)["node"].position, Vec3(10.0, 0.5, 0.0))
        self.assertEqual(space.sample(0.0, 1.0, 0.5)["node"].position, Vec3(20.0, 0.5, 0.0))
        self.assertEqual(space.sample(1.0, 1.0, 0.5)["node"].position, Vec3(30.0, 0.5, 0.0))

    def test_the_centre_is_the_bilinear_average(self):
        space = _grid()
        self.assertEqual(space.sample(0.5, 0.5, 0.5)["node"].position, Vec3(15.0, 0.5, 0.0))

    def test_edges_interpolate_one_axis(self):
        space = _grid()
        self.assertEqual(space.sample(0.5, 0.0, 0.5)["node"].position, Vec3(5.0, 0.5, 0.0))
        self.assertEqual(space.sample(0.0, 0.5, 0.5)["node"].position, Vec3(10.0, 0.5, 0.0))

    def test_values_clamp_to_the_grid(self):
        space = _grid()
        self.assertEqual(space.sample(-5.0, -5.0, 0.5)["node"].position, Vec3(0.0, 0.5, 0.0))
        self.assertEqual(space.sample(9.0, 9.0, 0.5)["node"].position, Vec3(30.0, 0.5, 0.0))

    def test_a_single_row_or_column_still_blends(self):
        row = BlendSpace2D(
            (
                BlendSample2D(_clip("a", 0.0), 0.0, 0.0),
                BlendSample2D(_clip("b", 10.0), 1.0, 0.0),
            )
        )
        self.assertEqual(row.sample(0.5, 42.0, 0.0)["node"].position, Vec3(5.0, 0.0, 0.0))
        column = BlendSpace2D(
            (
                BlendSample2D(_clip("a", 0.0), 0.0, 0.0),
                BlendSample2D(_clip("b", 10.0), 0.0, 1.0),
            )
        )
        self.assertEqual(column.sample(42.0, 0.5, 0.0)["node"].position, Vec3(5.0, 0.0, 0.0))

    def test_a_single_sample_is_returned_directly(self):
        space = BlendSpace2D((BlendSample2D(_clip("only", 7.0), 2.0, 3.0),))
        self.assertEqual(space.sample(0.0, 0.0, 0.0)["node"].position, Vec3(7.0, 0.0, 0.0))

    def test_a_3x2_grid_uses_the_local_cell(self):
        samples = []
        for yi, y in enumerate((0.0, 1.0)):
            for xi, x in enumerate((0.0, 1.0, 2.0)):
                samples.append(BlendSample2D(_clip(f"c{xi}{yi}", float(xi + yi * 10)), x, y))
        space = BlendSpace2D(tuple(samples))
        self.assertEqual(space.sample(1.5, 0.5, 0.0)["node"].position, Vec3(6.5, 0.0, 0.0))

    def test_sampling_is_deterministic(self):
        space = _grid()
        first = space.sample(0.25, 0.75, 0.4)
        second = space.sample(0.25, 0.75, 0.4)
        self.assertEqual(first, second)

    def test_duration_is_the_longest_clip(self):
        short = AnimationClip(name="short", position_tracks=(("node", Track(times=(0.0, 0.25), values=(Vec3(), Vec3()))),))
        long = AnimationClip(name="long", position_tracks=(("node", Track(times=(0.0, 2.0), values=(Vec3(), Vec3()))),))
        space = BlendSpace2D((BlendSample2D(short, 0.0, 0.0), BlendSample2D(long, 1.0, 0.0)))
        self.assertEqual(space.duration, 2.0)

    def test_documents_round_trip_and_are_json_safe(self):
        space = _grid()
        document = space.to_dict()
        self.assertEqual(document["schema"], 1)
        self.assertEqual(json.loads(json.dumps(document)), document)
        self.assertEqual(BlendSpace2D.from_dict(document), space)

    def test_reports_are_json_safe(self):
        report = _grid().report()
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["xs"], [0.0, 1.0])
        self.assertEqual(report["ys"], [0.0, 1.0])
        self.assertEqual(
            [(entry["clip"], entry["x"], entry["y"]) for entry in report["samples"]],
            [("bl", 0.0, 0.0), ("tl", 0.0, 1.0), ("br", 1.0, 0.0), ("tr", 1.0, 1.0)],
        )

    def test_an_incomplete_grid_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            BlendSpace2D(
                (
                    BlendSample2D(_clip("bl", 0.0), 0.0, 0.0),
                    BlendSample2D(_clip("br", 1.0), 1.0, 0.0),
                    BlendSample2D(_clip("tl", 2.0), 0.0, 1.0),
                )
            )
        self.assertIn("complete rectangular grid", str(caught.exception))

    def test_duplicate_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            BlendSpace2D(
                (
                    BlendSample2D(_clip("a", 0.0), 0.0, 0.0),
                    BlendSample2D(_clip("b", 1.0), 0.0, 0.0),
                )
            )

    def test_malformed_spaces_are_rejected(self):
        with self.assertRaises(ValueError):
            BlendSpace2D(())
        with self.assertRaises(TypeError):
            BlendSpace2D((object(),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            BlendSample2D("clip", 0.0, 0.0)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            BlendSample2D(_clip("a", 0.0), float("nan"), 0.0)

    def test_malformed_documents_are_rejected(self):
        with self.assertRaises(TypeError):
            BlendSpace2D.from_dict(["not", "a", "mapping"])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            BlendSpace2D.from_dict({"schema": 2, "samples": []})
        with self.assertRaises(ValueError):
            BlendSpace2D.from_dict({"schema": 1, "samples": [], "extra": 1})
        with self.assertRaises(ValueError):
            BlendSpace2D.from_dict({"schema": 1, "samples": [{"clip": _clip("a", 0.0).to_dict(), "x": 0.0, "y": 0.0, "z": 1.0}]})
        with self.assertRaises(ValueError):
            BlendSample2D.from_dict({"clip": _clip("a", 0.0).to_dict(), "x": "left", "y": 0.0})

    def test_describe_advertises_2d_blending(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["animation_blend_2d"])


if __name__ == "__main__":
    unittest.main()
