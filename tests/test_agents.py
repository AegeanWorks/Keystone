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
