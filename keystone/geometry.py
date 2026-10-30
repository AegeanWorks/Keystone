"""Indexed triangle mesh data and surface material, independent of any GPU API."""

from __future__ import annotations

from dataclasses import dataclass

from keystone.math3d import Vec3
from keystone.texture import TextureData


@dataclass(frozen=True, slots=True)
class Material:
    """Blinn-Phong surface parameters used by the renderer."""

    color: Vec3 = Vec3(0.78, 0.78, 0.82)
    specular: float = 0.35
    shininess: float = 32.0
    checker_scale: float = 0.0
    texture: TextureData | None = None

    def __post_init__(self) -> None:
        if self.specular < 0.0:
            raise ValueError("specular must be non-negative")
        if self.shininess <= 0.0:
            raise ValueError("shininess must be positive")
        if self.checker_scale < 0.0:
            raise ValueError("checker_scale must be non-negative")


@dataclass(frozen=True, slots=True)
class MeshData:
    """Immutable indexed triangle mesh with optional UVs."""

    positions: tuple[tuple[float, float, float], ...]
    normals: tuple[tuple[float, float, float], ...]
    uvs: tuple[tuple[float, float], ...] = ()
    indices: tuple[int, ...] = ()
    colors: tuple[tuple[float, float, float], ...] = ()

    def __post_init__(self) -> None:
        count = len(self.positions)
        if count < 3:
            raise ValueError("a mesh needs at least three vertices")
        if len(self.normals) != count:
            raise ValueError("every vertex needs exactly one normal")
        if self.uvs and len(self.uvs) != count:
            raise ValueError("UVs, when present, must match the vertex count")
        if self.colors and len(self.colors) != count:
            raise ValueError("vertex colors, when present, must match the vertex count")
        if not self.indices or len(self.indices) % 3 != 0:
            raise ValueError("indices must contain complete triangles")
        if any(index < 0 or index >= count for index in self.indices):
            raise ValueError("an index points outside the vertex array")

    def vertex_count(self) -> int:
        return len(self.positions)

    def triangle_count(self) -> int:
        return len(self.indices) // 3

    def bounds(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        xs, ys, zs = zip(*self.positions)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def interleaved(self) -> tuple[float, ...]:
        """Pack position, normal and UV into one vertex stream for the GPU."""
        stream: list[float] = []
        for index, position in enumerate(self.positions):
            normal = self.normals[index]
            uv = self.uvs[index] if self.uvs else (0.0, 0.0)
            color = self.colors[index] if self.colors else (1.0, 1.0, 1.0)
            stream.extend((*position, *normal, *uv, *color))
        return tuple(stream)
