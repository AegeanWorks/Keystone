"""Tests for deterministic distance attenuation and spatial mixdown."""

import unittest

from keystone.audio import SAMPLE_RATE, AudioClip
from keystone.audio_spatial import (
    SoundSource,
    distance_gain,
    spatial_mix,
    spatial_report,
)
from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo

CLIP = AudioClip(samples=(0.5, 0.0, -0.5, 0.25), sample_rate=SAMPLE_RATE, name="tick")


def _source(**overrides) -> SoundSource:
    values = {
        "position": Vec3(0.0, 0.0, 0.0),
        "clip": CLIP,
        "gain": 1.0,
        "pitch": 1.0,
        "min_distance": 1.0,
        "max_distance": 10.0,
        "bus": "sfx",
    }
    values.update(overrides)
    return SoundSource(**values)


class DistanceGainTest(unittest.TestCase):
    def test_inside_the_near_radius_is_full_volume(self):
        listener = Vec3(0.0, 0.0, 0.0)
        source = _source(position=Vec3(0.5, 0.0, 0.0))
        self.assertEqual(distance_gain(listener, source), 1.0)

    def test_at_or_beyond_the_far_radius_is_silent(self):
        listener = Vec3(0.0, 0.0, 0.0)
        self.assertEqual(distance_gain(listener, _source(position=Vec3(10.0, 0.0, 0.0))), 0.0)
        self.assertEqual(distance_gain(listener, _source(position=Vec3(30.0, 0.0, 0.0))), 0.0)

    def test_between_the_radii_falls_off_linearly(self):
        listener = Vec3(0.0, 0.0, 0.0)
        source = _source(position=Vec3(5.5, 0.0, 0.0), min_distance=1.0, max_distance=10.0)
        self.assertAlmostEqual(distance_gain(listener, source), 0.5)

    def test_distance_is_measured_in_three_dimensions(self):
        listener = Vec3(0.0, 0.0, 0.0)
        source = _source(position=Vec3(3.0, 4.0, 0.0), min_distance=0.0, max_distance=10.0)
        self.assertAlmostEqual(distance_gain(listener, source), 0.5)

    def test_gain_is_monotonic_with_distance(self):
        listener = Vec3()
        previous = 1.0
        for step in range(11):
            source = _source(position=Vec3(float(step), 0.0, 0.0), min_distance=0.0, max_distance=10.0)
            current = distance_gain(listener, source)
            self.assertLessEqual(current, previous + 1e-12)
            previous = current

    def test_bad_arguments_are_rejected(self):
        with self.assertRaises(TypeError):
            distance_gain((0.0, 0.0, 0.0), _source())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            distance_gain(Vec3(), {"position": Vec3()})  # type: ignore[arg-type]


class SoundSourceValidationTest(unittest.TestCase):
    def test_defaults_describe_a_mid_range_effect(self):
        source = SoundSource(position=Vec3(), clip=CLIP)
        self.assertEqual(source.bus, "sfx")
        self.assertEqual(source.min_distance, 1.0)
        self.assertEqual(source.max_distance, 25.0)

    def test_malformed_sources_are_rejected(self):
        with self.assertRaises(TypeError):
            SoundSource(position=(0.0, 0.0, 0.0), clip=CLIP)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            SoundSource(position=Vec3(), clip="tick")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            _source(gain=-0.1)
        with self.assertRaises(ValueError):
            _source(gain=float("nan"))
        with self.assertRaises(ValueError):
            _source(pitch=0.0)
        with self.assertRaises(ValueError):
            _source(min_distance=-1.0)
        with self.assertRaises(ValueError):
            _source(min_distance=5.0, max_distance=5.0)
        with self.assertRaises(ValueError):
            _source(bus=" ")
        with self.assertRaises(ValueError):
            _source(position=Vec3(float("inf"), 0.0, 0.0))


class SpatialMixTest(unittest.TestCase):
    def _mix(self, listener, sources, **kwargs):
        return spatial_mix(listener, sources, bus_gains={"master": 1.0, "sfx": 1.0}, **kwargs)

    def test_a_source_at_the_near_radius_mixes_at_full_source_gain(self):
        listener = Vec3()
        mixed = self._mix(listener, [_source(gain=0.5)])
        self.assertEqual(mixed.samples, tuple(max(-1.0, min(1.0, s * 0.5)) for s in CLIP.samples))
        self.assertEqual(mixed.name, "spatial-mix")

    def test_a_source_beyond_the_far_radius_is_silent(self):
        mixed = self._mix(Vec3(), [_source(position=Vec3(40.0, 0.0, 0.0))])
        self.assertEqual(mixed.samples, (0.0, 0.0, 0.0, 0.0))

    def test_sources_add_in_source_order(self):
        listener = Vec3()
        left = AudioClip(samples=(0.25, 0.0), sample_rate=SAMPLE_RATE, name="a")
        right = AudioClip(samples=(0.5, 0.0), sample_rate=SAMPLE_RATE, name="b")
        mixed = self._mix(
            listener,
            [
                _source(position=Vec3(0.0, 0.0, 0.0), clip=left),
                _source(position=Vec3(0.0, 0.0, 0.0), clip=right),
            ],
        )
        self.assertEqual(mixed.samples, (0.75, 0.0))

    def test_pitch_scales_the_mixed_length(self):
        mixed = self._mix(Vec3(), [_source(pitch=2.0)])
        self.assertEqual(len(mixed.samples), len(CLIP.samples) // 2)

    def test_an_empty_or_silent_scene_returns_silence_at_the_mixer_rate(self):
        empty = spatial_mix(Vec3(), [])
        self.assertEqual(empty.samples, ())
        self.assertEqual(empty.name, "spatial-mix")
        silent = self._mix(Vec3(), [_source(position=Vec3(50.0, 0.0, 0.0))])
        self.assertEqual(silent.samples, (0.0, 0.0, 0.0, 0.0))

    def test_custom_bus_gains_are_honoured(self):
        mixed = spatial_mix(
            Vec3(),
            [_source(gain=1.0)],
            bus_gains={"master": 1.0, "sfx": 0.25},
        )
        self.assertEqual(mixed.samples, tuple(max(-1.0, min(1.0, s * 0.25)) for s in CLIP.samples))

    def test_an_unknown_bus_is_rejected(self):
        with self.assertRaises(ValueError):
            spatial_mix(Vec3(), [_source(bus="unknown")])

    def test_mixing_is_deterministic(self):
        listener = Vec3(1.0, 0.0, 2.0)
        sources = [_source(position=Vec3(2.0, 0.0, 2.0), gain=0.7)]
        self.assertEqual(self._mix(listener, sources).samples, self._mix(listener, sources).samples)

    def test_malformed_mix_arguments_are_rejected(self):
        with self.assertRaises(TypeError):
            spatial_mix((0.0, 0.0, 0.0), [])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            spatial_mix(Vec3(), [("not", "a", "source")])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            spatial_mix(Vec3(), [], bus_gains=[("sfx", 1.0)])  # type: ignore[arg-type]


class SpatialReportTest(unittest.TestCase):
    def test_report_is_json_safe_and_ordered(self):
        listener = Vec3()
        sources = [
            _source(position=Vec3(0.5, 0.0, 0.0), gain=0.5),
            _source(position=Vec3(20.0, 0.0, 0.0), bus="music"),
        ]
        report = spatial_report(listener, sources)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["listener"], [0.0, 0.0, 0.0])
        self.assertEqual(report["audible"], 1)
        self.assertEqual(report["silent"], 1)
        self.assertEqual([entry["index"] for entry in report["sources"]], [0, 1])
        self.assertEqual(report["sources"][0]["attenuation"], 1.0)
        self.assertEqual(report["sources"][0]["gain"], 0.5)
        self.assertTrue(report["sources"][0]["audible"])
        self.assertEqual(report["sources"][1]["attenuation"], 0.0)
        self.assertFalse(report["sources"][1]["audible"])

    def test_empty_report_counts_nothing(self):
        report = spatial_report(Vec3(), [])
        self.assertEqual(report["sources"], [])
        self.assertEqual(report["audible"], 0)
        self.assertEqual(report["silent"], 0)

    def test_a_non_finite_listener_is_rejected_even_with_no_sources(self):
        with self.assertRaises(ValueError):
            spatial_report(Vec3(float("nan"), 0.0, 0.0), [])
        with self.assertRaises(ValueError):
            spatial_mix(Vec3(float("inf"), 0.0, 0.0), [])

    def test_report_rejects_bad_input(self):
        with self.assertRaises(TypeError):
            spatial_report("listener", [])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            spatial_report(Vec3(), ["source"])  # type: ignore[arg-type]

    def test_describe_advertises_spatial_audio(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["spatial_audio"])


if __name__ == "__main__":
    unittest.main()
