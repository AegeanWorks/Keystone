"""glTF mesh and primitive decoding."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from keystone.geometry import MeshData
from keystone.gltf.io import read_accessor


def _as_vec3(value: Any) -> tuple[float, float, float]:
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return (float(value[0]), float(value[1]), float(value[2]))
    return (0.0, 0.0, 0.0)


def _compute_normals(
    positions: list[tuple[float, float, float]],
    indices: list[int],
) -> list[tuple[float, float, float]]:
    normals = [[0.0, 0.0, 0.0] for _ in positions]
    for i in range(0, len(indices) - 2, 3):
        a = indices[i]
        b = indices[i + 1]
        c = indices[i + 2]
        if a >= len(positions) or b >= len(positions) or c >= len(positions):
            continue
        ax, ay, az = positions[a]
        bx, by, bz = positions[b]
        cx, cy, cz = positions[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        for vertex in (a, b, c):
            normals[vertex][0] += nx
            normals[vertex][1] += ny
            normals[vertex][2] += nz
    result: list[tuple[float, float, float]] = []
    for normal in normals:
        length = math.sqrt(normal[0] ** 2 + normal[1] ** 2 + normal[2] ** 2)
        if length > 1e-12:
            result.append((normal[0] / length, normal[1] / length, normal[2] / length))
        else:
            result.append((0.0, 1.0, 0.0))
    return result


def load_meshes(
    document: Mapping[str, Any],
    buffers: list[bytes],
    buffer_views: list[Any],
    materials: list[Any],
) -> list[list[tuple[MeshData, int | None]]]:
    raw_meshes = document.get("meshes", [])
    if not isinstance(raw_meshes, list):
        raise TypeError("glTF meshes must be a list")
    meshes: list[list[tuple[MeshData, int | None]]] = []
    for mesh_index, raw in enumerate(raw_meshes):
        if not isinstance(raw, Mapping):
            raise TypeError(f"glTF mesh {mesh_index} must be an object")
        primitives = raw.get("primitives", [])
        if not isinstance(primitives, list) or not primitives:
            raise TypeError(f"glTF mesh {mesh_index} has no primitives")
        mesh_primitives: list[tuple[MeshData, int | None]] = []
        for primitive in primitives:
            if not isinstance(primitive, Mapping):
                raise TypeError(f"glTF mesh {mesh_index} primitive must be an object")
            attributes = primitive.get("attributes", {})
            if not isinstance(attributes, Mapping):
                raise TypeError(f"glTF mesh {mesh_index} attributes must be an object")
            if "POSITION" not in attributes:
                raise ValueError(f"glTF mesh {mesh_index} primitive is missing POSITION")
            positions_raw = read_accessor(
                _accessor(document, int(attributes["POSITION"])),
                buffer_views,
                buffers,
            )
            positions = [_as_vec3(value) for value in positions_raw]
            if len(positions) < 3:
                raise ValueError(f"glTF mesh {mesh_index} needs at least three vertices")
            normals_raw = None
            if "NORMAL" in attributes:
                normals_raw = read_accessor(
                    _accessor(document, int(attributes["NORMAL"])),
                    buffer_views,
                    buffers,
                )
            if normals_raw is None:
                normals = _compute_normals(positions, list(range(len(positions))))
            else:
                normals = [_as_vec3(value) for value in normals_raw]
            if len(normals) != len(positions):
                raise ValueError(f"glTF mesh {mesh_index} normal count does not match position count")
            uvs_raw = None
            if "TEXCOORD_0" in attributes:
                uvs_raw = read_accessor(
                    _accessor(document, int(attributes["TEXCOORD_0"])),
                    buffer_views,
                    buffers,
                )
            uvs = []
            if uvs_raw is not None:
                for value in uvs_raw:
                    if isinstance(value, (tuple, list)) and len(value) >= 2:
                        uvs.append((float(value[0]), float(value[1])))
                    else:
                        uvs.append((0.0, 0.0))
            if uvs and len(uvs) != len(positions):
                raise ValueError(f"glTF mesh {mesh_index} UV count does not match position count")
            if not uvs:
                uvs = [(0.0, 0.0)] * len(positions)
            colors: list[tuple[float, float, float]] = []
            if "COLOR_0" in attributes:
                colors_raw = read_accessor(
                    _accessor(document, int(attributes["COLOR_0"])),
                    buffer_views,
                    buffers,
                )
                for value in colors_raw:
                    if isinstance(value, (tuple, list)) and len(value) >= 3:
                        colors.append((float(value[0]), float(value[1]), float(value[2])))
                    else:
                        colors.append((1.0, 1.0, 1.0))
                if len(colors) != len(positions):
                    raise ValueError(f"glTF mesh {mesh_index} color count does not match position count")
            indices_raw = None
            if "indices" in primitive:
                indices_raw = read_accessor(
                    _accessor(document, int(primitive["indices"])),
                    buffer_views,
                    buffers,
                )
            if indices_raw is None:
                indices = list(range(len(positions)))
            else:
                indices = [int(value) for value in indices_raw]
            if not indices or len(indices) % 3 != 0:
                raise ValueError(f"glTF mesh {mesh_index} indices must contain complete triangles")
            if any(index < 0 or index >= len(positions) for index in indices):
                raise ValueError(f"glTF mesh {mesh_index} has an out-of-range index")
            material_index = primitive.get("material")
            if material_index is not None:
                material_index = int(material_index)
            mesh = MeshData(
                positions=tuple(positions),
                normals=tuple(normals),
                uvs=tuple(uvs),
                indices=tuple(indices),
                colors=tuple(colors),
            )
            mesh_primitives.append((mesh, material_index))
        meshes.append(mesh_primitives)
    return meshes


def _accessor(document: Mapping[str, Any], index: int) -> Mapping[str, Any]:
    accessors = document.get("accessors", [])
    if not isinstance(accessors, list) or index < 0 or index >= len(accessors):
        raise TypeError("glTF accessor index is out of range")
    accessor = accessors[index]
    if not isinstance(accessor, Mapping):
        raise TypeError("glTF accessor must be an object")
    return accessor