# Features

Every implemented area of Keystone, with the notes that used to live in the
README. The README keeps a one-paragraph summary and links here.

- **OpenGL 3.3 renderer**: GLSL 330, PBR, shadows, sRGB, post grade with configurable exposure/vignette, optional Reinhard/ACES tonemapping and FXAA, bloom, placed sprite billboards, up to 8 point lights, and profiler stats.
- **Camera**: perspective camera and view matrices, first-person controls, viewmodel rigs, deterministic trauma-based shake with a composing shaker, pose blending with slerped heading and lerped position and lens, and timed camera paths with spline positions, slerped orientation, lens keys, closed loops, one-shot or looping playback, schema-1 documents and a `.kpath` library with recoverable deletes.
- **Scene graph**: stable IDs, tags, layers, typed components, world transforms, queries, merged tile-map meshes with exact per-cell colliders, and cached GPU meshes.
- **Prefabs**: capture, versioned `.kprefab` persistence, deterministic instantiation and override-preserving refresh.
- **Persistence**: `VersionedStore` with schema migrations, quarantine of corrupt documents, `.bak` fallback, a fresh default factory and an advisory lock with stale-lock reclamation.
- **Assets**: `MeshData`, primitives, streaming OBJ, PNG/checker `TextureData`, and an id/digest registry with hot reload plus core scene rebinding.
- **PBR materials**: specular/shininess plus metallic/roughness/emissive, wrapped/mipmapped textures and material graphs.
- **Runtime**: fixed-step clock with bounded catch-up; headless one-step-per-frame determinism.
- **Input**: rebindable `InputMap` across contexts, a game `bind_input` hook, and dead-binding diagnostics.
- **Audio**: synth, named-bus mixer, deterministic mixdown, WAV I/O, distance-attenuated spatial mixes and reports; no hardware output.
- **Animation**: tracks/clips, looping, crossfades, events, 1D and bilinear 2D blend spaces, state machines that drive either space, masked `apply_pose`, clip binding onto pooled nodes, root-motion extraction, a looping player, a controller-driven root-motion body and a scene presenter, CPU/GPU skinning and state machines.
- **Particles and physics**: seeded emitters with swept collision; rays, AABB/sphere queries, broadphase, scene picking, character movement and triggers.
- **Pathfinding**: immutable nav grids, deterministic A* over 4 or 8 neighbours with corner-cut refusal, line-of-sight path smoothing, JSON-safe path reports, scene/box-derived nav grids with schema-1 documents, a waypoint follower, seek/arrive/separation steering, and a composed nav agent that walks a route with collision and avoidance.
- **Replay and determinism**: command logs, stable hashes, `run_log`/`verify_log`, atomic JSON with `.bak`, and SplitMix64 random streams with labelled forks and snapshot/restore.
- **Testing and AI**: `--describe`, `--simulate`, `--verify-determinism`, `--expect-hash`, frame reports, pixel diffs, seeded playtests, deterministic capture routes with checkpoint evidence diffs, camera-path capture routes, and adapters.
- **Human UI and web**: overlay/pause menu, `draw_ui`, measured-text layout widgets (`label_row`, `table`, `progress_bar`, `badge`), textured HUD images, stdlib JSON API and WebGL2 console/editor.
- **Game-agnostic core**: no combat, light-lock, weave or expedition code.

