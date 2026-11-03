"""Tests for atomic JSON persistence."""

import tempfile
import unittest
from pathlib import Path

from keystone.serialization import read_json, write_json_atomic


class SerializationTest(unittest.TestCase):
    def test_round_trip_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            write_json_atomic(path, {"value": 1})
            self.assertEqual(read_json(path), {"value": 1})
            write_json_atomic(path, {"value": 2})
            self.assertEqual(read_json(path), {"value": 2})
            self.assertEqual(read_json(path.with_name("state.json.bak")), {"value": 1})
            self.assertFalse(path.with_name("state.json.tmp").exists())

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(FileNotFoundError):
            read_json(Path(directory) / "missing.json")

    def test_bom_prefixed_file_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            write_json_atomic(path, {"value": 1})
            path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
            self.assertEqual(read_json(path), {"value": 1})


if __name__ == "__main__":
    unittest.main()
