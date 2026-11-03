"""Unit tests for the stdlib PNG writer used by headless screenshots."""

import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from keystone.png import read_png, write_png

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
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            write_png(Path(directory) / "bad.png", 2, 2, b"\x00" * 8)

    def test_reader_round_trips_writer_pixels(self):
        pixels = bytes((1, 2, 3, 255, 4, 5, 6, 255, 7, 8, 9, 255, 10, 11, 12, 255))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roundtrip.png"
            write_png(path, 2, 2, pixels)
            width, height, restored = read_png(path)
            self.assertEqual((width, height), (2, 2))
            self.assertEqual(
                restored,
                bytes((7, 8, 9, 255, 10, 11, 12, 255, 1, 2, 3, 255, 4, 5, 6, 255)),
            )

    def test_reader_rejects_non_png(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.png"
            path.write_bytes(b"not a png")
            with self.assertRaises(ValueError):
                read_png(path)

    def test_creates_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "shot.png"
            write_png(path, 1, 1, bytes((1, 2, 3, 4)))
            self.assertTrue(path.exists())

    def test_reader_rejects_bad_crc(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shot.png"
            write_png(path, 2, 2, bytes((1, 2, 3, 255)) * 4)
            data = bytearray(path.read_bytes())
            data[-1] ^= 0xFF
            path.write_bytes(bytes(data))
            with self.assertRaises(ValueError):
                read_png(path)

    def test_reader_wraps_corrupt_idat_as_value_error(self):
        from keystone.png import SIGNATURE, _chunk

        header = struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0)
        bad = SIGNATURE + _chunk(b"IHDR", header) + _chunk(b"IDAT", b"not compressed") + _chunk(b"IEND", b"")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.png"
            path.write_bytes(bad)
            # zlib.error is not a ValueError subclass, so this also proves the wrap.
            with self.assertRaises(ValueError):
                read_png(path)


if __name__ == "__main__":
    unittest.main()
