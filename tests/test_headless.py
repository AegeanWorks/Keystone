"""Tests for no-OpenGL simulation and action scripts."""

import json
import tempfile
import unittest
from pathlib import Path

from keystone.headless import load_actions, run_simulation
from keystone.input import ActionState
from keystone.samples import CubeDemo


class HeadlessTest(unittest.TestCase):
    def test_simulation_advances_without_a_window(self):
        game = CubeDemo()
        game.build_scene()
        result = run_simulation(game, frames=3, actions=[ActionState(forward=1.0)])
        self.assertEqual(result["frames"], 3)
        self.assertAlmostEqual(result["final"]["time"], 3.0 / 60.0, places=4)
        self.assertIn("hash", result)

    def test_same_script_is_deterministic(self):
        first = run_simulation(CubeDemo(), 4, [ActionState(forward=1.0, look_yaw=0.1)])
        second = run_simulation(CubeDemo(), 4, [ActionState(forward=1.0, look_yaw=0.1)])
        self.assertEqual(first["hash"], second["hash"])

    def test_trace_contains_each_frame(self):
        result = run_simulation(CubeDemo(), 3, trace=True)
        self.assertEqual(len(result["trace"]), 3)

    def test_load_actions_accepts_list_and_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actions.json"
            path.write_text(json.dumps([{"forward": 1.0}]), encoding="utf-8")
            self.assertEqual(load_actions(path)[0].forward, 1.0)
            path.write_text(json.dumps({"actions": [{"right": 1.0}]}), encoding="utf-8")
            self.assertEqual(load_actions(path)[0].right, 1.0)

    def test_load_actions_pins_bad_item_index(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actions.json"
            path.write_text(json.dumps([{"forward": 1.0}, 5]), encoding="utf-8")
            with self.assertRaises(TypeError) as caught:
                load_actions(path)
            self.assertIn("actions[1]", str(caught.exception))

    def test_load_actions_rejects_command_logs(self):
        from keystone.replay import CommandLog

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log.json"
            CommandLog(seed=9).save(path)
            with self.assertRaises(ValueError) as caught:
                load_actions(path)
            self.assertIn("--replay", str(caught.exception))

    def test_invalid_frames_and_step(self):
        with self.assertRaises(ValueError):
            run_simulation(CubeDemo(), -1)
        with self.assertRaises(ValueError):
            run_simulation(CubeDemo(), 1, step=0.0)
        with self.assertRaises(ValueError):
            run_simulation(CubeDemo(), 1, step=float("nan"))
        with self.assertRaises(ValueError):
            run_simulation(CubeDemo(), 1, step=float("inf"))


if __name__ == "__main__":
    unittest.main()
