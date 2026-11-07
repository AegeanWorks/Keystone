"""Game-agnostic audio core: synth clips, bus mixer and WAV I/O.

No playback device or third-party dependency is required. All mixing is
deterministic pure Python so AI clients can synthesize, verify and audit
sound without hardware. Games own their score; the engine owns mixing.
"""

from __future__ import annotations

import math
import random
import struct
import wave
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from keystone.serialization import write_bytes_atomic

SAMPLE_RATE = 22050

__all__ = ["SAMPLE_RATE", "AudioClip", "Mixer", "audio_report", "mix_clips", "noise", "read_wav", "sine", "square", "write_wav"]


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class AudioClip:
    """Immutable mono PCM clip in [-1, 1] with a fixed sample rate."""

    samples: tuple[float, ...] = ()
    sample_rate: int = SAMPLE_RATE
    name: str = "clip"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("clip name must be a non-blank string")
        if isinstance(self.sample_rate, bool) or not isinstance(self.sample_rate, int) or self.sample_rate <= 0:
            raise ValueError("sample rate must be a positive integer")
        if isinstance(self.samples, (str, bytes)) or not isinstance(self.samples, (tuple, list)):
            raise TypeError("samples must be a sequence of numbers")
        cleaned: list[float] = []
        for sample in self.samples:
            value = _finite(sample, "audio sample")
            if not -1.0 <= value <= 1.0:
                raise ValueError("samples must be within [-1, 1]")
            cleaned.append(value)
        object.__setattr__(self, "samples", tuple(cleaned))

    def duration(self) -> float:
        return len(self.samples) / float(self.sample_rate) if self.samples else 0.0

    def with_gain(self, gain: float) -> AudioClip:
        gain = _finite(gain, "gain")
        if gain < 0.0:
            raise ValueError("gain must be non-negative")
        return AudioClip(
            samples=tuple(max(-1.0, min(1.0, sample * gain)) for sample in self.samples),
            sample_rate=self.sample_rate,
            name=self.name,
        )

    def to_dict(self) -> dict:
        return {"schema": 1, "name": self.name, "sample_rate": self.sample_rate, "samples": list(self.samples)}

    @classmethod
    def from_dict(cls, data: dict) -> AudioClip:
        if not isinstance(data, dict):
            raise TypeError("audio clip document must be a mapping")
        schema = data.get("schema", 1)
        if isinstance(schema, bool) or not isinstance(schema, int) or schema != 1:
            raise ValueError("unsupported audio clip schema")
        raw = data.get("samples", [])
        if not isinstance(raw, (list, tuple)):
            raise TypeError("audio clip samples must be a list")
        sample_rate = data.get("sample_rate", SAMPLE_RATE)
        if isinstance(sample_rate, bool) or not isinstance(sample_rate, int):
            raise TypeError("audio clip sample rate must be an integer")
        name = data.get("name", "clip")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("audio clip name must be a non-blank string")
        return cls(samples=tuple(_finite(value, "audio sample") for value in raw),
                   sample_rate=sample_rate,
                   name=name)


def sine(frequency: float, duration: float, sample_rate: int = SAMPLE_RATE, name: str = "sine") -> AudioClip:
    frequency = _finite(frequency, "frequency")
    duration = _finite(duration, "duration")
    if frequency <= 0.0 or duration <= 0.0 or sample_rate <= 0:
        raise ValueError("frequency, duration and sample rate must be positive")
    count = int(duration * sample_rate)
    return AudioClip(
        samples=tuple(math.sin(2.0 * math.pi * frequency * index / sample_rate) for index in range(count)),
        sample_rate=sample_rate,
        name=name,
    )


def square(frequency: float, duration: float, sample_rate: int = SAMPLE_RATE, name: str = "square") -> AudioClip:
    frequency = _finite(frequency, "frequency")
    duration = _finite(duration, "duration")
    if frequency <= 0.0 or duration <= 0.0 or sample_rate <= 0:
        raise ValueError("frequency, duration and sample rate must be positive")
    count = int(duration * sample_rate)
    return AudioClip(
        samples=tuple(1.0 if math.sin(2.0 * math.pi * frequency * index / sample_rate) >= 0.0 else -1.0
                      for index in range(count)),
        sample_rate=sample_rate,
        name=name,
    )


def noise(duration: float, seed: int = 7, sample_rate: int = SAMPLE_RATE, name: str = "noise") -> AudioClip:
    duration = _finite(duration, "duration")
    if duration <= 0.0 or sample_rate <= 0:
        raise ValueError("duration and sample rate must be positive")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("noise seed must be an int to keep mixes deterministic")
    rng = random.Random(seed)
    count = int(duration * sample_rate)
    return AudioClip(samples=tuple(rng.uniform(-1.0, 1.0) for _ in range(count)),
                     sample_rate=sample_rate, name=name)


def mix_clips(clips: list[tuple[AudioClip, float, float]]) -> AudioClip:
    """Mix (clip, gain, pitch) voices deterministically; pitch resamples by index scaling."""
    if clips is None:
        raise TypeError("clips must be a list of (clip, gain, pitch) voices")
    voices = list(clips)
    if not voices:
        return AudioClip((), SAMPLE_RATE, "silence")
    rate = voices[0][0].sample_rate
    for clip, gain, pitch in voices:
        if not isinstance(clip, AudioClip):
            raise TypeError("mix voices must hold AudioClip instances")
        if clip.sample_rate != rate:
            raise ValueError("all mixed clips must share one sample rate")
        if _finite(gain, "gain") < 0.0:
            raise ValueError("gain must be non-negative")
        if _finite(pitch, "pitch") <= 0.0:
            raise ValueError("pitch must be positive")
    lengths: list[int] = []
    for clip, _, pitch in voices:
        lengths.append(int(len(clip.samples) / pitch))
    total = max(lengths)
    mixed = [0.0] * total
    for clip, gain, pitch in voices:
        for index in range(int(len(clip.samples) / pitch)):
            source = clip.samples[int(index * pitch)]
            mixed[index] += source * gain
    mixed = [max(-1.0, min(1.0, value)) for value in mixed]
    return AudioClip(samples=tuple(mixed), sample_rate=rate, name="mix")


@dataclass
class Mixer:
    """Named-bus mixer: voices route through per-bus gains into one deterministic mix."""

    sample_rate: int = SAMPLE_RATE
    buses: dict[str, float] = field(default_factory=lambda: {"master": 1.0, "music": 0.8, "sfx": 0.9})
    _voices: list[tuple[AudioClip, str, float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.sample_rate, bool) or not isinstance(self.sample_rate, int) or self.sample_rate <= 0:
            raise ValueError("sample rate must be a positive integer")
        self.buses = dict(self.buses)
        for bus, gain in self.buses.items():
            if not isinstance(bus, str) or not bus.strip():
                raise ValueError("bus gains must be named and non-negative")
            if _finite(gain, "bus gain") < 0.0:
                raise ValueError("bus gains must be named and non-negative")

    def set_bus(self, bus: str, gain: float) -> None:
        if not isinstance(bus, str) or not bus.strip():
            raise ValueError("bus gain must be named and non-negative")
        gain = _finite(gain, "bus gain")
        if gain < 0.0:
            raise ValueError("bus gain must be named and non-negative")
        self.buses[bus] = gain

    def play(self, clip: AudioClip, bus: str = "sfx", gain: float = 1.0, pitch: float = 1.0) -> None:
        if not isinstance(clip, AudioClip):
            raise TypeError("voice clip must be an AudioClip")
        if clip.sample_rate != self.sample_rate:
            raise ValueError("clip sample rate must match the mixer")
        if not isinstance(bus, str) or not bus.strip():
            raise ValueError("bus name must be a non-blank string")
        if bus not in self.buses:
            raise ValueError(f"unknown bus '{bus}'")
        gain = _finite(gain, "voice gain")
        pitch = _finite(pitch, "voice pitch")
        if gain < 0.0 or pitch <= 0.0:
            raise ValueError("voice gain must be non-negative and pitch positive")
        self._voices.append((clip, bus, gain, pitch))

    def clear(self) -> None:
        self._voices.clear()

    def voice_count(self) -> int:
        return len(self._voices)

    def render(self) -> AudioClip:
        parts: list[tuple[AudioClip, float, float]] = []
        master = self.buses.get("master", 1.0)
        for clip, bus, gain, pitch in self._voices:
            if bus == "master":
                bus_gain = master
            else:
                bus_gain = self.buses.get(bus, 1.0) * master
            parts.append((clip, gain * bus_gain, pitch))
        result = mix_clips(parts)
        return AudioClip(samples=result.samples, sample_rate=self.sample_rate, name="mixdown")


def _wav_write(clip: AudioClip) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(clip.sample_rate)
        handle.writeframes(struct.pack(f"<{len(clip.samples)}h",
                                       *(int(max(-1.0, min(1.0, s)) * 32767) for s in clip.samples)))
    return buffer.getvalue()


def write_wav(path: str | Path, clip: AudioClip) -> None:
    write_bytes_atomic(path, _wav_write(clip))


def read_wav(path: str | Path) -> AudioClip:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
                raise ValueError("only mono 16-bit WAV files are supported")
            rate = handle.getframerate()
            expected = handle.getnframes() * 2
            frames = handle.readframes(handle.getnframes())
    except (OSError, EOFError, wave.Error) as exc:
        raise ValueError(f"could not read WAV from {path}: {exc}") from exc
    if len(frames) != expected or len(frames) % 2:
        raise ValueError(f"could not read WAV from {path}: truncated sample data")
    count = len(frames) // 2
    samples = struct.unpack(f"<{count}h", frames) if count else ()
    return AudioClip(samples=tuple(value / 32768.0 if value < 0 else value / 32767.0 for value in samples),
                     sample_rate=rate, name=Path(str(path)).stem)


def audio_report(clip: AudioClip, voices: int = 0, buses: dict | None = None) -> dict:
    if not isinstance(clip, AudioClip):
        raise TypeError("audio report needs an AudioClip")
    if isinstance(voices, bool) or not isinstance(voices, int) or voices < 0:
        raise ValueError("voices must be a non-negative integer")
    if buses is not None:
        if not isinstance(buses, dict):
            raise TypeError("buses must be a mapping")
        buses = {name: _finite(gain, "bus gain") for name, gain in buses.items()}
    samples = clip.samples
    peak = max((abs(sample) for sample in samples), default=0.0)
    rms = (sum(sample * sample for sample in samples) / max(1, len(samples))) ** 0.5
    return {
        "schema": 1,
        "name": clip.name,
        "sample_rate": clip.sample_rate,
        "frames": len(samples),
        "duration": round(clip.duration(), 4),
        "peak": round(peak, 4),
        "rms": round(rms, 4),
        "voices": voices,
        "buses": dict(buses or {}),
    }
