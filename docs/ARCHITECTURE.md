# Keystone Architecture

**Status:** implemented in v0.45.0 - core-only engine with scene identity, PBR materials, physics systems, human UI with profiler, deterministic animation with blending/events and skinning, particles with collision and GPU point sprites, audio, batch planning and merging, replay runner, seeded bot playtester with transcript diffing and fairness validation, a local web console with inspector, asset inventory and particle state, an asset registry with hot reload, material graphs, glTF 2.0 import, versioned scene snapshots with undo/redo, AI observation/action adapters, a post color-grade, bloom diffusion and character locomotion
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
├── playtest.py        seeded bot policies, transcript diffing, fairness validation
├── input.py          ActionState + InputMap
├── clock.py          FixedStepClock
├── culling.py        frustum planes and AABB visibility
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
├── material_graph.py declarative material graphs (color, float, checker, texture, mix, material, pbr)
├── gltf/             dependency-free glTF 2.0 import (meshes, materials, textures, scenes, skins)
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

`Node` exposes `id`, `tags`, `layer` and `components`. `Scene` allocates deterministic per-scene IDs (`node-1`, `node-2`, ...) when a node is attached or first traversed, preserves explicit IDs, rejects duplicates, and keeps an ID across reparenting. `Scene.query()` and `Scene.find()` filter by name, tag, layer and component type; `Scene.find_by_id()` resolves an ID. Tags are strings, a node has one layer, and components are keyed by their class (one per type). Queries are linear scans; an index is a future optimization. `Prefab.from_node()`/`from_scene()` capture detached templates; `Prefab.to_dict()`/`from_dict()` persist a schema-1 document whose mesh/material fields are registered asset ids, `Prefab.save()`/`load()` write atomically, and `Prefab.instantiate(scene)` clones templates with `instance:original-id` or scene-allocated IDs, deep-copies components and returns JSON-safe `describe()` metadata. Loading custom components requires an explicit `component_types` name map.

### Loading

`load_game("package.module:Factory")` imports the module, calls the factory, and validates the five methods. Invalid specs fail before the window opens, with a CLI `Why:`/`Fix:` message.

### Web API

`keystone.web` exports a versioned scene document (`SCENE_SCHEMA`, version 2) and a stdlib `ThreadingHTTPServer`. `GET /api/describe` reuses `describe_game()`, `POST /api/simulate` reuses `run_simulation()`, and `GET /api/scene` serializes the live scene with shared meshes, RGBA textures, camera, lights and world matrices. Requests share one in-memory `GameSession` behind a lock. The server binds to loopback by default, sends CORS headers for local clients, never creates a GL context and serves only its bundled static assets. The browser console renders that document with WebGL2; the OpenGL renderer remains the pixel authority.

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
- `analysis.analyze_frame(scene, pixels, width, height, image_path, ui=None, fx=None)` returns schema-11 JSON: image hashes, pixel statistics, content bbox, dominant colors, an 8×8 luminance grid, camera data, projected node bounds with scene identity/tags/layers/components, PBR material/texture metadata, sprite toggle, culling toggle plus per-frame FX counts and optional UI labels/buttons. `Engine.capture(image, report)` writes both artifacts.
- `analysis.compare_reports(before, after)` returns image/report equality, luminance/content-ratio deltas, bbox changes, added/removed/changed nodes (including identity, tag, layer, component and PBR material changes), and added/removed/moved UI labels and buttons. It accepts schema-1 through schema-11 reports as baselines and keys nodes by ID when both reports are schema 4 or newer.
- `keystone.agents.observe()` fuses `describe_game()` and `run_simulation()` into one hash-stable observation; `parse_actions()` validates LLM JSON into `ActionState`; `summarize_report()` compresses a frame report for model context; `AuditTrail` keeps a hash-chained log.
- `InputMap.save_bindings()/load_bindings()` persist rebindable keys as JSON; the profiler HUD shows draw calls and triangles from `Renderer.last_stats`.
- `analysis.diff_images(before, after, output)` reads PNGs, writes a visual diff and returns changed-pixel count/ratio, bbox and mean/max delta; `png.read_png()` is the dependency-free reader.
- `TextureData` is immutable RGBA8 data with PNG and checker factories; `Material.texture` is sampled through mesh UVs with repeat wrapping and mipmaps, and the renderer caches one GPU texture per payload.
- `keystone.ui.report.describe_canvas()` turns the rendered `Canvas` into `ui` metadata: visibility, pause state, label text/position/scale/color and button label/action/rect/selection/hover.
- `describe_game()` exposes `name`, `actions()`, `snapshot()`, capabilities (`simulate`, `render`, `human_ui`, `game_ui`, `web`) and the versioned report/scene schemas; `--describe` prints it without a window.
- `--serve` starts the local JSON API and browser console without OpenGL; `keystone.web.scene.scene_document()` exports the viewer document and `/api/editor` exposes hierarchy, selection, node authoring, transforms, undo/redo and prefab insertion.
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
8. `keystone.agents` may compose discovery, simulation and analysis; it never creates a window or GL context.

## 5. Core Systems

| System | Status | Responsibility |
|---|---|---|
| Math | Implemented | Vec3, Mat4, Quat, transforms |
| Scene | Implemented | hierarchy, visibility, lights, IDs, tags, layers and components |
| Prefabs | Implemented | detached subtree capture, versioned `.kprefab` save/load (schema 2), file-backed libraries, deterministic instance IDs, nested prefab instances with rebased links/IDs, component copy isolation, JSON-safe describe |
| Projects | Implemented | versioned `keystone.json` manifest, `--new` scaffold with starter scene/prefab content and component hooks, `--project` loader, `--validate-project` diagnostics, relative asset import as `project:<path>`, glTF/GLB scene-to-prefab import and generated five-op game |
| Scene queries | Implemented | name/tag/layer/component filters and ID lookup |
| Camera | Implemented | perspective and view matrices |
| Geometry | Implemented | indexed meshes, materials, vertex colors |
| Assets | Implemented | indexed meshes, materials, RGBA textures, OBJ, PNG and `.kprefab`; asset registry with stable ids, digests, dependencies and hot reload |
| State snapshots | Implemented | versioned scene save/load with camera, environment, asset references, typed components and bounded undo/redo history; duplicate ids, dangling parents and cycles rejected |
| Material graphs | Implemented | declarative node graphs evaluating to Material: color, float, checker, texture, mix, material and pbr nodes, cycle detection, JSON serialization |
| glTF 2.0 | Implemented | dependency-free importer for meshes, materials, textures and scenes; GLB containers, external and embedded buffers, normalized accessors, PNG textures, TRS and matrix transforms; sparse accessors and non-triangle primitives rejected |
| Renderer | Implemented | OpenGL 3.3, sky, lights, PBR (metallic/roughness/emissive), fog, textures, readback, draw/triangle stats, static batch planning and world-space merge |
| Runtime | Implemented | fixed clock, rebindable input with contexts and JSON persistence, loop, screenshots, profiler HUD with audio voices and animation clips |
| Audio | Implemented | synth clips, named-bus mixer, deterministic mixdown, WAV I/O, audit reports |
| Animation | Implemented | deterministic keyframe clips, looping controller, crossfade blending, timed events, pose application, JSON round trips, audit reports |
| Particles | Implemented | deterministic CPU emitters and systems with gravity/drag, swept AABB collision with bounce, friction and contact-kill, burst emission, lifetime culling, JSON round trips, HUD/inspector/AI reports, plus one GPU point-sprite billboard per live particle |
| Replay | Implemented | CommandLog runner and verifier without a window; --replay log.json with hash pinning |
| Plugin | Implemented | GameModule + loader |
| Replay | Implemented (basic) | action log, stable hash |
| Persistence | Implemented (basic) | atomic JSON with backup |
| Headless | Implemented | no-GL simulation and action scripts |
| AI discovery | Implemented | describe_game/--describe contract introspection |
| AI testing | Implemented | deterministic scenario helpers |
| Frame report | Implemented | image statistics, projected nodes, materials, UI metadata and report diff |
| Human UI | Implemented | bitmap font, canvas, HUD/help, interactive pause menu |
| Web console | Implemented | scene export, JSON API, CORS, static WebGL2 viewer |
| Scene editor | Implemented | hierarchy, node create/duplicate/reparent/delete, node property and transform edits, camera/environment authoring, atomic batch authoring, action examples in the web schema, asset inventory/metadata/assignment with a console metadata readout, typed component authoring with field schemas and generated console inputs, play/step/stop with action scripts and authored-scene restore, full-scene bounded undo/redo, scene-vs-saved diffs, prefab capture/insertion, multi-root prefab instance groups with revert/apply, per-field prefab override tracking, deterministic component lifecycle hooks, additive scene groups, hierarchy prefab badges, file-backed scene/prefab save/load/rename/duplicate/delete/restore with recoverable trash, `--scene` startup, an independent orbit/pan/zoom/focus viewport camera, click selection, a selection rim highlight, X/Y/Z viewport move/rotate/scale gizmos with live preview and one-action-per-drag, hierarchy/asset filters and keyboard undo/redo/delete/focus/nudge shortcuts via `/api/editor` and console controls |
| Physics | Implemented | rays, AABB, sphere queries, broadphase, character movement and triggers |
| AI adapters | Implemented | validated action parsing, fused observations, report summaries, hash-chained audit trail |
| Playtest | Implemented | seeded bot policies, CommandLog-compatible transcripts, transcript diffing, schema-1 reports, fairness validation |
| Batching | Implemented | static mesh/material grouping with draw-call savings, world-space merge, and skin-aware merge for identical rigs |
| Inspector | Implemented | web `/api/inspector` with node counts, batch plan, merge summary (incl. skinned rigs), audio, animation and particle state, asset inventory |
| ECS | Optional/missing | evaluate after a real workload |
| Editor/tooling | Missing | future core module |

## 6. Roadmap

1. **Scene identity and components** — implemented in v0.19.0; stable node IDs, tags/layers and typed component queries.
2. **Physics** — implemented in v0.21.0; broadphase, AABB character controller, triggers and filtered raycasts.
3. **Assets** — asset registry and hot reload in v0.22.0; material graphs in v0.23.0; glTF 2.0 import in v0.24.0; snapshots and undo/redo in v0.25.0; GLB containers and stricter format validation in v0.26.0; PBR material core, `pbr` graph nodes and full glTF PBR preservation in v0.27.0.
4. **Renderer** — PBR shading, emissive and render stats in v0.27.0; static batch planning in v0.28.0 and world-space batch merging in v0.29.0; skin-aware merge in v0.44.0; view-frustum culling in v0.45.0; GPU instancing in v0.32.0, directional shadows in v0.34.0, an sRGB linear pipeline in v0.35.0, a post color-grade in v0.36.0, bloom glow in v0.37.0 and bloom diffusion in v0.38.0; full post chain remains.
5. **Input/audio** — rebindable input with JSON persistence and profiler HUD in v0.27.0; action contexts, deterministic mixer with buses, WAV I/O and HUD voices in v0.28.0; live device playback remains out of scope.
6. **AI adapters** — implemented in v0.27.0; validated actions, fused observations, report summaries and hash-chained audit trail.
6. **Animation** — deterministic keyframe clips, looping controller, pose application and JSON round trips in v0.29.0; crossfade blending and timed events in v0.30.0; skinning (LBS-4, CPU + GPU, glTF) in v0.41.0; deterministic CPU particles with HUD/inspector/AI reports in v0.31.0, swept AABB collision in v0.40.0, GPU point sprites in v0.42.0, bounce/friction/contact-kill in v0.43.0.
6. **Serialization/replay** — versioned scene snapshot format and undo/redo in v0.25.0; deterministic replay runner with `--replay` in v0.30.0; seeded bot playtester with transcript diffing and fairness validation in v0.33.0.
7. **Tooling** — the v0.20.0 web console covers discovery, simulation and scene preview; `/api/inspector` with batch plan and audio state in v0.28.0 plus merge summary and animation state in v0.29.0 plus asset inventory in v0.30.0; the v0.46.0 scene editor adds hierarchy, selection, transforms and prefabs; richer HUD widgets and editor hooks remain.

Each core system must have a game-agnostic test and must not introduce genre vocabulary.

## 7. Acceptance

- `python -m pytest -q` passes.
- `python -m keystone --describe` prints the game contract without a window.
- `python -m keystone --simulate --frames 1` runs without OpenGL.
- `python -m keystone --verify-determinism --frames 2` exits 0 only for matching hashes.
- `python -m keystone --simulate --frames 1 --expect-hash <hash>` exits 0 only for the pinned hash.
- `python -m keystone --playtest --policy random --seed 0 --frames 8` exits 0 with a schema-1 transcript and report; the same seed replays to the same hash.
- `python -m keystone --playtest` on an unfair configuration exits 1 with `fairness.reasons` naming the rejection.
- `--headless --frames 1 --size 64x48` renders the sample.
- `--headless --frames 1 --ui --report hud.json` captures the human overlay.
- `--headless --frames 1 --ui --start-paused --report paused.json` captures the pause menu and its buttons.
- `--no-ui` keeps windowed and headless captures free of overlay pixels.
- Pausing opens a hit-testable Resume/Hide HUD/Quit menu and releases the cursor.
- A game's optional `draw_ui(canvas, state)` contributes pixels to the same capture.
- `compare_reports()` detects UI label/button changes when `ui` metadata is present.
- `SpatialGrid` returns exact overlapping proxies after updates/removals, without duplicates.
- `CharacterController` rests on a floor, stops at walls, leaves the ground on a jump, steps onto low stairs and rides caller-supplied platform velocity with swept pushout.
- Particles bounce with restitution, lose tangential velocity to friction, settle below rest speed and optionally die on contact, all deterministically.
- Particles sliding along a box face keep tangential motion; deep-interior spawns eject through the near face.
- `TriggerTracker` reports sorted enter/exit tuples and an immutable active set; `raycast()` filters candidates and returns the nearest hit.
- `Scene` assigns unique IDs, preserves them across reparenting and rejects duplicate explicit IDs.
- Scene snapshot schema 2 persists typed components; loading custom components without `component_types` fails with an actionable message, and schema-1 snapshots still load.
- `Scene.query()`/`find()` filter by name, tag, layer and component; `find_by_id()` resolves an ID.
- `Prefab` captures a detached subtree, saves/loads schema-2 `.kprefab` files through registered mesh/material ids, instantiates deterministic IDs, preserves tags/layers/components, isolates component copies, and persists nested links; schema-1 documents load with flat links.
- `/api/editor` schema 2 creates, deletes, duplicates and reparents nodes, links mesh/material ids through the game's asset registry, restores bounded undo/redo snapshots atomically, and can back prefab entries with a `PrefabLibrary` rooted in `<project>/prefabs`.
- The editor reloads persisted prefabs after a restart, reports corrupt library entries as per-entry errors, and inserts them with deterministic instance ids.
- Editor schema 3 saves and loads typed-component `.kscene` files in place, clears undo history on load, and rejects missing or wrong-kind asset references.
- Editor schema 4 lists registry assets and reassigns or clears a node's mesh/material with undo; missing or wrong-kind ids return a 400.
- Editor schema 5 adds/removes typed components through the game's `component_types` map, with undo and scene-file round trips.
- Editor schema 6 runs the game from the authored scene, blocks edits while playing, and restores the pre-play scene on stop.
- Editor schema 7 edits an existing node's name, visibility, tags and layer with undo and strict validation.
- Editor schema 8 applies up to 100 scene-mutating actions atomically with one undo entry and full rollback on failure.
- Editor schema 9 adds kind-specific asset metadata: mesh counts/flags, material factors, texture size and prefab node/dependency summaries; schema 12 adds mesh bounds.
- Editor schema 10 adds dataclass field hints for `component_types`, while custom codecs report a manual-codec note.
- The console renders dataclass component fields as typed inputs (int/float/string/bool/JSON) and keeps the JSON editor for custom codecs.
- Editor schema 13 adds bounded PNG preview data URIs to texture metadata and to each material's texture summary; the console shows the selected material texture preview.
- Editor schema 11 safely renames or deletes scene/prefab library entries and keeps cached prefabs in sync.
- The console viewport uses an independent orbit camera (`lookAt`, pointer drag, wheel zoom, Reset view) so navigation does not mutate the game camera.
- The selected node gets unlit Move/Rotate/Scale gizmos scaled by camera distance; translate uses world- or local-axis arrows (X toggles), rotate uses local-axis rings, and scale uses local-axis box handles. Dragging previews the delta on the node and its descendants, Ctrl/Cmd snaps to 0.25 units, 15 degrees or 0.1 scale, and release sends one `transform` action with the composed local value; play mode hides the gizmos.
- Scene snapshots are schema 4 and preserve editor-only prefab instance links and scene-group metadata; schema 1-3 documents load with no group metadata.
- Editor schema 18 exposes `prefab_link` and adds `revert_prefab`/`apply_prefab`: insertions get a deterministic instance prefix on every root, revert replaces the linked group with a fresh template copy, apply captures the group back into the prefab and its library, and prefab capture/instantiation strip links and instance prefixes so templates stay reusable.
- Editor schema 19 adds a `prefab_instances` inventory (`id`, `name`, `instance`) to every editor document so AI clients can discover linked roots without scanning nodes.
- Editor schema 20 allows `revert_prefab` inside atomic batches, so instance recovery and other edits share one undo entry.
- Scene diff schema 3 compares `prefab_link` and `scene_group` fields, so saved-scene diffs report instance-link and additive-group changes.
- Editor schema 21 makes prefab links and revert/apply/delete/reparent group-aware for multi-root prefabs; group roots must share one parent, revert preserves the group's earliest sibling position, and `prefab_instance_count` counts distinct groups.
- Editor schema 22 supports nested prefab instances with prefab schema 2: nested links persist, instantiation rebases effective `outer.inner` prefixes and IDs, and nested groups revert/apply independently of the outer instance.
- Editor schema 23 reports field-level prefab overrides (`prefab_overrides`, `prefab_override_count`) and adds `revert_prefab_override`/`apply_prefab_override`; mapping stops at nested prefab boundaries, revert is one undo entry, and apply clones the template before a library-safe write.
- Editor schema 24 adds deterministic component lifecycle hooks: `ComponentRuntime` starts hook-bearing components once in DFS node/type order, updates them before each fixed game step, stops them in reverse order, and exposes hooks in component schemas plus an active/frame/started summary in play state.
- Editor schema 25 adds additive scene groups: `SceneGroup(name)` metadata persists on container nodes, `add_scene`/`unload_scene` edit in history, `save_scene_group` writes children back to the library, and `/api/editor` exposes the group inventory/count.
- `--serve --scene NAME` opens a saved `.kscene` from the project/scene library before the first editor request and requires an explicit library.
- `--simulate --scene NAME` and `--headless --scene NAME` restore the same `.kscene` into the built scene and pass it to the simulation/engine without rebuilding.
- `--replay --scene NAME` and `--playtest --scene NAME` restore the scene into every fresh game instance, including fairness probes, so transcripts and verdicts share one authored layout.
- `--verify-determinism --scene NAME` loads the scene on both passes, and windowed runs pass the prepared scene to the engine; only `--describe` rejects `--scene`.
- `--project . --serve` uses `<project>/prefabs/*.kprefab`; `--prefab-dir DIR` overrides the library, and library entries report load errors instead of breaking the editor.
- `python -m keystone --new <dir>` scaffolds a project whose `--project <dir> --describe` and `--simulate` paths pass the five-operation contract.
- A project manifest may list relative `.obj`, `.png`, `.kprefab`, `.gltf` and `.glb` assets; `--project` imports regular files as `project:<path>` after dependencies, converts glTF/GLB scenes into `<prefabs>/<stem>.kprefab` with `gltf.<stem>.*` sub-assets, rejects absolute, escaping, missing or unsupported paths, and returns regular records in manifest order.
- `--project DIR --validate-project` builds the game scene, imports assets into an isolated registry and temporary glTF library, then reports per-entry scene/prefab errors without writing project files.
- Schema-4 reports include node ID, parent ID, tags, layer and component names; older reports still compare by name.
- `TextureData.checker()` renders through a textured plane and material metadata appears in reports.
- `python -m keystone --headless --frames 1 --out frame.png --report frame.json` writes both artifacts.
- `--compare-baseline baseline.json` exits non-zero on image change.
- `--diff-out diff.png` writes a visual pixel diff.
- `compare_reports()` detects image, stat and projected-node changes.
- Merged skinned rigs render pixel-identical frames with fewer draw calls.
- `python -m keystone --serve` starts a loopback JSON API and static console without OpenGL.
- `GET /api/describe`, `GET /api/scene` and `POST /api/simulate` return the CLI-compatible schemas and CORS headers.
- The WebGL2 viewer renders a scene document with shared meshes, textures, lights and fog.
- `python -m keystone --game missing.module:Factory` exits 1 with `Why:`/`Fix:`.
- `keystone/` contains no game rules and imports no external game.
- `GameModule` is the only game-facing runtime contract.
- Core state writes are atomic and replay actions/hashes are deterministic.

Games are not added to this repository. They live in their own packages and load through `--game`.
