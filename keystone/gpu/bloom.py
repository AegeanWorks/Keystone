"""Deterministic emissive-aware bloom glow (luminance threshold, in-shader, no FBO).

Pure-CPU glow math is GL-free and unit-tested; the renderer applies the
identical formula in GLSL after the sRGB encode and before the post grade.
Threshold is on display-referred luminance so the unmodified CubeDemo
(bright orb, lit cubes, zero emissive) still exceeds it. Diffusion adds
a fixed separable blur chain (bright-pass + H + V + composite) with the
same threshold; kernel weights are frozen. No wall-clock,
no randomness, no genre logic.
"""

from __future__ import annotations

BLOOM_THRESHOLD = 0.72
BLOOM_KNEE = 0.12
BLOOM_INTENSITY = 0.35
BLOOM_TAPS = 5
BLOOM_WEIGHTS = (0.227027, 0.3162162162, 0.0702702703)
BLOOM_OFFSETS = (0.0, 1.3846153846, 3.2307692308)
BLOOM_DOWNSAMPLE = 0.5
BLOOM_PASSES = 3

__all__ = [
    "BLOOM_DOWNSAMPLE",
    "BLOOM_INTENSITY",
    "BLOOM_KNEE",
    "BLOOM_OFFSETS",
    "BLOOM_PASSES",
    "BLOOM_TAPS",
    "BLOOM_THRESHOLD",
    "BLOOM_WEIGHTS",
    "bloom_blur_size",
    "bloom_color",
    "bloom_composite",
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


def bloom_blur_size(width: int, height: int, downsample: float = BLOOM_DOWNSAMPLE) -> tuple[int, int]:
    """Return the deterministic half-res blur size for a framebuffer."""
    if width <= 0 or height <= 0:
        raise ValueError("bloom blur size needs positive dimensions")
    return (max(1, int(width * float(downsample))), max(1, int(height * float(downsample))))


def bloom_composite(
    scene: tuple[float, float, float],
    blurred: tuple[float, float, float],
    intensity: float = BLOOM_INTENSITY,
) -> tuple[float, float, float]:
    """Add blurred light to the scene color with 0..1 clamp."""
    factor = float(intensity)
    return (
        max(0.0, min(1.0, float(scene[0]) + float(blurred[0]) * factor)),
        max(0.0, min(1.0, float(scene[1]) + float(blurred[1]) * factor)),
        max(0.0, min(1.0, float(scene[2]) + float(blurred[2]) * factor)),
    )
