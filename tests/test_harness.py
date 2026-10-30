"""Tests for the deterministic JSON AI harness."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from keystone.harness import catalog, main, run_actions, selftest


class HarnessApiTest(unittest.TestCase):
    def test_catalog_describes_actions_and_state(self):
        payload = catalog()
        self.assertTrue(payload["ok"])
        self.assertIn("move", payload["actions"])
        self.assertIn("hash", " ".join(payload["state_keys"]) + " hash")
        self.assertEqual(payload["limits"]["step"], 1.0 / 60.0)

    def test_actions_are_deterministic(self):
        actions = [
            {"action": "move", "forward": 1.0, "seconds": 0.5},
            {"action": "turn", "yaw": 45.0},
            {"action": "wait", "seconds": 0.25},
        ]
        first = run_actions(7, actions, size=32)
        second = run_actions(7, actions, size=32)
        self.assertEqual(first["hash"], second["hash"])
        self.assertEqual(first["final"], second["final"])

    def test_seed_changes_the_run(self):
        actions = [{"action": "wait", "seconds": 0.1}]
        self.assertNotEqual(run_actions(7, actions, size=32)["hash"], run_actions(8, actions, size=32)["hash"])

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            run_actions(7, [{"action": "teleport"}], size=32)
        self.assertIn("unknown action", str(caught.exception))

    def test_invalid_seconds_is_rejected(self):
        with self.assertRaises(ValueError):
            run_actions(7, [{"action": "move", "seconds": -1.0}], size=32)

    def test_selftest_passes(self):
        report = selftest()
        self.assertTrue(report["ok"])
        self.assertIn("portal entry", report["checks"])
        self.assertIn("exit transition", report["checks"])


class HarnessCliTest(unittest.TestCase):
    def test_catalog_prints_json(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(main(["catalog"]), 0)
        self.assertIn("move", json.loads(buffer.getvalue())["actions"])

    def test_run_reads_actions_and_writes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            actions_path = Path(directory) / "actions.json"
            out_path = Path(directory) / "run.json"
            actions_path.write_text(
                json.dumps([{"action": "move", "forward": 1.0, "seconds": 0.2}]),
                encoding="utf-8",
            )
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["run", "--seed", "7", "--size", "32", "--actions", str(actions_path), "--out", str(out_path)])
            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            self.assertEqual(json.loads(out_path.read_text(encoding="utf-8"))["seed"], 7)

    def test_actions_file_with_a_utf8_bom_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            actions_path = Path(directory) / "actions.json"
            actions_path.write_bytes(
                b"\xef\xbb\xbf" + json.dumps([{"action": "wait", "seconds": 0.1}]).encode("utf-8")
            )
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["run", "--size", "32", "--actions", str(actions_path)])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(buffer.getvalue())["ok"])

    def test_bad_seed_is_a_usage_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            main(["run", "--seed", "-1", "--actions", "actions.json"])
        self.assertEqual(caught.exception.code, 2)

    def test_bad_actions_print_a_triad(self):
        with tempfile.TemporaryDirectory() as directory:
            actions_path = Path(directory) / "actions.json"
            actions_path.write_text('{"actions": [{"action": "fly"}]}', encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(["run", "--actions", str(actions_path)])
            self.assertEqual(code, 1)
            self.assertIn("Why:", stderr.getvalue())
            self.assertIn("Fix:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
