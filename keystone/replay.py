"""Deterministic action logs and stable state hashes."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from keystone.input import ActionState
from keystone.serialization import read_json, write_json_atomic

FIXED_STEP = 1.0 / 60.0


def _canonical_hash_value(value: object) -> object:
    if isinstance(value, float) and value == 0.0:
        return 0.0
    if isinstance(value, dict):
        return {key: _canonical_hash_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_hash_value(item) for item in value]
    return value


def stable_hash(payload: object) -> str:
    """Hash a JSON-safe payload deterministically; reject process-local values."""
    try:
        text = json.dumps(
            _canonical_hash_value(payload),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise type(exc)(f"stable_hash requires JSON-safe finite values: {exc}") from exc
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


@dataclass
class CommandLog:
    seed: int
    step: float = FIXED_STEP
    frames: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("command-log seed must be an integer")
        if isinstance(self.step, bool) or not isinstance(self.step, (int, float)):
            raise TypeError("command-log step must be a real number")
        self.step = float(self.step)
        if not math.isfinite(self.step) or self.step <= 0.0:
            raise ValueError("command-log step must be a positive finite number")
        if not isinstance(self.frames, list):
            raise TypeError("command-log frames must be a list")
        if any(not isinstance(frame, dict) for frame in self.frames):
            raise TypeError("command-log frames must be mappings")

    def record(self, actions: ActionState) -> None:
        self.frames.append(actions.to_dict())

    def to_dict(self) -> dict:
        return {"seed": self.seed, "step": self.step, "frames": list(self.frames)}

    @classmethod
    def from_dict(cls, data: dict) -> CommandLog:
        seed_raw = data["seed"]
        if isinstance(seed_raw, bool) or not isinstance(seed_raw, int):
            raise TypeError("command-log seed must be an integer")
        step = float(data.get("step", FIXED_STEP))
        if not math.isfinite(step) or step <= 0.0:
            raise ValueError("command-log step must be positive")
        frames_raw = data.get("frames", [])
        if not isinstance(frames_raw, (list, tuple)):
            raise TypeError("command-log frames must be a list")
        return cls(seed_raw, step, list(frames_raw))

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

    state = _random.getstate()
    try:
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
    finally:
        _random.setstate(state)
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
