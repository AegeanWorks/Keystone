"""Deterministic runnable project bundles for Keystone games."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from keystone import __version__
from keystone.project import (
    ProjectContext,
    load_project,
    load_project_game,
    validate_project,
)
from keystone.serialization import write_json_atomic

EXPORT_SCHEMA_VERSION = 1
EXPORT_MANIFEST = "BUILD.json"
EXPORT_LAUNCHER = "run.py"
EXPORT_REQUIREMENTS = "requirements.txt"
EXPORT_README = "EXPORT.md"
RUNTIME_REQUIREMENTS = (
    "numpy==2.5.3",
    "PyOpenGL==3.1.10",
    "glfw==2.11.0",
)

_EXCLUDED_TOP_LEVEL = frozenset(
    {
        ".aikit",
        ".git",
        ".github",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "docs",
        "keystone",
        "tests",
        "venv",
    }
)
_EXCLUDED_DIRS = frozenset(
    {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
)
_EXCLUDED_FILES = frozenset({EXPORT_MANIFEST, ".DS_Store"})
_EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})

_LAUNCHER_SOURCE = '''"""Run this exported Keystone project."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor"))

from keystone.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(["--project", str(ROOT), *sys.argv[1:]]))
'''


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    # hygiene: allow binary hash read ignores text encoding
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_project(context: ProjectContext, target: Path) -> None:
    root = context.directory.resolve()
    for entry in sorted(root.rglob("*")):
        relative = entry.relative_to(root)
        parts = relative.parts
        if not parts or parts[0] in _EXCLUDED_TOP_LEVEL:
            continue
        if any(part in _EXCLUDED_DIRS for part in parts[:-1]):
            continue
        if entry.is_dir():
            continue
        if entry.suffix.lower() in _EXCLUDED_SUFFIXES or entry.name in _EXCLUDED_FILES:
            continue
        if entry.name.startswith(".tmp_") or _within(entry, target):
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry, destination)


def _copy_engine(target: Path) -> None:
    source = Path(__file__).resolve().parent
    vendor = target / "vendor"
    if vendor.exists():
        shutil.rmtree(vendor)
    shutil.copytree(
        source,
        vendor / "keystone",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def _write_export_docs(context: ProjectContext, target: Path) -> None:
    (target / EXPORT_LAUNCHER).write_text(_LAUNCHER_SOURCE, encoding="utf-8")
    (target / EXPORT_REQUIREMENTS).write_text(
        "\n".join(RUNTIME_REQUIREMENTS) + "\n", encoding="utf-8"
    )
    readme = (
        f"# {context.manifest.name} build\n\n"
        "This directory was exported by Keystone.\n\n"
        "```\n"
        "python -m pip install -r requirements.txt\n"
        "python run.py --simulate --frames 1\n"
        "python run.py\n"
        "```\n\n"
        "The bundled engine lives under `vendor/keystone`; `run.py` puts it "
        "first on sys.path.\n"
    )
    (target / EXPORT_README).write_text(readme, encoding="utf-8")


def _build_manifest(context: ProjectContext, target: Path) -> dict[str, object]:
    files: list[dict[str, object]] = []
    total = 0
    for path in sorted(target.rglob("*")):
        if not path.is_file() or path.name == EXPORT_MANIFEST:
            continue
        relative = path.relative_to(target).as_posix()
        size = path.stat().st_size
        total += size
        files.append({"path": relative, "size": size, "sha256": _sha256(path)})
    return {
        "schema": EXPORT_SCHEMA_VERSION,
        "project": {
            "name": context.manifest.name,
            "game": context.manifest.game,
        },
        "engine": {
            "name": "keystone",
            "version": __version__,
            "vendored": "vendor/keystone",
        },
        "entry": EXPORT_LAUNCHER,
        "requirements": EXPORT_REQUIREMENTS,
        "files": files,
        "summary": {
            "files": len(files),
            "bytes": total,
            "scenes": sum(
                1 for item in files if str(item["path"]).endswith(".kscene")
            ),
            "prefabs": sum(
                1 for item in files if str(item["path"]).endswith(".kprefab")
            ),
        },
    }


def export_project(
    project: str | Path,
    destination: str | Path,
    *,
    force: bool = False,
) -> dict[str, object]:
    """Validate a project and write a runnable, hashed export bundle."""
    context = load_project(project)
    game = load_project_game(context)
    report = validate_project(context, game)
    failures = [
        str(item.get("message", item)) for item in report.get("errors", [])
    ]
    failures.extend(
        f"prefab {item['name']}: {item['error']}"
        for item in report.get("prefabs", [])
        if item.get("error")
    )
    failures.extend(
        f"scene {item['name']}: {item['error']}"
        for item in report.get("scenes", [])
        if item.get("error")
    )
    if failures:
        raise ValueError("project validation failed: " + "; ".join(failures))

    root = context.directory.resolve()
    target = Path(destination).resolve()
    if target == root:
        raise ValueError("export destination must differ from the project directory")
    if target.exists() and not target.is_dir():
        raise ValueError(f"export destination is not a directory: {target}")
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(
            f"export destination is not empty: {target}.\n"
            "Why: exporting would overwrite or mix with existing files.\n"
            "Fix: choose an empty directory or pass --force."
        )
    target.mkdir(parents=True, exist_ok=True)
    _copy_project(context, target)
    _copy_engine(target)
    _write_export_docs(context, target)
    manifest = _build_manifest(context, target)
    write_json_atomic(target / EXPORT_MANIFEST, manifest)
    return manifest


__all__ = [
    "EXPORT_MANIFEST",
    "EXPORT_SCHEMA_VERSION",
    "export_project",
]
