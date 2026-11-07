"""Soft-delete helpers for file-backed scene and prefab libraries.

Deleting an entry moves it into a ``.trash`` directory with a unique suffix so
it can be restored without overwriting live content. Library listings only
scan the root directory, so trashed files disappear from normal views.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path

__all__ = [
    "TRASH_DIRECTORY",
    "move_to_trash",
    "restore_from_trash",
    "trash_entries",
]

TRASH_DIRECTORY = ".trash"


def _trash_root(directory: Path) -> Path:
    return directory / TRASH_DIRECTORY


def move_to_trash(path: Path, suffix: str) -> Path:
    """Move one library file into the trash directory and return its new path."""
    root = _trash_root(path.parent)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{path.stem}.{uuid.uuid4().hex}{suffix}"
    path.replace(target)
    return target


def _original_name(trash_name: str) -> str:
    stem = Path(trash_name).stem
    return stem.rsplit(".", 1)[0] if "." in stem else stem


def trash_entries(directory: Path, suffix: str) -> list[dict[str, str]]:
    """Return JSON-safe summaries of trashed entries in stable order."""
    root = _trash_root(directory)
    if not root.is_dir():
        return []
    entries: list[dict[str, str]] = []
    for path in sorted(root.glob(f"*{suffix}")):
        if not path.is_file():
            continue
        entries.append(
            {
                "name": _original_name(path.name),
                "trash": path.name,
                "source": path.as_posix(),
            }
        )
    return entries


def restore_from_trash(
    directory: Path,
    trash_name: str,
    suffix: str,
    validate_name: Callable[[object], str],
) -> Path:
    """Move one trashed entry back into the library without overwriting."""
    if not isinstance(trash_name, str) or not trash_name.strip():
        raise ValueError("trash entry must be a non-blank file name")
    if Path(trash_name).name != trash_name:
        raise ValueError("trash entry must be a file name, not a path")
    source = _trash_root(directory) / trash_name
    if not source.is_file():
        raise KeyError(f"no trashed entry {trash_name!r} in {_trash_root(directory)}")
    if source.suffix != suffix:
        raise ValueError(f"trash entry must use the {suffix} suffix")
    name = validate_name(_original_name(trash_name))
    target = directory / f"{name}{suffix}"
    if target.exists():
        raise FileExistsError(f"library entry {name!r} already exists")
    source.replace(target)
    return target
