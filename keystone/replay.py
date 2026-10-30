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
