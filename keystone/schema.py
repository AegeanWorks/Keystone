"""Core-facing schema versions shared with optional adapters."""

from __future__ import annotations

WEB_API_VERSION = 1
SCENE_SCHEMA_VERSION = 2
EDITOR_SCHEMA_VERSION = 2
PREFAB_SCHEMA_VERSION = 1
EDITOR_ACTIONS = (
    "select",
    "transform",
    "create_node",
    "delete_node",
    "duplicate_node",
    "reparent_node",
    "save_prefab",
    "insert_prefab",
    "undo",
    "redo",
)
