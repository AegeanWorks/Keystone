"""Content digests for mesh and material payloads.

The asset registry, static batch planner and instancing planner all need to
tell whether two payloads hold the same content. Object identity is not that
answer: two separate loads of one OBJ produce equal payloads in different
Python objects, and they should share one render group.

Digests are SHA-256 over the same field stream the registry has always used,
so a registered asset and an unregistered copy of it agree. Payloads are
immutable, so results are cached by object identity. The cache keeps a strong
reference to each key, which prevents an id from being reused while its entry
is live, and it is bounded so a scene larger than the bound recomputes the
overflow instead of growing without limit.
"""

from __future__ import annotations

import hashlib
import struct
from collections import OrderedDict
from collections.abc import Callable
from typing import TypeVar

from keystone.geometry import Material, MeshData
from keystone.texture import TextureData

__all__ = ["DIGEST_CACHE_LIMIT", "material_digest", "mesh_digest"]

DIGEST_CACHE_LIMIT = 1024

_Payload = TypeVar("_Payload")

_cache: OrderedDict[int, tuple[object, str]] = OrderedDict()


def _cached(payload: _Payload, compute: Callable[[_Payload], str]) -> str:
    key = id(payload)
    entry = _cache.get(key)
    if entry is not None and entry[0] is payload:
        _cache.move_to_end(key)
        return entry[1]
    digest = compute(payload)
    _cache[key] = (payload, digest)
    _cache.move_to_end(key)
    while len(_cache) > DIGEST_CACHE_LIMIT:
        _cache.popitem(last=False)
    return digest


def mesh_digest(mesh: MeshData) -> str:
    """Return the stable SHA-256 content digest of one mesh payload."""
    if not isinstance(mesh, MeshData):
        raise TypeError("mesh_digest needs a MeshData")
    return _cached(mesh, _hash_mesh)


def material_digest(material: Material) -> str:
    """Return the stable SHA-256 content digest of one material payload."""
    if not isinstance(material, Material):
        raise TypeError("material_digest needs a Material")
    return _cached(material, _hash_material)


def _hash_mesh(mesh: MeshData) -> str:
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


def _hash_material(material: Material) -> str:
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
