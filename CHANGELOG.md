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
- `AssetRegistry.reload(scene)` refreshes sources and rebinds live scene
  nodes, registered materials and inline textures, reporting `rebound` and
  `registry_rebound`. The web editor now calls the same core rule.
- `python -m keystone --version` prints the release version; the version is
  single-sourced through `keystone/_version.py`.
- `--frames` rejects 0 instead of silently running 1 or 120 frames.
- Component documents reject unknown keys and unknown dataclass fields.
