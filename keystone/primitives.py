"""Procedural primitives: cube, ground plane and UV sphere."""

from __future__ import annotations

import math

from keystone.geometry import MeshData

def _append_quad(
    positions: list,
    normals: list,
    uvs: list,
    indices: list,
    corners: tuple[tuple[float, float, float], ...],
    normal: tuple[float, float, float],
) -> None:
    base = len(positions)
    positions.extend(corners)
    normals.extend((normal,) * 4)
    uvs.extend(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))
    indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))


def cube(size: float = 1.0) -> MeshData:
    if size <= 0.0:
        raise ValueError("cube size must be positive")
    h = size / 2.0
    faces = (
        (((h, -h, h), (h, -h, -h), (h, h, -h), (h, h, h)), (1.0, 0.0, 0.0)),
        (((-h, -h, -h), (-h, -h, h), (-h, h, h), (-h, h, -h)), (-1.0, 0.0, 0.0)),
        (((-h, h, h), (h, h, h), (h, h, -h), (-h, h, -h)), (0.0, 1.0, 0.0)),
        (((-h, -h, -h), (h, -h, -h), (h, -h, h), (-h, -h, h)), (0.0, -1.0, 0.0)),
        (((-h, -h, h), (h, -h, h), (h, h, h), (-h, h, h)), (0.0, 0.0, 1.0)),
        (((h, -h, -h), (-h, -h, -h), (-h, h, -h), (h, h, -h)), (0.0, 0.0, -1.0)),
    )
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    indices: list[int] = []
    for corners, normal in faces:
        _append_quad(positions, normals, uvs, indices, corners, normal)
    return MeshData(tuple(positions), tuple(normals), tuple(uvs), tuple(indices))


def plane(size: float = 10.0) -> MeshData:
    if size <= 0.0:
        raise ValueError("plane size must be positive")
    h = size / 2.0
    positions = ((-h, 0.0, h), (h, 0.0, h), (h, 0.0, -h), (-h, 0.0, -h))
    normals = ((0.0, 1.0, 0.0),) * 4
    uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    return MeshData(positions, normals, uvs, (0, 1, 2, 0, 2, 3))


def sphere(radius: float = 1.0, segments: int = 32, rings: int = 16) -> MeshData:
    if radius <= 0.0:
        raise ValueError("sphere radius must be positive")
    if segments < 3 or rings < 2:
        raise ValueError("sphere needs at least 3 segments and 2 rings")
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    for ring in range(rings + 1):
        theta = math.pi * ring / rings
        sin_theta, cos_theta = math.sin(theta), math.cos(theta)
        for segment in range(segments + 1):
            phi = math.tau * segment / segments
            normal = (
                sin_theta * math.cos(phi),
                cos_theta,
                sin_theta * math.sin(phi),
            )
            positions.append((normal[0] * radius, normal[1] * radius, normal[2] * radius))
            normals.append(normal)
            uvs.append((segment / segments, ring / rings))
    indices: list[int] = []
    stride = segments + 1
    for ring in range(rings):
        for segment in range(segments):
            a = ring * stride + segment
            b = a + 1
            c = a + stride
            d = c + 1
            indices.extend((a, b, c, b, d, c))
    return MeshData(tuple(positions), tuple(normals), tuple(uvs), tuple(indices))
