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

    def test_repeated_script_does_not_repeat_edges(self):
        from keystone.scene import Scene

        class Recorder:
            name = "edge-recorder"

            def __init__(self):
                self.pressed = 0
                self.clicked = 0

            def build_scene(self):
                return Scene()

            def update(self, dt, actions):
                self.pressed += int("jump" in actions.pressed)
                self.clicked += int(actions.mouse_clicked)

            def snapshot(self):
                return {"pressed": self.pressed, "clicked": self.clicked}

            def actions(self):
                return {"buttons": ["jump"]}

            def status(self):
                return "recorder"

        game = Recorder()
        result = run_simulation(
            game,
            3,
            [ActionState(pressed=frozenset({"jump"}), mouse_clicked=True)],
        )
        self.assertEqual(result["final"], {"pressed": 1, "clicked": 1})
        self.assertEqual(result["actions"][0]["pressed"], ["jump"])
        self.assertEqual(result["actions"][1]["pressed"], [])
        self.assertFalse(result["actions"][1]["mouse_clicked"])

    def test_run_simulation_rejects_non_scene_build(self):
        class NoScene:
            name = "no-scene"

            def build_scene(self):
                return None

            def update(self, dt, actions):
                return None

            def snapshot(self):
                return {}

            def actions(self):
                return {}

            def status(self):
                return "no-scene"

        with self.assertRaises(TypeError) as caught:
            run_simulation(NoScene(), 1)
        self.assertIn("must return a Scene", str(caught.exception))

    def test_trace_snapshots_are_independent(self):
        from keystone.scene import Scene

        class CachedSnapshotGame:
            name = "cached"

            def __init__(self):
                self.state = {"time": 0.0}

            def build_scene(self):
                return Scene()

            def update(self, dt, actions):
                self.state["time"] += dt

            def snapshot(self):
                return self.state

            def actions(self):
                return {}

            def status(self):
                return "cached"

        result = run_simulation(CachedSnapshotGame(), 3, trace=True)
        times = [entry["time"] for entry in result["trace"]]
        self.assertEqual(len(set(times)), 3)
        self.assertAlmostEqual(times[0], 1 / 60, places=6)
        self.assertAlmostEqual(times[-1], 3 / 60, places=6)

    def test_load_actions_rejects_non_finite_and_bad_mouse_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actions.json"
            for payload in (
                [{"forward": float("nan")}],
                [{"look_yaw": float("inf")}],
                [{"mouse_clicked": "false"}],
            ):
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises((TypeError, ValueError), msg=repr(payload)):
                    load_actions(path)


if __name__ == "__main__":
    unittest.main()
