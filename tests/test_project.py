"""Tests for project manifests, scaffolding and the --project CLI path."""

import contextlib
import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from keystone.__main__ import main
from keystone.assets import AssetRegistry
from keystone.headless import run_simulation
from keystone.png import write_png
from keystone.project import (
    PROJECT_FILE,
    ProjectManifest,
    create_project,
    import_project_assets,
    load_project,
    load_project_game,
    project_asset_id,
    save_project,
)

OBJ_TEXT = """v 0 0 0
v 1 0 0
v 0 1 0
vn 0 0 1
f 1//1 2//1 3//1
"""
PIXELS = bytes((10, 20, 30, 255, 40, 50, 60, 255, 70, 80, 90, 255, 100, 110, 120, 255))


class ProjectManifestTest(unittest.TestCase):
    def test_round_trip_and_file_paths(self):
        manifest = ProjectManifest(
            name="demo",
            game="demo:Game",
            description="a demo",
            assets=("assets/floor.png",),
        )
        self.assertEqual(ProjectManifest.from_dict(manifest.to_dict()), manifest)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "demo"
            root.mkdir()
            path = save_project(root, manifest)
            self.assertEqual(path, root / PROJECT_FILE)
            self.assertEqual(load_project(root).manifest, manifest)
            self.assertEqual(load_project(path).manifest, manifest)

    def test_validation_rejects_bad_shapes(self):
        for data in (
            {},
            {"schema": True, "name": "x"},
            {"schema": 99, "name": "x"},
            {"schema": 1, "name": "", "game": "x:Y"},
            {"schema": 1, "name": "x", "game": "nocolon"},
            {"schema": 1, "name": "x", "game": "x:Y", "assets": "bad"},
            {"schema": 1, "name": "x", "game": "x:Y", "unknown": 1},
        ):
            with self.assertRaises((TypeError, ValueError)):
                ProjectManifest.from_dict(data)

    def test_missing_manifest_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError) as caught:
                load_project(Path(directory) / "absent")
            self.assertIn("Why:", str(caught.exception))
            self.assertIn("Fix:", str(caught.exception))


class ProjectScaffoldTest(unittest.TestCase):
    def _name(self):
        return f"demo_{uuid.uuid4().hex[:8]}"

    def test_create_project_loads_and_simulates(self):
        name = self._name()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            context = create_project(root, name=name)
            self.assertTrue((root / PROJECT_FILE).exists())
            self.assertTrue((root / f"{name}.py").exists())
            self.assertTrue((root / "README.md").exists())
            self.assertEqual(load_project(root).manifest.name, name)
            game = load_project_game(context)
            result = run_simulation(game, frames=3)
            self.assertEqual(result["frames"], 3)
            self.assertIn("hash", result)
            self.assertEqual(result["final"]["name"], name)

    def _project_with_assets(self, root, name):
        context = create_project(root, name=name)
        assets = root / "assets"
        assets.mkdir()
        (assets / "cube.obj").write_text(OBJ_TEXT, encoding="utf-8")
        write_png(assets / "grid.png", 2, 2, PIXELS)
        manifest = ProjectManifest(
            name=name,
            game=context.manifest.game,
            assets=("assets/cube.obj", "assets/grid.png"),
        )
        save_project(root, manifest)
        return load_project(root)

    def test_project_assets_import_with_stable_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            context = self._project_with_assets(root, self._name())
            registry = AssetRegistry()
            records = import_project_assets(context, registry)
            self.assertEqual(
                [record.id for record in records],
                ["project:assets/cube.obj", "project:assets/grid.png"],
            )
            self.assertEqual([record.kind for record in records], ["mesh", "texture"])
            self.assertEqual(project_asset_id("assets/grid.png"), "project:assets/grid.png")
            self.assertEqual(
                registry.require("project:assets/cube.obj").source,
                (root / "assets" / "cube.obj").resolve(),
            )

    def test_project_game_imports_manifest_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            context = self._project_with_assets(root, self._name())
            game = load_project_game(context)
            self.assertEqual(
                game.assets.ids(),
                ("project:assets/cube.obj", "project:assets/grid.png"),
            )
            result = run_simulation(game, frames=1)
            self.assertEqual(result["frames"], 1)
            self.assertIn("project:assets/cube.obj", game.assets.ids())

    def test_project_assets_reject_unsafe_missing_and_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            context = create_project(root, name=self._name())
            for bad in ("../outside.obj", "/absolute.obj"):
                manifest = ProjectManifest(
                    name=context.manifest.name,
                    game=context.manifest.game,
                    assets=(bad,),
                )
                save_project(root, manifest)
                with self.assertRaises(ValueError):
                    import_project_assets(load_project(root), AssetRegistry())
            (root / "assets").mkdir(exist_ok=True)
            (root / "assets" / "data.bin").write_bytes(b"x")
            for value, error in (
                ("assets/missing.obj", FileNotFoundError),
                ("assets/data.bin", ValueError),
            ):
                manifest = ProjectManifest(
                    name=context.manifest.name,
                    game=context.manifest.game,
                    assets=(value,),
                )
                save_project(root, manifest)
                with self.assertRaises(error):
                    import_project_assets(load_project(root), AssetRegistry())
            with self.assertRaises(ValueError):
                project_asset_id("../outside.obj")

    def test_cli_project_asset_failure_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            context = create_project(root, name=self._name())
            manifest = ProjectManifest(
                name=context.manifest.name,
                game=context.manifest.game,
                assets=("assets/missing.obj",),
            )
            save_project(root, manifest)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main(["--project", str(root), "--describe"]), 1)
            text = err.getvalue()
            self.assertIn("could not import project assets", text)
            self.assertIn("Why:", text)
            self.assertIn("Fix:", text)

    def test_non_empty_directory_requires_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            (root / "existing.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_project(root, name=self._name())
            create_project(root, name=self._name(), force=True)

    def test_cli_new_and_project(self):
        name = self._name()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(main(["--new", str(root), "--name", name]), 0)
            self.assertIn("Created Keystone project", out.getvalue())
            self.assertTrue((root / PROJECT_FILE).exists())

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["--project", str(root), "--describe"]), 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["game"], name)
            self.assertEqual(payload["project"]["manifest"]["name"], name)
            self.assertTrue(payload["capabilities"]["prefabs"])

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["--project", str(root), "--simulate", "--frames", "2"]), 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["frames"], 2)
            self.assertEqual(result["final"]["name"], name)

    def test_cli_new_is_standalone_and_missing_project_has_why_fix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(["--new", str(root), "--describe"])
            self.assertEqual(caught.exception.code, 2)

            missing = Path(directory) / "missing"
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main(["--project", str(missing), "--describe"]), 1)
            self.assertIn("Why:", err.getvalue())
            self.assertIn("Fix:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
