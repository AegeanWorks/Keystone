"""Streaming Wavefront OBJ loader producing indexed triangle meshes."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from keystone.geometry import MeshData
from keystone.math3d import Vec3

Corner = tuple[int, int | None, int | None]


def load_obj(path: str | Path) -> MeshData:
    """Read an OBJ file line by line so file size is never loaded whole."""
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        return _parse_lines(handle)


def parse_obj(text: str) -> MeshData:
    """Parse OBJ text already in memory, mainly for tests and embedded assets."""
    return _parse_lines(text.splitlines())


def _resolve_index(raw: str, count: int, kind: str, number: int, line: str) -> int:
    if not raw:
        raise ValueError(f"OBJ line {number}: missing {kind} index in face '{line}'")
    index = int(raw)
    if index == 0:
        raise ValueError(f"OBJ line {number}: {kind} index 0 is invalid")
    if index < 0:
        index = count + index + 1
    if not 1 <= index <= count:
        raise ValueError(
            f"OBJ line {number}: {kind} index {raw} is outside the {count} declared {kind} entries"
        )
    return index - 1


def _corner(token: str, number: int, line: str, vertices: int, uvs: int, normals: int) -> Corner:
    parts = token.split("/")
    vertex = _resolve_index(parts[0], vertices, "vertex", number, line)
    uv = _resolve_index(parts[1], uvs, "texture", number, line) if len(parts) > 1 and parts[1] else None
    normal = _resolve_index(parts[2], normals, "normal", number, line) if len(parts) > 2 and parts[2] else None
    return vertex, uv, normal


def _parse_lines(lines: Iterable[str]) -> MeshData:
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    faces: list[list[Corner]] = []
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        kind = parts[0]
        try:
            if kind == "v":
                values = tuple(float(value) for value in parts[1:4])
                if len(values) != 3:
                    raise ValueError("vertex needs three coordinates")
                positions.append(values)
            elif kind == "vn":
                values = tuple(float(value) for value in parts[1:4])
                if len(values) != 3:
                    raise ValueError("normal needs three coordinates")
                normals.append(values)
            elif kind == "vt":
                uvs.append((float(parts[1]), float(parts[2])))
            elif kind == "f":
                corners = [
                    _corner(token, number, line, len(positions), len(uvs), len(normals))
                    for token in parts[1:]
                ]
                if len(corners) < 3:
                    raise ValueError("a face needs at least three corners")
                faces.append(corners)
        except (ValueError, IndexError) as exc:
            if str(exc).startswith("OBJ line"):
                raise
            raise ValueError(f"OBJ line {number}: {exc}") from exc
    if not faces:
        raise ValueError("OBJ contains no faces")
    return _build_mesh(positions, normals, uvs, faces)


def _build_mesh(
    positions: list[tuple[float, float, float]],
    normals: list[tuple[float, float, float]],
    uvs: list[tuple[float, float]],
    faces: list[list[Corner]],
) -> MeshData:
    index_map: dict[tuple, int] = {}
    out_positions: list[tuple[float, float, float]] = []
    out_normals: list[tuple[float, float, float]] = []
    out_uvs: list[tuple[float, float]] = []
    out_indices: list[int] = []
    flat_sums: dict[tuple, Vec3] = {}
    for face_number, face in enumerate(faces):
        for offset in range(1, len(face) - 1):
            triangle = (face[0], face[offset], face[offset + 1])
            a = Vec3(*positions[triangle[0][0]])
            b = Vec3(*positions[triangle[1][0]])
            c = Vec3(*positions[triangle[2][0]])
            face_normal = (b - a).cross(c - a).normalized()
            for vertex, uv, normal in triangle:
                key = (vertex, uv, normal) if normal is not None else (vertex, uv, None, face_number)
                if key not in index_map:
                    index_map[key] = len(out_positions)
                    out_positions.append(positions[vertex])
                    out_normals.append(normals[normal] if normal is not None else (0.0, 0.0, 0.0))
                    out_uvs.append(uvs[uv] if uv is not None else (0.0, 0.0))
                    if normal is None:
                        flat_sums[key] = Vec3()
                if normal is None:
                    flat_sums[key] = flat_sums[key] + face_normal
                out_indices.append(index_map[key])
    for key, index in index_map.items():
        if key[2] is None:
            normal = flat_sums[key].normalized()
            out_normals[index] = (
                (normal.x, normal.y, normal.z) if normal.length_squared() > 1e-12 else (0.0, 1.0, 0.0)
            )
    return MeshData(tuple(out_positions), tuple(out_normals), tuple(out_uvs), tuple(out_indices))
