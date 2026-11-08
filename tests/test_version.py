"""Tests that the version is stated in exactly one place and does not drift."""

import re
import unittest
from pathlib import Path

import keystone
from keystone._version import __version__ as private_version

ROOT = Path(__file__).resolve().parent.parent


class VersionTest(unittest.TestCase):
    def test_package_and_private_version_agree(self):
        self.assertEqual(keystone.__version__, private_version)

    def test_pyproject_version_matches_the_package(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        self.assertIsNotNone(match, "pyproject.toml must declare a version")
        self.assertEqual(
            match.group(1),
            keystone.__version__,
            "pyproject.toml and keystone.__version__ drifted; "
            "update keystone/_version.py and pyproject.toml together",
        )

    def test_architecture_docs_do_not_claim_a_future_version(self):
        known = tuple(
            int(part) for part in keystone.__version__.split(".")
        )
        text = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")
        declared = {
            tuple(int(part) for part in found.split("."))
            for found in re.findall(r"v(\d+\.\d+\.\d+)", text)
        }
        ahead = sorted(v for v in declared if v > known)
        self.assertEqual(
            ahead,
            [],
            f"ARCHITECTURE.md claims versions ahead of {keystone.__version__}: "
            f"{['.'.join(map(str, v)) for v in ahead]}",
        )

    def test_changelog_exists_and_lists_the_current_version(self):
        changelog = ROOT / "CHANGELOG.md"
        self.assertTrue(changelog.is_file(), "CHANGELOG.md is missing")
        text = changelog.read_text(encoding="utf-8")
        self.assertIn(
            keystone.__version__,
            text,
            "CHANGELOG.md must mention the current version",
        )


if __name__ == "__main__":
    unittest.main()
