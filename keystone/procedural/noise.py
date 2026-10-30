"""Deterministic integer-hash value noise and fractal sums (no global RNG)."""

_MASK = 0xFFFFFFFF
_INV32 = 1.0 / 4294967296.0


def hash2i(ix: int, iy: int, seed: int) -> int:
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & _MASK
    n = (n ^ (n >> 13)) & _MASK
    n = (n * 1274126177) & _MASK
    n = (n ^ (n >> 16)) & _MASK
    return n


def rand01(ix: int, iy: int, seed: int) -> float:
    return hash2i(ix, iy, seed) * _INV32


def _smooth(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def value_noise(x: float, y: float, seed: int) -> float:
    ix, iy = int(x), int(y)
    fx, fy = _smooth(x - ix), _smooth(y - iy)
    a = rand01(ix, iy, seed)
    b = rand01(ix + 1, iy, seed)
    c = rand01(ix, iy + 1, seed)
    d = rand01(ix + 1, iy + 1, seed)
    ab = a + (b - a) * fx
    cd = c + (d - c) * fx
    return ab + (cd - ab) * fy


def fbm(
    x: float,
    y: float,
    seed: int,
    octaves: int = 4,
    lacunarity: float = 2.0,
    gain: float = 0.5,
) -> float:
    """Fractal Brownian motion in [0, 1], deterministic for a seed."""
    if octaves < 1:
        raise ValueError("fbm needs at least one octave")
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for _ in range(octaves):
        total += value_noise(x * frequency, y * frequency, seed) * amplitude
        norm += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return total / norm
