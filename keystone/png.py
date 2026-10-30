"""Minimal dependency-free PNG writer for headless frame captures."""

from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def write_png(path: str | Path, width: int, height: int, rgba: bytes, flip_vertical: bool = True) -> None:
    """Write RGBA bytes (OpenGL order: bottom-up) as an 8-bit PNG."""
    if width <= 0 or height <= 0:
        raise ValueError("PNG width and height must be positive")
    if len(rgba) != width * height * 4:
        raise ValueError(
            f"expected {width * height * 4} RGBA bytes for {width}x{height}, got {len(rgba)}"
        )
    rows = [rgba[row * width * 4 : (row + 1) * width * 4] for row in range(height)]
    if flip_vertical:
        rows.reverse()
    raw = b"".join(b"\x00" + row for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    data = (
        SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 6))
        + _chunk(b"IEND", b"")
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        # hygiene: allow binary PNG payload; text encoding does not apply to bytes
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
