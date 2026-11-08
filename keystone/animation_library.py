"""File-backed animation clip libraries for editors, tools and AI clients."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from keystone.animation import AnimationClip
from keystone.library_trash import move_to_trash, restore_from_trash, trash_entries
from keystone.prefab_library import validate_library_name
from keystone.serialization import read_json, write_json_atomic

ANIMATION_SUFFIX = ".kanim"

__all__ = ["ANIMATION_SUFFIX", "AnimationEntry", "AnimationLibrary"]


@dataclass(frozen=True, slots=True)
class AnimationEntry:
    """One library file and its clip summary, or why it could not load."""

    name: str
    path: Path
    duration: float | None = None
    track_count: int | None = None
    error: str | None = None

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe entry for editor and AI documents."""
        return {
            "name": self.name,
            "duration": self.duration,
            "track_count": self.track_count,
            "source": self.path.as_posix(),
            "error": self.error,
        }


class AnimationLibrary:
    """Discover, save and load ``.kanim`` clips in one directory."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def path_for(self, name: str) -> Path:
        """Return the safe file path for one library name."""
        return self.directory / f"{validate_library_name(name)}{ANIMATION_SUFFIX}"

    def save(self, name: str, clip: AnimationClip) -> AnimationEntry:
        """Write one clip atomically; its internal name must match the entry."""
        if not isinstance(clip, AnimationClip):
            raise TypeError("animation library payload must be an AnimationClip")
        selected = validate_library_name(name)
        if clip.name != selected:
            raise ValueError(
                f"clip name {clip.name!r} does not match library name {selected!r}"
            )
        path = self.path_for(selected)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, clip.to_dict(), backup=False)
        return self.entry(selected)

    def load(self, name: str) -> AnimationClip:
        """Load one clip or raise KeyError when the entry is absent."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(f"no saved animation {name!r} in {self.directory}")
        try:
            return AnimationClip.from_dict(read_json(path))
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(f"could not load animation {name!r}: {exc}") from exc

    def delete(self, name: str) -> Path:
        """Move one entry to the library trash and return its former path."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(f"no saved animation {name!r} in {self.directory}")
        move_to_trash(path, ANIMATION_SUFFIX)
        return path

    def trash(self) -> list[dict[str, str]]:
        """Return recoverable deleted entries."""
        return trash_entries(self.directory, ANIMATION_SUFFIX)

    def restore(self, trash_name: str) -> AnimationEntry:
        """Restore one trashed entry and return its summary."""
        path = restore_from_trash(
            self.directory, trash_name, ANIMATION_SUFFIX, validate_library_name
        )
        return self.entry(path.stem)

    def entry(self, name: str) -> AnimationEntry:
        """Load one entry's summary, capturing load failures as ``error``."""
        path = self.path_for(name)
        try:
            clip = self.load(name)
        except (KeyError, TypeError, ValueError) as exc:
            return AnimationEntry(name, path, error=str(exc))
        return AnimationEntry(
            name,
            path,
            duration=clip.duration(),
            track_count=sum(
                len(tracks)
                for tracks in (
                    clip.position_tracks,
                    clip.rotation_tracks,
                    clip.scale_tracks,
                )
            ),
        )

    def entries(self) -> tuple[AnimationEntry, ...]:
        """Return every ``.kanim`` file in stable name order."""
        if not self.directory.exists():
            return ()
        if not self.directory.is_dir():
            raise ValueError(
                f"animation library path is not a directory: {self.directory}"
            )
        entries: list[AnimationEntry] = []
        for path in sorted(self.directory.glob(f"*{ANIMATION_SUFFIX}")):
            if not path.is_file():
                continue
            name = path.stem
            try:
                validate_library_name(name)
            except ValueError as exc:
                entries.append(AnimationEntry(name, path, error=str(exc)))
                continue
            entries.append(self.entry(name))
        return tuple(entries)
