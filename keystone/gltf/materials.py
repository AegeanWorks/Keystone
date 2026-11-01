"""glTF material conversion."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from keystone.geometry import Material
from keystone.math3d import Vec3


def load_materials(document: Mapping[str, Any], textures: list[Any]) -> list[Material]:
    raw_materials = document.get("materials", [])
    if not isinstance(raw_materials, list):
        raise TypeError("glTF materials must be a list")
    materials: list[Material] = []
    for index, raw in enumerate(raw_materials):
        if not isinstance(raw, Mapping):
            raise TypeError(f"glTF material {index} must be an object")
        pbr = raw.get("pbrMetallicRoughness", {})
        if not isinstance(pbr, Mapping):
            pbr = {}
        base_color = pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])
        if not (isinstance(base_color, (list, tuple)) and len(base_color) >= 3):
            base_color = [1.0, 1.0, 1.0, 1.0]
        color = Vec3(float(base_color[0]), float(base_color[1]), float(base_color[2]))
        roughness = float(pbr.get("roughnessFactor", 1.0))
        roughness = min(1.0, max(0.0, roughness))
        specular = 1.0 - roughness
        shininess = max(1.0, (1.0 - roughness) * 128.0)
        texture = None
        base_texture = pbr.get("baseColorTexture")
        if isinstance(base_texture, Mapping) and "index" in base_texture:
            texture_index = int(base_texture["index"])
            if texture_index < 0 or texture_index >= len(textures):
                raise ValueError(
                    f"glTF material {index} references unknown texture {texture_index}"
                )
            texture = textures[texture_index]
        materials.append(
            Material(
                color=color,
                specular=specular,
                shininess=shininess,
                checker_scale=0.0,
                texture=texture,
            )
        )
    return materials
