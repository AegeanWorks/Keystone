"""File-backed prefab libraries for editors, tools and AI clients.

A library is one directory of versioned ``.kprefab`` documents. Names are
restricted to a portable filename alphabet, so a name can never escape the
library directory. Loading resolves mesh/material ids through the optional
asset registry and custom components through an explicit type map.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from keystone.prefab import Prefab

__all__ = ["PREFAB_SUFFIX", "PrefabEntry", "PrefabLibrary"]

PREFAB_SUFFIX = ".kprefab"
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _validate_name(name: object) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("prefab library name must be a non-blank string")
    if name != name.strip() or not _NAME.fullmatch(name):
        raise ValueError(
            "prefab library name may contain letters, digits, '.', '_' and '-' only"
        )
    return name


@dataclass(frozen=True, slots=True)
class PrefabEntry:
    """One library file and its loaded summary, or why it could not load."""

    name: str
    path: Path
    node_count: int | None = None
    error: str | None = None

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe entry for editor and AI documents."""
        return {
            "name": self.name,
            "node_count": self.node_count,
            "source": self.path.as_posix(),
            "error": self.error,
        }


class PrefabLibrary:
    """Discover, save and load ``.kprefab`` files in one directory."""

    def __init__(
        self,
        directory: str | Path,
        registry: object | None = None,
        component_types: Mapping[str, type] | None = None,
    ) -> None:
        self.directory = Path(directory)
        self.registry = registry
        if component_types is not None:
            if not isinstance(component_types, Mapping):
                raise TypeError("component_types must be a mapping of names to types")
            cleaned: dict[str, type] = {}
            for name, component_type in component_types.items():
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("component type names must be non-blank strings")
                if not isinstance(component_type, type):
                    raise TypeError("component_types values must be types")
                cleaned[name] = component_type
            self.component_types = cleaned
        else:
            self.component_types = None

    def path_for(self, name: str) -> Path:
        """Return the safe file path for one library name."""
        return self.directory / f"{_validate_name(name)}{PREFAB_SUFFIX}"

    def save(self, name: str, prefab: Prefab) -> PrefabEntry:
        """Write one prefab atomically; its internal name must match the entry."""
        if not isinstance(prefab, Prefab):
            raise TypeError("prefab library payload must be a Prefab")
        selected = _validate_name(name)
        if prefab.name != selected:
            raise ValueError(
                f"prefab name {prefab.name!r} does not match library name {selected!r}"
            )
        path = self.path_for(selected)
        prefab.save(path, self.registry)
        return PrefabEntry(selected, path, prefab.node_count)

    def load(self, name: str) -> Prefab:
        """Load one prefab or raise KeyError when the entry is absent."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(f"no saved prefab {name!r} in {self.directory}")
        try:
            return Prefab.load(path, self.registry, self.component_types)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"could not load prefab {name!r}: {exc}") from exc

    def entry(self, name: str) -> PrefabEntry:
        """Load one entry's summary, capturing load failures as ``error``."""
        path = self.path_for(name)
        try:
            prefab = self.load(name)
        except (KeyError, TypeError, ValueError) as exc:
            return PrefabEntry(name, path, error=str(exc))
        return PrefabEntry(name, path, prefab.node_count)

    def entries(self) -> tuple[PrefabEntry, ...]:
        """Return every ``.kprefab`` file in stable name order."""
        if not self.directory.exists():
            return ()
        if not self.directory.is_dir():
            raise ValueError(f"prefab library path is not a directory: {self.directory}")
        entries: list[PrefabEntry] = []
        for path in sorted(self.directory.glob(f"*{PREFAB_SUFFIX}")):
            if not path.is_file():
                continue
            name = path.stem
            try:
                _validate_name(name)
            except ValueError as exc:
                entries.append(PrefabEntry(name, path, error=str(exc)))
                continue
            entries.append(self.entry(name))
        return tuple(entries)

    def describe(self) -> list[dict[str, object]]:
        """Return JSON-safe summaries for every library file."""
        return [entry.describe() for entry in self.entries()]
