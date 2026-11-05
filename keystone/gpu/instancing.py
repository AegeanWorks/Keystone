"""Deterministic grouping for hardware instancing.

Groups visible mesh nodes sharing identical payloads so the renderer can
issue one instanced draw per group instead of one draw per node. Pure
CPU logic: no OpenGL, no window, no new dependencies. Mirrors the
ordering rules of `keystone.batch.plan_batches` so results are stable
across runs.
"""

from __future__ import annotations

from keystone.culling import model_visible
from keystone.geometry import Material, MeshData
from keystone.scene import Scene

__all__ = ["group_instances", "plan_instanced"]


Plane = tuple[float, float, float, float]


def _material_key(material: object) -> int:
    """Normalize the grouping key to match renderer fallback behavior."""
    if isinstance(material, Material):
        return id(material)
    return 0


def group_instances(
    scene: Scene,
    planes: tuple[Plane, ...] | None = None,
) -> list[dict]:
    """Group visible nodes by identical mesh/material payloads.

    Returns groups sorted by ``(-count, nodes[0])`` with nodes sorted by
    ``(id or name)``. Each group holds ``mesh``, ``material`` (or None for
    the renderer default), ``nodes``, ``node_keys``, ``models`` (Mat4 in
    node order) and ``triangles``.

    When ``planes`` (normalized frustum planes from
    ``keystone.culling.extract_planes``) is given, nodes fully outside the
    frustum are skipped inline using the same predicate as
    ``keystone.culling.cull_scene`` but reusing the already-computed world
    matrix, so culling adds no second scene traversal.     ``None`` preserves
    the legacy unculled grouping.
    """
    groups: dict[tuple[int, int], dict] = {}
    for node in scene.traverse():
        mesh = node.mesh
        if not isinstance(mesh, MeshData) or not node.world_visible():
            continue
        model = node.world_matrix()
        if planes is not None and not model_visible(mesh, model, planes):
            continue
        material = node.material if isinstance(node.material, Material) else None
        key = (id(mesh), id(material) if material is not None else 0)
        entry = groups.get(key)
        if entry is None:
            entry = {"mesh": mesh, "material": material, "items": []}
            groups[key] = entry
        label = node.id or node.name
        entry["items"].append((label, node, model))
    result: list[dict] = []
    for entry in groups.values():
        items = sorted(entry["items"], key=lambda item: item[0])
        nodes = [item[1] for item in items]
        models = [item[2] for item in items]
        mesh = entry["mesh"]
        count = len(nodes)
        result.append(
            {
                "mesh": mesh,
                "material": entry["material"],
                "nodes": nodes,
                "node_keys": [item[0] for item in items],
                "models": models,
                "triangles": mesh.triangle_count() * count,
            }
        )
    result.sort(key=lambda group: (-len(group["nodes"]), group["node_keys"][0] if group["node_keys"] else ""))
    return result


def plan_instanced(scene: Scene) -> dict:
    """Return a JSON-safe instancing plan mirroring ``plan_batches`` counts."""
    groups = group_instances(scene)
    nodes_total = sum(len(group["nodes"]) for group in groups)
    batches = []
    for group in groups:
        batches.append(
            {
                "nodes": list(group["node_keys"]),
                "count": len(group["nodes"]),
                "triangles": group["triangles"],
                "matrices": [list(model.flat()) for model in group["models"]],
            }
        )
    instanced = sum(len(group["nodes"]) for group in groups if len(group["nodes"]) >= 2)
    return {
        "schema": 1,
        "groups": len(groups),
        "draw_calls": nodes_total,
        "instanced_calls": len(groups),
        "saved_calls": max(0, nodes_total - len(groups)),
        "instances": instanced,
        "triangles": sum(group["triangles"] for group in groups),
        "batches": batches,
    }
