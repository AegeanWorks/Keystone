"""Deterministic trauma-based camera shake.

Shake is a game-feel layer, not a camera: this module accumulates trauma,
decays it, and samples a position and rotation offset from seeded sine noise.
A game adds trauma on an impact, calls ``update(dt)`` each frame, and applies
``sample()`` to whatever camera or rig it owns. Nothing here mutates a camera,
so a game keeps its own pose ownership and can compose shake with look input.

The noise is a fixed sum of sines with seed-derived phases, which is
deterministic across runs and platforms and needs no random draws per frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from keystone.math3d import Vec3
from keystone.rng import RandomStream

__all__ = ["CameraShake", "ShakeOffset", "shake_report"]


def _finite(label: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


@dataclass(frozen=True, slots=True)
class ShakeOffset:
    """One sampled shake offset: world-ish translation plus yaw and pitch."""

    position: Vec3
    yaw: float
    pitch: float

    def __post_init__(self) -> None:
        if not isinstance(self.position, Vec3):
            raise TypeError("shake offset position must be a Vec3")
        if not all(math.isfinite(component) for component in (self.position.x, self.position.y, self.position.z)):
            raise ValueError("shake offset position must be finite")
        _finite("shake offset yaw", self.yaw)
        _finite("shake offset pitch", self.pitch)


class CameraShake:
    """Accumulate trauma, decay it, and sample a deterministic offset."""

    def __init__(
        self,
        *,
        seed: int = 0,
        amplitude: float = 0.18,
        rotation_amplitude: float = 0.025,
        frequency: float = 16.0,
        decay: float = 1.8,
    ) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("camera shake seed must be an integer")
        self.amplitude = _finite("camera shake amplitude", amplitude)
        if self.amplitude < 0.0:
            raise ValueError("camera shake amplitude must be non-negative")
        self.rotation_amplitude = _finite(
            "camera shake rotation amplitude", rotation_amplitude
        )
        if self.rotation_amplitude < 0.0:
            raise ValueError("camera shake rotation amplitude must be non-negative")
        self.frequency = _finite("camera shake frequency", frequency)
        if self.frequency <= 0.0:
            raise ValueError("camera shake frequency must be positive")
        self.decay = _finite("camera shake decay", decay)
        if self.decay <= 0.0:
            raise ValueError("camera shake decay must be positive")
        rng = RandomStream(seed)
        self._phases = tuple(rng.random() * math.tau for _ in range(12))
        self.trauma = 0.0
        self.elapsed = 0.0

    def add(self, amount: float) -> None:
        """Add trauma, clamped to the unit range."""
        value = _finite("camera shake trauma", amount)
        if value < 0.0:
            raise ValueError("camera shake trauma must be non-negative")
        self.trauma = min(1.0, self.trauma + value)

    def update(self, dt: float) -> None:
        """Advance time and decay trauma linearly."""
        seconds = _finite("camera shake dt", dt)
        if seconds < 0.0:
            raise ValueError("camera shake dt must be non-negative")
        self.elapsed += seconds
        self.trauma = max(0.0, self.trauma - self.decay * seconds)

    def reset(self) -> None:
        """Clear trauma and elapsed time."""
        self.trauma = 0.0
        self.elapsed = 0.0

    def _noise(self, channel: int, multiplier: float) -> float:
        angle = self.elapsed * self.frequency * math.tau
        first = math.sin(angle + self._phases[channel])
        second = math.sin(angle * 1.73 + self._phases[channel + 1])
        return (0.6 * first + 0.4 * second) * multiplier

    def sample(self) -> ShakeOffset:
        """Return the current offset; zero trauma is exactly zero."""
        strength = self.trauma * self.trauma
        if strength <= 0.0:
            return ShakeOffset(Vec3(), 0.0, 0.0)
        position = Vec3(
            self._noise(0, strength * self.amplitude),
            self._noise(2, strength * self.amplitude),
            self._noise(4, strength * self.amplitude * 0.5),
        )
        return ShakeOffset(
            position,
            self._noise(6, strength * self.rotation_amplitude),
            self._noise(8, strength * self.rotation_amplitude),
        )


def shake_report(shake: CameraShake) -> dict:
    """Return a JSON-safe summary of a shake state and its current offset."""
    if not isinstance(shake, CameraShake):
        raise TypeError("shake_report needs a CameraShake")
    offset = shake.sample()
    return {
        "schema": 1,
        "trauma": round(shake.trauma, 6),
        "position": [
            round(offset.position.x, 6),
            round(offset.position.y, 6),
            round(offset.position.z, 6),
        ],
        "yaw": round(offset.yaw, 6),
        "pitch": round(offset.pitch, 6),
    }
