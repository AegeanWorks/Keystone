"""Machine-readable frame reports for AI and headless UI analysis."""

from __future__ import annotations

import hashlib
from pathlib import Path

from keystone.geometry import MeshData
from keystone.math3d import Vec3
from keystone.replay import stable_hash
from keystone.scene import Scene
from keystone.serialization import write_json_atomic

GRID = 8

REPORT_SCHEMA = {
    "version": 1,
    "fields": {
        "image": ["path", "width", "height", "rgba_sha256", "png_sha256"],
        "stats": ["mean_rgb", "mean_luma", "content_pixels", "content_ratio", "content_bbox", "dominant_colors", "grid_luma"],
        "scene": ["camera", "node_count", "nodes"],
        "node": ["name", "parent", "visible", "world", "screen", "bbox", "triangles"],
        "diagnostics": ["hash", "schema"],
    },
    "notes": [
        "grid_luma is an 8x8 backward-compatible luminance summary.",
        "screen and bbox are top-down image coordinates; screen may be null behind the camera.",
        "hash covers image metadata, stats and projected nodes, not visual quality.",
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


def _node_report(scene: Scene, width: int, height: int) -> list[dict]:
    camera = scene.camera
    view_projection = camera.view_projection(width / height)
    nodes: list[dict] = []
    for node in scene.traverse():
        world = node.world_matrix()
        center = world.transform_point(Vec3())
        entry = {
            "name": node.name,
            "parent": node.parent.name if node.parent else None,
            "visible": node.world_visible(),
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
        except ZeroDivisionError:
            continue
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
    report = {
        "schema": 1,
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
        },
    }
    report["hash"] = stable_hash({"image": image, "stats": stats, "nodes": nodes})
    return report


def compare_reports(before: dict, after: dict) -> dict:
    """Compare two schema-1 frame reports for AI-driven visual regression."""
    if before.get("schema") != 1 or after.get("schema") != 1:
        raise ValueError("both reports must use schema 1")
    first_stats = before["stats"]
    second_stats = after["stats"]
    first_nodes = {node["name"]: node for node in before["scene"]["nodes"]}
    second_nodes = {node["name"]: node for node in after["scene"]["nodes"]}
    changed = []
    for name in sorted(set(first_nodes) | set(second_nodes)):
        old = first_nodes.get(name)
        new = second_nodes.get(name)
        if old is None or new is None or (old.get("screen"), old.get("bbox"), old.get("visible")) != (
            new.get("screen"),
            new.get("bbox"),
            new.get("visible"),
        ):
            changed.append(name)
    return {
        "schema": 1,
        "same_image": before["image"]["rgba_sha256"] == after["image"]["rgba_sha256"],
        "same_report": before.get("hash") == after.get("hash"),
        "mean_luma_delta": round(second_stats["mean_luma"] - first_stats["mean_luma"], 3),
        "content_ratio_delta": round(second_stats["content_ratio"] - first_stats["content_ratio"], 4),
        "content_bbox": {"before": first_stats["content_bbox"], "after": second_stats["content_bbox"]},
        "changed_nodes": changed,
        "added_nodes": sorted(set(second_nodes) - set(first_nodes)),
        "removed_nodes": sorted(set(first_nodes) - set(second_nodes)),
    }


def write_report(path: str | Path, report: dict) -> None:
    write_json_atomic(path, report, backup=False)
