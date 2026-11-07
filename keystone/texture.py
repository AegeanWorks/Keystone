"""Immutable RGBA texture data and dependency-free texture sources."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

from keystone.png import read_png

Color = tuple[float, float, float]


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
