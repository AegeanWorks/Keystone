# Changelog

All notable changes to Keystone. The version below is the single release
identifier; `keystone/_version.py` and `pyproject.toml` must agree with it
(`tests/test_version.py` fails on drift).

## 0.45.0

Shipped features at this release, grouped by capability. Later sections record
changes that do not bump the release number yet.

### Rendering
- OpenGL 3.3 core forward renderer: GLSL 330, indexed meshes, depth/culling,
  Blinn-Phong and PBR shading, sRGB pipeline, directional shadows, post
  color-grade, bloom diffusion and point-sprite particles.
- Deterministic CPU frustum culling, GPU hardware instancing, static batch
  planning and world-space merge, plus skin-aware merge.

### Scene and assets
- Scene graph with stable node IDs, tags, layers, typed components and
  cached GPU meshes.
- Asset registry with content digests, dependency ordering, hot reload and
  recoverable library deletes.
- glTF/GLB import with PBR materials, textures, skins and TRS hierarchies.
- Versioned scene snapshots (schema 6), structured scene diffs and bounded
  undo/redo.

### Simulation
- Fixed-step clock with a bounded catch-up budget.
- Rays, AABB and sphere queries, sphere pushout, spatial-grid broadphase,
  AABB character movement, trigger tracking and filtered raycasts.
- Seeded CPU particle emitters with swept collision, bounce, friction and
  contact-kill.

### Animation
- Keyframe clips, looping controller, crossfade blending, timed events and
  pose application.
- 1D blend spaces, blend states, parameter-driven state machines and
  file-backed `.kanim` / `.kstate` libraries.
- Blend states loop, wrap and crossfade at the blend space's own duration.

### Tooling and AI
- Headless simulation and rendering with machine-readable frame reports
  (report schema 11) and visual pixel diffs.
- Deterministic discovery (`--describe`), `--verify-determinism`,
  `--expect-hash` and pinned baselines.
- Seeded bot playtester with transcripts and fairness validation.
- Local web console, scene editor (editor schema 59) and WebGL2 viewer.

### Adoption fixes
- `GameModule.bind_input(mapping)` lets a game bind its own live controls;
  the engine merges them over its defaults and reports the hook in
  `--describe` under `capabilities.input_bind_hook`.
- `InputMap.unbound_buttons()` reports declared buttons that no binding can
  produce, so a misleading `actions()` contract is visible.
- The real key table includes the number row, `InputMap.unknown_keys()` and
  `Engine.unbound_buttons`/`unknown_keys` expose dead bindings after the game
  hook, and `--describe` reports `capabilities.input_keys`.
- `AssetRegistry.reload(scene)` refreshes sources and rebinds live scene
  nodes, registered materials and inline textures, reporting `rebound` and
  `registry_rebound`. The web editor now calls the same core rule.
- `python -m keystone --version` prints the release version; the version is
  single-sourced through `keystone/_version.py`.
- `--frames` rejects 0 instead of silently running 1 or 120 frames.
- Component documents reject unknown keys and unknown dataclass fields.
- `apply_pose(scene, pose, mask={...})` writes only the named channels, so a
  game can animate rotation/scale while its simulation owns position.
- `PerspectiveCamera.up()` and `basis()` expose the camera frame for viewmodel
  and billboard work instead of hand-derived cross products.
- `plan_batches` reports `node_draws` and `instanced_calls` beside the
  compatibility `draw_calls`, so a plan metric states what it counts.
- `Canvas` measures and aligns text: `text_width`, `line_height`, `fit_text`,
  `text_right` and `text_center`, matching the shared font metrics.
- `TextureData.pattern("cell"|"grid"|"panel"|"rivets"|"noise")` builds
  deterministic procedural textures with a seed. The margin presets are linear
  in pixel count (panel 180ms -> 2ms, rivets 288ms -> 6.5ms at 512x512) and
  `MAX_PATTERN_SIZE` caps a single allocation at 16 MB.
- `keystone.testing.scene_fingerprint` and `assert_scene_budget` let a testbed
  pin content and coarse budgets instead of exact node counts.
- `run_bot(..., on_frame=, on_event=, events=)` reports read-only per-frame
  telemetry and named frame events without altering the transcript or hash.
- `--policy package.module:factory` registers a game's own bot policy;
  `keystone.playtest.load_policy` resolves built-ins and module factories.
- Locked editor nodes now also reject `set_node` and `set_selection_properties`;
  previously a lock could be bypassed by renaming, re-layering, re-tagging,
  hiding or bulk-editing the node.
- Scene snapshots and animation clips serialize every vector component as a
  float, so a document no longer changes textually across one save/load cycle
  when a consumer built a `Vec3`/`Quat` from ints.
- WAV decoding scales both signs by 32767 and clamps to [-1, 1], so a round
  trip is symmetric; negatives no longer drift toward zero while positives do
  not, and full-scale +/-1.0 now round-trips exactly.
- A failure after the game loads now reports "could not finish" with advice
  naming the failing step; previously every failure claimed the game factory
  was invalid, and a corrupt `--compare-baseline` report leaked a raw JSON
  decoder message.
- A frame report's node `bbox` is now the on-screen silhouette clipped at the
  near plane, so a ground plane under the camera spans the frame instead of
  collapsing to the zero-height line of its far edge.
- A `--project` load failure now points at the `game` field in `keystone.json`;
  previously it advised passing `--game`, which the project already supplies.
- An editor action that returns 400 now carries a `fix` matched to its cause
  (such as `--scene-dir` for a missing scene library) instead of the same
  transform-values hint for every failure.
- A scene can now hold multiple point lights (`Scene.point_lights`, up to
  eight lit at once). `scene.point_light` still reads and writes the first
  light, so existing code is unchanged.
- `Node.sprite` places a camera-facing billboard (`Sprite(size, color, alpha)`)
  as scene content; sprites no longer require a particle emitter, and the
  frame report gives a sprite-only node the bbox and description it draws.
- A sprite now survives prefab capture and instantiation, editor undo, and the
  web `set_node` action (which accepts a partial mapping or `null` to clear).
- `--describe` advertises `sprite_nodes` and `point_lights`, both engine
  schemas list `sprite`, and the scene export emits it, so an agent can find
  the features from the discovery payload.
- Static batch and instancing groups now key on `keystone.content` mesh and
  material digests instead of Python object identity, so two separately
  loaded copies of one asset share a group. Digest results are cached per
  immutable payload, and the asset registry uses the same digest stream.
- `CameraRig(camera)` syncs a scene root to the camera pose and `attach()`
  places ordinary nodes at camera-space offsets on the reserved `overlay`
  layer. The renderer draws that layer after a depth clear, so level
  geometry cannot occlude a viewmodel or reticle, and world culling, batch
  plans, merges and shadows skip it. The renderer reports `overlay_calls`,
  `overlay_triangles` and `overlay_nodes`, and `--describe` advertises
  `camera_rig` and `overlay_layer`.
- `AnimationClip.bind({"subject": "enemy-07"})` returns a copy of a clip
  retargeted onto other node ids, with an optional `name` so one authored
  motion can be registered per pooled slot. Unknown source ids are rejected
  with the ids the clip does animate, and `--describe` reports
  `capabilities.animation_binding`.
- HUD layout widgets `label_row`, `table`, `progress_bar` and `badge` measure
  text with the shared font metric and clamp every draw to the canvas, so a
  right-anchored row stays inside the frame at narrow viewports. The engine
  overlay truncates its own right panel at the same edge.
- `keystone.evidence` adds deterministic capture routes: `Route` runs a
  per-frame `stage` callback over an engine, `capture_route` writes one PNG
  and frame report per named checkpoint plus a route hash, and
  `diff_evidence` compares two runs per label. `--describe` reports
  `capabilities.evidence`.
- The README now keeps a condensed orientation tree and links to
  `docs/TREE.md`, which carries the full annotated module and test map. The
  split restores room under the README size limit for feature documentation.
- `keystone.pathfinding` adds immutable `NavGrid` and deterministic A*:
  `find_path()` searches 4 or 8 neighbours, refuses to cut wall corners,
  returns path/cost/expansion evidence, and `path_report()` emits a JSON-safe
  route summary. `--describe` reports `capabilities.pathfinding`.
- `keystone.navigation` adds `PathFollower`, `grid_path_points` and
  `navigation_report`: a follower turns a route into wish velocity for
  `CharacterController`, advances from the reported position (so collisions
  cannot make it skip waypoints), and reports JSON-safe progress.
  `--describe` reports `capabilities.navigation`.
- `keystone.audio_spatial` adds `SoundSource`, `distance_gain`, `spatial_mix`
  and `spatial_report`: linear distance attenuation inside a near/far range,
  deterministic mixdown through the existing buses, and JSON-safe per-source
  audibility. `--describe` reports `capabilities.spatial_audio`.
- `keystone.nav_authoring` derives a `NavGrid` from the same AABBs a character
  collides with (`scene_boxes` collects visible world meshes and skips the
  camera-relative overlay; `grid_from_boxes` inflates by a clearance radius
  on X/Z) and persists grids as schema-1 documents (`NavGrid.to_dict`/
  `from_dict`, `write_navgrid`, `read_navgrid`). `--describe` reports
  `capabilities.nav_authoring`.
- `line_of_sight()` and `smooth_path()` test grid segments cell by cell with
  the same corner rule as movement and greedily drop redundant waypoints, so
  a smoothed A* route stays legal while using fewer points. `--describe`
  reports `capabilities.path_smoothing`.
- `keystone.picking` adds `raycast_scene`, `SceneHit` and `hit_report`: a ray
  returns the nearest visible mesh node with world distance and contact
  point, skipping hidden, overlay, layer-filtered and ignored nodes.
  `--describe` reports `capabilities.scene_raycast`.
- `ray_aabb` and `ray_sphere` now return world-unit distances for non-unit
  ray directions; they normalized the direction and scaled the result again.
- `Canvas.line()` and `Canvas.frame()` add clipped pixel lines with a square
  brush and rectangular outlines, useful for minimaps, pointers and debug
  HUDs. `--describe` reports `capabilities.ui_shapes`.
- `Canvas.image()` adds textured HUD quads with UV subrects, tint, alpha
  and clipping; `UiRenderer` draws them with a cached clamp-to-edge texture
  pass after color primitives. `--describe` reports
  `capabilities.ui_images`.
- `Canvas.paragraph()` and `keystone.ui.font.wrap_text()` wrap HUD text at
  word boundaries, preserve explicit newlines and blank lines, truncate an
  overlong single word and return the height used. `--describe` reports
  `capabilities.ui_text_wrap`.
- `PostSettings.anti_alias` accepts `none` or `fxaa`: an opt-in
  full-screen FXAA pass renders through the color FBOs and blends luma
  edges, leaving uniform frames and the default path byte-identical.
  Snapshots, scene export (schema 5), editor `set_scene` (schema 62) and
  renderer stats (`post_aa`) carry it; `--describe` reports
  `capabilities.post_fxaa`.
- `PostSettings` gains `exposure` (default 1.12) and `vignette` (default
  0.28): the shaders read both, snapshots persist them, `set_scene` accepts
  `environment.exposure`/`vignette`, and renderer stats report them.
  Defaults preserve every existing frame; scene export schema is 4 and
  editor schema 61.
- `PostSettings` gains `tone` (`none`, `reinhard`, `aces`): the post grade
  optionally tonemaps linear colour before exposure/vignette, persists the
  choice in snapshots, exposes it through `set_scene` and scene export, and
  reports it in renderer stats. `--describe` reports
  `capabilities.post_tonemap`. Scene export schema is 3, editor schema 60.
- The editor gains `trace_navgrid`: it walks a fresh `NavAgent` from a
  start cell toward a goal under a frame budget and reports `found`,
  `reached`, `steps` and the final body state, so an AI can prove a level is
  walkable through the same JSON API.
- The editor gains `route_navgrid`: it runs A* on a schema-1 nav-grid
  document between two cells with optional diagonals and line-of-sight
  smoothing, returning the path report, the raw route and the smoothed
  route under `navgrid_route`.
- The editor gains `inspect_navgrid` and `bake_navgrid`: the first validates
  a schema-1 nav-grid document and reports counts, the second derives a grid
  from the scene's visible meshes with optional layer, origin, cell size and
  clearance and returns the document for persistence. The editor document
  exposes `navgrid` and `navgrid_bake`.
- The editor gains `inspect_tilemap` and `build_tilemap`: the first reports
  a tile-map document's counts and bounds, the second applies the merged
  mesh to a scene node through undo history, with schema examples and
  document fields. The editor document exposes `tilemap` and
  `tilemap_build`.
- `keystone.tilemap` adds an immutable `TileMap` with exact `AABB`
  colliders per solid cell, a merged floor-and-wall `MeshData` in one draw,
  `with_cell()` copies, schema-1 documents and a JSON-safe
  `tilemap_report()`. `--describe` reports `capabilities.tilemap`.
- `keystone.nav_agent` adds `NavAgent` and `nav_agent_report`: one object
  composes A*, smoothing, waypoint following, separation steering and
  `CharacterController`; `set_goal` plans once, `replan` re-runs, and `step`
  moves the body against colliders with optional neighbour avoidance while
  returning JSON-safe progress. `--describe` reports `capabilities.nav_agent`.
- `keystone.steering` adds deterministic `Agent`, `seek`, `arrive`,
  `separation`, `steer` and `steering_report`: pure wish-velocity shaping
  with quadratic contact repulsion and a max-speed clamp, no time step or
  hidden state. `--describe` reports `capabilities.steering`.
- The editor gains `preview_blend_space2d`: it samples a 2D blend space at
  `x`, `y` and `time`, applies the pose through undo history (or
  `record: false`), and reports the axes and parameters. `--describe`
  reports `capabilities.animation_preview_blend_2d`.
- Animation states can drive a `BlendSpace2D`: a state takes
  `blend_space2d` plus two parameter names, samples the bilinear grid from
  live machine parameters, round-trips through `.kstate` documents and
  reports axes and parameters. A state may use one space kind only.
  `--describe` reports `capabilities.animation_state_blend_2d`.
- The itemised feature list moved from the README into
  `docs/FEATURES.md`; the README keeps a one-paragraph summary and a link,
  restoring room under its size gate for future feature notes.
- `RootMotionPresenter` places a container node at a `RootMotionBody`'s
  position and yaw (keeping scale) and applies the in-place pose to its
  children, keeping movement, collision and presentation in sync.
  `--describe` reports `capabilities.root_motion_presenter`.
- `RootMotionBody` drives a `CharacterController` body from a root-motion
  clip: each step converts horizontal motion into wish velocity, accumulates
  the turn, moves against colliders and returns an in-place pose plus the
  consumed delta. `--describe` reports `capabilities.root_motion_body`.
- `RootMotionPlayer` advances one clip and returns its pose plus the root
  delta consumed, composing loop wraps and full cycles, clamping non-loop
  playback and reporting clip, node, time, looped and done.
  `--describe` reports `capabilities.root_motion_player`.
- `keystone.root_motion` adds `RootMotion`, `extract_root_motion`,
  `in_place_pose` and `root_motion_report`: a clip's root delta between two
  times (planar or full), its yaw, and a copy of a pose with the root reset
  to a reference transform. `--describe` reports `capabilities.root_motion`.
- `keystone.rng` adds deterministic SplitMix64 `RandomStream` and
  `RandomStreamState`: uniform/random/randint/choice/shuffled, labelled
  forks and snapshot/restore, with the published reference vector pinned by
  tests. `--describe` reports `capabilities.deterministic_random`.
- `BlendSpace2D` and `BlendSample2D` add bilinear two-parameter blend
  spaces over complete rectangular grids, with canonical sample order,
  schema-1 documents, strict validation and JSON-safe reports.
  `--describe` reports `capabilities.animation_blend_2d`.
- `overlap_scene()` and `overlap_report()` add sphere and AABB area queries
  over visible mesh bounds, sorted by distance then node id with the picking
  filters. `--describe` reports `capabilities.scene_overlap`.
