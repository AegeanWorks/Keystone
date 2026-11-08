"""File-backed animation state machine libraries for editors and AI clients."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from keystone.animation_state import AnimationStateMachine
from keystone.library_trash import move_to_trash, restore_from_trash, trash_entries
from keystone.prefab_library import validate_library_name
from keystone.serialization import read_json, write_json_atomic

STATE_MACHINE_SUFFIX = ".kstate"

__all__ = ["STATE_MACHINE_SUFFIX", "StateMachineEntry", "StateMachineLibrary"]


@dataclass(frozen=True, slots=True)
class StateMachineEntry:
    """One library file and its state summary, or why it could not load."""

    name: str
    path: Path
    states: int | None = None
    transitions: int | None = None
    current: str | None = None
    error: str | None = None

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe entry for editor and AI documents."""
        return {
            "name": self.name,
            "states": self.states,
            "transitions": self.transitions,
            "current": self.current,
            "source": self.path.as_posix(),
            "error": self.error,
        }


class StateMachineLibrary:
    """Discover, save and load ``.kstate`` machines in one directory."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def path_for(self, name: str) -> Path:
        """Return the safe file path for one library name."""
        return (
            self.directory
            / f"{validate_library_name(name)}{STATE_MACHINE_SUFFIX}"
        )

    def save(
        self, name: str, machine: AnimationStateMachine
    ) -> StateMachineEntry:
        """Write one state machine atomically."""
        if not isinstance(machine, AnimationStateMachine):
            raise TypeError(
                "state machine library payload must be an AnimationStateMachine"
            )
        selected = validate_library_name(name)
        path = self.path_for(selected)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, machine.to_dict(), backup=False)
        return self.entry(selected)

    def load(self, name: str) -> AnimationStateMachine:
        """Load one machine or raise KeyError when the entry is absent."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(
                f"no saved state machine {name!r} in {self.directory}"
            )
        try:
            return AnimationStateMachine.from_dict(read_json(path))
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(
                f"could not load state machine {name!r}: {exc}"
            ) from exc

    def delete(self, name: str) -> Path:
        """Move one entry to the library trash and return its former path."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(
                f"no saved state machine {name!r} in {self.directory}"
            )
        move_to_trash(path, STATE_MACHINE_SUFFIX)
        return path

    def trash(self) -> list[dict[str, str]]:
        """Return recoverable deleted entries."""
        return trash_entries(self.directory, STATE_MACHINE_SUFFIX)

    def restore(self, trash_name: str) -> StateMachineEntry:
        """Restore one trashed entry and return its summary."""
        path = restore_from_trash(
            self.directory,
            trash_name,
            STATE_MACHINE_SUFFIX,
            validate_library_name,
        )
        return self.entry(path.stem)

    def entry(self, name: str) -> StateMachineEntry:
        """Load one entry's summary, capturing load failures as ``error``."""
        path = self.path_for(name)
        try:
            machine = self.load(name)
        except (KeyError, TypeError, ValueError) as exc:
            return StateMachineEntry(name, path, error=str(exc))
        return StateMachineEntry(
            name,
            path,
            states=len(machine.states),
            transitions=len(machine.transitions),
            current=machine.current,
        )

    def entries(self) -> tuple[StateMachineEntry, ...]:
        """Return every ``.kstate`` file in stable name order."""
        if not self.directory.exists():
            return ()
        if not self.directory.is_dir():
            raise ValueError(
                f"state machine library path is not a directory: {self.directory}"
            )
        entries: list[StateMachineEntry] = []
        for path in sorted(self.directory.glob(f"*{STATE_MACHINE_SUFFIX}")):
            if not path.is_file():
                continue
            name = path.stem
            try:
                validate_library_name(name)
            except ValueError as exc:
                entries.append(StateMachineEntry(name, path, error=str(exc)))
                continue
            entries.append(self.entry(name))
        return tuple(entries)
