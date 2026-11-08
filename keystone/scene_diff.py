"""Structured diffs between versioned scene snapshot documents.

The diff is deterministic and JSON-safe: nodes are keyed by id, fields are
reported with before/after values, and camera/environment/root sections are
compared one level deep. It is intended for editor and AI iteration, not for
three-way merges.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ["SCENE_DIFF_SCHEMA_VERSION", "diff_scene_documents"]

SCENE_DIFF_SCHEMA_VERSION = 4
NODE_FIELDS = (
    "name",
    "parent_id",
    "tags",
    "layer",
    "visible",
    "transform",
    "mesh",
    "material",
    "prefab_link",
    "prefab_base",
    "scene_group",
    "components",
)


def _node_map(document: Mapping[str, object]) -> dict[str, dict[str, object]]:
    raw_nodes = document.get("nodes", [])
    if not isinstance(raw_nodes, (list, tuple)):
        raise TypeError("scene diff nodes must be a list")
    nodes: dict[str, dict[str, object]] = {}
    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            raise TypeError("scene diff node must be a mapping")
        node_id = raw.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("scene diff node id must be a non-blank string")
        if node_id in nodes:
            raise ValueError(f"scene diff has duplicate node id {node_id!r}")
        nodes[node_id] = dict(raw)
    return nodes


def _section_diff(before: object, after: object) -> dict[str, dict[str, object]]:
    left = before if isinstance(before, Mapping) else {}
    right = after if isinstance(after, Mapping) else {}
    changed: dict[str, dict[str, object]] = {}
    for key in sorted(set(left) | set(right)):
        if left.get(key) != right.get(key):
            changed[key] = {"before": left.get(key), "after": right.get(key)}
    return changed


def diff_scene_documents(
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> dict[str, object]:
    """Compare two scene snapshot documents and return a structured diff."""
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        raise TypeError("scene diff documents must be mappings")
    before_nodes = _node_map(before)
    after_nodes = _node_map(after)
    added = sorted(set(after_nodes) - set(before_nodes))
    removed = sorted(set(before_nodes) - set(after_nodes))
    changed: list[dict[str, object]] = []
    for node_id in sorted(set(before_nodes) & set(after_nodes)):
        fields: dict[str, dict[str, object]] = {}
        for field in NODE_FIELDS:
            if before_nodes[node_id].get(field) != after_nodes[node_id].get(field):
                fields[field] = {
                    "before": before_nodes[node_id].get(field),
                    "after": after_nodes[node_id].get(field),
                }
        if fields:
            changed.append({"id": node_id, "fields": fields})
    camera = _section_diff(before.get("camera"), after.get("camera"))
    environment = _section_diff(before.get("environment"), after.get("environment"))
    root = _section_diff(before.get("root"), after.get("root"))
    return {
        "schema": SCENE_DIFF_SCHEMA_VERSION,
        "added": added,
        "removed": removed,
        "changed": changed,
        "camera": camera,
        "environment": environment,
        "root": root,
        "has_changes": bool(added or removed or changed or camera or environment or root),
    }
