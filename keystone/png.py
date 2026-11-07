"""Minimal dependency-free PNG writer for headless frame captures."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from keystone.serialization import write_bytes_atomic

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _paeth(a: int, b: int, c: int) -> int:
    estimate = a + b - c
    pa, pb, pc = abs(estimate - a), abs(estimate - b), abs(estimate - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def read_png(path: str | Path) -> tuple[int, int, bytes]:
    """Read an 8-bit RGBA non-interlaced PNG and return top-down pixels."""
    data = Path(path).read_bytes()
    if not data.startswith(SIGNATURE):
        raise ValueError("not a PNG file")
    offset = len(SIGNATURE)
    width = height = 0
    compressed = bytearray()
    compressed_idat = False
    saw_iend = False
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        if length > len(data) - offset - 12:
            raise ValueError("PNG chunk exceeds the file length")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        stored_crc = struct.unpack(">I", data[offset + 8 + length : offset + 12 + length])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != stored_crc:
            raise ValueError(f"PNG chunk {kind!r} failed CRC check")
        offset += 12 + length
        if kind == b"IHDR":
            try:
                width, height, depth, color, compression, filter_method, interlace = struct.unpack(">IIBBBBB", payload)
            except struct.error as exc:
                raise ValueError(f"PNG IHDR is corrupt: {exc}") from exc
            if depth != 8 or color != 6 or compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("only 8-bit non-interlaced RGBA PNGs are supported")
        elif kind == b"IDAT":
            compressed.extend(payload)
            compressed_idat = True
        elif kind == b"IEND":
            saw_iend = True
            break
    if not saw_iend:
        raise ValueError("PNG has no IEND chunk")
    if width <= 0 or height <= 0 or not compressed_idat:
        raise ValueError("PNG has no valid IHDR/IDAT")
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as exc:
        raise ValueError(f"PNG IDAT is corrupt: {exc}") from exc
    stride = width * 4
    rows: list[bytes] = []
    previous = bytes(stride)
    position = 0
    for _ in range(height):
        if position >= len(raw):
            raise ValueError("PNG data is truncated")
        filter_type = raw[position]
        position += 1
        row = bytearray(raw[position : position + stride])
        if len(row) != stride:
            raise ValueError("PNG data is truncated")
        position += stride
        for index in range(stride):
            left = row[index - 4] if index >= 4 else 0
            up = previous[index]
            upper_left = previous[index - 4] if index >= 4 else 0
            if filter_type == 0:
                continue
            if filter_type == 1:
                row[index] = (row[index] + left) & 0xFF
            elif filter_type == 2:
                row[index] = (row[index] + up) & 0xFF
            elif filter_type == 3:
                row[index] = (row[index] + ((left + up) >> 1)) & 0xFF
            elif filter_type == 4:
                row[index] = (row[index] + _paeth(left, up, upper_left)) & 0xFF
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}")
        rows.append(bytes(row))
        previous = bytes(row)
    return width, height, b"".join(rows)


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
    write_bytes_atomic(path, data)
