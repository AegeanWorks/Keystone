"""Tests for deterministic AI/CI scenario helpers."""

import unittest

from keystone.input import ActionState
from keystone.samples import CubeDemo
from keystone.testing import assert_deterministic, run_script, verify_determinism


class TestingHelpersTest(unittest.TestCase):
    def test_run_script_uses_action_count_by_default(self):
        result = run_script(CubeDemo(), [ActionState(forward=1.0), ActionState(forward=0.0)])
        self.assertEqual(result["frames"], 2)

    def test_verify_determinism_passes_for_the_sample(self):
        result = verify_determinism(lambda: CubeDemo(), [ActionState(forward=1.0)], frames=3)
        self.assertTrue(result["ok"])
        self.assertEqual(result["first"], result["second"])

    def test_assert_deterministic_returns_evidence(self):
        result = assert_deterministic(lambda: CubeDemo(), [ActionState(look_yaw=0.1)], frames=2)
        self.assertTrue(result["ok"])
        self.assertIn("hash", result)

    def test_scene_loader_runs_for_each_determinism_pass(self):
        calls = []

        def loader(game, scene):
            calls.append(scene)
            scene.background = [0.2, 0.3, 0.4]

        result = verify_determinism(
            lambda: CubeDemo(),
            [ActionState(forward=1.0)],
            frames=2,
            scene_loader=loader,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(calls), 2)
        with self.assertRaises(TypeError):
            run_script(CubeDemo(), [], scene_loader=object())

    def test_trace_mode_is_available(self):
        result = run_script(CubeDemo(), [], frames=2, trace=True)
        self.assertEqual(len(result["trace"]), 2)


if __name__ == "__main__":
    unittest.main()
