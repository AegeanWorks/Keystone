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

SAMPLE_RATE = 22050

__all__ = ["SAMPLE_RATE", "AudioClip", "Mixer", "audio_report", "mix_clips", "noise", "read_wav", "sine", "square", "write_wav"]


@dataclass(frozen=True, slots=True)
class AudioClip:
    """Immutable mono PCM clip in [-1, 1] with a fixed sample rate."""

    samples: tuple[float, ...] = ()
    sample_rate: int = SAMPLE_RATE
    name: str = "clip"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("clip name must be a non-blank string")
        if self.sample_rate <= 0:
            raise ValueError("sample rate must be positive")
        for sample in self.samples:
            if not -1.0 <= float(sample) <= 1.0:
                raise ValueError("samples must be within [-1, 1]")

    def duration(self) -> float:
        return len(self.samples) / float(self.sample_rate) if self.samples else 0.0

    def with_gain(self, gain: float) -> AudioClip:
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
        if data.get("schema", 1) != 1:
            raise ValueError("unsupported audio clip schema")
        raw = data.get("samples", [])
        if not isinstance(raw, (list, tuple)):
            raise TypeError("audio clip samples must be a list")
        return cls(samples=tuple(float(value) for value in raw),
                   sample_rate=int(data.get("sample_rate", SAMPLE_RATE)),
                   name=str(data.get("name", "clip")))


def sine(frequency: float, duration: float, sample_rate: int = SAMPLE_RATE, name: str = "sine") -> AudioClip:
    if frequency <= 0.0 or duration <= 0.0 or sample_rate <= 0:
        raise ValueError("frequency, duration and sample rate must be positive")
    count = int(duration * sample_rate)
    return AudioClip(
        samples=tuple(math.sin(2.0 * math.pi * frequency * index / sample_rate) for index in range(count)),
        sample_rate=sample_rate,
        name=name,
    )


def square(frequency: float, duration: float, sample_rate: int = SAMPLE_RATE, name: str = "square") -> AudioClip:
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
    if duration <= 0.0 or sample_rate <= 0:
        raise ValueError("duration and sample rate must be positive")
    rng = random.Random(seed)
    count = int(duration * sample_rate)
    return AudioClip(samples=tuple(rng.uniform(-1.0, 1.0) for _ in range(count)),
                     sample_rate=sample_rate, name=name)


def mix_clips(clips: list[tuple[AudioClip, float, float]]) -> AudioClip:
    """Mix (clip, gain, pitch) voices deterministically; pitch resamples by index scaling."""
    if not clips:
        return AudioClip((), SAMPLE_RATE, "silence")
    rate = clips[0][0].sample_rate
    for clip, _, _ in clips:
        if clip.sample_rate != rate:
            raise ValueError("all mixed clips must share one sample rate")
    lengths: list[int] = []
    for clip, _, pitch in clips:
        if pitch <= 0.0:
            raise ValueError("pitch must be positive")
        lengths.append(int(len(clip.samples) / pitch))
    total = max(lengths)
    mixed = [0.0] * total
    for clip, gain, pitch in clips:
        if gain < 0.0:
            raise ValueError("gain must be non-negative")
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
        if self.sample_rate <= 0:
            raise ValueError("sample rate must be positive")
        self.buses = dict(self.buses)
        for bus, gain in self.buses.items():
            if not bus.strip() or gain < 0.0:
                raise ValueError("bus gains must be named and non-negative")

    def set_bus(self, bus: str, gain: float) -> None:
        if not bus.strip() or gain < 0.0:
            raise ValueError("bus gain must be named and non-negative")
        self.buses[bus] = gain

    def play(self, clip: AudioClip, bus: str = "sfx", gain: float = 1.0, pitch: float = 1.0) -> None:
        if clip.sample_rate != self.sample_rate:
            raise ValueError("clip sample rate must match the mixer")
        if not isinstance(bus, str) or not bus.strip():
            raise ValueError("bus name must be a non-blank string")
        if bus not in self.buses:
            raise ValueError(f"unknown bus '{bus}'")
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
    import os

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        # hygiene: allow binary-mode WAV write needs no text encoding
        with temporary.open("wb") as handle:
            handle.write(_wav_write(clip))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_wav(path: str | Path) -> AudioClip:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
                raise ValueError("only mono 16-bit WAV files are supported")
            rate = handle.getframerate()
            frames = handle.readframes(handle.getnframes())
    except (OSError, wave.Error) as exc:
        raise ValueError(f"could not read WAV from {path}: {exc}") from exc
    count = len(frames) // 2
    samples = struct.unpack(f"<{count}h", frames) if count else ()
    return AudioClip(samples=tuple(value / 32768.0 if value < 0 else value / 32767.0 for value in samples),
                     sample_rate=rate, name=Path(str(path)).stem)


def audio_report(clip: AudioClip, voices: int = 0, buses: dict | None = None) -> dict:
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
