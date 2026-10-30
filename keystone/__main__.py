"""Command-line entry point for the Keystone demo."""

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


def _seed(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seed must be an integer") from exc
    if not 0 <= value <= 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("seed must be between 0 and 4294967295")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m keystone",
        description="Run the Keystone 3D demo window, or render frames headlessly.",
    )
    parser.add_argument("--headless", action="store_true", help="render without opening a window")
    parser.add_argument("--frames", type=_frames, default=0, help="frames to render (0 = until the window closes)")
    parser.add_argument("--size", type=_size, default=(960, 540), metavar="WxH", help="framebuffer size, e.g. 1280x720")
    parser.add_argument("--out", default=None, help="write a PNG after a headless run")
    parser.add_argument("--seed", type=_seed, default=7, help="expedition seed (default: 7)")
    parser.add_argument(
        "--layout",
        choices=("auto", "crypt", "weave"),
        default="auto",
        help="dungeon layout: auto (seed parity), crypt rooms or woven room chain (default: auto)",
    )
    parser.add_argument("--demo", action="store_true", help="run the original showcase scene instead of the expedition")
    args = parser.parse_args(argv)
    if args.out and not args.headless:
        parser.error("--out requires --headless")

    from keystone.app import Engine

    engine = None
    try:
        if args.demo:
            from keystone.demo import Demo

            experience = Demo()
            controls = None
            title = "Keystone | Showcase"
        else:
            from keystone.expedition import Expedition

            experience = Expedition(args.seed, layout=args.layout)
            controls = experience.handle_input
            title = f"Keystone | Expedition seed {args.seed} | {experience.world.layout}"
        engine = Engine(
            experience.scene,
            args.size[0],
            args.size[1],
            visible=not args.headless,
            msaa=0 if args.headless else 4,
            title=title,
        )
        max_frames = args.frames if args.frames else (1 if args.headless else 0)
        rendered = engine.run(
            update=experience.update,
            max_frames=max_frames,
            controls=controls,
            status=getattr(experience, "status", None),
        )
        if args.out:
            engine.screenshot(args.out)
        if args.headless:
            suffix = f" -> {args.out}" if args.out else ""
            world = getattr(experience, "world", None)
            mode = getattr(world, "mode", "demo")
            layout = getattr(world, "layout", "demo")
            seed = f" seed={args.seed}" if not args.demo else ""
            print(
                f"Rendered {rendered} frame(s) at {args.size[0]}x{args.size[1]}"
                f"{seed} mode={mode} layout={layout}{suffix}"
            )
        return 0
    except Exception as exc:  # noqa: BLE001 - a CLI must never leak a traceback (PRINCIPLE-011 R6)
        message = str(exc)
        print("Keystone could not start.", file=sys.stderr)
        if "Why:" in message and "Fix:" in message:
            print(message, file=sys.stderr)
        else:
            print(f"Why: {message}", file=sys.stderr)
            print(
                "Fix: install the pinned stack with `python -m pip install -r requirements.txt`, "
                "then retry with `python -m keystone --headless --frames 1 --out frame.png`.",
                file=sys.stderr,
            )
        return 1
    finally:
        if engine is not None:
            engine.close()


if __name__ == "__main__":
    raise SystemExit(main())
