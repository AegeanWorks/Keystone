"""glTF node, transform and scene construction."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from keystone.geometry import Material, MeshData
from keystone.math3d import Quat, Vec3
from keystone.scene import Node, Scene, Transform


def _matrix_to_transform(matrix: list[Any]) -> Transform:
    if not (isinstance(matrix, (list, tuple)) and len(matrix) == 16):
        raise ValueError("glTF node matrix must contain 16 numbers")
    values = [float(value) for value in matrix]
    tx, ty, tz = values[12], values[13], values[14]
    sx = math.sqrt(values[0] ** 2 + values[1] ** 2 + values[2] ** 2)
    sy = math.sqrt(values[4] ** 2 + values[5] ** 2 + values[6] ** 2)
    sz = math.sqrt(values[8] ** 2 + values[9] ** 2 + values[10] ** 2)
    if sx < 1e-12:
        sx = 1.0
    if sy < 1e-12:
        sy = 1.0
    if sz < 1e-12:
        sz = 1.0
    r00 = values[0] / sx
    r01 = values[4] / sy
    r02 = values[8] / sz
    r10 = values[1] / sx
    r11 = values[5] / sy
    r12 = values[9] / sz
    r20 = values[2] / sx
    r21 = values[6] / sy
    r22 = values[10] / sz
    trace = r00 + r11 + r22
    if trace > 0.0:
        s = 0.5 / math.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (r21 - r12) * s
        y = (r02 - r20) * s
        z = (r10 - r01) * s
    elif r00 > r11 and r00 > r22:
        s = 2.0 * math.sqrt(1.0 + r00 - r11 - r22)
        w = (r21 - r12) / s
        x = 0.25 * s
        y = (r01 + r10) / s
        z = (r02 + r20) / s
    elif r11 > r22:
        s = 2.0 * math.sqrt(1.0 + r11 - r00 - r22)
        w = (r02 - r20) / s
        x = (r01 + r10) / s
        y = 0.25 * s
        z = (r12 + r21) / s
    else:
        s = 2.0 * math.sqrt(1.0 + r22 - r00 - r11)
        w = (r10 - r01) / s
        x = (r02 + r20) / s
        y = (r12 + r21) / s
        z = 0.25 * s
    rotation = Quat(w, x, y, z).normalized()
    return Transform(position=Vec3(tx, ty, tz), rotation=rotation, scale=Vec3(sx, sy, sz))


def _node_transform(raw: Mapping[str, Any]) -> Transform:
    if "matrix" in raw:
        return _matrix_to_transform(raw["matrix"])
    translation = raw.get("translation", [0.0, 0.0, 0.0])
    rotation = raw.get("rotation", [0.0, 0.0, 0.0, 1.0])
    scale = raw.get("scale", [1.0, 1.0, 1.0])
    if not (isinstance(translation, (list, tuple)) and len(translation) == 3):
        raise ValueError("glTF node translation must contain three numbers")
    if not (isinstance(rotation, (list, tuple)) and len(rotation) == 4):
        raise ValueError("glTF node rotation must contain four numbers")
    if not (isinstance(scale, (list, tuple)) and len(scale) == 3):
        raise ValueError("glTF node scale must contain three numbers")
    return Transform(
        position=Vec3(float(translation[0]), float(translation[1]), float(translation[2])),
        rotation=Quat(float(rotation[3]), float(rotation[0]), float(rotation[1]), float(rotation[2])),
        scale=Vec3(float(scale[0]), float(scale[1]), float(scale[2])),
    )


def build_scene(
    document: Mapping[str, Any],
    meshes: list[list[tuple[MeshData, int | None]]],
    materials: list[Material],
) -> Scene:
    raw_nodes = document.get("nodes", [])
    if raw_nodes and not isinstance(raw_nodes, list):
        raise TypeError("glTF nodes must be a list")
    raw_nodes = raw_nodes or []
    built: dict[int, Node] = {}
    visiting: set[int] = set()

    def build(index: int) -> Node:
        if index in built:
            return built[index]
        if index in visiting:
            raise ValueError("glTF node hierarchy contains a cycle")
        if index < 0 or index >= len(raw_nodes):
            raise ValueError("glTF node index is out of range")
        visiting.add(index)
        raw = raw_nodes[index]
        if not isinstance(raw, Mapping):
            raise TypeError("glTF node must be an object")
        name = str(raw.get("name", f"node-{index}"))
        node = Node(name, id=f"node-{index}")
        node.transform = _node_transform(raw)
        mesh_index = raw.get("mesh")
        if mesh_index is not None:
            mesh_index = int(mesh_index)
            if mesh_index < 0 or mesh_index >= len(meshes):
                raise ValueError("glTF node references an unknown mesh")
            primitives = meshes[mesh_index]
            if primitives:
                first_mesh, first_material = primitives[0]
                node.mesh = first_mesh
                if first_material is not None and 0 <= first_material < len(materials):
                    node.material = materials[first_material]
                elif first_material is None:
                    node.material = Material()
                for offset, (primitive_mesh, primitive_material) in enumerate(primitives[1:], start=1):
                    child = Node(
                        f"{name}-primitive-{offset}",
                        id=f"node-{index}-primitive-{offset}",
                        mesh=primitive_mesh,
                    )
                    if primitive_material is not None and 0 <= primitive_material < len(materials):
                        child.material = materials[primitive_material]
                    node.add_child(child)
        try:
            for child_index in raw.get("children", []):
                node.add_child(build(int(child_index)))
        finally:
            visiting.discard(index)
        built[index] = node
        return node

    scene_index = int(document.get("scene", 0)) if document.get("scenes") else 0
    scenes = document.get("scenes", [])
    if scenes and not isinstance(scenes, list):
        raise TypeError("glTF scenes must be a list")
    if not scenes:
        scenes = [{}]
    if scene_index < 0 or scene_index >= len(scenes):
        raise ValueError("glTF scene index is out of range")
    scene_raw = scenes[scene_index]
    if not isinstance(scene_raw, Mapping):
        raise TypeError("glTF scene must be an object")
    scene = Scene()
    for root_index in scene_raw.get("nodes", []):
        scene.add(build(int(root_index)))
    return scene