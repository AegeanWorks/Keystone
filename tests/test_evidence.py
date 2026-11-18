"""Tests for deterministic capture routes and evidence diffs."""

import tempfile
import unittest
from pathlib import Path

from keystone.app import Engine
from keystone.camera_path import CameraKey, CameraPath
from keystone.evidence import (
    Checkpoint,
    Route,
    camera_path_route,
    capture_route,
    diff_evidence,
    write_evidence,
)
from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo
from keystone.scene import Scene


class RouteValidationTest(unittest.TestCase):
    def test_default_route_is_one_frame(self):
        route = Route()
        self.assertEqual(route.frames, 1)
        self.assertEqual(route.checkpoints, ())

    def test_checkpoints_must_be_ordered_and_inside_the_route(self):
        with self.assertRaises(ValueError):
            Route(checkpoints=(Checkpoint(5, "later"), Checkpoint(3, "earlier")))
        with self.assertRaises(ValueError):
            Route(frames=3, checkpoints=(Checkpoint(4, "past"),))
        with self.assertRaises(ValueError):
            Route(frames=3, checkpoints=(Checkpoint(1, "same"), Checkpoint(2, "same")))
        with self.assertRaises(ValueError):
            Route(frames=3, checkpoints=(Checkpoint(1, "first"), Checkpoint(1, "second")))

    def test_malformed_routes_are_rejected(self):
        with self.assertRaises(ValueError):
            Route(name=" ")
        with self.assertRaises(ValueError):
            Route(frames=0)
        with self.assertRaises(ValueError):
            Route(frames=True)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            Checkpoint(0, "start")
        with self.assertRaises(ValueError):
            Checkpoint(1, " ")
        with self.assertRaises(TypeError):
            Route(stage="not callable")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Route(checkpoints=(("1", "label"),))  # type: ignore[arg-type]

    def test_frame_numbers_are_reported(self):
        route = Route(frames=9, checkpoints=(Checkpoint(2, "a"), Checkpoint(7, "b")))
        self.assertEqual(route.frame_numbers(), (2, 7))

    def test_describe_advertises_evidence(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["evidence"])
        self.assertTrue(capabilities["camera_path_route"])


class CaptureRouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def _capture(self, route: Route, directory: Path) -> dict:
        engine = Engine(CubeDemo(), 24, 18, visible=False)
        try:
            return capture_route(engine, route, directory)
        finally:
            engine.close()

    def _route(self, directory_name: str, background=None) -> tuple[Route, Path]:
        def stage(frame, scene):
            if background is not None and frame >= 3:
                scene.background = background

        directory = self.directory / directory_name
        route = Route(
            name="cube-proof",
            frames=6,
            checkpoints=(Checkpoint(2, "entry"), Checkpoint(6, "settled")),
            stage=stage,
        )
        return route, directory

    def test_capture_writes_one_png_and_report_per_checkpoint(self):
        route, directory = self._route("run")
        summary = self._capture(route, directory)
        self.assertEqual(summary["schema"], 1)
        self.assertEqual(summary["frames_run"], 6)
        self.assertEqual([sample["label"] for sample in summary["checkpoints"]], ["entry", "settled"])
        self.assertEqual([sample["frame"] for sample in summary["checkpoints"]], [2, 6])
        self.assertEqual(len(summary["route_hash"]), 32)
        for sample in summary["checkpoints"]:
            self.assertTrue((directory / sample["image"]).is_file())
            self.assertTrue((directory / sample["report"]).is_file())
            self.assertGreater(len(sample["image_sha256"]), 0)
            for field in ("mean_luma", "content_ratio", "content_pixels"):
                self.assertIn(field, sample["stats"])
            self.assertGreater(sample["render"]["draw_calls"], 0)

    def test_stage_runs_for_every_frame_before_the_step(self):
        seen = []
        route = Route(
            name="staged",
            frames=4,
            stage=lambda frame, scene: seen.append((frame, scene.background.x)),
        )
        self._capture(route, self.directory / "staged")
        self.assertEqual([frame for frame, _ in seen], [1, 2, 3, 4])

    def test_two_runs_of_one_route_are_byte_identical(self):
        first, first_dir = self._route("first")
        second, second_dir = self._route("second")
        left = self._capture(first, first_dir)
        right = self._capture(second, second_dir)
        self.assertEqual(left["route_hash"], right["route_hash"])
        self.assertEqual(
            [sample["image_sha256"] for sample in left["checkpoints"]],
            [sample["image_sha256"] for sample in right["checkpoints"]],
        )

    def test_a_staged_change_is_visible_in_the_diff(self):
        plain, plain_dir = self._route("plain")
        altered, altered_dir = self._route("altered", background=Vec3(0.9, 0.1, 0.1))
        before = self._capture(plain, plain_dir)
        after = self._capture(altered, altered_dir)
        diff = diff_evidence(before, after)
        self.assertTrue(diff["changed"])
        self.assertEqual(diff["missing"], [])
        self.assertEqual(diff["added"], [])
        entry = next(item for item in diff["checkpoints"] if item["label"] == "entry")
        settled = next(item for item in diff["checkpoints"] if item["label"] == "settled")
        self.assertFalse(entry["image_changed"])
        self.assertTrue(settled["image_changed"])
        self.assertNotEqual(settled["mean_luma_delta"], 0)

    def test_identical_evidence_reports_no_change(self):
        route, directory = self._route("same")
        first = self._capture(route, directory)
        second = self._capture(route, directory)
        diff = diff_evidence(first, second)
        self.assertFalse(diff["changed"])

    def test_renamed_checkpoints_are_reported(self):
        route, directory = self._route("names")
        before = self._capture(route, directory)
        renamed = Route(
            name="cube-proof",
            frames=6,
            checkpoints=(Checkpoint(2, "entry"), Checkpoint(6, "final")),
        )
        after = self._capture(renamed, directory)
        diff = diff_evidence(before, after)
        self.assertEqual(diff["missing"], ["settled"])
        self.assertEqual(diff["added"], ["final"])
        self.assertTrue(diff["changed"])

    def test_write_evidence_round_trips_atomically(self):
        route, directory = self._route("saved")
        summary = self._capture(route, directory)
        path = directory / "evidence.json"
        write_evidence(path, summary)
        text = path.read_text(encoding="utf-8")
        self.assertIn('"route_hash"', text)

    def test_engine_and_route_types_are_checked(self):
        route, directory = self._route("types")
        with self.assertRaises(TypeError):
            capture_route(object(), route, directory)
        with self.assertRaises(TypeError):
            capture_route(object(), {"name": "not a route"}, directory)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            diff_evidence({}, {"checkpoints": []})
        with self.assertRaises(TypeError):
            write_evidence(directory / "x.json", ["not", "a", "mapping"])  # type: ignore[arg-type]

    def test_stage_failure_names_the_frame(self):
        def explode(frame, scene):
            if frame == 3:
                raise RuntimeError("boom")

        route = Route(name="broken", frames=5, stage=explode)
        with self.assertRaises(RuntimeError) as caught:
            self._capture(route, self.directory / "broken")
        message = str(caught.exception)
        self.assertIn("broken", message)
        self.assertIn("3", message)


if __name__ == "__main__":
    unittest.main()


class CameraPathRouteTest(unittest.TestCase):
    def _path(self, *, loop: bool = False) -> CameraPath:
        keys = [
            CameraKey(0.0, Vec3(0.0, 1.5, 8.0)),
            CameraKey(2.0, Vec3(10.0, 1.5, 8.0)),
        ]
        if loop:
            return CameraPath(keys, loop=True, duration=3.0)
        return CameraPath(keys)

    def test_defaults_to_one_final_checkpoint(self):
        route = camera_path_route(self._path(), frames=90)
        self.assertEqual(route.name, "camera-path")
        self.assertEqual(route.frames, 90)
        self.assertEqual(route.checkpoints, (Checkpoint(90, "final"),))
        self.assertTrue(callable(route.stage))

    def test_custom_name_and_checkpoints_pass_through(self):
        route = camera_path_route(
            self._path(),
            frames=30,
            name="intro",
            checkpoints=(Checkpoint(5, "enter"), Checkpoint(30, "end")),
        )
        self.assertEqual(route.name, "intro")
        self.assertEqual(route.frame_numbers(), (5, 30))

    def test_stage_samples_by_frame_step_and_keeps_the_lens_depth(self):
        route = camera_path_route(self._path(), frames=121)
        scene = Scene()
        scene.camera.near = 0.5
        scene.camera.far = 250.0
        route.stage(1, scene)
        self.assertEqual(scene.camera.position, Vec3(0.0, 1.5, 8.0))
        self.assertEqual((scene.camera.near, scene.camera.far), (0.5, 250.0))
        route.stage(61, scene)
        self.assertEqual(scene.camera.position, Vec3(5.0, 1.5, 8.0))
        route.stage(121, scene)
        self.assertEqual(scene.camera.position, Vec3(10.0, 1.5, 8.0))
        route.stage(500, scene)
        self.assertEqual(scene.camera.position, Vec3(10.0, 1.5, 8.0))

    def test_a_looping_path_wraps_instead_of_holding(self):
        route = camera_path_route(self._path(loop=True), frames=181)
        scene = Scene()
        route.stage(121, scene)
        self.assertEqual(scene.camera.position, Vec3(10.0, 1.5, 8.0))
        route.stage(181, scene)
        self.assertEqual(scene.camera.position, Vec3(0.0, 1.5, 8.0))
        route.stage(151, scene)
        self.assertGreater(scene.camera.position.x, 0.0)
        self.assertLess(scene.camera.position.x, 10.0)

    def test_path_and_step_are_validated(self):
        with self.assertRaises(TypeError):
            camera_path_route(object(), frames=1)  # type: ignore[arg-type]
        for step in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(step=step), self.assertRaises(ValueError):
                camera_path_route(self._path(), frames=1, step=step)
        for step in (True, "0.1", None):
            with self.subTest(step=step), self.assertRaises(TypeError):
                camera_path_route(self._path(), frames=1, step=step)  # type: ignore[arg-type]

    def test_route_rules_still_apply(self):
        with self.assertRaises(ValueError):
            camera_path_route(self._path(), frames=0)
        with self.assertRaises(ValueError):
            camera_path_route(
                self._path(), frames=3, checkpoints=(Checkpoint(4, "past"),)
            )
        with self.assertRaises(ValueError):
            camera_path_route(self._path(), frames=3, name=" ")

    def test_capture_route_renders_the_authored_move(self):
        route = camera_path_route(
            self._path(),
            frames=10,
            step=0.2,
            checkpoints=(Checkpoint(1, "first"), Checkpoint(10, "last")),
        )
        with tempfile.TemporaryDirectory() as directory:
            engine = Engine(CubeDemo(), 24, 18, visible=False)
            try:
                summary = capture_route(engine, route, Path(directory))
            finally:
                engine.close()
        self.assertEqual(
            [sample["label"] for sample in summary["checkpoints"]],
            ["first", "last"],
        )
        hashes = [sample["image_sha256"] for sample in summary["checkpoints"]]
        self.assertTrue(all(hashes))
        self.assertNotEqual(hashes[0], hashes[1])
