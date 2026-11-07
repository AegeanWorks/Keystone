"""Core-facing schema versions shared with optional adapters."""

from __future__ import annotations

WEB_API_VERSION = 1
SCENE_SCHEMA_VERSION = 2
EDITOR_SCHEMA_VERSION = 17
PREFAB_SCHEMA_VERSION = 1
EDITOR_ACTIONS = (
    "select",
    "transform",
    "set_node",
    "set_scene",
    "batch",
    "assign_asset",
    "set_component",
    "remove_component",
    "play_start",
    "play_step",
    "play_stop",
    "create_node",
    "delete_node",
    "duplicate_node",
    "reparent_node",
    "save_prefab",
    "insert_prefab",
    "rename_prefab",
    "duplicate_prefab",
    "delete_prefab",
    "restore_prefab",
    "save_scene",
    "load_scene",
    "diff_scene",
    "rename_scene",
    "duplicate_scene",
    "delete_scene",
    "restore_scene",
    "undo",
    "redo",
)
