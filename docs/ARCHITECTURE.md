# Keystone Architecture

**Status:** implemented in v0.22.0 — core-only engine with scene identity, textured materials, physics systems, human UI, a local web console and an asset registry with hot reload
**Boundary:** `keystone/` is game-agnostic; games are external modules.

## 1. What Keystone Is

Keystone is a small 3D engine core. It owns the runtime that any game needs:

- window and OpenGL 3.3 context;
- fixed-step time;
- input sampling;
- scene graph and transforms;
- meshes, materials, primitives and asset loading;
- forward rendering and screenshots;
- a human HUD, controls help and pause overlay;
- collision queries;
- deterministic action logs and stable hashes;
- atomic JSON persistence;
- a five-operation game contract and loader.

It contains no combat, puzzles, procedural worlds, space simulation or other genre rules. The bundled `CubeDemo` is only a smoke test.

## 2. Layers

```text
keystone/
├── app.py            Engine: context, renderer, clock, input, loop, screenshots
├── plugin.py         GameModule Protocol and load_game()
├── input.py          ActionState + InputMap
├── clock.py          FixedStepClock
├── replay.py         CommandLog + stable_hash()
├── serialization.py  atomic JSON with .bak
├── headless.py       no-GL action simulation
├── analysis.py       frame statistics, projected scene and report diff
├── testing.py        deterministic AI/CI scenario helpers
├── physics.py        Ray, AABB, Sphere, queries, raycasts and pushout
├── broadphase.py     deterministic spatial-grid broadphase
├── character.py      AABB character movement, gravity and ground state
├── triggers.py       trigger volumes and enter/exit tracking
├── schema.py         versioned core schema constants
├── scene.py          Node, Transform, Scene identity/queries, DirectionalLight, PointLight
├── camera.py         PerspectiveCamera
├── geometry.py       MeshData, Material
├── mesh_builder.py   static geometry composition
├── primitives.py     cube, plane, cone, cylinder, sphere
├── obj_loader.py     streaming OBJ
├── png.py            PNG writer and reader
├── texture.py        immutable RGBA textures, PNG and checker sources
├── math3d.py         Vec3, Mat4, Quat
├── samples.py        CubeDemo smoke test
├── ui/               bitmap font, canvas, widgets, pause menu and overlay
├── web/              scene export, stdlib JSON API and static WebGL console
└── gpu/              GLFW context, GLSL, buffers, 3D and UI renderers
```

## 3. Runtime Contract

### GameModule

A game implements exactly five operations:

```python
class GameModule(Protocol):
    name: str

    def build_scene(self) -> Scene: ...
    def update(self, dt: float, actions: ActionState) -> None: ...
    def snapshot(self) -> dict[str, object]: ...
    def actions(self) -> dict[str, object]: ...
    def status(self) -> str: ...
```

The engine owns the runtime; the game owns its state and rules. The engine never imports a game module.

A game may additionally expose `draw_ui(canvas, state)`. It is an optional presentation hook, not part of the five required operations, and receives the per-frame `Canvas` and `HudState`. `describe_game()` reports its presence as `capabilities.game_ui`.

### Scene identity

`Node` exposes `id`, `tags`, `layer` and `components`. `Scene` allocates deterministic per-scene IDs (`node-1`, `node-2`, ...) when a node is attached or first traversed, preserves explicit IDs, rejects duplicates, and keeps an ID across reparenting. `Scene.query()` and `Scene.find()` filter by name, tag, layer and component type; `Scene.find_by_id()` resolves an ID. Tags are strings, a node has one layer, and components are keyed by their class (one per type). Queries are linear scans; an index is a future optimization.

### Loading

`load_game("package.module:Factory")` imports the module, calls the factory, and validates the five methods. Invalid specs fail before the window opens, with a CLI `Why:`/`Fix:` message.

### Web API

`keystone.web` exports a versioned scene document (`SCENE_SCHEMA`, version 1) and a stdlib `ThreadingHTTPServer`. `GET /api/describe` reuses `describe_game()`, `POST /api/simulate` reuses `run_simulation()`, and `GET /api/scene` serializes the live scene with shared meshes, RGBA textures, camera, lights and world matrices. Requests share one in-memory `GameSession` behind a lock. The server binds to loopback by default, sends CORS headers for local clients, never creates a GL context and serves only its bundled static assets. The browser console renders that document with WebGL2; the OpenGL renderer remains the pixel authority.

### Frame lifecycle

```text
Engine.run
  -> poll events / resize
  -> sample InputMap -> ActionState
  -> handle quit / mouse capture / HUD / pause menu input
  -> for each fixed step: GameModule.update(dt, actions) unless paused
  -> Renderer.render(GameModule scene)
  -> UiRenderer.draw(HumanOverlay.build(HudState, optional game.draw_ui))
  -> swap and update the title
```

Headless runs advance exactly one fixed step per rendered frame. Visible runs use `FixedStepClock` with a 0.25 s catch-up cap. Pausing stops gameplay updates but keeps rendering, input and the overlay alive. The pause menu releases the cursor, supports keyboard selection (`W`/`S` or arrows, `Enter`) and mouse clicks, and `Engine.apply_ui_action()` exposes the same actions to scripted tests.

### Determinism

`ActionState` is a frozen DTO and serializes to JSON. `CommandLog` records action frames with a seed and step size; `stable_hash()` canonically hashes snapshots. The engine does not silently use wall-clock time for simulation.

### AI and headless contracts

- `headless.run_simulation(game, frames, actions, step, trace)` calls `build_scene()` and then `update()` in fixed steps without importing the renderer or creating a GL context.
- `load_actions()` accepts a JSON list or an object with `actions`; every item is an `ActionState`.
- `analysis.analyze_frame(scene, pixels, width, height, image_path, ui=None)` returns schema-4 JSON: image hashes, pixel statistics, content bbox, dominant colors, an 8×8 luminance grid, camera data, projected node bounds with scene identity/tags/layers/components, material/texture metadata and optional UI labels/buttons. `Engine.capture(image, report)` writes both artifacts.
- `analysis.compare_reports(before, after)` returns image/report equality, luminance/content-ratio deltas, bbox changes, added/removed/changed nodes (including identity, tag, layer, component and material changes), and added/removed/moved UI labels and buttons. It accepts schema-1/2/3 reports as baselines and keys schema-4 nodes by ID.
- `analysis.diff_images(before, after, output)` reads PNGs, writes a visual diff and returns changed-pixel count/ratio, bbox and mean/max delta; `png.read_png()` is the dependency-free reader.
- `TextureData` is immutable RGBA8 data with PNG and checker factories; `Material.texture` is sampled through mesh UVs with repeat wrapping and mipmaps, and the renderer caches one GPU texture per payload.
- `keystone.ui.report.describe_canvas()` turns the rendered `Canvas` into `ui` metadata: visibility, pause state, label text/position/scale/color and button label/action/rect/selection/hover.
- `describe_game()` exposes `name`, `actions()`, `snapshot()`, capabilities (`simulate`, `render`, `human_ui`, `game_ui`, `web`) and the versioned report/scene schemas; `--describe` prints it without a window.
- `--serve` starts the local JSON API and browser console without OpenGL; `keystone.web.scene.scene_document()` exports the viewer document.
- `ActionState` includes `mouse_clicked` as a one-frame edge so games and menus can react without importing GLFW.
- `testing.run_script()`, `verify_determinism()` and `assert_deterministic()` turn an action script into test evidence; `--verify-determinism` exposes the two-run check to agents; `--expect-hash` pins a final result.
- `--simulate` requires no GPU; `--headless` renders off-screen; `--ui` adds the human overlay to a capture; `--start-paused` renders the pause menu; `--no-ui` disables it; `--report` documents a rendered frame; `--compare-baseline` gates visual changes; `--describe` discovers the contract.
- `docs/AI_GUIDE.md` is the end-to-end workflow reference.
- These are core APIs, not a game harness: they never import a game module or know a genre.

## 4. Dependency Rules

1. `keystone.*` imports only the standard library, declared dependencies and other core modules.
2. `keystone.*` never imports a game module.
3. A game imports the public `keystone` API and its own modules.
4. The public surface is `keystone/__init__.py` plus the documented modules; no deep imports are required by games.
5. Shared DTOs are frozen dataclasses.
6. Game modules are external; this repository ships only the `CubeDemo` smoke test.
7. `keystone.web` may import core modules; core library modules must not import `keystone.web` (the CLI entry point may compose the adapter).

## 5. Core Systems

| System | Status | Responsibility |
|---|---|---|
| Math | Implemented | Vec3, Mat4, Quat, transforms |
| Scene | Implemented | hierarchy, visibility, lights, IDs, tags, layers and components |
| Scene queries | Implemented | name/tag/layer/component filters and ID lookup |
| Camera | Implemented | perspective and view matrices |
| Geometry | Implemented | indexed meshes, materials, vertex colors |
| Assets | Implemented | indexed meshes, materials, RGBA textures, OBJ, PNG; asset registry with stable ids, digests, dependencies and hot reload |
| Material graphs | Implemented | declarative node graphs evaluating to Material: color, float, checker, texture, mix and material nodes, cycle detection, JSON serialization |
| Renderer | Implemented | OpenGL 3.3, sky, lights, fog, textures, readback |
| Runtime | Implemented | fixed clock, input, loop, screenshots |
| Plugin | Implemented | GameModule + loader |
| Replay | Implemented (basic) | action log, stable hash |
| Persistence | Implemented (basic) | atomic JSON with backup |
| Headless | Implemented | no-GL simulation and action scripts |
| AI discovery | Implemented | describe_game/--describe contract introspection |
| AI testing | Implemented | deterministic scenario helpers |
| Frame report | Implemented | image statistics, projected nodes, materials, UI metadata and report diff |
| Human UI | Implemented | bitmap font, canvas, HUD/help, interactive pause menu |
| Web console | Implemented | scene export, JSON API, CORS, static WebGL2 viewer |
| Physics | Implemented | rays, AABB, sphere queries, broadphase, character movement and triggers |
| Audio | Missing | future core module |
| ECS | Optional/missing | evaluate after a real workload |
| Editor/tooling | Missing | future core module |

## 6. Roadmap

1. **Scene identity and components** — implemented in v0.19.0; stable node IDs, tags/layers and typed component queries.
2. **Physics** — implemented in v0.21.0; broadphase, AABB character controller, triggers and filtered raycasts.
3. **Assets** — asset registry and hot reload implemented in v0.22.0; material graphs implemented in v0.23.0; glTF import remains.
4. **Renderer** — instancing/batching, shadows, PBR, post-processing, sRGB/linear color.
5. **Input/audio** — rebinding, action contexts, mixer and buses.
6. **Serialization/replay** — versioned scene/save format, undo/rewind, replay runner.
7. **Tooling** — the v0.20.0 web console covers discovery, simulation and scene preview; inspector, asset browser, profiler, richer HUD widgets and editor hooks remain.

Each core system must have a game-agnostic test and must not introduce genre vocabulary.

## 7. Acceptance

- `python -m pytest -q` passes.
- `python -m keystone --describe` prints the game contract without a window.
- `python -m keystone --simulate --frames 1` runs without OpenGL.
- `python -m keystone --verify-determinism --frames 2` exits 0 only for matching hashes.
- `python -m keystone --simulate --frames 1 --expect-hash <hash>` exits 0 only for the pinned hash.
- `--headless --frames 1 --size 64x48` renders the sample.
- `--headless --frames 1 --ui --report hud.json` captures the human overlay.
- `--headless --frames 1 --ui --start-paused --report paused.json` captures the pause menu and its buttons.
- `--no-ui` keeps windowed and headless captures free of overlay pixels.
- Pausing opens a hit-testable Resume/Hide HUD/Quit menu and releases the cursor.
- A game's optional `draw_ui(canvas, state)` contributes pixels to the same capture.
- `compare_reports()` detects UI label/button changes when `ui` metadata is present.
- `SpatialGrid` returns exact overlapping proxies after updates/removals, without duplicates.
- `CharacterController` rests on a floor, stops at walls and leaves the ground on a jump.
- `TriggerTracker` reports sorted enter, stay and exit sets; `raycast()` filters candidates and returns the nearest hit.
- `Scene` assigns unique IDs, preserves them across reparenting and rejects duplicate explicit IDs.
- `Scene.query()`/`find()` filter by name, tag, layer and component; `find_by_id()` resolves an ID.
- Schema-4 reports include node ID, parent ID, tags, layer and component names; older reports still compare by name.
- `TextureData.checker()` renders through a textured plane and material metadata appears in reports.
- `python -m keystone --headless --frames 1 --out frame.png --report frame.json` writes both artifacts.
- `--compare-baseline baseline.json` exits non-zero on image change.
- `--diff-out diff.png` writes a visual pixel diff.
- `compare_reports()` detects image, stat and projected-node changes.
- `python -m keystone --serve` starts a loopback JSON API and static console without OpenGL.
- `GET /api/describe`, `GET /api/scene` and `POST /api/simulate` return the CLI-compatible schemas and CORS headers.
- The WebGL2 viewer renders a scene document with shared meshes, textures, lights and fog.
- `python -m keystone --game missing.module:Factory` exits 1 with `Why:`/`Fix:`.
- `keystone/` contains no game rules and imports no external game.
- `GameModule` is the only game-facing runtime contract.
- Core state writes are atomic and replay actions/hashes are deterministic.

Games are not added to this repository. They live in their own packages and load through `--game`.
