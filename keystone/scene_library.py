"""File-backed scene libraries for editors, tools and AI clients.

A library is one directory of versioned ``.kscene`` documents. Saving writes
the component-aware scene snapshot atomically; loading can rebuild a new Scene
or restore one in place, preserving game-owned Scene references.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from keystone.component_codec import validate_component_types
from keystone.library_trash import move_to_trash, restore_from_trash, trash_entries
from keystone.prefab_library import validate_library_name
from keystone.scene import Scene
from keystone.scene_snapshot import restore_scene, scene_from_dict, scene_to_dict
from keystone.serialization import read_json, write_json_atomic

__all__ = ["SCENE_SUFFIX", "SceneEntry", "SceneLibrary"]

SCENE_SUFFIX = ".kscene"


def _node_count(scene: Scene) -> int:
    return max(0, sum(1 for _ in scene.traverse()) - 1)


def _asset_refs(data: Mapping[str, object]) -> list[tuple[str, str, object]]:
    raw_nodes = data.get("nodes", [])
    if not isinstance(raw_nodes, (list, tuple)):
        return []
    refs: list[tuple[str, str, object]] = []
    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            continue
        for field in ("mesh", "material"):
            value = raw.get(field)
            if value is not None:
                refs.append((field, field, value))
    return refs


@dataclass(frozen=True, slots=True)
class SceneEntry:
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


class SceneLibrary:
    """Discover, save, load and restore ``.kscene`` files in one directory."""

    def __init__(
        self,
        directory: str | Path,
        registry: object | None = None,
        component_types: Mapping[str, type] | None = None,
    ) -> None:
        self.directory = Path(directory)
        self.registry = registry
        self.component_types = validate_component_types(component_types)

    def path_for(self, name: str) -> Path:
        """Return the safe file path for one library name."""
        return self.directory / f"{validate_library_name(name)}{SCENE_SUFFIX}"

    def save(self, name: str, scene: Scene) -> SceneEntry:
        """Write one scene snapshot atomically."""
        if not isinstance(scene, Scene):
            raise TypeError("scene library payload must be a Scene")
        selected = validate_library_name(name)
        document = scene_to_dict(scene, self.registry)
        document["name"] = selected
        path = self.path_for(selected)
        write_json_atomic(path, document, backup=False)
        return SceneEntry(selected, path, _node_count(scene))

    def document(self, name: str) -> dict:
        """Read one scene document without rebuilding it."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(f"no saved scene {name!r} in {self.directory}")
        try:
            data = read_json(path)
        except (OSError, ValueError) as exc:
            raise ValueError(f"could not read scene {name!r}: {exc}") from exc
        if not isinstance(data, Mapping):
            raise TypeError(f"scene {name!r} must be a JSON object")
        if "name" in data and data["name"] != name:
            raise ValueError(f"scene {name!r} names a different entry")
        return dict(data)

    def _require_assets(self, name: str, data: Mapping[str, object]) -> None:
        refs = _asset_refs(data)
        if not refs:
            return
        if self.registry is None:
            raise ValueError(
                f"scene {name!r} references assets but no registry was provided"
            )
        for field, kind, value in refs:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"scene {name!r} has an invalid {field} id")
            record = self.registry.get(value)  # type: ignore[union-attr]
            if record is None:
                raise ValueError(
                    f"scene {name!r} references missing {field} asset {value!r}"
                )
            if getattr(record, "kind", kind) != kind:
                raise ValueError(
                    f"scene {name!r} {field} asset {value!r} is not a {kind}"
                )

    def load(self, name: str) -> Scene:
        """Load one scene or raise KeyError when the entry is absent."""
        data = self.document(name)
        try:
            self._require_assets(name, data)
            return scene_from_dict(data, self.registry, self.component_types)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"could not load scene {name!r}: {exc}") from exc

    def load_into(self, name: str, scene: Scene) -> Scene:
        """Replace one existing Scene in place from a library entry."""
        if not isinstance(scene, Scene):
            raise TypeError("scene restore target must be a Scene")
        data = self.document(name)
        try:
            self._require_assets(name, data)
            return restore_scene(scene, data, self.registry, self.component_types)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"could not load scene {name!r}: {exc}") from exc

    def rename(self, old: str, new: str) -> SceneEntry:
        """Rename one entry, updating its internal name and rejecting collisions."""
        old_path = self.path_for(old)
        new_path = self.path_for(new)
        if old == new:
            return self.entry(old)
        if not old_path.is_file():
            raise KeyError(f"no saved scene {old!r} in {self.directory}")
        if new_path.exists():
            raise FileExistsError(f"scene {new!r} already exists in {self.directory}")
        data = read_json(old_path)
        if not isinstance(data, dict):
            raise TypeError(f"scene {old!r} must be a JSON object")
        data["name"] = new
        write_json_atomic(new_path, data, backup=False)
        old_path.unlink()
        return self.entry(new)

    def duplicate(self, old: str, new: str) -> SceneEntry:
        """Copy one entry to a new name, updating its internal name."""
        old_path = self.path_for(old)
        new_path = self.path_for(new)
        if old == new:
            raise ValueError("duplicate target must differ from the source")
        if not old_path.is_file():
            raise KeyError(f"no saved scene {old!r} in {self.directory}")
        if new_path.exists():
            raise FileExistsError(f"scene {new!r} already exists in {self.directory}")
        data = read_json(old_path)
        if not isinstance(data, dict):
            raise TypeError(f"scene {old!r} must be a JSON object")
        data["name"] = new
        write_json_atomic(new_path, data, backup=False)
        return self.entry(new)

    def delete(self, name: str) -> Path:
        """Move one entry to the library trash and return its former path."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(f"no saved scene {name!r} in {self.directory}")
        move_to_trash(path, SCENE_SUFFIX)
        return path

    def trash(self) -> list[dict[str, str]]:
        """Return recoverable deleted entries."""
        return trash_entries(self.directory, SCENE_SUFFIX)

    def restore(self, trash_name: str) -> SceneEntry:
        """Restore one trashed entry and return its summary."""
        path = restore_from_trash(
            self.directory, trash_name, SCENE_SUFFIX, validate_library_name
        )
        return self.entry(path.stem)

    def entry(self, name: str) -> SceneEntry:
        """Load one entry's summary, capturing load failures as ``error``."""
        path = self.path_for(name)
        try:
            scene = self.load(name)
        except (KeyError, TypeError, ValueError) as exc:
            return SceneEntry(name, path, error=str(exc))
        return SceneEntry(name, path, _node_count(scene))

    def entries(self) -> tuple[SceneEntry, ...]:
        """Return every ``.kscene`` file in stable name order."""
        if not self.directory.exists():
            return ()
        if not self.directory.is_dir():
            raise ValueError(f"scene library path is not a directory: {self.directory}")
        entries: list[SceneEntry] = []
        for path in sorted(self.directory.glob(f"*{SCENE_SUFFIX}")):
            if not path.is_file():
                continue
            name = path.stem
            try:
                validate_library_name(name)
            except ValueError as exc:
                entries.append(SceneEntry(name, path, error=str(exc)))
                continue
            entries.append(self.entry(name))
        return tuple(entries)

    def describe(self) -> list[dict[str, object]]:
        """Return JSON-safe summaries for every library file."""
        return [entry.describe() for entry in self.entries()]
