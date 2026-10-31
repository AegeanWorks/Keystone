"""Game-agnostic asset registry with stable ids, content hashes and dependencies."""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from keystone.geometry import Material, MeshData
from keystone.texture import TextureData

ASSET_KINDS = ("mesh", "material", "texture")
AssetPayload = MeshData | Material | TextureData


@dataclass(frozen=True, slots=True)
class AssetRecord:
    """One registered asset: a stable id, kind, immutable payload and content digest."""

    id: str
    kind: str
    payload: AssetPayload
    sha256: str
    source: Path | None = None
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_id(self.id)
        _validate_kind(self.kind)
        if _kind_of(self.payload) != self.kind:
            raise TypeError(f"payload is a {_kind_of(self.payload)}, not a {self.kind}")
        if len(self.sha256) != 64:
            raise ValueError("sha256 must be a 64-character hex digest")
        if self.source is not None and not isinstance(self.source, Path):
            raise TypeError("source must be a Path or None")
        for dependency in self.dependencies:
            _validate_dependency(self.id, dependency)

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe description for AI clients and diagnostics."""
        return {
            "id": self.id,
            "kind": self.kind,
            "sha256": self.sha256,
            "source": self.source.as_posix() if self.source is not None else None,
            "dependencies": list(self.dependencies),
        }


class AssetRegistry:
    """Caller-owned registry for meshes, materials and textures.

    The registry is intentionally synchronous: it starts no thread and watches no files. A game
    that wants hot reload calls ``refresh()`` from its own loop. Registering or replacing one asset
    is a single dictionary assignment, so a reader sees either the old or the new record.
    """

    def __init__(self) -> None:
        self._records: dict[str, AssetRecord] = {}

    def __len__(self) -> int:
        return len(self._records)

    def __contains__(self, asset_id: object) -> bool:
        return asset_id in self._records

    def __iter__(self) -> Iterator[AssetRecord]:
        return iter(self._records.values())

    def register(
        self,
        asset_id: str,
        payload: AssetPayload,
        *,
        kind: str | None = None,
        source: str | Path | None = None,
        dependencies: Iterable[str] = (),
        replace: bool = False,
    ) -> AssetRecord:
        """Register one asset, inferring its kind from the payload when omitted."""
        _validate_id(asset_id)
        inferred = _kind_of(payload)
        if kind is not None:
            _validate_kind(kind)
            if kind != inferred:
                raise TypeError(f"payload is a {inferred}, not a {kind}")
        kind = inferred if kind is None else kind
        if asset_id in self._records and not replace:
            raise ValueError(
                f"asset {asset_id!r} is already registered; pass replace=True to replace it"
            )
        record = AssetRecord(
            id=asset_id,
            kind=kind,
            payload=payload,
            sha256=_digest(kind, payload),
            source=Path(source) if source is not None else None,
            dependencies=_dependencies(asset_id, dependencies),
        )
        self._records[asset_id] = record
        return record

    def get(self, asset_id: str) -> AssetRecord | None:
        """Return one record, or None when the id is not registered."""
        return self._records.get(asset_id)

    def require(self, asset_id: str) -> AssetRecord:
        """Return one record or raise a KeyError naming the missing asset."""
        record = self._records.get(asset_id)
        if record is None:
            raise KeyError(f"asset {asset_id!r} is not registered")
        return record

    def remove(self, asset_id: str) -> AssetRecord:
        """Remove one record or raise a KeyError naming the missing asset."""
        record = self._records.pop(asset_id, None)
        if record is None:
            raise KeyError(f"asset {asset_id!r} is not registered")
        return record

    def clear(self) -> None:
        self._records.clear()

    def ids(self, kind: str | None = None) -> tuple[str, ...]:
        """Return registered ids in insertion order, optionally filtered by kind."""
        if kind is not None:
            _validate_kind(kind)
        return tuple(
            asset_id for asset_id, record in self._records.items()
            if kind is None or record.kind == kind
        )

    def find_by_digest(self, sha256: str) -> tuple[AssetRecord, ...]:
        """Return every record whose content digest matches, in insertion order."""
        return tuple(record for record in self._records.values() if record.sha256 == sha256)

    def duplicates(self) -> tuple[tuple[str, ...], ...]:
        """Return groups of ids that share one kind and content digest."""
        groups: dict[tuple[str, str], list[str]] = {}
        for asset_id, record in self._records.items():
            groups.setdefault((record.kind, record.sha256), []).append(asset_id)
        return tuple(tuple(ids) for ids in groups.values() if len(ids) > 1)

    def missing_dependencies(self) -> tuple[tuple[str, str], ...]:
        """Return every (asset id, dependency id) pair whose dependency is absent."""
        missing: list[tuple[str, str]] = []
        for asset_id, record in self._records.items():
            for dependency in record.dependencies:
                if dependency not in self._records:
                    missing.append((asset_id, dependency))
        return tuple(sorted(missing))

    def stats(self) -> dict[str, object]:
        """Return total and per-kind counts in a stable order."""
        counts = {kind: 0 for kind in ASSET_KINDS}
        for record in self._records.values():
            counts[record.kind] += 1
        return {"total": len(self._records), "kinds": counts}

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe registry document sorted by asset id."""
        return {
            "schema": 1,
            "stats": self.stats(),
            "assets": [
                record.describe() for record in sorted(self._records.values(), key=lambda item: item.id)
            ],
        }


def _validate_id(asset_id: object) -> None:
    if not isinstance(asset_id, str):
        raise TypeError("asset id must be a string")
    if not asset_id.strip() or asset_id != asset_id.strip():
        raise ValueError("asset id must be non-blank with no surrounding whitespace")


def _validate_kind(kind: str) -> None:
    if kind not in ASSET_KINDS:
        raise ValueError(f"asset kind must be one of {', '.join(ASSET_KINDS)}")


def _validate_dependency(asset_id: str, dependency: object) -> None:
    if not isinstance(dependency, str):
        raise TypeError("dependency ids must be strings")
    if not dependency.strip() or dependency != dependency.strip():
        raise ValueError("dependency ids must be non-blank with no surrounding whitespace")
    if dependency == asset_id:
        raise ValueError("an asset cannot depend on itself")


def _dependencies(asset_id: str, dependencies: Iterable[str]) -> tuple[str, ...]:
    if isinstance(dependencies, str):
        raise TypeError("dependencies must be a collection of asset ids, not a string")
    cleaned: set[str] = set()
    for dependency in dependencies:
        _validate_dependency(asset_id, dependency)
        cleaned.add(dependency)
    return tuple(sorted(cleaned))


def _kind_of(payload: object) -> str:
    if isinstance(payload, MeshData):
        return "mesh"
    if isinstance(payload, Material):
        return "material"
    if isinstance(payload, TextureData):
        return "texture"
    raise TypeError("payload must be a MeshData, Material or TextureData")


def _digest(kind: str, payload: AssetPayload) -> str:
    if kind == "texture" and isinstance(payload, TextureData):
        return payload.sha256()
    if kind == "mesh" and isinstance(payload, MeshData):
        return _digest_mesh(payload)
    if kind == "material" and isinstance(payload, Material):
        return _digest_material(payload)
    raise TypeError(f"payload is a {_kind_of(payload)}, not a {kind}")


def _digest_mesh(mesh: MeshData) -> str:
    digest = hashlib.sha256()
    for group in (mesh.positions, mesh.normals, mesh.uvs, mesh.colors):
        digest.update(len(group).to_bytes(8, "little"))
        for item in group:
            digest.update(struct.pack(f"<{len(item)}d", *item))
    digest.update(len(mesh.indices).to_bytes(8, "little"))
    if mesh.indices:
        digest.update(struct.pack(f"<{len(mesh.indices)}i", *mesh.indices))
    return digest.hexdigest()


def _digest_material(material: Material) -> str:
    digest = hashlib.sha256()
    values = (*material.color, material.specular, material.shininess, material.checker_scale)
    digest.update(struct.pack(f"<{len(values)}d", *values))
    texture = material.texture if isinstance(material.texture, TextureData) else None
    digest.update(texture.sha256().encode("ascii") if texture is not None else b"")
    return digest.hexdigest()
