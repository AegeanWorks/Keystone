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

    def test_invalid_frames_and_step(self):
        with self.assertRaises(ValueError):
            run_simulation(CubeDemo(), -1)
        with self.assertRaises(ValueError):
            run_simulation(CubeDemo(), 1, step=0.0)


if __name__ == "__main__":
    unittest.main()
