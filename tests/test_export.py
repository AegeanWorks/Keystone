"""Tests for deterministic project export bundles."""

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from keystone.__main__ import main
from keystone.export import EXPORT_MANIFEST, export_project
from keystone.project import create_project


class ProjectExportTest(unittest.TestCase):
    def test_export_bundle_structure_hashes_and_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = create_project(root / "demo", name="demo")
            target = root / "build"
            result = export_project(project.directory, target)

            self.assertEqual(result["schema"], 1)
            self.assertEqual(result["project"]["name"], "demo")
            self.assertEqual(result["entry"], "run.py")
            self.assertTrue((target / "keystone.json").is_file())
            self.assertTrue((target / "demo.py").is_file())
            self.assertTrue((target / "run.py").is_file())
            self.assertTrue((target / "requirements.txt").is_file())
            self.assertTrue((target / "EXPORT.md").is_file())
            self.assertTrue(
                (target / "vendor" / "keystone" / "__main__.py").is_file()
            )
            self.assertTrue((target / "scenes" / "main.kscene").is_file())
            self.assertTrue((target / "prefabs" / "cube.kprefab").is_file())

            build = json.loads(
                (target / EXPORT_MANIFEST).read_text(encoding="utf-8")
            )
            self.assertEqual(build["schema"], 1)
            self.assertEqual(build["project"]["game"], "demo:Game")
            self.assertEqual(build["summary"]["scenes"], 1)
            self.assertEqual(build["summary"]["prefabs"], 1)
            self.assertGreater(build["summary"]["files"], 10)
            paths = {item["path"] for item in build["files"]}
            self.assertIn("run.py", paths)
            self.assertIn("vendor/keystone/__main__.py", paths)
            self.assertNotIn("__pycache__", " ".join(paths))
            run_entry = next(
                item for item in build["files"] if item["path"] == "run.py"
            )
            self.assertEqual(
                run_entry["sha256"],
                hashlib.sha256((target / "run.py").read_bytes()).hexdigest(),
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(target / "run.py"),
                    "--simulate",
                    "--frames",
                    "1",
                ],
                cwd=target,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["game"], "demo")

    def test_export_refuses_non_empty_target_and_force_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = create_project(root / "demo", name="demo")
            target = root / "build"
            export_project(project.directory, target)
            with self.assertRaises(FileExistsError):
                export_project(project.directory, target)
            reexported = export_project(project.directory, target, force=True)
            self.assertEqual(reexported["project"]["name"], "demo")
            self.assertTrue((target / "run.py").is_file())

    def test_export_cli_and_validation_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = create_project(root / "demo", name="demo")
            target = root / "cli-build"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "--project",
                        str(project.directory),
                        "--export",
                        str(target),
                    ]
                )
            self.assertEqual(status, 0)
            self.assertIn("Exported 'demo'", output.getvalue())
            self.assertTrue((target / "run.py").is_file())

            with self.assertRaises(FileNotFoundError):
                export_project(root / "missing", root / "missing-build")

            broken = create_project(root / "broken", name="broken")
            (broken.directory / "scenes" / "bad.kscene").write_text(
                "{}", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                export_project(broken.directory, root / "broken-build")
            self.assertFalse((root / "broken-build").exists())

    def test_export_excludes_development_files_and_nested_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = create_project(root / "demo", name="demo")
            (project.directory / "tests").mkdir()
            (project.directory / "tests" / "test_game.py").write_text(
                "raise SystemExit(1)\n", encoding="utf-8"
            )
            (project.directory / "keystone").mkdir()
            (project.directory / "keystone" / "local.py").write_text(
                "LOCAL = True\n", encoding="utf-8"
            )
            target = project.directory / "build"
            export_project(project.directory, target)
            self.assertTrue((target / "run.py").is_file())
            self.assertFalse((target / "tests").exists())
            self.assertFalse((target / "keystone").exists())
            self.assertFalse((target / "build").exists())
            build = json.loads(
                (target / EXPORT_MANIFEST).read_text(encoding="utf-8")
            )
            paths = {item["path"] for item in build["files"]}
            self.assertNotIn("tests/test_game.py", paths)
            self.assertNotIn("keystone/local.py", paths)


if __name__ == "__main__":
    unittest.main()
