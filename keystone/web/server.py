"""A localhost JSON API and static web console for the game-agnostic engine."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from keystone.headless import run_simulation
from keystone.input import ActionState
from keystone.plugin import GameModule, describe_game
from keystone.replay import FIXED_STEP
from keystone.scene import Scene
from keystone.web.scene import scene_document
from keystone.web.schema import SCENE_SCHEMA, WEB_API_VERSION

MAX_BODY = 1_000_000
MAX_FRAMES = 1_000_000
STATIC_ROOT = Path(__file__).with_name("static")
STATIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "app.js": "text/javascript; charset=utf-8",
    "viewer.js": "text/javascript; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
}


class WebProblem(Exception):
    """One client-facing error with an actionable fix."""

    def __init__(self, status: int, why: str, fix: str) -> None:
        super().__init__(why)
        self.status = status
        self.why = why
        self.fix = fix


class GameSession:
    """One in-memory game guarded by a lock for concurrent HTTP requests."""

    def __init__(self, game: GameModule) -> None:
        self.game = game
        self.lock = threading.Lock()

    @property
    def name(self) -> str:
        return getattr(self.game, "name", "game")

    def describe(self) -> dict:
        with self.lock:
            return describe_game(self.game)

    def simulate(self, frames: int, actions: list, step: float, trace: bool) -> dict:
        if isinstance(frames, bool) or not isinstance(frames, int) or frames < 0:
            raise WebProblem(400, "frames must be a non-negative integer", 'send {"frames": 1}')
        if frames > MAX_FRAMES:
            raise WebProblem(400, f"frames must be at most {MAX_FRAMES}", "send a smaller frame count")
        if isinstance(step, bool) or not isinstance(step, (int, float)) or step <= 0.0:
            raise WebProblem(400, "step must be a positive number", 'send {"frames": 1, "step": 0.0167}')
        if not isinstance(trace, bool):
            raise WebProblem(400, "trace must be a boolean", 'send {"frames": 1, "trace": false}')
        if not isinstance(actions, list):
            raise WebProblem(400, "actions must be a JSON list", 'send {"frames": 1, "actions": [{"forward": 1.0}]}')
        try:
            script = [ActionState.from_dict(item) for item in actions]
        except (AttributeError, TypeError, ValueError) as exc:
            raise WebProblem(400, f"invalid action item: {exc}", "each action must be a JSON object") from exc
        with self.lock:
            return run_simulation(self.game, frames, script, step=float(step), trace=bool(trace))

    def scene(self) -> dict:
        with self.lock:
            scene = getattr(self.game, "scene", None)
            if not isinstance(scene, Scene) or not scene.root.children:
                scene = self.game.build_scene()
            return scene_document(scene, game=self.name)

    def inspector(self) -> dict:
        from keystone.batch import merge_batches, plan_batches

        with self.lock:
            scene = getattr(self.game, "scene", None)
            if not isinstance(scene, Scene) or not scene.root.children:
                scene = self.game.build_scene()
            document = scene_document(scene, game=self.name)
            try:
                batches = plan_batches(scene)
            except (AttributeError, TypeError, ValueError):
                batches = {"schema": 1, "groups": 0, "draw_calls": 0, "batched_calls": 0, "saved_calls": 0, "triangles": 0, "batches": []}
            try:
                merged = merge_batches(scene)
                merged_summary = {
                    "groups": merged["groups"],
                    "merged_calls": merged["merged_calls"],
                    "saved_calls": merged["saved_calls"],
                    "triangles": merged["triangles"],
                }
            except (AttributeError, TypeError, ValueError):
                merged_summary = None
            try:
                from keystone.gpu.instancing import plan_instanced

                instanced = plan_instanced(scene)
                instancing_summary = {
                    "groups": instanced["groups"],
                    "instanced_calls": instanced["instanced_calls"],
                    "saved_calls": instanced["saved_calls"],
                    "instances": instanced["instances"],
                    "triangles": instanced["triangles"],
                }
            except (AttributeError, TypeError, ValueError):
                instancing_summary = None
            mixer = getattr(self.game, "mixer", None)
            audio = None
            if mixer is not None and hasattr(mixer, "voice_count"):
                try:
                    from keystone.audio import audio_report

                    clip = mixer.render() if hasattr(mixer, "render") else None
                    voices = mixer.voice_count() if callable(mixer.voice_count) else 0
                    buses = dict(mixer.buses) if isinstance(getattr(mixer, "buses", None), dict) else {}
                    audio = audio_report(clip, voices=voices, buses=buses) if clip is not None else {"voices": voices, "buses": buses}
                except (AttributeError, TypeError, ValueError):
                    audio = None
            animation = None
            for attribute in ("animations", "animator", "controller"):
                try:
                    controller = getattr(self.game, attribute, None)
                    clips = getattr(controller, "clips", None) if controller is not None else None
                    if not isinstance(clips, dict):
                        continue
                    from keystone.animation import animation_report

                    animation = animation_report(controller)
                except (AttributeError, TypeError, ValueError, KeyError):
                    animation = None
                    continue
                break
            particles = None
            for attribute in ("particles", "fx", "particle_system"):
                try:
                    system = getattr(self.game, attribute, None)
                    if system is None or not hasattr(system, "alive_count"):
                        continue
                    from keystone.particles import particles_report

                    particles = particles_report(system)
                except (AttributeError, TypeError, ValueError):
                    particles = None
                    continue
                break
            assets = None
            registry = getattr(self.game, "assets", None)
            if registry is not None and hasattr(registry, "describe"):
                try:
                    inventory = registry.describe()
                    counts = inventory.get("stats", {}) if isinstance(inventory, dict) else {}
                    items = inventory.get("assets", []) if isinstance(inventory, dict) else []
                    assets = {
                        "total": counts.get("total", len(items) if isinstance(items, list) else 0),
                        "kinds": counts.get("kinds", {}),
                        "ids": sorted(item.get("id", "") for item in items if isinstance(item, dict))[:64],
                        "truncated": isinstance(items, list) and len(items) > 64,
                    }
                except (AttributeError, TypeError, ValueError):
                    assets = None
            shadow = getattr(scene, "shadow", None)
            color = getattr(scene, "color", None)
            post = getattr(scene, "post", None)
            bloom = getattr(scene, "bloom", None)
            return {
                "schema": 1,
                "game": self.name,
                "node_count": document["node_count"],
                "mesh_count": document["mesh_count"],
                "texture_count": document["texture_count"],
                "batches": batches,
                "merged": merged_summary,
                "instancing": instancing_summary,
                "shadows": {
                    "enabled": bool(getattr(shadow, "enabled", True)),
                    "size": 1024,
                },
                "color": {"enabled": bool(getattr(color, "enabled", True))},
                "post": {"enabled": bool(getattr(post, "enabled", True))},
                "bloom": {"enabled": bool(getattr(bloom, "enabled", True))},
                "audio": audio,
                "animation": animation,
                "particles": particles,
                "assets": assets,
                "scene_schema": SCENE_SCHEMA["version"],
            }


class KeystoneHTTPServer(ThreadingHTTPServer):
    """Threaded server carrying one game session for the request handler."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], session: GameSession) -> None:
        self.session = session
        super().__init__(address, ConsoleHandler)

    def handle_error(self, request: object, client_address: tuple[str, int]) -> None:
        error = sys.exc_info()[1]
        if isinstance(error, (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class ConsoleHandler(BaseHTTPRequestHandler):
    """Serve the API and the bundled static console."""

    protocol_version = "HTTP/1.1"
    server_version = "KeystoneWeb/1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_OPTIONS(self) -> None:
        self._send(204, b"", None)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/" or path == "/index.html":
                self._send_file("index.html")
            elif path in ("/app.js", "/viewer.js", "/style.css"):
                self._send_file(path.lstrip("/"))
            elif path == "/api":
                self._send_json(200, self._index())
            elif path == "/api/health":
                self._send_json(200, self._health())
            elif path == "/api/describe":
                self._send_json(200, self.session.describe())
            elif path == "/api/scene":
                self._send_json(200, self.session.scene())
            elif path == "/api/inspector":
                self._send_json(200, self.session.inspector())
            else:
                raise WebProblem(404, f"no route for {path}", "use /, /api, /api/describe, /api/scene, /api/inspector or /api/simulate")
        except WebProblem as exc:
            self._send_problem(exc)
        except Exception as exc:  # noqa: BLE001 - HTTP must never leak a traceback
            self._send_problem(WebProblem(500, str(exc), "check the server log and retry the request"))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path != "/api/simulate":
                raise WebProblem(404, f"no route for {path}", "POST /api/simulate")
            payload = self._read_json()
            if not isinstance(payload, dict):
                raise WebProblem(400, "request body must be a JSON object", 'send {"frames": 1}')
            frames = payload.get("frames", 1)
            actions = payload.get("actions", [])
            step = payload.get("step", FIXED_STEP)
            trace = payload.get("trace", False)
            self._send_json(200, self.session.simulate(frames, actions, step, trace))
        except WebProblem as exc:
            self._send_problem(exc)
        except Exception as exc:  # noqa: BLE001 - HTTP must never leak a traceback
            self._send_problem(WebProblem(500, str(exc), "check the server log and retry the request"))

    def do_PUT(self) -> None:
        self._method_not_allowed()

    def do_PATCH(self) -> None:
        self._method_not_allowed()

    def do_DELETE(self) -> None:
        self._method_not_allowed()

    @property
    def session(self) -> GameSession:
        return self.server.session

    def _index(self) -> dict:
        return {
            "ok": True,
            "api": WEB_API_VERSION,
            "game": self.session.name,
            "scene_schema": SCENE_SCHEMA,
            "endpoints": {
                "health": {"method": "GET", "path": "/api/health"},
                "describe": {"method": "GET", "path": "/api/describe"},
                "scene": {"method": "GET", "path": "/api/scene"},
                "inspector": {"method": "GET", "path": "/api/inspector"},
                "simulate": {
                    "method": "POST",
                    "path": "/api/simulate",
                    "body": {"frames": 1, "actions": [], "step": FIXED_STEP, "trace": False},
                },
            },
        }

    def _health(self) -> dict:
        return {"ok": True, "api": WEB_API_VERSION, "scene_schema": SCENE_SCHEMA["version"], "game": self.session.name}

    def _read_json(self) -> object:
        header = self.headers.get("Content-Length")
        if header is None:
            raise WebProblem(411, "Content-Length is required", "send a JSON body with Content-Type: application/json")
        try:
            length = int(header)
        except ValueError as exc:
            raise WebProblem(400, "Content-Length must be an integer", "send a valid byte length") from exc
        if length < 0:
            raise WebProblem(400, "Content-Length cannot be negative", "send a valid byte length")
        if length > MAX_BODY:
            raise WebProblem(413, f"request body exceeds {MAX_BODY} bytes", "send a smaller action list")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise WebProblem(400, "request body was truncated", "resend the complete JSON body")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WebProblem(400, "request body must be UTF-8", "encode the JSON body as UTF-8") from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise WebProblem(400, f"invalid JSON: {exc.msg}", "send a valid JSON object") from exc

    def _send_file(self, name: str) -> None:
        content_type = STATIC_FILES.get(name)
        if content_type is None:
            raise WebProblem(404, f"no static asset named {name}", "use /, /app.js, /viewer.js or /style.css")
        try:
            body = (STATIC_ROOT / name).read_bytes()
        except OSError as exc:
            raise WebProblem(500, f"could not read {name}: {exc}", "reinstall the Keystone package") from exc
        self._send(200, body, content_type)

    def _send_problem(self, problem: WebProblem) -> None:
        self._send_json(
            problem.status,
            {"ok": False, "error": problem.why, "fix": problem.fix},
        )

    def _method_not_allowed(self) -> None:
        self._send_json(405, {"ok": False, "error": "method not allowed", "fix": "use GET, POST or OPTIONS"})

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _send(self, status: int, body: bytes, content_type: str | None) -> None:
        self.send_response(status)
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        if body:
            self.wfile.write(body)


def create_server(game: GameModule, host: str = "127.0.0.1", port: int = 0) -> KeystoneHTTPServer:
    """Create a bound server; port 0 asks the OS for a free port."""
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return KeystoneHTTPServer((host, port), GameSession(game))


def serve(game: GameModule, host: str = "127.0.0.1", port: int = 8000) -> int:
    """Run the local console until interrupted."""
    try:
        server = create_server(game, host=host, port=port)
    except OSError as exc:
        raise ValueError(
            f"web console could not bind {host}:{port}.\n"
            f"Why: {exc}\n"
            "Fix: pass --port with a free port, or stop the process using it."
        ) from exc
    actual_port = server.server_address[1]
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("Warning: the console has no authentication; prefer the loopback host.", flush=True)
    print(f"Keystone web console: http://{display_host}:{actual_port}/", flush=True)
    print("Serving the JSON API and WebGL viewer. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.", flush=True)
    finally:
        server.server_close()
    return 0
