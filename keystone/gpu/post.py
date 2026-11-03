"""Deterministic post color-grade (exposure + vignette, in-shader, no FBO).

Pure-CPU grade math is GL-free and unit-tested; the renderer applies the
identical formula in GLSL after the sRGB encode and before the UI overlay.
No wall-clock, no randomness, no genre logic.
"""

from __future__ import annotations

POST_EXPOSURE = 1.12
POST_VIGNETTE = 0.28

__all__ = [
    "POST_EXPOSURE",
    "POST_VIGNETTE",
    "grade_color",
    "vignette_factor",
]


def vignette_factor(nx: float, ny: float, strength: float = POST_VIGNETTE) -> float:
    """Return the deterministic vignette multiplier for normalized coords 0..1."""
    dx = float(nx) - 0.5
    dy = float(ny) - 0.5
    factor = 1.0 - float(strength) * (dx * dx + dy * dy) * 2.0
    return max(0.0, min(1.0, factor))


def grade_color(
    color: tuple[float, float, float],
    nx: float,
    ny: float,
    exposure: float = POST_EXPOSURE,
    strength: float = POST_VIGNETTE,
) -> tuple[float, float, float]:
    """Apply exposure then vignette to a display-referred 0..1 RGB triple."""
    factor = vignette_factor(nx, ny, strength)
    graded = tuple(
        max(0.0, min(1.0, float(channel) * float(exposure) * factor))
        for channel in color
    )
    return (graded[0], graded[1], graded[2])
