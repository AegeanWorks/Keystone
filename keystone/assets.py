"""Game-agnostic asset registry with stable ids, content hashes and dependencies."""

from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from keystone.asset_io import (
    ASSET_KINDS,
    AssetLoader,
    AssetPayload,
    AssetSource,
    ReloadReport,
    asset_kind,
    default_loader,
    fingerprint,
    kind_from_suffix,
    load_asset,
)
from keystone.geometry import Material, MeshData
from keystone.prefab import Prefab
from keystone.texture import TextureData


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
        actual = asset_kind(self.payload)
        if actual != self.kind:
            raise TypeError(f"payload is a {actual}, not a {self.kind}")
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
    """Caller-owned registry for meshes, materials, textures and prefabs.

    The registry is intentionally synchronous: it starts no thread and watches no files. A game
    that wants hot reload calls ``refresh()`` from its own loop. Registering or replacing one asset
    is a single dictionary assignment, so a reader sees either the old or the new record.
    """

    def __init__(self) -> None:
        self._records: dict[str, AssetRecord] = {}
        self._sources: dict[str, AssetSource] = {}

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
        inferred = asset_kind(payload)
        if kind is not None:
            _validate_kind(kind)
            if kind != inferred:
                raise TypeError(f"payload is a {inferred}, not a {kind}")
        kind = inferred if kind is None else kind
        if asset_id in self._records and not replace:
            raise ValueError(
                f"asset {asset_id!r} is already registered; pass replace=True to replace it"
            )
        resolved_dependencies = _dependencies(asset_id, dependencies)
        if isinstance(payload, Prefab):
            resolved_dependencies = _dependencies(
                asset_id, (*resolved_dependencies, *payload.asset_ids(self))
            )
        pending = list(resolved_dependencies)
        seen: set[str] = set()
        while pending:
            dependency = pending.pop()
            if dependency == asset_id:
                raise ValueError(f"asset {asset_id!r} has a dependency cycle")
            if dependency in seen:
                continue
            seen.add(dependency)
            existing = self._records.get(dependency)
            if existing is not None:
                pending.extend(existing.dependencies)
        record = AssetRecord(
            id=asset_id,
            kind=kind,
            payload=payload,
            sha256=_digest(kind, payload, self),
            source=Path(source) if source is not None else None,
            dependencies=resolved_dependencies,
        )
        self._records[asset_id] = record
        return record

    def register_file(
        self,
        asset_id: str,
        path: str | Path,
        *,
        kind: str | None = None,
        loader: AssetLoader | None = None,
        dependencies: Iterable[str] = (),
        component_types: Mapping[str, type] | None = None,
        replace: bool = False,
    ) -> AssetRecord:
        """Load a .obj, .png or .kprefab file and bind it for hot reload."""
        _validate_id(asset_id)
        if asset_id in self._records and not replace:
            raise ValueError(
                f"asset {asset_id!r} is already registered; pass replace=True to replace it"
            )
        source_path = Path(path)
        if kind is None:
            kind = kind_from_suffix(source_path)
        else:
            _validate_kind(kind)
        if component_types is not None:
            if kind != "prefab":
                raise ValueError("component_types only applies to prefab assets")
            if loader is not None:
                raise ValueError("component_types cannot be combined with a custom loader")
        mark = fingerprint(source_path)
        if mark is None:
            raise FileNotFoundError(f"asset source {source_path} does not exist")
        selected = loader or default_loader(kind)
        if kind == "prefab" and loader is None:
            types = None if component_types is None else dict(component_types)
            selected = lambda source: Prefab.load(
                source, registry=self, component_types=types
            )
        payload = load_asset(kind, source_path, selected)
        record = self.register(
            asset_id,
            payload,
            kind=kind,
            source=source_path,
            dependencies=dependencies,
            replace=replace,
        )
        self._sources[asset_id] = AssetSource(source_path, kind, selected, mark)
        return record

    def refresh(self) -> ReloadReport:
        """Re-read every changed source and report reloaded, unchanged, failed and missing ids."""
        reloaded: list[str] = []
        unchanged: list[str] = []
        failed: list[tuple[str, str]] = []
        missing: list[str] = []
        for asset_id in sorted(self._sources):
            source = self._sources[asset_id]
            mark = fingerprint(source.path)
            if mark is None:
                missing.append(asset_id)
                continue
            if mark == source.fingerprint:
                if source.error is not None:
                    failed.append((asset_id, source.error))
                else:
                    unchanged.append(asset_id)
                continue
            try:
                payload = load_asset(source.kind, source.path, source.loader)
            except Exception as exc:  # noqa: BLE001 - a loader failure is reported, never hidden
                message = f"{type(exc).__name__}: {exc}"
                failed.append((asset_id, message))
                self._sources[asset_id] = replace(source, fingerprint=mark, error=message)
                continue
            old = self._records[asset_id]
            record = self.register(
                asset_id,
                payload,
                kind=source.kind,
                source=source.path,
                dependencies=old.dependencies,
                replace=True,
            )
            self._sources[asset_id] = replace(source, fingerprint=mark, error=None)
            if record.sha256 == old.sha256:
                unchanged.append(asset_id)
            else:
                reloaded.append(asset_id)
        return ReloadReport(
            checked=len(self._sources),
            reloaded=tuple(reloaded),
            unchanged=tuple(unchanged),
            failed=tuple(failed),
            missing=tuple(missing),
        )

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
        self._sources.pop(asset_id, None)
        return record

    def clear(self) -> None:
        self._records.clear()
        self._sources.clear()

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
            "sources": [
                {
                    "id": asset_id,
                    "path": source.path.as_posix(),
                    "kind": source.kind,
                    "fingerprint": list(source.fingerprint),
                    "error": source.error,
                }
                for asset_id, source in sorted(self._sources.items())
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


def _digest(kind: str, payload: AssetPayload, registry: AssetRegistry | None = None) -> str:
    if kind == "texture" and isinstance(payload, TextureData):
        digest = hashlib.sha256()
        digest.update(struct.pack("<2q", payload.width, payload.height))
        digest.update(payload.sha256().encode("ascii"))
        return digest.hexdigest()
    if kind == "mesh" and isinstance(payload, MeshData):
        return _digest_mesh(payload)
    if kind == "material" and isinstance(payload, Material):
        return _digest_material(payload)
    if kind == "prefab" and isinstance(payload, Prefab):
        return _digest_prefab(payload, registry)
    raise TypeError(f"payload is a {asset_kind(payload)}, not a {kind}")


def _digest_prefab(prefab: Prefab, registry: AssetRegistry | None) -> str:
    document = prefab.to_dict(registry)
    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _digest_mesh(mesh: MeshData) -> str:
    digest = hashlib.sha256()
    for group in (mesh.positions, mesh.normals, mesh.uvs, mesh.colors):
        digest.update(len(group).to_bytes(8, "little"))
        for item in group:
            digest.update(struct.pack(f"<{len(item)}d", *item))
    for group in (mesh.joints,):
        digest.update(len(group).to_bytes(8, "little"))
        for item in group:
            digest.update(len(item).to_bytes(8, "little"))
            digest.update(struct.pack(f"<{len(item)}i", *item))
    for group in (mesh.weights, mesh.skin_inverse_bind):
        digest.update(len(group).to_bytes(8, "little"))
        for item in group:
            digest.update(len(item).to_bytes(8, "little"))
            digest.update(struct.pack(f"<{len(item)}d", *item))
    digest.update(len(mesh.skin_joints).to_bytes(8, "little"))
    for name in mesh.skin_joints:
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little"))
        digest.update(encoded)
    digest.update(len(mesh.indices).to_bytes(8, "little"))
    if mesh.indices:
        digest.update(struct.pack(f"<{len(mesh.indices)}i", *mesh.indices))
    return digest.hexdigest()


def _digest_material(material: Material) -> str:
    digest = hashlib.sha256()
    values = (
        *material.color,
        material.specular,
        material.shininess,
        material.checker_scale,
        material.metallic,
        material.roughness,
        *material.emissive,
    )
    digest.update(struct.pack(f"<{len(values)}d", *values))
    texture = material.texture if isinstance(material.texture, TextureData) else None
    digest.update(texture.sha256().encode("ascii") if texture is not None else b"")
    return digest.hexdigest()
