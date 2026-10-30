"""Tests for the game-agnostic engine loop and CLI."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from keystone.__main__ import main
from keystone.app import Engine
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


if __name__ == "__main__":
    unittest.main()
