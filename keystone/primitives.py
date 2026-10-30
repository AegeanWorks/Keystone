"""Procedural primitives: cube, plane, cone, cylinder and UV sphere."""

from __future__ import annotations

import math

from keystone.geometry import MeshData
from keystone.math3d import Vec3


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


def cone(radius: float = 0.5, height: float = 1.0, segments: int = 16) -> MeshData:
    if radius <= 0.0 or height <= 0.0:
        raise ValueError("cone radius and height must be positive")
    if segments < 3:
        raise ValueError("cone needs at least 3 segments")
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    indices: list[int] = []
    base_y, apex_y = -height / 2.0, height / 2.0
    apex = (0.0, apex_y, 0.0)
    for index in range(segments):
        a0 = math.tau * index / segments
        a1 = math.tau * (index + 1) / segments
        p0 = (math.cos(a0) * radius, base_y, math.sin(a0) * radius)
        p1 = (math.cos(a1) * radius, base_y, math.sin(a1) * radius)
        normal = (Vec3(*p1) - Vec3(*p0)).cross(Vec3(*apex) - Vec3(*p0)).normalized()
        base = len(positions)
        positions.extend((p0, p1, apex))
        normals.extend(((normal.x, normal.y, normal.z),) * 3)
        uvs.extend(((index / segments, 0.0), ((index + 1) / segments, 0.0), (0.5, 1.0)))
        indices.extend((base, base + 1, base + 2))
    center = (0.0, base_y, 0.0)
    for index in range(segments):
        a0 = math.tau * index / segments
        a1 = math.tau * (index + 1) / segments
        p0 = (math.cos(a0) * radius, base_y, math.sin(a0) * radius)
        p1 = (math.cos(a1) * radius, base_y, math.sin(a1) * radius)
        base = len(positions)
        positions.extend((p0, center, p1))
        normals.extend(((0.0, -1.0, 0.0),) * 3)
        uvs.extend(((0.0, 0.0), (0.5, 0.5), (1.0, 0.0)))
        indices.extend((base, base + 1, base + 2))
    return MeshData(tuple(positions), tuple(normals), tuple(uvs), tuple(indices))


def cylinder(radius: float = 0.5, height: float = 1.0, segments: int = 16) -> MeshData:
    if radius <= 0.0 or height <= 0.0:
        raise ValueError("cylinder radius and height must be positive")
    if segments < 3:
        raise ValueError("cylinder needs at least 3 segments")
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    indices: list[int] = []
    bottom, top = -height / 2.0, height / 2.0
    for index in range(segments):
        a0 = math.tau * index / segments
        a1 = math.tau * (index + 1) / segments
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        base = len(positions)
        positions.extend(
            (
                (c0 * radius, bottom, s0 * radius),
                (c0 * radius, top, s0 * radius),
                (c1 * radius, top, s1 * radius),
                (c1 * radius, bottom, s1 * radius),
            )
        )
        normals.extend(((c0, 0.0, s0), (c0, 0.0, s0), (c1, 0.0, s1), (c1, 0.0, s1)))
        uvs.extend(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)))
        indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))
    for y, sign in ((top, 1.0), (bottom, -1.0)):
        center_index = len(positions)
        positions.append((0.0, y, 0.0))
        normals.append((0.0, sign, 0.0))
        uvs.append((0.5, 0.5))
        ring: list[int] = []
        for index in range(segments):
            angle = math.tau * index / segments
            ring.append(len(positions))
            positions.append((math.cos(angle) * radius, y, math.sin(angle) * radius))
            normals.append((0.0, sign, 0.0))
            uvs.append((0.5 + 0.5 * math.cos(angle), 0.5 + 0.5 * math.sin(angle)))
        for index in range(segments):
            a, b = ring[index], ring[(index + 1) % segments]
            if sign > 0.0:
                indices.extend((center_index, b, a))
            else:
                indices.extend((center_index, a, b))
    return MeshData(tuple(positions), tuple(normals), tuple(uvs), tuple(indices))


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
