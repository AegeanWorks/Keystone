"""Disk-backed asset sources, default loaders and hot-reload reporting."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from keystone.geometry import Material, MeshData
from keystone.obj_loader import load_obj
from keystone.prefab import Prefab
from keystone.texture import TextureData

ASSET_KINDS = ("mesh", "material", "texture", "prefab")
AssetPayload = MeshData | Material | TextureData | Prefab
AssetLoader = Callable[[Path], object]
Fingerprint = tuple[int, int]

LOADERS: dict[str, AssetLoader] = {
    "mesh": load_obj,
    "texture": TextureData.from_png,
    "prefab": Prefab.load,
}
SUFFIX_KINDS = {".obj": "mesh", ".png": "texture", ".kprefab": "prefab"}


@dataclass(frozen=True, slots=True)
class AssetSource:
    """One file-backed asset: where it came from, how to load it and its last stamp."""

    path: Path
    kind: str
    loader: AssetLoader
    fingerprint: Fingerprint
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise TypeError("source path must be a Path")
        if self.kind not in ASSET_KINDS:
            raise ValueError(f"asset kind must be one of {', '.join(ASSET_KINDS)}")
        if not callable(self.loader):
            raise TypeError("source loader must be callable")
        if len(self.fingerprint) != 2 or not all(isinstance(value, int) for value in self.fingerprint):
            raise TypeError("source fingerprint must be a (mtime_ns, size) pair")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("source error must be a string or None")


@dataclass(frozen=True, slots=True)
class ReloadReport:
    """Outcome of one synchronous registry refresh."""

    checked: int
    reloaded: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    failed: tuple[tuple[str, str], ...] = ()
    missing: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """True when every checked source loaded and none disappeared."""
        return not self.failed and not self.missing

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe report for logs and AI clients."""
        return {
            "checked": self.checked,
            "reloaded": list(self.reloaded),
            "unchanged": list(self.unchanged),
            "failed": [{"id": asset_id, "error": error} for asset_id, error in self.failed],
            "missing": list(self.missing),
            "ok": self.ok,
        }


def default_loader(kind: str) -> AssetLoader:
    """Return the built-in loader for a kind, or explain how to supply one."""
    if kind not in ASSET_KINDS:
        raise ValueError(f"asset kind must be one of {', '.join(ASSET_KINDS)}")
    loader = LOADERS.get(kind)
    if loader is None:
        raise ValueError(f"no default loader for {kind} assets; pass loader=...")
    return loader


def kind_from_suffix(path: str | Path) -> str:
    """Infer an asset kind from a .obj, .png or .kprefab path."""
    suffix = Path(path).suffix.lower()
    try:
        return SUFFIX_KINDS[suffix]
    except KeyError as exc:
        raise ValueError(
            f"cannot infer an asset kind from '{suffix or path}'; pass kind=..."
        ) from exc


def fingerprint(path: str | Path) -> Fingerprint | None:
    """Return (mtime_ns, size) for a readable path, or None when it is absent."""
    try:
        status = Path(path).stat()
    except OSError:
        return None
    return (status.st_mtime_ns, status.st_size)


def asset_kind(payload: object) -> str:
    """Return the registry kind of a payload object."""
    if isinstance(payload, MeshData):
        return "mesh"
    if isinstance(payload, Material):
        return "material"
    if isinstance(payload, TextureData):
        return "texture"
    if isinstance(payload, Prefab):
        return "prefab"
    raise TypeError("payload must be a MeshData, Material, TextureData or Prefab")


def load_asset(kind: str, path: str | Path, loader: AssetLoader | None = None) -> AssetPayload:
    """Load one source and prove the payload matches the declared kind."""
    if kind not in ASSET_KINDS:
        raise ValueError(f"asset kind must be one of {', '.join(ASSET_KINDS)}")
    selected = loader or default_loader(kind)
    payload = selected(Path(path))
    actual = asset_kind(payload)
    if actual != kind:
        raise TypeError(f"loader returned a {actual}, expected a {kind}")
    return payload
