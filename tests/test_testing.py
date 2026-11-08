"""Tests for deterministic AI/CI scenario helpers."""

import unittest
from dataclasses import replace

from keystone.input import ActionState
from keystone.math3d import Vec3
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import Node, Scene
from keystone.testing import (
    assert_deterministic,
    assert_scene_budget,
    run_script,
    scene_fingerprint,
    verify_determinism,
)


class SceneBudgetTest(unittest.TestCase):
    def _scene(self, count: int) -> Scene:
        scene = Scene()
        for index in range(count):
            node = scene.add(Node(f"n{index}", id=f"n{index}"))
            node.mesh = cube(1.0)
        return scene

    def test_fingerprint_is_stable_and_name_independent(self):
        first = scene_fingerprint(self._scene(3))
        second = scene_fingerprint(self._scene(3))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, scene_fingerprint(self._scene(4)))

    def test_fingerprint_changes_when_a_transform_changes(self):
        scene = self._scene(2)
        before = scene_fingerprint(scene)
        node = scene.find_by_id("n0")
        assert node is not None
        node.transform = replace(node.transform, position=Vec3(1, 2, 3))
        self.assertNotEqual(before, scene_fingerprint(scene))

    def test_budget_passes_under_the_limits(self):
        report = assert_scene_budget(self._scene(2), max_nodes=5, max_triangles=100)
        self.assertEqual(report["nodes"], 2)
        self.assertLessEqual(report["triangles"], 100)

    def test_budget_fails_over_the_limit_with_a_clear_message(self):
        with self.assertRaises(AssertionError) as caught:
            assert_scene_budget(self._scene(4), max_nodes=2)
        self.assertIn("nodes", str(caught.exception))

    def test_budget_rejects_bad_limits(self):
        scene = self._scene(1)
        for kwargs in (
            {"max_nodes": -1},
            {"max_triangles": -5},
            {"max_nodes": True},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                assert_scene_budget(scene, **kwargs)


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
