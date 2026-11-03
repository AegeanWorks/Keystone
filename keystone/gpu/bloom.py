"""Deterministic emissive-aware bloom glow (luminance threshold, in-shader, no FBO).

Pure-CPU glow math is GL-free and unit-tested; the renderer applies the
identical formula in GLSL after the sRGB encode and before the post grade.
Threshold is on display-referred luminance so the unmodified CubeDemo
(bright orb, lit cubes, zero emissive) still exceeds it. No wall-clock,
no randomness, no genre logic.
"""

from __future__ import annotations

BLOOM_THRESHOLD = 0.72
BLOOM_KNEE = 0.12
BLOOM_INTENSITY = 0.35

__all__ = [
    "BLOOM_INTENSITY",
    "BLOOM_KNEE",
    "BLOOM_THRESHOLD",
    "bloom_color",
    "bloom_factor",
]


def bloom_factor(luma: float, threshold: float = BLOOM_THRESHOLD, knee: float = BLOOM_KNEE) -> float:
    """Return the deterministic smoothstep glow weight for one luminance."""
    low = float(threshold)
    high = float(threshold) + float(knee)
    value = float(luma)
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    width = high - low
    if width <= 0.0:
        return 1.0 if value >= low else 0.0
    t = (value - low) / width
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def bloom_color(
    color: tuple[float, float, float],
    threshold: float = BLOOM_THRESHOLD,
    knee: float = BLOOM_KNEE,
    intensity: float = BLOOM_INTENSITY,
) -> tuple[float, float, float]:
    """Add the threshold glow to a display-referred 0..1 RGB triple."""
    r, g, b = (float(color[0]), float(color[1]), float(color[2]))
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    factor = bloom_factor(luma, threshold, knee) * float(intensity)
    glowed = (
        max(0.0, min(1.0, r + r * factor)),
        max(0.0, min(1.0, g + g * factor)),
        max(0.0, min(1.0, b + b * factor)),
    )
    return (glowed[0], glowed[1], glowed[2])
