"""AI observation/action adapters: seen, used, audited, verified and analyzed by AI.

This module is game-agnostic. It fuses the existing discovery, simulation
and frame-report contracts into one auditable observation, validates
LLM-produced action JSON into :class:`ActionState`, and keeps an
append-only audit trail with stable hashes.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keystone.headless import run_simulation
from keystone.input import ActionState
from keystone.plugin import GameModule, describe_game
from keystone.replay import stable_hash
from keystone.serialization import read_json, write_json_atomic


def parse_actions(payload: object) -> list[ActionState]:
    """Validate LLM-produced JSON into a list of ActionState.

    Accepts a list of action objects, or an object with an ``actions`` list.
    Each item must be a mapping; unknown keys raise. Numeric axes are
    clamped to [-1, 1] so a model cannot inject unbounded velocities.
    """
    if isinstance(payload, dict):
        payload = payload.get("actions", payload.get("frames", payload))
        if isinstance(payload, dict):
            raise TypeError("actions payload must hold a list of action objects")
    if not isinstance(payload, (list, tuple)):
        raise TypeError("actions payload must be a list of action objects")
    result: list[ActionState] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise TypeError(f"action {index} must be an object")
        allowed = {"forward", "right", "up", "look_yaw", "look_pitch", "pressed", "held", "pointer", "mouse_clicked"}
        unknown = set(item) - allowed
        if unknown:
            raise ValueError(f"action {index} has unknown keys: {sorted(unknown)}")
        clamped = dict(item)
        for axis in ("forward", "right", "up", "look_yaw", "look_pitch"):
            if axis in clamped:
                try:
                    value = float(clamped[axis])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"action {index} axis {axis!r} must be numeric") from exc
                if not math.isfinite(value):
                    raise ValueError(f"action {index} axis {axis!r} must be finite")
                clamped[axis] = max(-1.0, min(1.0, value))
        result.append(ActionState.from_dict(clamped))
    if not result:
        raise ValueError("actions payload must contain at least one action")
    return result


def observe(game: GameModule, frames: int = 60, actions: list[ActionState] | None = None, step: float = 1 / 60) -> dict[str, Any]:
    """Build one auditable AI observation: discovery + deterministic simulation.

    No window or OpenGL context is created. The result contains the game
    description, the simulation result, and a stable observation hash that
    an auditor can recompute from the same inputs.
    """
    if frames <= 0:
        raise ValueError("frames must be positive")
    build = getattr(game, "build_scene", None)
    if not callable(build):
        raise TypeError("game must expose build_scene()")
    state = random.getstate()
    try:
        random.seed(0)
        build()
        description = describe_game(game)
        simulation = run_simulation(game, frames=frames, actions=actions or [], step=step)
    finally:
        random.setstate(state)
    hashed = {"game": description.get("game"), "actions": simulation["actions"], "final": simulation["final"]}
    return {
        "schema": 1,
        "game": description.get("game"),
        "description": description,
        "simulation": simulation,
        "hash": stable_hash(hashed),
    }


def summarize_report(report: dict[str, Any], max_nodes: int = 24) -> dict[str, Any]:
    """Compress a schema-4/5 frame report into an LLM-sized observation summary."""
    if not isinstance(report, dict) or "stats" not in report or "scene" not in report:
        raise TypeError("report must be a frame report mapping")
    nodes = report["scene"].get("nodes", [])
    kept = []
    for node in nodes[:max_nodes]:
        material = node.get("material") or {}
        kept.append(
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "visible": node.get("visible"),
                "world": node.get("world"),
                "screen": node.get("screen"),
                "triangles": node.get("triangles"),
                "material": {
                    "color": material.get("color"),
                    "metallic": material.get("metallic", 0.0),
                    "roughness": material.get("roughness", 0.7),
                }
                if material
                else None,
            }
        )
    stats = report["stats"]
    return {
        "schema": 1,
        "hash": report.get("hash"),
        "image_sha": report.get("image", {}).get("rgba_sha256"),
        "mean_luma": stats.get("mean_luma"),
        "content_ratio": stats.get("content_ratio"),
        "node_count": report["scene"].get("node_count"),
        "truncated": len(nodes) > max_nodes,
        "nodes": kept,
        "ui": report.get("ui"),
    }


@dataclass
class AuditTrail:
    """Append-only, hash-chained audit log for AI-driven runs."""

    path: str | Path | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)
    _persisted_length: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.path is not None:
            path = Path(self.path)
            if path.exists():
                document = read_json(path)
                if not isinstance(document, dict) or document.get("schema") != 1:
                    raise ValueError("audit trail must use schema 1")
                entries = document.get("entries")
                if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
                    raise ValueError("audit trail entries must be a list of mappings")
                self.entries = list(entries)
        self._persisted_length = len(self.entries)

    def record(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not kind or not kind.strip():
            raise ValueError("audit kind must be a non-blank string")
        if not isinstance(payload, dict):
            raise TypeError("audit payload must be a mapping")
        previous = self.entries[-1]["hash"] if self.entries else "genesis"
        entry = {"index": len(self.entries), "kind": kind, "payload": payload, "previous": previous}
        entry["hash"] = stable_hash({"previous": previous, "kind": kind, "payload": payload})
        entries = [*self.entries, entry]
        if self.path is not None:
            write_json_atomic(self.path, {"schema": 1, "entries": entries}, backup=False)
        self.entries = entries
        self._persisted_length = len(entries)
        return entry

    def verify(self) -> bool:
        if len(self.entries) < self._persisted_length:
            return False
        previous = "genesis"
        for index, entry in enumerate(self.entries):
            if entry.get("index") != index or entry.get("previous") != previous:
                return False
            recomputed = stable_hash({"previous": previous, "kind": entry.get("kind"), "payload": entry.get("payload")})
            if recomputed != entry.get("hash"):
                return False
            previous = entry.get("hash", "")
        return True
