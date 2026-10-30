"""Deterministic JSON harness for the space mode."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from keystone.math3d import Vec3
from keystone.sim.world import MoveIntent
from keystone.space import GATE, SpaceWorld

MAX_ACTIONS = 200
FIXED_STEP = 1.0 / 60.0


def catalog() -> dict[str, Any]:
    return {
        "ok": True,
        "mode": "space",
        "actions": {
            "fly": {"fields": {"forward": "float", "right": "float", "up": "float", "seconds": "float", "sprint": "bool"}},
            "turn": {"fields": {"yaw": "degrees", "pitch": "degrees"}},
            "scan": {"fields": {}},
            "jump": {"fields": {}},
            "wait": {"fields": {"seconds": "float"}},
        },
        "state_keys": ["seed", "system", "ship", "bodies", "credits", "scanned", "total", "complete", "events"],
        "notes": [
            "Fly within 6 units of a body radius and use scan.",
            "The jump gate is at (0, 0, 60); fly within 12 units and use jump.",
            "The same seed and actions reproduce the same hash.",
        ],
    }


def _number(action: dict[str, Any], key: str, default: float) -> float:
    value = action.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"'{key}' must be a number")
    return float(value)


def _seconds(action: dict[str, Any]) -> float:
    value = _number(action, "seconds", 0.5)
    if not 0.0 <= value <= 10.0:
        raise ValueError("'seconds' must be between 0 and 10")
    return value


def apply_action(world: SpaceWorld, action: dict[str, Any]) -> None:
    name = action.get("action")
    if name == "fly":
        intent = MoveIntent(
            forward=_number(action, "forward", 0.0),
            right=_number(action, "right", 0.0),
            up=_number(action, "up", 0.0),
            sprint=bool(action.get("sprint", False)),
        )
        for _ in range(round(_seconds(action) / FIXED_STEP)):
            world.step(FIXED_STEP, intent)
    elif name == "turn":
        world.step(0.0, MoveIntent(turn=math.radians(_number(action, "yaw", 0.0)), pitch=math.radians(_number(action, "pitch", 0.0))))
    elif name == "scan":
        world.step(0.0, MoveIntent(scan=True))
    elif name == "jump":
        world.step(0.0, MoveIntent(jump=True))
    elif name == "wait":
        for _ in range(round(_seconds(action) / FIXED_STEP)):
            world.step(FIXED_STEP)
    else:
        raise ValueError(f"unknown action '{name}'")


def run_actions(seed: int, actions: list[dict[str, Any]]) -> dict[str, Any]:
    if not 0 <= int(seed) <= 0xFFFFFFFF:
        raise ValueError("seed must be between 0 and 4294967295")
    if len(actions) > MAX_ACTIONS:
        raise ValueError(f"at most {MAX_ACTIONS} actions are allowed")
    world = SpaceWorld(int(seed))
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise TypeError(f"action {index} must be an object")
        try:
            apply_action(world, action)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"action {index}: {exc}") from exc
    return {"ok": True, "seed": int(seed), "final": world.snapshot(), "hash": world.state_hash()}


def selftest() -> dict[str, Any]:
    actions = [
        {"action": "fly", "forward": 1.0, "seconds": 0.5},
        {"action": "turn", "yaw": 30.0},
        {"action": "wait", "seconds": 0.25},
    ]
    first = run_actions(7, actions)
    if first["hash"] != run_actions(7, actions)["hash"]:
        raise AssertionError("same seed and actions produced different hashes")
    checks = ["deterministic replay"]
    if first["hash"] == run_actions(8, actions)["hash"]:
        raise AssertionError("different seeds produced the same hash")
    checks.append("seed sensitivity")

    world = SpaceWorld(7)
    body = world.system.bodies[1]
    bx, by, bz = body.position(world.time)
    world.ship.position = Vec3(bx, by, bz)
    apply_action(world, {"action": "scan"})
    if not body.scanned:
        raise AssertionError("scan did not complete")
    checks.append("body scan")
    world.ship.position = GATE
    original = world.system_id
    apply_action(world, {"action": "jump"})
    if world.system_id == original:
        raise AssertionError("jump did not change system")
    checks.append("gate jump")

    try:
        run_actions(7, [{"action": "warp"}])
    except ValueError:
        checks.append("invalid action rejected")
    else:
        raise AssertionError("invalid action was accepted")
    return {"ok": True, "checks": checks}


def _read_actions(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read actions from {path}: {exc}") from exc
    if isinstance(payload, dict):
        payload = payload.get("actions")
    if not isinstance(payload, list):
        raise TypeError("actions file must hold a list or an object with an 'actions' list")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m keystone.space_harness", description="Drive Keystone space headlessly.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="print the action and state schema")
    run = sub.add_parser("run", help="apply a JSON action list")
    run.add_argument("--seed", type=int, default=7)
    run.add_argument("--actions", type=Path, required=True)
    run.add_argument("--out", type=Path, default=None)
    sub.add_parser("selftest", help="verify determinism, scan and jump")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            print(json.dumps(catalog(), indent=2, sort_keys=True))
            return 0
        if args.command == "selftest":
            print(json.dumps(selftest(), indent=2, sort_keys=True))
            return 0
        result = run_actions(args.seed, _read_actions(args.actions))
        if args.out is not None:
            _write_json(args.out, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, TypeError, AssertionError) as exc:
        print("Keystone space harness failed.", file=sys.stderr)
        print(f"Why: {exc}", file=sys.stderr)
        print("Fix: run `python -m keystone.space_harness catalog` and retry with a valid action list.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
