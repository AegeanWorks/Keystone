"""Tests for AI observation/action adapters, audit trail and input bindings."""

import tempfile
import unittest
from pathlib import Path

from keystone.agents import AuditTrail, observe, parse_actions, summarize_report
from keystone.analysis import analyze_frame
from keystone.input import ActionState, InputMap
from keystone.samples import CubeDemo


class AgentsTest(unittest.TestCase):
    def test_parse_actions_validates_and_clamps(self):
        actions = parse_actions([{"forward": 5.0, "pressed": ["jump"]}])
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].forward, 1.0)
        self.assertIn("jump", actions[0].pressed)
        with self.assertRaises(ValueError):
            parse_actions([{"unknown_axis": 1.0}])
        with self.assertRaises(ValueError):
            parse_actions([])
        with self.assertRaises(ValueError):
            parse_actions([{"forward": float("nan")}])

    def test_observe_is_deterministic_and_auditable(self):
        first = observe(CubeDemo(), frames=4, actions=[ActionState(forward=1.0)])
        second = observe(CubeDemo(), frames=4, actions=[ActionState(forward=1.0)])
        self.assertEqual(first["hash"], second["hash"])
        self.assertIn("description", first)
        self.assertIn("simulation", first)

    def test_summarize_report_truncates_and_keeps_pbr(self):
        report = analyze_frame(CubeDemo().build_scene(), bytes((0, 0, 0, 255)) * 16, 4, 4)
        summary = summarize_report(report, max_nodes=2)
        self.assertEqual(summary["hash"], report["hash"])
        self.assertTrue(summary["truncated"] or len(summary["nodes"]) <= 2)
        with_material = [node for node in summary["nodes"] if node.get("material")]
        self.assertTrue(with_material)
        self.assertIn("metallic", with_material[0]["material"])

    def test_audit_trail_appends_and_verifies(self):
        trail = AuditTrail()
        first = trail.record("simulate", {"frames": 4})
        second = trail.record("render", {"nodes": 6})
        self.assertEqual(second["previous"], first["hash"])
        self.assertTrue(trail.verify())
        trail.entries[0]["payload"] = {"frames": 999}
        self.assertFalse(trail.verify())

    def test_audit_trail_loads_and_detects_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            AuditTrail(path).record("simulate", {"frames": 4})
            second = AuditTrail(path)
            second.record("render", {"nodes": 6})
            self.assertEqual(len(second.entries), 2)
            self.assertTrue(second.verify())
            del second.entries[-1]
            self.assertFalse(second.verify())

    def test_observe_builds_scene_before_snapshot(self):
        from keystone.scene import Scene

        class BuildFirst:
            name = "build-first"

            def __init__(self):
                self.scene = None

            def build_scene(self):
                self.scene = Scene()
                return self.scene

            def update(self, dt, actions):
                return None

            def snapshot(self):
                if self.scene is None:
                    raise RuntimeError("snapshot before build")
                return {"time": 0.0}

            def actions(self):
                return {}

            def status(self):
                return "build-first"

        observation = observe(BuildFirst(), frames=1)
        self.assertEqual(observation["game"], "build-first")

    def test_input_bindings_round_trip(self):
        bindings = InputMap()
        bindings.bind("dash", "left_shift")
        self.assertEqual(bindings.list_actions()["dash"], "left_shift")
        document = bindings.to_dict()
        restored = InputMap.from_dict(document)
        self.assertEqual(restored.list_actions()["dash"], "left_shift")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bindings.json"
            bindings.save_bindings(path)
            loaded = InputMap.load_bindings(path)
            self.assertEqual(loaded.list_actions()["dash"], "left_shift")
        with self.assertRaises(ValueError):
            bindings.bind("", "w")


if __name__ == "__main__":
    unittest.main()
