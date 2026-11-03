"""Deterministic GPU point-sprite math: size attenuation and soft alpha.

GL-free oracle mirroring the sprite vertex/fragment shaders. Games own
emission through ``keystone.particles``; this module owns only how one
live particle maps to one billboarded quad (offset, world size, alpha).
No window, GL context or third-party dependency is required.
"""

from __future__ import annotations

import math

from keystone.math3d import Vec3

__all__ = [
    "SPRITE_ATTEN",
    "SPRITE_COLOR",
    "SPRITE_MAX_SIZE",
    "SPRITE_MIN_SIZE",
    "billboard_corners",
    "soft_alpha",
    "sprite_alpha",
    "sprite_scale",
]

#: Fixed perspective attenuation factor (world_size * ATTEN / distance).
SPRITE_ATTEN = 180.0
#: Pixel-size clamp range for one sprite (deterministic on every GPU).
SPRITE_MAX_SIZE = 64.0
SPRITE_MIN_SIZE = 1.0
#: Warm display-referred sprite tint (matches shader uniform default).
SPRITE_COLOR = (1.0, 0.9, 0.7)


def sprite_scale(distance: float, size: float) -> float:
    """Return the deterministic pixel size for a particle."""
    if not math.isfinite(distance) or not math.isfinite(size):
        raise ValueError("distance and size must be finite")
    dist = max(float(distance), 0.1)
    pixels = float(size) * SPRITE_ATTEN / dist
    return min(max(pixels, SPRITE_MIN_SIZE), SPRITE_MAX_SIZE)


def soft_alpha(u: float, v: float) -> float:
    """Return the soft-circle coverage for quad UVs in [0, 1]."""
    if not math.isfinite(u) or not math.isfinite(v):
        raise ValueError("uv must be finite")
    dx = float(u) - 0.5
    dy = float(v) - 0.5
    radius = math.sqrt(dx * dx + dy * dy) * 2.0
    return min(max(1.0 - radius, 0.0), 1.0)


def sprite_alpha(age: float, lifetime: float, u: float = 0.5, v: float = 0.5) -> float:
    """Return the combined fade * soft-circle alpha for one particle."""
    if not math.isfinite(age) or not math.isfinite(lifetime):
        raise ValueError("age and lifetime must be finite")
    if lifetime <= 0.0:
        raise ValueError("lifetime must be positive")
    fade = min(max(1.0 - float(age) / float(lifetime), 0.0), 1.0)
    return fade * soft_alpha(u, v)


def billboard_corners(center: Vec3, right: Vec3, up: Vec3, world_size: float) -> tuple[Vec3, ...]:
    """Return the four world corners for a camera-facing quad."""
    if world_size < 0.0 or not math.isfinite(world_size):
        raise ValueError("world_size must be a finite non-negative number")
    half = float(world_size) * 0.5
    return (
        center - right * half - up * half,
        center + right * half - up * half,
        center + right * half + up * half,
        center - right * half + up * half,
    )
