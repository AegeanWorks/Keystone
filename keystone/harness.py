"""Deterministic JSON harness for driving the expedition without a GPU."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from keystone.sim.world import MoveIntent, World

MAX_ACTIONS = 200
MAX_SECONDS = 120.0
FIXED_STEP = 1.0 / 60.0


def catalog() -> dict[str, Any]:
    """Describe every action and the state an agent can observe."""
    return {
        "ok": True,
        "actions": {
            "move": {
                "fields": {"forward": "float", "right": "float", "seconds": "float", "sprint": "bool"},
                "defaults": {"forward": 0.0, "right": 0.0, "seconds": 0.5, "sprint": False},
            },
            "turn": {
                "fields": {"yaw": "degrees", "pitch": "degrees"},
                "defaults": {"yaw": 0.0, "pitch": 0.0},
            },
            "interact": {"fields": {}},
            "rotate": {"fields": {}},
            "wait": {"fields": {"seconds": "float"}, "defaults": {"seconds": 0.5}},
        },
        "state_keys": [
            "seed", "time", "day_fraction", "mode", "player", "terrain", "dungeon",
            "near_entrance", "near_exit", "light_lock", "combat", "events",
        ],
        "limits": {"actions": MAX_ACTIONS, "seconds": MAX_SECONDS, "step": FIXED_STEP},
        "layouts": ["auto", "crypt", "weave"],
        "notes": [
            "Each run starts from one integer seed; identical seed and actions reproduce the same hash.",
            "Positions are world coordinates; mode is 'overworld' or 'dungeon'.",
            "auto chooses crypt on odd seeds and weave on even seeds; --layout forces one.",
            "Use interact near the portal to enter the crypt and near the exit rune to leave.",
            "Combat auto-fires at the nearest enemy; move to avoid contact damage and watch the wave.",
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


def apply_action(world: World, action: dict[str, Any]) -> None:
    """Validate and apply one catalogued action to the world."""
    name = action.get("action")
    if name == "move":
        seconds = _seconds(action)
        intent = MoveIntent(
            forward=_number(action, "forward", 0.0),
            right=_number(action, "right", 0.0),
            sprint=bool(action.get("sprint", False)),
        )
        for _ in range(round(seconds / FIXED_STEP)):
            world.step(FIXED_STEP, intent)
    elif name == "turn":
        world.step(
            0.0,
            MoveIntent(
                turn=math.radians(_number(action, "yaw", 0.0)),
                pitch=math.radians(_number(action, "pitch", 0.0)),
            ),
        )
    elif name == "interact":
        world.step(0.0, MoveIntent(interact=True))
    elif name == "rotate":
        if not world.rotate_mirror():
            raise ValueError("no mirror is within reach")
    elif name == "wait":
        for _ in range(round(_seconds(action) / FIXED_STEP)):
            world.step(FIXED_STEP)
    else:
        raise ValueError(f"unknown action '{name}'")


def run_actions(
    seed: int,
    actions: list[dict[str, Any]],
    size: int = 96,
    layout: str = "auto",
) -> dict[str, Any]:
    if not 0 <= int(seed) <= 0xFFFFFFFF:
        raise ValueError("seed must be between 0 and 4294967295")
    if len(actions) > MAX_ACTIONS:
        raise ValueError(f"at most {MAX_ACTIONS} actions are allowed")
    world = World(int(seed), size=size, layout=layout)
    total_seconds = 0.0
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise TypeError(f"action {index} must be an object")
        try:
            apply_action(world, action)
        except ValueError as exc:
            raise ValueError(f"action {index}: {exc}") from exc
        total_seconds += _number(action, "seconds", 0.0)
        if total_seconds > MAX_SECONDS:
            raise ValueError(f"actions exceed the {MAX_SECONDS:g} second budget")
    return {
        "ok": True,
        "seed": int(seed),
        "action_count": len(actions),
        "final": world.snapshot(),
        "hash": world.state_hash(),
    }


def selftest() -> dict[str, Any]:
    """Prove determinism, seed sensitivity, collision and portal transitions."""
    checks: list[str] = []
    actions = [
        {"action": "move", "forward": 1.0, "seconds": 0.5},
        {"action": "turn", "yaw": 45.0},
        {"action": "move", "forward": 1.0, "right": 0.25, "seconds": 0.5},
        {"action": "wait", "seconds": 0.25},
    ]
    first = run_actions(7, actions, size=32)
    second = run_actions(7, actions, size=32)
    if first["hash"] != second["hash"]:
        raise AssertionError("same seed and actions produced different hashes")
    checks.append("deterministic replay")
    if first["hash"] == run_actions(8, actions, size=32)["hash"]:
        raise AssertionError("different seeds produced the same hash")
    checks.append("seed sensitivity")

    world = World(7, size=32)
    world.light_lock.set_orientation(-1, 0, "\\")
    world.light_lock.set_orientation(-1, 2, "/")
    world.player.x = world.terrain.entrance[0]
    world.player.z = world.terrain.entrance[1]
    apply_action(world, {"action": "interact"})
    if world.mode != "dungeon":
        raise AssertionError("interact did not enter the dungeon")
    checks.append("portal entry")
    world.player.x = world.dungeon.exit[0] + 0.5
    world.player.z = world.dungeon.exit[1] + 0.5
    apply_action(world, {"action": "interact"})
    if world.mode != "overworld":
        raise AssertionError("interact did not leave the dungeon")
    checks.append("exit transition")

    try:
        run_actions(7, [{"action": "teleport"}])
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


def _seed_arg(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seed must be an integer") from exc
    if not 0 <= value <= 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("seed must be between 0 and 4294967295")
    return value


def _size_arg(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size must be an integer") from exc
    if value < 16:
        raise argparse.ArgumentTypeError("size must be at least 16")
    return value


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
    parser = argparse.ArgumentParser(prog="python -m keystone.harness", description="Drive Keystone headlessly.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="print the action and state schema")
    run = sub.add_parser("run", help="apply a JSON action list")
    run.add_argument("--seed", type=_seed_arg, default=7)
    run.add_argument("--actions", type=Path, required=True)
    run.add_argument("--size", type=_size_arg, default=96)
    run.add_argument("--layout", choices=("auto", "crypt", "weave"), default="auto")
    run.add_argument("--out", type=Path, default=None)
    sub.add_parser("selftest", help="verify determinism, collisions and transitions")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            print(json.dumps(catalog(), indent=2, sort_keys=True))
            return 0
        if args.command == "selftest":
            print(json.dumps(selftest(), indent=2, sort_keys=True))
            return 0
        result = run_actions(args.seed, _read_actions(args.actions), size=args.size, layout=args.layout)
        if args.out is not None:
            _write_json(args.out, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, TypeError, AssertionError) as exc:
        print("Keystone harness failed.", file=sys.stderr)
        print(f"Why: {exc}", file=sys.stderr)
        print("Fix: run `python -m keystone.harness catalog` and retry with a valid action list.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
