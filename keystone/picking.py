"""Scene picking: ray queries over visible world meshes.

Physics can cast a ray against keyed AABBs, and the scene can derive those
AABBs for navigation; this module connects the two so a game or an AI can ask
"what is under this ray" and get the node back. Bounds are the same
conservative world-space mesh boxes navigation uses, so picking never sees
camera-relative overlay content, hidden nodes or excluded layers.

Ties break on node id, which keeps repeated queries deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from keystone.culling import world_bounds
from keystone.geometry import MeshData
from keystone.math3d import Vec3
from keystone.physics import (
    AABB,
    Ray,
    Sphere,
    aabb_overlap,
    raycast,
    sphere_aabb_overlap,
)
from keystone.scene import OVERLAY_LAYER, Node, Scene

__all__ = ["SceneHit", "SceneOverlap", "hit_report", "overlap_report", "overlap_scene", "raycast_scene"]


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class SceneHit:
    """One scene ray hit: the node, the world distance and the contact point."""

    node_id: str
    node_name: str
    distance: float
    point: Vec3
    box: AABB


def _ignore_names(value: object) -> frozenset[str]:
    if isinstance(value, str):
        raise TypeError("ignore must be an iterable of node ids or names, not a string")
    try:
        names = tuple(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError("ignore must be an iterable of node ids or names") from exc
    for name in names:
        if not isinstance(name, str) or not name.strip():
            raise TypeError("ignored node ids and names must be non-blank strings")
    return frozenset(names)


def _scene_meshes(
    scene: Scene,
    layer: str | None,
    ignored: frozenset[str],
) -> list[tuple[Node, AABB]]:
    """Visible world meshes and their conservative world AABBs."""
    found: list[tuple[Node, AABB]] = []
    for node in scene.traverse():
        if not node.world_visible() or node.layer == OVERLAY_LAYER:
            continue
        if layer is not None and node.layer != layer:
            continue
        if node.id in ignored or node.name in ignored:
            continue
        mesh = node.mesh
        if not isinstance(mesh, MeshData):
            continue
        low, high = world_bounds(mesh, node.world_matrix())
        found.append(
            (
                node,
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
                ),
            )
        )
    return found


def raycast_scene(
    scene: Scene,
    ray: Ray,
    *,
    layer: str | None = None,
    ignore: object = (),
    max_distance: float | None = None,
) -> SceneHit | None:
    """Return the nearest visible mesh hit, or None.

    ``layer`` narrows the query like ``scene_boxes``; overlay and hidden
    nodes are always skipped. ``ignore`` holds node ids or names to exclude,
    and ``max_distance`` shortens the ray without rebuilding it.
    """
    if not isinstance(scene, Scene):
        raise TypeError("raycast_scene needs a Scene")
    if not isinstance(ray, Ray):
        raise TypeError("raycast_scene needs a Ray")
    if layer is not None and not isinstance(layer, str):
        raise TypeError("raycast layer must be a string or None")
    if layer is not None and not layer.strip():
        raise ValueError("raycast layer must be a non-blank string")
    ignored = _ignore_names(ignore)
    limit = ray.t_max
    if max_distance is not None:
        limit = min(limit, _finite(max_distance, "max distance"))
        if limit < 0.0:
            raise ValueError("max distance must be non-negative")
    effective = ray if limit == ray.t_max else Ray(ray.origin, ray.direction, limit)
    boxes = _scene_meshes(scene, layer, ignored)
    colliders = [(node.id, box) for node, box in boxes]
    nodes = {node.id: node for node, _box in boxes}
    hit = raycast(effective, colliders)
    if hit is None:
        return None
    node = nodes[hit.key]
    unit = ray.direction / ray.direction.length()
    point = ray.origin + unit * hit.distance
    return SceneHit(
        node_id=hit.key,
        node_name=node.name,
        distance=hit.distance,
        point=point,
        box=hit.box,
    )


def hit_report(hit: SceneHit | None) -> dict:
    """Return a JSON-safe summary of one scene ray query."""
    if hit is None:
        return {
            "schema": 1,
            "hit": False,
            "node_id": None,
            "node_name": None,
            "distance": None,
            "point": None,
        }
    if not isinstance(hit, SceneHit):
        raise TypeError("hit_report needs a SceneHit or None")
    return {
        "schema": 1,
        "hit": True,
        "node_id": hit.node_id,
        "node_name": hit.node_name,
        "distance": round(hit.distance, 6),
        "point": [round(hit.point.x, 6), round(hit.point.y, 6), round(hit.point.z, 6)],
    }

@dataclass(frozen=True, slots=True)
class SceneOverlap:
    """One node whose world bounds overlap the query shape."""

    node_id: str
    node_name: str
    distance: float
    box: AABB


def overlap_scene(
    scene: Scene,
    shape: Sphere | AABB,
    *,
    layer: str | None = None,
    ignore: object = (),
) -> tuple[SceneOverlap, ...]:
    """Return visible meshes whose world bounds overlap a sphere or box.

    Results sort by centre distance, then node id, so a query is
    deterministic. Hidden nodes and camera-relative overlay content never
    overlap; ``layer`` and ``ignore`` filter like ``raycast_scene``.
    """
    if not isinstance(scene, Scene):
        raise TypeError("overlap_scene needs a Scene")
    if not isinstance(shape, (Sphere, AABB)):
        raise TypeError("overlap_scene needs a Sphere or AABB")
    if layer is not None and not isinstance(layer, str):
        raise TypeError("overlap layer must be a string or None")
    if layer is not None and not layer.strip():
        raise ValueError("overlap layer must be a non-blank string")
    ignored = _ignore_names(ignore)
    centre = shape.center
    found: list[SceneOverlap] = []
    for node, box in _scene_meshes(scene, layer, ignored):
        if isinstance(shape, Sphere):
            overlaps = sphere_aabb_overlap(shape, box)
        else:
            overlaps = aabb_overlap(shape, box)
        if not overlaps:
            continue
        found.append(
            SceneOverlap(
                node_id=node.id,
                node_name=node.name,
                distance=(box.center - centre).length(),
                box=box,
            )
        )
    found.sort(key=lambda hit: (hit.distance, hit.node_id))
    return tuple(found)


def overlap_report(hits: tuple[SceneOverlap, ...] | list[SceneOverlap]) -> dict:
    """Return a JSON-safe summary of one overlap query."""
    try:
        items = tuple(hits)
    except TypeError as exc:
        raise TypeError("overlap_report needs an iterable of SceneOverlap") from exc
    for hit in items:
        if not isinstance(hit, SceneOverlap):
            raise TypeError("overlap_report needs an iterable of SceneOverlap")
    return {
        "schema": 1,
        "count": len(items),
        "nodes": [
            {
                "node_id": hit.node_id,
                "node_name": hit.node_name,
                "distance": round(hit.distance, 6),
                "center": [round(hit.box.center.x, 6), round(hit.box.center.y, 6), round(hit.box.center.z, 6)],
            }
            for hit in items
        ],
    }
