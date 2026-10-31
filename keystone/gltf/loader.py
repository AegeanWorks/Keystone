"""Top-level glTF import orchestration."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from keystone.geometry import Material, MeshData
from keystone.gltf.io import load_buffers, read_source
from keystone.gltf.materials import load_materials
from keystone.gltf.meshes import load_meshes
from keystone.gltf.scene import build_scene
from keystone.gltf.textures import load_textures
from keystone.scene import Scene
from keystone.texture import TextureData


@dataclass(frozen=True, slots=True)
class GltfImport:
    """The result of importing one glTF document."""

    scene: Scene
    meshes: tuple[MeshData, ...]
    materials: tuple[Material, ...]
    textures: tuple[TextureData, ...]
    node_count: int


def load_gltf(source: object, registry: Any = None) -> GltfImport:
    """Load a glTF 2.0 document from a path, JSON text or bytes."""
    text, base_dir = read_source(source)
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid glTF JSON: {exc}") from exc
    if not isinstance(document, Mapping):
        raise TypeError("glTF document must be a JSON object")
    asset = document.get("asset", {})
    version = ""
    if isinstance(asset, Mapping):
        version = str(asset.get("version", ""))
    if not version.startswith("2"):
        raise ValueError("glTF asset version must be 2.x")

    buffers = load_buffers(document, base_dir)
    buffer_views = document.get("bufferViews", [])
    if not isinstance(buffer_views, list):
        raise TypeError("glTF bufferViews must be a list")
    textures = load_textures(document, buffers, buffer_views, base_dir)
    materials = load_materials(document, textures)
    meshes = load_meshes(document, buffers, buffer_views, materials)
    scene = build_scene(document, meshes, materials)

    all_meshes: list[MeshData] = []
    for mesh_primitives in meshes:
        for mesh, _ in mesh_primitives:
            all_meshes.append(mesh)

    result = GltfImport(
        scene=scene,
        meshes=tuple(all_meshes),
        materials=tuple(materials),
        textures=tuple(textures),
        node_count=len(document.get("nodes", [])) if isinstance(document.get("nodes", []), list) else 0,
    )

    if registry is not None:
        for index, texture in enumerate(textures):
            registry.register(f"gltf.texture.{index}", texture, replace=True)
        for index, material in enumerate(materials):
            registry.register(f"gltf.material.{index}", material, replace=True)
        for index, mesh in enumerate(all_meshes):
            registry.register(f"gltf.mesh.{index}", mesh, replace=True)

    return result