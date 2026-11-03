"""Indexed triangle mesh data and surface material, independent of any GPU API."""

from __future__ import annotations

import math
from dataclasses import dataclass

from keystone.math3d import Vec3
from keystone.texture import TextureData

MAX_SKIN_INFLUENCES = 4
MAX_SKIN_BONES = 64


@dataclass(frozen=True, slots=True)
class Material:
    """Blinn-Phong surface parameters with PBR extensions used by the renderer."""

    color: Vec3 = Vec3(0.78, 0.78, 0.82)
    specular: float = 0.35
    shininess: float = 32.0
    checker_scale: float = 0.0
    texture: TextureData | None = None
    metallic: float = 0.0
    roughness: float = 0.7
    emissive: Vec3 = Vec3(0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if self.specular < 0.0:
            raise ValueError("specular must be non-negative")
        if self.shininess <= 0.0:
            raise ValueError("shininess must be positive")
        if self.checker_scale < 0.0:
            raise ValueError("checker_scale must be non-negative")
        if not 0.0 <= self.metallic <= 1.0:
            raise ValueError("metallic must be within [0, 1]")
        if not 0.0 <= self.roughness <= 1.0:
            raise ValueError("roughness must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class MeshData:
    """Immutable indexed triangle mesh with optional UVs and skinning."""

    positions: tuple[tuple[float, float, float], ...]
    normals: tuple[tuple[float, float, float], ...]
    uvs: tuple[tuple[float, float], ...] = ()
    indices: tuple[int, ...] = ()
    colors: tuple[tuple[float, float, float], ...] = ()
    joints: tuple[tuple[int, ...], ...] = ()
    weights: tuple[tuple[float, ...], ...] = ()
    skin_joints: tuple[str, ...] = ()
    skin_inverse_bind: tuple[tuple[float, ...], ...] = ()

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
        if self.joints or self.weights:
            if not (self.joints and self.weights):
                raise ValueError("skin joints and weights must appear together")
            if len(self.joints) != count or len(self.weights) != count:
                raise ValueError("skin joints and weights must match the vertex count")
            for vertex_joints, vertex_weights in zip(self.joints, self.weights):
                if not (1 <= len(vertex_joints) <= MAX_SKIN_INFLUENCES):
                    raise ValueError("each vertex needs 1 to 4 joint influences")
                if len(vertex_joints) != len(vertex_weights):
                    raise ValueError("joint and weight counts must match per vertex")
                if any(not isinstance(joint, int) or joint < 0 for joint in vertex_joints):
                    raise ValueError("skin joint indices must be non-negative integers")
                if any(weight < 0.0 for weight in vertex_weights):
                    raise ValueError("skin weights must be non-negative")
                if abs(sum(vertex_weights) - 1.0) > 1e-3:
                    raise ValueError("skin weights must sum to 1")
        if self.skin_joints or self.skin_inverse_bind:
            if not (self.joints and self.weights and self.skin_joints and self.skin_inverse_bind):
                raise ValueError("a skin palette needs joints, weights, joint names and inverse bind matrices together")
            if len(self.skin_joints) < 1 or len(self.skin_joints) > MAX_SKIN_BONES:
                raise ValueError("skin joint names must number 1 to 64")
            if any(not isinstance(name, str) or not name.strip() for name in self.skin_joints):
                raise ValueError("skin joint names must be non-blank strings")
            if len(set(self.skin_joints)) != len(self.skin_joints):
                raise ValueError("skin joint names must be unique")
            if len(self.skin_inverse_bind) != len(self.skin_joints):
                raise ValueError("inverse bind matrices must match the joint count")
            for matrix in self.skin_inverse_bind:
                if len(matrix) != 16 or any(not math.isfinite(value) for value in matrix):
                    raise ValueError("inverse bind matrices must hold 16 finite numbers")
            for vertex_joints in self.joints:
                if any(joint >= len(self.skin_joints) for joint in vertex_joints):
                    raise ValueError("skin joint index is out of range")

    @property
    def skinned(self) -> bool:
        """Whether this mesh carries a bound skin palette."""
        return bool(self.joints and self.weights and self.skin_joints and self.skin_inverse_bind)

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

    def interleaved_skinned(self) -> tuple[float, ...]:
        """Pack the base stream plus padded joints and weights for the GPU."""
        if not self.skinned:
            raise ValueError("mesh has no skinning influences")
        stream: list[float] = []
        for index, position in enumerate(self.positions):
            normal = self.normals[index]
            uv = self.uvs[index] if self.uvs else (0.0, 0.0)
            color = self.colors[index] if self.colors else (1.0, 1.0, 1.0)
            stream.extend((*position, *normal, *uv, *color))
            vertex_joints = self.joints[index]
            vertex_weights = self.weights[index]
            padded_joints = tuple(float(joint) for joint in vertex_joints) + (0.0,) * (MAX_SKIN_INFLUENCES - len(vertex_joints))
            padded_weights = tuple(vertex_weights) + (0.0,) * (MAX_SKIN_INFLUENCES - len(vertex_weights))
            stream.extend(padded_joints)
            stream.extend(padded_weights)
        return tuple(stream)
