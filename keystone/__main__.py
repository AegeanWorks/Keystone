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


def _seed(text: str) -> int:
    try:
        return int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seed must be an integer") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m keystone",
        description="Run a Keystone game module from 'package.module:Factory'.",
    )
    parser.add_argument("--game", default="keystone.samples:CubeDemo", help="game factory spec")
    parser.add_argument("--new", type=Path, default=None, metavar="DIR", help="scaffold a new Keystone game project")
    parser.add_argument("--project", type=Path, default=None, metavar="PATH", help="open a keystone.json project directory or file")
    parser.add_argument("--name", default=None, help="project name for --new (default: directory name)")
    parser.add_argument("--force", action="store_true", help="allow --new to write into a non-empty directory")
    parser.add_argument("--describe", action="store_true", help="print the game capability/action/snapshot schema")
    parser.add_argument("--headless", action="store_true", help="render without opening a window")
    parser.add_argument("--simulate", action="store_true", help="advance the game without OpenGL")
    parser.add_argument("--verify-determinism", action="store_true", help="run a scenario twice and compare hashes")
    parser.add_argument("--expect-hash", type=_hash, default=None, help="assert the final scenario hash")
    parser.add_argument("--compare-baseline", type=Path, default=None, help="compare the current report with a baseline report")
    parser.add_argument("--diff-out", type=Path, default=None, help="write a visual pixel-diff PNG with --compare-baseline")
    parser.add_argument("--actions", type=Path, default=None, help="JSON action list for --simulate/--verify-determinism")
    parser.add_argument("--replay", type=Path, default=None, help="replay a CommandLog JSON without OpenGL")
    parser.add_argument("--playtest", action="store_true", help="run a seeded bot policy without OpenGL")
    parser.add_argument("--policy", choices=("random", "greedy", "scripted"), default="random",
                        help="bot policy for --playtest (default: random)")
    parser.add_argument("--seed", type=_seed, default=0, help="bot seed for --playtest (default: 0)")
    parser.add_argument("--script", type=Path, default=None, help="JSON action list for the scripted --playtest policy")
    parser.add_argument("--transcript-out", type=Path, default=None, help="write the bot transcript JSON for --playtest")
    parser.add_argument("--trace", action="store_true", help="include per-frame snapshots in simulation output")
    parser.add_argument(
        "--frames",
        type=_frames,
        default=0,
        help="frame count (default: 1 for --headless, action count for --simulate, 120 for --playtest, unlimited for windowed)",
    )
    parser.add_argument("--size", type=_size, default=(960, 540), metavar="WxH", help="framebuffer size, e.g. 1280x720")
    parser.add_argument("--ui", action="store_true", help="draw the human HUD/help overlay (default: windowed only)")
    parser.add_argument("--no-ui", action="store_true", help="disable the human overlay")
    parser.add_argument("--shadows", action="store_true", help="enable directional shadow mapping (default: on)")
    parser.add_argument("--no-shadows", action="store_true", help="disable directional shadow mapping")
    parser.add_argument("--srgb", action="store_true", help="enable sRGB-correct linear pipeline (default: on)")
    parser.add_argument("--no-srgb", action="store_true", help="disable sRGB-correct linear pipeline")
    parser.add_argument("--post", action="store_true", help="enable post color-grade (default: on)")
    parser.add_argument("--no-post", action="store_true", help="disable post color-grade")
    parser.add_argument("--bloom", action="store_true", help="enable bloom glow (default: on)")
    parser.add_argument("--no-bloom", action="store_true", help="disable bloom glow")
    parser.add_argument("--sprites", action="store_true", help="enable GPU point sprites (default: on)")
    parser.add_argument("--no-sprites", action="store_true", help="disable GPU point sprites")
    parser.add_argument("--culling", action="store_true", help="enable view-frustum culling (default: on)")
    parser.add_argument("--no-culling", action="store_true", help="disable view-frustum culling")
    parser.add_argument("--start-paused", action="store_true", help="start a rendered run with gameplay paused")
    parser.add_argument("--serve", action="store_true", help="serve the local JSON API and WebGL web console")
    parser.add_argument("--host", default=None, help="web console bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=_port, default=None, help="web console port (default: 8000; 0 picks a free port)")
    parser.add_argument("--prefab-dir", type=Path, default=None, metavar="DIR", help="persist editor prefabs as .kprefab files (default for --project: DIR/prefabs)")
    parser.add_argument("--out", type=Path, default=None, help="PNG for rendering; JSON report for --simulate")
    parser.add_argument("--report", type=Path, default=None, help="machine-readable frame report (requires --headless)")
    args = parser.parse_args(argv)
    if args.new is not None:
        incompatible = (
            args.project is not None or args.describe or args.headless or args.simulate
            or args.verify_determinism or args.expect_hash is not None or args.compare_baseline is not None
            or args.diff_out is not None or args.actions is not None or args.replay is not None
            or args.playtest or args.policy != "random" or args.seed != 0 or args.script is not None
            or args.transcript_out is not None or args.trace or args.frames or args.size != (960, 540)
            or args.ui or args.no_ui or args.shadows or args.no_shadows or args.srgb or args.no_srgb
            or args.post or args.no_post or args.bloom or args.no_bloom or args.sprites or args.no_sprites
            or args.culling or args.no_culling or args.start_paused or args.serve
            or args.host is not None or args.port is not None or args.prefab_dir is not None or args.out is not None
            or args.report is not None or args.game != "keystone.samples:CubeDemo"
        )
        if incompatible:
            parser.error("--new is a standalone project-scaffolding command")
        from keystone.project import create_project

        try:
            context = create_project(args.new, name=args.name, force=args.force)
        except Exception as exc:  # noqa: BLE001 - CLI reports Why/Fix, never a traceback
            print("Keystone could not create the project.", file=sys.stderr)
            message = str(exc)
            if "Why:" in message and "Fix:" in message:
                print(message, file=sys.stderr)
            else:
                print(f"Why: {message}", file=sys.stderr)
                print("Fix: choose an empty directory or pass --force.", file=sys.stderr)
            return 1
        print(f"Created Keystone project {context.manifest.name!r} at {context.directory}")
        print(f"Manifest: {context.directory / 'keystone.json'}")
        print("Next: python -m keystone --project . --describe")
        return 0
    if args.name is not None:
        parser.error("--name requires --new")
    if args.force:
        parser.error("--force requires --new")
    if args.serve and (
        args.describe or args.headless or args.simulate or args.verify_determinism or args.expect_hash
        or args.compare_baseline or args.diff_out or args.actions or args.trace or args.ui or args.no_ui
        or args.shadows or args.no_shadows or args.srgb or args.no_srgb or args.post or args.no_post
        or args.bloom or args.no_bloom or args.sprites or args.no_sprites or args.culling or args.no_culling
        or args.start_paused or args.out or args.report or args.replay or args.playtest or args.script
        or args.transcript_out or args.policy != "random" or args.seed != 0
        or args.frames or args.size != (960, 540)
    ):
        parser.error("--serve is a standalone web-console command")
    if (args.host is not None or args.port is not None or args.prefab_dir is not None) and not args.serve:
        parser.error("--host, --port and --prefab-dir require --serve")
    if args.describe and (
        args.headless or args.simulate or args.verify_determinism or args.expect_hash
        or args.compare_baseline or args.diff_out or args.out or args.report or args.actions or args.trace
        or args.ui or args.no_ui or args.shadows or args.no_shadows
        or args.srgb or args.no_srgb or args.post or args.no_post or args.bloom or args.no_bloom or args.sprites or args.no_sprites or args.culling or args.no_culling or args.start_paused
        or args.replay or args.playtest
        or args.script or args.transcript_out or args.policy != "random" or args.seed != 0
        or args.frames or args.size != (960, 540)
    ):
        parser.error("--describe is a standalone discovery command")
    if args.headless and args.simulate:
        parser.error("--headless and --simulate are mutually exclusive")
    if args.replay and (args.headless or args.simulate or args.verify_determinism or args.describe or args.serve or args.playtest or args.shadows or args.no_shadows or args.srgb or args.no_srgb or args.post or args.no_post or args.bloom or args.no_bloom or args.sprites or args.no_sprites or args.culling or args.no_culling):
        parser.error("--replay is a standalone no-GL command")
    if args.playtest and (
        args.headless or args.simulate or args.verify_determinism or args.describe or args.serve
        or args.replay         or args.report or args.compare_baseline or args.diff_out or args.actions
        or args.size != (960, 540)
        or args.trace or args.ui or args.no_ui or args.shadows or args.no_shadows
        or args.srgb or args.no_srgb or args.post or args.no_post or args.bloom or args.no_bloom or args.sprites or args.no_sprites or args.culling or args.no_culling or args.start_paused
    ):
        parser.error("--playtest is a standalone no-GL command")
    if args.simulate and args.size != (960, 540):
        parser.error("--simulate needs no window; --size does not apply")
    if args.replay and (args.actions or args.compare_baseline or args.diff_out or args.report or args.ui or args.no_ui or args.shadows or args.no_shadows or args.srgb or args.no_srgb or args.post or args.no_post or args.bloom or args.no_bloom or args.sprites or args.no_sprites or args.culling or args.no_culling or args.start_paused):
        parser.error("--replay takes a CommandLog; --actions/--compare-baseline/--report/--ui/--shadows/--srgb/--post/--bloom do not apply")
    if args.replay and (args.frames or args.size != (960, 540)):
        parser.error("--replay uses the log frame count and needs no window; --frames/--size do not apply")
    if args.ui and args.no_ui:
        parser.error("--ui and --no-ui are mutually exclusive")
    if args.shadows and args.no_shadows:
        parser.error("--shadows and --no-shadows are mutually exclusive")
    if args.srgb and args.no_srgb:
        parser.error("--srgb and --no-srgb are mutually exclusive")
    if args.post and args.no_post:
        parser.error("--post and --no-post are mutually exclusive")
    if args.bloom and args.no_bloom:
        parser.error("--bloom and --no-bloom are mutually exclusive")
    if args.sprites and args.no_sprites:
        parser.error("--sprites and --no-sprites are mutually exclusive")
    if args.culling and args.no_culling:
        parser.error("--culling and --no-culling are mutually exclusive")
    if (args.post or args.no_post) and (args.describe or args.simulate or args.verify_determinism):
        parser.error("--post/--no-post apply to rendered runs, not discovery or simulation commands")
    if (args.bloom or args.no_bloom) and (args.describe or args.simulate or args.verify_determinism):
        parser.error("--bloom/--no-bloom apply to rendered runs, not discovery or simulation commands")
    if (args.sprites or args.no_sprites) and (args.describe or args.simulate or args.verify_determinism):
        parser.error("--sprites/--no-sprites apply to rendered runs, not discovery or simulation commands")
    if (args.culling or args.no_culling) and (args.describe or args.simulate or args.verify_determinism):
        parser.error("--culling/--no-culling apply to rendered runs, not discovery or simulation commands")
    if (args.ui or args.no_ui) and (args.describe or args.simulate or args.verify_determinism):
        parser.error("--ui/--no-ui apply to rendered runs, not discovery or simulation commands")
    if (args.shadows or args.no_shadows) and (args.describe or args.simulate or args.verify_determinism):
        parser.error("--shadows/--no-shadows apply to rendered runs, not discovery or simulation commands")
    if (args.srgb or args.no_srgb) and (args.describe or args.simulate or args.verify_determinism):
        parser.error("--srgb/--no-srgb apply to rendered runs, not discovery or simulation commands")
    if args.start_paused and (args.simulate or args.verify_determinism):
        parser.error("--start-paused applies to rendered runs, not simulation commands")
    if args.verify_determinism and (
        args.headless or args.simulate or args.report or args.compare_baseline
        or args.replay or args.size != (960, 540)
    ):
        parser.error("--verify-determinism is a standalone no-GL command")
    if args.expect_hash and not (args.simulate or args.verify_determinism or args.replay or args.playtest):
        parser.error("--expect-hash requires --simulate, --verify-determinism, --replay or --playtest")
    if args.simulate and args.report:
        parser.error("--report requires the rendered --headless path")
    if args.report and not args.headless:
        parser.error("--report requires --headless")
    if args.compare_baseline and not (args.headless and args.report):
        parser.error("--compare-baseline requires --headless and --report")
    if args.diff_out and not args.compare_baseline:
        parser.error("--diff-out requires --compare-baseline")
    if args.out and not (args.headless or args.simulate or args.verify_determinism or args.replay or args.playtest):
        parser.error("--out requires --headless, --simulate, --verify-determinism, --replay or --playtest")
    if args.actions and not (args.simulate or args.verify_determinism):
        parser.error("--actions requires --simulate or --verify-determinism")
    if args.trace and not (args.simulate or args.replay):
        parser.error("--trace requires --simulate or --replay")
    if (args.policy != "random" or args.seed != 0 or args.script is not None or args.transcript_out is not None) and not args.playtest:
        parser.error("--policy, --seed, --script and --transcript-out require --playtest")
    if args.script is not None and args.policy != "scripted":
        parser.error("--script requires --policy scripted")
    if args.policy == "scripted" and args.script is None:
        parser.error("--policy scripted requires --script")

    project_context = None
    if args.project is not None:
        from keystone.project import load_project

        try:
            project_context = load_project(args.project)
        except (OSError, ValueError, TypeError) as exc:
            print("Keystone could not open the project.", file=sys.stderr)
            print(f"Why: {exc}", file=sys.stderr)
            print(
                "Fix: run python -m keystone --new <directory>, or pass a valid keystone.json.",
                file=sys.stderr,
            )
            return 1
        if args.game == "keystone.samples:CubeDemo":
            args.game = project_context.manifest.game
        directory = str(project_context.directory)
        if directory not in sys.path:
            sys.path.insert(0, directory)

    from keystone.plugin import describe_game, load_game

    engine = None
    try:
        game = load_game(args.game)
        if project_context is not None:
            from keystone.project import attach_project_assets

            try:
                attach_project_assets(game, project_context)
            except (OSError, KeyError, TypeError, ValueError) as exc:
                print("Keystone could not import project assets.", file=sys.stderr)
                print(f"Why: {exc}", file=sys.stderr)
                print(
                    "Fix: list existing .obj/.png/.kprefab paths in keystone.json assets.",
                    file=sys.stderr,
                )
                return 1
        if args.serve:
            from keystone.web import serve

            prefab_dir = args.prefab_dir
            if prefab_dir is None and project_context is not None:
                prefab_dir = project_context.directory / "prefabs"
            return serve(
                game,
                args.host or "127.0.0.1",
                args.port if args.port is not None else 8000,
                prefab_dir=prefab_dir,
            )
        if args.describe:
            payload = describe_game(game)
            if project_context is not None:
                payload["project"] = project_context.describe()
            print(json.dumps(payload, indent=2, sort_keys=True))
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
        if args.replay:
            from keystone.replay import CommandLog, run_log
            from keystone.serialization import write_json_atomic

            try:
                log = CommandLog.load(args.replay)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise ValueError(
                    f"could not read replay log {args.replay}.\n"
                    f"Why: {exc}\n"
                    "Fix: pass a valid CommandLog JSON file written by --simulate --out."
                ) from exc
            result = run_log(lambda: load_game(args.game), log, trace=args.trace)
            if args.expect_hash:
                result["expected_hash"] = args.expect_hash
                result["ok"] = result["hash"] == args.expect_hash
            if args.out:
                write_json_atomic(args.out, result)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["ok"] else 1

        if args.playtest:
            from keystone.headless import load_actions
            from keystone.playtest import (
                GreedyPolicy,
                RandomPolicy,
                ScriptedPolicy,
                make_report,
                run_bot,
                validate_fairness,
            )
            from keystone.serialization import write_json_atomic

            if args.policy == "scripted":
                script = load_actions(args.script)
                policy: RandomPolicy | GreedyPolicy | ScriptedPolicy = ScriptedPolicy(script)
                reference: list | None = list(script)
            elif args.policy == "greedy":
                policy = GreedyPolicy()
                reference = None
            else:
                policy = RandomPolicy()
                reference = None
            frames = args.frames if args.frames else 120
            transcript = run_bot(lambda: load_game(args.game), policy, frames=frames, seed=args.seed, trace=True)
            limit = transcript.get("final", {}).get("time_limit")
            fairness = validate_fairness(
                lambda: load_game(args.game),
                reference_actions=reference,
                frames=frames,
                seeds=(args.seed,),
                time_limit_frames=limit if isinstance(limit, int) else None,
            )
            report = make_report(transcript, fairness)
            if args.expect_hash:
                report["expected_hash"] = args.expect_hash
            ok = report["hash"] == args.expect_hash if args.expect_hash else True
            if fairness["verdict"] == "unfair":
                ok = False
            if args.transcript_out:
                write_json_atomic(args.transcript_out, transcript)
            if args.out:
                write_json_atomic(args.out, report)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if ok else 1

        from keystone.app import Engine
        from keystone.scene import (
            BloomSettings,
            ColorSettings,
            CullingSettings,
            PostSettings,
            ShadowSettings,
            SpriteSettings,
        )

        engine = Engine(
            game,
            args.size[0],
            args.size[1],
            visible=not args.headless,
            msaa=0 if args.headless else 4,
            title=f"Keystone | {getattr(game, 'name', 'game')}",
            ui=args.ui or (not args.headless and not args.no_ui),
        )
        if args.no_shadows:
            engine.scene.shadow = ShadowSettings(enabled=False)
        elif args.shadows:
            engine.scene.shadow = ShadowSettings(enabled=True)
        if args.no_srgb:
            engine.scene.color = ColorSettings(enabled=False)
        elif args.srgb:
            engine.scene.color = ColorSettings(enabled=True)
        if args.no_post:
            engine.scene.post = PostSettings(enabled=False)
        elif args.post:
            engine.scene.post = PostSettings(enabled=True)
        if args.no_bloom:
            engine.scene.bloom = BloomSettings(enabled=False)
        elif args.bloom:
            engine.scene.bloom = BloomSettings(enabled=True)
        if args.no_sprites:
            engine.scene.sprite = SpriteSettings(enabled=False)
        elif args.sprites:
            engine.scene.sprite = SpriteSettings(enabled=True)
        if args.no_culling:
            engine.scene.culling = CullingSettings(enabled=False)
        elif args.culling:
            engine.scene.culling = CullingSettings(enabled=True)
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
                f"Rendered {rendered} frame(s) at {engine.renderer.width}x{engine.renderer.height} "
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
