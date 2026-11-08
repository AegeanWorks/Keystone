"""Immutable RGBA texture data and dependency-free texture sources."""

from __future__ import annotations

import hashlib
import random
import struct
from dataclasses import dataclass
from pathlib import Path

from keystone.png import read_png

Color = tuple[float, float, float]


def _rgba(color: object, label: str) -> bytes:
    """Clamp three linear floats to one opaque RGBA8 tuple."""
    if (
        isinstance(color, (str, bytes))
        or not isinstance(color, (tuple, list))
        or len(color) != 3
    ):
        raise TypeError(f"{label} color must have three channels")
    for channel in color:
        if isinstance(channel, bool) or not isinstance(channel, (int, float)):
            raise TypeError(f"{label} channels must be numbers")
    return bytes(
        max(0, min(255, round(float(channel) * 255.0))) for channel in color
    ) + b"\xff"


def _blend(first: bytes, second: bytes, amount: float) -> bytes:
    """Mix two opaque RGBA8 tuples by ``amount`` (0 = first, 1 = second)."""
    return bytes(
        round(a + (b - a) * amount) for a, b in zip(first, second)
    )


def _cell(size: int, base: bytes, accent: bytes, seed: int) -> bytes:
    """One flat color for every pixel."""
    return base * (size * size)


def _grid(size: int, base: bytes, accent: bytes, seed: int) -> bytes:
    """Thin lattice of accent lines every eighth of the texture."""
    step = max(4, size // 8)
    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            on_line = x % step == 0 or y % step == 0
            pixels += accent if on_line else base
    return bytes(pixels)


def _panel(size: int, base: bytes, accent: bytes, seed: int) -> bytes:
    """Recessed plate: brighter bevel near the edges, darker centre."""
    inset = max(1, size // 16)
    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            edge = min(x, y, size - 1 - x, size - 1 - y)
            if edge < inset:
                pixels += _blend(base, accent, 0.55)
            elif edge < inset * 2:
                pixels += _blend(base, accent, 0.25)
            else:
                pixels += base
    return bytes(pixels)


def _rivets(size: int, base: bytes, accent: bytes, seed: int) -> bytes:
    """A panel with four corner studs."""
    pixels = bytearray(_panel(size, base, accent, seed))
    radius = max(1, size // 16)
    centres = (
        (radius * 2, radius * 2),
        (size - 1 - radius * 2, radius * 2),
        (radius * 2, size - 1 - radius * 2),
        (size - 1 - radius * 2, size - 1 - radius * 2),
    )
    for centre_x, centre_y in centres:
        for y in range(size):
            for x in range(size):
                if (x - centre_x) ** 2 + (y - centre_y) ** 2 <= radius * radius:
                    offset = (y * size + x) * 4
                    pixels[offset : offset + 4] = _blend(accent, base, 0.15)
    return bytes(pixels)


def _noise(size: int, base: bytes, accent: bytes, seed: int) -> bytes:
    """Seeded speckle; the same seed always yields the same pixels."""
    rng = random.Random(seed)
    pixels = bytearray()
    for _ in range(size * size):
        amount = rng.random()
        pixels += _blend(base, accent, amount * amount)
    return bytes(pixels)


_PATTERNS = {
    "cell": _cell,
    "grid": _grid,
    "panel": _panel,
    "rivets": _rivets,
    "noise": _noise,
}


@dataclass(frozen=True, slots=True)
class TextureData:
    """Top-down RGBA8 pixels with a stable name for reports and debugging."""

    width: int
    height: int
    rgba: bytes
    name: str = ""

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("texture width and height must be positive")
        if not isinstance(self.rgba, bytes):
            raise TypeError("texture rgba must be immutable bytes")
        if len(self.rgba) != self.width * self.height * 4:
            raise ValueError(
                f"expected {self.width * self.height * 4} RGBA bytes "
                f"for {self.width}x{self.height}, got {len(self.rgba)}"
            )

    def sha256(self) -> str:
        """Return a stable digest of the shape plus the pixel payload."""
        return hashlib.sha256(struct.pack(">II", self.width, self.height) + self.rgba).hexdigest()

    @classmethod
    def from_png(cls, path: str | Path, name: str | None = None) -> TextureData:
        """Load an 8-bit RGBA non-interlaced PNG through the dependency-free reader."""
        source = Path(path)
        width, height, rgba = read_png(source)
        return cls(width, height, rgba, name or source.stem)

    @classmethod
    def from_png_bytes(cls, data: bytes, name: str = "texture") -> TextureData:
        """Load an 8-bit RGBA non-interlaced PNG from bytes."""
        import os
        import tempfile
        from pathlib import Path

        descriptor, temporary_name = tempfile.mkstemp(suffix=".png")
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
            temporary = Path(temporary_name)
            width, height, rgba = read_png(temporary)
        finally:
            try:
                Path(temporary_name).unlink()
            except OSError:  # hygiene: allow best-effort cleanup of a temporary file
                pass
        return cls(width, height, rgba, name)

    @classmethod
    def pattern(
        cls,
        preset: str,
        size: int = 64,
        dark: Color = (0.10, 0.12, 0.16),
        light: Color = (0.18, 0.20, 0.25),
        seed: int = 0,
        name: str | None = None,
    ) -> TextureData:
        """Build a deterministic procedural texture without an image file.

        Presets: ``grid`` (thin lattice), ``panel`` (recessed plate with a
        bevel), ``rivets`` (panel plus corner studs), ``noise`` (seeded
        speckle). The same arguments always produce the same pixels, so a
        texture digest stays stable across runs.
        """
        if preset not in _PATTERNS:
            raise ValueError(
                f"unknown texture pattern {preset!r}; "
                f"use one of {sorted(_PATTERNS)}"
            )
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ValueError("pattern size must be a positive integer")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("pattern seed must be an integer")
        base = _rgba(dark, "pattern dark")
        accent = _rgba(light, "pattern light")
        pixels = _PATTERNS[preset](size, base, accent, seed)
        return cls(size, size, pixels, name or f"pattern-{preset}")

    @classmethod
    def checker(
        cls,
        size: int = 64,
        dark: Color = (0.10, 0.12, 0.16),
        light: Color = (0.18, 0.20, 0.25),
        cell: int = 8,
        name: str = "checker",
    ) -> TextureData:
        """Build a deterministic RGBA checker texture without an image file."""
        if size <= 0 or cell <= 0:
            raise ValueError("checker size and cell must be positive")
        for label, color in (("dark", dark), ("light", light)):
            if isinstance(color, (str, bytes)) or not isinstance(color, (tuple, list)) or len(color) != 3:
                raise TypeError(f"checker {label} color must have three channels")
        dark_rgba = tuple(max(0, min(255, round(channel * 255.0))) for channel in dark) + (255,)
        light_rgba = tuple(max(0, min(255, round(channel * 255.0))) for channel in light) + (255,)
        pixels = bytearray(size * size * 4)
        for y in range(size):
            for x in range(size):
                color = light_rgba if (x // cell + y // cell) % 2 == 0 else dark_rgba
                offset = (y * size + x) * 4
                pixels[offset : offset + 4] = bytes(color)
        return cls(size, size, bytes(pixels), name)
