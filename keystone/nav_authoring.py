"""Author nav grids from collision boxes or JSON documents.

Hand-maintaining blocked cells beside a game's collision boxes is a
correctness hazard: move a wall and the route silently runs through it. This
module derives a `NavGrid` from the same AABBs the character collides with,
so navigation data follows the level. Cells are blocked when their world-space
centre falls inside a box inflated by a clearance radius on X and Z, which is
the standard point-agent approximation and keeps a body's width away from
walls.

`write_navgrid`/`read_navgrid` persist the grid as a schema-1 JSON document,
so an AI can inspect, diff and hand-edit navigation data outside a running
engine.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path

from keystone.culling import world_bounds
from keystone.geometry import MeshData
from keystone.math3d import Vec3
from keystone.pathfinding import NavGrid
from keystone.physics import AABB
from keystone.scene import OVERLAY_LAYER, Scene
from keystone.serialization import read_json, write_json_atomic

__all__ = ["grid_from_boxes", "read_navgrid", "scene_boxes", "write_navgrid"]


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def grid_from_boxes(
    width: int,
    height: int,
    boxes: Iterable[AABB],
    *,
    cell_size: float = 1.0,
    origin: Vec3 | None = None,
    clearance: float = 0.0,
) -> NavGrid:
    """Rasterize collision boxes into an XZ nav grid.

    ``origin`` is the world position of the grid's lower corner; cell
    ``(x, y)`` has its centre at ``origin + ((x + 0.5) * cell_size, 0,
    (y + 0.5) * cell_size)``. A cell blocks when that centre lies inside a box
    expanded by ``clearance`` on X and Z, so a character radius keeps a
    walkable margin. Vertical extents are ignored: pass only the boxes that
    matter for the level's floor.
    """
    width = _positive_int(width, "nav grid width")
    height = _positive_int(height, "nav grid height")
    size = _finite(cell_size, "cell size")
    if size <= 0.0:
        raise ValueError("cell size must be positive")
    margin = _finite(clearance, "clearance")
    if margin < 0.0:
        raise ValueError("clearance must be non-negative")
    start = Vec3() if origin is None else origin
    if not isinstance(start, Vec3):
        raise TypeError("grid origin must be a Vec3 or None")
    for axis in ("x", "y", "z"):
        _finite(getattr(start, axis), f"grid origin {axis}")
    try:
        obstacles = tuple(boxes)
    except TypeError as exc:
        raise TypeError("boxes must be an iterable of AABB") from exc
    for box in obstacles:
        if not isinstance(box, AABB):
            raise TypeError("boxes must be an iterable of AABB")
    blocked: set[tuple[int, int]] = set()
    for y in range(height):
        centre_z = start.z + (y + 0.5) * size
        for x in range(width):
            centre_x = start.x + (x + 0.5) * size
            for box in obstacles:
                if (
                    abs(centre_x - box.center.x) <= box.half_extents.x + margin
                    and abs(centre_z - box.center.z) <= box.half_extents.z + margin
                ):
                    blocked.add((x, y))
                    break
    return NavGrid(width, height, frozenset(blocked))


def scene_boxes(scene: Scene, *, layer: str | None = None) -> tuple[AABB, ...]:
    """Return one world AABB per visible world-space mesh node.

    Camera-relative overlay content never blocks a level, so it is skipped
    even when it carries a mesh; ``layer`` narrows the result to one named
    layer for games that mark walls separately from props.
    """
    if not isinstance(scene, Scene):
        raise TypeError("scene_boxes needs a Scene")
    if layer is not None and not isinstance(layer, str):
        raise TypeError("scene box layer must be a string or None")
    if layer is not None and not layer.strip():
        raise ValueError("scene box layer must be a non-blank string")
    boxes: list[AABB] = []
    for node in scene.traverse():
        if not node.world_visible() or node.layer == OVERLAY_LAYER:
            continue
        if layer is not None and node.layer != layer:
            continue
        mesh = node.mesh
        if not isinstance(mesh, MeshData):
            continue
        low, high = world_bounds(mesh, node.world_matrix())
        boxes.append(
            AABB(
                Vec3(
                    (low.x + high.x) * 0.5,
                    (low.y + high.y) * 0.5,
                    (low.z + high.z) * 0.5,
                ),
                Vec3(
                    (high.x - low.x) * 0.5,
                    (high.y - low.y) * 0.5,
                    (high.z - low.z) * 0.5,
                ),
            )
        )
    return tuple(boxes)


def read_navgrid(path: str | Path) -> NavGrid:
    """Load a schema-1 nav grid document."""
    data = read_json(path)
    if not isinstance(data, dict):
        raise TypeError("nav grid document must be a mapping")
    return NavGrid.from_dict(data)


def write_navgrid(path: str | Path, grid: NavGrid) -> None:
    """Write a nav grid as an atomic JSON document."""
    if not isinstance(grid, NavGrid):
        raise TypeError("write_navgrid needs a NavGrid")
    write_json_atomic(path, grid.to_dict())
