"""Tests for the game-agnostic audio core."""

import tempfile
import unittest
from pathlib import Path

from keystone.audio import (
    AudioClip,
    Mixer,
    audio_report,
    mix_clips,
    noise,
    read_wav,
    sine,
    square,
    write_wav,
)


class AudioTest(unittest.TestCase):
    def test_synth_clips_are_deterministic(self):
        first = sine(440.0, 0.05)
        second = sine(440.0, 0.05)
        self.assertEqual(first.samples, second.samples)
        self.assertGreater(len(first.samples), 0)
        self.assertEqual(noise(0.05, seed=3).samples, noise(0.05, seed=3).samples)
        self.assertNotEqual(noise(0.05, seed=3).samples, noise(0.05, seed=4).samples)
        self.assertEqual(len(square(220.0, 0.02).samples), int(0.02 * first.sample_rate))

    def test_noise_rejects_nonint_seed_to_keep_determinism(self):
        for bad in (None, "7", 3.5, True):
            with self.assertRaises(TypeError):
                noise(0.05, seed=bad)

    def test_validation_rejects_bad_params(self):
        with self.assertRaises(ValueError):
            sine(0.0, 0.1)
        with self.assertRaises(ValueError):
            AudioClip(samples=(2.0,), name="loud")
        with self.assertRaises(ValueError):
            Mixer().set_bus("", 1.0)
        with self.assertRaises(ValueError):
            Mixer().play(sine(440.0, 0.02), pitch=0.0)

    def test_mixer_applies_buses_and_renders(self):
        mixer = Mixer()
        mixer.set_bus("sfx", 0.5)
        mixer.play(sine(440.0, 0.05), bus="sfx", gain=1.0)
        mixer.play(sine(660.0, 0.05), bus="music", gain=1.0)
        self.assertEqual(mixer.voice_count(), 2)
        rendered = mixer.render()
        self.assertEqual(rendered.name, "mixdown")
        self.assertGreater(len(rendered.samples), 0)
        report = audio_report(rendered, voices=mixer.voice_count(), buses=mixer.buses)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["voices"], 2)

    def test_mix_clips_requires_shared_rate(self):
        first = AudioClip(samples=(0.1, 0.2), sample_rate=22050, name="a")
        second = AudioClip(samples=(0.1,), sample_rate=8000, name="b")
        with self.assertRaises(ValueError):
            mix_clips([(first, 1.0, 1.0), (second, 1.0, 1.0)])

    def test_mix_clips_clamps_once_at_the_end(self):
        rate = 22050

        def voice(value):
            return AudioClip(samples=(value,), sample_rate=rate, name="v")

        mixed = mix_clips([(voice(1.0), 1.0, 1.0), (voice(1.0), 1.0, 1.0), (voice(-1.0), 1.0, 1.0)])
        self.assertEqual(mixed.samples, (1.0,))
        self.assertEqual(
            mix_clips([(voice(-1.0), 1.0, 1.0), (voice(1.0), 1.0, 1.0), (voice(1.0), 1.0, 1.0)]).samples,
            mixed.samples,
        )

    def test_wav_round_trip(self):
        clip = sine(440.0, 0.05, name="tone")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            write_wav(path, clip)
            loaded = read_wav(path)
            self.assertEqual(loaded.sample_rate, clip.sample_rate)
            self.assertEqual(len(loaded.samples), len(clip.samples))
            self.assertAlmostEqual(loaded.samples[10], clip.samples[10], places=2)

    def test_clip_json_round_trip(self):
        clip = sine(330.0, 0.02, name="blip")
        restored = AudioClip.from_dict(clip.to_dict())
        self.assertEqual(restored.samples, clip.samples)
        self.assertEqual(restored.name, "blip")

    def test_read_wav_accepts_full_scale_negative(self):
        import struct
        import wave
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ext.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(22050)
                handle.writeframes(struct.pack("<2h", 0, -32768))
            loaded = read_wav(path)
            self.assertAlmostEqual(loaded.samples[1], -1.0, places=4)

    def test_master_bus_applies_once(self):
        clip = sine(440.0, 0.05)
        direct = Mixer(buses={"master": 0.5, "sfx": 1.0})
        direct.play(clip, bus="master")
        via_sfx = Mixer(buses={"master": 0.5, "sfx": 1.0})
        via_sfx.play(clip, bus="sfx")
        self.assertAlmostEqual(direct.render().samples[10], via_sfx.render().samples[10], places=6)

    def test_play_rejects_unknown_bus(self):
        with self.assertRaises(ValueError):
            Mixer().play(sine(440.0, 0.02), bus="sfx_typo")

    def test_non_finite_audio_values_are_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                sine(bad, 0.01)
            with self.assertRaises(ValueError):
                square(bad, 0.01)
            with self.assertRaises(ValueError):
                AudioClip(samples=(bad,))
            with self.assertRaises(ValueError):
                AudioClip(samples=(0.1,)).with_gain(bad)
            with self.assertRaises(ValueError):
                Mixer(sample_rate=bad)
            with self.assertRaises(ValueError):
                Mixer().play(AudioClip(samples=(0.1,)), gain=bad)
            with self.assertRaises(ValueError):
                Mixer().play(AudioClip(samples=(0.1,)), pitch=bad)

    def test_audio_clip_normalizes_samples_and_rate(self):
        clip = AudioClip(samples=[0.1, -0.2], sample_rate=8000)
        self.assertIsInstance(clip.samples, tuple)
        with self.assertRaises((TypeError, ValueError)):
            AudioClip(samples=(0.1,), sample_rate=22050.5)  # type: ignore[arg-type]
        with self.assertRaises((TypeError, ValueError)):
            AudioClip(samples=(0.1,), sample_rate=True)  # type: ignore[arg-type]
        with self.assertRaises((TypeError, ValueError)):
            AudioClip.from_dict({"samples": [0.1], "sample_rate": 22050.9})

    def test_removed_bus_mutes_instead_of_full_gain(self):
        mixer = Mixer()
        mixer.play(AudioClip(samples=(0.5,), name="loud"), bus="sfx")
        del mixer.buses["sfx"]
        self.assertEqual(mixer.render().samples, (0.0,))

    def test_mix_clips_rejects_runaway_pitch(self):
        clip = AudioClip(samples=(0.5,), name="short")
        with self.assertRaises(ValueError):
            mix_clips([(clip, 1.0, 1e-5)])

    def test_mix_clips_rejects_none(self):
        with self.assertRaises(TypeError):
            mix_clips(None)  # type: ignore[arg-type]

    def test_read_wav_rejects_truncated_payload(self):
        import struct
        import wave

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "truncated.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(22050)
                handle.writeframes(struct.pack("<4h", 0, 1000, -1000, 500))
            path.write_bytes(path.read_bytes()[:-3])
            with self.assertRaises(ValueError):
                read_wav(path)


if __name__ == "__main__":
    unittest.main()
