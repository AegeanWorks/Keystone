# Keystone Architecture

**Status:** implemented in v0.8.0 — core-only engine  
**Boundary:** `keystone/` is game-agnostic; games are external modules.

## 1. What Keystone Is

Keystone is a small 3D engine core. It owns the runtime that any game needs:

- window and OpenGL 3.3 context;
- fixed-step time;
- input sampling;
- scene graph and transforms;
- meshes, materials, primitives and asset loading;
- forward rendering and screenshots;
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
├── physics.py        Ray, AABB, Sphere, queries and pushout
├── scene.py          Node, Transform, Scene, DirectionalLight, PointLight
├── camera.py         PerspectiveCamera
├── geometry.py       MeshData, Material
├── mesh_builder.py   static geometry composition
├── primitives.py     cube, plane, cone, cylinder, sphere
├── obj_loader.py     streaming OBJ
├── png.py            screenshot writer
├── math3d.py         Vec3, Mat4, Quat
├── samples.py        CubeDemo smoke test
└── gpu/              GLFW context, GLSL, buffers, forward renderer
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

### Loading

`load_game("package.module:Factory")` imports the module, calls the factory, and validates the five methods. Invalid specs fail before the window opens, with a CLI `Why:`/`Fix:` message.

### Frame lifecycle

```text
Engine.run
  -> poll events / resize
  -> sample InputMap -> ActionState
  -> handle quit / mouse capture
  -> for each fixed step: GameModule.update(dt, actions)
  -> Renderer.render(GameModule scene)
  -> swap and update the title
```

Headless runs advance exactly one fixed step per rendered frame. Visible runs use `FixedStepClock` with a 0.25 s catch-up cap.

### Determinism

`ActionState` is a frozen DTO and serializes to JSON. `CommandLog` records action frames with a seed and step size; `stable_hash()` canonically hashes snapshots. The engine does not silently use wall-clock time for simulation.

### AI and headless contracts

- `headless.run_simulation(game, frames, actions, step, trace)` calls `build_scene()` and then `update()` in fixed steps without importing the renderer or creating a GL context.
- `load_actions()` accepts a JSON list or an object with `actions`; every item is an `ActionState`.
- `analysis.analyze_frame(scene, pixels, width, height, image_path)` returns schema-1 JSON: image hashes, pixel statistics, content bbox, dominant colors, an 8×8 luminance grid, camera data and projected node bounds. `Engine.capture(image, report)` writes both artifacts.
- `analysis.compare_reports(before, after)` returns image/report equality, luminance/content-ratio deltas, bbox changes and added/removed/changed nodes.
- `describe_game()` exposes `name`, `actions()`, `snapshot()`, capabilities and the versioned report schema; `--describe` prints it without a window.
- `testing.run_script()`, `verify_determinism()` and `assert_deterministic()` turn an action script into test evidence; `--verify-determinism` exposes the two-run check to agents.
- `--simulate` requires no GPU; `--headless` renders off-screen; `--report` documents a rendered frame; `--compare-baseline` gates visual changes; `--describe` discovers the contract.
- These are core APIs, not a game harness: they never import a game module or know a genre.

## 4. Dependency Rules

1. `keystone.*` imports only the standard library, declared dependencies and other core modules.
2. `keystone.*` never imports a game module.
3. A game imports the public `keystone` API and its own modules.
4. The public surface is `keystone/__init__.py` plus the documented modules; no deep imports are required by games.
5. Shared DTOs are frozen dataclasses.
6. Game modules are external; this repository ships only the `CubeDemo` smoke test.

## 5. Core Systems

| System | Status | Responsibility |
|---|---|---|
| Math | Implemented | Vec3, Mat4, Quat, transforms |
| Scene | Implemented | hierarchy, visibility, lights |
| Camera | Implemented | perspective and view matrices |
| Geometry | Implemented | indexed meshes, materials, vertex colors |
| Assets | Implemented (basic) | primitives, OBJ, PNG |
| Renderer | Implemented | OpenGL 3.3, sky, lights, fog, readback |
| Runtime | Implemented | fixed clock, input, loop, screenshots |
| Plugin | Implemented | GameModule + loader |
| Replay | Implemented (basic) | action log, stable hash |
| Persistence | Implemented (basic) | atomic JSON with backup |
| Headless | Implemented | no-GL simulation and action scripts |
| AI discovery | Implemented | describe_game/--describe contract introspection |
| AI testing | Implemented | deterministic scenario helpers |
| Frame report | Implemented | image statistics, projected nodes and report diff |
| Physics | Implemented (queries) | rays, AABB, sphere overlap/pushout |
| Audio | Missing | future core module |
| ECS | Optional/missing | evaluate after a real workload |
| Editor/tooling | Missing | future core module |

## 6. Roadmap

1. **Scene identity and components** — stable node IDs, tags/layers, optional ECS queries.
2. **Physics** — broadphase, character controller, triggers, raycast filters.
3. **Assets** — registry, handles, textures/materials, glTF, hot reload.
4. **Renderer** — instancing/batching, shadows, PBR, post-processing, sRGB/linear color.
5. **Input/audio** — rebinding, action contexts, mixer and buses.
6. **Serialization/replay** — versioned scene/save format, undo/rewind, replay runner.
7. **Tooling** — inspector, asset browser, profiler, editor hooks.

Each core system must have a game-agnostic test and must not introduce genre vocabulary.

## 7. Acceptance

- `python -m pytest -q` passes.
- `python -m keystone --describe` prints the game contract without a window.
- `python -m keystone --simulate --frames 1` runs without OpenGL.
- `python -m keystone --verify-determinism --frames 2` exits 0 only for matching hashes.
- `python -m keystone --headless --frames 1 --size 64x48` renders the sample.
- `python -m keystone --headless --frames 1 --out frame.png --report frame.json` writes both artifacts.
- `--compare-baseline baseline.json` exits non-zero on image change.
- `compare_reports()` detects image, stat and projected-node changes.
- `python -m keystone --game missing.module:Factory` exits 1 with `Why:`/`Fix:`.
- `keystone/` contains no game rules and imports no external game.
- `GameModule` is the only game-facing runtime contract.
- Core state writes are atomic and replay actions/hashes are deterministic.

Games are not added to this repository. They live in their own packages and load through `--game`.
