# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

<!-- Entry format:
### ADR-NNN: <decision in one line>
- **Date**: YYYY-MM-DD
- **Status**: Accepted
- **Context**: <what forced the decision>
- **Decision**: <what was decided>
- **Consequences**: <what follows, including what it costs>
-->

### ADR-001: Render on the GPU with OpenGL 3.3 core

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The request was a performance-first 3D engine. This machine has a working OpenGL 3.3 core driver but no Rust or C/C++ toolchain, and a CPU Python rasterizer would not meet the performance goal.
- **Decision**: Use GLFW for the window/context and PyOpenGL for a GLSL 330 pipeline. Keep the renderer behind `keystone/gpu/` so a different graphics API can be added without changing scene or geometry code.
- **Consequences**: Real GPU rasterization and interactive frame rates without a native build step. The project requires an OpenGL 3.3 driver; machines without one fail at startup with a `Why:`/`Fix:` message. GLFW and PyOpenGL are declared dependencies.

### ADR-002: Keep the engine core Python-only and column-major

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The engine must be readable, testable and fast enough for the demo without a compiler. The renderer needs matrix data in the layout OpenGL consumes.
- **Decision**: Implement math, scene, geometry and asset loading in pure Python, with `numpy` only at the GPU buffer boundary. Store `Mat4` column-major and expose `flat()` for direct uniform upload; keep vectors and transforms immutable.
- **Consequences**: No C extension or native build, and tests run with the standard Python toolchain. Per-object Python work remains the scaling limit for very large scenes; batching and instancing are future work.

### ADR-003: Verify rendering headlessly and cache GPU buffers by mesh identity

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Agents and CI cannot rely on a visible window or a human looking at the screen, yet renderer regressions must be caught. Re-uploading static meshes every frame would waste bandwidth.
- **Decision**: Create a hidden GLFW window for integration tests, read pixels with `glReadPixels`, and write PNG frames with a stdlib writer. Upload each immutable `MeshData` once into a VAO/VBO/EBO and cache it by identity in `Renderer`.
- **Consequences**: Renderer behaviour is observable in automated tests and screenshots, and static geometry has no per-frame upload cost. Tests require a machine with an OpenGL 3.3 context; the dependency is documented in the README.

### ADR-004: Make a deterministic seeded expedition the engine core

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Rendering alone did not make Keystone a game engine. Sibling projects already prove procedural worlds, seeded replay and AI-addressable simulation; the engine needed one loop that binds them and runs without a GPU.
- **Decision**: `keystone.sim.World` owns seed, time, player, terrain, dungeon, movement, mode transitions and `state_hash()`. It imports no OpenGL. `keystone.expedition.Expedition` is the view/adapter that rebuilds a `Scene` on mode changes; `keystone.harness` drives the same world from JSON actions.
- **Consequences**: The same run can be rendered, replayed headlessly or hashed in tests. Terrain, dungeon, collision and atmosphere become reusable systems rather than demo code. The simulation contract must stay stable; changing generation or movement changes replay hashes and needs an ADR.

### ADR-005: Add vertex colors, static batching and a local point light

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Procedural terrain needs per-vertex biome colors; a forest of individual nodes would cost one draw call per tree; the enclosed crypt needs a local light source.
- **Decision**: `MeshData` gains optional per-vertex RGB (11 floats per interleaved vertex). `MeshBuilder.add_mesh` merges primitives into a single indexed mesh. `Scene.point_light` adds one optional warm point light with quadratic falloff, used as the player torch in the dungeon.
- **Consequences**: The GPU layout and shader gain a color attribute and point-light uniforms; all existing meshes default to white vertex colors. The expedition renders in about ten draw calls. Only one point light is supported per scene; multiple lights need a future lighting pass.

### ADR-006: Extract algorithms, not AGL source, into the AL-1.1 engine

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Several sibling games contributed proven algorithms, but they are AGL-1.1 projects while Keystone is AL-1.1 software.
- **Decision**: Reimplement the useful algorithms as new modular Python (FBM/heightfield/atmosphere from Aldervale, room/corridor/FOV/BFS and harness shape from Crypt-Crawler, collision ideas from Dustline). Do not copy AGL source files or assets. Credit the sources in the README and record any future direct reuse in a new ADR after a license review.
- **Consequences**: Provenance is explicit and the engine stays under AL-1.1. Direct code or asset reuse remains a deliberate, reviewed action rather than an accident of porting.

### ADR-007: Combat is a deterministic core mechanic, not a separate mode

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The seeded expedition had exploration and collision but no threat, fail state or reason to move. Dustline already proves an archetype/wave/boss model that suits the existing auto-render loop.
- **Decision**: Add `keystone.combat.Combat` to `World`: seeded enemy spawns, six archetypes, contact damage, split-on-death, bomber detonation, auto-fire hitscan, escalating waves, a Warlord every fifth wave, player death and safe-point respawn. Combat is GL-free and included in `World.snapshot()` and `state_hash()`. Enemies are rendered as primitive nodes; HP/wave/kills appear in the window title.
- **Consequences**: The core loop gains a fail state and combat state becomes part of replay hashes. Balance edits that change spawns or damage change hashes and need the harness selftest updated. No HUD yet, and only one weapon; weapons, upgrades, affixes and loot remain future work.

### ADR-008: Gate the crypt with a deterministic light lock

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The portal opened unconditionally, so the new world had no spatial puzzle and Iris's beam mechanic was unused. A full 3D light simulation would be larger than the core loop needs.
- **Decision**: Add `keystone.beams.LightLock`: a seeded 2D circuit at the portal with a red emitter, green dye, two `/` or `\` mirrors, a yellow (red+green) receiver, additive color masks, cycle-safe tracing and a solved state. `World` gates portal entry on it, rotates the nearest mirror with `E`, and includes its snapshot in the replay hash. `Expedition` renders the circuit and rebuilds it when the mirror version changes.
- **Consequences**: The crypt is now locked by a solvable puzzle; the harness gains a `rotate` action and `light_lock` state. The puzzle is local to the portal and not yet a full chamber system; lenses, movable emitters and in-dungeon locks are future work. Changing the layout or initial orientations changes replay hashes.

### ADR-009: Add a Weft-style Hamiltonian room-chain layout

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The crypt's rooms-and-corridors layout was the only dungeon topology. Weft's Hamiltonian route generator guarantees full coverage and offers a visibly different, deterministic layout that fits the existing `Dungeon` interface.
- **Decision**: Add `keystone.procedural.weave.WeaveLayout`: a 4×3 Hamiltonian room path with Warnsdorff ordering and connectivity checks, cut into three colored thread segments, expanded into 7×7 rooms joined by corridors. `World(layout=auto)` chooses weave for even seeds and crypt for odd seeds; `crypt`/`weave` force one. Room floors carry the thread color and `World.snapshot()` includes the weave path/segments.
- **Consequences**: The engine now has two deterministic dungeon topologies and the CLI/harness expose `--layout`. Changing the grid, room size or path changes hashes and screenshots. The weave is a chain, not a loop or branch graph; those remain future work.

### ADR-010: Make the cyber network the dungeon objective

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The dungeon exit opened unconditionally once the light lock was solved, so the crypt had no infiltration objective and Cyberpulse's network/living-alert model was unused.
- **Decision**: Add `keystone.procedural.network.Network`: a seeded graph of four terminal rooms selected from reachable non-spawn/non-exit rooms, a deterministic link tree plus one extra link, four-step hacks, alert gain/decay and a hunter response at 50+ alert. The exit is sealed until every terminal is hacked. Terminals and links render in the dungeon; network state is included in `World.snapshot()` and `state_hash()`.
- **Consequences**: A dungeon run now has an objective beyond survival and navigation; hacking creates risk and combat pressure. Terminal count/link topology changes hashes and screenshots. The current hack is a progress counter, not Cyberpulse's frequency/buffer/hash puzzle variants; those remain future work.

### ADR-011: Add a free-flight space survey as the second playable mode

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Keystone only had the ground expedition. VoidFarer already proves procedural systems, orbiting bodies, hyperlane connectivity and a scan/survey loop; a self-contained mode would prove the engine is not tied to one game.
- **Decision**: Add `keystone.procedural.space` for deterministic six-system galaxies, `keystone.space.SpaceWorld` for free flight, body scans, survey completion and gate jumps, and `keystone.space_expedition.SpaceExpedition` for the starfield/planet/gate scene and controls. `--space` selects the mode; `keystone.space_harness` exposes catalog/run/selftest without a GPU.
- **Consequences**: Keystone has two independent playable modes and two headless harnesses. Space has no combat, trade or multi-ship systems yet; those are future work. Orbit phases, scan state, ship position and system links are part of the space replay hash.

### ADR-012: Separate the engine core from game modules and freeze genre work

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Combat, light locks, weave layouts, cyber networks and the space survey were built beside the renderer and math but treated as engine mechanics. They are games built on the engine, and the core still lacks a game-agnostic module contract, generic input/replay, physics, assets, audio and serialization.
- **Decision**: Freeze genre feature work. Define `keystone/` as core only and `games/` as optional examples/modules. Introduce a five-operation `GameModule` protocol, `ActionState`, a game registry and a game-agnostic `Engine`; core must never import `games.*`. Preserve the current features by moving them to `games/expedition`, `games/space` and `games/showcase` after this document is reviewed. The full boundary, inventory, dependency rules, module roadmap and staged refactor sequence are in `docs/ARCHITECTURE.md`.
- **Consequences**: No new genre modules until the core split is accepted. The current v0.7.0 tree keeps running during review; the next work is the boundary refactor, then real core systems (physics, assets/serialization, scene/ECS, renderer, input/audio, tooling). Existing replay hashes and screenshots may change when modules move.

### ADR-013: Remove the genre prototypes and ship a core-only engine

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The user rejected the game mechanics as engine core and directed a game-agnostic engine with the prototypes removed. ADR-012 described the split; this ADR executes it.
- **Decision**: Delete the expedition, combat, light-lock, weave, network, space and showcase modules, their tests and screenshots. Keep a game-agnostic core with a five-operation `GameModule` protocol, a generic `Engine`, `ActionState`/`InputMap`, `FixedStepClock`, collision primitives, `CommandLog`/`stable_hash`, atomic JSON persistence and the `CubeDemo` smoke test. External games load through `--game package.module:Factory`.
- **Consequences**: v0.8.0 is much smaller and contains no genre rules. The deleted prototypes remain in git history but are not part of the package. The engine now has a real core API to extend; physics, assets, audio, ECS and tooling remain roadmap items.

### ADR-014: Add a no-OpenGL simulation path and machine-readable frame reports

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: AIKit, CI and AI model tooling need to drive and inspect the engine without a desktop window or GPU. A PNG alone is not enough for a model to reason about scene layout, and creating an OpenGL context on every test host is fragile.
- **Decision**: Add `keystone.headless.run_simulation()` and `load_actions()` to apply JSON action scripts directly to a `GameModule` with no GL context. Add `keystone.analysis.analyze_frame()` and `Engine.capture()` to emit a schema-1 JSON report beside a PNG: image hashes, mean/luminance statistics, content bounding box, dominant colors, an 8×8 luminance grid, projected screen positions and mesh bounding boxes for every scene node. CLI gains `--simulate`, `--actions`, `--trace`, and `--report`.
- **Consequences**: CI and AI tests can run game logic on GPU-less hosts through `--simulate`; rendered reports still require OpenGL. The report schema is versioned (`schema: 1`) and stable action/snapshot hashes make model-driven regressions reproducible. Pixel statistics are descriptive, not a visual-quality metric.

### ADR-015: Add discovery, deterministic test helpers and report comparison

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: A headless command and a single frame report are not enough for an AI client: it must discover the action/snapshot contract, assert a scenario is deterministic, and compare a baseline against a new frame. Without a stable contract those steps become ad-hoc scripts.
- **Decision**: Add `describe_game()` and `--describe` for capability/action/snapshot discovery; `keystone.testing.run_script()`, `verify_determinism()` and `assert_deterministic()` for deterministic scenarios; and `analysis.compare_reports()` for image/report/stat/node diffs. All are core, GL-free where possible, and versioned separately from a game's own actions.
- **Consequences**: AI clients have a discovery → simulate → verify → render → compare loop with JSON evidence. Reports remain descriptive rather than aesthetic judgments, and games still own their action semantics.

### ADR-016: Make verification and baseline comparison first-class CLI workflows

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: `keystone.testing` and `compare_reports()` were library-only, forcing an AI client to write Python wrappers for the two most common checks: repeat a scenario deterministically and gate a frame against a baseline.
- **Decision**: Add `--verify-determinism` (no GL, two runs, exit 0 only on matching hashes) and `--compare-baseline` (requires `--headless` and `--report`, prints image/stat/node diff, exits non-zero on image change). Publish `REPORT_SCHEMA` through `describe_game()`/`--describe`.
- **Consequences**: AI/CI clients get direct exit-code gates and schema discovery. Visual comparison is image-hash first; descriptive statistics and node changes are evidence, not aesthetic judgment.

### ADR-017: Support explicit expected-hash gates and an AI workflow guide

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: Determinism was checkable by running twice, but an AI client also needs to pin a known-good result and fail on drift in one command. The workflow was spread across README sections.
- **Decision**: Add `--expect-hash <32-hex>` to `--simulate` and `--verify-determinism`; mismatches return 1 and include `expected_hash`. Add `docs/AI_GUIDE.md` covering discovery, simulation, hash pinning, rendering, reports and baseline comparison.
- **Consequences**: A model can gate a known outcome directly. Expected hashes are explicit operator input, never silently refreshed; changing game behavior requires updating the pin deliberately.

### ADR-018: Add a dependency-free PNG reader and visual pixel diff

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The report comparison could say that an image changed, but an AI or human reviewer had no pixel-level artifact or changed-region evidence.
- **Decision**: Add `png.read_png()` for 8-bit RGBA non-interlaced PNGs (all PNG filters), and `analysis.diff_images()` to compare two PNGs, write a visual diff, and report changed pixels/ratio, bbox, mean/max channel delta. Wire `--diff-out` into `--compare-baseline`.
- **Consequences**: Baseline checks now produce both JSON and a diff image without third-party imaging libraries. The reader intentionally supports only RGBA 8-bit non-interlaced files; other PNG variants fail with a clear error.

### ADR-019: Give the human runtime a first-class, game-agnostic HUD

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The engine had become excellent for AI clients but a person launching the window had no in-engine HUD, control reference or pause feedback; the title bar was the only status surface.
- **Decision**: Add `keystone.ui` (embedded 5×7 bitmap font, clipped `Canvas`, `HumanOverlay`/`HudState`) and `gpu.ui_renderer.UiRenderer` for one alpha-blended screen-space draw. The Engine draws the overlay after the 3D scene, toggles it with `H`, pauses gameplay with `P` without stopping rendering, and exposes `--ui`/`--no-ui`. Windowed runs default to UI on; headless captures default to off so existing report hashes and baselines stay stable.
- **Consequences**: People get a readable HUD, controls help and pause banner with no font/asset dependency. The overlay is presentation-only and never mutates game state. UI pixels are included in `--ui` reports, so UI screenshots can be reviewed by the same report/diff workflow; `--no-ui` preserves clean scene captures.

### ADR-020: Make the pause menu interactive with mouse and keyboard

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The human overlay displayed a pause banner but offered no actions; a person still had to remember `P` to resume and `Esc` to quit, and there was no clickable UI or reusable menu state for games.
- **Decision**: Add a pure `PauseMenu` (Resume / Hide HUD / Quit), draw hit-testable buttons with selected and hover states, add a one-frame `ActionState.mouse_clicked` edge, bind `Enter` to `confirm`, release the cursor while paused, and expose `Engine.apply_ui_action()` for scripted use. `W`/`S` or arrows move the selection.
- **Consequences**: Pausing now opens a real menu that works by mouse or keyboard; resuming recaptures the cursor. `mouse_clicked` defaults to false so existing action scripts stay valid. Menu selection and hitboxes are presentation state only; games remain unaware of the overlay.

### ADR-021: Let games contribute HUD pixels through an optional hook

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The human overlay showed engine/runtime information, but an external game had no supported way to draw its own health, score or panels; it would have needed to fork the engine or draw 3D proxies.
- **Decision**: If a game exposes a callable `draw_ui(canvas, state)`, the Engine passes it to the overlay builder, which calls it before drawing the engine HUD and pause menu. The hook receives the same `Canvas` and `HudState` used by the HUD and is skipped when the overlay is hidden or UI is disabled. `describe_game()` reports `capabilities.game_ui`.
- **Consequences**: Games can add HUD pixels with the dependency-free font/canvas toolkit while the required five-operation contract stays unchanged. The hook is presentation-only and receives no input dispatch; game UI participates in `--ui` captures and report/diff workflows like any other pixel.

### ADR-022: Capture structured UI metadata in schema-2 frame reports

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: The human UI was visible in PNGs, but an AI reading a frame report could not tell which labels and buttons were on screen, which menu item was selected, or whether the game was paused; UI regressions were only pixel diffs.
- **Decision**: Record `TextElement`/`ButtonElement` metadata on the `Canvas`, add `ui.report.describe_canvas()`, and include an optional `ui` object in the frame report: visibility, pause state, labels with text/position/scale/color and buttons with label/action/rect/selected/hovered. Bump the report schema to 2; include `ui` in the report hash only when present; diff UI labels/buttons in `compare_reports()`; accept schema-1 reports as baselines. Add `--start-paused` so the pause menu can be captured headlessly.
- **Consequences**: AI and human reviewers get structural UI evidence alongside pixels. `--no-ui` reports keep `ui: null` and their old hash behavior; schema-1 baselines remain comparable. UI metadata is presentation-only, and volatile labels (FPS/time) make deterministic headless captures the reliable baseline.

### ADR-023: Add immutable RGBA textures and material texture metadata

- **Date**: 2026-10-30
- **Status**: Accepted
- **Context**: `MeshData` carried UVs and primitives filled them, but the renderer ignored them; materials had only a flat color and a world-space checker. Textured surfaces are a basic 3D engine capability, and AI graphics reports could not identify which texture a node used.
- **Decision**: Add immutable `TextureData` (RGBA8, PNG and procedural checker sources), `Material.texture`, a renderer-owned `GpuTexture` cache with repeat wrapping and mipmaps, and GLSL texture sampling multiplied into the base color. Use a checker texture on the sample floor. Report material color/specular/shininess/checker and texture name/dimensions/SHA-256; bump the report schema to 3 and accept schema 1/2 baselines.
- **Consequences**: Games get textured materials with no new dependency beyond the existing PNG reader and PyOpenGL. Textures are opaque (alpha is not blended), one sampler per material, and color management stays linear/untagged. The renderer releases cached textures with meshes; `compare_reports()` flags material changes on a node.

### ADR-024: Give scene nodes stable IDs, tags, layers and typed components

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Nodes were addressable only by name, so two nodes with the same name could not be distinguished, and the engine had no game-agnostic way to attach behaviour or query entities. AI frame reports keyed nodes by that colliding name.
- **Decision**: Add optional `Node.id`, `tags`, `layer` and typed `components` with add/get/require/remove helpers. `Scene` allocates deterministic per-scene IDs (`node-1`, `node-2`, ...) on attach or first traversal, preserves explicit IDs, rejects duplicates, and keeps an ID across reparenting. Add `Scene.query()`, `Scene.find()` and `Scene.find_by_id()`. Bump the frame report schema to 4 with `id`, `parent_id`, `tags`, `layer` and component names; `compare_reports()` keys nodes by ID only when both reports are schema 4, and keeps name keying for older baselines. The sample uses explicit IDs.
- **Consequences**: Games can address, tag and query nodes without a name collision, and AI diffs can distinguish duplicate names. Auto IDs depend on attach/traversal order and are scene-local, not a cross-process save format; a future serialized scene must persist assigned IDs. Queries are linear scans, and the report hash changes for schema 4.

### ADR-025: Add a local web console, JSON API and WebGL2 scene viewer

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: The AI surface was CLI-only and the human surface was a desktop window. AI clients and browser users could not inspect the same game contract, scene state or deterministic simulation over a local interface.
- **Decision**: Add `keystone.web` with a versioned scene document (schema 1), a stdlib `ThreadingHTTPServer` and a vanilla web console. Endpoints are `GET /api`, `GET /api/health`, `GET /api/describe`, `GET /api/scene` and `POST /api/simulate`; responses reuse `describe_game()`, `run_simulation()` and the scene export. Add `--serve`, `--host` and `--port`. The console has a WebGL2 viewer for shared meshes, RGBA textures, camera, lights and fog, and CORS headers for local clients.
- **Consequences**: AI clients and the bundled browser UI share one JSON contract without a new runtime dependency or a server GPU requirement. The server binds to loopback by default and is not an internet service; simulation mutates one in-memory game behind a lock. The WebGL preview is approximate, while the OpenGL renderer remains the pixel authority. The static assets are package data, so a source checkout and an installed wheel both serve the console.

### ADR-026: Add broadphase, character movement, triggers and filtered raycasts

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Physics stopped at individual ray and overlap queries. Games had to scan every collider, reimplement character movement, and hand-roll trigger state; none of those are genre rules, so they belong in the core.
- **Decision**: Add `keystone.broadphase.SpatialGrid` (uniform grid, exact overlap filtering, insertion-order results), `keystone.character.CharacterBody`/`CharacterController` (AABB body, horizontal wish velocity, gravity, swept axis resolution, ground state), `keystone.triggers.TriggerVolume`/`TriggerTracker` (sorted enter/exit/active events), and `AABB.low/high/contains/overlaps` plus `RayHit`/`raycast()` with an optional key/box predicate. Keep all state caller-owned and GL-free.
- **Consequences**: Games get deterministic nearby-body queries, reusable character movement and trigger reactions without a genre contract. The controller covers axis-aligned static colliders only; slopes, step-up, moving platforms, capsules and a physics solver remain future work. Cell size controls broadphase performance, never correctness, and trigger tracker state is mutable by design.

### ADR-027: Add the asset registry and hot reload

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Meshes, materials and textures were anonymous objects passed straight to nodes, so games could not address, deduplicate, inspect or refresh them. The roadmap's asset step needed a game-agnostic registry and a deterministic hot-reload path before material graphs and glTF import.
- **Decision**:
  1. Add `keystone.assets` with `AssetRegistry`, `AssetRecord` and `ASSET_KINDS`. Kinds are inferred from `MeshData`, `Material` and `TextureData`, with explicit kind validation, id and dependency validation, stable content digests, duplicate groups, missing-dependency reports and a JSON-safe `describe()`.
  2. Add `keystone.asset_io` with `AssetSource`, `Fingerprint`, `ReloadReport`, default PNG and OBJ loaders, suffix-based kind inference, `load_asset` and `fingerprint`. `register_file` loads a source and binds it; `refresh()` re-reads changed files, keeps the last good payload on a loader failure or a missing file, reports persistent errors, and preserves dependencies.
  3. Export `AssetRegistry` from the package and wire `CubeDemo` through the registry so the smoke test proves asset identity.
- **Consequences**: Games get stable asset ids, content hashes, dependency tracking and synchronous hot reload with no new dependencies or background thread. Broken or missing files surface in `ReloadReport` instead of crashing the render loop. Material graphs and glTF import remain future work.

### ADR-028: Add declarative material graphs

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Materials were literal `Material` values, so reusable procedural surfaces, texture references and mixes had to be rebuilt by hand in every game and could not be serialized or inspected by AI clients.
- **Decision**:
  1. Add `keystone.material_graph` with `MaterialGraphNode` and `MaterialGraph`. Node kinds are `color`, `float`, `checker`, `texture`, `mix` and `material`; inputs form a directed graph evaluated in topological order with cycle detection.
  2. Parameters are frozen `(name, value)` pairs and graphs serialize to schema-1 JSON with `to_dict()`/`from_dict()`, keeping `Vec3` as channel arrays and parameters as JSON values.
  3. `evaluate(textures=..., registry=...)` resolves color, checker and texture nodes, including asset ids through an `AssetRegistry`, and returns one `Material`.
- **Consequences**: Games and AI clients can build, serialize, inspect and evaluate materials without OpenGL. Graphs are immutable and deterministic; texture payloads are referenced by asset id or name rather than embedded. Material graphs do not change the report schema or the renderer contract.

### ADR-029: Add dependency-free glTF 2.0 import

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: Keystone could load OBJ and PNG assets but had no path for modern glTF scenes, so AI and game authors had to convert assets or hand-build meshes. A glTF importer must not add a runtime dependency or require OpenGL.
- **Decision**:
  1. Add `keystone.gltf` as a package with `io`, `textures`, `materials`, `meshes`, `scene` and `loader` modules. `load_gltf(source, registry=None)` accepts a path, JSON text, bytes or an already-parsed mapping and returns a `GltfImport`.
  2. Decode external and embedded base64 buffers, typed accessors (SCALAR/VEC2/VEC3/VEC4/MAT4), meshes with optional normals/UVs/colors/indices, PBR materials (base color, roughness to specular/shininess, base color texture), PNG images and node/scene hierarchies with TRS or matrix transforms.
  3. Reuse `TextureData.from_png_bytes`, `MeshData`, `Material` and `Scene`, and optionally register imported assets in an `AssetRegistry`.
- **Consequences**: Games and AI clients can import glTF 2.0 scenes without new dependencies or a GPU. JPEG images, animations, skins, morph targets and multi-primitive mesh splitting beyond the first primitive remain future work. Matrix decomposition assumes affine transforms with non-zero scale.

### ADR-030: Add versioned scene snapshots and undo/redo history

- **Date**: 2026-10-31
- **Status**: Accepted
- **Context**: The engine had no way to save, restore or roll back a scene graph without OpenGL or a game-specific serializer, and replay/inspection workflows need deterministic state checkpoints.
- **Decision**:
  1. Add `keystone.history.History`, a bounded undo/redo stack that deep-copies snapshots and reports `can_undo`/`can_redo`.
  2. Add `keystone.scene_snapshot` with `SCENE_SNAPSHOT_VERSION = 1`, `scene_to_dict` and `scene_from_dict`. Snapshots store node identity, hierarchy, tags, layer, visibility, transforms and camera state, plus mesh/material asset ids when an `AssetRegistry` is supplied.
  3. Rebuild parents through `Node.add_child`, validate the snapshot version and reattach assets from the registry on load.
- **Consequences**: Games and AI clients can save, restore and roll back scene graphs without OpenGL or a GPU. Mesh and material payloads are referenced by asset id rather than embedded, so a snapshot is small and a missing asset leaves the node without that payload. Undo/redo state is caller-owned and in memory.

### ADR-031: Harden glTF import and scene snapshot correctness

- **Date**: 2026-11-01
- **Status**: Accepted
- **Context**: Review of the v0.23-v0.25 additions found silent correctness failures. Generated glTF normals followed vertex order instead of triangle indices, non-triangle primitive modes were treated as triangles, cyclic node hierarchies recursed until `RecursionError`, normalized integer accessors returned raw byte values, sparse accessors decoded as zeros, snapshots dropped lighting and atmosphere, and snapshot loaders accepted duplicate ids and dangling parents.
- **Decision**:
  1. Decode indices before normals and generate normals from the actual triangle list; reject primitive modes other than TRIANGLES and reject unknown material indices.
  2. Apply glTF normalization rules to signed and unsigned integer accessors and refuse sparse accessors with a clear error instead of returning base or zero data.
  3. Track visiting nodes during hierarchy construction so a cycle raises `ValueError`.
  4. Extend scene snapshot schema 1 with optional camera lens and environment fields (ambient, background, sky, fog, directional and point lights) and reject duplicate ids, unknown parents and self-parenting. Older schema-1 documents still load with engine defaults.
  5. Make a material graph's `texture_name` fail when it cannot resolve, matching texture nodes.
- **Consequences**: Malformed or unsupported glTF and snapshot documents fail early with actionable errors instead of producing wrong geometry or state. Snapshots round-trip the visible environment, and schema 1 stays backwards compatible because every new field is optional.

### ADR-032: Add GLB containers and tighten glTF and snapshot validation

- **Date**: 2026-11-01
- **Status**: Accepted
- **Context**: A second review of the v0.25.1 format work found that binary `.glb` files failed as invalid UTF-8 JSON, out-of-range material texture indices were silently ignored, accessor offsets and bufferView bounds were not checked, snapshots could attach a material asset as a node mesh, non-string ids were coerced, and asset lookup scanned the whole registry once per distinct payload.
- **Decision**:
  1. Parse GLB version 2 headers and chunks in `keystone.gltf.io`, feed the first buffer without a uri from the BIN chunk, and reject truncated containers, wrong versions, duplicate JSON chunks and invalid buffer lengths.
  2. Validate accessor and bufferView offsets against the declared bufferView byteLength and reject material texture indices that do not resolve.
  3. Require string snapshot node ids, reject non-mapping camera and transform fields, validate asset kinds on reattachment, and build one payload-to-id index per snapshot instead of scanning the registry per node.
- **Consequences**: Standard GLB bundles import through the same path as JSON glTF. Malformed glTF and snapshot documents fail with precise errors instead of silently losing textures or attaching the wrong payload. Snapshot schema 1 is unchanged; only validation is stricter and serialization is linear in registry size.

### ADR-033: Add GPU hardware instancing for repeated static geometry

- **Date**: 2026-11-02
- **Status**: Accepted
- **Context**: Static batch merging baked still geometry into one mesh, but repeated rigid nodes (including moving ones sharing a mesh/material) still cost one GL draw call each. Draw-call count limited scene scale while pixels stayed identical.
- **Decision**: Add `keystone/gpu/instancing.py` with deterministic `group_instances()`/`plan_instanced()` grouping by identical mesh/material payloads, an instanced vertex shader with per-instance model/normal divisor attributes, and a renderer path issuing one `glDrawElementsInstanced` per multi-node group. Single-node groups keep the uniform path. Expose counts via `last_stats`, `/api/inspector` and `capabilities.instancing`. Frame report schema stays at 5.
- **Consequences**: Repeated meshes render with fewer draw calls and identical pixels; CubeDemo keeps 5 plain draws while a 200-cube test scene collapses to 1 call. Single-instance fallback avoids divisor state leaks. Report hashes and simulation hashes are unchanged. Shadows, post-processing, skinning and editor work remain future.

### ADR-034: Add the seeded bot playtester as first-class engine tooling

- **Date**: 2026-11-02
- **Status**: Accepted
- **Context**: `--simulate` replayed fixed action scripts, so an AI client could not bot-play a game end to end, diff a bot run against a pinned baseline, or ask the engine whether a configuration is winnable at all. Each check was an ad-hoc script with its own hash semantics.
- **Decision**:
  1. Add `keystone.playtest` with a `BotPolicy` protocol (`reset`/`select` over snapshots, action specs and a private `random.Random`) plus `RandomPolicy`, lookahead-free bandit `GreedyPolicy` and `ScriptedPolicy`. `run_bot()` records a schema-1 transcript wrapping the exact `CommandLog` shape, so `--expect-hash` pins it and `--replay`/`run_log` replay it with the same `stable_hash(final)`.
  2. Add `diff_transcripts()` (hash fast-path, first-divergent-frame walk on traced runs), frozen schema-1 `make_report()` shared byte-identically with thin web adapters (`POST /api/simulate` plus the same policy/seed envelope; no browser driving), and canonical `canon()` projection (drops `time`, rounds floats) for visited-sets.
  3. Add `validate_fairness()` with a defined rejection predicate: `unfair` only for spawn-terminal, nondeterministic, no-witnessed-win-with-reference, or reference-longer-than-time-limit runs; `fair` requires a deterministic witnessed win; anything else (no outcome signal, no reference, exhausted state budget) is `unknown`, never a false `fair`. Games opt in via `outcome`/`score` snapshot keys; the five-operation contract is unchanged and `describe_game()` gains only the additive `capabilities.playtest` flag.
  4. Add `--playtest --policy {random,greedy,scripted} --seed --script --transcript-out` to the CLI (standalone no-GL command, wall-clock capped, unfair verdict exits 1). The proving stub is `tests/support_maze_game.py`, a deterministic grid fixture outside `keystone/` so the boundary test stays green; maze-exact BFS ground truth lives fixture-side, the core stays sampling-based.
- **Consequences**: Bot runs are deterministic first-class artifacts next to `--simulate`; unfair configurations are rejected with machine-readable reasons. Cost ceilings (`frames`, `max_wall_seconds`, `max_states`) bound every search; greedy lookahead and exhaustive game-tree search are explicitly deferred. Bumps version to 0.33.0.

### ADR-035: First screenshot keepers are the scripted HUD render and the live web console
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: Keystone had approved cube/KE brand (6/6) but `assets/screenshots/` did not exist and `media.json screenshots: []`; the legacy `assets/engine.png` sample predates the bitmap-font HUD/profiler and carries no commit record.
- **Decision**: Keep `engine.png` as legacy art; register `2026-11-03-hud.png` (scripted `python -m keystone --headless --frames 1 --size 960x540 --ui --out`, commit `e6c6318`, deterministic) and `2026-11-03-console.png` (`python -m keystone --serve`, WebGL viewer, viewport 1440x900) in `.aikit/media.json` and the README `aegean:screenshots` block.
- **Consequences**: README proves both the headless and the served workflows against the documented cube-demo smoke test; the HUD render re-renders byte-identical on demand. Reproduce with the two commands above.

### ADR-036: Add deterministic directional shadow mapping to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The renderer roadmap listed shadows as remaining; every game needs depth cueing but no game should implement its own light pass. The change must stay render-only so simulation hashes never move.
- **Decision**: Add frozen `Scene.shadow` (`ShadowSettings.enabled`, default on) plus `keystone/gpu/shadow.py` (fixed 1024 depth FBO, ortho extent 12, near 1, far 40, bias 0.005, deterministic light VP). Render a depth-only pass reusing `group_instances()` ordering (one depth draw per instance; instanced divisor path deferred), then a PCF 3x3 lit pass. Gate with `--shadows/--no-shadows`; `--no-shadows` preserves legacy pixels. Bump frame report schema 5 to 6 with `scene.shadows`, add `capabilities.shadows`, persist optional `environment.shadow` in snapshot schema 1, export `shadows` in the web scene/inspector, and extend `last_stats` with `shadow_calls/shadow_map_size/shadows_enabled` plus a HUD `SHADOW N PASS` line.
- **Consequences**: CubeDemo renders with shadows by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` is unchanged because shadows never enter `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: scene draw calls unchanged, `shadow_calls <= 5` on CubeDemo, wall time `<=1.3x` no-shadow baseline. Post-processing, sRGB, skinning and GPU sprite work remain future.

### ADR-037: Add an sRGB-correct linear lighting pipeline to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The renderer shaded and fogged raw sRGB bytes as if linear, so mid-tones were systematically dark; every game pays that error but no game should implement its own color pipeline. The fix must stay render-only so simulation hashes never move.
- **Decision**: Add frozen `Scene.color` (`ColorSettings.enabled`, default on) plus in-shader `pow 2.2` decode/encode (no driver `GL_SRGB` dependency). Decode the combined `base_color`, ambient, light/point radiances, emissive and fog color, shade linear, fog in linear, encode the final color and the sky gradient; the UI overlay stays display-referred and unencoded. Gate with `--srgb/--no-srgb`; `--no-srgb` preserves legacy pixels. Bump frame report schema 6 to 7 with `scene.color`, add `capabilities.srgb`, persist optional `environment.color` in snapshot schema 1, export `color` in the web scene/inspector, and extend `last_stats` with `srgb_enabled`.
- **Consequences**: CubeDemo renders sRGB-correct by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` is unchanged because color never enters `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: no new draws or triangles, wall time `<=1.05x` no-sRGB baseline. Post-processing, skinning and GPU sprite work remain future.

### ADR-038: Add a deterministic post color-grade to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The renderer stopped at sRGB encode, so every game shipped ungraded linear output with no vignette control; each game would otherwise hand-roll its own grade. The change must stay render-only so simulation hashes never move.
- **Decision**: Add frozen `Scene.post` (`PostSettings.enabled`, default on) plus `keystone/gpu/post.py` (fixed exposure 1.12, vignette 0.28, GL-free `grade_color`/`vignette_factor`). Apply the grade in-shader after the sRGB encode (main pass via `gl_FragCoord`/`u_resolution`, sky via `v_uv`), before the UI overlay; no FBO, no new draws. Gate with `--post/--no-post`; `--no-post` preserves legacy pixels. Bump frame report schema 7 to 8 with `scene.post`, add `capabilities.post`, persist optional `environment.post` in snapshot schema 1, export `post` in the web scene/inspector, and extend `last_stats` with `post_enabled` plus a HUD `POST GRADE` line.
- **Consequences**: CubeDemo renders graded by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` is unchanged because post never enters `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: no new draws or triangles, wall time `<=1.02x` no-post baseline. Bloom, full post chain, skinning and GPU sprite work remain future.

### ADR-039: Add a deterministic bloom glow to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The renderer stopped at exposure/vignette, so bright surfaces and emissive highlights had no glow and every game would hand-roll its own bloom; the change must stay render-only so simulation hashes never move.
- **Decision**: Add frozen `Scene.bloom` (`BloomSettings.enabled`, default on) plus `keystone/gpu/bloom.py` (fixed threshold 0.72, knee 0.12, intensity 0.35, GL-free `bloom_factor`/`bloom_color` on display-referred luma). Apply the glow in-shader after the sRGB encode and before the post grade (main pass and sky via `v_uv`), before the UI overlay; no FBO, no blur pass, no new draws. Gate with `--bloom/--no-bloom`; `--no-bloom` preserves legacy pixels. Bump frame report schema 8 to 9 with `scene.bloom`, add `capabilities.bloom`, persist optional `environment.bloom` in snapshot schema 1, export `bloom` in the web scene/inspector, and extend `last_stats` with `bloom_enabled` plus a HUD `BLOOM GLOW` line.
- **Consequences**: CubeDemo renders with glow by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` is unchanged because bloom never enters `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: no new draws or triangles, wall time `<=1.05x` no-bloom baseline. Full blur/mip-chain bloom, skinning and GPU sprite work remain future.

### ADR-040: Add deterministic bloom diffusion to the core renderer
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The v0.37.0 threshold glow adds sparkle but no diffusion, so bright surfaces still lack Unity-class spread and games would hand-roll blur FBOs with divergent hashes.
- **Decision**: Keep `Scene.bloom.enabled` unchanged and add frozen diffusion in `gpu/bloom.py` (5-tap weights summing to 1.0, half-res `floor(w/2)` min 1, `bloom_composite`) plus `gpu/bloom_fbo.py` (RGBA8, NEAREST, CLAMP_TO_EDGE, completeness `Why:/Fix: --no-bloom`). When bloom is on, render the scene to a full-res FBO, run bright-pass downsample + separable H/V blur + composite to the default framebuffer; when off, keep the exact legacy direct-to-screen path. No CLI, snapshot, report-schema, web, or HUD changes; `last_stats` shape unchanged.
- **Consequences**: CubeDemo diffuses bright orb/cubes with `--no-bloom` byte-identical legacy; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged because diffusion never enters `snapshot()`. Perf budget: no new scene draws, wall `<=1.35x` no-bloom median; miss falls back to threshold-only. Skinning, GPU sprites, editor remain future.

### ADR-041: Add deterministic character slopes, step-up and platform carry
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: The controller stopped at axis-aligned walls, so stairs blocked movement and platforms could not carry bodies without per-game teleports that bypass swept pushout and fork determinism.
- **Decision**: Extend frozen `CharacterController` with `slope_rise 0.55`, `slope_run 1.0`, `step_height 0.45` and `step(..., platform_velocity=None→zero)` (defaults preserve all 4-arg call sites). Fixed order: swept platform carry, X, Z, swept step-up probe (headroom, horizontal retry, settle, rise within `slope_rise*(run/slope_run+1)`), gravity Y. No new collider types (stairs, not ramps), no snapshot/report/CLI/web/GPU changes; character stays runtime-only and GL-free.
- **Consequences**: Low stairs climb, tall walls stop, carry respects walls and ledges; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged (CubeDemo never calls `step`). Perf budget: no-hit path unchanged, hit path ≤2 extra sweeps, `<=1.10x` over 10k steps/32 AABBs manual. Capsules, solvers, ladders remain future.

### ADR-042: Add deterministic particle-vs-AABB collision
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: Particles fell through floors and tunneled walls, so every game hand-rolled FX collision with divergent results.
- **Decision**: Extend `ParticleSystem.step` with `step(dt, colliders=())` and a swept point-vs-AABB pass (X→Z→Y, caller list order, `POINT_SKIN 1e-9`), response stop-at-surface with hit-axis velocity zeroed and lifetime continuing; zero colliders runs the legacy code verbatim. No `Emitter`/`Particle`/`particles_report` changes (both schema 1 frozen), no snapshot/CLI/web/GPU changes; colliders are per-step args, never state.
- **Consequences**: Sparks rest on floors, fast shots stop at walls without tunneling; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged (CubeDemo uses no particles). Perf budget (measured, steady-state medians): `<=2.0x` stress (1k particles × 8 AABBs, observed ~1.8x) and `<=1.8x` typical (200 × 2, observed ~1.7x); zero-collider path is byte-identical legacy code. Bounce, friction, kill modes, GPU sprites and broadphase acceleration remain future.

### ADR-043: Add deterministic linear-blend skinning
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: Every rigged character needs deformation, but the mesh core stopped at rigid bind poses, so games would hand-roll CPU skinning with divergent poses, hashes, and batching.
- **Decision**: Add optional skin data to `MeshData` (per-vertex joints/weights up to 4, joint names, inverse bind matrices; defaults preserve all legacy constructors and `interleaved()` bytes) plus `keystone/skin.py` (`bone_matrices` id-or-name resolution in joint order, `skin_point`/`skin_mesh` CPU oracle mirroring the vertex shader). GPU path: new `SkinnedGpuMesh` (19-float stride, attribs 11/12) + skinned vertex/depth programs (`u_bones[64]`, `vec4` joints) + per-model single draws; unskinned VAO/program/stride untouched. glTF: `JOINTS_0`/`WEIGHTS_0` + `skins` import with normalization and rejection rules. `plan_batches`/`merge_batches` auto-skip skinned meshes (like animated via `exclude`); `describe` gains `capabilities.skin`. No snapshot/report/CLI/web-schema changes: skin rides mesh assets, pose rides node transforms.
- **Consequences**: Rigged meshes deform deterministically on CPU and GPU with identical math; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged (CubeDemo unskinned). Perf budget: unskinned `<=1.02x` baseline, skinned `<=1.15x` equivalent verts. IK, dual quaternions, per-instance palettes, and skin-aware merging remain future. Deviations from Stage 2 mechanics: `batch.py` gained auto-skip (no `app.py` call site exists — `web/server.py` calls `merge_batches` without `exclude`); `set_mat4_array` added to `ShaderProgram` (array base location `u_bones[0]`).


### ADR-044: Add deterministic GPU point-sprite particle rendering
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: CPU particles simulated deterministically but had no GPU path, so every game would hand-roll FX quads with divergent blending, depth handling, and report hashes.
- **Decision**: Add frozen `Scene.sprite` (`SpriteSettings.enabled`, default on) plus `keystone/gpu/sprites.py` (fixed atten 180.0, size clamp 1-64px, GL-free `sprite_scale`/`soft_alpha`/`sprite_alpha`/`billboard_corners`) and a renderer instanced-quad path (per-instance offset/scale/fade-alpha, camera-right/up billboards, depth-test on with depth-write off, SRC_ALPHA blending, display-referred sprite tint with shared bloom/post grade). Engine supplies the game-owned `ParticleSystem` via the existing duck-typed `particles|fx|particle_system` channel (five-op contract unchanged). Gate with `--sprites/--no-sprites`; `--no-sprites` preserves legacy pixels. Bump frame report schema 9 to 10 with `scene.sprites` + top-level `fx`, add `capabilities.sprites`, persist optional `environment.sprites` in snapshot schema 1, export `sprites` in the web scene/inspector, and extend `last_stats` with `sprite_calls/sprites/sprites_enabled` plus a HUD `SPRITE N DRAWN` line. CubeDemo gains a seeded 64-particle fountain fixture stepped in `update()` but excluded from `snapshot()`.
- **Consequences**: CubeDemo renders soft FX sprites by default; `--simulate --frames 120` hash `772cac5232a0947b8f6d1914a5cf0cde` unchanged because sprites never enter `snapshot()`. Frame/image hashes change and were re-pinned explicitly. Perf budget: no new scene draws, `sprite_calls <= 1`, CubeDemo wall `<=1.10x` no-sprite baseline, 1k-sprite stress `<=1.25x`; shadow pass skips sprites. Bounce, per-particle color/texture, and skin-aware merging remain future.


### ADR-045: Fix four reproduced swarm defects with minimal contract-preserving patches
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Parallel analysis swarms (6 modules) returned 40+ claims; main session reproduced 6/6 sampled claims (cone-base scope reduced after sampling: cone-side normals need deeper winding-mode decision, deferred). Four minimal true defects fixed: TextureData missing from public API, CubeDemo time not reset on rebuild, ActionState string/pointer shredding, camera pitch construction/look_at crash.
- **Decision**: Import TextureData in keystone/__init__ (no new dep); reset _time in CubeDemo.build_scene; strict ActionState.from_dict type/length checks (TypeError/ValueError); clamp PerspectiveCamera pitch in __post_init__ and look_at to +-MAX_PITCH. Five regression tests added (plugin export, samples rebuild, input strict x4 asserts in 1 test, 2 camera). Deferred: cone winding, material-graph Vec3 params, PNG CRC/zlib wrap, broadphase huge-box guard, playtest/global-RNG and other unverified S3-S6 static claims (filed, not implemented).
- **Consequences**: from keystone import TextureData works; sequential run_simulation on one instance deterministic; malformed action JSON fails fast with indexable TypeError; pitch +-90deg cameras stay usable; 447 tests green, ruff clean, 6/6 aikit gates; public five-op contract, schemas and hashes unchanged (simulate hash 9993994cc8aac268c007e43d0d33c95e). Cone/material/PNG/GPU items remain future.



### ADR-046: Harden PNG, skin, scene and sample boundaries with failing-first guards
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Second verified-fix iteration over swarm claims: PNG reader ignored CRC and leaked zlib.error, MeshData accepted NaN/Inf skin weights that later poison skin_point, Node accepted mismatched component values splitting query vs get_component, CubeDemo.update crashed with bare StopIteration when orb is missing.
- **Decision**: Verify per-chunk CRC32 in read_png and wrap IHDR/zlib errors as ValueError; require finite numeric skin weights in MeshData; require isinstance(value, key) for Node components; raise RuntimeError with node name when CubeDemo orb is absent. Six regression tests added (CRC, corrupt-IDAT wrap, NaN/Inf weights, component value, orb-missing).
- **Consequences**: Corrupt PNGs fail fast with actionable ValueError; NaN weights rejected at construction; hand-built component dicts cannot desync queries; sample update error is diagnosable; 450 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged (no CubeDemo asset/behavior change on the happy path).



### ADR-047: Fix cone winding, merge normals and graph color params
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Cone side normals pointed inward with inverted winding and the base cap stored -Y normals with +Y winding; MeshBuilder transformed normals with M instead of transpose(inverse(M)), breaking non-uniform merges while the GPU renderer already used the correct normal matrix; material-graph color/checker/material/pbr params rejected Vec3 even though _json_value serializes Vec3.
- **Decision**: Flip cone side cross order and both triangle windings to outward/CCW-consistent; transform merge normals with transpose(inverse(M)) matching gpu.renderer.normal_matrix (singular matrices now raise via Mat4.inverse); accept Vec3 for color, checker dark/light and material/pbr color/emissive params. Five regression tests added (outward normals, winding-vs-normal alignment, inverse-transpose values, Vec3 color, Vec3 checker/material).
- **Consequences**: Cone lighting and culling are correct; non-uniform merges match GPU shading; graph round-trips preserve Vec3; 455 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged (CubeDemo uses no cones, merges or graphs). Skin CPU-oracle normals remain a known follow-up.



### ADR-048: Strict construction-time validation for OBJ, textures and meshes
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: OBJ silently dropped face-slash extras, vertex w components and trailing junk; TextureData.checker with a 2-channel color failed deep inside with a byte-count message; MeshData accepted short/NaN tuples and non-integer indices, deferring failure to bounds() with a misleading unpack error.
- **Decision**: Reject face corners beyond v/vt/vn, require exact v/vn arity while honoring the OBJ homogeneous w coordinate (x/w, y/w, z/w; zero w rejected), accept vt with optional w; validate checker dark/light as 3-channel sequences with a naming TypeError; validate MeshData positions/normals/colors as 3 finite numbers, UVs as 2 finite numbers and indices as integers at construction. Six regression tests added (extra slash, w handling, junk/short vertices, channel counts, malformed tuples).
- **Consequences**: Malformed assets fail at the boundary with OBJ line numbers instead of silent corruption; 460 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged (no sample asset changes). Remaining: perspective Mat4*Vec3 guard, builder/primitive UV orientation decision, docs drift, S2 CLI/replay/clock groups.



### ADR-049: Reject ignored CLI flags and harden runtime boundaries
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: --serve/--describe/--playtest/--simulate silently ignored --frames/--size/--diff-out (e.g. --describe --diff-out misreported as a baseline error); CommandLog coerced seed 3.7 to 3 and silently emptied dict frames; run_log permanently reseeded global random; read_json choked on BOM that write_json_atomic peers (load_actions) already tolerate; FixedStepClock minted 15 phantom steps on a backwards wall timestamp and froze on NaN; snapshot coerced non-string names; load_actions reported bare AttributeError without the failing index. The swarm claim that --verify-determinism --trace is accepted was refuted on reproduction (already exit 2) and dropped.
- **Decision**: Extend the standalone-command guards (serve/describe/playtest plus a new simulate window guard) to reject window flags; require integer seeds, finite positive steps and list frames in CommandLog; save/restore random state around run_log; read JSON as utf-8-sig; ignore backwards wall time without retreating the clock and reject non-finite now; require string snapshot names; wrap bad action items as TypeError with actions[i]. Eight regression tests added across CLI, replay, headless, serialization, clock and snapshot suites.
- **Consequences**: Ignored flags now fail fast at exit 2 with the naming command; replay is side-effect-free and strict at the boundary; BOM files load; clocks cannot mint debt or freeze; 467 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged. Deferred: unbind-resurrect schema, snapshot missing-asset strictness, headless hold-last semantics, UI pause-capture semantics.



### ADR-050: Guard projective misuse and close doc drift
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Mat4.transform_point silently returned non-divided points for projective matrices (eye-space z instead of NDC) while inverse() already rejected them; docs drifted (README geometry line claimed a skin export, endpoint table omitted /api/inspector and pinned schema 1, ARCHITECTURE pinned scene-doc version 1, omitted gltf/ from the layer tree and pbr from the material-graph row). ADR-029 multi-primitive note is stale (fan-out already ships) but ADRs are append-only, so it stands with this record noting the correction.
- **Decision**: transform_point (and Mat4*Vec3 through it) raises ValueError for projective matrices directing to project_point, mirroring inverse()'s affine check; analysis/world and builder paths are affine-only so behavior is unchanged. Docs: fix the geometry line, add the inspector endpoint row, correct schema versions to 2, add gltf/ and pbr to ARCHITECTURE.
- **Consequences**: Projection misuse fails fast with an actionable message; two math regression tests added; README stays within the 32500-char budget (32495) with the duplicated inspector clause folded into the endpoint table; 468 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged.



### ADR-051: Fail fast on hierarchy, script, mix and grid boundary misuse
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Node.add_child accepted duplicate ids and deferred the failure to a later read; load_actions accepted command-log documents and silently dropped their seed; mix_clips clamped per voice, making mixes order-dependent and losing headroom (+1,+1,-1 mixed to 0 instead of 1); SpatialGrid._cells_for iterated an unbounded cell range (a 4001^3-cell box projects to ~87 minutes) and insert() stored the proxy before the iteration could fail, leaving partial state.
- **Decision**: Validate duplicate ids in add_child at write time (blank ids still defer to Scene assignment); reject seed/step-shaped documents in load_actions with a --replay pointer; sum voices then clamp once in mix_clips; cap proxies at 100k cells with a finite-bounds check and materialize the cell list before mutating grid state. Six regression tests added.
- **Consequences**: Hierarchy, script, mix and grid misuse fail at the boundary with actionable messages; mixes are order-independent; enormous proxies raise instead of hanging; 472 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged. Deferred: unbind-resurrect schema, snapshot missing-asset strictness, hold-last semantics, UI pause-capture semantics, UV-orientation decision, skin oracle purity, sphere pole topology, digest coverage.



### ADR-052: Cover full material, texture and skin identity in asset digests
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Asset digests feed duplicates() and refresh() change detection, but _digest_material ignored metallic/roughness/emissive, texture digests ignored dimensions (a 2x8 and a 4x4 with identical bytes collided), and _digest_mesh ignored all skinning (joints/weights/names/bind matrices), so variants shared one digest. The parallel claim that refresh() only handles the first record was refuted by reading (it iterates every source) and dropped.
- **Decision**: Hash metallic/roughness/emissive into material digests, width/height plus pixel sha into texture digests, and joint/weight/skin-joint/bind-matrix groups into mesh digests with length-prefixed packing. Two existing assertions that pinned pixel-only texture digests were updated to the new contract. Four regression tests added (metallic/roughness/emissive divergence, reshaped-texture divergence, skin-weight divergence with no false duplicates).
- **Consequences**: Content-distinct assets no longer collide in duplicates()/find_by_digest() and refresh() detects their changes; 473 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged. apply_ui_action resume idempotence kept as-is (idempotent success, no harm reproduced); texture names stay out of digests by content-addressing design.



### ADR-053: Keep every reported node and isolate bot randomness
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: _node_report dropped any node whose center hit the projection plane (ZeroDivisionError -> continue skipped the whole entry, corrupting node_count and diffs); run_bot permanently reseeded global random like run_log did before ADR-049; run_bot and validate_fairness accepted NaN/Inf steps and wall budgets, silently disabling timeouts and poisoning clocks. The hygiene gate rejects bare except-pass, so the deliberate null-screen keep carries a scoped marker (bare form needs a 3+ char reason word per the checker).
- **Decision**: Degrade on-plane nodes to screen null instead of dropping them; save/restore global RNG around run_bot like run_log; require finite positive step and wall budgets in run_bot and validate_fairness. Five regression tests added (on-plane inclusion with null screen, RNG restore, NaN/Inf step rejection).
- **Consequences**: Frame reports never lose nodes; bot runs are side-effect-free and strictly validated; 475 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged. apply_ui_action resume idempotence and unbind-resurrect stay filed as judgment calls, not defects.


### ADR-054: Add deterministic particle bounce, friction and contact-kill
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: Particles stopped dead on every contact, so games needing sparks, debris or bouncing shots would hand-roll response math with divergent trajectories and hashes.
- **Decision**: Extend ParticleSystem.step with restitution=0.0, friction=0.0, kill_on_contact=False (defaults reproduce the legacy dead stop bit-identically, including a verbatim zero-assignment branch so no negative zero leaks into traces). Validation precedes the empty-box fast path. On a hit: kill drops the particle; else per-axis reflect-or-zero in swept X-Z-Y order with REST_SPEED 0.05 settle snapping; friction scales tangential velocity only on hit steps. CubeDemo gains a floor slab AABB center (0,-0.05,0) half (10,0.05,10) with restitution=0.45 stepped in update() but excluded from snapshot(). No Emitter, Particle, report, renderer, CLI or schema changes.
- **Consequences**: The fountain visibly bounces in headless frames while the simulate hash 772cac5232a0947b8f6d1914a5cf0cde is unchanged. Perf budget: step wall at most 1.05x legacy at 1k particles by 8 AABBs. Known quirk (pre-existing, filed as follow-up): a particle sliding tangentially while in box contact relocates to the box min face via the interior-start clause of the swept pass; the fountain never triggers it because lifetimes end before any settle.


### ADR-055: Fix slide-teleport by gating the sweep interior clause
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: The swept pass ejected any point strictly interior on the sweep axis to the min face, including points resting on a face (within POINT_SKIN) whose tangential motion should slide. A resting particle with sideways velocity teleported to the box corner and stopped. Supersedes the ADR-054 quirk paragraph: the quirk is fixed, not merely filed.
- **Decision**: Gate the interior-start clause on strict interiority on every axis (no skin tolerance), computed from the already-available point coordinates. Face-contact points (offset exactly one skin outside) skip the clause and slide; genuinely deep-interior spawns eject exactly as before. Two-line change in _move_point_flat; no signature, schema, or behavior change for crossings, rests, or ejections.
- **Consequences**: Sliding preserves tangential motion deterministically; frame-70 demo hash e37b744448a1fbbb5cf5f390f41753db is bit-identical pre/post fix and the simulate hash is unchanged. Failing-first slide/graze tests plus a deep-interior preservation lock added. Tangential exit off a box edge while still in the skin band now slides off cleanly instead of teleporting.


### ADR-056: Add skin-aware batch merging for identical rigs
- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: merge_batches skipped every skinned mesh, so rigged crowds paid one draw per model with no engine path to consolidate; per-game rig merging would fork draw-call accounting and frame hashes.
- **Decision**: Merge skinned groups keyed by material, joint-name tuple and node world-matrix tuple, concatenating positions, normals, UVs, colors, joints and weights verbatim with the shared inverse binds; the merged node reuses the common world matrix so deformation is bit-exact. MeshBuilder gains a mode-guarded add_skinned_mesh path; plan_batches and the merge summary gain additive skin counters; the web inspector exports them. Cross-transform merges (inverse-bind rebasing) and palette-union remaps stay future.
- **Consequences**: N identical rigs render as 1 draw with pixel-identical frames to the unmerged scene (proven by a headless Engine pixel-parity test on a test rig module). Static plans, pins and the simulate hash are unchanged (CubeDemo is unskinned). Perf budget: merge wall at most 1.3x current cost on equivalent groups; runtime draws strictly decrease.
### ADR-057: Key skin-aware batch merges on the full bind palette

- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: The skin-aware merge keyed groups by material, joint-name tuple and node world matrix only, and MeshBuilder accepted any member with matching joint names. Two rigs sharing joint names but carrying different inverse bind matrices merged into one group keeping the first binds, so the second rig deformed against the wrong rest pose. Reproduced with identical joints/materials/transforms and shifted binds collapsing to one group.
- **Decision**: Extend the plan/merge skin keys with the inverse bind matrix tuple and reject mismatched binds in MeshBuilder.add_skinned_mesh alongside the joint-name check. Remove the unused particles._AXES constant left over from the swept-pass change.
- **Consequences**: Differing bind palettes stay in separate groups and the builder fails fast at the boundary; identical rigs still merge to one draw with pixel-identical frames. 496 tests green, ruff clean, 6/6 aikit gates; simulate hash unchanged (CubeDemo is unskinned).


### ADR-058: Fix six reproduced 12-module swarm defects with minimal patches

- **Date**: 2026-11-04
- **Status**: Accepted
- **Context**: 12 parallel analysis subagents (one module each) returned completed documents; main session sampled and reproduced every implemented claim, refuted one (S04 None-context with schema 1 masked by legacy fallback, confirmed with schema 2) and narrowed one (animation duration must keep event-only clips working). Fabricated-batch rule not triggered: all sampled claims reproduced.
- **Decision**: Six minimal fixes: input.bind blank-context misroute (None vs empty), input.from_dict context str-coercion, particles.step and headless.run_simulation NaN/Inf step rejection, animation.duration tracks-only when tracks exist (event-only fallback preserved), analysis._stats per-cell grid divisor, mixer.render single master factor. Seven regression tests added (input x2, particles, headless asserts, animation x2, analysis grid, audio master).
- **Consequences**: 503 tests green, verify-determinism 120 ok, simulate hash 772cac5232a0947b8f6d1914a5cf0cde unchanged, headless report schema 10 ok, 6/6 aikit gates after fix pass. Filed-but-deferred: plan-vs-merge grouping divergence, sprite oracle vs renderer sizing, hold-last pressed parity, interior-eject direction, unbind-resurrect, touch-trigger hysteresis (real but behavior-changing, need separate versioned decisions).

### ADR-059: Fix five reproduced swarm defects with failing-first pins

- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: 12 parallel analysis subagents returned completed documents; main session reproduced a sample before touching code and refuted one flagship claim (batching B1 wrong-normal: code already computes transpose(inverse), verified against Mat4 column-major layout and rotation_z repro giving correct (0,1,0)). Five sampled claims reproduced and fixed.
- **Decision**: Five minimal fail-fast fixes: input contexts inherit custom bindings (merged from self.bindings, not DEFAULT_BINDINGS), Vec3 mul rejects non-numeric operands, Track rejects duplicate keyframe times (strictly increasing), PauseMenu.move requires int (rejects float/bool), web simulate step rejects non-finite (400 not 500). Five regression tests added; README tree fixed for test_swarm_fixes.py with size-budget trims; codebase map refreshed via update_knowledge_base.
- **Consequences**: 520 tests green, verify-determinism 120 ok hash 772cac5232a0947b8f6d1914a5cf0cde unchanged (no re-pin), headless 320x180 report ok, --describe accurate, 6/6 aikit gates pass. Filed-but-deferred: mesh_builder vs batch key divergence, sprite oracle drift, unbind resurrection, trigger teleport misses, audio unknown-bus policy, broadphase large-query contract (real but behavior-changing, need separate versioned decisions).

### ADR-060: Fail-fast on History capacity type, blank input bindings, unknown audio bus
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: Stage 3 swarm triage reproduced three validation holes with scripts: History(True)/2.5 accepted, InputMap.from_dict accepted blank action/key while bind() rejects, Mixer.play accepted typo bus with silent full gain.
- **Decision**: Reject non-int History capacity with TypeError (bool explicitly rejected); reject blank action/key in InputMap.from_dict and context maps with ValueError matching bind(); reject unknown Mixer bus with ValueError (allow master). Three regression tests added.
- **Consequences**: No sim-hash change (validation-only, default paths untouched); typo bugs fail fast; audio unknown-bus deferred item from ADR-059 now closed.

### ADR-061: Add deterministic CPU view-frustum culling to the core renderer
- **Date**: 2026-11-05
- **Status**: Accepted
- **Context**: The renderer drew every world-visible node with no frustum test, so draw calls were the scaling limit; per-game culling would fork draw accounting and frame hashes.
- **Decision**: Add GL-free `keystone/culling.py` (normalized 6-plane extraction from `view_projection`, 8-corner world AABB via `world_matrix`, p-vertex test, on-plane visible, skinned always visible, `cull_scene()` reference API) plus frozen `Scene.culling` (`CullingSettings.enabled`, default on). The color pass culls inline in `group_instances(scene, planes)` reusing the already-computed world matrix (same predicate as `cull_scene`, proven by an agreement test; a second full traversal measured 1.38x so the inline path was chosen); the shadow depth pass is unchanged (off-camera casters still shade the frame). Gate with `--culling/--no-culling` in every `__main__` guard list; `--no-culling` preserves legacy pixels. Bump frame report schema 10 to 11 with `scene.culling`, add `capabilities.culling`, persist optional `environment.culling` in snapshot schema 1, export `culling` in the web scene/inspector, and extend `last_stats` with `culled_nodes/culling_enabled` plus a HUD `CULL N OFFSCREEN` line.
- **Consequences**: Off-screen meshes skip color-pass draws with identical on-screen pixels (10 behind-camera cubes: 6→5 draws, 830→710 tris, `culled_nodes` 10; `--no-culling` renders the legacy frame); `--simulate --frames 120` hash unchanged because culling never enters `snapshot()`. Frame/report hashes change and were re-pinned explicitly. Perf budget (measured, trimmed-mean over 40 headless frames at 320x180): CubeDemo wall `<=1.15x` no-cull baseline (observed 1.11x). Light-frustum shadow culling, LOD and occlusion remain future.

### ADR-062: Harden the 12-module engine audit with reproduced, fail-fast fixes

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: A second 12-module swarm (renderer, scene, loop, input, animation, particles, audio, collision, serialization, batching, HUD, web) returned 423 evidence rows. The lead reproduced the high-severity candidates independently; no batch was invalidated. The recurring root causes were permissive dataclass fields, frame-sampled one-shot edges, duplicated/nondeterministic serialization, and counters that disagreed with the renderer.
- **Decision**: Land minimal root-cause fixes with a failing-first test each: strict finite/type validation for `ActionState`, `InputMap`, `Transform`, `Node`, lights, particles, audio, physics and `CommandLog`; context-isolated binding round-trips; separate mouse-look vs click gating and pending-edge/look delivery across zero-step frames; one-shot repeated headless actions; trace deep copies; `Scene` reciprocal parent/child construction, iterative traversal, snapshot root/next-id preservation and strict versions; unique atomic temp files plus strict JSON and `stable_hash`; material-graph duplicate/cycle validation; PNG framing bounds; animation wrap events, channel type checks and inverse-transpose normals; nearest-face particle ejection; character step-up remaining-delta/zero-rise/nearest-face fixes; inside-sphere ray semantics and keyed raycast ties; exclude-aware merge and truthful instancing counters; playtest seed/witness/audit-trail fixes; web 400s, frame inference, empty-live-scene preservation, false settings, HEAD/405 and keep-alive close; report world/triangle/alpha/settings comparisons; singular-model and shadow-state renderer guards; glTF V-origin conversion; and the documented schema/version/capability drift.
- **Consequences**: Full suite 547+ tests green; `--verify-determinism --frames 120` remains `772cac5232a0947b8f6d1914a5cf0cde`; `--simulate --frames 120 --expect-hash 772cac...` exits 0; headless PNG/report proofs and 6/6 AIKit gates pass. Valid data is unchanged; invalid data now fails at the boundary. Filed-but-deferred items (stationary deep-particle depenetration, renderer cache eviction, report-hash image-path removal, HUD alpha blending, sprite size clamp, broadphase large-query policy, trigger teleport hysteresis, stateful web Step, emitter speed semantics, renderer cache and asset digest improvements) are recorded with reproductions in the Stage 4 report and are not silently implemented.

### ADR-063: Close the deferred audit items with 18 fixes and 9 evidenced drops

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The first closure pass left 26 verified defects deferred and several pre-fix reproduction scripts still asserted the old contract. The reviewer required every item to be fixed with a failing-first test or formally dropped with evidence, and every reproduction to become a passing post-fix assertion.
- **Decision**: Fix glTF reflected/singular matrix decomposition, skinned-node transform semantics (ignore the mesh node transform), finite normalized skin weights, context-loss-safe skinned release, stationary deep-particle depenetration, emitter speed as a magnitude, mixer bus removal muting, a minimum pitch guard, broadphase large-query linear fallback, grounded-only platform carry, zero-gravity ground probes, strict sphere tangency, negative-zero hash canonicalization, opaque HUD alpha blending, tiny-canvas menu suppression, diagnostics schema cleanup, explicit web reset-step labeling, finite animation track values/zero quaternions, sorted clip tracks, integer unique glTF joints, boolean coordinate rejection, Material/TextureData type checks, finite perspective parameters, world-visible disabled culling, pressure-free glTF weight validation, and finite material-graph parameters. Formally drop, with the recorded evidence and reasons: GPU cache eviction (VRAM/lifecycle policy), emitter deletion mid-flight (explicit author action; per-particle force snapshots would change the Particle contract), sprite clamp oracle (deferred visual policy), trigger teleport hysteresis (needs a swept temporal contract), report hash image path (intentional artifact identity; `same_image` is the pixel check), web resource/deployment limits, sub-120px exact headless capture (GLFW minimum; the message is now truthful), `--simulate` action-count default (documented behavior), and renderer cache/asset-digest performance work (workload/policy-dependent).
- **Consequences**: 644 tests green; 22/22 post-fix reproduction scripts pass via `reports/keystone-swarm-repro/verify_all.py`; the five named stale scripts (m2, m6, m7, m9, m11) are post-fix assertions and their `.pre_fix.py` evidence is preserved; determinism remains `772cac5232a0947b8f6d1914a5cf0cde`; headless schema 11 and `--describe` remain accurate; 6/6 AIKit gates pass. The drops are documented in `reports/keystone-swarm-deferred-closures.md`, not silently omitted.

### ADR-064: Reject malformed glTF accessors, asset cycles and unsafe direct pitch

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: A final broad M1 probe still reproduced three real validation gaps outside the original 26-row list: glTF accepted FLOAT indices, SCALAR POSITION and negative accessor counts; the asset registry accepted transitive dependency cycles; and assigning `PerspectiveCamera.pitch` directly above the clamp could make `look_at` fail.
- **Decision**: Enforce glTF accessor type/component rules for POSITION and indices, reject negative accessor counts even without a bufferView, detect transitive asset dependency cycles at registration, and clamp pitch inside `PerspectiveCamera.forward()` while preserving the stored value.
- **Consequences**: 647 tests green; 23/23 post-fix reproduction scripts pass; determinism remains `772cac5232a0947b8f6d1914a5cf0cde`; malformed imports and cycles now fail at the boundary, and direct camera pitch stays render-safe.

### ADR-065: Add deterministic prefabs for reusable scene subtrees

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Unity/Unreal-style authoring needs a reusable entity/template primitive. Keystone could save whole scenes but had no way to capture a subtree and instantiate isolated copies without rebuilding it by hand; AI clients also lacked a structural prefab description.
- **Decision**: Add `keystone.prefab.Prefab` with `from_node()`, `from_scene()`, `instantiate(scene, parent=None, instance=None)`, `node_count` and JSON-safe `describe()`. Templates are detached; components are deep-copied per instance; mesh/material payloads stay shared; IDs become `instance:original-id` or scene-allocated when no prefix is given. Export `Prefab` from the public API and add `capabilities.prefabs` to `--describe`. `Prefab.instantiate(scene)` is the canonical call to avoid a `scene -> prefab -> scene` import cycle.
- **Consequences**: 652 tests green; prefab instances are isolated and deterministic, duplicate instance IDs fail through the existing scene duplicate guard, and the five-operation game contract is unchanged. A scene-editor UI and prefab file format remain future tooling work.

### ADR-066: Add a versioned project manifest and one-command scaffolding

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Keystone could load an external game only through `--game package.module:Factory`; a human or AI had to hand-create a package, remember the five operations and pass a long spec. Unity/Unreal-style onboarding needs a project unit.
- **Decision**: Add `keystone.project` with a schema-1 `keystone.json` manifest (`name`, `game`, `description`, `assets`), strict load/save, `ProjectContext.describe()`, `create_project()`, and `load_project_game()`. Add `python -m keystone --new DIR [--name NAME] [--force]` scaffolding (`keystone.json`, a generated five-operation game module, README, `.gitignore`) and `--project DIR|keystone.json` to open it. `--project` adds the directory to the import path, uses the manifest game unless `--game` overrides it, and adds a `project` object to `--describe`.
- **Consequences**: A new project runs with one create command and one open command; generated projects are deterministic, headless-ready and contract-validated. Project manifests are local JSON and do not change the engine's five-operation contract. Prefab persistence, a scene-editor workflow and behavior/system hooks remain future work.

### ADR-067: Add a web-console scene editor with hierarchy, transforms and prefabs

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The web console could inspect a scene but not select or edit it; a Unity/Unreal-style workflow needs a hierarchy, transform editing and prefab insertion from the same AI-addressable API as the viewer.
- **Decision**: Add `keystone.web.editor` helpers and schema-1 `/api/editor`: `GET` returns hierarchy (nodes, roots, parent/child ids, local transforms, world matrices, tags/layers/components), selection and saved prefabs; `POST` supports `select`, `transform` (finite position/rotation/scale arrays), `save_prefab` (capture the selected node with `Prefab.from_node`) and `insert_prefab` (deterministic instance prefix or scene IDs). The console gains a hierarchy `<select>`, transform fields, prefab name/instance inputs and apply/save/insert buttons; the viewer reloads after edits. `--describe` advertises the editor schema and `/api/editor`.
- **Consequences**: Humans and AI clients share one editor contract; selection and prefabs are session-local, transforms mutate the live scene, and prefab insertion uses the deterministic prefab system. Editing a game-owned scene may be overwritten by the next `update()`; persistent editor state, undo/redo and prefab files remain future work. The five-operation game contract is unchanged.

### ADR-068: Persist versioned prefabs through the asset registry

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Prefabs were in-memory templates; a Unity/Unreal-style authoring loop needs prefab files that survive a process restart and resolve shared mesh/material payloads without duplicating binary data. The asset registry already owned stable ids, digests, dependencies and hot reload but knew only meshes, materials and textures.
- **Decision**: Add `PREFAB_SCHEMA_VERSION = 1`, strict `Prefab.to_dict()`/`from_dict()` documents (transform, visibility, tags, layer, components and registered mesh/material ids), and atomic `Prefab.save()`/`load()` writing `.kprefab` files. Loading custom components requires an explicit `component_types` name map; non-JSON components, unknown types and wrong asset kinds fail at the boundary. Extend `ASSET_KINDS` with `prefab`, teach `asset_kind()`/`kind_from_suffix()`/`default_loader()` and `AssetRegistry.register_file(..., component_types=...)` about the kind, derive prefab dependencies from referenced assets automatically, and digest the canonical JSON document. Refresh uses a registry-bound loader so reloads re-resolve mesh/material ids.
- **Consequences**: 673 tests green; prefabs are a first-class asset with stable hashes, dependency tracking, missing-dependency reporting and hot reload; serialized files hold ids rather than duplicate payloads; the five-operation game contract and core module boundaries are unchanged. Editor prefab libraries and undo/redo persistence remain future work.

### ADR-069: Add node authoring and bounded undo/redo to the web editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The scene editor could select, transform and insert prefabs but could not create, delete, duplicate or reparent nodes, so human and AI authoring stopped at template placement. There was no way to recover from a bad edit, and mesh/material assignment from the asset registry was unavailable.
- **Decision**: Bump `EDITOR_SCHEMA_VERSION` to 2 and centralize `EDITOR_ACTIONS` in `keystone.schema` so the CLI description and web schema cannot drift. Add pure `create_node`, `delete_node`, `duplicate_node` and `reparent_node` helpers plus a bounded `EditorHistory` that snapshots the node tree, restores it atomically when an action fails, and exposes undo/redo depths. Wire the actions through `/api/editor`, accept registry asset ids for node mesh/material fields, and add console controls for create/duplicate/delete/reparent, undo and redo. `duplicate_node` reuses the prefab cloner so component copies stay isolated.
- **Consequences**: 674 tests green; authoring actions validate before mutation, failed edits leave the scene unchanged, undo/redo preserves node IDs while replacing node objects, and the editor document reports history depth. Selection and history remain session-local; persistent editor prefabs, scene files and component authoring remain future work. The five-operation game contract is unchanged.

### ADR-070: Add a file-backed prefab library to the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `.kprefab` persistence existed, but the editor kept captured prefabs in a session dictionary. Closing the console lost the authoring library, and AI clients could not discover what was on disk or why an entry failed to load.
- **Decision**: Add `keystone.prefab_library` with `PrefabLibrary` and `PrefabEntry`: one directory of `.kprefab` files, portable name validation that blocks path traversal, atomic save, registry/component-aware load, stable listing and per-entry error reporting. Wire an optional library into `GameSession`, list `source`/`error`/`node_count` in `/api/editor`, lazily load an entry on first insert, and expose the active `workspace.prefab_dir`. `--project .` defaults the library to `<project>/prefabs`; `--prefab-dir DIR` overrides it. Rebind the library to the game's live `AssetRegistry` after `build_scene()` because games may rebuild their registry.
- **Consequences**: 679 tests green; prefab authoring survives console restarts, invalid names and corrupt files are reported without breaking the editor, and only prefab writes touch the configured library directory. Project asset import, scene files and component authoring remain future work.

### ADR-071: Import project manifest assets into the game registry

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `keystone.json` already listed `assets`, but nothing loaded them. A Unity/Unreal-style project needs relative `.obj`, `.png` and `.kprefab` files to become stable registry ids before scenes and editor commands reference them, without duplicating import code in every game.
- **Decision**: Add `project_asset_id`, `import_project_assets` and `attach_project_assets`. Manifest paths must be relative and stay inside the project; ids are deterministic `project:<relative-path>` strings, kinds come from the file suffix, and prefab entries receive the game's `component_types`. `load_project_game` and the `--project` CLI path attach assets to `game.assets` when the project declares any, with an actionable `Why:`/`Fix:` error on failure. The generated game owns one `AssetRegistry`, registers built-in meshes/materials with `replace=True`, and never replaces the registry during rebuilds.
- **Consequences**: 683 tests green; projects can ship assets without hand-wiring registrations, unsafe or missing paths fail before rendering, and editor asset ids survive rebuilds. Scene files, component authoring and play-in-editor remain future work.

### ADR-072: Persist typed components in scene snapshots

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Scene snapshots preserved node identity, transforms, tags, layers, visibility, meshes and materials, but dropped typed components. Prefabs already had a component codec, and duplicating that logic would drift. A Unity/Unreal-style scene file must round-trip the same authored data the editor shows.
- **Decision**: Extract the component codec into `keystone.component_codec` and use it from both prefabs and snapshots. Bump `SCENE_SNAPSHOT_VERSION` to 2 and write a sorted `components` list per node; `scene_from_dict(..., component_types=...)` reconstructs them, rejects duplicate types, unknown names and unsupported payloads, and still accepts schema-1 snapshots without components.
- **Consequences**: 685 tests green; scene snapshots preserve dataclass, `to_dict`/`from_dict` and JSON-primitive components; loading a component-bearing scene without a type map fails explicitly. Editor scene files and component authoring remain future work.

### ADR-073: Add file-backed scene save/load to the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Component-aware snapshots made scene files possible, but the editor still could not persist authored scenes. A Unity/Unreal-style workflow needs named `.kscene` files that survive restarts, restore in place and report broken entries without taking down the editor.
- **Decision**: Add `keystone.scene_library` with `SceneLibrary`/`SceneEntry`: portable name validation, atomic `.kscene` save, strict registry asset-reference validation, component-aware load and `load_into()` backed by `restore_scene()`. Bump the editor schema to 3, add `save_scene`/`load_scene`, expose saved scenes plus `workspace.scene_dir`, and add console controls. `--project .` defaults the library to `<project>/scenes`; `--scene-dir DIR` overrides it. Loading a scene clears selection and undo history while preserving the game-owned `Scene` object.
- **Consequences**: 691 tests green; authored scenes survive console restarts, missing/wrong-kind assets and corrupt entries fail explicitly, and restore keeps `self.scene` identity. Asset browser assignment, component authoring and play-in-editor remain future work.

### ADR-074: Add registry asset inventory and assignment to the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `create_node` could reference registry assets by id, but existing nodes could not be inspected or reassigned. A Unity/Unreal-style inspector needs the asset browser and node mesh/material fields in the same AI-addressable editor document.
- **Decision**: Bump the editor schema to 4, include the registry's JSON-safe asset inventory (`id`, `kind`, `sha256`, `source`, `dependencies`) and each node's resolved `mesh`/`material` ids, and add `assign_asset` with `mesh`/`material` fields that assign or clear through the registry. Validate missing/kind-mismatched ids, route the mutation through `EditorHistory`, and add mesh/material selects plus an apply button to the console.
- **Consequences**: 692 tests green; humans and AI clients can discover assets and reassign node payloads with undo, while invalid ids fail with 400 before mutation. Component authoring and play-in-editor remain future work.

### ADR-075: Add typed component authoring to the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The editor displayed component names but could not add, edit or remove them. Game-defined components already had a shared codec and optional `game.component_types` map for prefabs and scenes, so the editor lacked only the authoring contract and UI.
- **Decision**: Bump the editor schema to 5, expose the game's `component_types` names and each node's serialized `component_data`, and add `set_component`/`remove_component` actions. Data is decoded through `component_codec`, replacements are keyed by type, unknown or non-serializable payloads fail with 400, and mutations run through `EditorHistory`. The console adds a type select, JSON data editor and set/remove buttons.
- **Consequences**: 693 tests green; component edits undo and survive `.kscene` save/load, while games without a `component_types` map reject component authoring explicitly. Play-in-editor and richer component field forms remain future work.

### ADR-076: Add play/step/stop with authored-scene restore

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `/api/simulate` rebuilds the game scene, so running the game from the editor discarded authored changes. A Unity/Unreal-style workflow needs a play mode that advances the live scene and restores the authored state on stop.
- **Decision**: Bump the editor schema to 6 and add `play_start`, `play_step` and `play_stop`. Start snapshots the component-aware scene with `scene_to_dict`; step calls `game.update(FIXED_STEP, ActionState)` for a bounded frame count with optional action payloads; stop restores through `restore_scene`, clears history/selection and reports `play.active`/`play.frames`. Editing actions and `/api/simulate` are blocked while playing. The console adds Play/Step/Stop controls.
- **Consequences**: 694 tests green; authored scene graph state is restored after play, while game-owned counters (time, particles) are not rewound; play mode is a scene preview, not a full state rewind. Full game-state snapshots and inspector property editing remain future work.

### ADR-077: Add inspector property editing for existing nodes

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The editor could create nodes with names, tags, layers and visibility, but could not change those properties afterwards. A Unity/Unreal-style inspector needs rename, hide/show, tagging and layer reassignment without delete-and-recreate.
- **Decision**: Bump the editor schema to 7 and add `set_node` with optional `name`, `visible`, `tags` and `layer` fields. Validate every supplied value before mutating, update atomically through `EditorHistory`, reject blank names/layers, non-boolean visibility and non-list tags, and add inspector fields plus an apply button to the console.
- **Consequences**: 695 tests green; node metadata edits undo cleanly and remain compatible with scene files, prefabs and queries. Transactional batch authoring and asset previews remain future work.

### ADR-078: Add atomic batch authoring for AI clients

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: AI clients often need several related edits (create a node, name it, assign assets, parent a child). Sending them one by one leaves partial scenes on failure and creates many undo steps.
- **Decision**: Bump the editor schema to 8 and add `batch` with up to 100 actions from a fixed scene-mutating set (`transform`, `set_node`, `assign_asset`, `set_component`, `remove_component`, `create_node`, `delete_node`, `duplicate_node`, `reparent_node`, `insert_prefab`). Run sub-actions through a reentrant session lock with history suppressed, take one pre-batch snapshot, restore the whole scene and selection on failure, and reject nested batches, undo/redo, play and file actions.
- **Consequences**: 696 tests green; an AI can apply a complete structural edit atomically and undo it in one step, while invalid or unsupported sub-actions fail before mutation. Asset previews and richer schema hints remain future work.

### ADR-079: Import project prefabs after their asset dependencies

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Manifest assets were imported in list order. A `.kprefab` listed before its mesh dependency failed even though both files existed, which made manifest ordering a hidden constraint.
- **Decision**: Resolve and validate every manifest path first, import non-prefab assets in manifest order, then prefabs, and return records in the original manifest order. Missing paths fail before any registration.
- **Consequences**: 697 tests green; manifest order no longer constrains prefab dependencies and a missing file cannot leave a partially imported project. Asset metadata introspection remains future work.

### ADR-080: Expose kind-specific asset metadata in the editor

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The editor could list asset ids and kinds, but an AI client could not tell a useful mesh from an empty one, compare material factors, check texture size or see a prefab's contents without loading raw payloads.
- **Decision**: Bump the editor schema to 9 and enrich `asset_entries()` with metadata: mesh vertices/triangles/UV/color/skin-joint flags, material color/specular/shininess/metallic/roughness/emissive/texture flag, texture name/size, and prefab node count plus resolved asset dependencies. Keep the registry's id/kind/sha256/source/dependencies fields unchanged.
- **Consequences**: 698 tests green; AI clients can choose assets from summaries and catch empty or mismatched assets before assignment. Scene startup and asset previews remain future work.

### ADR-081: Open a saved scene when the editor starts

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `.kscene` files survived restarts, but every console start rebuilt the game scene and required a manual load. A Unity/Unreal-style project should open its scene directly.
- **Decision**: Add `--scene NAME` for `--serve` with `--project` or `--scene-dir`, pass `initial_scene` through `serve`/`create_server`/`GameSession`, and eagerly build the game scene and `load_into` the named entry before the first request. Missing libraries or entries fail at startup with explicit errors.
- **Consequences**: 700 tests green; the editor opens on the authored scene with empty history/selection, and invalid scene names fail before serving. Non-serve scene loading and asset previews remain future work.

### ADR-082: Scaffold the editor workflow into new projects

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: New projects had `keystone.json` and a game module, but no prefab/scene directories or component hook, so the editor workflow required manual setup and `--scene` had no default library.
- **Decision**: Make `create_project()` create `prefabs/` and `scenes/` with short README files, initialize `self.assets = AssetRegistry()` and `self.component_types = {}` in the generated game, and document the save/serve/`--scene` loop in the generated README.
- **Consequences**: 700 tests green; a new project can open the console, save prefabs/scenes and reload them without extra setup, while existing projects remain compatible. Editor camera polish and non-serve scene loading remain future work.

### ADR-083: Expose dataclass field schemas for component authoring

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: AI clients could list component type names but not the fields needed for `set_component`, so payloads were guesswork. Dataclasses already carry enough metadata to describe their fields safely.
- **Decision**: Bump the editor schema to 10 and add `component_schemas`: dataclass types expose field name, type name, required flag and JSON-safe default; non-dataclass types expose an empty field list with a manual-codec note. No runtime component data is exposed beyond the existing serialized `component_data`.
- **Consequences**: 700 tests green; an AI can construct valid dataclass component payloads from `/api/editor` and still fall back to the `to_dict`/`from_dict` contract for custom types. Editor camera polish and non-serve scene loading remain future work.

### ADR-084: Add safe rename/delete for prefab and scene libraries

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The editor could save and load library entries but never rename or remove them, so AI clients had no lifecycle management and stale files accumulated.
- **Decision**: Add `PrefabLibrary`/`SceneLibrary` `rename()` and `delete()` with portable names, missing-entry KeyErrors, destination collision checks, raw JSON name updates, and atomic writes. Expose `rename_prefab`, `delete_prefab`, `rename_scene` and `delete_scene`; keep the cached prefab dictionary in sync and reject the actions in batches or play mode. Bump the editor schema to 11.
- **Consequences**: 703 tests green; library lifecycle is safe and AI-addressable, while deletes remain immediate and intentionally non-undoable. Library UI controls and editor camera polish remain future work.

### ADR-085: Expose library rename/delete in the console

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Rename/delete existed only in the JSON API; humans had to call the API directly to manage scene and prefab files.
- **Decision**: Add new-name fields plus Rename/Delete buttons for scene and prefab libraries, wire them to the existing schema-11 actions, and include them in the busy-state button set. No API or schema change.
- **Consequences**: 703 tests green; the console covers the full save/load/rename/delete lifecycle for both libraries. Editor camera polish and non-serve scene loading remain future work.

### ADR-086: Add an independent orbit camera to the editor viewport

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The WebGL viewport always used the game camera, so inspecting an authored scene from another angle required changing gameplay state. A Unity/Unreal-style editor needs viewport navigation independent of the scene.
- **Decision**: Add a `lookAt` matrix and spherical editor camera state to `viewer.js`: left-drag orbits, the wheel zooms within bounds, and Reset view re-frames from the scene camera. The editor camera survives scene refreshes, while the game camera remains untouched. Add a viewport Reset view button and a `touch-action: none` canvas rule.
- **Consequences**: 703 tests green and both JS modules pass `node --check`; navigation is independent of gameplay state, with no pan/fly or gizmo controls yet. Non-serve scene loading remains future work.

### ADR-087: Suggest saved scene and prefab names in the console

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The console listed saved scenes/prefabs in editor state but its text inputs required remembering exact names, which made load/rename/delete error-prone.
- **Decision**: Add `<datalist>` suggestions populated from `editor.scenes` and `editor.prefabs`; labels show node counts or a load-error marker. No API or schema change.
- **Consequences**: 703 tests green and both JS modules pass `node --check`; the console exposes the same library names the AI API already returns. Non-serve scene loading remains future work.

### ADR-088: Load saved scenes for simulate and headless runs

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `.kscene` files were usable only through `--serve`; AI clients could not simulate or render an authored scene without starting the console.
- **Decision**: Add optional `scene` parameters to `run_simulation()` and `Engine`, prepare the game scene once in the CLI, restore the named `.kscene` through `SceneLibrary`, and pass it to the chosen run. Allow `--scene` with `--serve`, `--simulate` or `--headless` when `--project`/`--scene-dir` supplies the library; reject other combinations.
- **Consequences**: 705 tests green; saved scenes drive editor, simulation and headless rendering without rebuilding, while replay/playtest scene loading remains future work.

### ADR-089: Load saved scenes for replay and playtest

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Replay and playtest create fresh game instances, so the simulate/headless prepared-scene path could not be reused. Their factories also skipped project asset attachment.
- **Decision**: Add optional `scene_loader(game, scene)` hooks to `run_log`, `verify_log`, `run_bot` and `validate_fairness`, called after each fresh `build_scene()`. Extend `--scene` to `--replay` and `--playtest`, build the scene loader lazily, and use a shared `make_game()` factory that reattaches project assets for every run. Fairness probes now see the same authored layout.
- **Consequences**: 708 tests green; transcripts and fairness verdicts run against saved scenes, and project assets are available to every fresh instance. Windowed scene loading and editor visual polish remain future work.

### ADR-090: Complete scene loading across verify and windowed runs

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: After simulate, headless, replay and playtest support, `--scene` was still rejected for verify-determinism and windowed runs even though both already build a scene and can accept a prepared one.
- **Decision**: Add optional `scene_loader` to `run_script`, `verify_determinism` and `assert_deterministic`, pass the CLI scene loader through both verify passes, and allow `--scene` on the windowed path where the prepared scene already reaches `Engine`. `--describe` remains the only incompatible command.
- **Consequences**: 710 tests green; every runnable path accepts authored scenes except discovery, while windowed execution itself remains covered by the existing startup checks rather than a display-dependent test.

### ADR-091: Render dataclass component schemas as console inputs

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The API exposed dataclass field schemas but the console still required hand-written JSON, so human component authoring remained error-prone despite the schema data.
- **Decision**: Generate typed inputs from `component_schemas` for int, float, string, boolean and JSON-valued fields, prefill from the selected component or defaults, parse values back into a data object for `set_component`, and retain the JSON editor for custom `to_dict`/`from_dict` codecs. No API or schema change.
- **Consequences**: 710 tests green and `app.js` passes `node --check`; dataclass components are form-editable while custom types keep the explicit JSON path. Visual selection focus and asset previews remain future work.

### ADR-092: Add focus-selected framing to the viewport camera

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The orbit camera could navigate freely but could not jump to the selected node, which made large scenes slow to inspect.
- **Decision**: Add `SceneViewer.focusNode(nodeId)`: read the selected node's world translation, set it as the orbit target, clamp the distance to a useful range, and re-render. Add a Focus selected viewport control and cover the JS with `node --check`.
- **Consequences**: 710 tests green; selection and viewport navigation share one workflow, while selection highlighting and asset previews remain future work.

### ADR-093: Highlight the selected node in the viewport

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The hierarchy and inspector showed the selected node, but the 3D viewport did not, so selection was ambiguous in dense scenes.
- **Decision**: Add `SceneViewer.setSelected(nodeId)`, pass the current editor selection on every `showEditor`, and add a `u_selected` fragment-shader rim term. No API or schema change.
- **Consequences**: 710 tests green and both JS modules pass `node --check`; selected geometry is visibly outlined without affecting the game camera or scene data. Asset previews and richer viewport tools remain future work.

### ADR-094: Add console keyboard shortcuts for common editor actions

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The console exposed buttons for undo, redo, delete and focus, but keyboard-driven editing was unavailable and the interface encouraged mouse-only use.
- **Decision**: Add document-level shortcuts when focus is outside inputs/textareas/selects/contenteditable: Ctrl/Cmd+Z undo, Ctrl/Cmd+Shift+Z or Ctrl/Cmd+Y redo, Delete deletes the selected node, F focuses it, Escape clears selection. Reuse the existing `run()` busy guard and editor actions; no API or schema change.
- **Consequences**: 710 tests green and `app.js` passes `node --check`; shortcuts and buttons share one validated command path. Asset previews and richer viewport tools remain future work.

### ADR-095: Show kind-specific asset metadata in the console

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The editor API exposed mesh/material metadata, but the console asset selectors showed only ids, so humans could not compare counts or material factors before assignment.
- **Decision**: Add an `asset-info` readout that renders the selected mesh/material metadata as formatted JSON and refresh it on selection changes. No API or schema change.
- **Consequences**: 710 tests green and `app.js` passes `node --check`; asset metadata is visible in both AI documents and the human console. Thumbnail previews remain future work.

### ADR-096: Add mesh bounds to editor asset metadata

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Mesh metadata listed vertex and triangle counts but not extents, so AI clients could not reason about size or choose focus distances.
- **Decision**: Bump the editor schema to 12 and add `bounds.min`/`bounds.max` to mesh metadata, computed from the payload positions (zero bounds for empty meshes). No new API action.
- **Consequences**: 710 tests green; asset summaries now carry placement and framing information, and the console metadata readout shows it automatically. Thumbnail previews remain future work.

### ADR-097: Add play-mode frame and action controls to the console

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `play_step` accepted actions, but the console always advanced one default-input frame, so play mode could not exercise gameplay controls.
- **Decision**: Add `play-frames` and `play-actions` inputs, validate a 1..10000 frame count and JSON action list, and send both to `play_step`; the API already repeats the last action and clears pressed edges. No backend or schema change.
- **Consequences**: 710 tests green and `app.js` passes `node --check`; play mode exercises real action scripts while preserving authored-scene restore. Thumbnail previews and camera panning remain future work.

### ADR-098: Add shift-drag camera panning to the viewport

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Orbit and zoom covered rotation and distance, but inspecting off-center geometry still required orbiting around the scene target.
- **Decision**: Derive camera right/up basis vectors from yaw and pitch, and make shift-drag translate the orbit target in that plane with distance-scaled motion. No API or schema change.
- **Consequences**: 710 tests green and `viewer.js` passes `node --check`; viewport navigation now covers orbit, pan, zoom, reset and focus without touching the game camera. Thumbnail previews remain future work.

### ADR-099: Import glTF/GLB scenes as prefab-library entries

- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The engine could load glTF 2.0/GLB, and projects could import `.obj`, `.png` and `.kprefab`, but a glTF scene could not enter the editor asset pipeline. Unity/Unreal-style projects need one-step scene-model import.
- **Decision**: Add `keystone.gltf_import` with `is_gltf_asset()` and `import_gltf_prefab()`: load the scene, register textures/materials/meshes as `gltf.<name>.texture.N`/`.material.N`/`.mesh.N` with replace-on-reimport, save the scene as `<prefabs>/<name>.kprefab`, and return the prefab. Project attachment skips glTF during normal asset import, creates `<project>/prefabs` when needed, and imports glTF/GLB files after regular assets so the game registry and editor library are ready. `load_project_game` and `--project` inherit the behavior.
- **Consequences**: 714 tests green; glTF/GLB models become insertable prefabs with stable sub-asset ids, and re-import refreshes their payloads. External glTF buffer/image dependency tracking and thumbnail previews remain future work.

### ADR-100: Scaffold a starter scene and prefab into new projects

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: New projects had the scene/prefab libraries and component hooks but no content, so `--serve --scene main` could not work until the user manually saved something.
- **Decision**: After writing the generated game, load it through an isolated importlib spec, build its scene, and save `scenes/main.kscene` plus `prefabs/cube.kprefab` with the game's `AssetRegistry` and `component_types`. Document the `--serve --scene main` path in the generated README.
- **Consequences**: 714 tests green; a fresh project opens with a working scene and reusable cube prefab. Sample art, richer starter scenes and thumbnail previews remain future work.

### ADR-101: Select scene nodes by clicking the viewport

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Selection required the hierarchy or inspector; the viewport was display-only, which is unlike Unity/Unreal-style editors.
- **Decision**: Compute world-space AABBs for visible mesh nodes on scene load, cast a camera ray from the click position through the camera basis and FOV, pick the nearest AABB hit, and dispatch the existing `select` editor action (or clear selection on empty space). Drags beyond four pixels and shift-pan gestures do not select. No API or schema change.
- **Consequences**: 714 tests green and both JS modules pass `node --check`; viewport clicks and hierarchy selection share one command path. Ray picking is AABB-level, so overlapping bounds may prefer the nearer box; triangle-accurate picking and thumbnails remain future work.

### ADR-102: Add bounded texture previews to editor asset metadata

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Asset metadata exposed counts and factors but no visual preview, so choosing a texture or textured material required opening the scene document or external files.
- **Decision**: Add an in-memory `png_bytes()` encoder, generate a nearest-neighbour thumbnail capped at 64px for each texture, encode it as a PNG data URI, expose it on texture metadata and on each material's `texture` summary, and show the selected material texture preview in the console. Bump the editor schema to 13.
- **Consequences**: 714 tests green and `app.js` passes `node --check`; previews stay bounded in size and the PNG writer reuses the same encoder. Triangle-accurate picking and richer material swatches remain future work.

### ADR-103: Add scene/prefab duplication to the library lifecycle

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Save/load/rename/delete existed, but copying a scene or prefab required saving under a new name or manual file work. Unity/Unreal-style asset libraries treat duplicate as a first-class operation.
- **Decision**: Add `duplicate(old, new)` to `PrefabLibrary` and `SceneLibrary`: validate names, require the source, reject same-name and destination collisions, copy the JSON with the internal `name` updated, and return the new entry. Expose `duplicate_prefab`/`duplicate_scene` and console buttons, and refresh the cached prefab under its new name. Bump the editor schema to 14.
- **Consequences**: 717 tests green; scene/prefab libraries now cover save, load, rename, duplicate and delete with cached-prefab consistency. Transform gizmos and prefab overrides remain future work.

### ADR-104: Publish ready-to-send examples for every editor action

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Field schemas told AI clients which keys existed but not how to assemble a valid request. Every action still required inference from docs or tests.
- **Decision**: Add `EDITOR_EXAMPLES` with one JSON payload per action, include it as `endpoints.editor.schema.examples` in `/api`, and test that the example keys exactly match `EDITOR_ACTIONS` and each payload's `action` matches its key.
- **Consequences**: 718 tests green; AI clients can copy a known-valid request shape directly from the discovery endpoint. Examples are documentation and must be updated whenever an action's required fields change. Transform gizmos and prefab overrides remain future work.

### ADR-105: Add camera/environment authoring with full-scene undo

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The editor could change nodes but not the scene camera, lights, atmosphere or render toggles; those settings required code or direct scene-file edits.
- **Decision**: Add `set_scene` with optional `camera` and `environment` mappings, strict validation (finite vectors, FOV/near/far ranges, non-negative fog, light/point-light constructors, boolean toggles, unknown-key rejection), and assign only after full validation. Expose `scene_settings` in `/api/editor`, add a console JSON editor, and extend `EditorHistory` snapshots from nodes-only to the full scene state so undo/redo restores camera and environment too. Bump the editor schema to 15.
- **Consequences**: 719 tests green; camera, lighting, atmosphere and render toggles are AI- and human-authorable with atomic failure and full-scene undo. Transform gizmos, prefab overrides and behavior systems remain future work.

### ADR-106: Add keyboard transform nudging for the selection

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Transforms required typing into numeric fields or dragging nodes in the viewport; there was no quick keyboard adjustment for placement.
- **Decision**: Add arrow-key X/Z nudges and PageUp/PageDown Y nudges for the selected node, 0.1 units normally and 1.0 with Shift, reusing the validated `transform` action and undo history. Ignore input/textarea/select/contenteditable targets and suppress browser scrolling. No API or schema change.
- **Consequences**: 719 tests green and `app.js` passes `node --check`; placement is keyboard-accessible while retaining one undo step per nudge. Transform gizmos remain future work.

### ADR-107: Add hierarchy and asset filters to the console

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Large scenes and registries produced long select lists, making the target node or mesh/material hard to find.
- **Decision**: Add case-insensitive hierarchy and asset filter inputs. Hierarchy matching covers id, name, layer, tags and component names while preserving indentation; asset matching covers id, kind and metadata. Filters update client-side without API calls.
- **Consequences**: 719 tests green and `app.js` passes `node --check`; navigation stays fast without changing the editor document contract. Transform gizmos and prefab overrides remain future work.

### ADR-108: Add non-destructive project validation for AI/CI

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Project failures surfaced only when a game was loaded or a scene/prefab was opened. AI and CI needed one command that checked assets, glTF imports and both libraries without mutating the project.
- **Decision**: Add `validate_project(context, game=None)`: build the game scene, copy game assets into an isolated registry, import manifest assets, import glTF scenes into a temporary prefab library, then report per-entry scene/prefab errors. Add `--project DIR --validate-project` as a standalone command, print a schema-1 JSON report and exit 1 on errors. Skip the normal project asset attachment on validation so no glTF prefabs are written.
- **Consequences**: 721 tests green; AI/CI can validate the full project authoring surface without side effects. Transform gizmos, prefab overrides and behavior systems remain future work.

### ADR-109: Add structured scene diffs for AI iteration

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: AI clients could save and load scenes but could not tell what had changed since the last save, forcing full-document comparisons or blind overwrites.
- **Decision**: Add `keystone.scene_diff.diff_scene_documents()`: deterministic node diffs keyed by id (name, parent, tags, layer, visibility, transform, mesh/material ids, components) plus one-level camera/environment/root section diffs. Expose `diff_scene` against a saved `.kscene`, keep the last diff on the editor document, add a console Diff scene button and bump the editor schema to 16.
- **Consequences**: 725 tests green; AI and human editors can inspect deltas without loading the saved scene or diffing full JSON. Three-way merges, transform gizmos and prefab overrides remain future work.

### ADR-110: Make library deletes recoverable through trash/restore

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Scene and prefab deletes unlinked files immediately, so an AI or human mistake was irreversible and no recovery path existed in the editor.
- **Decision**: Add `library_trash.py` and route library deletes into a `.trash` directory with unique file names. Add `trash()` and `restore(trash_name)` to both libraries, expose entries in `/api/editor`, add `restore_prefab`/`restore_scene` and console buttons, and keep cached prefabs synchronized. Bump the editor schema to 17.
- **Consequences**: 728 tests green; deletes are recoverable without overwriting live entries, and corrupt/legacy trash files remain inert. Transform gizmos, prefab overrides and behavior systems remain future work.

### ADR-111: Add a viewport translate gizmo with one-action drags

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Nodes could be selected and nudged, but direct viewport translation still required typing coordinates; Unity/Unreal-style authoring expects draggable axis handles.
- **Decision**: Draw an unlit X/Y/Z arrow gizmo at the selection's world position with camera-distance scaling. Hit-test the projected axis segments, begin an axis drag on pointer-down, and preview a world-space delta on the selected node and its descendants. Ctrl/Cmd snaps to 0.25 units. On release restore the preview and send one validated `transform` action whose local position is derived through the parent world inverse. Hide the gizmo in play mode. No REST or schema change.
- **Consequences**: 728 tests green, both JS modules pass `node --check`, and one drag equals one undo entry. The gizmo is translate-only and world-axis aligned; rotation/scale gizmos and local-space axes remain future work.

### ADR-112: Link prefab instances and add revert/apply actions

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Prefab insertion produced detached copies. Later prefab edits could not reach existing instances, and there was no way to discard instance overrides or push them back into the prefab.
- **Decision**: Add `PrefabLink(name, instance)` as editor-only node metadata. Inserting a single-root prefab always allocates a deterministic instance prefix and stamps the root link; multi-root prefabs stay unlinked. Expose `prefab_link` in the editor document, persist it in scene snapshot schema 3 (schemas 1-2 load without links), keep it through undo/redo, and add `revert_prefab` (replace the linked instance with a fresh template copy, preserving sibling order and one undo entry) and `apply_prefab` (capture the instance back into the prefab cache and `.kprefab` library with rollback on save failure). Prefab capture and instantiation strip links, so nested instances remain unsupported. Renaming a prefab updates existing links. Bump the editor schema to 18.
- **Consequences**: 731 tests green; prefab workflows are link-aware and reversible, and snapshots carry the metadata without changing the engine scene document. Multi-root instances, nested prefabs, per-property override tracking and automatic propagation of prefab edits to existing instances remain future work.

### ADR-113: Add local-axis rotate and scale gizmos

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The viewport could only translate; rotation and scale required typed inspector fields, unlike Unity/Unreal direct manipulation.
- **Decision**: Extend the gizmo framework with a mode switch. Translate keeps world-axis arrows; rotate draws three local-axis rings hit-tested against projected segments and previews an axis-angle rotation around the selection origin; scale draws local-axis box handles and previews a local-axis scale matrix. Ctrl/Cmd snaps translate to 0.25 units, rotation to 15 degrees and scale to 0.1; release sends one `transform` action with the composed local quaternion or scaled vector. Console Move/Rotate/Scale buttons and W/E/R select the mode; play mode hides all gizmos. No REST or schema change.
- **Consequences**: 731 tests green and both JS modules pass `node --check`; rotation and scale are local-axis only and each drag remains one undo entry. World-space rotation, multi-selection and numeric gizmo readouts remain future work.

### ADR-114: Toggle translate gizmos between world and local axes

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Translate handles were always world-axis, which makes placement awkward for rotated parents; Unity/Unreal editors switch between global and local handles.
- **Decision**: Add a `gizmoSpace` state to the viewer and a Space button plus X shortcut in the console. World mode keeps the fixed X/Y/Z arrows; local mode derives the arrow basis from the selected node's world matrix. Rotate and scale remain local-axis. Toggling cancels any active drag and re-renders. No REST or schema change.
- **Consequences**: 731 tests green and both JS modules pass `node --check`; translate now supports both spaces while each drag remains one action and one undo entry. World-space rotation, multi-selection and numeric gizmo readouts remain future work.

### ADR-115: Expose a prefab-instance inventory in the editor document

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Prefab instances carry editor-only links, but AI clients and the console had to scan every node to find them.
- **Decision**: Add a deterministic `prefab_instances` list (`id`, `name`, `instance`) to `editor_document`, derived from nodes with a `prefab_link`. Document it in schema 19 and the AI guide. No new action or persistence.
- **Consequences**: 731 tests green; linked roots are discoverable in one read, while the existing per-node `prefab_link` remains the source of truth. Nested and multi-root instances remain future work.

### ADR-116: Allow prefab reverts inside atomic batches

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: AI clients could batch scene edits, but recovering a prefab instance required a separate undo step, so recovery could not be composed atomically with other authoring.
- **Decision**: Add `revert_prefab` to `BATCH_ACTIONS`. The existing nested `_batch_depth` path applies it without a second history entry, and a failure still rolls the whole batch back. Bump the editor schema to 20.
- **Consequences**: 732 tests green; batch scripts can transform and recover instances under one undo entry. `apply_prefab` remains outside batches because it writes the prefab library; multi-root instances remain future work.

### ADR-117: Report prefab-link changes in scene diffs

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: `diff_scene` compared transforms, visibility, assets and components, but ignored editor-only prefab links, so AI clients could not see instance link changes.
- **Decision**: Add `prefab_link` to `NODE_FIELDS` and bump `SCENE_DIFF_SCHEMA_VERSION` to 2. Before/after values are link dictionaries or null.
- **Consequences**: 733 tests green; saved-scene comparisons now report link changes alongside other node fields. Nested and multi-root instance tracking remains future work.

### ADR-118: Support multi-root prefab instances as groups

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Only single-root prefabs received instance links, so multi-root prefab assets could be inserted but not reverted or applied as a unit.
- **Decision**: Link every inserted root with the same `PrefabLink`. Add `Prefab.from_nodes()` for multi-root capture and strip the source instance prefix from template IDs. Group helpers require all linked roots to share one parent and read their order from that parent. Revert removes the whole group, instantiates the prefab, and reinserts the new roots at the group's earliest sibling index. Apply captures the whole group as a multi-root prefab. Bump the editor schema to 21.
- **Consequences**: 735 tests green; multi-root insert, revert, apply and undo are covered, `prefab_instance_count` counts groups, and split groups fail with a clear 400 instead of silently replacing one root. Nested prefabs and per-property override tracking remain future work.

### ADR-119: Keep multi-root prefab groups atomic for delete and reparent

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: After multi-root support, deleting or reparenting one linked root could split a group, making later revert/apply fail.
- **Decision**: Make `delete_node` remove every root sharing the clicked link and return the group parent. Make `reparent_node` move every group root to the target and reject moves into the group itself. Split groups now fail with a clear 400.
- **Consequences**: 736 tests green; multi-root groups stay atomic through deletion, reparenting and undo. A future explicit unlink action can expose per-root detachment when needed.

### ADR-120: Support nested prefab instances with prefab schema 2

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Prefab capture and instantiation stripped every link, so nested instances were flattened and could not be composed, reverted or applied as nested prefabs.
- **Decision**: Prefab documents are schema 2 and persist each node's `prefab_link`; schema-1 documents load with flat links. Capture strips the captured roots' links and effective instance prefixes, preserves descendant links, normalizes each nested link relative to its immediate parent, and rejects root links, self-references and links outside their parent instance. Instantiation computes effective `outer.inner...` prefixes, rebases nested links and IDs, and allocates a deterministic `prefab` prefix when a nested template is instantiated without one. Bump the editor schema to 22.
- **Consequences**: 740 tests green; nested capture, instantiation, revert/apply, prefix rebasing and schema-1 migration are covered. Cross-prefab cycles, per-property overrides and automatic dependency validation remain future work; nested prefab assets should be saved alongside their dependencies.

### ADR-121: Track and resolve per-field prefab overrides

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Whole-instance revert/apply hid which fields diverged from the template and forced all-or-nothing resolution.
- **Decision**: Structurally map instance roots and children to prefab roots and children, stopping at nested prefab boundaries. Compare `name`, `visible`, `tags`, `layer`, transform position/rotation/scale, registry-resolved mesh/material ids and whole components. Expose `prefab_overrides` and `prefab_override_count` in `/api/editor`. Add `revert_prefab_override` and `apply_prefab_override` with `id` and `field`: revert restores one scene field through the undo history; apply clones the template, mutates one field, saves the library and swaps the cache only after success. Bump the editor schema to 23.
- **Consequences**: 744 tests green; field-level overrides are discoverable and resolvable. Component overrides are whole-component granularity, structural mismatches stop child mapping, nested applies update that prefab only because outer templates are snapshots, and apply is an asset write rather than a scene-undo operation.

### ADR-122: Deterministic component lifecycle hooks

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Authored components were inert data; editor play mode only advanced the game's own `update()` and provided no reusable component behavior loop.
- **Decision**: Add `keystone.lifecycle.ComponentRuntime`. Components opt in with `start(context)`, `update(context)` and/or `stop(context)` methods. Hooks receive a frozen `LifecycleContext(scene, node, component, dt, frame)`. Components run in scene DFS order and by component type; start happens once, update runs each fixed tick, stop runs in reverse start order, components without hooks are ignored, and components added after start begin on the next tick. Editor play snapshots the scene, starts the runtime before the first frame, updates it before each `game.update()`, and stops it before restoring the authored scene. Editor schema 24 advertises hooks in component schemas and includes the runtime active/frame/started/hooks summary in play state.
- **Consequences**: 750 tests green; authored behaviors run deterministically in editor play mode and games can opt into the same runtime without changing the five-operation contract. Hook priorities, per-hook error isolation, automatic windowed-engine wiring and multi-scene behavior remain future work.

### ADR-123: Additive scene groups with persisted metadata

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The editor edited one scene at a time; Unity/Unreal-style additive authoring needs named scene containers that can be loaded, saved and unloaded independently.
- **Decision**: Add `SceneGroup(name)` metadata on container nodes and persist it in scene snapshot schema 4; schema 1-3 documents load without groups. Add `add_scene` (load a `.kscene` through the library as a named child group, clone its roots with prefab links/components/nested groups, and rename only colliding node IDs), `unload_scene` (history-backed removal) and `save_scene_group` (write group children through a temporary Scene using the current camera/environment). Expose `scene_groups`/`scene_group_count` and node `scene_group` in `/api/editor`. Bump the editor schema to 25 and scene diff schema to 3.
- **Consequences**: 753 tests green; additive scene groups survive whole-scene save/load, save in place and unload with undo. Added scene camera/environment are ignored, saving uses the current editor settings, container transforms are not persisted, save-as is not exposed, and multi-selection remains future work.

### ADR-124: Selection sets and batch authoring

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The editor selected one node; Unity/Unreal-style authoring needs ordered selection sets and batch transform, visibility and delete operations.
- **Decision**: Keep `selected_id` as the primary node for backward compatibility and add an ordered `selected_ids` set. Add `select_many` with replace/add/remove/toggle modes, `transform_selection` (world position delta plus local rotation/scale deltas applied to top-level selected nodes only), `toggle_selection_visible` and `delete_selection` (deduplicated prefab groups), each scene edit using one undo entry. Expose `selected_ids`/`selection_count` and multi-select flags. Make the hierarchy multi-select, Ctrl/Cmd-click viewport selection toggle, and draw a centroid group-translate gizmo while rotate/scale stay single-selection. Bump the editor schema to 26.
- **Consequences**: 755 tests green; batch authoring, selection modes, parent/child deduplication, visibility toggles, delete/undo and console multi-select are covered. Group rotate/scale around a shared pivot, box selection and multi-node inspector fields remain future work.

### ADR-125: Group rotate and uniform scale around the selection centroid

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Multi-selection supported only translation, so rotating or scaling several nodes around a shared center required per-node edits.
- **Decision**: Extend `transform_selection` with `pivot`, `group_rotation` (world quaternion) and positive uniform `group_scale`. Group mode cannot mix the independent position/rotation/scale fields, applies to top-level selected nodes, converts new world positions back through the parent inverse, composes local rotations through the parent world rotation, and multiplies local scales uniformly. The multi-selection gizmo now renders world rings/scale handles at the centroid, previews the same `T(pivot) * T * T(-pivot)` transform across selected subtrees, and submits one action with undo. Bump the editor schema to 27.
- **Consequences**: 756 tests green; group rotation and uniform scale around the centroid preview and commit correctly for root selections, and parent/child selection deduplication is retained. Non-uniform parent transforms can make the local decomposition approximate, group scale is uniform rather than axis-local, and box selection/multi-node inspector editing remain future work.

### ADR-126: Viewport marquee box selection

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Viewport selection required individual clicks; multi-selection needed a marquee gesture without disrupting camera orbit and gizmo drags.
- **Decision**: Add an explicit box-select mode (`B` or the console button). In that mode, left-drag draws an overlay rectangle, projects each visible node's eight world-AABB corners, and selects nodes whose screen AABB intersects the marquee. No modifier replaces the selection, Shift adds, and Ctrl/Cmd toggles; hits are submitted through the existing `select_many` action, so highlighting and the batch centroid gizmo work unchanged. Gizmo handles keep pointer priority; pointercancel, mode changes and play-mode editing disable cancel the marquee. No API or schema change.
- **Consequences**: 756 tests green; marquee selection reuses the selection-set contract and static console/viewer coverage verifies the wiring. Hidden/meshless nodes and nodes with bounds crossing the camera plane are not box-selected; box mode suppresses orbit until toggled off, and multi-node inspector fields remain future work.

### ADR-127: Multi-node shared inspector editing

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The inspector edited only the primary node; multi-selection could not batch-edit shared name, visibility, tags, layer or absolute transforms.
- **Decision**: Add `set_selection_properties` (name/visible/tags/layer) and `set_selection_transform` (absolute local position/rotation/scale), each applying the same validated values to every ordered selected node under one undo entry. Expose `selection_summary` with per-field `shared`/`value` entries and a `mixed` list; the console shows mixed fields and routes Apply transform/Apply node properties through the batch actions when more than one node is selected. Bump the editor schema to 28.
- **Consequences**: 758 tests green; multi-node property/transform editing, shared/mixed summaries and undo are covered. Absolute transform edits intentionally collapse selected nodes to the same value, mixed fields show the primary inspector value until overwritten, and per-field mixed-value entry remains future work.

### ADR-128: Axis-local group scaling around the selection centroid

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Multi-selection scaling was uniform, so the X/Y/Z scale handles could not stretch a selection along one world axis.
- **Decision**: Let `group_scale` be either a positive scalar (uniform) or three positive X/Y/Z factors. Group scaling applies the factors to world offsets from `pivot`, multiplies local scale components by the same factors, and converts positions back through the parent inverse; group rotation still works alongside it. The multi-selection scale gizmo previews `T(pivot) * S(axis) * T(-pivot)` for the dragged world axis and submits one `transform_selection` action with the corresponding factor array and undo. Bump the editor schema to 29.
- **Consequences**: 758 tests green; axis-local and uniform group scaling, previews, invalid-factor rejection and undo are covered. Rotated or non-uniformly parented nodes can only approximate world-axis scaling under the local TRS model, and multi-node inspector/box-selection refinements remain future work.

### ADR-129: Scene-group save-as with source settings and container transforms

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Additive scene groups ignored source camera/environment, discarded container transforms on group save and could not be saved under a new name.
- **Decision**: Persist optional source camera/environment documents in `SceneGroup` metadata and scene snapshot schema 5. `add_scene` captures the source documents and copies the source root transform/visibility onto the container. `save_scene_group` restores source settings through `scene_from_dict`, writes the container transform as the saved root transform, and accepts an optional `name` for save-as; save-as writes first, then updates group name/container name under one undo entry. Editor schema 30 and the scene-group inventory expose the source settings and container roots.
- **Consequences**: 760 tests green; source settings, container transforms, save-as, undo and cross-session reload are covered. Undo restores save-as metadata but leaves the newly written scene file as an asset side effect; legacy groups without stored settings fall back to current editor settings.

### ADR-130: Box selection proxies and near-plane clipping

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Marquee selection ignored hidden and meshless nodes and dropped AABBs whose corners crossed the camera near plane.
- **Decision**: Keep click-picking on visible mesh bounds, but build separate box-selection bounds for every mesh node regardless of visibility and world-position proxies for meshless/hidden nodes. Clip each world AABB's six faces against the camera near plane in view space, project the clipped polygon vertices, and marquee-test the resulting screen AABB; include the node if the camera lies inside its bounds. Proxies use an 8px screen tolerance. No API or schema change.
- **Consequences**: 760 tests green; hidden/meshless nodes and near-plane-crossing bounds are selectable, with static viewer coverage. Proxies can produce false positives for coincident empty nodes, click-picking remains visible-mesh-only, and box selection intentionally has no occlusion test.

### ADR-131: Named multi-step editor transaction history

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Undo/redo moved one step at a time and `/api/editor` exposed only stack depths, so an AI client could not see which authoring actions were undoable or roll back a named sequence in one request.
- **Decision**: Store a label with every `EditorHistory` entry. `apply(..., label=...)` records the action plus its `id`/`name` target, and atomic batches record one `batch N actions` entry. `undo` and `redo` accept a 1-100 `steps` count, return the number applied, preserve the remaining redo entries during multi-redo, and `describe()` exposes counts, the limit and newest-first `undo_stack`/`redo_stack` labels. The server validates step counts, derives labels from the action payload, and bumps the editor schema to 31. The console adds a History steps input and an undo/redo label readout.
- **Consequences**: 761 tests green; multi-step undo/redo, newest-first labels, batch labels, redo preservation and invalid-step rejection are covered. History labels are in-memory only (loading a scene or starting play clears them), and selection changes are intentionally not history entries.

### ADR-132: Real-time play mode with pause and resume

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The editor advanced play only when Step was pressed and had no paused state, so it could not behave like a Unity/Unreal game view.
- **Decision**: Add `play_pause` and `play_resume` editor actions, a `paused` flag in the play document, and editor schema 32. Pause/resume require an active play session and remain valid while paused. Step still advances the fixed frame count and keeps the paused flag. The console Play button starts a guarded real-time loop that batches elapsed frames into `play_step` requests at the fixed step, refreshes the scene, and stops on Pause, Stop, or an error; Pause/Resume buttons and a paused play-state label expose the loop, and Step pauses a running loop before advancing.
- **Consequences**: 762 tests green; pause/resume validation, paused stepping, edit blocking and stop restoration are covered. Browser refresh cannot pause the loop, labels remain in-memory, and the loop advances at wall-clock rate with a 0.25s catch-up cap, so deterministic verification still uses `--simulate` or explicit play_step calls.

### ADR-133: Isolated prefab edit mode

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Prefabs could only be changed through an inserted instance, so editing a template required scattering scene objects and could not isolate the authored scene or its undo history.
- **Decision**: Add `edit_prefab`, `save_prefab_edit` and `close_prefab_edit` with editor schema 33. `edit_prefab` instantiates the template into a fresh scene with copied camera/environment settings, keeps the authored scene, selection and history aside, and marks edits dirty. `save_prefab_edit` captures the isolated root group through the existing multi-root prefab path and writes the library; `close_prefab_edit` optionally saves and restores the authored scene, selection and history. While editing, play, scene-library and prefab-library mutation actions are blocked; nested prefabs may be inserted but not reverted/applied. The editor document exposes `prefab_edit` with name, roots, root count and dirty state, and the console adds Edit, Save, Save & close and Discard & close controls.
- **Consequences**: 763 tests green; open/edit/save/discard, history isolation, blocked actions, camera copying, cross-session reload and missing-mode errors are covered. Prefab edits do not auto-refresh existing scene instances until revert/apply, asset writes are not scene-undoable, and nested prefab edit-in-place remains future work.

### ADR-134: Scene/Game viewport modes

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The WebGL viewport always used the free editor camera, so play mode never cut to the scene camera and there was no Unity/Unreal-style Scene view versus Game view separation.
- **Decision**: Track `viewMode` in `SceneViewer` (`scene` or `game`). Switching to Game view stores the editor camera, derives a camera state from the live scene yaw/pitch/position, follows the scene camera on every scene reload, and suppresses pointer navigation, click selection, box selection, rim highlights and gizmos. Switching back restores the editor camera. The console adds a View: Scene/Game toggle, Play auto-switches to Game view and Stop returns to Scene view, and Reset view re-derives the game camera. No API or schema change.
- **Consequences**: 763 tests green; static viewer/console coverage confirms the mode, camera derivation and auto-switch wiring. Game view is still the WebGL inspection approximation rather than the authoritative OpenGL render, exposes the single scene camera, and offers no runtime input capture or resolution controls.

### ADR-135: Refresh authored prefab instances from the edited template

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Saving an isolated prefab edit left existing authored instances stale until each one was reverted or applied by hand.
- **Decision**: Add `refresh_prefab_instances` with a `name` and a boolean `keep_overrides` (default false). It replaces top-level authored instance groups of that prefab with the current template in one undo entry, skips nested or split groups, and when `keep_overrides` is true skips groups with field overrides. The action reports `refreshed`, `skipped_overrides`, `skipped_nested`, `skipped_invalid` and `total` counts, is blocked during prefab edit mode and play, and the console adds a Refresh instances button. Bump the editor schema to 34.
- **Consequences**: 764 tests green; force refresh, override-preserving skip, undo, missing-prefab and prefab-edit blocking are covered. Nested instances inside a refreshed group come from the template, overridden groups need explicit revert/apply resolution, and template writes remain asset side effects rather than scene-undo entries.

### ADR-136: Scene-view grid and persistent snap toggle

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The Scene view had no ground reference grid, and snapping required holding Ctrl/Cmd for every drag, which slowed precise authoring.
- **Decision**: Build minor/major grid lines and colored X/Z axes in the WebGL viewer and render them with the existing line shader only in Scene view, behind depth testing so geometry occludes the grid. Add Grid and Snap console toggles with G/S shortcuts. Snap now activates when the toggle is on or Ctrl/Cmd is held, and all translate/rotate/scale rounding routes through one `snapActive` predicate. No API or schema change.
- **Consequences**: 764 tests green; static viewer/console coverage verifies grid geometry, rendering, toggles and the snap predicate. Grid spacing and snap increments remain fixed, the grid is presentation-only and absent from Game view, and game-view camera controls stay disabled.

### ADR-137: Save a multi-selection as a multi-root prefab

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The editor could insert, revert and apply multi-root prefabs, but `save_prefab` only captured one node, so a multi-selection could not become a template.
- **Decision**: Accept an ordered `ids` list on `save_prefab`. Deduplicate ids in selection order, drop nodes whose selected ancestor already covers them, require the remaining top-level roots to share a parent, and capture them through `Prefab.from_nodes`. Single `id` behavior is unchanged. The console sends the whole selection automatically when more than one node is selected, and the editor schema reaches 35.
- **Consequences**: 765 tests green; multi-root save, library reload, duplicate-id dedupe, descendant folding, mixed-parent rejection and missing-id errors are covered. Captured roots must share a parent, asset writes remain outside scene undo, and nested prefab links are preserved by the existing capture path.

### ADR-138: Perspective and orthographic view presets

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The Scene view was perspective-only, so axis-aligned top/front/side authoring common in Unity and Unreal was unavailable.
- **Decision**: Track a Scene-view projection mode and preset in `SceneViewer`. A projection button cycles Persp, Top, Front and Side (O shortcut). Orthographic presets reuse the editor camera state, orient yaw/pitch for the axis, and use a standard orthographic matrix sized by the camera distance; wheel zoom changes the orthographic height. Game view remains perspective, and grid, picking, box selection and gizmos continue through the same view-projection path. No API or schema change.
- **Consequences**: 765 tests green; static viewer/console coverage verifies the projection matrix, presets, button and shortcut wiring. Presets snap the camera to world axes without an up-axis switch, orthographic size is tied to the orbit distance, and no separate per-viewport camera state is stored.

### ADR-139: In-console prefab override panel

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The API reported per-field prefab overrides, but the console hid them, so resolving a divergence still required hand-written API calls.
- **Decision**: Render `prefab_overrides` in the console as instance groups with errors, per-node/field rows showing template and instance values, and Revert/Apply buttons that call the existing `revert_prefab_override` and `apply_prefab_override` actions. Build the DOM with `textContent` and `createElement`, refresh the scene after each action, and keep the existing busy/run guard. No API or schema change.
- **Consequences**: 765 tests green; static console coverage verifies the panel and both actions. Revert remains scene-undoable, Apply remains an asset write, and large component values wrap instead of expanding the panel width.

### ADR-140: Structured camera, environment and render-toggle inspector

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Camera and lighting authoring required hand-editing a raw JSON textarea, which was slow and error-prone for people and AI clients.
- **Decision**: Add labeled camera position/yaw/pitch/fov controls, environment light direction/color/intensity, ambient, fog density, and shadows/color/post/bloom/sprites/culling toggles. Fill them from `scene_settings` on every editor refresh, submit only the edited camera or environment fields through the existing validated `set_scene` action, and keep the JSON textarea as an advanced fallback. No API or schema change.
- **Consequences**: 765 tests green; static console coverage verifies the controls, fill path, readers and both apply actions. Near/far, background/sky and point-light fields stay in advanced JSON, toggle state follows the editor document after undo, and partial environment payloads preserve untouched engine fields.

### ADR-141: Live play snapshot and status inspection

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Play mode exposed frames and component lifecycle but not the game's own snapshot or status, so inspecting runtime state required a separate simulation.
- **Decision**: Add `status` and `snapshot` to the play document while play is active, with `status_error` and `snapshot_error` when a game hook fails. Snapshots are JSON-checked before exposure; stopped play returns both as null. The console renders the play document as JSON under a live snapshot panel. Bump the editor schema to 36.
- **Consequences**: 767 tests green; active/stopped shapes, JSON snapshots and failing hooks are covered. Snapshot calls run under the editor lock on each editor document refresh, game hooks remain foreign code, and non-JSON snapshots surface as errors rather than breaking the API.

### ADR-142: Deterministic project export bundles

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Projects could be created and opened, but shipping a game still required manual file copying and no build artifact recorded what was packaged.
- **Decision**: Add `--export DIR` for `--project`. Export loads and validates the project game, assets, scenes and prefabs, then copies runtime project files while excluding caches, tests, docs and a local engine source tree. It vendors the installed `keystone` package under `vendor/keystone`, writes `run.py`, `requirements.txt` and `EXPORT.md`, and finishes with a schema-1 `BUILD.json` containing sorted relative paths, sizes and SHA-256 hashes plus scene/prefab/file totals. A non-empty destination is refused unless `--force` is passed; the destination may sit inside the project because its subtree is excluded from the copy.
- **Consequences**: 771 tests green; bundle structure, hashes, launcher execution, force behavior, CLI output, validation failures and development-file exclusion are covered. The bundle still needs the pinned runtime dependencies, game modules with same-named imports can share `sys.modules` during validation, and export is a copy operation rather than a standalone executable build.

### ADR-143: Inline animation clip preview and scrubber

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The engine had deterministic clips, sampling and pose application, but the editor could not preview an authored clip, so animation remained a code-only feature.
- **Decision**: Add `preview_animation` with an inline schema-1 clip document and a non-negative preview time. The action parses through `AnimationClip.from_dict`, samples the pose, applies it with `apply_pose` in one undo entry, and exposes `animation_preview` with name, time, updated node ids and track count. The console adds a clip JSON editor, preview time, Preview animation and Sample selected node actions. Bump the editor schema to 37.
- **Consequences**: 772 tests green; pose application, undo, invalid time/clip rejection, play-mode blocking and sample generation are covered. Clips are inline and non-persistent for now, unknown node ids are ignored by `apply_pose`, and previews overwrite scene transforms until undo or another preview.

### ADR-144: File-backed animation clip library

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Animation preview accepted only inline clip JSON, so authored clips could not be saved, listed, or reused between editor sessions.
- **Decision**: Add `AnimationLibrary` over `.kanim` documents in a project `animations/` directory, with save/load/delete/restore/trash and stable entries. Add `--animation-dir`, default it to `DIR/animations` for projects, and expose the inventory in `/api/editor`. Add `save_animation`, `delete_animation` and `restore_animation`; `preview_animation` now accepts a library `name` or inline `clip` and reports its source. The console adds a clip-name field, datalist, save/delete/restore controls and preview-by-name. Bump the editor schema to 38.
- **Consequences**: 775 tests green; library round trips, cross-session reload, preview by name, delete/restore, missing-library errors and ambiguous preview payloads are covered. Clip names are portable file stems, save is an asset write rather than scene undo, and there is no rename/duplicate or timeline keyframe editor yet.

### ADR-145: Workspace layout persistence

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The browser editor forgot its Scene camera, view mode, projection, grid and snap settings on every reload, unlike Unity/Unreal workspaces.
- **Decision**: Store a schema-free layout snapshot in browser `localStorage` under a per-game key. Snapshots contain the editor camera target/distance/yaw/pitch, Scene/Game mode, projection preset, grid and snap. Camera drags, wheel zoom, reset/focus and the viewport toggles schedule a debounced save; the console restores the layout after the first scene and editor load, and a Reset layout button clears the record and restores defaults. Storage failures are ignored and malformed records fall back to defaults. No API or schema change.
- **Consequences**: 775 tests green; static viewer/console coverage verifies snapshots, restoration, debouncing and reset wiring. Layout is per browser and game name, Game view still re-derives its camera from the live scene, and Reset layout is local rather than a server operation.

### ADR-146: File-backed material library and editor

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Materials are core PBR assets, but the editor could only assign materials created in game code; it could not author, save or reuse material assets.
- **Decision**: Add `MaterialLibrary` over `.kmaterial` JSON documents with save/load/entries/register-all and texture-id resolution. Add `--material-dir`, default it to `DIR/materials`, and expose the inventory in `/api/editor`. Register saved materials as `material.<name>` after the game scene builds but before scene/prefab libraries load. Add `save_material` (writes and registers) and `assign_material` (applies or clears a node material under one undo entry). The console edits color, metallic, roughness, emissive, specular, shininess, checker and texture id and can save, assign or clear. Bump the editor schema to 39.
- **Consequences**: 778 tests green; library round trips, texture resolution, registry registration, assignment/undo, cross-session reload, missing-library errors and missing-material errors are covered. Delete/restore and material graphs remain future work, saving is an asset write rather than scene undo, and material registration depends on the game exposing an AssetRegistry.

### ADR-147: Scene-view pivot icons for meshless nodes

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Meshless nodes (empties, group containers and other scene markers) were selectable through box proxies but invisible in the Scene view, making them hard to find and author.
- **Decision**: Draw a small amber three-axis pivot cross at every meshless node's world position using the existing gizmo line shader and the `boxProxies` positions. Selected pivots tint green, the icon scales with camera distance through `gizmoScale`, and the pass is skipped in Game view. No API or schema change.
- **Consequences**: 778 tests green; static viewer coverage verifies the pivot geometry and render pass. Icons are scene-view presentation only, depth-tested against geometry, and do not replace click selection or box-proxy hit testing.

### ADR-148: Draggable hierarchy tree

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The hierarchy was a flat multi-select list; reparenting required the separate parent dropdown and Reparent button, unlike Unity/Unreal tree drag-and-drop.
- **Decision**: Replace the hierarchy `<select>` with a role-tree list of draggable rows showing indentation, prefab badges and selection state. Clicking selects, Ctrl/Cmd-click toggles, dragging a row onto another node calls `reparent_node` with that node as parent, and dropping on empty hierarchy space reparents to the scene root. Drag-over rows and the tree background get dashed feedback. The server remains authoritative for self/descendant/prefab-group validation. No API or schema change.
- **Consequences**: 778 tests green; static coverage verifies tree semantics, draggable rows, drag/drop wiring and reparent routing. Drag/drop is not covered by a real-browser integration test, filtered views only show matching rows, and multi-select drag moves only the dragged node while prefab groups still move atomically through the server.

### ADR-149: Material delete and restore lifecycle

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Saved materials could be created and assigned but never removed, so the material library grew without a lifecycle.
- **Decision**: Add `MaterialLibrary.delete/trash/restore` using the shared recoverable trash helper. Add `delete_material` and `restore_material` actions. Deletion is refused while any node in the current scene references the registered material object; otherwise the file moves to `.trash`, the registry record is removed, and a later restore re-registers `material.<name>`. The console adds Delete material and Restore material controls. Bump the editor schema to 40.
- **Consequences**: 779 tests green; library delete/restore, in-use protection, registry removal/re-registration, inventory/trash exposure and restore are covered. Deleting a material still referenced by an unsaved or unloaded scene is the user's responsibility, and scene/prefab asset writes remain outside scene undo.

### ADR-150: Animation timeline scrubber

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Animation preview accepted only a typed time value, with no duration feedback or visual timeline for scrubbing.
- **Decision**: Add a range scrubber to the animation panel. Its duration comes from the selected library entry when available, otherwise from the maximum key time in the inline clip JSON, with a 0.01s floor and a safe 1s fallback for malformed input. Scrubbing mirrors the time field; releasing the scrubber previews once through `preview_animation`. The time field also clamps the scrubber. No API or schema change.
- **Consequences**: 779 tests green; static coverage verifies duration derivation and scrub/time wiring. Scrubbing records one preview undo entry per release, invalid inline JSON only affects duration estimation, and playback/loop controls remain future work.

### ADR-151: Real-time animation preview playback

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The timeline could scrub one pose at a time but could not play a clip continuously, so animation review required repeated manual releases.
- **Decision**: Add a `record` flag to `preview_animation` (default true); record-free frames apply the sampled pose without history. The console adds a Play/Pause button that records one initial frame, then drives wall-clock preview frames through direct API calls at roughly 30 fps, wrapping at the clip duration, capping elapsed catch-up, guarding one in-flight frame, and stopping on errors or any editor action. Bump the editor schema to 41.
- **Consequences**: 779 tests green; record-free history behavior, playback wiring, schema examples and duration/scrub integration are covered. Playback leaves the final pose in the scene until Undo, does not persist or loop-event, and the browser loop is not covered by a real-browser timing test.

### ADR-152: Collapsible hierarchy tree

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The draggable hierarchy rendered every node, so large scenes became a long list with no way to fold subtrees.
- **Decision**: Keep a client-side set of collapsed node ids. Rows with children get a toggle that stops propagation, flips the set, and re-renders; descendants of collapsed nodes are hidden unless a hierarchy filter is active, and a selection change expands the selected node's ancestors. No API or schema change.
- **Consequences**: 779 tests green; static coverage verifies collapse state, ancestor checks, toggle markup and selection reveal. Collapse state is not persisted across reloads, filtered views deliberately ignore folding, and drag/drop still targets visible rows.

### ADR-153: AI-readable scene validation report

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: AI and human authors could save scenes with unregistered assets, dangling prefab links or duplicate names without an explicit preflight report.
- **Decision**: Add `validate_scene`, returning a schema-1 report with `ok`, error/warning counts, node count and structured issues (`severity`, `node_id`, `field`, `message`). Check unregistered mesh/material references, dangling prefab links, blank names, duplicate names and empty scene groups; warn when the game exposes no AssetRegistry. The action does not mutate history, resets on the next editor action, and the console adds Validate scene with a compact count readout. Bump the editor schema to 42.
- **Consequences**: 780 tests green; valid, missing-material, dangling-link, duplicate-name and reset cases are covered. Validation uses registry identity and current prefab cache, reports no geometry/topology or performance issues, and does not block saving on errors.

### ADR-154: Editable snap increments

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Snap rounding was hard-coded to 0.25 units, 15 degrees and 0.1 scale, so authors could not match a project grid or angle convention.
- **Decision**: Store translate/rotate/scale snap increments on `SceneViewer`, validate them as finite positive numbers, and route translate, rotate and scale rounding through those values. The console adds Snap move/rotate/scale number inputs, persists increments in the workspace layout snapshot, restores validated values, and resets defaults (0.25, 15, 0.1) with Reset layout. No API or schema change.
- **Consequences**: 780 tests green; static viewer/console coverage verifies editable increments, layout persistence and reset wiring. Extreme increments are allowed, snapping remains opt-in through the toggle or Ctrl/Cmd, and the nudge shortcuts keep their fixed 0.1/1.0 steps.

### ADR-155: Project-relative asset import from the editor

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The editor could assign registry assets but could not import new mesh, texture or prefab files, so authors had to edit `keystone.json` and restart the server.
- **Decision**: Add `import_asset` with a project-relative path. Require a `--project` directory, resolve and contain the path, accept only `.obj`, `.png` and `.kprefab`, append new paths to the manifest atomically, register `project:<path>` with replace semantics, and restore the previous manifest if registration fails. Re-importing a listed path refreshes its registry record without duplicating the manifest entry. glTF/GLB and other formats fail with guidance toward the CLI manifest pipeline. Expose `imported_asset` and `workspace.project_dir`; add a console path input, Import asset button and readout. Bump the editor schema to 43.
- **Consequences**: Targeted project/web tests and the full suite cover new, duplicate, traversal, missing, unsupported, glTF and no-project cases plus manifest rollback. Editor import is synchronous under the editor lock and does not hot-reload changed files outside an explicit import; glTF/GLB still requires a restart.

### ADR-156: Asset hot reload with scene and history rebinding

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: File-backed assets were loaded at import or startup, so re-exported `.obj`, `.png` or `.kprefab` files left stale payloads in the scene, and `AssetRegistry.refresh()` had no editor surface or structured report.
- **Decision**: Add `reload_assets`, which snapshots record ids before calling `AssetRegistry.refresh()`, maps changed old payload identities to new payloads, and rebinds scene node mesh/material references, inline material textures and every undo/redo snapshot. Failure and missing files keep the last-good payloads. Return a schema-1 `asset_reload` report with checked/reloaded/unchanged/failed/missing lists plus `rebound` and `history_rebound` counts; expose it in the editor document and add a console Reload assets button. Bump the editor schema to 44.
- **Consequences**: Targeted tests cover changed geometry, failed and missing files, history rebinding and a missing registry. Prefab record payloads reload in the registry but existing instances are not regenerated, external texture references inside unchanged prefab records are not rewritten, and the action is synchronous under the editor lock.

### ADR-157: Editor glTF/GLB scene import

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The CLI imported glTF/GLB scenes into prefab libraries, but the editor rejected those formats, so authors had to edit `keystone.json` and restart to bring in a 3D scene.
- **Decision**: Add `import_gltf` with a project-relative `.gltf`/`.glb` path and optional prefab name. Require a project directory and prefab library, validate the source and name before writing, append new sources to the manifest atomically, import through `import_gltf_prefab`, and report the generated prefab, derived `gltf.<name>.*` assets, duplicate/replaced state and manifest count. On failure roll back the manifest and remove newly added registry assets; pop any stale in-memory prefab cache entry. The console routes `.gltf`/`.glb` paths from the existing Import asset control. Bump the editor schema to 45.
- **Consequences**: Project and web tests cover import, reimport, insertion, bad suffix, traversal, missing file, missing project/library and manifest rollback. Reimported prefabs overwrite the library entry with an atomic write; overwritten derived assets are not restored if a partial import fails after registration, and external glTF buffers resolve relative to the source file.

### ADR-158: Project startup scene

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Opening a project still required remembering `--scene`, and no manifest field recorded which saved scene a game should start with.
- **Decision**: Bump the project manifest to schema 2 with an optional `startup_scene`, while accepting schema-1 manifests. `create_project` records `main`; `--project` opens the startup scene for scene-aware commands when `--scene` is absent, but `--describe`, `--validate-project` and `--export` never load it. Add `set_startup_scene` (name or null), require a project and scene library, validate that the saved scene exists, and write the manifest atomically. Expose top-level `startup_scene` plus console Set startup/Clear startup controls. Bump the editor schema to 46.
- **Consequences**: Project tests cover schema-1 compatibility, name validation, persistence and CLI defaults; web tests cover setting, clearing, missing scenes, invalid names, no project and no scene library. Scene names are limited to the library alphabet, and the console updates its document but does not automatically reload the scene after the change.

### ADR-159: Scene dirty tracking and revert

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The console could save and load scenes but never showed whether the live scene differed from its saved file, and there was no way to discard local edits.
- **Decision**: Track `saved_scene` and `scene_dirty` in `GameSession`. Mark scene-editing actions dirty, leave selects, play, validation, library-only actions and asset import/reload neutral, and clear the flag on save/load/revert. Add `revert_scene`, which reloads `saved_scene` (or `startup_scene` as a fallback), clears history and selection, and reports `name`, `node_count` and `cleared_history`. Update `saved_scene` on save/load/rename, clear it when the saved scene is deleted, and block revert during prefab edit/play. Expose top-level `saved_scene`, `scene_dirty` and `revert` document fields plus console Saved/Unsaved readout and Revert button. Bump the editor schema to 47.
- **Consequences**: Web tests cover dirty transitions, play neutrality, save/load, rename/delete interactions, revert, missing saved scenes and prefab-edit blocking. Undo after a revert cannot restore the discarded scene because history is cleared, and undo back to the saved state still reports dirty.

### ADR-160: Project asset inventory and forget-from-project

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Assets could be imported and reloaded but never removed from `keystone.json` or the registry, so discarded experiments accumulated and the editor had no manifest inventory.
- **Decision**: Expose `project_assets` in the editor document and add `forget_asset` for project-relative `.obj`, `.png` and `.kprefab` paths. Before writing, block when any scene node mesh/material, material texture, registry dependency or cached prefab references the asset. Then remove the path from the manifest atomically, unregister the file-backed record and keep the source file for re-import. Reject glTF/GLB with guidance and unsupported formats. Add a console Forget asset control and project-path suggestions. Bump the editor schema to 48.
- **Consequences**: Project tests cover manifest/registry removal, file retention, re-import, unsupported formats and rollback; web tests cover inventory, forgetting, node and prefab protection, glTF guidance, traversal and no-project errors. Saved scene files and prefab-library files that are not currently loaded are not scanned, so forgetting may still break those references.

### ADR-161: Editor project builds

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The validated project export existed only as a CLI command, so the console could edit and preview a project but could not produce a runnable build.
- **Decision**: Add `build_project` with a project-relative target (default `build`) and `force`. Resolve the target inside the project, run the existing validated export pipeline, and return only build metadata (`schema`, relative `target`, `BUILD.json` path, file/byte summary). Non-empty targets fail with force guidance; traversal, absolute paths, root targets and validation failures return 400. Add target/force console controls and a build readout. Bump the editor schema to 49.
- **Consequences**: Web tests cover a first build, BUILD.json/run.py creation, non-empty refusal, forced rebuild, traversal/absolute targets and missing project context. Builds are synchronous under the editor lock and can take seconds while the engine and project files are copied; the in-memory editor scene is not exported, only on-disk project files.

### ADR-162: Asset usage reports across live and saved content

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Forgetting an asset only checked the live scene, registry dependencies and cached prefabs; authors and AI clients could not ask where an asset was used before removing or replacing it, and saved scenes or prefab files could keep dangling references.
- **Decision**: Add `asset_usages` with exactly one of an exact asset id or a project-relative path. Return structured references from scene nodes (mesh/material/texture), registry dependencies/textures, in-memory and saved prefabs, saved scenes, plus project-manifest membership, registered/kind, reference count and `found`. Reuse the same report in `forget_asset`, which now blocks saved scene and prefab file references. Add a console Find usages button and readout. Bump the editor schema to 50.
- **Consequences**: Web tests cover live nodes, saved scenes, prefabs, project-path lookup, unknown ids, mutual-exclusion errors, traversal errors and saved-reference forget blocking. Saved-content scans load library entries on each request, so very large libraries make the action slower; unreadable entries are skipped rather than failing the report.

### ADR-163: Registry-backed material texture picker

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The material panel accepted a free-text texture id, so imported texture assets had to be typed manually and there was no visual confirmation of the chosen texture.
- **Decision**: Replace the texture id input with a select populated from registry texture assets, independent of the asset text filter. Preserve unregistered texture ids as a "missing" option, show a thumbnail from the asset preview metadata, and update the preview on selection changes. No API or schema change.
- **Consequences**: Static console tests cover the select, preview image, re-render wiring and missing-id fallback. The picker only lists registered textures; a missing id is preserved but saving it still fails through the existing material decoder until the texture is imported again.

### ADR-164: Deterministic animation state machines

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The engine had deterministic clips, crossfades, timed events and an animation controller, but no state machine, so games and AI clients had to reimplement state, parameter and trigger handling.
- **Decision**: Add `AnimationState`, `AnimationTransition` and `AnimationStateMachine` with named clips, loop/speed settings, parameter conditions (`greater`, `less`, `equal`, `not_equal`, `trigger`), declaration-order transitions, trigger consumption on entry, crossfade durations, clip events, a schema-1 JSON round trip and a report. States and transitions validate shapes, names, references, operators and finite values; the machine owns one `AnimationController`. Export the types from the public `keystone` package.
- **Consequences**: New tests cover parameter transitions, state speed/loop settings, trigger consumption, timed events, crossfades, serialization, reports and validation. The machine is synchronous and core-only; editor state-machine authoring and file libraries are not included yet, and multiple states sharing a clip name share one controller clip.

### ADR-165: File-backed state machines and editor preview

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The deterministic state machine core existed, but authors and AI clients could only use it from code; there was no library, console panel or scene preview.
- **Decision**: Add a `.kstate` `StateMachineLibrary` in the animation directory with atomic save, load summaries, recoverable delete and restore. Add `save_state_machine`, `delete_state_machine`, `restore_state_machine` and `preview_state_machine`. Preview loads a machine by name, applies a `parameters` object and `triggers` list, advances `frames` by a positive `step`, applies the final pose to the scene, and reports current state, parameters, events, updated nodes, record flag and the machine report. Add a console JSON authoring panel with save/preview/delete/restore controls and a library datalist. Bump the editor schema to 51.
- **Consequences**: Library and web tests cover save/load/delete/restore, preview transitions, pose application, record-free previews, malformed documents, missing names and missing libraries. Each preview starts from the saved machine state, so parameter changes and trigger consumption do not persist across requests; editing an existing machine still requires pasting its JSON because no load-to-editor action is included.

### ADR-166: Load state machines into the editor

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Saved `.kstate` machines could be previewed but not loaded back into the console JSON panel, so editing one required opening its file outside the editor.
- **Decision**: Add `load_state_machine`, which loads a saved machine and returns `state_machine_document` (`name`, `machine`) in the editor document. The console adds a Load state machine button that fills the name field and JSON textarea from the response. Reset the loaded document on every action and bump the editor schema to 52.
- **Consequences**: Web and static tests cover loading, missing names, missing libraries and textarea wiring. The action reads the file through the validated state machine parser, but the returned document is transient and is not persisted until Save is pressed.

### ADR-167: Shared asset assignment for multi-selection

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: `assign_asset` edited one node, so a multi-selection could not share or replace a mesh/material in one operation.
- **Decision**: Add `assign_asset_selection`, which resolves every selected node under the editor lock and runs the existing `assign_assets` validation for each node inside one history entry. The console adds an Assign to selection button that sends only non-empty mesh/material fields; single-node clearing stays on `assign_asset`. Bump the editor schema to 53.
- **Consequences**: Web tests cover two-node assignment, one-step undo, empty selection and invalid asset errors. Nested selections receive the assignment on every selected node, and the console cannot clear both fields across a selection.

### ADR-168: Copy/paste selection

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Multi-selection could transform and delete nodes but not copy or paste them; duplicate handled only one node at a time.
- **Decision**: Add `copy_selection`, which captures the top-level selected nodes as a detached clipboard `Prefab` (folding nested selections and requiring a shared parent), and `paste_nodes`, which instantiates fresh IDs under the selected node or an explicit `parent` in one undo entry. Expose a `clipboard` report (`count`, `names`) and console Copy/Paste buttons. Bump the editor schema to 54.
- **Consequences**: Web tests cover two-node copy/paste, fresh IDs, shared mesh values, one-step undo, parent paste and empty selection/clipboard errors. The clipboard holds payload references for the session, persists across scene edits, and is not written to disk.

### ADR-169: Library animation keyframe authoring

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Clips could be previewed, sampled, scrubbed and saved, but the editor could not add or remove keyframes, so animation authoring stopped at external JSON.
- **Decision**: Add `set_animation_key`/`remove_animation_key` for library `.kanim` clips. They target the selected node and one position/rotation/scale channel at a non-negative time; values default to the node's current transform. Set replaces a key within `1e-6` or inserts it sorted, remove drops the key and empty tracks, and both save the clip atomically and return an `animation_key` report. Add console channel selector and Set key/Remove key controls. Bump the editor schema to 55.
- **Consequences**: Web tests cover insert/replace/sorted times, current-transform defaults, explicit values, preview, removal, empty-track cleanup and error cases. Key edits write library assets and are not scene-undoable; the browser must preview separately to see the authored pose.

### ADR-170: Layer visibility toggles

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Scenes with many layers could not hide unrelated nodes, and there was no AI-readable layer inventory or visibility state.
- **Decision**: Add a `layers` inventory (`name`, `count`) and session-only `hidden_layers` to the editor document, plus `set_layer_visible`. Hidden layers remain in the scene document but the viewer filters them from scene-view rendering, picking, marquee bounds and pivots; game view ignores the filter. The console renders checkbox toggles. Bump the editor schema to 56.
- **Consequences**: Web tests cover counts, hide/show, node preservation and invalid inputs; static tests cover the toggle container and viewer wiring. Visibility is not persisted to layouts or project files, and hiding a layer does not clear a selection inside it.

### ADR-171: Node lock protection

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Large or prefab-heavy scenes could be accidentally transformed or deleted; there was no editor-only lock state or AI-readable lock report.
- **Decision**: Add session-only `locked_ids`, `set_nodes_locked` for an id list or current selection, a `locked` flag per node document, and top-level `locked_ids`/`locked_count`. Locked nodes and descendants reject transforms, batch selection transforms, delete selection/node, reparent, asset assignment, component edits and prefab revert/apply while remaining selectable and visible. Add console Lock/Unlock selection controls and a locked-count readout. Bump the editor schema to 57.
- **Consequences**: Web tests cover lock state, transform/delete/asset/component/reparent rejection and unlock recovery; static tests cover the console wiring. Locks are not persisted to project files or layouts, and refresh_prefab_instances is not yet lock-aware.

### ADR-172: Named scene-view camera bookmarks

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The editor camera could be reset or focused, but recurring inspection views had to be recreated manually every session.
- **Decision**: Add viewer `cameraBookmark`/`applyCameraBookmark` methods with finite target/distance/yaw/pitch validation. The console stores named bookmarks per game in `localStorage`, renders a sorted select, and provides Save view, Go to view and Delete view controls with a terse readout. No API or schema change.
- **Consequences**: Static tests cover the controls, script wiring and camera methods. Bookmarks are client-local, do not travel with the project, and malformed storage falls back to an empty set.

### ADR-173: Commit audit fixes unchanged reload identity

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1→3 audit found that `AssetRegistry.refresh()` re-registers a changed file even when its digest is unchanged. `reload_scene_assets` rebound only `reloaded` records, leaving scene and history references on the old payload object. Identity-based asset usage and forget protection could then miss live nodes after a no-op re-save.
- **Decision**: Rebind old payload identities for both `reloaded` and `unchanged` refresh results when the payload object actually changed. Add a regression that touches an identical `.obj`, reloads, asserts the node and history use the new registry payload, and confirms `asset_usages` still finds the node.
- **Consequences**: The audit fix is covered by the targeted web test and the full AIKit 6/6 gate. Unchanged records now do a small identity-map check even when their content did not change.

### ADR-174: Commit audit keeps startup scene in sync with library edits

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1→6 audit found that renaming or deleting a saved scene updated `saved_scene` but not the project manifest's `startup_scene`. A restart could open a missing startup scene.
- **Decision**: When the renamed/deleted scene is the startup scene and a project is configured, rewrite the manifest atomically through `set_project_startup_scene`. Rename rolls the file name back if the manifest write fails; delete clears the manifest before moving the file and restores the old startup value if the delete fails.
- **Consequences**: A new web test covers startup rename and delete persistence. Scene library operations are slightly heavier when they touch the startup scene; scenes without a project manifest behave as before.

### ADR-175: Commit audit orders asset refresh by dependencies

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1→9 audit found that `AssetRegistry.refresh()` walked source ids alphabetically. A changed prefab whose id sorted before its changed mesh dependency could load the old mesh payload and then keep it after the mesh reloaded.
- **Decision**: Compute a dependency-first refresh order from each record's current dependency edges, falling back to sorted order if a cycle or incomplete graph blocks progress. Keep report lists sorted for stable AI output. Add a regression where `aaa.prefab` depends on `zzz.mesh`; after changing both, the reloaded prefab must reference the reloaded mesh payload.
- **Consequences**: The new registry test and full AIKit gate cover the fix. New dependencies introduced only by a changed prefab file are still unknown until that prefab loads, so an exotic dependency-changing edit can retain the old order.

### ADR-176: Commit audit isolates state clips by state name

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1→12 audit found that `AnimationStateMachine` keyed its controller clips by `AnimationClip.name`. Two states with distinct clips sharing a clip name overwrote each other, so one state played the wrong animation.
- **Decision**: Register a `replace(clip, name=state.name)` copy for each state in the controller, and play/crossfade by state name. Reports continue to expose the original clip name. Add a regression where states `a` and `b` both use a clip named `shared` with different positions and assert each pose is preserved.
- **Consequences**: State-machine playback is isolated by state name even when source clips collide; controller `current` now names the active state rather than the clip. No schema or API change.

### ADR-177: Commit audit decouples crossfade time from playback speed

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1→15 audit found that crossfade progress advanced by `dt * playback speed`. A state with speed 0 could therefore start a crossfade that never completed, leaving the controller permanently blending.
- **Decision**: Advance `_blend_elapsed` by wall `dt` while playback speed continues to scale clip time. Add a zero-speed target transition test and adjust the existing non-unit-speed crossfade test to wall-clock duration.
- **Consequences**: Crossfades now always take their declared wall-clock duration regardless of clip speed; non-unit-speed playback still changes sampled pose time. No schema or API change.

### ADR-178: Commit audit reports inherited node locks

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1→End audit found that `node_document` marked only directly locked ids, while edit checks walked ancestors. A child of a locked parent appeared unlocked but could not be edited.
- **Decision**: Add an ancestor-aware `_node_locked` helper and use it for every node document's `locked` flag. Add a regression that creates a child under a locked parent, asserts the child reports locked, and confirms its transform is rejected.
- **Consequences**: Lock indicators now match enforcement for descendants. Locks remain session-only and `refresh_prefab_instances` remains outside lock enforcement.

### ADR-179: Merge-preserving prefab instance refresh

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: `refresh_prefab_instances` with `keep_overrides` skipped any instance whose fields differed from the current template, so authors could either propagate a prefab edit or keep instance edits, never both. Deriving overrides by comparing an instance with the *current* template was also wrong after a template edit: an untouched instance field could look like an override and block the new template value.
- **Decision**: Store each instance node's template values in `Node.prefab_base` when it is inserted, reverted or applied, and persist the mapping in scene snapshot schema 6. Override reports and `_resolve_prefab_override` compare current values with this baseline instead of the current template. `refresh_prefab_instances` with `keep_overrides: true` captures baseline-relative fields (including nested instance nodes), replaces instances with the current template, reapplies the captured values, and reports `preserved_overrides`/`dropped_overrides`; a false flag still performs a clean replacement. `apply_prefab_override` moves affected baselines to the value written into the prefab. Scene diff schema 4 reports baseline changes.
- **Consequences**: Template-owned changes now propagate to every instance while authored name, visibility, tags, layer, transform, mesh/material and component overrides survive. Baselines travel with `.kscene` files and undo snapshots. Structural edits are not field overrides: adding a child in the template adds it to refreshed instances, while an override on a template node that is removed is reported as dropped. Overrides remain editor metadata rather than prefab-file contents, and the editor document schema and five-operation game contract are unchanged.

### ADR-180: Commit audit rebinds cached prefab and clipboard payloads

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->21 audit found that `reload_scene_assets` rebound scene nodes and undo/redo snapshots after a same-content asset reload, but not the session's cached `Prefab` templates or clipboard. Inserting or refreshing a prefab could therefore reintroduce the stale mesh/material object that the reload had just replaced.
- **Decision**: Extend `reload_scene_assets` with optional `prefabs` and `clipboard` inputs, rebind node payloads inside every cached template and the clipboard through `_rebind_prefab_assets`, and report `prefab_rebound` and `clipboard_rebound`. Keep the existing `rebound` and `history_rebound` keys. Add a regression that saves a prefab and copies the selection before an unchanged reload, then asserts both caches and a newly inserted instance use the reloaded payload.
- **Consequences**: Same-content reloads now keep every editor-owned payload reference consistent. The report grows by two counts; callers that omit the new inputs keep the old behavior and fields. Prefab library files still store asset ids, so disk round trips were already safe.

### ADR-181: Commit audit restores saved-scene state after rename rollback

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->24 audit found that a startup-scene rename updates `saved_scene` before writing the project manifest. If the manifest write fails, the file rename is rolled back but `saved_scene` still names the rolled-back file, so dirty/revert state points at a missing scene.
- **Decision**: Capture the previous `saved_scene` before the library rename and restore it in the manifest-failure path before rolling the file back. Add a regression that forces `set_project_startup_scene` to fail and asserts the file, startup scene, saved scene and manifest all return to the original name.
- **Consequences**: Failed startup renames are now atomic from the editor's point of view. Successful renames and renames unrelated to the startup scene are unchanged; the fix adds no API or schema surface.

### ADR-182: Commit audit makes prefab refresh lock-aware

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->27 audit found that `refresh_prefab_instances` still replaced every top-level instance of a prefab, including groups with locked nodes. That bypassed the lock protection added for transforms, deletes, asset/component edits and prefab revert/apply.
- **Decision**: Add an optional `is_locked` predicate to `refresh_prefab_instances`. A group whose root or any descendant is locked is skipped before override capture, and the report gains `skipped_locked`. The server passes its ancestor-aware lock check. Add a regression that locks only a child of one instance, renames the prefab, refreshes, and asserts one group is skipped and the other updated; unlocking makes both refresh.
- **Consequences**: Locked prefab instances now survive a bulk refresh while unlocked siblings still receive template changes. The action reports the skipped count instead of failing, so a mixed scene remains usable. Direct calls without `is_locked` keep the previous behavior.

### ADR-183: Commit audit scopes prefab apply baselines to the applied group

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->30 audit found two problems in the new override baseline flow. Applying an outer prefab seeded baselines for every descendant, including nested prefab groups, which erased nested overrides. Applying also rebased baselines before the prefab library write, so a failed write left instance metadata pointing at a template that was never saved.
- **Decision**: Remove baseline seeding from `apply_prefab_instance` and add `seed_prefab_instance_baselines`, which rebases only the applied group's own nodes and skips nested groups. The `apply_prefab` action calls it only after the library write succeeds. Add regressions for nested overrides surviving an outer apply and for a failed library write keeping the old template, baseline and override report.
- **Consequences**: Nested instance overrides survive outer prefab applies, and failed applies are metadata-atomic. `apply_prefab_instance` is now a pure capture helper; callers that need baselines call the new helper after persistence.

### ADR-184: Commit audit rebases prefab edit baselines after save

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: Moving baseline seeding out of `apply_prefab_instance` fixed apply rollback and nested-group preservation, but `save_prefab_edit` still captured the edit scene without rebasing it. After a successful save, the isolated edit scene reported every saved name/transform as an override against the old baseline.
- **Decision**: Call `seed_prefab_instance_baselines` on the edit scene after the prefab library write succeeds. Add assertions that a saved prefab edit reports zero overrides while remaining dirty until the save.
- **Consequences**: The edit scene reflects its saved prefab immediately, and a failed write still leaves the edit baseline untouched. The direct apply action already uses the same post-write rebase helper.

### ADR-185: Commit audit restores replaced glTF assets on failed re-import

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->3 audit found that a failed glTF re-import rolled back only registry ids that did not exist before the attempt. Existing `gltf.<name>.*` ids replaced during the partial import stayed bound to the new payloads, so the old prefab file could resolve to a half-imported material, mesh or texture.
- **Decision**: Snapshot every `AssetRecord` before `import_gltf_prefab`, remove ids added by the failed attempt, and re-register every changed or missing old record with its original payload, kind, source and dependencies. Restore non-prefab records before prefabs so dependency resolution sees the old graph. Add a regression that changes a glTF material, forces `Prefab.from_scene` to fail after registration, and asserts old payload identities and digests return.
- **Consequences**: Failed glTF imports are registry-atomic even when they overwrite a previously imported scene. The manifest rollback is unchanged, and the helper only runs on the failure path.

### ADR-186: Commit audit clears forgotten assets from undo history

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->6 audit found that `forget_asset` scanned authored content for references but ignored undo/redo snapshots. Deleting a node that used an asset let the asset be forgotten, and Undo then restored a node bound to an unregistered mesh, material or texture payload.
- **Decision**: Add `EditorHistory.clear_payloads`, which walks every undo and redo snapshot and nulls matching mesh/material references or replaces inline materials whose texture matches a forgotten texture. The `forget_asset` action calls it after the registry removal succeeds and reports `history_cleared`. Add a regression that deletes an asset-bearing node, forgets the source, undoes, and asserts the restored node has no mesh.
- **Consequences**: Forgetting an asset can no longer resurrect stale payloads through history. Undo still restores the structural edit, but the forgotten reference becomes empty. Reports and schema grow by one count; live and saved content checks are unchanged.

### ADR-187: Commit audit reports history references in asset usage

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->9 audit found that `asset_usages` scanned the live scene, registry, prefabs and saved scenes but not undo/redo snapshots. After a node using an asset was deleted, the usage report could say the payload was unused while history still held it.
- **Decision**: Add `EditorHistory.count_payloads` and a `history_references` count to `asset_usage_report`. Count mesh, material and inline-material-texture identities in both stacks. Keep the count out of `references`/`found` because `forget_asset` now safely clears history instead of blocking on it. Add a regression that creates and deletes a node, then checks the count without changing authored references.
- **Consequences**: AI and human clients can see pending history references before forgetting or reloading an asset. The report is additive; existing `references` semantics and the forget gate stay authored-content-only.

### ADR-188: Commit audit completes state-machine library lifecycle

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->12 audit found that the `.kstate` library added in this range could save, load, delete and restore machines, but had no rename or duplicate operations. Prefab and scene libraries already expose both, so AI and editor clients had to edit `.kstate` files by hand to reorganise machines.
- **Decision**: Add `StateMachineLibrary.rename` and `duplicate`, preserving the JSON body and rejecting source/target collisions, missing entries and same-name duplicates. Add `rename_state_machine` and `duplicate_state_machine` editor actions, mark them scene-neutral, bump the editor schema to 58, and map file collisions to a 400 with a name-choice fix. Add library and web regressions.
- **Consequences**: State machines now share the library lifecycle shape of prefabs and scenes. The console has no rename/duplicate buttons yet; the actions are available to AI clients and scripts, and adding controls later needs only a UI delivery task.

### ADR-189: Commit audit clears forgotten assets from the clipboard

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->15 audit found that the selection clipboard, added in this range, was not covered by `forget_asset`. After copying a selection and deleting its source node, an asset could be forgotten while the clipboard still held the payload; pasting then reintroduced an unregistered mesh/material/texture.
- **Decision**: Add `clear_clipboard_payloads` and `count_prefab_payloads`. `forget_asset` clears matching clipboard payloads after registry removal and reports `clipboard_cleared`; `asset_usages` reports `clipboard_references` separately, without raising `references` or blocking forget. Add a copy-delete-forget-paste regression that asserts the pasted node has no mesh.
- **Consequences**: Forgotten assets no longer survive in the clipboard, and clients can see pending clipboard references before forgetting. Existing clipboard content and references semantics are otherwise unchanged.

### ADR-190: Commit audit prunes selection when hiding a layer

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->18 audit found that hiding a layer removed its nodes from the viewport but left them in `selected_ids`. Inspector edits and gizmos could therefore continue to act on invisible nodes.
- **Decision**: When `set_layer_visible` hides a layer, filter the current selection to nodes whose layer remains visible and update the primary selection through `_set_selected_ids`. Showing the layer again does not restore the pruned selection. Add a two-layer selection regression.
- **Consequences**: Selection and hidden-layer state stay coherent across editor documents. Hiding a layer is still session-only and neutral to scene dirtiness; existing viewer filtering is unchanged.

### ADR-191: Commit audit rebinds registry material textures on reload

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->21 audit found that asset reload rebound scene nodes, history, cached prefabs, clipboard and inline node materials, but left registry material records pointing at the old texture object. A future node assigned from the registry could render with stale texture data.
- **Decision**: Before rebinding scene payloads, walk registry material records, replace any inline texture found in the reload map, re-register the material payload and add the old-material-to-new-material mapping so scene, history, prefab and clipboard references converge on the same object. Report `registry_rebound`. Add a texture-file reload regression that checks registry material, node material and texture identities.
- **Consequences**: Texture hot reload now reaches every material owner, not only live scene nodes. The report grows by one count; failed or missing textures still keep last-good payloads.

### ADR-192: Commit audit loads prefab sources after non-prefab sources

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->24 audit found that dependency-first refresh used each prefab's previous dependency list. A changed prefab that newly referenced a changed mesh not in its old list could load before the mesh and keep the old payload.
- **Decision**: When selecting the next ready source, order non-prefab kinds before prefabs, then sort by id. Prefabs therefore resolve new asset ids against freshly loaded meshes, materials and textures while prefab-to-prefab edges still follow the old graph. Add a regression where an initially meshless prefab starts referencing a changed mesh.
- **Consequences**: New prefab asset edges are handled without a second refresh pass. The known limitation remains for new material-to-texture edges, which are both non-prefab and still ordered by the old graph.

### ADR-193: Commit audit blocks deleting ancestors of locked nodes

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->27 audit found that lock checks covered selected nodes and ancestors but not descendants. Deleting an unlocked parent removed a subtree containing a locked child, bypassing lock protection.
- **Decision**: Add `_ensure_subtree_unlocked_locked` and use it for `delete_node` and `delete_selection`. It reports every locked node in the affected subtrees. Child creation under locked parents remains allowed because such children inherit the lock; only destructive deletion is blocked.
- **Consequences**: Locks now protect complete subtrees from deletion without changing hierarchy-growth behavior. Existing lock and inherited-lock tests remain valid.

### ADR-194: Commit audit makes prefab override apply transactional

- **Date**: 2026-11-08
- **Status**: Accepted
- **Context**: The cumulative 1->30 audit found that `apply_prefab_override` rebased instance baselines before the prefab library write. If the write failed, the template stayed old but the override diff disappeared, so clients could no longer see or revert it.
- **Decision**: Snapshot every node baseline before applying an override, and restore all baselines if template construction or the library write raises. Add a regression that patches `PrefabLibrary.save` to fail and asserts the old template and override report remain.
- **Consequences**: Failed override applies are metadata-atomic. Successful applies still rebase all affected instances and assign the updated prefab cache only after persistence.
