"""Tests for the seeded bot playtester: transcripts, diffs, policies and fairness."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from keystone.headless import run_simulation
from keystone.input import ActionState
from keystone.playtest import (
    PLAYTEST_REPORT_SCHEMA,
    TRANSCRIPT_SCHEMA,
    GreedyPolicy,
    RandomPolicy,
    ScriptedPolicy,
    canon,
    canon_hash,
    diff_transcripts,
    make_report,
    run_bot,
    to_command_log,
    validate_fairness,
)
from keystone.replay import run_log, stable_hash
from keystone.samples import CubeDemo
from tests.support_maze_game import (
    FairMaze,
    HazardMaze,
    TightMaze,
    WalledMaze,
    maze_shortest_path,
    open_config,
    optimal_actions,
    reachable,
    walled_goal_config,
)


class TranscriptTest(unittest.TestCase):
    def test_run_bot_records_a_command_log_compatible_transcript(self):
        transcript = run_bot(FairMaze, ScriptedPolicy([ActionState(forward=1.0)]), frames=3, seed=0, trace=True)
        self.assertEqual(transcript["schema"], TRANSCRIPT_SCHEMA)
        self.assertEqual(transcript["game"], "maze-stub")
        self.assertEqual(len(transcript["actions"]), 3)
        self.assertEqual(transcript["steps_used"], 3)
        self.assertEqual(len(transcript["snapshots"]), 3)
        self.assertEqual(transcript["hash"], stable_hash(transcript["final"]))

    def test_transcript_hash_matches_simulation_for_the_same_actions(self):
        actions = [ActionState(forward=1.0)] * 5
        transcript = run_bot(CubeDemo, ScriptedPolicy(actions), frames=5, seed=7, trace=True)
        result = run_simulation(CubeDemo(), frames=5, actions=actions)
        self.assertEqual(transcript["hash"], result["hash"])

    def test_same_seed_same_transcript(self):
        first = run_bot(FairMaze, RandomPolicy(), frames=10, seed=3, trace=True)
        second = run_bot(FairMaze, RandomPolicy(), frames=10, seed=3, trace=True)
        self.assertEqual(first["hash"], second["hash"])
        self.assertEqual(first["actions"], second["actions"])

    def test_transcript_replays_through_the_command_log(self):
        transcript = run_bot(FairMaze, ScriptedPolicy(optimal_actions(open_config())), frames=8, seed=0)
        replayed = run_log(FairMaze, to_command_log(transcript))
        self.assertEqual(replayed["hash"], transcript["hash"])
        self.assertEqual(replayed["final"]["outcome"], "win")

    def test_terminal_outcome_ends_the_run_early(self):
        transcript = run_bot(FairMaze, ScriptedPolicy(optimal_actions(open_config())), frames=40, seed=0)
        self.assertEqual(transcript["outcome"], "win")
        self.assertEqual(transcript["steps_used"], 8)

    def test_invalid_runner_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            run_bot(FairMaze, RandomPolicy(), frames=-1)
        with self.assertRaises(ValueError):
            run_bot(FairMaze, RandomPolicy(), step=0.0)
        with self.assertRaises(TypeError):
            run_bot(FairMaze, object())
        with self.assertRaises(TypeError):
            run_bot("not-a-factory", RandomPolicy())

    def test_canon_drops_time_and_rounds_floats(self):
        projected = canon({"time": 9.99, "x": 1.123456, "nested": {"y": 2.987654}})
        self.assertNotIn("time", projected)
        self.assertEqual(projected["x"], 1.123)
        self.assertEqual(canon_hash({"time": 1.0, "x": 1.0}), canon_hash({"time": 2.0, "x": 1.0}))


class DiffTest(unittest.TestCase):
    def test_identical_transcripts_match_with_no_divergence(self):
        before = run_bot(CubeDemo, RandomPolicy(), frames=4, seed=1, trace=True)
        after = run_bot(CubeDemo, RandomPolicy(), frames=4, seed=1, trace=True)
        diff = diff_transcripts(before, after)
        self.assertTrue(diff["same_hash"])
        self.assertTrue(diff["final_equal"])
        self.assertIsNone(diff["first_divergent_frame"])

    def test_divergent_transcripts_report_the_first_frame(self):
        before = run_bot(
            FairMaze, ScriptedPolicy([ActionState(right=1.0)] * 4), frames=4, seed=0, trace=True
        )
        after = run_bot(
            FairMaze, ScriptedPolicy([ActionState(right=1.0)] * 3 + [ActionState(forward=1.0)]),
            frames=4,
            seed=0,
            trace=True,
        )
        diff = diff_transcripts(before, after)
        self.assertFalse(diff["same_hash"])
        self.assertEqual(diff["first_divergent_frame"], 3)

    def test_schema_mismatches_are_rejected(self):
        good = run_bot(CubeDemo, RandomPolicy(), frames=2, seed=0)
        with self.assertRaises(ValueError):
            diff_transcripts({"schema": 99}, good)


class PolicyTest(unittest.TestCase):
    def test_random_policy_is_bounded_and_seeded(self):
        first = run_bot(CubeDemo, RandomPolicy(), frames=10, seed=3, trace=True)
        second = run_bot(CubeDemo, RandomPolicy(), frames=10, seed=3, trace=True)
        self.assertEqual(first["hash"], second["hash"])
        for action in first["actions"]:
            for axis in ("forward", "right", "up", "look_yaw", "look_pitch"):
                self.assertLessEqual(abs(action[axis]), 1.0)

    def test_greedy_policy_repeats_a_winning_action(self):
        policy = GreedyPolicy()
        import random as _random

        rng = _random.Random(0)
        spec = {"axes": ["forward"], "buttons": []}
        first = policy.select({"score": 1.0}, spec, rng)
        repeated = policy.select({"score": 2.0}, spec, rng)
        self.assertEqual(first.to_dict(), repeated.to_dict())
        self.assertTrue(policy.params["score_guided"])

    def test_greedy_policy_without_a_score_is_random_equivalent(self):
        policy = GreedyPolicy()
        import random as _random

        action = policy.select({"pos": [0, 0]}, {"axes": ["forward"], "buttons": []}, _random.Random(0))
        self.assertIsInstance(action, ActionState)
        self.assertFalse(policy.params["score_guided"])

    def test_scripted_policy_holds_its_final_action(self):
        transcript = run_bot(CubeDemo, ScriptedPolicy([ActionState(forward=1.0)]), frames=4, seed=0)
        self.assertTrue(all(action["forward"] == 1.0 for action in transcript["actions"]))

    def test_scripted_policy_rejects_an_empty_script(self):
        with self.assertRaises(ValueError):
            ScriptedPolicy([])


class FairnessTest(unittest.TestCase):
    def test_fair_configuration_is_accepted_with_a_witness(self):
        verdict = validate_fairness(FairMaze, reference_actions=optimal_actions(open_config()), frames=40, seeds=(0,))
        self.assertEqual(verdict["verdict"], "fair")
        self.assertTrue(any(reason.startswith("witnessed_win:") for reason in verdict["reasons"]))

    def test_walled_goal_is_rejected(self):
        self.assertIsNone(maze_shortest_path(walled_goal_config()))
        self.assertFalse(reachable(walled_goal_config()))
        verdict = validate_fairness(WalledMaze, reference_actions=[{"forward": 1.0}], frames=40, seeds=(0,))
        self.assertEqual(verdict["verdict"], "unfair")
        self.assertIn("no_witnessed_win", verdict["reasons"])

    def test_hazard_spawn_is_rejected_as_terminal(self):
        verdict = validate_fairness(HazardMaze, reference_actions=[{"forward": 1.0}], frames=40, seeds=(0,))
        self.assertEqual(verdict["verdict"], "unfair")
        self.assertIn("spawn_terminal:lose", verdict["reasons"])

    def test_tight_clock_is_rejected_as_infeasible(self):
        reference = optimal_actions(open_config())
        verdict = validate_fairness(
            TightMaze, reference_actions=reference, frames=40, seeds=(0,), time_limit_frames=3
        )
        self.assertEqual(verdict["verdict"], "unfair")
        self.assertTrue(any(reason.startswith("budget_infeasible:") for reason in verdict["reasons"]))

    def test_game_without_an_outcome_signal_is_unknown(self):
        verdict = validate_fairness(CubeDemo, frames=8, seeds=(0,))
        self.assertEqual(verdict["verdict"], "unknown")
        self.assertIn("no_outcome_signal", verdict["reasons"])

    def test_no_reference_without_a_win_is_unknown_not_unfair(self):
        verdict = validate_fairness(FairMaze, frames=4, seeds=(0,))
        self.assertEqual(verdict["verdict"], "unknown")
        self.assertIn("no_reference_solution", verdict["reasons"])

    def test_nondeterministic_game_is_rejected(self):
        counter = {"calls": 0}

        class Flaky:
            name = "flaky"

            def build_scene(self):
                from keystone.scene import Scene

                return Scene()

            def update(self, dt, actions):
                return None

            def snapshot(self):
                counter["calls"] += 1
                return {"outcome": "ongoing", "calls": counter["calls"]}

            def actions(self):
                return {"axes": [], "buttons": []}

            def status(self):
                return "flaky"

        verdict = validate_fairness(Flaky, frames=4, seeds=(0,))
        self.assertEqual(verdict["verdict"], "unfair")
        self.assertIn("nondeterministic", verdict["reasons"])


class ReportTest(unittest.TestCase):
    def test_report_is_frozen_schema_1_and_web_compatible(self):
        transcript = run_bot(FairMaze, RandomPolicy(), frames=6, seed=0, trace=True)
        fairness = validate_fairness(FairMaze, reference_actions=optimal_actions(open_config()), frames=40, seeds=(0,))
        report = make_report(transcript, fairness)
        self.assertEqual(report["schema"], PLAYTEST_REPORT_SCHEMA)
        self.assertEqual(report["hash"], transcript["hash"])
        self.assertEqual(report["transcript_hash"], transcript["hash"])
        self.assertEqual(report["fairness"]["verdict"], "fair")
        self.assertEqual(report["coverage"]["states_visited"], 6)
        self.assertTrue(report["web_compatible"])

    def test_report_covers_an_untraced_transcript(self):
        transcript = run_bot(FairMaze, RandomPolicy(), frames=6, seed=0, trace=False)
        report = make_report(transcript)
        self.assertEqual(report["coverage"], {"states_visited": 6, "unique_hashes": None})
        self.assertEqual(report["fairness"], {"verdict": "unknown", "reasons": ["no_fairness_check"]})

    def test_web_simulate_result_assembles_into_the_same_report(self):
        """A thin adapter wraps POST /api/simulate output; no browser driving."""
        actions = [ActionState(right=1.0)] * 4
        simulated = run_simulation(FairMaze(), frames=4, actions=actions, trace=True)
        transcript = {
            "schema": TRANSCRIPT_SCHEMA,
            "game": simulated["game"],
            "policy": {"name": "random", "seed": 0, "params": {}},
            "seed": 0,
            "frames": simulated["frames"],
            "steps_used": simulated["frames"],
            "outcome": simulated["final"].get("outcome", "unknown"),
            "actions": simulated["actions"],
            "snapshots": simulated["trace"],
            "final": simulated["final"],
            "hash": simulated["hash"],
        }
        report = make_report(transcript)
        self.assertEqual(report["hash"], simulated["hash"])
        self.assertEqual(report["outcome"], "ongoing")


class PlaytestCliTest(unittest.TestCase):
    def test_playtest_cli_writes_transcript_and_report(self):
        from keystone.__main__ import main

        with tempfile.TemporaryDirectory() as directory:
            transcript_path = Path(directory) / "run.json"
            report_path = Path(directory) / "report.json"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(
                    [
                        "--game",
                        "tests.support_maze_game:FairMaze",
                        "--playtest",
                        "--seed",
                        "0",
                        "--frames",
                        "8",
                        "--transcript-out",
                        str(transcript_path),
                        "--out",
                        str(report_path),
                    ]
                )
            self.assertEqual(code, 0)
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["transcript_hash"], transcript["hash"])
            self.assertEqual(report["schema"], PLAYTEST_REPORT_SCHEMA)

    def test_playtest_cli_rejects_an_unfair_configuration(self):
        from keystone.__main__ import main

        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "attempt.json"
            script.write_text(json.dumps(optimal_actions(open_config())), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "--game",
                        "tests.support_maze_game:WalledMaze",
                        "--playtest",
                        "--policy",
                        "scripted",
                        "--script",
                        str(script),
                        "--frames",
                        "40",
                    ]
                )
            self.assertEqual(code, 1)

    def test_playtest_cli_pins_the_transcript_hash(self):
        from keystone.__main__ import main

        with tempfile.TemporaryDirectory() as directory:
            transcript_path = Path(directory) / "run.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "--game",
                        "tests.support_maze_game:FairMaze",
                        "--playtest",
                        "--seed",
                        "1",
                        "--frames",
                        "4",
                        "--transcript-out",
                        str(transcript_path),
                    ]
                )
            self.assertEqual(code, 0)
            pinned = json.loads(transcript_path.read_text(encoding="utf-8"))["hash"]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "--game",
                            "tests.support_maze_game:FairMaze",
                            "--playtest",
                            "--seed",
                            "1",
                            "--frames",
                            "4",
                            "--expect-hash",
                            pinned,
                        ]
                    ),
                    0,
                )
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "--game",
                            "tests.support_maze_game:FairMaze",
                            "--playtest",
                            "--seed",
                            "1",
                            "--frames",
                            "4",
                            "--expect-hash",
                            "0" * 32,
                        ]
                    ),
                    1,
                )

    def test_playtest_cli_flag_guards(self):
        from keystone.__main__ import main

        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--playtest", "--simulate"])
        self.assertEqual(caught.exception.code, 2)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--playtest", "--policy", "scripted"])
        self.assertEqual(caught.exception.code, 2)

    def test_describe_advertises_the_playtest_capability(self):
        from keystone.__main__ import main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(main(["--describe"]), 0)
        self.assertTrue(json.loads(buffer.getvalue())["capabilities"]["playtest"])

    def test_fixture_lives_outside_the_engine_core(self):
        import keystone.playtest

        root = Path(keystone.playtest.__file__).parent
        self.assertFalse((root / "support_maze_game.py").exists())


if __name__ == "__main__":
    unittest.main()
