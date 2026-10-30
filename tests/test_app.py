"""Integration tests for the engine loop, demo scene and CLI."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from keystone.__main__ import main
from keystone.app import Engine
from keystone.demo import Demo
from keystone.expedition import Expedition


class DemoTest(unittest.TestCase):
    def test_demo_scene_contains_renderables(self):
        demo = Demo()
        renderables = [node for node in demo.scene.traverse() if node.mesh is not None]
        self.assertGreaterEqual(len(renderables), 8)

    def test_update_rotates_and_bobs_over_time(self):
        demo = Demo()
        crystal = demo.crystal
        before_rotation = crystal.transform.rotation
        before_height = crystal.transform.position.y
        demo.update(0.75)
        self.assertNotEqual(crystal.transform.rotation, before_rotation)
        self.assertNotEqual(crystal.transform.position.y, before_height)


class EngineTest(unittest.TestCase):
    def test_headless_engine_runs_and_saves_a_png(self):
        demo = Demo()
        engine = Engine(demo.scene, 48, 32, visible=False)
        self.addCleanup(engine.close)
        frames = engine.run(update=demo.update, max_frames=2)
        self.assertEqual(frames, 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.png"
            engine.screenshot(path)
            self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


class ExpeditionEngineTest(unittest.TestCase):
    def test_headless_expedition_renders_and_saves_a_png(self):
        expedition = Expedition(7, size=32)
        engine = Engine(expedition.scene, 48, 32, visible=False)
        self.addCleanup(engine.close)
        frames = engine.run(update=expedition.update, max_frames=2)
        self.assertEqual(frames, 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "expedition.png"
            engine.screenshot(path)
            self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


class CliTest(unittest.TestCase):
    def test_bad_size_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--size", "wide"])
        self.assertEqual(caught.exception.code, 2)

    def test_out_requires_headless(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--out", "frame.png"])
        self.assertEqual(caught.exception.code, 2)

    def test_bad_seed_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--seed", "not-a-number"])
        self.assertEqual(caught.exception.code, 2)

    def test_bad_layout_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--layout", "maze"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
