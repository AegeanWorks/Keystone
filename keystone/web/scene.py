"""Export a game-agnostic scene as a JSON document for the browser viewer."""

from __future__ import annotations

import base64

from keystone.geometry import Material, MeshData
from keystone.scene import Scene
from keystone.texture import TextureData
from keystone.web.schema import SCENE_SCHEMA


def _floats(values: tuple[tuple[float, ...], ...]) -> list[float]:
    return [component for value in values for component in value]


def _mesh_document(mesh: MeshData) -> dict:
    return {
        "positions": _floats(mesh.positions),
        "normals": _floats(mesh.normals),
        "uvs": _floats(mesh.uvs),
        "colors": _floats(mesh.colors),
        "indices": list(mesh.indices),
    }


def _texture_document(texture: TextureData) -> dict:
    return {
        "name": texture.name,
        "width": texture.width,
        "height": texture.height,
        "rgba_base64": base64.b64encode(texture.rgba).decode("ascii"),
        "sha256": texture.sha256(),
    }


def scene_document(scene: Scene, game: str = "game") -> dict:
    """Serialize one scene into a deterministic, viewer-ready document."""
    meshes: dict[str, dict] = {}
    textures: dict[str, dict] = {}
    mesh_ids: dict[int, str] = {}
    texture_ids: dict[int, str] = {}
    nodes = []
    for node in scene.traverse():
        mesh_id = None
        if isinstance(node.mesh, MeshData):
            key = id(node.mesh)
            if key not in mesh_ids:
                mesh_id = f"mesh-{len(mesh_ids) + 1}"
                mesh_ids[key] = mesh_id
                meshes[mesh_id] = _mesh_document(node.mesh)
            mesh_id = mesh_ids[key]
        material = None
        if isinstance(node.material, Material):
            texture_id = None
            texture = node.material.texture
            if isinstance(texture, TextureData):
                key = id(texture)
                if key not in texture_ids:
                    texture_id = f"texture-{len(texture_ids) + 1}"
                    texture_ids[key] = texture_id
                    textures[texture_id] = _texture_document(texture)
                texture_id = texture_ids[key]
            emissive = getattr(node.material, "emissive", None)
            from keystone.math3d import Vec3 as _Vec3

            if not isinstance(emissive, _Vec3):
                emissive = _Vec3()
            material = {
                "color": [node.material.color.x, node.material.color.y, node.material.color.z],
                "specular": node.material.specular,
                "shininess": node.material.shininess,
                "checker_scale": node.material.checker_scale,
                "metallic": float(getattr(node.material, "metallic", 0.0)),
                "roughness": float(getattr(node.material, "roughness", 0.7)),
                "emissive": [emissive.x, emissive.y, emissive.z],
                "texture": texture_id,
            }
        nodes.append(
            {
                "id": node.id,
                "name": node.name,
                "parent_id": node.parent.id if node.parent else None,
                "visible": node.world_visible(),
                "tags": sorted(node.tags),
                "layer": node.layer,
                "components": sorted(component_type.__name__ for component_type in node.components),
                "world": list(node.world_matrix().flat()),
                "mesh": mesh_id,
                "material": material,
            }
        )
    camera = scene.camera
    light = scene.light
    point_light = scene.point_light
    return {
        "schema": SCENE_SCHEMA["version"],
        "game": game,
        "node_count": len(nodes),
        "mesh_count": len(meshes),
        "texture_count": len(textures),
        "camera": {
            "position": list(camera.position),
            "yaw": camera.yaw,
            "pitch": camera.pitch,
            "fov_y": camera.fov_y,
            "near": camera.near,
            "far": camera.far,
            "view": list(camera.view_matrix().flat()),
        },
        "light": {
            "direction": list(light.unit_direction()),
            "color": list(light.color),
            "intensity": light.intensity,
        },
        "point_light": (
            {
                "position": list(point_light.position),
                "color": list(point_light.color),
                "intensity": point_light.intensity,
                "radius": point_light.radius,
            }
            if point_light is not None
            else None
        ),
        "atmosphere": {
            "ambient": list(scene.ambient),
            "background": list(scene.background),
            "sky": list(scene.sky),
            "fog_density": scene.fog_density,
        },
        "nodes": nodes,
        "meshes": meshes,
        "textures": textures,
    }
