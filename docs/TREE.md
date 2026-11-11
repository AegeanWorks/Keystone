# Repository Layout

The full annotated tree for Keystone: every source module, test file and top-level
document with a one-line note. The README keeps a condensed tree for orientation;
this page is the detailed map used when locating a module.

```text
keystone/
├── keystone/
│   ├── __init__.py           <- public API and version
│   ├── _version.py           <- single-source release version
│   ├── __main__.py           <- CLI: --game, headless frames, PNG
│   ├── agents.py             <- AI adapters and audit trail
│   ├── animation.py          <- clips, controller and pose reports
│   ├── animation_blend.py    <- blend spaces
│   ├── animation_state.py    <- parameter-driven state machine transitions
│   ├── animation_library.py  <- file-backed .kanim clip library
│   ├── state_machine_library.py <- file-backed .kstate machine library
│   ├── app.py                <- Engine loop
│   ├── audio.py              <- synth clips, mixer and WAV I/O
│   ├── audio_spatial.py      <- distance attenuation and spatial mixdown
│   ├── batch.py              <- static batch planning, world-space and rig merge
│   ├── clock.py              <- fixed-step clock
│   ├── camera_rig.py          <- camera-following overlay rig for viewmodels and HUD anchors
│   ├── content.py             <- content digests for batching, instancing and assets
│   ├── evidence.py            <- deterministic capture routes and checkpoint evidence diffs
│   ├── culling.py            <- frustum culling
│   ├── input.py              <- ActionState and InputMap
│   ├── lifecycle.py          <- deterministic component start/update/stop
│   ├── plugin.py             <- GameModule protocol and loader
│   ├── playtest.py           <- seeded bot policies and fairness
│   ├── replay.py             <- command log and stable hash
│   ├── history.py            <- bounded undo/redo snapshots
│   ├── scene_snapshot.py     <- versioned scene save/load
│   ├── scene_library.py      <- file-backed scene library
│   ├── scene_diff.py         <- structured saved-scene diffs
│   ├── serialization.py      <- atomic JSON persistence
│   ├── headless.py           <- no-GL simulation and action scripts
│   ├── analysis.py           <- frame stats, projection and report diff
│   ├── testing.py            <- deterministic scenario helpers
│   ├── physics.py            <- rays, AABB, sphere queries, pushout and raycasts
│   ├── particles.py          <- deterministic CPU emitters and systems
│   ├── picking.py            <- scene ray queries and hit reports
│   ├── broadphase.py         <- deterministic spatial-grid broadphase
│   ├── pathfinding.py        <- deterministic A* over a bounded nav grid
│   ├── navigation.py         <- waypoint following and grid-to-world route points
│   ├── nav_authoring.py      <- scene/box-derived nav grids and schema-1 documents
│   ├── character.py          <- AABB movement and ground detection
│   ├── triggers.py           <- trigger volumes and tracking
│   ├── assets.py             <- mesh, material and texture asset registry
│   ├── asset_io.py           <- file-backed sources, loaders and hot reload
│   ├── component_codec.py    <- shared JSON codec for typed components
│   ├── gltf_import.py        <- glTF/GLB scene to prefab import
│   ├── schema.py             <- versioned core schema constants
│   ├── math3d.py             <- Vec3, Mat4, Quat (column-major, OpenGL-ready)
│   ├── camera.py             <- perspective camera
│   ├── project.py           <- manifests, scaffolding and --project loading
│   ├── export.py            <- deterministic runnable project bundles
│   ├── prefab.py            <- deterministic subtree templates
│   ├── prefab_library.py    <- file-backed prefab library
│   ├── library_trash.py      <- recoverable library deletes
│   ├── scene.py              <- hierarchy, identity, components, transforms and lights
│   ├── geometry.py           <- MeshData, Material
│   ├── skin.py               <- bone palettes, CPU skinning
│   ├── mesh_builder.py       <- merge boxes, quads, meshes, skinned rigs
│   ├── material_graph.py     <- node graphs evaluating to Material
│   ├── material_library.py   <- file-backed .kmaterial library
│   ├── primitives.py         <- cube, plane, cone, cylinder and sphere
│   ├── obj_loader.py         <- Wavefront OBJ loader
│   ├── png.py                <- dependency-free PNG writer and reader
│   ├── texture.py            <- immutable RGBA textures, PNG and checker sources
│   ├── samples.py            <- CubeDemo smoke test
│   ├── gltf/
│   │   ├── __init__.py       <- glTF package exports
│   │   ├── io.py             <- source, buffer and accessor decoding
│   │   ├── textures.py       <- image and texture decoding
│   │   ├── materials.py      <- PBR to Material conversion
│   │   ├── meshes.py         <- primitive, mesh, skin decoding
│   │   ├── skins.py          <- joints and inverse binds
│   │   ├── scene.py          <- node, skin and scene construction
│   │   └── loader.py         <- top-level import orchestration
│   ├── ui/
│   │   ├── __init__.py       <- UI package exports
│   │   ├── font.py           <- embedded 5x7 bitmap font
│   │   ├── canvas.py         <- clipped screen-space quads and text
│   │   ├── widgets.py        <- panels and menu buttons
│   │   ├── menu.py           <- pure pause-menu selection state
│   │   ├── report.py         <- UI labels/buttons for AI reports
│   │   └── overlay.py        <- HUD, controls help and pause menu
│   ├── web/
│   │   ├── __init__.py       <- web package exports
│   │   ├── editor.py         <- hierarchy, transform and prefab edits
│   │   ├── schema.py         <- web API and scene document schemas
│   │   ├── scene.py          <- scene-to-JSON export for the viewer
│   │   ├── server.py         <- stdlib JSON API and static server
│   │   └── static/
│   │       ├── index.html    <- console shell
│   │       ├── app.js        <- console controls and API client
│   │       ├── viewer.js     <- WebGL2 scene renderer
│   │       └── style.css     <- console layout and tokens
│   └── gpu/
│       ├── __init__.py       <- GPU adapter package marker
│       ├── context.py        <- GLFW window and OpenGL 3.3 context
│       ├── shader.py         <- GLSL compilation and uniforms
│       ├── mesh_buffer.py    <- VAO/VBO/EBO upload and drawing
│       ├── skinned_buffer.py <- skinned mesh upload
│       ├── sprites.py        <- deterministic sprite math
│       ├── instancing.py     <- deterministic instancing groups
│       ├── shadow.py         <- shadow map
│       ├── post.py           <- post grade math
│       ├── bloom.py          <- bloom glow
│       ├── bloom_fbo.py      <- bloom diffusion FBO
│       ├── texture_buffer.py <- 2D texture upload, mipmaps and cleanup
│       ├── ui_renderer.py    <- screen-space alpha-blended UI draw
│       └── renderer.py       <- forward renderer, sky, lights, shadows, post, bloom, sprites
├── assets/
│   ├── octahedron.obj        <- generic sample OBJ
│   ├── engine.png            <- sample frame
│   ├── engine.json           <- sample frame report
│   ├── logo.svg              <- project logo
│   ├── social-preview.svg    <- social preview
│   └── screenshots/          <- approved HUD + console keepers
├── docs/
│   ├── ARCHITECTURE.md       <- core layers and contract
│   ├── AI_GUIDE.md           <- discover, simulate and verify
│   ├── IMPLICIT_STATE_AUDIT.md <- state-machine audit
│   └── TREE.md               <- this full repository tree
├── tests/
│   ├── test_math3d.py        <- math core
│   ├── test_scene.py         <- hierarchy, camera and lights
│   ├── test_geometry.py      <- meshes, primitives, builder and OBJ
│   ├── test_png.py           <- PNG writer and reader
│   ├── test_texture.py       <- texture data, checker and PNG loading
│   ├── test_ui.py            <- font, canvas, menu and overlay
│   ├── test_ui_widgets.py     <- HUD layout widgets and viewport safety
│   ├── test_ui_text.py        <- word wrapping and paragraph layout
│   ├── test_renderer.py      <- headless OpenGL integration
│   ├── test_input.py         <- action mapping and ActionState
│   ├── test_input_keys.py    <- GL key table and dead bindings
│   ├── test_lifecycle.py     <- component start/update/stop lifecycle
│   ├── test_clock.py         <- fixed-step clock
│   ├── test_physics.py       <- rays, AABB, sphere queries and raycasts
│   ├── test_picking.py       <- scene ray hits, filters and reports
│   ├── test_overlap.py        <- scene sphere/box overlap queries
│   ├── test_pathfinding.py   <- nav grids, A* routes and path reports
│   ├── test_path_smoothing.py <- line of sight and waypoint reduction
│   ├── test_navigation.py    <- waypoint followers and route integration
│   ├── test_nav_authoring.py <- nav documents and box rasterization
│   ├── test_scene_boxes.py   <- scene collision boxes and route integration
│   ├── test_broadphase.py    <- spatial-grid queries, updates and pairs
│   ├── test_project.py      <- manifest, scaffold and --project workflow
│   ├── test_export.py       <- export bundle structure, hashes and launcher
│   ├── test_prefab.py       <- prefab capture, IDs and isolation
│   ├── test_prefab_library.py <- prefab library save, load and errors
│   ├── test_particles.py     <- seeded emitters, forces and reports
│   ├── test_pbr.py           <- metallic/roughness/emissive shading
│   ├── test_character.py     <- floor, wall, jump and validation behavior
│   ├── test_triggers.py      <- enter/exit tracking and multiple volumes
│   ├── test_agents.py        <- AI adapters, validation and audit trail
│   ├── test_animation.py     <- clips, blending and timed events
│   ├── test_animation_binding.py <- clip retargeting onto pooled node ids
│   ├── test_animation_blend.py <- blend spaces
│   ├── test_animation_blend2d.py <- bilinear 2D blend grids
│   ├── test_animation_state.py <- state transitions, triggers and round trips
│   ├── test_animation_library.py <- clip library save, load, delete and restore
│   ├── test_state_machine_library.py <- .kstate library save/delete/restore
│   ├── test_material_library.py <- material library save, load, register and textures
│   ├── test_skinning.py      <- skin math, GPU path, glTF
│   ├── test_sprites.py       <- sprite math, report, sample fixture
│   ├── test_sprite_nodes.py  <- placed sprite nodes and billboards
│   ├── test_merge_skin.py    <- skin-aware merge
│   ├── test_assets.py          <- registry ids, digests, dependencies and reload
│   ├── test_audio.py         <- synth, mixer buses and WAV I/O
│   ├── audio_spatial.py      <- distance attenuation and spatial mixdown
│   ├── test_audio_spatial.py <- distance gain, spatial mixes and reports
│   ├── test_batch.py         <- batch planning and world-space merge
│   ├── test_camera_rig.py     <- camera-space parts and rig sync
│   ├── test_content.py        <- mesh and material digest cache
│   ├── test_evidence.py       <- capture routes, reruns and evidence diffs
│   ├── test_feature_composition.py <- rig routes and overlay instancing seams
│   ├── test_overlay.py        <- overlay pass, depth clear and metric split
│   ├── test_material_graph.py <- declarative material graph evaluation
│   ├── test_gltf.py           <- glTF/GLB import and texture loading
│   ├── test_gltf_import.py    <- glTF/GLB prefab import coverage
│   ├── test_history.py        <- bounded undo/redo history
│   ├── test_instancing.py     <- hardware-instancing groups and draws
│   ├── test_shadows.py        <- shadow map
│   ├── test_srgb.py           <- sRGB pipeline
│   ├── test_post.py           <- post color-grade
│   ├── test_bloom.py          <- bloom
│   ├── test_culling.py        <- frustum culling
│   ├── test_scene_snapshot.py <- versioned scene save/load
│   ├── test_round_trip_stability.py <- idempotent save/load
│   ├── test_scene_library.py <- scene library save, load and restore
│   ├── test_scene_diff.py   <- structured scene diff coverage
│   ├── test_plugin.py        <- GameModule contract and loader
│   ├── test_replay.py        <- command log and hashes
│   ├── test_serialization.py <- atomic JSON persistence
│   ├── test_component_codec.py <- typed component JSON codec
│   ├── test_library_trash.py <- recoverable library deletes
│   ├── test_version.py       <- version single-source drift guard
│   ├── test_headless.py      <- no-GL simulation and action scripts
│   ├── test_analysis.py      <- frame stats, projection, report diff
│   ├── test_projected_bbox.py <- near-plane silhouette clipping
│   ├── test_testing.py       <- deterministic helpers
│   ├── test_samples.py       <- CubeDemo smoke test
│   ├── test_boundary.py      <- no game modules/imports
│   ├── test_cli_failure_advice.py <- post-start errors name the step
│   ├── test_web.py           <- scene export, JSON API, assets
│   ├── test_app.py           <- engine loop, CLI, simulate and reports
│   ├── test_playtest.py      <- seeded bots and fairness
│   ├── test_swarm_fixes.py   <- swarm pins
│   ├── support_maze_game.py  <- deterministic grid fixture
│   └── support_policy.py     <- external policy fixture
├── requirements.txt          <- pinned runtime and test dependencies
├── pyproject.toml            <- package metadata, pytest and ruff configuration
├── .gitignore                <- transient AIKit state excluded
├── LICENSE                   <- Aegean License 1.1 (AL-1.1): free personal use
├── COMMERCIAL.md             <- Commercial licensing terms
├── LICENSES/                 <- REUSE license texts
├── REUSE.toml                <- Machine-readable SPDX metadata
├── CHANGELOG.md              <- release history
├── README.md
└── .aikit/                   <- this project's memory: record, ledger, decisions
```
