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


if __name__ == "__main__":
    unittest.main()
