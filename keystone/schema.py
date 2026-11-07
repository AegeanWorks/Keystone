"""Core-facing schema versions shared with optional adapters."""

from __future__ import annotations

WEB_API_VERSION = 1
SCENE_SCHEMA_VERSION = 2
EDITOR_SCHEMA_VERSION = 4
PREFAB_SCHEMA_VERSION = 1
EDITOR_ACTIONS = (
    "select",
    "transform",
    "assign_asset",
    "create_node",
    "delete_node",
    "duplicate_node",
    "reparent_node",
    "save_prefab",
    "insert_prefab",
    "save_scene",
    "load_scene",
    "undo",
    "redo",
)
