"""Tests for deterministic action logs and stable hashes."""

import tempfile
import unittest
from pathlib import Path

from keystone.input import ActionState
from keystone.replay import CommandLog, stable_hash


class ReplayTest(unittest.TestCase):
    def test_hash_ignores_mapping_order(self):
        self.assertEqual(stable_hash({"a": 1, "b": 2}), stable_hash({"b": 2, "a": 1}))
        self.assertNotEqual(stable_hash({"a": 1}), stable_hash({"a": 2}))

    def test_command_log_round_trip(self):
        log = CommandLog(seed=7)
        log.record(ActionState(forward=1.0, pressed=frozenset({"jump"})))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            log.save(path)
            loaded = CommandLog.load(path)
        self.assertEqual(loaded.to_dict(), log.to_dict())
        self.assertEqual(loaded.replay_actions()[0].forward, 1.0)

    def test_invalid_step_is_rejected(self):
        with self.assertRaises(ValueError):
            CommandLog.from_dict({"seed": 1, "step": 0.0, "frames": []})


if __name__ == "__main__":
    unittest.main()
