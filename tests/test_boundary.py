"""Boundary test: the engine core contains no game rules or imports."""

import ast
import unittest
from pathlib import Path

import keystone

FORBIDDEN = {
    "beams",
    "combat",
    "demo",
    "expedition",
    "harness",
    "network",
    "procedural",
    "sim",
    "space",
    "space_expedition",
    "space_harness",
    "weave",
}


class CoreBoundaryTest(unittest.TestCase):
    def test_core_has_no_genre_modules(self):
        root = Path(keystone.__file__).parent
        for name in FORBIDDEN:
            self.assertFalse((root / f"{name}.py").exists(), name)
            self.assertFalse((root / name).exists(), name)

    def test_core_imports_only_core_modules(self):
        root = Path(keystone.__file__).parent
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    first = node.module.split(".")[0]
                    if first == "keystone" and len(node.module.split(".")) > 1:
                        imported = node.module.split(".")[1]
                        self.assertNotIn(imported, FORBIDDEN, f"{path} imports {node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        first = alias.name.split(".")[0]
                        if first == "games":
                            self.fail(f"{path} imports {alias.name}")


if __name__ == "__main__":
    unittest.main()
