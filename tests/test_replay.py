"""Tests for deterministic action logs and stable hashes."""

import tempfile
import unittest
from pathlib import Path

from keystone.input import ActionState
from keystone.replay import CommandLog, run_log, stable_hash, verify_log
from keystone.samples import CubeDemo
from keystone.scene import Scene


class ReplayTest(unittest.TestCase):
    def test_hash_ignores_mapping_order(self):
        self.assertEqual(stable_hash({"a": 1, "b": 2}), stable_hash({"b": 2, "a": 1}))
        self.assertNotEqual(stable_hash({"a": 1}), stable_hash({"a": 2}))

    def test_hash_canonicalizes_negative_zero(self):
        self.assertEqual(stable_hash({"x": -0.0}), stable_hash({"x": 0.0}))
        self.assertEqual(stable_hash({"x": [-0.0, {"y": -0.0}]}), stable_hash({"x": [0.0, {"y": 0.0}]}))

    def test_hash_rejects_non_json_and_non_finite_values(self):
        with self.assertRaises(TypeError):
            stable_hash({"set": {"alpha", "beta"}})
        with self.assertRaises(TypeError):
            stable_hash({"object": object()})
        with self.assertRaises(ValueError):
            stable_hash({"nan": float("nan")})
        with self.assertRaises(ValueError):
            stable_hash({"inf": float("inf")})

    def test_command_log_constructor_validates_fields(self):
        for seed in (1.5, True, "7"):
            with self.assertRaises((TypeError, ValueError)):
                CommandLog(seed=seed)  # type: ignore[arg-type]
        for step in (0.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                CommandLog(seed=1, step=step)
        with self.assertRaises(TypeError):
            CommandLog(seed=1, frames={"bad": 1})  # type: ignore[arg-type]

    def test_command_log_round_trip(self):
        log = CommandLog(seed=7)
        log.record(ActionState(forward=1.0, pressed=frozenset({"jump"})))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            log.save(path)
            loaded = CommandLog.load(path)
        self.assertEqual(loaded.to_dict(), log.to_dict())
        self.assertEqual(loaded.replay_actions()[0].forward, 1.0)

    def test_scene_loader_restores_each_fresh_scene(self):
        log = CommandLog(seed=1)
        log.record(ActionState())
        calls = []

        def loader(game, scene):
            self.assertIsInstance(scene, Scene)
            self.assertIs(scene, game.scene)
            calls.append((game, scene))
            scene.background = [0.1, 0.2, 0.3]

        result = run_log(CubeDemo, log, scene_loader=loader)
        self.assertEqual(result["frames"], 1)
        self.assertEqual(len(calls), 1)
        calls.clear()
        verify_log(CubeDemo, log, scene_loader=loader)
        self.assertEqual(len(calls), 2)
        with self.assertRaises(TypeError):
            run_log(CubeDemo, log, scene_loader=object())

    def test_invalid_step_is_rejected(self):
        with self.assertRaises(ValueError):
            CommandLog.from_dict({"seed": 1, "step": 0.0, "frames": []})

    def test_strict_seed_and_frames_are_rejected(self):
        for bad_seed in (3.7, "3", True):
            with self.assertRaises(TypeError):
                CommandLog.from_dict({"seed": bad_seed, "frames": []})
        for bad_frames in ({"a": 1}, "actions"):
            with self.assertRaises(TypeError):
                CommandLog.from_dict({"seed": 1, "frames": bad_frames})

    def test_run_log_restores_global_random_state(self):
        import random

        log = CommandLog(seed=9)
        log.record(ActionState(forward=1.0))
        random.seed(0)
        expected = random.random()
        random.seed(0)
        run_log(CubeDemo, log)
        self.assertEqual(random.random(), expected)

    def test_run_log_replays_deterministically(self):
        log = CommandLog(seed=7)
        log.record(ActionState(forward=1.0))
        log.record(ActionState(forward=0.5))
        result = run_log(CubeDemo, log, trace=True)
        self.assertEqual(result["frames"], 2)
        self.assertEqual(result["seed"], 7)
        self.assertEqual(len(result["trace"]), 2)
        verified = verify_log(CubeDemo, log)
        self.assertTrue(verified["ok"])
        with self.assertRaises(TypeError):
            run_log(object(), log)


if __name__ == "__main__":
    unittest.main()
