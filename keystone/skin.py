"""Deterministic linear-blend skinning: bone palettes and CPU reference math.

Bone matrices are resolved from the live scene in frozen joint order, so
every run with the same pose yields the same palette. Games own rigs and
clips; the engine owns deformation. GL-free and game-agnostic.
"""

from __future__ import annotations

import math

from keystone.geometry import MAX_SKIN_BONES, MeshData
from keystone.math3d import Mat4, Vec3
from keystone.scene import Scene

__all__ = ["MAX_SKIN_BONES", "bone_matrices", "skin_mesh", "skin_point"]


def bone_matrices(scene: Scene, mesh: MeshData) -> tuple[Mat4, ...]:
    """Return world-space bone palettes (joint world matrix times inverse bind)."""
    if not mesh.skinned:
        raise ValueError("mesh has no skinning influences")
    if len(mesh.skin_joints) > MAX_SKIN_BONES:
        raise ValueError("skin joint count exceeds the bone palette")
    index: dict[str, object] = {}
    for node in scene.traverse():
        if node.id:
            index[node.id] = node
        index.setdefault(node.name, node)
    bones: list[Mat4] = []
    for name, inverse in zip(mesh.skin_joints, mesh.skin_inverse_bind):
        node = index.get(name)
        if node is None:
            raise ValueError(
                f"skin joint {name!r} is missing from the scene.\n"
                "Why: the skinned mesh references a joint with no matching node id or name.\n"
                "Fix: add the joint node to the scene, or rebuild the mesh with valid joint names."
            )
        bones.append(node.world_matrix() * Mat4(tuple(inverse)))
    return tuple(bones)


def _rotate_normal(bone: Mat4, normal: Vec3) -> Vec3:
    return Vec3(
        bone.m[0] * normal.x + bone.m[4] * normal.y + bone.m[8] * normal.z,
        bone.m[1] * normal.x + bone.m[5] * normal.y + bone.m[9] * normal.z,
        bone.m[2] * normal.x + bone.m[6] * normal.y + bone.m[10] * normal.z,
    )


def skin_point(
    position: Vec3,
    normal: Vec3,
    joints: tuple[int, ...],
    weights: tuple[float, ...],
    bones: tuple[Mat4, ...],
) -> tuple[Vec3, Vec3]:
    """Deform one vertex by its influences; mirrors the vertex shader exactly."""
    if len(joints) != len(weights) or not joints:
        raise ValueError("joints and weights must be non-empty and match")
    px, py, pz = 0.0, 0.0, 0.0
    nx, ny, nz = 0.0, 0.0, 0.0
    for joint, weight in zip(joints, weights):
        if joint < 0 or joint >= len(bones):
            raise ValueError("skin joint index is out of range")
        moved = bones[joint] * position
        rotated = _rotate_normal(bones[joint], normal)
        px += weight * moved.x
        py += weight * moved.y
        pz += weight * moved.z
        nx += weight * rotated.x
        ny += weight * rotated.y
        nz += weight * rotated.z
    deformed_normal = Vec3(nx, ny, nz)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length > 1e-12:
        deformed_normal = Vec3(nx / length, ny / length, nz / length)
    else:
        deformed_normal = Vec3(normal.x, normal.y, normal.z)
    return Vec3(px, py, pz), deformed_normal


def skin_mesh(mesh: MeshData, bones: tuple[Mat4, ...]) -> MeshData:
    """Return a deformed copy of the mesh in bind-pose layout (CPU oracle)."""
    if not mesh.skinned:
        raise ValueError("mesh has no skinning influences")
    if len(bones) != len(mesh.skin_joints):
        raise ValueError("bone palette must match the joint count")
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    for vertex in range(mesh.vertex_count()):
        position, normal = skin_point(
            Vec3(*mesh.positions[vertex]),
            Vec3(*mesh.normals[vertex]),
            mesh.joints[vertex],
            mesh.weights[vertex],
            bones,
        )
        positions.append((position.x, position.y, position.z))
        normals.append((normal.x, normal.y, normal.z))
    return MeshData(
        positions=tuple(positions),
        normals=tuple(normals),
        uvs=mesh.uvs,
        indices=mesh.indices,
        colors=mesh.colors,
        joints=mesh.joints,
        weights=mesh.weights,
        skin_joints=mesh.skin_joints,
        skin_inverse_bind=mesh.skin_inverse_bind,
    )
