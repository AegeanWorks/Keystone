"""Deterministic action logs and stable state hashes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from keystone.input import ActionState
from keystone.serialization import read_json, write_json_atomic

FIXED_STEP = 1.0 / 60.0


def stable_hash(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


@dataclass
class CommandLog:
    seed: int
    step: float = FIXED_STEP
    frames: list[dict] = field(default_factory=list)

    def record(self, actions: ActionState) -> None:
        self.frames.append(actions.to_dict())

    def to_dict(self) -> dict:
        return {"seed": self.seed, "step": self.step, "frames": self.frames}

    @classmethod
    def from_dict(cls, data: dict) -> CommandLog:
        seed = int(data["seed"])
        step = float(data.get("step", FIXED_STEP))
        frames = list(data.get("frames", []))
        if step <= 0.0:
            raise ValueError("command-log step must be positive")
        return cls(seed, step, frames)

    def save(self, path: str | Path) -> None:
        write_json_atomic(path, self.to_dict())

    @classmethod
    def load(cls, path: str | Path) -> CommandLog:
        return cls.from_dict(read_json(path))

    def replay_actions(self) -> list[ActionState]:
        return [ActionState.from_dict(frame) for frame in self.frames]


def run_log(factory: object, log: CommandLog, trace: bool = False) -> dict:
    """Replay a command log on a fresh game without a window or GL context.

    The global RNG is seeded from ``log.seed`` so games drawing on it replay
    deterministically; games with their own RNG should seed it from the log.
    """
    if not callable(factory):
        raise TypeError("factory must be callable")
    if not isinstance(log, CommandLog):
        raise TypeError("log must be a CommandLog")
    import random as _random

    _random.seed(log.seed)
    game = factory()
    build = getattr(game, "build_scene", None)
    if not callable(build):
        raise TypeError("replayed game must expose build_scene()")
    build()
    update = getattr(game, "update", None)
    snapshot = getattr(game, "snapshot", None)
    if not callable(update) or not callable(snapshot):
        raise TypeError("replayed game must expose update() and snapshot()")
    actions = log.replay_actions()
    snapshots: list[dict] = []
    for action in actions:
        update(log.step, action)
        if trace:
            snapshots.append(snapshot())
    final = snapshot()
    report: dict = {
        "ok": True,
        "game": getattr(game, "name", "game"),
        "frames": len(actions),
        "step": log.step,
        "seed": log.seed,
        "final": final,
        "hash": stable_hash(final),
    }
    if trace:
        report["trace"] = snapshots
    return report


def verify_log(factory: object, log: CommandLog) -> dict:
    """Run one log twice from a factory and compare final hashes."""
    first = run_log(factory, log)
    second = run_log(factory, log)
    return {
        "ok": first["hash"] == second["hash"],
        "hash": first["hash"],
        "first": first["final"],
        "second": second["final"],
    }
