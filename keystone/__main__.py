"""Command-line entry point for the game-agnostic Keystone engine."""

from __future__ import annotations

import argparse
import sys


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
    parser.add_argument(
        "--game",
        default="keystone.samples:CubeDemo",
        help="game factory spec (default: keystone.samples:CubeDemo)",
    )
    parser.add_argument("--headless", action="store_true", help="render without opening a window")
    parser.add_argument("--frames", type=_frames, default=0, help="frames to render (0 = until the window closes)")
    parser.add_argument("--size", type=_size, default=(960, 540), metavar="WxH", help="framebuffer size, e.g. 1280x720")
    parser.add_argument("--out", default=None, help="write a PNG after a headless run")
    args = parser.parse_args(argv)
    if args.out and not args.headless:
        parser.error("--out requires --headless")

    from keystone.app import Engine
    from keystone.plugin import load_game

    engine = None
    try:
        game = load_game(args.game)
        engine = Engine(
            game,
            args.size[0],
            args.size[1],
            visible=not args.headless,
            msaa=0 if args.headless else 4,
            title=f"Keystone | {getattr(game, 'name', 'game')}",
        )
        rendered = engine.run(max_frames=args.frames if args.frames else (1 if args.headless else 0))
        if args.out:
            engine.screenshot(args.out)
        if args.headless:
            suffix = f" -> {args.out}" if args.out else ""
            print(
                f"Rendered {rendered} frame(s) at {args.size[0]}x{args.size[1]} "
                f"game={getattr(game, 'name', args.game)}{suffix}"
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
