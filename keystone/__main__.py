"""Command-line entry point for the game-agnostic Keystone engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _size(text: str) -> tuple[int, int]:
    try:
        width, height = text.lower().split("x")
        values = int(width), int(height)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size must look like 960x540") from exc
    if values[0] <= 0 or values[1] <= 0:
        raise argparse.ArgumentTypeError("size components must be positive")
    return values


def _frames(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("frame count must be an integer") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("frame count cannot be negative")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m keystone",
        description="Run a Keystone game module from 'package.module:Factory'.",
    )
    parser.add_argument("--game", default="keystone.samples:CubeDemo", help="game factory spec")
    parser.add_argument("--describe", action="store_true", help="print the game capability/action/snapshot schema")
    parser.add_argument("--headless", action="store_true", help="render without opening a window")
    parser.add_argument("--simulate", action="store_true", help="advance the game without OpenGL")
    parser.add_argument("--actions", type=Path, default=None, help="JSON action list for --simulate")
    parser.add_argument("--trace", action="store_true", help="include per-frame snapshots in simulation output")
    parser.add_argument("--frames", type=_frames, default=0, help="frame count (default: 1 headless, or until close)")
    parser.add_argument("--size", type=_size, default=(960, 540), metavar="WxH", help="framebuffer size, e.g. 1280x720")
    parser.add_argument("--out", type=Path, default=None, help="PNG for rendering; JSON report for --simulate")
    parser.add_argument("--report", type=Path, default=None, help="machine-readable frame report (requires --headless)")
    args = parser.parse_args(argv)
    if args.describe and (args.headless or args.simulate or args.out or args.report or args.actions or args.trace):
        parser.error("--describe is a standalone discovery command")
    if args.headless and args.simulate:
        parser.error("--headless and --simulate are mutually exclusive")
    if args.simulate and args.report:
        parser.error("--report requires the rendered --headless path")
    if args.report and not args.headless:
        parser.error("--report requires --headless")
    if args.out and not (args.headless or args.simulate):
        parser.error("--out requires --headless or --simulate")
    if args.actions and not args.simulate:
        parser.error("--actions requires --simulate")
    if args.trace and not args.simulate:
        parser.error("--trace requires --simulate")

    from keystone.plugin import describe_game, load_game

    engine = None
    try:
        game = load_game(args.game)
        if args.describe:
            print(json.dumps(describe_game(game), indent=2, sort_keys=True))
            return 0
        if args.simulate:
            from keystone.headless import load_actions, run_simulation
            from keystone.serialization import write_json_atomic

            actions = load_actions(args.actions) if args.actions else []
            frames = args.frames if args.frames else (len(actions) or 1)
            result = run_simulation(game, frames, actions, trace=args.trace)
            if args.out:
                write_json_atomic(args.out, result)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        from keystone.app import Engine

        engine = Engine(
            game,
            args.size[0],
            args.size[1],
            visible=not args.headless,
            msaa=0 if args.headless else 4,
            title=f"Keystone | {getattr(game, 'name', 'game')}",
        )
        rendered = engine.run(max_frames=args.frames if args.frames else (1 if args.headless else 0))
        if args.out or args.report:
            engine.capture(args.out, args.report)
        if args.headless:
            suffix = f" -> {args.out}" if args.out else ""
            report = f" report={args.report}" if args.report else ""
            print(
                f"Rendered {rendered} frame(s) at {args.size[0]}x{args.size[1]} "
                f"game={getattr(game, 'name', args.game)}{suffix}{report}"
            )
        return 0
    except Exception as exc:  # noqa: BLE001 - a CLI must never leak a traceback
        print("Keystone could not start.", file=sys.stderr)
        message = str(exc)
        if "Why:" in message and "Fix:" in message:
            print(message, file=sys.stderr)
        else:
            print(f"Why: {message}", file=sys.stderr)
            print(
                "Fix: pass a valid 'package.module:Factory' with build_scene, update, "
                "snapshot, actions and status methods.",
                file=sys.stderr,
            )
        return 1
    finally:
        if engine is not None:
            engine.close()


if __name__ == "__main__":
    raise SystemExit(main())
