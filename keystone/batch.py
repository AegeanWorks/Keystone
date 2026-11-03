"""Static batch planner: group draw nodes to cut draw calls without new deps.

Batching is game-agnostic and CPU-only: it inspects the scene graph, groups
visible mesh nodes by shared mesh and material payloads, and reports the
draw-call savings a renderer could realize. `merge_batches()` additionally
bakes each material group into one world-space mesh without mutating the
scene. Static merges suit still geometry; animated nodes must be excluded
and skinned meshes never merge.
"""

from __future__ import annotations

from keystone.geometry import MeshData
from keystone.mesh_builder import MeshBuilder
from keystone.scene import Scene

__all__ = ["merge_batches", "plan_batches"]


def _skinned(mesh: MeshData) -> bool:
    """Whether a mesh deforms at render time and must never bake or merge."""
    return bool(getattr(mesh, "skinned", False))


def plan_batches(scene: Scene) -> dict:
    groups: dict[tuple[int, int], dict] = {}
    total_triangles = 0
    for node in scene.traverse():
        mesh = node.mesh
        if not isinstance(mesh, MeshData) or not node.world_visible():
            continue
        if _skinned(mesh):
            continue
        material = node.material
        key = (id(mesh), id(material) if material is not None else 0)
        entry = groups.get(key)
        if entry is None:
            entry = {"nodes": [], "triangles": 0, "mesh": mesh, "material": material}
            groups[key] = entry
        entry["nodes"].append(node.id or node.name)
        entry["triangles"] += mesh.triangle_count()
        total_triangles += mesh.triangle_count()
    batches = [
        {"nodes": sorted(entry["nodes"]), "count": len(entry["nodes"]), "triangles": entry["triangles"]}
        for entry in groups.values()
    ]
    batches.sort(key=lambda item: (-item["count"], item["nodes"][0] if item["nodes"] else ""))
    nodes_total = sum(entry["count"] for entry in batches)
    return {
        "schema": 1,
        "groups": len(batches),
        "draw_calls": nodes_total,
        "batched_calls": len(batches),
        "saved_calls": max(0, nodes_total - len(batches)),
        "triangles": total_triangles,
        "batches": batches,
    }


def merge_batches(scene: Scene, exclude: set[str] | None = None) -> dict:
    """Bake static groups into world-space meshes; animated ids stay separate.

    `exclude` holds node ids (or names) that must not merge, e.g. animated
    nodes driven by `keystone.animation`. Skinned meshes never merge.
    Returns per-group merged meshes plus a summary reusing `plan_batches()`
    counts.
    """
    excluded = set(exclude or ())
    groups: dict[int, dict] = {}
    for node in scene.traverse():
        mesh = node.mesh
        if not isinstance(mesh, MeshData) or not node.world_visible():
            continue
        if _skinned(mesh):
            continue
        if node.id in excluded or node.name in excluded:
            continue
        key = id(node.material) if node.material is not None else 0
        entry = groups.get(key)
        if entry is None:
            entry = {"nodes": [], "material": node.material, "builder": MeshBuilder()}
            groups[key] = entry
        entry["nodes"].append(node.id or node.name)
        entry["builder"].add_mesh_matrix(mesh, node.world_matrix())
    merged = []
    for entry in groups.values():
        if entry["builder"].is_empty():
            continue
        mesh = entry["builder"].build()
        merged.append(
            {"nodes": sorted(entry["nodes"]), "count": len(entry["nodes"]), "triangles": mesh.triangle_count(), "mesh": mesh,
             "material": entry["material"]}
        )
    merged.sort(key=lambda item: (-item["count"], item["nodes"][0] if item["nodes"] else ""))
    plan = plan_batches(scene)
    return {
        "schema": 1,
        "groups": len(merged),
        "merged_calls": len(merged),
        "saved_calls": max(0, plan["draw_calls"] - len(merged)),
        "triangles": sum(item["triangles"] for item in merged),
        "merged": merged,
        "plan": plan,
    }
