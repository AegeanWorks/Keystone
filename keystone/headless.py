"""Simulation without a window: JSON action scripts and deterministic traces."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Iterable
from pathlib import Path

from keystone.input import ActionState
from keystone.plugin import GameModule
from keystone.replay import FIXED_STEP, stable_hash
from keystone.scene import Scene


def load_actions(path: str | Path) -> list[ActionState]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read actions from {path}: {exc}") from exc
    if isinstance(payload, dict):
        if "seed" in payload or "step" in payload:
            raise ValueError("actions file looks like a command log; replay it with --replay")
        payload = payload.get("actions", payload.get("frames"))
    if not isinstance(payload, list):
        raise TypeError("actions file must hold a list or an object with an 'actions' list")
    actions: list[ActionState] = []
    for index, item in enumerate(payload):
        try:
            actions.append(ActionState.from_dict(item))
        except (AttributeError, TypeError, ValueError) as exc:
            raise type(exc)(f"actions[{index}]: {exc}") from exc
    return actions


def run_simulation(
    game: GameModule,
    frames: int = 1,
    actions: Iterable[ActionState] | None = None,
    step: float = FIXED_STEP,
    trace: bool = False,
) -> dict:
    """Advance a game without creating a window or OpenGL context."""
    if frames < 0:
        raise ValueError("frames cannot be negative")
    if step <= 0.0 or not math.isfinite(step):
        raise ValueError("step must be positive and finite")
    built = game.build_scene()
    if not isinstance(built, Scene):
        raise TypeError("GameModule.build_scene() must return a Scene")
    script = list(actions or [])
    snapshots: list[dict] = []
    used: list[dict] = []
    for index in range(frames):
        if script:
            action = script[index] if index < len(script) else script[-1].without_pressed()
        else:
            action = ActionState()
        used.append(action.to_dict())
        game.update(step, action)
        if trace:
            snapshots.append(copy.deepcopy(game.snapshot()))
    final = copy.deepcopy(game.snapshot())
    report = {
        "ok": True,
        "game": getattr(game, "name", "game"),
        "frames": frames,
        "step": step,
        "actions": used,
        "final": final,
        "hash": stable_hash(final),
    }
    if trace:
        report["trace"] = snapshots
    return report
