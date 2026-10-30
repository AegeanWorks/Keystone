"""Unit tests for the stdlib PNG writer used by headless screenshots."""

import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from keystone.png import write_png

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    chunks = []
    offset = len(SIGNATURE)
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        chunks.append((kind, payload))
        offset += 12 + length
    return chunks


class PngTest(unittest.TestCase):
    def test_round_trip_pixels_and_header(self):
        pixels = bytes(
            (
                255, 0, 0, 255,
                0, 255, 0, 255,
                0, 0, 255, 255,
                255, 255, 0, 255,
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shot.png"
            write_png(path, 2, 2, pixels)
            data = path.read_bytes()
            self.assertTrue(data.startswith(SIGNATURE))
            chunks = dict(_chunks(data))
            width, height = struct.unpack(">II", chunks[b"IHDR"][:8])
            self.assertEqual((width, height), (2, 2))
            raw = zlib.decompress(chunks[b"IDAT"])
            self.assertEqual(
                raw,
                b"\x00" + bytes((0, 0, 255, 255, 255, 255, 0, 255))
                + b"\x00" + bytes((255, 0, 0, 255, 0, 255, 0, 255)),
            )

    def test_rejects_wrong_pixel_count(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                write_png(Path(directory) / "bad.png", 2, 2, b"\x00" * 8)

    def test_creates_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "shot.png"
            write_png(path, 1, 1, bytes((1, 2, 3, 4)))
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
