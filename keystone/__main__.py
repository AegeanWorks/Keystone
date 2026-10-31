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


def _hash(text: str) -> str:
    value = text.lower()
    if len(value) != 32 or any(character not in "0123456789abcdef" for character in value):
        raise argparse.ArgumentTypeError("hash must be 32 hexadecimal characters")
    return value


def _port(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 0 <= value <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
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
    parser.add_argument("--verify-determinism", action="store_true", help="run a scenario twice and compare hashes")
    parser.add_argument("--expect-hash", type=_hash, default=None, help="assert the final scenario hash")
    parser.add_argument("--compare-baseline", type=Path, default=None, help="compare the current report with a baseline report")
    parser.add_argument("--diff-out", type=Path, default=None, help="write a visual pixel-diff PNG with --compare-baseline")
    parser.add_argument("--actions", type=Path, default=None, help="JSON action list for --simulate/--verify-determinism")
    parser.add_argument("--trace", action="store_true", help="include per-frame snapshots in simulation output")
    parser.add_argument("--frames", type=_frames, default=0, help="frame count (default: 1 headless, or until close)")
    parser.add_argument("--size", type=_size, default=(960, 540), metavar="WxH", help="framebuffer size, e.g. 1280x720")
    parser.add_argument("--ui", action="store_true", help="draw the human HUD/help overlay (default: windowed only)")
    parser.add_argument("--no-ui", action="store_true", help="disable the human overlay")
    parser.add_argument("--start-paused", action="store_true", help="start a rendered run with gameplay paused")
    parser.add_argument("--serve", action="store_true", help="serve the local JSON API and WebGL web console")
    parser.add_argument("--host", default=None, help="web console bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=_port, default=None, help="web console port (default: 8000; 0 picks a free port)")
    parser.add_argument("--out", type=Path, default=None, help="PNG for rendering; JSON report for --simulate")
    parser.add_argument("--report", type=Path, default=None, help="machine-readable frame report (requires --headless)")
    args = parser.parse_args(argv)
    if args.serve and (
        args.describe or args.headless or args.simulate or args.verify_determinism or args.expect_hash
        or args.compare_baseline or args.diff_out or args.actions or args.trace or args.ui or args.no_ui
        or args.start_paused or args.out or args.report
    ):
        parser.error("--serve is a standalone web-console command")
    if (args.host is not None or args.port is not None) and not args.serve:
        parser.error("--host and --port require --serve")
    if args.describe and (
        args.headless or args.simulate or args.verify_determinism or args.expect_hash
        or args.compare_baseline or args.out or args.report or args.actions or args.trace
        or args.ui or args.no_ui or args.start_paused
    ):
        parser.error("--describe is a standalone discovery command")
    if args.headless and args.simulate:
        parser.error("--headless and --simulate are mutually exclusive")
    if args.ui and args.no_ui:
        parser.error("--ui and --no-ui are mutually exclusive")
    if (args.ui or args.no_ui) and (args.describe or args.simulate or args.verify_determinism):
        parser.error("--ui/--no-ui apply to rendered runs, not discovery or simulation commands")
    if args.start_paused and (args.simulate or args.verify_determinism):
        parser.error("--start-paused applies to rendered runs, not simulation commands")
    if args.verify_determinism and (args.headless or args.simulate or args.report or args.compare_baseline):
        parser.error("--verify-determinism is a standalone no-GL command")
    if args.expect_hash and not (args.simulate or args.verify_determinism):
        parser.error("--expect-hash requires --simulate or --verify-determinism")
    if args.simulate and args.report:
        parser.error("--report requires the rendered --headless path")
    if args.report and not args.headless:
        parser.error("--report requires --headless")
    if args.compare_baseline and not (args.headless and args.report):
        parser.error("--compare-baseline requires --headless and --report")
    if args.diff_out and not args.compare_baseline:
        parser.error("--diff-out requires --compare-baseline")
    if args.out and not (args.headless or args.simulate or args.verify_determinism):
        parser.error("--out requires --headless, --simulate or --verify-determinism")
    if args.actions and not (args.simulate or args.verify_determinism):
        parser.error("--actions requires --simulate or --verify-determinism")
    if args.trace and not args.simulate:
        parser.error("--trace requires --simulate")

    from keystone.plugin import describe_game, load_game

    engine = None
    try:
        game = load_game(args.game)
        if args.serve:
            from keystone.web import serve

            return serve(game, args.host or "127.0.0.1", args.port if args.port is not None else 8000)
        if args.describe:
            print(json.dumps(describe_game(game), indent=2, sort_keys=True))
            return 0
        if args.verify_determinism:
            from keystone.headless import load_actions
            from keystone.serialization import write_json_atomic
            from keystone.testing import verify_determinism

            actions = load_actions(args.actions) if args.actions else []
            result = verify_determinism(lambda: load_game(args.game), actions, frames=args.frames or None)
            if args.expect_hash:
                result["expected_hash"] = args.expect_hash
                result["ok"] = result["ok"] and result["hash"] == args.expect_hash
            if args.out:
                write_json_atomic(args.out, result)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["ok"] else 1
        if args.simulate:
            from keystone.headless import load_actions, run_simulation
            from keystone.serialization import write_json_atomic

            actions = load_actions(args.actions) if args.actions else []
            frames = args.frames if args.frames else (len(actions) or 1)
            result = run_simulation(game, frames, actions, trace=args.trace)
            if args.expect_hash:
                result["expected_hash"] = args.expect_hash
                result["ok"] = result["hash"] == args.expect_hash
            if args.out:
                write_json_atomic(args.out, result)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["ok"] else 1

        from keystone.app import Engine

        engine = Engine(
            game,
            args.size[0],
            args.size[1],
            visible=not args.headless,
            msaa=0 if args.headless else 4,
            title=f"Keystone | {getattr(game, 'name', 'game')}",
            ui=args.ui or (not args.headless and not args.no_ui),
        )
        if args.start_paused:
            engine.toggle_pause()
        rendered = engine.run(max_frames=args.frames if args.frames else (1 if args.headless else 0))
        if args.out or args.report:
            engine.capture(args.out, args.report)
        if args.compare_baseline:
            from keystone.analysis import compare_reports, diff_images
            from keystone.serialization import read_json

            baseline = read_json(args.compare_baseline)
            current = read_json(args.report)
            diff = compare_reports(baseline, current)
            pixel_diff = None
            if args.diff_out:
                baseline_image = baseline.get("image", {}).get("path")
                current_image = current.get("image", {}).get("path")
                if not baseline_image or not current_image:
                    raise ValueError("baseline and current reports must both contain image paths for --diff-out")
                baseline_png = Path(baseline_image)
                if not baseline_png.is_absolute() and not baseline_png.exists():
                    baseline_png = Path(args.compare_baseline).parent / baseline_png
                current_png = Path(current_image)
                if not current_png.is_absolute() and not current_png.exists():
                    current_png = Path(args.report).parent / current_png
                pixel_diff = diff_images(baseline_png, current_png, args.diff_out)
            print(
                json.dumps(
                    {
                        "ok": diff["same_image"],
                        "baseline": str(args.compare_baseline),
                        "current": str(args.report),
                        "diff": diff,
                        "pixel_diff": pixel_diff,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0 if diff["same_image"] else 1
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
