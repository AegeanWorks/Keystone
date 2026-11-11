"""Deterministic 3D audio attenuation and mixdown.

`keystone.audio` mixes clips on named buses but has no notion of where a
sound is or where it is heard. This module adds the missing spatial layer for
games that manage positions themselves: a `SoundSource` carries a position, a
clip and a distance range, and `distance_gain` turns listener-to-source
distance into a linear attenuation that is exactly 1 inside the near radius
and exactly 0 at the far radius.

`spatial_mix` feeds those attenuation-weighted voices through the existing
`Mixer`, so bus gains, pitch resampling and clipping behave exactly as they do
for non-spatial audio. Clips are mono, so this is distance attenuation, not
panning; a stereo stage would need a different clip format.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from keystone.audio import MIN_PITCH, SAMPLE_RATE, AudioClip, Mixer
from keystone.math3d import Vec3

__all__ = ["SoundSource", "distance_gain", "spatial_mix", "spatial_report"]


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _finite_vec3(value: object, label: str) -> Vec3:
    if not isinstance(value, Vec3):
        raise TypeError(f"{label} must be a Vec3")
    for axis in ("x", "y", "z"):
        _finite(getattr(value, axis), f"{label} {axis}")
    return value


@dataclass(frozen=True, slots=True)
class SoundSource:
    """One positional mono source with a linear distance range."""

    position: Vec3
    clip: AudioClip
    gain: float = 1.0
    pitch: float = 1.0
    min_distance: float = 1.0
    max_distance: float = 25.0
    bus: str = "sfx"

    def __post_init__(self) -> None:
        _finite_vec3(self.position, "sound position")
        if not isinstance(self.clip, AudioClip):
            raise TypeError("sound source clip must be an AudioClip")
        if _finite(self.gain, "sound gain") < 0.0:
            raise ValueError("sound gain must be non-negative")
        if _finite(self.pitch, "sound pitch") < MIN_PITCH:
            raise ValueError(f"sound pitch must be at least {MIN_PITCH}")
        near = _finite(self.min_distance, "sound near distance")
        far = _finite(self.max_distance, "sound far distance")
        if near < 0.0:
            raise ValueError("sound near distance must be non-negative")
        if far <= near:
            raise ValueError("sound far distance must be greater than the near distance")
        if not isinstance(self.bus, str) or not self.bus.strip():
            raise ValueError("sound bus must be a non-blank string")


def distance_gain(listener: Vec3, source: SoundSource) -> float:
    """Linear attenuation: 1 inside the near radius, 0 at the far radius."""
    _finite_vec3(listener, "listener position")
    if not isinstance(source, SoundSource):
        raise TypeError("distance_gain needs a SoundSource")
    distance = (source.position - listener).length()
    if distance <= source.min_distance:
        return 1.0
    if distance >= source.max_distance:
        return 0.0
    return 1.0 - (distance - source.min_distance) / (source.max_distance - source.min_distance)


def _bus_gains(overrides: Mapping[str, float] | None) -> dict[str, float]:
    gains = {"master": 1.0, "music": 0.8, "sfx": 0.9}
    if overrides is None:
        return gains
    if not isinstance(overrides, Mapping):
        raise TypeError("bus gains must be a mapping of bus names to numbers")
    for bus, gain in overrides.items():
        if not isinstance(bus, str) or not bus.strip():
            raise ValueError("bus gains must be named with non-blank strings")
        value = _finite(gain, f"bus gain {bus!r}")
        if value < 0.0:
            raise ValueError("bus gains must be non-negative")
        gains[bus] = value
    return gains


def _sources(value: Iterable[SoundSource]) -> tuple[SoundSource, ...]:
    try:
        sources = tuple(value)
    except TypeError as exc:
        raise TypeError("sources must be an iterable of SoundSource") from exc
    for source in sources:
        if not isinstance(source, SoundSource):
            raise TypeError("sources must be an iterable of SoundSource")
    return sources


def spatial_mix(
    listener: Vec3,
    sources: Iterable[SoundSource],
    *,
    bus_gains: Mapping[str, float] | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> AudioClip:
    """Mix every source through distance attenuation and the named buses."""
    _finite_vec3(listener, "listener position")
    items = _sources(sources)
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or sample_rate <= 0:
        raise ValueError("spatial mix sample rate must be a positive integer")
    mixer = Mixer(sample_rate=sample_rate, buses=_bus_gains(bus_gains))
    for source in items:
        mixer.play(
            source.clip,
            bus=source.bus,
            gain=source.gain * distance_gain(listener, source),
            pitch=source.pitch,
        )
    mixed = mixer.render()
    return AudioClip(samples=mixed.samples, sample_rate=mixer.sample_rate, name="spatial-mix")


def spatial_report(listener: Vec3, sources: Iterable[SoundSource]) -> dict:
    """Return a JSON-safe per-source attenuation summary."""
    _finite_vec3(listener, "listener position")
    items = _sources(sources)
    entries: list[dict] = []
    for index, source in enumerate(items):
        attenuation = distance_gain(listener, source)
        entries.append(
            {
                "index": index,
                "distance": round((source.position - listener).length(), 6),
                "attenuation": round(attenuation, 6),
                "gain": source.gain,
                "bus": source.bus,
                "audible": attenuation > 0.0 and source.gain > 0.0,
            }
        )
    audible = sum(1 for entry in entries if entry["audible"])
    return {
        "schema": 1,
        "listener": [listener.x, listener.y, listener.z],
        "sources": entries,
        "audible": audible,
        "silent": len(entries) - audible,
    }
