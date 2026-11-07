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
        "node": ["id", "name", "parent_id", "children", "visible", "selected", "tags", "layer", "components", "transform", "world"],
        "transform": ["position", "rotation", "scale"],
        "create_node": ["id", "name", "parent", "position", "rotation", "scale", "tags", "layer", "visible", "mesh", "material"],
        "reparent_node": ["id", "parent"],
        "history": ["undo", "redo", "limit"],
        "scene": ["name", "node_count", "source", "error"],
    },
    "notes": [
        "rotation is [x, y, z, w]; transforms are local; world is column-major",
        "schema 2 adds create/delete/duplicate/reparent, undo/redo and registry-linked mesh/material ids",
        "schema 3 adds save_scene/load_scene with typed-component scene files",
        "mesh and material are asset ids; create_node needs the game to expose an AssetRegistry as assets",
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
