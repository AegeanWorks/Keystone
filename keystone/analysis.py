"""Machine-readable frame reports for AI and headless UI analysis."""

from __future__ import annotations

import hashlib
from pathlib import Path

from keystone.geometry import Material, MeshData
from keystone.math3d import Vec3
from keystone.png import read_png, write_png
from keystone.replay import stable_hash
from keystone.scene import Scene
from keystone.serialization import write_json_atomic
from keystone.texture import TextureData

GRID = 8

REPORT_SCHEMA = {
    "version": 10,
    "fields": {
        "image": ["path", "width", "height", "rgba_sha256", "png_sha256"],
        "stats": ["mean_rgb", "mean_luma", "content_pixels", "content_ratio", "content_bbox", "dominant_colors", "grid_luma"],
        "scene": ["camera", "node_count", "nodes", "shadows", "color", "post", "bloom", "sprites"],
        "shadows": ["enabled", "size"],
        "color": ["enabled"],
        "post": ["enabled"],
        "bloom": ["enabled"],
        "sprites": ["enabled"],
        "fx": ["alive", "drawn", "enabled"],
        "node": ["id", "name", "parent", "parent_id", "visible", "tags", "layer", "components", "world", "screen", "bbox", "triangles", "material"],
        "material": ["color", "specular", "shininess", "checker_scale", "metallic", "roughness", "emissive", "texture"],
        "texture": ["name", "width", "height", "sha256"],
        "ui": ["visible", "paused", "labels", "buttons"],
        "ui_label": ["text", "x", "y", "scale", "color"],
        "ui_button": ["label", "action", "rect", "selected", "hovered"],
        "diagnostics": ["hash", "schema"],
    },
    "notes": [
        "grid_luma is an 8x8 backward-compatible luminance summary.",
        "screen and bbox are top-down image coordinates; screen may be null behind the camera.",
        "hash covers image metadata, stats, projected nodes with identity/materials, shadows and ui when present, not visual quality.",
        "ui is null unless the human overlay was rendered; schema-2 added it.",
        "schema-3 adds material and texture metadata; schema-4 adds node id, tags, layer and components.",
        "schema-5 adds PBR material fields (metallic, roughness, emissive).",
        "schema-6 adds scene shadows metadata (enabled, size).",
        "schema-7 adds scene color metadata (sRGB pipeline enabled).",
        "schema-8 adds scene post metadata (post color-grade enabled).",
        "schema-9 adds scene bloom metadata (bloom glow enabled).",
        "schema-10 adds scene sprite metadata and top-level fx particle counts.",
        "schema-1/2/3 reports remain comparable; nodes are keyed by id when both reports are schema 4 or newer.",
        "ui labels and button rects are presentation metadata in top-left pixels.",
    ],
}


def _rows(pixels: bytes, width: int, height: int, flip: bool) -> list[bytes]:
    rows = [pixels[row * width * 4 : (row + 1) * width * 4] for row in range(height)]
    if flip:
        rows.reverse()
    return rows


def _stats(pixels: bytes, width: int, height: int, background: Vec3, flip: bool = True) -> dict:
    if len(pixels) != width * height * 4:
        raise ValueError(f"expected {width * height * 4} RGBA bytes, got {len(pixels)}")
    rows = _rows(pixels, width, height, flip)
    bg = (background.x * 255.0, background.y * 255.0, background.z * 255.0)
    total_r = total_g = total_b = total_luma = 0.0
    content = 0
    min_x, min_y, max_x, max_y = width, height, -1, -1
    bins: dict[tuple[int, int, int], int] = {}
    grid = [[0.0 for _ in range(GRID)] for _ in range(GRID)]
    for y, row in enumerate(rows):
        for x in range(width):
            offset = x * 4
            r, g, b = row[offset], row[offset + 1], row[offset + 2]
            luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
            total_r += r
            total_g += g
            total_b += b
            total_luma += luma
            if (r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2 > 144.0:
                content += 1
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)
            key = (r >> 4, g >> 4, b >> 4)
            bins[key] = bins.get(key, 0) + 1
            grid[min(GRID - 1, y * GRID // height)][min(GRID - 1, x * GRID // width)] += luma
    count = max(1, width * height)
    for gy in range(GRID):
        for gx in range(GRID):
            cells = ((height + GRID - 1) // GRID) * ((width + GRID - 1) // GRID)
            grid[gy][gx] = round(grid[gy][gx] / max(1, cells), 2)
    dominant = [
        {"rgb": [key[0] * 16 + 8, key[1] * 16 + 8, key[2] * 16 + 8], "pixels": count_bin}
        for key, count_bin in sorted(bins.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
    return {
        "mean_rgb": [round(total_r / count, 2), round(total_g / count, 2), round(total_b / count, 2)],
        "mean_luma": round(total_luma / count, 2),
        "content_pixels": content,
        "content_ratio": round(content / count, 4),
        "content_bbox": [min_x, min_y, max_x, max_y] if max_x >= 0 else None,
        "dominant_colors": dominant,
        "grid_luma": grid,
    }


def _material_report(material: object) -> dict | None:
    if not isinstance(material, Material):
        return None
    texture = material.texture if isinstance(material.texture, TextureData) else None
    metallic = getattr(material, "metallic", 0.0)
    roughness = getattr(material, "roughness", 0.7)
    emissive = getattr(material, "emissive", Vec3())
    if not isinstance(emissive, Vec3):
        emissive = Vec3()
    return {
        "color": [round(material.color.x, 3), round(material.color.y, 3), round(material.color.z, 3)],
        "specular": material.specular,
        "shininess": material.shininess,
        "checker_scale": material.checker_scale,
        "metallic": round(float(metallic), 3),
        "roughness": round(float(roughness), 3),
        "emissive": [round(emissive.x, 3), round(emissive.y, 3), round(emissive.z, 3)],
        "texture": (
            {
                "name": texture.name,
                "width": texture.width,
                "height": texture.height,
                "sha256": texture.sha256(),
            }
            if texture is not None
            else None
        ),
    }


def _node_report(scene: Scene, width: int, height: int) -> list[dict]:
    camera = scene.camera
    view_projection = camera.view_projection(width / height)
    nodes: list[dict] = []
    for node in scene.traverse():
        world = node.world_matrix()
        center = world.transform_point(Vec3())
        entry = {
            "id": node.id,
            "name": node.name,
            "parent": node.parent.name if node.parent else None,
            "parent_id": node.parent.id if node.parent else None,
            "visible": node.world_visible(),
            "tags": sorted(node.tags),
            "layer": node.layer,
            "components": sorted(component_type.__name__ for component_type in node.components),
            "world": [round(center.x, 3), round(center.y, 3), round(center.z, 3)],
            "screen": None,
            "bbox": None,
        }
        try:
            ndc = view_projection.project_point(center)
            if -1.0 <= ndc.z <= 1.0:
                entry["screen"] = [
                    round((ndc.x + 1.0) * 0.5 * width, 2),
                    round((1.0 - ndc.y) * 0.5 * height, 2),
                ]
        # hygiene: allow nodes on the projection plane to keep a null screen
        except ZeroDivisionError:
            pass
        material = _material_report(node.material)
        if material is not None:
            entry["material"] = material
        mesh = node.mesh
        if isinstance(mesh, MeshData):
            entry["triangles"] = mesh.triangle_count()
            low, high = mesh.bounds()
            corners = [
                world.transform_point(Vec3(x, y, z))
                for x in (low[0], high[0])
                for y in (low[1], high[1])
                for z in (low[2], high[2])
            ]
            projected = []
            for corner in corners:
                try:
                    ndc = view_projection.project_point(corner)
                    if -1.0 <= ndc.z <= 1.0:
                        projected.append(((ndc.x + 1.0) * 0.5 * width, (1.0 - ndc.y) * 0.5 * height))
                # hygiene: allow a corner on the projection plane; skip that corner
                except ZeroDivisionError:
                    continue
            if projected:
                xs = [point[0] for point in projected]
                ys = [point[1] for point in projected]
                entry["bbox"] = [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
        nodes.append(entry)
    return nodes


def analyze_frame(
    scene: Scene,
    pixels: bytes,
    width: int,
    height: int,
    image_path: str | Path | None = None,
    ui: dict | None = None,
    fx: dict | None = None,
) -> dict:
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    stats = _stats(pixels, width, height, scene.background)
    nodes = _node_report(scene, width, height)
    image = {
        "path": Path(image_path).as_posix() if image_path is not None else None,
        "width": width,
        "height": height,
        "rgba_sha256": hashlib.sha256(pixels).hexdigest(),
        "png_sha256": None,
    }
    if image_path is not None:
        image["png_sha256"] = hashlib.sha256(Path(image_path).read_bytes()).hexdigest()
    camera = scene.camera
    shadow = getattr(scene, "shadow", None)
    shadows = {
        "enabled": bool(getattr(shadow, "enabled", True)),
        "size": 1024 if bool(getattr(shadow, "enabled", True)) else 0,
    }
    color_setting = getattr(scene, "color", None)
    color = {"enabled": bool(getattr(color_setting, "enabled", True))}
    post_setting = getattr(scene, "post", None)
    post = {"enabled": bool(getattr(post_setting, "enabled", True))}
    bloom_setting = getattr(scene, "bloom", None)
    bloom = {"enabled": bool(getattr(bloom_setting, "enabled", True))}
    sprite_setting = getattr(scene, "sprite", None)
    sprites = {"enabled": bool(getattr(sprite_setting, "enabled", True))}
    if fx is None:
        fx = {"alive": 0, "drawn": 0, "enabled": sprites["enabled"]}
    else:
        fx = {
            "alive": int(fx.get("alive", 0)),
            "drawn": int(fx.get("drawn", 0)),
            "enabled": bool(fx.get("enabled", sprites["enabled"])),
        }
    report = {
        "schema": 10,
        "image": image,
        "stats": stats,
        "scene": {
            "camera": {
                "position": [round(camera.position.x, 3), round(camera.position.y, 3), round(camera.position.z, 3)],
                "yaw": round(camera.yaw, 4),
                "pitch": round(camera.pitch, 4),
                "fov_y": camera.fov_y,
                "near": camera.near,
                "far": camera.far,
            },
            "node_count": len(nodes),
            "nodes": nodes,
            "shadows": shadows,
            "color": color,
            "post": post,
            "bloom": bloom,
            "sprites": sprites,
        },
        "fx": fx,
        "ui": ui,
    }
    hashed = {"image": image, "stats": stats, "nodes": nodes, "shadows": shadows, "color": color, "post": post, "bloom": bloom, "sprites": sprites, "fx": fx}
    if ui is not None:
        hashed["ui"] = ui
    report["hash"] = stable_hash(hashed)
    return report


def _compare_ui(before: dict | None, after: dict | None) -> dict:
    empty = {"visible": False, "paused": False, "labels": [], "buttons": []}
    first = before or empty
    second = after or empty

    def label_map(ui: dict) -> dict[str, dict]:
        return {label["text"]: label for label in ui.get("labels", [])}

    def button_map(ui: dict) -> dict[str, dict]:
        return {button["action"]: button for button in ui.get("buttons", [])}

    first_labels = label_map(first)
    second_labels = label_map(second)
    first_buttons = button_map(first)
    second_buttons = button_map(second)
    shared_labels = set(first_labels) & set(second_labels)
    shared_buttons = set(first_buttons) & set(second_buttons)
    return {
        "same": first == second,
        "visible": {"before": first.get("visible"), "after": second.get("visible")},
        "paused": {"before": first.get("paused"), "after": second.get("paused")},
        "added_labels": sorted(set(second_labels) - set(first_labels)),
        "removed_labels": sorted(set(first_labels) - set(second_labels)),
        "moved_labels": sorted(text for text in shared_labels if first_labels[text] != second_labels[text]),
        "added_buttons": sorted(set(second_buttons) - set(first_buttons)),
        "removed_buttons": sorted(set(first_buttons) - set(second_buttons)),
        "changed_buttons": sorted(action for action in shared_buttons if first_buttons[action] != second_buttons[action]),
    }


def _shadows_of(report: dict) -> dict | None:
    scene = report.get("scene", {})
    shadows = scene.get("shadows") if isinstance(scene, dict) else None
    if isinstance(shadows, dict):
        return {
            "enabled": bool(shadows.get("enabled", True)),
            "size": int(shadows.get("size", 0)),
        }
    return None


def _color_of(report: dict) -> dict | None:
    scene = report.get("scene", {})
    color = scene.get("color") if isinstance(scene, dict) else None
    if isinstance(color, dict):
        return {"enabled": bool(color.get("enabled", True))}
    return None


def _post_of(report: dict) -> dict | None:
    scene = report.get("scene", {})
    post = scene.get("post") if isinstance(scene, dict) else None
    if isinstance(post, dict):
        return {"enabled": bool(post.get("enabled", True))}
    return None


def _bloom_of(report: dict) -> dict | None:
    scene = report.get("scene", {})
    bloom = scene.get("bloom") if isinstance(scene, dict) else None
    if isinstance(bloom, dict):
        return {"enabled": bool(bloom.get("enabled", True))}
    return None


def _sprites_of(report: dict) -> dict | None:
    scene = report.get("scene", {})
    sprites = scene.get("sprites") if isinstance(scene, dict) else None
    if isinstance(sprites, dict):
        return {"enabled": bool(sprites.get("enabled", True))}
    return None


def _fx_of(report: dict) -> dict | None:
    fx = report.get("fx")
    if isinstance(fx, dict):
        return {
            "alive": int(fx.get("alive", 0)),
            "drawn": int(fx.get("drawn", 0)),
            "enabled": bool(fx.get("enabled", True)),
        }
    return None


def compare_reports(before: dict, after: dict) -> dict:
    """Compare schema-1/2/3/4/5/6/7/8/9/10 frame reports for AI-driven regression checks."""
    if before.get("schema") not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10) or after.get("schema") not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
        raise ValueError("both reports must use schema 1, 2, 3, 4, 5, 6, 7, 8, 9 or 10")
    first_stats = before["stats"]
    second_stats = after["stats"]
    key = "id" if before.get("schema", 0) >= 4 and after.get("schema", 0) >= 4 else "name"
    first_nodes = {(node.get(key) or node["name"]): node for node in before["scene"]["nodes"]}
    second_nodes = {(node.get(key) or node["name"]): node for node in after["scene"]["nodes"]}
    changed = []
    for name in sorted(set(first_nodes) | set(second_nodes)):
        old = first_nodes.get(name)
        new = second_nodes.get(name)
        if old is None or new is None or (
            old.get("id"),
            old.get("name"),
            old.get("parent"),
            old.get("parent_id"),
            old.get("visible"),
            old.get("tags"),
            old.get("layer"),
            old.get("components"),
            old.get("screen"),
            old.get("bbox"),
            old.get("material"),
        ) != (
            new.get("id"),
            new.get("name"),
            new.get("parent"),
            new.get("parent_id"),
            new.get("visible"),
            new.get("tags"),
            new.get("layer"),
            new.get("components"),
            new.get("screen"),
            new.get("bbox"),
            new.get("material"),
        ):
            changed.append(name)
    ui_diff = _compare_ui(before.get("ui"), after.get("ui"))
    before_shadows = _shadows_of(before)
    after_shadows = _shadows_of(after)
    if before_shadows is None or after_shadows is None:
        same_shadows = True
        shown_before = before_shadows or {"enabled": True, "size": 1024}
        shown_after = after_shadows or {"enabled": True, "size": 1024}
    else:
        same_shadows = before_shadows == after_shadows
        shown_before = before_shadows
        shown_after = after_shadows
    before_color = _color_of(before)
    after_color = _color_of(after)
    if before_color is None or after_color is None:
        same_color = True
        color_before = before_color or {"enabled": True}
        color_after = after_color or {"enabled": True}
    else:
        same_color = before_color == after_color
        color_before = before_color
        color_after = after_color
    before_post = _post_of(before)
    after_post = _post_of(after)
    if before_post is None or after_post is None:
        same_post = True
        post_before = before_post or {"enabled": True}
        post_after = after_post or {"enabled": True}
    else:
        same_post = before_post == after_post
        post_before = before_post
        post_after = after_post
    before_bloom = _bloom_of(before)
    after_bloom = _bloom_of(after)
    if before_bloom is None or after_bloom is None:
        same_bloom = True
        bloom_before = before_bloom or {"enabled": True}
        bloom_after = after_bloom or {"enabled": True}
    else:
        same_bloom = before_bloom == after_bloom
        bloom_before = before_bloom
        bloom_after = after_bloom
    before_sprites = _sprites_of(before)
    after_sprites = _sprites_of(after)
    if before_sprites is None or after_sprites is None:
        same_sprites = True
        sprites_before = before_sprites or {"enabled": True}
        sprites_after = after_sprites or {"enabled": True}
    else:
        same_sprites = before_sprites == after_sprites
        sprites_before = before_sprites
        sprites_after = after_sprites
    before_fx = _fx_of(before)
    after_fx = _fx_of(after)
    if before_fx is None or after_fx is None:
        same_fx = True
        fx_before = before_fx or {"alive": 0, "drawn": 0, "enabled": True}
        fx_after = after_fx or {"alive": 0, "drawn": 0, "enabled": True}
    else:
        same_fx = before_fx == after_fx
        fx_before = before_fx
        fx_after = after_fx
    return {
        "schema": 10,
        "same_image": before["image"]["rgba_sha256"] == after["image"]["rgba_sha256"],
        "same_report": before.get("hash") == after.get("hash"),
        "same_ui": ui_diff["same"],
        "same_shadows": same_shadows,
        "shadows": {"before": shown_before, "after": shown_after},
        "same_color": same_color,
        "color": {"before": color_before, "after": color_after},
        "same_post": same_post,
        "post": {"before": post_before, "after": post_after},
        "same_bloom": same_bloom,
        "bloom": {"before": bloom_before, "after": bloom_after},
        "same_sprites": same_sprites,
        "sprites": {"before": sprites_before, "after": sprites_after},
        "same_fx": same_fx,
        "fx": {"before": fx_before, "after": fx_after},
        "mean_luma_delta": round(second_stats["mean_luma"] - first_stats["mean_luma"], 3),
        "content_ratio_delta": round(second_stats["content_ratio"] - first_stats["content_ratio"], 4),
        "content_bbox": {"before": first_stats["content_bbox"], "after": second_stats["content_bbox"]},
        "changed_nodes": changed,
        "added_nodes": sorted(set(second_nodes) - set(first_nodes)),
        "removed_nodes": sorted(set(first_nodes) - set(second_nodes)),
        "ui": ui_diff,
    }


def diff_images(before: str | Path, after: str | Path, output: str | Path, threshold: int = 8) -> dict:
    """Write a visual diff PNG and return changed-pixel statistics."""
    first_width, first_height, first = read_png(before)
    second_width, second_height, second = read_png(after)
    if (first_width, first_height) != (second_width, second_height):
        raise ValueError("images must have the same dimensions")
    width, height = first_width, first_height
    diff = bytearray(width * height * 4)
    changed = 0
    total_delta = 0
    max_delta = 0
    min_x, min_y, max_x, max_y = width, height, -1, -1
    count = width * height
    for pixel in range(count):
        offset = pixel * 4
        delta = max(
            abs(first[offset + channel] - second[offset + channel])
            for channel in range(3)
        )
        total_delta += delta
        max_delta = max(max_delta, delta)
        if delta > threshold:
            changed += 1
            x, y = pixel % width, pixel // width
            min_x, min_y = min(min_x, x), min(min_y, y)
            max_x, max_y = max(max_x, x), max(max_y, y)
            diff[offset : offset + 4] = bytes((255, 0, 0, 255))
        else:
            gray = first[offset] // 3
            diff[offset : offset + 4] = bytes((gray, gray, gray, 255))
    write_png(output, width, height, bytes(diff), flip_vertical=False)
    return {
        "width": width,
        "height": height,
        "changed_pixels": changed,
        "changed_ratio": round(changed / max(1, count), 4),
        "mean_delta": round(total_delta / max(1, count), 3),
        "max_delta": max_delta,
        "bbox": [min_x, min_y, max_x, max_y] if max_x >= 0 else None,
        "path": Path(output).as_posix(),
    }


def write_report(path: str | Path, report: dict) -> None:
    write_json_atomic(path, report, backup=False)
