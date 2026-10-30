"""Tests for the space harness."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from keystone.space_harness import catalog, main, run_actions, selftest


class SpaceHarnessTest(unittest.TestCase):
    def test_catalog_exposes_flight_scan_and_jump(self):
        payload = catalog()
        self.assertEqual(payload["mode"], "space")
        for action in ("fly", "scan", "jump"):
            self.assertIn(action, payload["actions"])

    def test_actions_are_deterministic(self):
        actions = [{"action": "fly", "forward": 1.0, "seconds": 0.25}, {"action": "turn", "yaw": 30.0}]
        self.assertEqual(run_actions(7, actions)["hash"], run_actions(7, actions)["hash"])
        self.assertNotEqual(run_actions(7, actions)["hash"], run_actions(8, actions)["hash"])

    def test_invalid_action_is_rejected(self):
        with self.assertRaises(ValueError):
            run_actions(7, [{"action": "warp"}])

    def test_selftest(self):
        report = selftest()
        self.assertTrue(report["ok"])
        self.assertIn("body scan", report["checks"])
        self.assertIn("gate jump", report["checks"])

    def test_cli_catalog_and_run(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(main(["catalog"]), 0)
        self.assertEqual(json.loads(buffer.getvalue())["mode"], "space")
        with tempfile.TemporaryDirectory() as directory:
            actions = Path(directory) / "actions.json"
            out = Path(directory) / "run.json"
            actions.write_text(json.dumps([{"action": "wait", "seconds": 0.1}]), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", "--seed", "7", "--actions", str(actions), "--out", str(out)]), 0)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
