"""A CLI failure must name the action that actually failed.

The catch-all handler used to print "could not start" and blame the game
factory for *any* exception, including ones raised long after the game loaded
(a corrupt baseline report, mismatched diff dimensions). That told an agent to
replace a game module that was working fine.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(args, timeout=300, cwd=None):
    # The scaffolded game imports keystone, so a temp working directory needs
    # the package on the path even though the tests run from the repo root.
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-m", "keystone", *args],
        cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout,
        check=False, env=environment,
    )


class CliFailureAdviceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._directory = tempfile.TemporaryDirectory()
        base = Path(cls._directory.name)
        cls.base = base
        cls.baseline_png = base / "baseline.png"
        cls.baseline_report = base / "baseline.json"
        run(["--headless", "--frames", "1", "--size", "96x64",
             "--out", str(cls.baseline_png), "--report", str(cls.baseline_report)])

    @classmethod
    def tearDownClass(cls):
        cls._directory.cleanup()

    def test_startup_failure_blames_the_game_factory(self):
        result = run(["--game", "no.such.module"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not start", result.stderr)
        self.assertIn("package.module:Factory", result.stderr)

    def test_project_start_failure_points_at_keystone_json(self):
        """With --project the caller never typed a factory string.

        The scaffold pins "game": "<name>:Game" in keystone.json, so renaming
        the class breaks the project. Telling that caller to "pass a valid
        package.module:Factory" points at an argument they already supplied
        indirectly; the field that needs editing is in the manifest.
        """
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            created = run(["--new", "demo"], cwd=work)
            self.assertEqual(created.returncode, 0, created.stderr)
            project = work / "demo"
            module = project / "demo.py"
            original = module.read_text(encoding="utf-8")
            self.assertIn("class Game:", original)
            module.write_text(
                original.replace("class Game:", "class DemoGame:"), encoding="utf-8"
            )

            result = run(["--project", "demo", "--validate-project"], cwd=work)
            self.assertEqual(result.returncode, 1)
            output = result.stderr
            self.assertIn("could not start", output)
            self.assertIn("keystone.json", output)
            self.assertIn("'game' field", output)
            self.assertNotIn(
                "pass a valid 'package.module:Factory'",
                output,
                "a --project caller should not be told to pass a factory",
            )

            # Fixing the manifest field is enough to recover.
            manifest = project / "keystone.json"
            config = json.loads(manifest.read_text(encoding="utf-8"))
            config["game"] = "demo:DemoGame"
            manifest.write_text(json.dumps(config, indent=2), encoding="utf-8")
            recovered = run(["--project", "demo", "--validate-project"], cwd=work)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)

    def test_corrupt_baseline_names_the_report_not_the_game(self):
        broken = self.base / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        result = run(["--headless", "--frames", "1", "--size", "96x64",
                      "--out", str(self.base / "c.png"),
                      "--report", str(self.base / "c.json"),
                      "--compare-baseline", str(broken)])
        self.assertEqual(result.returncode, 1)
        output = result.stderr
        self.assertIn("could not finish", output)
        self.assertIn("baseline report", output)
        self.assertIn("--headless --report", output)
        self.assertNotIn(
            "package.module:Factory",
            output,
            "a loaded game must not be blamed for a corrupt report",
        )

    def test_mismatched_diff_dimensions_advise_matching_sizes(self):
        other_png = self.base / "other.png"
        other_report = self.base / "other.json"
        run(["--headless", "--frames", "1", "--size", "128x96",
             "--out", str(other_png), "--report", str(other_report)])
        result = run(["--headless", "--frames", "1", "--size", "128x96",
                      "--out", str(other_png), "--report", str(other_report),
                      "--compare-baseline", str(self.baseline_report),
                      "--diff-out", str(self.base / "delta.png")])
        self.assertEqual(result.returncode, 1)
        output = result.stderr
        self.assertIn("could not finish", output)
        self.assertIn("--size", output)
        self.assertNotIn("package.module:Factory", output)

    def test_baseline_gate_still_keys_on_pixels(self):
        # Same pixels at a new path must pass, even though the report hash
        # encodes the artifact path (ADR-063).
        current_png = self.base / "current.png"
        current_report = self.base / "current.json"
        run(["--headless", "--frames", "1", "--size", "96x64",
             "--out", str(current_png), "--report", str(current_report)])
        result = run(["--headless", "--frames", "1", "--size", "96x64",
                      "--out", str(current_png), "--report", str(current_report),
                      "--compare-baseline", str(self.baseline_report)])
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["diff"]["same_image"])

    def test_a_real_change_fails_the_gate_and_writes_a_diff(self):
        changed_png = self.base / "changed.png"
        changed_report = self.base / "changed.json"
        diff_image = self.base / "delta.png"
        result = run(["--headless", "--frames", "2", "--size", "96x64",
                      "--out", str(changed_png), "--report", str(changed_report),
                      "--compare-baseline", str(self.baseline_report),
                      "--diff-out", str(diff_image)])
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["diff"]["same_image"])
        self.assertTrue(diff_image.is_file(), "--diff-out must write the image")


if __name__ == "__main__":
    unittest.main()
