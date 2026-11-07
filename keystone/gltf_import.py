"""Import glTF/GLB scenes into the prefab library and asset registry.

The engine's glTF loader already produces meshes, materials, textures and a
scene. This adapter registers those payloads under stable ids and saves the
scene as a reusable ``.kprefab`` entry so editor and AI clients can insert it.
"""

from __future__ import annotations

from pathlib import Path

from keystone.assets import AssetRegistry
from keystone.gltf import load_gltf
from keystone.prefab import Prefab
from keystone.prefab_library import PrefabLibrary, validate_library_name

__all__ = ["GLTF_SUFFIXES", "import_gltf_prefab", "is_gltf_asset"]

GLTF_SUFFIXES = (".gltf", ".glb")


def is_gltf_asset(path: str | Path) -> bool:
    """Return True for a glTF JSON or binary GLB path."""
    if not isinstance(path, (str, Path)):
        raise TypeError("glTF asset path must be a string or Path")
    return Path(path).suffix.lower() in GLTF_SUFFIXES


def import_gltf_prefab(
    path: str | Path,
    registry: AssetRegistry,
    library: PrefabLibrary,
    name: str | None = None,
) -> Prefab:
    """Import one glTF/GLB scene, register its assets and save a prefab."""
    if not isinstance(registry, AssetRegistry):
        raise TypeError("glTF import needs an AssetRegistry")
    if not isinstance(library, PrefabLibrary):
        raise TypeError("glTF import needs a PrefabLibrary")
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"glTF source does not exist: {source}")
    if not is_gltf_asset(source):
        raise ValueError("glTF import source must use .gltf or .glb")
    selected = validate_library_name(name or source.stem)
    imported = load_gltf(source)
    for index, texture in enumerate(imported.textures):
        registry.register(f"gltf.{selected}.texture.{index}", texture, replace=True)
    for index, material in enumerate(imported.materials):
        registry.register(f"gltf.{selected}.material.{index}", material, replace=True)
    for index, mesh in enumerate(imported.meshes):
        registry.register(f"gltf.{selected}.mesh.{index}", mesh, replace=True)
    prefab = Prefab.from_scene(imported.scene, name=selected)
    library.save(selected, prefab)
    return prefab
