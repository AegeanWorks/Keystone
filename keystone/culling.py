"""Deterministic CPU view-frustum culling for the core forward renderer.

Pure CPU logic: no OpenGL, no window, no new dependencies. Extracts the six
clip planes from ``PerspectiveCamera.view_projection(aspect)`` and tests each
world-visible mesh node against its world-space bounds. Nodes fully outside
any plane are skipped in the color pass. Nodes touching a plane (distance
zero) count as visible. Skinned meshes are always visible (conservative:
deformation exceeds the bind-pose bounds). The shadow depth pass is not
culled here: off-camera casters still shade the frame, and the light VP
differs from the camera VP.
"""

from __future__ import annotations

import math

from keystone.geometry import MeshData
from keystone.math3d import Mat4, Vec3
from keystone.scene import Scene

__all__ = [
    "aabb_visible",
    "cull_scene",
    "culling_enabled",
    "extract_planes",
    "model_visible",
    "node_visible",
    "world_bounds",
]


def culling_enabled(scene: Scene) -> bool:
    """Return whether frustum culling is requested for this scene."""
    return bool(getattr(getattr(scene, "culling", None), "enabled", True))


def extract_planes(view_projection: Mat4) -> tuple[tuple[float, float, float, float], ...]:
    """Extract normalized (a, b, c, d) frustum planes, deterministic order.

    Order is left, right, bottom, top, near, far. Planes point inward, so a
    point is inside when ``a*x + b*y + c*z + d >= 0`` for every plane.
    """
    m = view_projection.m
    row0 = (m[0], m[4], m[8], m[12])
    row1 = (m[1], m[5], m[9], m[13])
    row2 = (m[2], m[6], m[10], m[14])
    row3 = (m[3], m[7], m[11], m[15])
    raw = (
        (row3[0] + row0[0], row3[1] + row0[1], row3[2] + row0[2], row3[3] + row0[3]),
        (row3[0] - row0[0], row3[1] - row0[1], row3[2] - row0[2], row3[3] - row0[3]),
        (row3[0] + row1[0], row3[1] + row1[1], row3[2] + row1[2], row3[3] + row1[3]),
        (row3[0] - row1[0], row3[1] - row1[1], row3[2] - row1[2], row3[3] - row1[3]),
        (row3[0] + row2[0], row3[1] + row2[1], row3[2] + row2[2], row3[3] + row2[3]),
        (row3[0] - row2[0], row3[1] - row2[1], row3[2] - row2[2], row3[3] - row2[3]),
    )
    planes: list[tuple[float, float, float, float]] = []
    for a, b, c, d in raw:
        length = math.sqrt(a * a + b * b + c * c)
        if length < 1e-12:
            raise ValueError("degenerate frustum plane")
        planes.append((a / length, b / length, c / length, d / length))
    return tuple(planes)


def world_bounds(mesh: MeshData, model: Mat4) -> tuple[Vec3, Vec3]:
    """Return the world-space AABB of a mesh under an affine model matrix."""
    low, high = mesh.bounds()
    min_x, min_y, min_z = math.inf, math.inf, math.inf
    max_x, max_y, max_z = -math.inf, -math.inf, -math.inf
    for x in (low[0], high[0]):
        for y in (low[1], high[1]):
            for z in (low[2], high[2]):
                corner = model.transform_point(Vec3(x, y, z))
                min_x = min(min_x, corner.x)
                min_y = min(min_y, corner.y)
                min_z = min(min_z, corner.z)
                max_x = max(max_x, corner.x)
                max_y = max(max_y, corner.y)
                max_z = max(max_z, corner.z)
    return (Vec3(min_x, min_y, min_z), Vec3(max_x, max_y, max_z))


def aabb_visible(
    low: Vec3,
    high: Vec3,
    planes: tuple[tuple[float, float, float, float], ...],
) -> bool:
    """Return True when an AABB touches or intersects every frustum plane."""
    for a, b, c, d in planes:
        px = high.x if a >= 0.0 else low.x
        py = high.y if b >= 0.0 else low.y
        pz = high.z if c >= 0.0 else low.z
        if a * px + b * py + c * pz + d < 0.0:
            return False
    return True


def model_visible(
    mesh: MeshData,
    model: Mat4,
    planes: tuple[tuple[float, float, float, float], ...],
) -> bool:
    """Return True when a mesh under an affine model matrix survives culling.

    Skinned meshes are always visible (conservative: deformation exceeds the
    bind-pose bounds). Degenerate models fall back to visible.
    """
    if bool(getattr(mesh, "skinned", False)):
        return True
    try:
        low, high = world_bounds(mesh, model)
    except (ValueError, ArithmeticError):
        return True
    return aabb_visible(low, high, planes)


def node_visible(node: object, planes: tuple[tuple[float, float, float, float], ...]) -> bool:
    """Return True when a scene node survives frustum culling."""
    world_visible = getattr(node, "world_visible", None)
    if callable(world_visible) and not world_visible():
        return False
    mesh = getattr(node, "mesh", None)
    if not isinstance(mesh, MeshData):
        return True
    world_matrix = getattr(node, "world_matrix", None)
    if not callable(world_matrix):
        return True
    model = world_matrix()
    if not isinstance(model, Mat4):
        return True
    return model_visible(mesh, model, planes)


def cull_scene(scene: Scene, width: int, height: int) -> set[int]:
    """Return python ``id()`` values of frustum-visible nodes.

    Non-mesh nodes are included (callers already skip them for drawing);
    world-invisible nodes are excluded. Raises ValueError for degenerate
    framebuffer sizes.
    """
    if width <= 0 or height <= 0:
        raise ValueError("culling width and height must be positive")
    if not culling_enabled(scene):
        return {id(node) for node in scene.traverse() if node.world_visible()}
    planes = extract_planes(scene.camera.view_projection(width / height))
    return {id(node) for node in scene.traverse() if node_visible(node, planes)}
