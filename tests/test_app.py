"""Tests for the game-agnostic engine loop and CLI."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

from keystone.__main__ import main
from keystone.app import Engine
from keystone.headless import run_simulation
from keystone.samples import CubeDemo


class HudCube(CubeDemo):
    name = "hud-cube"

    def draw_ui(self, canvas, _state):
        canvas.rect(70, 70, 30, 20, (1.0, 0.0, 0.0, 1.0))


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

    def test_ui_capture_alpha_is_opaque(self):
        engine = Engine(CubeDemo(), 160, 120, visible=False, ui=True)
        self.addCleanup(engine.close)
        engine.run(max_frames=1)
        pixels = engine.renderer.read_pixels()
        self.assertEqual(min(pixels[3::4]), 255)

    def test_ui_overlay_changes_the_captured_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            plain_path = Path(directory) / "plain.png"
            ui_path = Path(directory) / "ui.png"
            paused_path = Path(directory) / "paused.png"
            plain = Engine(CubeDemo(), 160, 120, visible=False)
            plain.run(max_frames=1)
            plain.screenshot(plain_path)
            plain.close()
            overlay = Engine(CubeDemo(), 160, 120, visible=False, ui=True)
            self.addCleanup(overlay.close)
            overlay.run(max_frames=1)
            overlay.screenshot(ui_path)
            overlay.toggle_pause()
            overlay.screenshot(paused_path)
            self.assertNotEqual(plain_path.read_bytes(), ui_path.read_bytes())
            self.assertNotEqual(ui_path.read_bytes(), paused_path.read_bytes())

    def test_pause_stops_updates_but_keeps_rendering(self):
        game = CubeDemo()
        engine = Engine(game, 48, 32, visible=False)
        self.addCleanup(engine.close)
        engine.run(max_frames=1)
        paused_at = game.snapshot()["time"]
        engine.toggle_pause()
        self.assertEqual(engine.run(max_frames=3), 3)
        self.assertEqual(game.snapshot()["time"], paused_at)
        engine.toggle_pause()
        engine.run(max_frames=1)
        self.assertGreater(game.snapshot()["time"], paused_at)

    def test_ui_actions_are_drivable_without_real_input(self):
        engine = Engine(CubeDemo(), 48, 32, visible=False, ui=True)
        self.addCleanup(engine.close)
        self.assertTrue(engine.apply_ui_action("pause"))
        self.assertTrue(engine.paused)
        self.assertTrue(engine.apply_ui_action("toggle_ui"))
        self.assertFalse(engine.overlay.visible)
        self.assertTrue(engine.apply_ui_action("toggle_ui"))
        self.assertTrue(engine.apply_ui_action("resume"))
        self.assertFalse(engine.paused)
        self.assertFalse(engine.apply_ui_action("missing"))

    def test_game_ui_hook_adds_pixels_to_the_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            custom_path = Path(directory) / "custom.png"
            plain_path = Path(directory) / "plain.png"
            custom = Engine(HudCube(), 160, 120, visible=False, ui=True)
            self.addCleanup(custom.close)
            custom.run(max_frames=1)
            custom.screenshot(custom_path)
            custom.close()
            plain = Engine(CubeDemo(), 160, 120, visible=False, ui=True)
            self.addCleanup(plain.close)
            plain.run(max_frames=1)
            plain.screenshot(plain_path)
            self.assertNotEqual(custom_path.read_bytes(), plain_path.read_bytes())

    def test_bad_size_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--size", "wide"])
        self.assertEqual(caught.exception.code, 2)

    def test_out_requires_headless(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--out", "frame.png"])
        self.assertEqual(caught.exception.code, 2)

    def test_ui_flags_are_limited_to_rendered_runs(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--simulate", "--ui"])
        self.assertEqual(caught.exception.code, 2)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--ui", "--no-ui"])
        self.assertEqual(caught.exception.code, 2)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--simulate", "--start-paused"])
        self.assertEqual(caught.exception.code, 2)

    def test_replay_cli_replays_a_log_without_opening_a_window(self):
        from keystone.input import ActionState
        from keystone.replay import CommandLog

        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "run.json"
            out = Path(directory) / "result.json"
            record = CommandLog(seed=11)
            record.record(ActionState(forward=1.0))
            record.save(log)
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["--replay", str(log), "--out", str(out)])
            self.assertEqual(code, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["frames"], 1)
            self.assertEqual(payload["seed"], 11)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(["--replay", str(log), "--simulate"])
            self.assertEqual(caught.exception.code, 2)
            for argv in (["--replay", str(log), "--frames", "2"], ["--replay", str(log), "--size", "320x180"]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    main(argv)
                self.assertEqual(caught.exception.code, 2)

    def test_serve_is_a_standalone_web_command(self):
        for argv in (
            ["--serve", "--headless"],
            ["--serve", "--simulate"],
            ["--serve", "--ui"],
            ["--serve", "--out", "frame.png"],
            ["--serve", "--frames", "2"],
            ["--serve", "--size", "320x180"],
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(argv)
            self.assertEqual(caught.exception.code, 2)

    def test_windowless_commands_reject_window_flags(self):
        for argv in (
            ["--describe", "--diff-out", "diff.png"],
            ["--simulate", "--frames", "1", "--size", "320x180"],
            ["--playtest", "--frames", "8", "--size", "320x180"],
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(argv)
            self.assertEqual(caught.exception.code, 2)

    def test_web_flags_require_serve(self):
        for argv in (
            ["--port", "9000"],
            ["--host", "0.0.0.0"],
            ["--prefab-dir", "prefabs"],
            ["--scene-dir", "scenes"],
            ["--scene", "level"],
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(argv)
            self.assertEqual(caught.exception.code, 2)

    def test_scene_startup_requires_a_library(self):
        for argv in (
            ["--serve", "--scene", "level"],
            ["--simulate", "--scene", "level", "--frames", "1"],
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(argv)
            self.assertEqual(caught.exception.code, 2)

    def test_bad_web_port_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["--serve", "--port", "70000"])
        self.assertEqual(caught.exception.code, 2)

    def test_headless_ui_capture_writes_a_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "ui.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["--headless", "--frames", "1", "--size", "160x120", "--ui", "--report", str(report)])
            self.assertEqual(code, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], 11)
            self.assertTrue(payload["ui"]["visible"])
            self.assertIn("KEYSTONE", [label["text"] for label in payload["ui"]["labels"]])

    def test_start_paused_headless_report_describes_the_menu(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "paused.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "--headless",
                        "--frames",
                        "1",
                        "--size",
                        "320x240",
                        "--ui",
                        "--start-paused",
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(payload["ui"]["paused"])
            self.assertEqual([button["action"] for button in payload["ui"]["buttons"]], ["resume", "toggle_ui", "quit"])
            self.assertTrue(payload["ui"]["buttons"][0]["selected"])

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
            self.assertEqual(payload["schema"], 11)
            self.assertIsNone(payload["ui"])
            self.assertEqual(payload["image"]["path"], Path(image).as_posix())
            self.assertGreater(payload["stats"]["mean_luma"], 0.0)


class CleanupAndCliTest(unittest.TestCase):
    def test_close_closes_context_when_release_raises(self):
        class BadRelease:
            def release(self):
                raise RuntimeError("release failed")

        class FakeContext:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        engine = object.__new__(Engine)
        object.__setattr__(engine, "_closed", False)
        engine.ui_renderer = BadRelease()
        engine.renderer = BadRelease()
        engine.context = FakeContext()
        with self.assertRaises(RuntimeError):
            engine.close()
        self.assertTrue(engine.context.closed)
        self.assertTrue(engine._closed)

    def test_standalone_commands_reject_irrelevant_flags(self):
        for argv in (
            ["--describe", "--frames", "5"],
            ["--describe", "--size", "320x180"],
            ["--verify-determinism", "--size", "320x180"],
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(argv)
            self.assertEqual(caught.exception.code, 2, argv)


class _CadenceContext:
    def __init__(self, times, keys=(), pointer_step=0.0, press_from=0):
        self._times = iter(times)
        self._keys = set(keys)
        self._x = 0.0
        self._y = 0.0
        self._pointer_step = pointer_step
        self._frame = -1
        self._press_from = press_from
        self.mouse = False
        self.pointer = (0.0, 0.0)
        self.captured = None

    def should_close(self):
        return False

    def poll_events(self):
        self._frame += 1

    def framebuffer_size(self):
        return (64, 64)

    def time(self):
        return next(self._times)

    def key_down(self, name):
        return name in self._keys and self._frame >= self._press_from

    def mouse_down(self, button="left"):
        return self.mouse

    def cursor_position(self):
        x = self._x
        self._x += self._pointer_step
        return (x, self._y)

    def swap_buffers(self):
        return None

    def set_title(self, title):
        return None

    def set_cursor_captured(self, captured):
        self.captured = captured

    def request_close(self):
        return None


class _CadenceRenderer:
    width = 64
    height = 64
    last_stats: ClassVar[dict[str, int]] = {"draw_calls": 0, "triangles": 0}

    def render(self, scene, particles=None):
        return dict(self.last_stats)


class _CadenceRecorder:
    name = "cadence"

    def __init__(self):
        self.updates = []

    def build_scene(self):
        from keystone.scene import Scene

        return Scene()

    def update(self, dt, actions):
        self.updates.append((actions.pressed, actions.look_yaw))

    def snapshot(self):
        return {"time": 0.0}

    def actions(self):
        return {"axes": ["forward"]}

    def status(self):
        return "cadence"


class InputCadenceTest(unittest.TestCase):
    def _engine(self, times, keys=(), pointer_step=0.0, press_from=0):
        from keystone.clock import FixedStepClock
        from keystone.input import InputMap

        engine = object.__new__(Engine)
        engine.game = _CadenceRecorder()
        engine.context = _CadenceContext(times, keys, pointer_step, press_from)
        engine.renderer = _CadenceRenderer()
        engine.ui_renderer = None
        engine.overlay = None
        engine.scene = engine.game.build_scene()
        engine.input = InputMap()
        engine.clock = FixedStepClock()
        engine.paused = False
        object.__setattr__(engine, "_frames", 0)
        object.__setattr__(engine, "_elapsed", 0.0)
        object.__setattr__(engine, "_fps", 0.0)
        object.__setattr__(engine, "_pointer", (0.0, 0.0))
        object.__setattr__(engine, "_visible", True)
        object.__setattr__(engine, "_closed", False)
        object.__setattr__(engine, "_captured", True)
        object.__setattr__(engine, "_pending_pressed", frozenset())
        object.__setattr__(engine, "_pending_clicked", False)
        object.__setattr__(engine, "_pending_yaw", 0.0)
        object.__setattr__(engine, "_pending_pitch", 0.0)
        return engine

    def test_look_delta_is_frame_rate_independent(self):
        for fps in (30, 60, 144):
            times = [index / fps for index in range(fps + 1)]
            engine = self._engine(times, pointer_step=10.0)
            engine.run(max_frames=fps)
            applied = sum(look for _, look in engine.game.updates)
            expected = len(engine.game.updates) * (fps / 60.0) * 10.0 * engine.input.mouse_sensitivity
            self.assertAlmostEqual(
                applied, expected, delta=10.0 * engine.input.mouse_sensitivity, msg=f"{fps} Hz"
            )

    def test_pressed_edge_survives_zero_step_frames(self):
        fps = 144
        times = [index / fps for index in range(fps + 1)]
        engine = self._engine(times, keys={"w"}, press_from=1)
        engine.run(max_frames=fps)
        pressed = sum(1 for actions, _ in engine.game.updates if "forward" in actions)
        self.assertEqual(pressed, 1)

    def test_pause_menu_mouse_click_resumes(self):
        from keystone.ui.overlay import HudState, HumanOverlay

        engine = self._engine([0.0, 0.0], keys=())
        engine.overlay = HumanOverlay()
        engine.paused = True
        engine._set_capture(False)
        engine.overlay.build(
            HudState(
                game="g",
                status="r",
                fps=60.0,
                frame=0,
                elapsed=0.0,
                width=320,
                height=240,
                paused=True,
            )
        )
        left, top, width, height, _action = engine.overlay.hits[0]
        engine.context.mouse = True
        engine.context._x = left + width / 2
        engine.context._y = top + height / 2
        actions = engine.input.sample(engine.context, 0.0)
        self.assertTrue(actions.mouse_clicked)
        engine._handle_system_actions(actions)
        self.assertFalse(engine.paused)


if __name__ == "__main__":
    unittest.main()
