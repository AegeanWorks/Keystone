"""Versioned schemas shared by the web API, AI clients and the browser viewer."""

from __future__ import annotations

from keystone.schema import SCENE_SCHEMA_VERSION, WEB_API_VERSION

__all__ = ["SCENE_SCHEMA", "WEB_API_VERSION"]

SCENE_SCHEMA = {
    "version": SCENE_SCHEMA_VERSION,
    "fields": {
        "camera": ["position", "yaw", "pitch", "fov_y", "near", "far", "view"],
        "light": ["direction", "color", "intensity"],
        "point_light": ["position", "color", "intensity", "radius"],
        "atmosphere": ["ambient", "background", "sky", "fog_density"],
        "node": ["id", "name", "parent_id", "visible", "tags", "layer", "components", "world", "mesh", "material"],
        "mesh": ["positions", "normals", "uvs", "colors", "indices"],
        "material": ["color", "specular", "shininess", "checker_scale", "texture"],
        "texture": ["name", "width", "height", "rgba_base64", "sha256"],
    },
    "notes": [
        "world is a column-major 4x4 matrix ready for WebGL uniformMatrix4fv.",
        "nodes reference shared meshes and textures by id; geometry is never duplicated per node.",
        "positions, normals, uvs and colors are flat arrays in vertex order.",
        "the browser viewer is an approximation; the OpenGL renderer remains the pixel authority.",
    ],
}
