"""Tests for the game-agnostic engine loop and CLI."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from keystone.__main__ import main
from keystone.app import Engine
from keystone.headless import run_simulation
from keystone.samples import CubeDemo


class EngineTest(unittest.TestCase):
    def test_headless_engine_runs_fixed_steps_and_saves_a_png(self):
        game = CubeDemo()
        engine = Engine(game, 48, 32, visible=False)
        self.addCleanup(engine.close)
        frames = engine.run(max_frames=2)
        self.assertEqual(frames, 2)
        self.assertAlmostEqual(game.snapshot()["time"], 2.0 / 60.0, places=4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame.png"
            engine.screenshot(path)
            self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_bad_size_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--size", "wide"])
        self.assertEqual(caught.exception.code, 2)

    def test_out_requires_headless(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--out", "frame.png"])
        self.assertEqual(caught.exception.code, 2)

    def test_bad_game_spec_reports_why_and_fix(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(main(["--game", "missing.module:Factory"]), 1)
        message = stderr.getvalue()
        self.assertIn("Why:", message)
        self.assertIn("Fix:", message)

    def test_describe_cli_prints_capabilities_without_opening_a_window(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(main(["--describe"]), 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["game"], "cube-demo")
        self.assertTrue(payload["capabilities"]["simulate"])

    def test_verify_determinism_cli_is_gpu_free(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(main(["--verify-determinism", "--frames", "2"]), 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["first"], payload["second"])

    def test_expect_hash_gate_matches_and_rejects(self):
        expected = run_simulation(CubeDemo(), 1)["hash"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--simulate", "--frames", "1", "--expect-hash", expected]), 0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--simulate", "--frames", "1", "--expect-hash", "0" * 32]), 1)

    def test_invalid_expected_hash_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--simulate", "--expect-hash", "not-a-hash"])
        self.assertEqual(caught.exception.code, 2)

    def test_simulate_cli_prints_json_without_opening_a_window(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(main(["--simulate", "--frames", "2"]), 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["frames"], 2)
        self.assertIn("hash", payload)

    def test_simulate_cli_reads_actions_and_writes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            actions = Path(directory) / "actions.json"
            out = Path(directory) / "run.json"
            actions.write_text(json.dumps([{"forward": 1.0}]), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(["--simulate", "--frames", "2", "--actions", str(actions), "--out", str(out)]),
                    0,
                )
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["frames"], 2)

    def test_compare_baseline_cli_exits_zero_and_writes_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            current = Path(directory) / "current.json"
            baseline_png = Path(directory) / "baseline.png"
            current_png = Path(directory) / "current.png"
            diff_png = Path(directory) / "diff.png"
            common = ["--headless", "--frames", "1", "--size", "32x24"]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([*common, "--out", str(baseline_png), "--report", str(baseline)]), 0)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(
                    [
                        *common,
                        "--out",
                        str(current_png),
                        "--report",
                        str(current),
                        "--compare-baseline",
                        str(baseline),
                        "--diff-out",
                        str(diff_png),
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(buffer.getvalue())
            self.assertTrue(payload["diff"]["same_image"])
            self.assertEqual(payload["pixel_diff"]["changed_pixels"], 0)
            self.assertTrue(diff_png.exists())

    def test_capture_report_and_png(self):
        game = CubeDemo()
        engine = Engine(game, 32, 24, visible=False)
        self.addCleanup(engine.close)
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "frame.png"
            report = Path(directory) / "report.json"
            engine.capture(image, report)
            self.assertTrue(image.exists())
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], 1)
            self.assertEqual(payload["image"]["path"], Path(image).as_posix())
            self.assertGreater(payload["stats"]["mean_luma"], 0.0)


if __name__ == "__main__":
    unittest.main()
