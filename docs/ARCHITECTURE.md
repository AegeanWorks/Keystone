# Keystone Architecture: Engine Core vs Game Modules

**Status:** proposed for review — 2026-10-30  
**Decision:** freeze genre feature work; split the engine core from game modules before adding more systems.

## 1. Why this document exists

The current tree is a playable vertical slice, but it is not yet a clean engine. Combat, light locks, weave layouts, cyber networks and the space survey are **games built on the engine**, not engine mechanics. They currently sit beside `math3d`, `scene` and `gpu/`, so the package cannot answer “what is Keystone?” without also shipping a dungeon crawler and a space game.

The correction is structural:

- `keystone/` is the engine and contains no game rules or genre nouns.
- `games/` contains optional, independently testable content built on the public engine API.
- The engine can run an empty game with a single cube before any of the current features are loaded.

The current code stays runnable during review. Nothing is moved or deleted until this document is accepted.

## 2. Goals and non-goals

**Goals**

- A core that can render, update and serialize a game without importing a game.
- A stable, documented `GameModule` contract.
- Generic input, fixed-step time, deterministic replay and snapshot hashing.
- Core systems for scene, assets, physics, audio, serialization and tooling.
- Core tests that prove no dependency on `games/`.
- Current features preserved as examples, not deleted.

**Non-goals for this review**

- Implementing ECS, physics, audio or an editor now.
- Moving files or changing runtime APIs now.
- Adding combat, puzzles, networks, space or other genre systems.
- Choosing a new rendering API or rewriting the renderer.

## 3. Target repository layout

```text
keystone/
├── keystone/                 # engine core only
│   ├── __init__.py           # public API and __all__
│   ├── api.py                # stable public surface
│   ├── math3d.py             # Vec3, Mat4, Quat
│   ├── scene.py              # Node, Transform, Scene, lights
│   ├── camera.py             # cameras
│   ├── geometry.py           # MeshData, Material
│   ├── mesh_builder.py       # static geometry composition
│   ├── primitives.py         # generic meshes (cube, sphere, ...)
│   ├── obj_loader.py         # generic asset loaders
│   ├── png.py                # generated-image utility
│   ├── input.py              # ActionState, bindings
│   ├── replay.py             # command log, fixed-step replay, stable hash
│   ├── serialization.py      # scene/save format
│   ├── app.py                # game-agnostic Engine loop
│   ├── plugin.py             # GameModule protocol and registry
│   └── gpu/                  # context, shader, buffers, renderer
├── games/
│   ├── expedition/           # current dungeon/combat/light/network/weave game
│   ├── space/                # current space survey game
│   ├── showcase/             # current demo scene
│   └── empty/                # minimal cube fixture proving the core runs alone
├── tests/
│   ├── core/                 # imports no games.*
│   └── games/                # one suite per game
└── docs/
```

The exact folder names are reviewable. The dependency direction is not.

## 4. The `GameModule` contract

The core exposes one small protocol. It is intentionally a role with five operations, not an inheritance tree.

```python
class GameModule(Protocol):
    name: str

    def build_scene(self) -> Scene: ...
    def update(self, dt: float, actions: ActionState) -> None: ...
    def snapshot(self) -> dict[str, object]: ...
    def actions(self) -> dict[str, object]: ...
    def status(self) -> str: ...
```

**Ownership**

- The **Engine** owns the GLFW window, GL context, renderer, fixed-step clock, input sampling, screenshot/PNG output and loop lifetime.
- The **GameModule** owns its state, rules, scene contents and update logic.
- The Engine never imports a game. A registry maps `--game <name>` to a factory.
- `ActionState` is a frozen DTO: move axes, look delta, pressed/held actions and pointer data. Bindings live in core input configuration, not in game code.
- `snapshot()` returns JSON-safe data for replay hashes and save inspection. The game defines the payload; the core provides the stable hashing function.
- `actions()` returns the game's action schema for agents. The core does not know what a “hack” or “scan” means.

**Lifecycle**

```text
Engine.run
  -> sample input into ActionState
  -> fixed-step GameModule.update(dt, actions)
  -> GameModule.build_scene() once / on lifecycle change
  -> Renderer.render(game.scene)
  -> optional snapshot hash every N steps
```

The loop is fixed-step by default. Games may choose a presentation interpolation strategy, but the simulation step is deterministic.

## 5. Dependency rules

1. `keystone.*` may import only the standard library, declared runtime dependencies, and other `keystone.*` core modules.
2. No `keystone.*` module may import `games.*`.
3. `games.*` may import the public `keystone` API and its own modules, never another game.
4. The public surface is `keystone/__init__.py` plus `keystone/api.py`; games do not import deep implementation modules except through that surface.
5. Core module names and code must not contain genre nouns such as `combat`, `beam`, `network`, `weave`, `space`, `expedition`, `dungeon` or `terrain`.
6. Shared DTOs passed between core layers are frozen dataclasses or `NamedTuple`s.
7. An import-cycle or boundary test runs in the core suite. A static check fails on `keystone -> games` imports and on game nouns in core module names.

This is the enforcement version of PRINCIPLE-009: layering, constructor injection and registries apply at the engine boundary, not as decorative folders.

## 6. Current module inventory

| Current module | Classification | Target |
|---|---|---|
| `math3d.py`, `camera.py`, `scene.py`, `geometry.py`, `mesh_builder.py`, `primitives.py`, `obj_loader.py`, `png.py` | **Core** | Stay in `keystone/` |
| `gpu/context.py`, `gpu/shader.py`, `gpu/mesh_buffer.py`, `gpu/renderer.py` | **Core** | Stay in `keystone/gpu/` |
| `app.py` | **Core, refactor** | Generic `Engine` around `GameModule`; remove game-facing controls/status callbacks |
| `__main__.py` | **CLI adapter** | Dispatch through the game registry, not direct game imports |
| `atmosphere.py` | Optional visual utility | `keystone/extras/atmosphere.py` or `games/expedition/atmosphere.py`; not core |
| `procedural/noise.py` | Optional math utility | `keystone/noise.py` or `keystone/extras/noise.py`; not core |
| `demo.py` | **Game/example** | `games/showcase/` |
| `sim/world.py` | **Game state** | `games/expedition/world.py` |
| `combat.py` | **Game rule** | `games/expedition/combat.py` |
| `beams.py` | **Game rule** | `games/expedition/lightlock.py` |
| `expedition.py` | **Game scene/controller** | `games/expedition/scene.py` |
| `harness.py` | **Game harness** | `games/expedition/harness.py`; core keeps generic replay |
| `procedural/terrain.py`, `dungeon.py`, `weave.py`, `network.py` | **Content generators** | `games/expedition/procgen/` |
| `space.py`, `space_expedition.py`, `space_harness.py` | **Game** | `games/space/` |
| `procedural/space.py` | **Content generator** | `games/space/procgen.py` |

`primitives.py` and `obj_loader.py` stay core because they serve any game. `atmosphere.py` is a close call: it is reusable, but day/night is a game environment policy; keep it optional until a second game needs it.

## 7. Core system roadmap

These are the actual engine investments, in dependency order:

1. **GameModule + Engine boundary** — protocol, registry, `ActionState`, fixed-step loop, generic replay/snapshot hash.
2. **Scene and identity** — scene graph, stable node IDs, transforms, visibility, tags/layers; evaluate a hybrid ECS only after a real workload.
3. **Physics and collision** — broadphase, sphere/AABB/OBB queries, raycasts, character controller, trigger volumes. Replace the current game-specific collision code.
4. **Assets and materials** — registry, handles, dependency loading, texture/material support, glTF import, async or background loading only when measured.
5. **Renderer** — camera/render graph, instancing, batching, shadows, PBR, post-processing, sRGB/linear color, GPU resource lifetime.
6. **Input and audio** — action maps, rebinding, dead zones, mixer/buses, streaming rules.
7. **Serialization and replay** — scene/save format, schema versioning, snapshots, deterministic command logs, undo/rewind hooks.
8. **Tooling** — scene inspector, asset browser, profiler, headless screenshots, editor hooks.

Each item must be game-agnostic and covered by core tests. A core system with no game using it is acceptable only if it has a direct acceptance test or a planned module.

## 8. Deferred game modules

These are preserved as examples and future modules; none is a reason to change the core contract.

| Module | Current source | Depends on | Status |
|---|---|---|---|
| Expedition world | `sim/world.py` | core scene/time, procgen | Example |
| Combat | `combat.py` | world, collision, scene | Example |
| Light lock | `beams.py` | input, scene, renderer | Example |
| Weave layout | `procedural/weave.py` | dungeon layout API | Example |
| Cyber network | `procedural/network.py` | dungeon rooms, combat | Example |
| Space survey | `space.py`, `space_expedition.py` | core scene/renderer, procgen | Example |
| Terrain/dungeon | `procedural/terrain.py`, `dungeon.py` | noise, math | Example |
| Expedition harness | `harness.py` | world/action schema | Example |
| Space harness | `space_harness.py` | space/world | Example |
| Fold-style undo | not implemented | core replay/serialization | Future module |
| Iris-style beams | `beams.py` concept | input/renderer | Future module |
| Weft routes | `procedural/weave.py` concept | procgen | Future module |
| Cyberpulse puzzles | not implemented | network/action schema | Future module |

A module may be promoted to core only if at least two games need the same abstraction and it has no genre-specific vocabulary. “It is useful” is not enough.

## 9. Refactor sequence

The refactor is deliberately staged so the current build keeps running.

1. **Accept this document.** Record ADR-012. No code moves before acceptance.
2. **Add the boundary without moving content.** Introduce `plugin.py`, `GameModule`, `ActionState` and `Engine(game)`. Adapt `Expedition`, `SpaceExpedition` and `Demo` as temporary wrappers.
3. **Move examples.** `git mv` game modules into `games/expedition`, `games/space` and `games/showcase`; update imports, CLI and tests. Keep a one-release compatibility shim only if it is cheap.
4. **Enforce boundaries.** Split `tests/core` and `tests/games`; add the core import test and static name check; update packaging so a core install needs only core dependencies.
5. **Prove the empty core.** Add `games/empty` with one cube, run `python -m keystone --game empty`.
6. **Continue core systems.** Start with physics/collision or scene/ECS based on the first real need; do not add genre modules while a core gap is open.

Each step ends with the project Phase 4 gates. The refactor is not a big-bang rewrite.

## 10. Acceptance criteria

- `python -m keystone --game empty` runs with no game imports and renders a cube.
- A static check proves no `keystone.*` module imports `games.*`.
- Core tests import no `games.*`; game tests are separate.
- `keystone/__init__.py` exports a documented public API; games import only that surface.
- A core install works with only the declared core dependencies.
- The current expedition, space and showcase examples still run after the move.
- README states which parts are core and which are examples.
- No genre noun appears in core module names or core docs except in this architecture/roadmap document.

## 11. Review questions

1. Is a scene graph enough as the core identity model, with ECS optional, or should ECS be a core requirement now?
2. Should physics/collision be a core built-in or an optional module?
3. Should the games stay in this repository or move to separate repositories after extraction?
4. Which core system ships first after the split: physics, assets/serialization, or scene/ECS?
5. Is the proposed public API (`GameModule` + `ActionState` + `Engine`) the right size, or should the runtime expose a smaller facade?
