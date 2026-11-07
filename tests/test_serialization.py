"""Tests for atomic JSON persistence."""

import tempfile
import threading
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

    def test_non_finite_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            with self.assertRaises(ValueError):
                write_json_atomic(path, {"value": float("nan")})
            self.assertFalse(path.exists())

    def test_concurrent_writers_use_distinct_temp_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            errors: list[BaseException] = []
            barrier = threading.Barrier(4)

            def save(index: int) -> None:
                try:
                    barrier.wait(timeout=5)
                    write_json_atomic(path, {"writer": index}, backup=False)
                except BaseException as exc:  # noqa: BLE001 - collect thread failures
                    errors.append(exc)

            threads = [threading.Thread(target=save, args=(index,)) for index in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            self.assertEqual(errors, [])
            self.assertIn(read_json(path)["writer"], {0, 1, 2, 3})


if __name__ == "__main__":
    unittest.main()
