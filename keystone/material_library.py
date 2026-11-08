"""File-backed material libraries for editors, tools and AI clients."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.prefab_library import validate_library_name
from keystone.serialization import read_json, write_json_atomic
from keystone.texture import TextureData

MATERIAL_SUFFIX = ".kmaterial"
MATERIAL_SCHEMA_VERSION = 1

__all__ = [
    "MATERIAL_SCHEMA_VERSION",
    "MATERIAL_SUFFIX",
    "MaterialEntry",
    "MaterialLibrary",
    "material_from_document",
    "material_to_document",
]


def _vec3(value: object, label: str) -> Vec3:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, (list, tuple))
        or len(value) != 3
    ):
        raise TypeError(f"material {label} must contain three numbers")
    numbers: list[float] = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise TypeError(f"material {label} must contain numbers")
        number = float(component)
        if not math.isfinite(number):
            raise ValueError(f"material {label} must be finite")
        numbers.append(number)
    return Vec3(*numbers)


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"material {label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"material {label} must be finite")
    return number


def material_from_document(
    data: object, registry: object | None = None
) -> Material:
    """Build a validated Material from one JSON-safe document."""
    if not isinstance(data, dict):
        raise TypeError("material document must be a JSON object")
    schema = data.get("schema", MATERIAL_SCHEMA_VERSION)
    if schema != MATERIAL_SCHEMA_VERSION:
        raise ValueError(f"unsupported material schema {schema!r}")
    allowed = {
        "schema",
        "name",
        "color",
        "specular",
        "shininess",
        "checker_scale",
        "metallic",
        "roughness",
        "emissive",
        "texture",
    }
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"material has unknown keys: {sorted(unknown)}")
    texture = None
    texture_id = data.get("texture")
    if texture_id is not None:
        if not isinstance(texture_id, str) or not texture_id.strip():
            raise TypeError("material texture must be an asset id or null")
        if registry is None:
            raise ValueError("material texture needs an AssetRegistry")
        try:
            record = registry.require(texture_id)  # type: ignore[union-attr]
        except KeyError as exc:
            raise ValueError(
                f"material texture {texture_id!r} is not registered"
            ) from exc
        if record.kind != "texture" or not isinstance(record.payload, TextureData):
            raise ValueError(f"material asset {texture_id!r} is not a texture")
        texture = record.payload
    return Material(
        color=_vec3(data.get("color", [0.78, 0.78, 0.82]), "color"),
        specular=_number(data.get("specular", 0.35), "specular"),
        shininess=_number(data.get("shininess", 32.0), "shininess"),
        checker_scale=_number(
            data.get("checker_scale", 0.0), "checker_scale"
        ),
        texture=texture,
        metallic=_number(data.get("metallic", 0.0), "metallic"),
        roughness=_number(data.get("roughness", 0.7), "roughness"),
        emissive=_vec3(data.get("emissive", [0.0, 0.0, 0.0]), "emissive"),
    )


def material_to_document(
    name: str, material: Material, registry: object | None = None
) -> dict[str, object]:
    """Return a JSON-safe material document, resolving its texture id."""
    if not isinstance(material, Material):
        raise TypeError("material document payload must be a Material")
    texture_id = None
    if material.texture is not None:
        if registry is None:
            raise ValueError("material texture needs an AssetRegistry")
        for record in registry:  # type: ignore[union-attr]
            if getattr(record, "kind", None) == "texture" and (
                getattr(record, "payload", None) is material.texture
            ):
                texture_id = str(record.id)
                break
        if texture_id is None:
            raise ValueError("material texture is not registered")
    color = material.color
    emissive = material.emissive
    return {
        "schema": MATERIAL_SCHEMA_VERSION,
        "name": name,
        "color": [color.x, color.y, color.z],
        "specular": material.specular,
        "shininess": material.shininess,
        "checker_scale": material.checker_scale,
        "metallic": material.metallic,
        "roughness": material.roughness,
        "emissive": [emissive.x, emissive.y, emissive.z],
        "texture": texture_id,
    }


@dataclass(frozen=True, slots=True)
class MaterialEntry:
    """One library file and its material summary, or why it could not load."""

    name: str
    path: Path
    color: tuple[float, float, float] | None = None
    metallic: float | None = None
    roughness: float | None = None
    emissive: tuple[float, float, float] | None = None
    texture: str | None = None
    error: str | None = None

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe entry for editor and AI documents."""
        return {
            "name": self.name,
            "source": self.path.as_posix(),
            "color": list(self.color) if self.color is not None else None,
            "metallic": self.metallic,
            "roughness": self.roughness,
            "emissive": (
                list(self.emissive) if self.emissive is not None else None
            ),
            "texture": self.texture,
            "error": self.error,
        }


class MaterialLibrary:
    """Discover, save and load ``.kmaterial`` files in one directory."""

    def __init__(self, directory: str | Path, registry: object | None = None) -> None:
        self.directory = Path(directory)
        self.registry = registry

    def asset_id(self, name: str) -> str:
        """Return the registry id used for a saved material."""
        return f"material.{validate_library_name(name)}"

    def path_for(self, name: str) -> Path:
        """Return the safe file path for one library name."""
        return self.directory / f"{validate_library_name(name)}{MATERIAL_SUFFIX}"

    def save(self, name: str, material: Material) -> MaterialEntry:
        """Write one material atomically."""
        selected = validate_library_name(name)
        path = self.path_for(selected)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            path, material_to_document(selected, material, self.registry), backup=False
        )
        return self.entry(selected)

    def load(self, name: str) -> Material:
        """Load one material or raise KeyError when the entry is absent."""
        path = self.path_for(name)
        if not path.is_file():
            raise KeyError(f"no saved material {name!r} in {self.directory}")
        try:
            return material_from_document(read_json(path), self.registry)
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(f"could not load material {name!r}: {exc}") from exc

    def entry(self, name: str) -> MaterialEntry:
        """Load one entry's summary, capturing load failures as ``error``."""
        path = self.path_for(name)
        try:
            material = self.load(name)
        except (KeyError, TypeError, ValueError) as exc:
            return MaterialEntry(name, path, error=str(exc))
        color = material.color
        emissive = material.emissive
        texture_id = None
        if material.texture is not None and self.registry is not None:
            for record in self.registry:  # type: ignore[union-attr]
                if getattr(record, "kind", None) == "texture" and (
                    getattr(record, "payload", None) is material.texture
                ):
                    texture_id = str(record.id)
                    break
        return MaterialEntry(
            name,
            path,
            color=(color.x, color.y, color.z),
            metallic=material.metallic,
            roughness=material.roughness,
            emissive=(emissive.x, emissive.y, emissive.z),
            texture=texture_id,
        )

    def entries(self) -> tuple[MaterialEntry, ...]:
        """Return every ``.kmaterial`` file in stable name order."""
        if not self.directory.exists():
            return ()
        if not self.directory.is_dir():
            raise ValueError(
                f"material library path is not a directory: {self.directory}"
            )
        entries: list[MaterialEntry] = []
        for path in sorted(self.directory.glob(f"*{MATERIAL_SUFFIX}")):
            if not path.is_file():
                continue
            name = path.stem
            try:
                validate_library_name(name)
            except ValueError as exc:
                entries.append(MaterialEntry(name, path, error=str(exc)))
                continue
            entries.append(self.entry(name))
        return tuple(entries)

    def register_all(self, registry: object | None = None) -> int:
        """Register every loadable material; invalid entries stay reported."""
        target = registry if registry is not None else self.registry
        if target is None:
            return 0
        registered = 0
        for entry in self.entries():
            if entry.error is not None:
                continue
            try:
                material = self.load(entry.name)
                target.register(  # type: ignore[union-attr]
                    self.asset_id(entry.name),
                    material,
                    kind="material",
                    source=entry.path,
                    replace=True,
                )
            except (KeyError, TypeError, ValueError):
                continue
            registered += 1
        return registered
