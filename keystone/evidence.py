"""Deterministic capture routes and evidence diffs.

A route is a named, frame-indexed capture plan: a ``stage`` callback runs
before every frame (move the camera, toggle a setting, spawn a prop), and
each checkpoint writes a PNG plus a frame report. Because the engine steps
one fixed tick per frame when headless, two runs of one route over one game
produce byte-identical evidence, which is what makes a route usable as a
proof artefact for an AI-authored change.

``diff_evidence`` compares two route summaries per checkpoint, so a change
can be reported as "these images moved, these counters moved" instead of
"trust me".

The module is engine-agnostic: it drives anything with ``run(frames)``,
``capture(image, report)`` and a ``scene`` attribute, which the real
``keystone.app.Engine`` satisfies.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from keystone.replay import stable_hash
from keystone.scene import Scene
from keystone.serialization import read_json, write_json_atomic

__all__ = ["Checkpoint", "Route", "capture_route", "diff_evidence", "write_evidence"]

EVIDENCE_SCHEMA = 1

RENDER_FIELDS = (
    "draw_calls",
    "triangles",
    "instanced_calls",
    "instances",
    "shadow_calls",
    "sprite_calls",
    "sprites",
    "overlay_calls",
    "overlay_triangles",
    "overlay_nodes",
    "culled_nodes",
)

#: Frame-statistic fields compared by ``diff_evidence``.
STAT_FIELDS = ("mean_luma", "content_ratio", "content_pixels")


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """One frame to capture, under a label that survives report diffs."""

    frame: int
    label: str

    def __post_init__(self) -> None:
        if isinstance(self.frame, bool) or not isinstance(self.frame, int) or self.frame < 1:
            raise ValueError("checkpoint frame must be a positive integer")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("checkpoint label must be a non-blank string")


@dataclass(frozen=True, slots=True)
class Route:
    """A deterministic capture plan over one engine session."""

    name: str = "route"
    frames: int = 1
    checkpoints: tuple[Checkpoint, ...] = ()
    stage: Callable[[int, Scene], None] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("route name must be a non-blank string")
        if isinstance(self.frames, bool) or not isinstance(self.frames, int) or self.frames < 1:
            raise ValueError("route frames must be a positive integer")
        points = tuple(self.checkpoints)
        seen: set[str] = set()
        previous = 0
        for point in points:
            if not isinstance(point, Checkpoint):
                raise TypeError("route checkpoints must be Checkpoint instances")
            if point.frame <= previous:
                raise ValueError("route checkpoints must be sorted by increasing frame")
            if point.frame > self.frames:
                raise ValueError(f"checkpoint {point.label!r} is past the route's last frame")
            if point.label in seen:
                raise ValueError(f"route has duplicate checkpoint label {point.label!r}")
            seen.add(point.label)
            previous = point.frame
        object.__setattr__(self, "checkpoints", points)
        if self.stage is not None and not callable(self.stage):
            raise TypeError("route stage must be callable or None")

    def frame_numbers(self) -> tuple[int, ...]:
        return tuple(point.frame for point in self.checkpoints)


def _slug(label: str) -> str:
    cleaned = "".join(character if character.isalnum() else "-" for character in label.lower())
    return "-".join(part for part in cleaned.split("-") if part) or "checkpoint"


def _engine_error(engine: object) -> None:
    for attribute in ("run", "capture", "scene"):
        if not hasattr(engine, attribute):
            raise TypeError("capture_route needs an engine with run(), capture() and scene")


def _render_snapshot(engine: object) -> dict[str, int]:
    stats = getattr(getattr(engine, "renderer", None), "last_stats", {})
    if not isinstance(stats, dict):
        return {}
    return {field: int(stats[field]) for field in RENDER_FIELDS if field in stats}


def capture_route(engine: object, route: Route, directory: str | Path) -> dict:
    """Run ``route`` on ``engine`` and write one PNG and report per checkpoint."""
    if not isinstance(route, Route):
        raise TypeError("capture_route needs a Route")
    _engine_error(engine)
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    points = {point.frame: point for point in route.checkpoints}
    samples: list[dict] = []
    frames_run = 0
    for frame in range(1, route.frames + 1):
        if route.stage is not None:
            try:
                route.stage(frame, engine.scene)
            except Exception as exc:
                raise RuntimeError(f"route {route.name!r} stage failed at frame {frame}") from exc
        stepped = int(engine.run(1))
        frames_run += stepped
        if not stepped:
            break
        point = points.get(frame)
        if point is None:
            continue
        stem = f"{frame:04d}-{_slug(point.label)}"
        image = target / f"{stem}.png"
        report_path = target / f"{stem}.json"
        engine.capture(image, report_path)
        report = read_json(report_path)
        if not isinstance(report, dict) or not isinstance(report.get("stats"), dict):
            raise TypeError(f"frame report for {point.label!r} is missing stats")
        image_block = report.get("image", {})
        samples.append(
            {
                "frame": frame,
                "label": point.label,
                "image": image.name,
                "report": report_path.name,
                "image_sha256": image_block.get("png_sha256"),
                "stats": report["stats"],
                "render": _render_snapshot(engine),
            }
        )
    summary = {
        "schema": EVIDENCE_SCHEMA,
        "route": {
            "name": route.name,
            "frames": route.frames,
            "checkpoints": [{"frame": point.frame, "label": point.label} for point in route.checkpoints],
        },
        "frames_run": frames_run,
        "checkpoints": samples,
    }
    summary["route_hash"] = stable_hash(
        {
            "route": route.name,
            "frames_run": frames_run,
            "checkpoints": [
                {key: sample[key] for key in ("label", "frame", "image_sha256", "stats", "render")}
                for sample in samples
            ],
        }
    )
    return summary


def write_evidence(path: str | Path, summary: dict) -> None:
    """Write a route summary atomically, with the project's usual ``.bak``."""
    if not isinstance(summary, dict):
        raise TypeError("evidence summary must be a mapping")
    write_json_atomic(path, summary)


def _delta(before: object, after: object) -> float | None:
    left = getattr(before, "real", before)
    right = getattr(after, "real", after)
    if isinstance(left, bool) or isinstance(right, bool):
        return None
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return None
    if not math.isfinite(left) or not math.isfinite(right):
        return None
    return round(float(right) - float(left), 6)


def diff_evidence(before: dict, after: dict) -> dict:
    """Compare two route summaries checkpoint by checkpoint.

    Checkpoints are matched by label. A label present on only one side is
    reported as ``missing`` (before) or ``added`` (after), because a renamed
    checkpoint is a real difference for an evidence trail.
    """
    for name, payload in (("before", before), ("after", after)):
        if not isinstance(payload, dict) or not isinstance(payload.get("checkpoints"), list):
            raise TypeError(f"{name} evidence needs a 'checkpoints' list")
    old = {sample["label"]: sample for sample in before["checkpoints"]}
    new = {sample["label"]: sample for sample in after["checkpoints"]}
    comparisons: list[dict] = []
    changed = bool(set(old) - set(new)) or bool(set(new) - set(old))
    for label in old.keys() & new.keys():
        first, second = old[label], new[label]
        comparison: dict = {
            "label": label,
            "image_changed": first.get("image_sha256") != second.get("image_sha256"),
        }
        for field in STAT_FIELDS:
            comparison[f"{field}_delta"] = _delta(first["stats"].get(field), second["stats"].get(field))
        for field in ("draw_calls", "triangles", "overlay_calls"):
            comparison[f"{field}_delta"] = _delta(
                first.get("render", {}).get(field), second.get("render", {}).get(field)
            )
        comparisons.append(comparison)
        if comparison["image_changed"] or any(
            isinstance(value, (int, float)) and value != 0 for value in comparison.values()
        ):
            changed = True
    return {
        "schema": EVIDENCE_SCHEMA,
        "route": before.get("route", {}).get("name"),
        "changed": changed,
        "missing": sorted(set(old) - set(new)),
        "added": sorted(set(new) - set(old)),
        "checkpoints": sorted(comparisons, key=lambda item: item["label"]),
    }
