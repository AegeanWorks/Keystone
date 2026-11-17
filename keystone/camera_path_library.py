"""File-backed camera path libraries for editors, tools and AI clients.

A library is one directory of schema-1 ``.kpath`` documents. Names follow the
same portable alphabet as prefab libraries, so a name can never escape the
library directory. Deleting moves an entry into ``.trash`` for recovery,
mirroring the animation and state-machine libraries.

Documents are written atomically without a ``.bak`` copy because a path is an
authored source file, not a save game; a corrupt entry is reported per entry
instead of failing the whole listing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from keystone.camera_path import (
    CameraPath,
    camera_path_from_dict,
    camera_path_to_dict,
)
from keystone.library_trash import move_to_trash, restore_from_trash, trash_entries
from keystone.prefab_library import validate_library_name
from keystone.serialization import read_json, write_json_atomic

CAMERA_PATH_SUFFIX = ".kpath"

__all__ = ["CAMERA_PATH_SUFFIX", "CameraPathEntry", "CameraPathLibrary"]


@dataclass(frozen=True, slots=True)
class CameraPathEntry:
    """One library file and its path summary, or why it could not load."""

    name: str
    path: Path
    duration: float | None = None
    keys: int | None = None
    loop: bool | None = None
    error: str | None = None

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe entry for editor and AI documents."""
        return {
            "name": self.name,
            "duration": self.duration,
            "keys": self.keys,
            "loop": self.loop,
            "source": self.path.as_posix(),
            "error": self.error,
        }


class CameraPathLibrary:
    """Discover, save and load ``.kpath`` camera paths in one directory."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def path_for(self, name: str) -> Path:
        """Return the safe file path for one library name."""
        return self.directory / f"{validate_library_name(name)}{CAMERA_PATH_SUFFIX}"

    def save(self, name: str, path: CameraPath) -> CameraPathEntry:
        """Write one camera path atomically and return its summary."""
        if not isinstance(path, CameraPath):
            raise TypeError("camera path library payload must be a CameraPath")
        selected = validate_library_name(name)
        target = self.path_for(selected)
        target.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(target, camera_path_to_dict(path), backup=False)
        return self.entry(selected)

    def load(self, name: str) -> CameraPath:
        """Load one path or raise KeyError when the entry is absent."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(f"no saved camera path {name!r} in {self.directory}")
        try:
            return camera_path_from_dict(read_json(path))
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(f"could not load camera path {name!r}: {exc}") from exc

    def rename(self, old: str, new: str) -> CameraPathEntry:
        """Rename one entry, rejecting collisions and updating the file."""
        old_path = self.path_for(old)
        new_path = self.path_for(new)
        if not old_path.is_file():
            raise KeyError(f"no saved camera path {old!r} in {self.directory}")
        if old == new:
            return self.entry(old)
        if new_path.exists():
            raise FileExistsError(
                f"camera path {new!r} already exists in {self.directory}"
            )
        data = read_json(old_path)
        if not isinstance(data, dict):
            raise TypeError(f"camera path {old!r} must be a JSON object")
        write_json_atomic(new_path, data, backup=False)
        old_path.unlink()
        return self.entry(new)

    def duplicate(self, old: str, new: str) -> CameraPathEntry:
        """Copy one entry to a new name, rejecting collisions."""
        old_path = self.path_for(old)
        new_path = self.path_for(new)
        if old == new:
            raise ValueError("duplicate target must differ from the source")
        if not old_path.is_file():
            raise KeyError(f"no saved camera path {old!r} in {self.directory}")
        if new_path.exists():
            raise FileExistsError(
                f"camera path {new!r} already exists in {self.directory}"
            )
        data = read_json(old_path)
        if not isinstance(data, dict):
            raise TypeError(f"camera path {old!r} must be a JSON object")
        write_json_atomic(new_path, data, backup=False)
        return self.entry(new)

    def delete(self, name: str) -> Path:
        """Move one entry to the library trash and return its former path."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(f"no saved camera path {name!r} in {self.directory}")
        move_to_trash(path, CAMERA_PATH_SUFFIX)
        return path

    def trash(self) -> list[dict[str, str]]:
        """Return recoverable deleted entries."""
        return trash_entries(self.directory, CAMERA_PATH_SUFFIX)

    def restore(self, trash_name: str) -> CameraPathEntry:
        """Restore one trashed entry and return its summary."""
        path = restore_from_trash(
            self.directory,
            trash_name,
            CAMERA_PATH_SUFFIX,
            validate_library_name,
        )
        return self.entry(path.stem)

    def entry(self, name: str) -> CameraPathEntry:
        """Load one entry's summary, capturing load failures as ``error``."""
        path = self.path_for(name)
        try:
            camera_path = self.load(name)
        except (KeyError, TypeError, ValueError) as exc:
            return CameraPathEntry(name, path, error=str(exc))
        return CameraPathEntry(
            name,
            path,
            duration=camera_path.duration,
            keys=len(camera_path.keys),
            loop=camera_path.loop,
        )

    def entries(self) -> tuple[CameraPathEntry, ...]:
        """Return every ``.kpath`` file in stable name order."""
        if not self.directory.exists():
            return ()
        if not self.directory.is_dir():
            raise ValueError(
                f"camera path library path is not a directory: {self.directory}"
            )
        entries: list[CameraPathEntry] = []
        for path in sorted(self.directory.glob(f"*{CAMERA_PATH_SUFFIX}")):
            if not path.is_file():
                continue
            name = path.stem
            try:
                validate_library_name(name)
            except ValueError as exc:
                entries.append(CameraPathEntry(name, path, error=str(exc)))
                continue
            entries.append(self.entry(name))
        return tuple(entries)
