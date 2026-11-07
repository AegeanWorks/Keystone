"""Versioned schemas shared by the web API, AI clients and the browser viewer."""

from __future__ import annotations

from keystone.schema import (
    EDITOR_ACTIONS,
    EDITOR_SCHEMA_VERSION,
    SCENE_SCHEMA_VERSION,
    WEB_API_VERSION,
)

__all__ = ["EDITOR_SCHEMA", "SCENE_SCHEMA", "WEB_API_VERSION"]

EDITOR_SCHEMA = {
    "version": EDITOR_SCHEMA_VERSION,
    "actions": list(EDITOR_ACTIONS),
    "fields": {
        "node": ["id", "name", "parent_id", "children", "visible", "selected", "tags", "layer", "components", "component_data", "mesh", "material", "transform", "world"],
        "transform": ["position", "rotation", "scale"],
        "set_node": ["id", "name", "visible", "tags", "layer"],
        "batch": ["actions"],
        "rename_prefab": ["name", "new_name"],
        "duplicate_prefab": ["name", "new_name"],
        "delete_prefab": ["name"],
        "rename_scene": ["name", "new_name"],
        "duplicate_scene": ["name", "new_name"],
        "delete_scene": ["name"],
        "create_node": ["id", "name", "parent", "position", "rotation", "scale", "tags", "layer", "visible", "mesh", "material"],
        "assign_asset": ["id", "mesh", "material"],
        "set_component": ["id", "type", "data"],
        "remove_component": ["id", "type"],
        "play_step": ["frames", "actions"],
        "play": ["active", "frames", "step"],
        "asset": ["id", "kind", "sha256", "source", "dependencies", "metadata"],
        "component_types": ["name"],
        "component_schema": ["fields"],
        "component_field": ["name", "type", "required", "default"],
        "reparent_node": ["id", "parent"],
        "history": ["undo", "redo", "limit"],
        "scene": ["name", "node_count", "source", "error"],
    },
    "notes": [
        "rotation is [x, y, z, w]; transforms are local; world is column-major",
        "schema 2 adds create/delete/duplicate/reparent, undo/redo and registry-linked mesh/material ids",
        "schema 3 adds save_scene/load_scene with typed-component scene files",
        "schema 4 adds asset inventory and assign_asset for existing nodes",
        "schema 5 adds component_types plus set_component/remove_component authoring",
        "schema 6 adds play_start/play_step/play_stop and restores the authored scene on stop",
        "schema 7 adds set_node property editing for name, visibility, tags and layer",
        "schema 8 adds atomic multi-action batches with one undo entry",
        "schema 9 adds mesh/material/texture/prefab metadata to the asset inventory",
        "schema 10 adds dataclass field schemas for component_types",
        "schema 11 adds safe prefab/scene rename and delete actions",
        "schema 12 adds mesh bounds to asset metadata",
        "schema 13 adds material/texture preview thumbnails to asset metadata",
        "schema 14 adds safe scene/prefab duplication",
        "mesh and material are asset ids; create_node and assign_asset need the game to expose an AssetRegistry as assets",
    ],
}

SCENE_SCHEMA = {
    "version": SCENE_SCHEMA_VERSION,
    "fields": {
        "camera": ["position", "yaw", "pitch", "fov_y", "near", "far", "view"],
        "light": ["direction", "color", "intensity"],
        "point_light": ["position", "color", "intensity", "radius"],
        "atmosphere": ["ambient", "background", "sky", "fog_density"],
        "node": ["id", "name", "parent_id", "visible", "tags", "layer", "components", "world", "mesh", "material"],
        "mesh": ["positions", "normals", "uvs", "colors", "indices"],
        "material": ["color", "specular", "shininess", "checker_scale", "metallic", "roughness", "emissive", "texture"],
        "texture": ["name", "width", "height", "rgba_base64", "sha256"],
    },
    "notes": [
        "world is a column-major 4x4 matrix ready for WebGL uniformMatrix4fv.",
        "nodes reference shared meshes and textures by id; geometry is never duplicated per node.",
        "positions, normals, uvs and colors are flat arrays in vertex order.",
        "schema 2 adds PBR material fields (metallic, roughness, emissive).",
        "the browser viewer is an approximation; the OpenGL renderer remains the pixel authority.",
    ],
}
