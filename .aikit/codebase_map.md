# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document catalogues Python modules, classes, and exported functions. See Map Coverage for any stack it does not index.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `157`
- **Total Classes**: `255`
- **Total Top-Level Functions**: `455`
- **Total Class Methods**: `1657`
- **Total Source Lines**: `44248`

## 🧭 Map Coverage
- **Indexed**: python (`157` module(s))
- **Not indexed by this map**: javascript (`2` file(s))

> Only Python symbols are catalogued. A language above is reported as not indexed, never as verified by this map.

---

## 📦 Modules & Exported Symbols

### [`keystone/__init__.py`](keystone/__init__.py)
> *Keystone: a game-agnostic 3D engine core.*

**Size**: `185` lines (`4133` bytes)

**Functions:**
- `def __getattr__(name)`

---

### [`keystone/__main__.py`](keystone/__main__.py)
> *Command-line entry point for the game-agnostic Keystone engine.*

**Size**: `747` lines (`39601` bytes)

**Functions:**
- `def _size(text)`
- `def _frames(text)`
- `def _hash(text)`
- `def _port(text)`
- `def _seed(text)`
- `def main(argv)`
- `def _start_failure_hint(args)` - *Name the fix for a failure that happened while loading the game.*
- `def _read_comparison_report(path, role)` - *Read one side of a baseline comparison with actionable guidance.*
- `def _run_failure_hint(args)` - *Name the fix for a failure that happened after the game loaded.*

---

### [`keystone/_version.py`](keystone/_version.py)
> *The single source of truth for the engine version.*

**Size**: `10` lines (`324` bytes)

---

### [`keystone/agents.py`](keystone/agents.py)
> *AI observation/action adapters: seen, used, audited, verified and analyzed by AI.*

**Size**: `177` lines (`7599` bytes)

**Classes:**
- `class AuditTrail` - *Append-only, hash-chained audit log for AI-driven runs.*
  - Method `.__post_init__()`
  - Method `.record(kind, payload)`
  - Method `.verify()`

**Functions:**
- `def parse_actions(payload)` - *Validate LLM-produced JSON into a list of ActionState.*
- `def observe(game, frames, actions, step)` - *Build one auditable AI observation: discovery + deterministic simulation.*
- `def summarize_report(report, max_nodes)` - *Compress a schema-4/5 frame report into an LLM-sized observation summary.*

---

### [`keystone/analysis.py`](keystone/analysis.py)
> *Machine-readable frame reports for AI and headless UI analysis.*

**Size**: `666` lines (`27384` bytes)

**Functions:**
- `def _enabled(value)`
- `def _rows(pixels, width, height, flip)`
- `def _stats(pixels, width, height, background, flip)`
- `def _material_report(material)`
- `def _node_report(scene, width, height)`
- `def _clip_point(view_projection, point)` - *Return homogeneous clip coordinates ``(x, y, z, w)`` for one world point.*
- `def _to_screen(clip, width, height)` - *Map clip coordinates to top-down image pixels, clamped to the frame.*
- `def _edges_for(count)` - *Return the edges joining ``count`` corners in their given order.*
- `def _near_distance(clip)` - *Return how far a clip point sits in front of the near plane.*
- `def _projected_bbox(corners, view_projection, width, height)` - *Return the on-screen box of a world AABB's silhouette, or None.*
- `def analyze_frame(scene, pixels, width, height, image_path, ui, fx)`
- `def _compare_ui(before, after)`
- `def _shadows_of(report)`
- `def _color_of(report)`
- `def _post_of(report)`
- `def _bloom_of(report)`
- `def _sprites_of(report)`
- `def _culling_of(report)`
- `def _fx_of(report)`
- `def compare_reports(before, after)` - *Compare schema-1/2/3/4/5/6/7/8/9/10/11 frame reports for AI-driven regression checks.*
- `def diff_images(before, after, output, threshold)` - *Write a visual diff PNG and return changed-pixel statistics.*
- `def write_report(path, report)`

---

### [`keystone/animation.py`](keystone/animation.py)
> *Deterministic, game-agnostic animation: keyframe clips, sampling and control.*

**Size**: `531` lines (`23468` bytes)

**Classes:**
- `class Track` - *One keyframed channel: sorted times with Vec3 or Quat values.*
  - Method `.__post_init__()`
  - Method `.duration()`
  - Method `.sample(time)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AnimationClip` - *A named set of per-node tracks sharing one duration.*
  - Method `.__post_init__()`
  - Method `.duration()`
  - Method `.node_ids()`
  - Method `.sample(time)`
  - Method `.events_in_range(start, end)` - *Return event names with start < time <= end (loop callers split wraps).*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AnimationController` - *Deterministic playback: advance time, loop, blend and write Transforms.*
  - Method `.set_pose_provider(pose, wrap_duration)` - *Let a caller-supplied sampler own the pose and the loop length.*
  - Method `._pose_at(moment, clip)`
  - Method `.__post_init__()`
  - Method `.add(clip)`
  - Method `.play(name, restart)`
  - Method `.crossfade(name, duration)` - *Blend from the current sampled pose into another clip over duration.*
  - Method `._moment()`
  - Method `.advance(dt)`
  - Method `.advance_with_events(dt)`

**Functions:**
- `def _check_times(times)`
- `def blend_poses(first, second, factor)` - *Blend two sampled poses; factor 0 returns first, 1 returns second.*
- `def apply_pose(scene, pose, mask)` - *Write sampled Transforms onto nodes by id or name; return updated ids.*
- `def _pose_channels(mask)` - *Normalize a channel mask, rejecting names that are not pose channels.*
- `def animation_report(controller)`

---

### [`keystone/animation_blend.py`](keystone/animation_blend.py)
> *Deterministic one-dimensional animation blend spaces.*

**Size**: `154` lines (`5598` bytes)

**Classes:**
- `class BlendSample` - *One clip anchored at a scalar threshold.*
  - Method `.__post_init__()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class BlendSpace1D` - *Ordered clips blended by one finite scalar parameter.*
  - Method `.__post_init__()`
  - Property `.thresholds`
  - Property `.duration`
  - Method `.sample(parameter, time)` - *Return a blended pose for one scalar parameter and clip time.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
  - Method `.report()` - *Return a JSON-safe summary for AI clients and diagnostics.*

**Functions:**
- `def _finite(label, value)`
- `def _schema(data)`

---

### [`keystone/animation_library.py`](keystone/animation_library.py)
> *File-backed animation clip libraries for editors, tools and AI clients.*

**Size**: `132` lines (`4952` bytes)

**Classes:**
- `class AnimationEntry` - *One library file and its clip summary, or why it could not load.*
  - Method `.describe()` - *Return a JSON-safe entry for editor and AI documents.*
- `class AnimationLibrary` - *Discover, save and load ``.kanim`` clips in one directory.*
  - Method `.__init__(directory)`
  - Method `.path_for(name)` - *Return the safe file path for one library name.*
  - Method `.save(name, clip)` - *Write one clip atomically; its internal name must match the entry.*
  - Method `.load(name)` - *Load one clip or raise KeyError when the entry is absent.*
  - Method `.delete(name)` - *Move one entry to the library trash and return its former path.*
  - Method `.trash()` - *Return recoverable deleted entries.*
  - Method `.restore(trash_name)` - *Restore one trashed entry and return its summary.*
  - Method `.entry(name)` - *Load one entry's summary, capturing load failures as ``error``.*
  - Method `.entries()` - *Return every ``.kanim`` file in stable name order.*

---

### [`keystone/animation_state.py`](keystone/animation_state.py)
> *Deterministic parameter-driven animation state machines.*

**Size**: `396` lines (`14776` bytes)

**Classes:**
- `class AnimationState` - *One named clip or 1D blend space with loop and speed settings.*
  - Method `.__post_init__()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AnimationTransition` - *One parameter condition that moves between states.*
  - Method `.__post_init__()`
  - Method `.matches(parameters)` - *Return whether the parameter condition currently passes.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AnimationStateMachine` - *One deterministic controller driven by named states and transitions.*
  - Method `.__init__(states, transitions, parameters, current)`
  - Method `._state(name)`
  - Method `._sync_pose_provider()` - *Give the controller the active blend-space sampler, or clear it.*
  - Method `.play(name, restart)`
  - Method `.set_parameter(name, value)`
  - Method `.set_trigger(name)`
  - Method `.available_transitions()`
  - Method `.advance(dt)`
  - Method `.take_events()`
  - Method `.report()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`

**Functions:**
- `def _name(label, value)`
- `def _finite(label, value, *, minimum)`
- `def _parameter_value(label, value)`

---

### [`keystone/app.py`](keystone/app.py)
> *Game-agnostic engine runtime: window, fixed step, input, render and capture.*

**Size**: `356` lines (`14308` bytes)

**Classes:**
- `class Engine` - *Owns the runtime around one external GameModule.*
  - Method `.__init__(game, width, height, visible, msaa, title, ui, scene)`
  - Method `._apply_game_bindings()` - *Let the game extend the default bindings through an optional hook.*
  - Method `.__enter__()`
  - Method `.__exit__(*exc_info)`
  - Method `._set_capture(captured)`
  - Method `._handle_system_actions(actions)`
  - Method `.toggle_pause()` - *Pause or resume gameplay; release the cursor while the menu is open.*
  - Method `.apply_ui_action(action)` - *Run a named UI action; returns False when the action is unknown.*
  - Method `._game_particles()`
  - Method `._draw_ui()`
  - Method `.run(max_frames)` - *Run until the window closes or max_frames (0 = unlimited) is reached.*
  - Method `.capture(image_path, report_path)`
  - Method `.screenshot(path)`
  - Method `.close()`

---

### [`keystone/asset_io.py`](keystone/asset_io.py)
> *Disk-backed asset sources, default loaders and hot-reload reporting.*

**Size**: `184` lines (`6438` bytes)

**Classes:**
- `class AssetSource` - *One file-backed asset: where it came from, how to load it and its last stamp.*
  - Method `.__post_init__()`
- `class ReloadReport` - *Outcome of one synchronous registry refresh.*
  - Property `.ok` - *True when every checked source loaded and none disappeared.*
  - Method `.describe()` - *Return a JSON-safe report for logs and AI clients.*

**Functions:**
- `def default_loader(kind)` - *Return the built-in loader for a kind, or explain how to supply one.*
- `def rebind_payload(payload, replacements)` - *Return a reloaded payload (or a material with a reloaded texture).*
- `def rebind_node_assets(node, replacements)` - *Point one node's mesh and material at reloaded payloads; return changes.*
- `def rebind_prefab_assets(prefab, replacements)` - *Swap reloaded payloads inside one cached prefab template.*
- `def kind_from_suffix(path)` - *Infer an asset kind from a .obj, .png or .kprefab path.*
- `def fingerprint(path)` - *Return (mtime_ns, size) for a readable path, or None when it is absent.*
- `def asset_kind(payload)` - *Return the registry kind of a payload object.*
- `def load_asset(kind, path, loader)` - *Load one source and prove the payload matches the declared kind.*

---

### [`keystone/assets.py`](keystone/assets.py)
> *Game-agnostic asset registry with stable ids, content hashes and dependencies.*

**Size**: `496` lines (`19308` bytes)

**Classes:**
- `class AssetRecord` - *One registered asset: a stable id, kind, immutable payload and content digest.*
  - Method `.__post_init__()`
  - Method `.describe()` - *Return a JSON-safe description for AI clients and diagnostics.*
- `class AssetRegistry` - *Caller-owned registry for meshes, materials, textures and prefabs.*
  - Method `.__init__()`
  - Method `.__len__()`
  - Method `.__contains__(asset_id)`
  - Method `.__iter__()`
  - Method `.register(asset_id, payload, *, kind, source, dependencies, replace)` - *Register one asset, inferring its kind from the payload when omitted.*
  - Method `.register_file(asset_id, path, *, kind, loader, dependencies, component_types, replace)` - *Load a .obj, .png or .kprefab file and bind it for hot reload.*
  - Method `._refresh_order()` - *Order sources so dependencies and new leaf edges reload first.*
  - Method `.refresh()` - *Re-read every changed source and report reloaded, unchanged, failed and missing ids.*
  - Method `.reload(scene)` - *Refresh every source and rebind live scene nodes to new payloads.*
  - Method `._rebind_registry_materials(replacements)` - *Keep registered materials pointing at their reloaded textures.*
  - Method `.get(asset_id)` - *Return one record, or None when the id is not registered.*
  - Method `.require(asset_id)` - *Return one record or raise a KeyError naming the missing asset.*
  - Method `.remove(asset_id)` - *Remove one record or raise a KeyError naming the missing asset.*
  - Method `.clear()`
  - Method `.ids(kind)` - *Return registered ids in insertion order, optionally filtered by kind.*
  - Method `.find_by_digest(sha256)` - *Return every record whose content digest matches, in insertion order.*
  - Method `.duplicates()` - *Return groups of ids that share one kind and content digest.*
  - Method `.missing_dependencies()` - *Return every (asset id, dependency id) pair whose dependency is absent.*
  - Method `.stats()` - *Return total and per-kind counts in a stable order.*
  - Method `.describe()` - *Return a JSON-safe registry document sorted by asset id.*

**Functions:**
- `def _validate_id(asset_id)`
- `def _validate_kind(kind)`
- `def _validate_dependency(asset_id, dependency)`
- `def _dependencies(asset_id, dependencies)`
- `def _digest(kind, payload, registry)`
- `def _digest_prefab(prefab, registry)`
- `def _digest_mesh(mesh)`
- `def _digest_material(material)`

---

### [`keystone/audio.py`](keystone/audio.py)
> *Game-agnostic audio core: synth clips, bus mixer and WAV I/O.*

**Size**: `288` lines (`12484` bytes)

**Classes:**
- `class AudioClip` - *Immutable mono PCM clip in [-1, 1] with a fixed sample rate.*
  - Method `.__post_init__()`
  - Method `.duration()`
  - Method `.with_gain(gain)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class Mixer` - *Named-bus mixer: voices route through per-bus gains into one deterministic mix.*
  - Method `.__post_init__()`
  - Method `.set_bus(bus, gain)`
  - Method `.play(clip, bus, gain, pitch)`
  - Method `.clear()`
  - Method `.voice_count()`
  - Method `.render()`

**Functions:**
- `def _finite(value, label)`
- `def sine(frequency, duration, sample_rate, name)`
- `def square(frequency, duration, sample_rate, name)`
- `def noise(duration, seed, sample_rate, name)`
- `def mix_clips(clips)` - *Mix (clip, gain, pitch) voices deterministically; pitch resamples by index scaling.*
- `def _wav_write(clip)`
- `def write_wav(path, clip)`
- `def read_wav(path)`
- `def audio_report(clip, voices, buses)`

---

### [`keystone/batch.py`](keystone/batch.py)
> *Static batch planner: group draw nodes to cut draw calls without new deps.*

**Size**: `162` lines (`7047` bytes)

**Functions:**
- `def _skinned(mesh)` - *Whether a mesh deforms at render time and must never bake or merge.*
- `def plan_batches(scene)`
- `def merge_batches(scene, exclude)` - *Bake static groups into world-space meshes; animated ids stay separate.*

---

### [`keystone/broadphase.py`](keystone/broadphase.py)
> *Deterministic spatial-grid broadphase for nearby AABB candidates.*

**Size**: `143` lines (`5721` bytes)

**Classes:**
- `class SpatialGrid` - *A uniform grid of AABB proxies with exact overlap filtering.*
  - Method `.__init__(cell_size)`
  - Method `.__len__()`
  - Method `.__contains__(key)`
  - Method `.get(key)`
  - Method `.insert(key, box)` - *Insert or replace a proxy and its current bounds.*
  - Method `.update(key, box)` - *Move a proxy; unknown keys are inserted.*
  - Method `.remove(key)` - *Remove a proxy; return whether it existed.*
  - Method `.clear()`
  - Method `.query(box)` - *Return proxies whose bounds overlap ``box`` in insertion order.*
  - Method `.query_point(point)`
  - Method `.pairs()` - *Return every exact overlapping proxy pair, once, in insertion order.*
  - Method `._cells_for(box)`
  - Method `._candidates(box)`

---

### [`keystone/camera.py`](keystone/camera.py)
> *Perspective camera with yaw/pitch orientation and fly-style movement.*

**Size**: `80` lines (`2815` bytes)

**Classes:**
- `class PerspectiveCamera` - *A right-handed camera looking down -Z when yaw and pitch are zero.*
  - Method `.__post_init__()`
  - Method `.forward()`
  - Method `.right()`
  - Method `.up()` - *The camera-local up vector, perpendicular to forward and right.*
  - Method `.basis()` - *Return ``(forward, right, up)`` as one right-handed camera frame.*
  - Method `.view_matrix()`
  - Method `.projection_matrix(aspect)`
  - Method `.view_projection(aspect)`
  - Method `.move(forward, right, up)`
  - Method `.rotate(yaw_delta, pitch_delta)`
  - Method `.look_at(target)`

---

### [`keystone/character.py`](keystone/character.py)
> *Game-agnostic AABB character movement with gravity and collision response.*

**Size**: `216` lines (`8500` bytes)

**Classes:**
- `class CharacterBody` - *An axis-aligned character body with velocity and ground state.*
  - Method `.__post_init__()`
  - Method `.box()`
- `class CharacterController` - *Resolve horizontal wish velocity and gravity against static AABBs.*
  - Method `.__post_init__()`
  - Method `.step(body, wish_velocity, dt, colliders, platform_velocity)` - *Advance one step; horizontal speed is the wish velocity, vertical is body velocity.*
  - Method `._try_step_up(position, half, amount_x, amount_z, colliders)`
  - Method `._move_axis(position, half, axis, amount, colliders)`

**Functions:**
- `def _finite_vec3(value, label)`
- `def _finite(value, label)`
- `def _component(vector, axis)`
- `def _with_axis(vector, axis, value)`
- `def _other_axes_overlap(position, half, box, axis)`

---

### [`keystone/clock.py`](keystone/clock.py)
> *Fixed-step clock with a bounded catch-up budget.*

**Size**: `42` lines (`1501` bytes)

**Classes:**
- `class FixedStepClock` - *Accumulates wall time and releases whole deterministic simulation steps.*
  - Method `.__init__(step, max_frame)`
  - Method `.reset(now)`
  - Method `.advance(now)`

---

### [`keystone/component_codec.py`](keystone/component_codec.py)
> *Shared JSON codec for typed scene components.*

**Size**: `141` lines (`5498` bytes)

**Functions:**
- `def validate_component_types(component_types)` - *Copy and validate a component name-to-type map.*
- `def json_safe(value, label)` - *Return the value after proving it can cross a JSON boundary.*
- `def component_to_dict(component)` - *Encode one component as ``{'type': name, 'data': ...}``.*
- `def _dataclass_from_mapping(name, component_type, data)` - *Construct a dataclass, rejecting fields it does not declare.*
- `def component_from_dict(item, component_types)` - *Decode one component, requiring an explicit type map.*

---

### [`keystone/culling.py`](keystone/culling.py)
> *Deterministic CPU view-frustum culling for the core forward renderer.*

**Size**: `146` lines (`5629` bytes)

**Functions:**
- `def culling_enabled(scene)` - *Return whether frustum culling is requested for this scene.*
- `def extract_planes(view_projection)` - *Extract normalized (a, b, c, d) frustum planes, deterministic order.*
- `def world_bounds(mesh, model)` - *Return the world-space AABB of a mesh under an affine model matrix.*
- `def aabb_visible(low, high, planes)` - *Return True when an AABB touches or intersects every frustum plane.*
- `def model_visible(mesh, model, planes)` - *Return True when a mesh under an affine model matrix survives culling.*
- `def node_visible(node, planes)` - *Return True when a scene node survives frustum culling.*
- `def cull_scene(scene, width, height)` - *Return python ``id()`` values of frustum-visible nodes.*

---

### [`keystone/export.py`](keystone/export.py)
> *Deterministic runnable project bundles for Keystone games.*

**Size**: `224` lines (`6740` bytes)

**Functions:**
- `def _within(path, root)`
- `def _sha256(path)`
- `def _copy_project(context, target)`
- `def _copy_engine(target)`
- `def _write_export_docs(context, target)`
- `def _build_manifest(context, target)`
- `def export_project(project, destination, *, force)` - *Validate a project and write a runnable, hashed export bundle.*

---

### [`keystone/geometry.py`](keystone/geometry.py)
> *Indexed triangle mesh data and surface material, independent of any GPU API.*

**Size**: `180` lines (`8928` bytes)

**Classes:**
- `class Material` - *Blinn-Phong surface parameters with PBR extensions used by the renderer.*
  - Method `.__post_init__()`
- `class MeshData` - *Immutable indexed triangle mesh with optional UVs and skinning.*
  - Method `.__post_init__()`
  - Property `.skinned` - *Whether this mesh carries a bound skin palette.*
  - Method `.vertex_count()`
  - Method `.triangle_count()`
  - Method `.bounds()`
  - Method `.interleaved()` - *Pack position, normal and UV into one vertex stream for the GPU.*
  - Method `.interleaved_skinned()` - *Pack the base stream plus padded joints and weights for the GPU.*

**Functions:**
- `def _is_finite_number(value)`
- `def _check_triplets(name, values)`

---

### [`keystone/gltf/__init__.py`](keystone/gltf/__init__.py)
> *Dependency-free glTF 2.0 import for Keystone scenes.*

**Size**: `5` lines (`153` bytes)

---

### [`keystone/gltf/io.py`](keystone/gltf/io.py)
> *glTF source reading, buffers and typed accessor decoding.*

**Size**: `212` lines (`8593` bytes)

**Functions:**
- `def _decode_glb(data)`
- `def _decode_text(data)`
- `def read_source(source)` - *Return (json text, base directory, GLB binary chunk) for a source.*
- `def decode_data_uri(uri)`
- `def load_buffers(document, base_dir, binary_chunk)`
- `def read_accessor(accessor, buffer_views, buffers)`

---

### [`keystone/gltf/loader.py`](keystone/gltf/loader.py)
> *Top-level glTF import orchestration.*

**Size**: `81` lines (`3010` bytes)

**Classes:**
- `class GltfImport` - *The result of importing one glTF document.*

**Functions:**
- `def load_gltf(source, registry)` - *Load a glTF 2.0 document from a path, JSON text or bytes.*

---

### [`keystone/gltf/materials.py`](keystone/gltf/materials.py)
> *glTF material conversion.*

**Size**: `58` lines (`2455` bytes)

**Functions:**
- `def load_materials(document, textures)`

---

### [`keystone/gltf/meshes.py`](keystone/gltf/meshes.py)
> *glTF mesh and primitive decoding.*

**Size**: `227` lines (`11425` bytes)

**Functions:**
- `def _as_vec3(value)`
- `def _compute_normals(positions, indices)`
- `def load_meshes(document, buffers, buffer_views, materials)`
- `def _accessor(document, index)`
- `def _require_joints_accessor(accessor, mesh_index)`
- `def _require_weights_accessor(accessor, mesh_index)`

---

### [`keystone/gltf/scene.py`](keystone/gltf/scene.py)
> *glTF node, transform and scene construction.*

**Size**: `204` lines (`8089` bytes)

**Functions:**
- `def _matrix_to_transform(matrix)`
- `def _node_transform(raw)`
- `def _with_skin(mesh, skin)`
- `def _node_skin(document, raw, skins)`
- `def build_scene(document, meshes, materials, skins)`

---

### [`keystone/gltf/skins.py`](keystone/gltf/skins.py)
> *glTF skin parsing: joint nodes and inverse bind matrices.*

**Size**: `69` lines (`3142` bytes)

**Functions:**
- `def load_skins(document, buffers, buffer_views, node_count)` - *Parse the glTF skins array into joint indices and inverse bind matrices.*
- `def _accessor(document, index)`

---

### [`keystone/gltf/textures.py`](keystone/gltf/textures.py)
> *glTF image and texture decoding.*

**Size**: `99` lines (`3946` bytes)

**Functions:**
- `def _image_bytes(image, buffers, buffer_views, base_dir)`
- `def _mime_from_path(path)`
- `def _texture_from_bytes(data, mime_type, name)`
- `def load_textures(document, buffers, buffer_views, base_dir)`

---

### [`keystone/gltf_import.py`](keystone/gltf_import.py)
> *Import glTF/GLB scenes into the prefab library and asset registry.*

**Size**: `55` lines (`2220` bytes)

**Functions:**
- `def is_gltf_asset(path)` - *Return True for a glTF JSON or binary GLB path.*
- `def import_gltf_prefab(path, registry, library, name)` - *Import one glTF/GLB scene, register its assets and save a prefab.*

---

### [`keystone/gpu/__init__.py`](keystone/gpu/__init__.py)
> *OpenGL 3.3 adapter: context, shader, mesh buffers and renderer.*

**Size**: `1` lines (`70` bytes)

---

### [`keystone/gpu/bloom.py`](keystone/gpu/bloom.py)
> *Deterministic emissive-aware bloom glow (luminance threshold, in-shader, no FBO).*

**Size**: `92` lines (`3146` bytes)

**Functions:**
- `def bloom_factor(luma, threshold, knee)` - *Return the deterministic smoothstep glow weight for one luminance.*
- `def bloom_color(color, threshold, knee, intensity)` - *Add the threshold glow to a display-referred 0..1 RGB triple.*
- `def bloom_blur_size(width, height, downsample)` - *Return the deterministic half-res blur size for a framebuffer.*
- `def bloom_composite(scene, blurred, intensity)` - *Add blurred light to the scene color with 0..1 clamp.*

---

### [`keystone/gpu/bloom_fbo.py`](keystone/gpu/bloom_fbo.py)
> *Deterministic RGBA8 color framebuffers for the bloom diffusion chain.*

**Size**: `89` lines (`3778` bytes)

**Classes:**
- `class BloomFbo` - *One RGBA8 color FBO owned by the renderer (one GL context).*
  - Method `.__init__(width, height)`
  - Method `.bind_for_write()`
  - Method `.unbind_after_write(width, height)`
  - Method `.bind_for_read(unit)`
  - Method `.unbind_after_read(unit)`
  - Method `.release()`

---

### [`keystone/gpu/context.py`](keystone/gpu/context.py)
> *GLFW window and OpenGL 3.3 context lifecycle with deterministic teardown.*

**Size**: `166` lines (`5578` bytes)

**Classes:**
- `class GLContext` - *A hidden or visible GLFW window owning one OpenGL 3.3 core context.*
  - Method `.__init__(width, height, title, visible, msaa)`
  - Method `.__enter__()`
  - Method `.__exit__(*exc_info)`
  - Method `._version_string()`
  - Method `.version()`
  - Method `.should_close()`
  - Method `.request_close()`
  - Method `.poll_events()`
  - Method `.swap_buffers()`
  - Method `.time()`
  - Method `.key_down(name)`
  - Method `.cursor_position()`
  - Method `.mouse_down(button)`
  - Method `.set_cursor_captured(captured)`
  - Method `.set_title(title)`
  - Method `.framebuffer_size()`
  - Method `.close()`

**Functions:**
- `def key_names()` - *Return the key names a real GL context can report to InputMap.sample().*
- `def require_opengl_33(version)` - *Refuse a context that cannot run the 3.3 core shader pipeline.*

---

### [`keystone/gpu/instancing.py`](keystone/gpu/instancing.py)
> *Deterministic grouping for hardware instancing.*

**Size**: `112` lines (`4204` bytes)

**Functions:**
- `def _material_key(material)` - *Normalize the grouping key to match renderer fallback behavior.*
- `def group_instances(scene, planes)` - *Group visible nodes by identical mesh/material payloads.*
- `def plan_instanced(scene)` - *Return a JSON-safe instancing plan mirroring ``plan_batches`` counts.*

---

### [`keystone/gpu/mesh_buffer.py`](keystone/gpu/mesh_buffer.py)
> *GPU mesh upload and indexed drawing for the Keystone renderer.*

**Size**: `116` lines (`4868` bytes)

**Classes:**
- `class GpuMesh` - *VAO/VBO/EBO triple owning one immutable MeshData upload.*
  - Method `.__init__(mesh)`
  - Method `.draw()`
  - Method `.draw_instanced(model_flats, normal_flats)` - *Draw all instances with per-instance model/normal divisor attributes.*
  - Method `.release()`

---

### [`keystone/gpu/post.py`](keystone/gpu/post.py)
> *Deterministic post color-grade (exposure + vignette, in-shader, no FBO).*

**Size**: `42` lines (`1264` bytes)

**Functions:**
- `def vignette_factor(nx, ny, strength)` - *Return the deterministic vignette multiplier for normalized coords 0..1.*
- `def grade_color(color, nx, ny, exposure, strength)` - *Apply exposure then vignette to a display-referred 0..1 RGB triple.*

---

### [`keystone/gpu/renderer.py`](keystone/gpu/renderer.py)
> *Blinn-Phong forward renderer with fog, shadows and screenshot readback.*

**Size**: `1211` lines (`48406` bytes)

**Classes:**
- `class Renderer` - *Owns the shader and per-mesh GPU buffers for one OpenGL context.*
  - Method `.__init__(width, height)`
  - Method `.resize(width, height)`
  - Method `._create_bloom_fbos()`
  - Method `._release_bloom_fbos()`
  - Method `._ensure_bloom_fbos()`
  - Method `._gpu_mesh(mesh)`
  - Method `._gpu_skinned_mesh(mesh)`
  - Method `._upload_bones(program, scene, mesh)`
  - Method `._gpu_texture(texture)`
  - Method `._draw_sky(scene, srgb_on, post_on, bloom_on)`
  - Method `._shadows_requested(scene)`
  - Method `._srgb_requested(scene)`
  - Method `._post_requested(scene)`
  - Method `._bloom_requested(scene)`
  - Method `._sprites_requested(scene)`
  - Method `._culling_requested(scene)`
  - Method `._init_sprite_buffers()`
  - Method `._release_sprite_buffers()`
  - Method `._camera_basis(scene)`
  - Method `._draw_sprites(scene, particles, view_projection, post_on, bloom_on)`
  - Method `._apply_bloom(program, bloom_on)`
  - Method `._apply_post(program, post_on)`
  - Method `._apply_shared(program, scene, view_projection, light_vp, shadows_on, srgb_on)`
  - Method `._apply_material(program, material)`
  - Method `._render_shadow_pass(scene, light_vp)`
  - Method `._draw_quad()`
  - Method `._draw_geometry(scene, view_projection, light_vp, shadows_on, srgb_on, post_on, bloom_on, planes)`
  - Method `._run_bloom_chain()`
  - Method `.render(scene, particles)`
  - Method `.read_pixels()`
  - Method `.save_png(path)`
  - Method `.release()`

**Functions:**
- `def normal_matrix(model)` - *Return transpose(inverse(upper 3x3)) in column-major order.*

---

### [`keystone/gpu/shader.py`](keystone/gpu/shader.py)
> *GLSL program compilation, uniform upload and cleanup.*

**Size**: `106` lines (`4298` bytes)

**Classes:**
- `class ShaderProgram` - *A linked vertex/fragment program with cached uniform locations.*
  - Method `.__init__(vertex_source, fragment_source)`
  - Method `._compile(stage, source, label)`
  - Method `.use()`
  - Method `._location(name)`
  - Method `.set_mat4(name, matrix)`
  - Method `.set_mat4_array(name, matrices)` - *Upload a fixed mat4 array palette (e.g. skinning bones).*
  - Method `.set_mat3(name, values)`
  - Method `.set_vec2(name, x, y)`
  - Method `.set_vec3(name, vector)`
  - Method `.set_vec3_array(name, vectors)` - *Upload a vec3 array; the uniform is located by its ``[0]`` element.*
  - Method `.set_float_array(name, values)` - *Upload a float array; the uniform is located by its ``[0]`` element.*
  - Method `.set_float(name, value)`
  - Method `.set_int(name, value)`
  - Method `.release()`

---

### [`keystone/gpu/shadow.py`](keystone/gpu/shadow.py)
> *Deterministic directional shadow mapping (fixed 1024 depth map, 3x3 PCF).*

**Size**: `154` lines (`5394` bytes)

**Classes:**
- `class ShadowMap` - *Fixed-size depth FBO owned by the renderer (one GL context).*
  - Method `.__init__(size)`
  - Method `.bind_for_write()`
  - Method `.unbind_after_write(width, height)`
  - Method `.bind_for_read(unit)`
  - Method `.unbind_after_read(unit)`
  - Method `.release()`

**Functions:**
- `def orthographic(left, right, bottom, top, near, far)` - *Build a deterministic orthographic projection (column-major).*
- `def light_view(direction)` - *Look from the light direction toward the origin (deterministic).*
- `def light_vp(direction)` - *Deterministic light view-projection for the fixed ortho box.*
- `def light_vp_for(light)` - *Convenience wrapper taking the scene directional light.*

---

### [`keystone/gpu/skinned_buffer.py`](keystone/gpu/skinned_buffer.py)
> *GPU upload for skinned meshes: base stream plus joints and weights.*

**Size**: `74` lines (`3012` bytes)

**Classes:**
- `class SkinnedGpuMesh` - *VAO/VBO/EBO triple owning one immutable skinned mesh upload.*
  - Method `.__init__(mesh)`
  - Method `.draw()`
  - Method `.release()`

---

### [`keystone/gpu/sprites.py`](keystone/gpu/sprites.py)
> *Deterministic GPU point-sprite math: size attenuation and soft alpha.*

**Size**: `74` lines (`2667` bytes)

**Functions:**
- `def sprite_scale(distance, size)` - *Return the deterministic pixel size for a particle.*
- `def soft_alpha(u, v)` - *Return the soft-circle coverage for quad UVs in [0, 1].*
- `def sprite_alpha(age, lifetime, u, v)` - *Return the combined fade * soft-circle alpha for one particle.*
- `def billboard_corners(center, right, up, world_size)` - *Return the four world corners for a camera-facing quad.*

---

### [`keystone/gpu/texture_buffer.py`](keystone/gpu/texture_buffer.py)
> *GPU upload and lifecycle for immutable TextureData.*

**Size**: `53` lines (`1835` bytes)

**Classes:**
- `class GpuTexture` - *One OpenGL 2D texture with mipmaps and repeat wrapping.*
  - Method `.__init__(data)`
  - Method `.bind(unit)`
  - Method `.release()`

---

### [`keystone/gpu/ui_renderer.py`](keystone/gpu/ui_renderer.py)
> *Screen-space OpenGL renderer for the human UI canvas.*

**Size**: `99` lines (`3160` bytes)

**Classes:**
- `class UiRenderer` - *Uploads one canvas per frame and draws it over the 3D scene.*
  - Method `.__init__()`
  - Method `.draw(canvas)` - *Draw the canvas with alpha blending, then restore 3D render state.*
  - Method `.release()`

---

### [`keystone/headless.py`](keystone/headless.py)
> *Simulation without a window: JSON action scripts and deterministic traces.*

**Size**: `77` lines (`2723` bytes)

**Functions:**
- `def load_actions(path)`
- `def run_simulation(game, frames, actions, step, trace, scene)` - *Advance a game without creating a window or OpenGL context.*

---

### [`keystone/history.py`](keystone/history.py)
> *Bounded undo/redo history for engine and game state.*

**Size**: `86` lines (`2813` bytes)

**Classes:**
- `class History` - *A small, bounded undo/redo stack.*
  - Method `.__init__(capacity)`
  - Property `.capacity`
  - Property `.can_undo`
  - Property `.can_redo`
  - Property `.redo_available`
  - Method `.push(value)` - *Record a new snapshot and discard any redo branch.*
  - Method `.undo()` - *Move to the previous snapshot and return it, or None when at the bottom.*
  - Method `.redo()` - *Move to the next snapshot and return it, or None when at the top.*
  - Method `.peek()` - *Return the current snapshot without moving, or None when empty.*
  - Method `.values()` - *Return all retained snapshots in chronological order.*
  - Method `.clear()`
  - Method `.__len__()`

---

### [`keystone/input.py`](keystone/input.py)
> *Generic input mapping: named actions, axes and pointer look.*

**Size**: `415` lines (`17468` bytes)

**Classes:**
- `class ActionState` - *One sampled input frame; games translate names into their own rules.*
  - Method `.__post_init__()`
  - Method `.without_pressed()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class InputMap` - *Maps keys and pointer motion to action names and continuous axes.*
  - Method `.__init__(bindings, look_speed, mouse_sensitivity, contexts, context)`
  - Method `.bind(action, key, context)`
  - Method `.set_context(context)`
  - Method `.get_context()`
  - Method `.list_contexts()`
  - Method `.unbind(action)` - *Remove a custom binding from the active context; returns False when not bound.*
  - Method `.list_actions()` - *Return a copy of the current action-to-key map for UI and AI clients.*
  - Method `.unbound_buttons(buttons)` - *Return declared buttons that no binding in any context can produce.*
  - Method `.unknown_keys(supported)` - *Return bound key names the given context cannot sample.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
  - Method `.save_bindings(path)`
  - Method `.load_bindings(path)`
  - Method `.set_mouse_enabled(enabled)`
  - Method `.set_look_enabled(enabled)`
  - Method `.sample(context, dt)`

**Functions:**
- `def _finite_number(value, label)` - *Return a finite real number, rejecting bools and string coercion.*
- `def _binding_pair(action, key)`

---

### [`keystone/library_trash.py`](keystone/library_trash.py)
> *Soft-delete helpers for file-backed scene and prefab libraries.*

**Size**: `82` lines (`2633` bytes)

**Functions:**
- `def _trash_root(directory)`
- `def move_to_trash(path, suffix)` - *Move one library file into the trash directory and return its new path.*
- `def _original_name(trash_name)`
- `def trash_entries(directory, suffix)` - *Return JSON-safe summaries of trashed entries in stable order.*
- `def restore_from_trash(directory, trash_name, suffix, validate_name)` - *Move one trashed entry back into the library without overwriting.*

---

### [`keystone/lifecycle.py`](keystone/lifecycle.py)
> *Deterministic start/update/stop lifecycle for scene components.*

**Size**: `177` lines (`6323` bytes)

**Classes:**
- `class LifecycleContext` - *Arguments passed to one component lifecycle hook.*
- `class ComponentRuntime` - *Run deterministic component lifecycle hooks for one scene.*
  - Method `.__init__(scene)`
  - Method `._entries()`
  - Method `._context(node, component, dt)`
  - Method `._start_component(node, component)`
  - Method `.start()` - *Start every hook-bearing component once and return the count.*
  - Method `._unwind_failed_start()` - *Stop whatever started before a failure, ignoring stop() errors.*
  - Method `.update(dt)` - *Advance one fixed tick and return the number of update hooks run.*
  - Method `.stop()` - *Stop started components in reverse order and return the count.*
  - Method `.describe()` - *Return the JSON-safe runtime summary for editor documents.*

**Functions:**
- `def lifecycle_hooks(value)` - *Return the lifecycle hook names implemented by a component or type.*

---

### [`keystone/material_graph.py`](keystone/material_graph.py)
> *Declarative, deterministic material graphs that evaluate to a Material.*

**Size**: `374` lines (`15883` bytes)

**Classes:**
- `class MaterialGraphNode` - *One node in a material graph: a kind, parameters and input node ids.*
  - Method `.__post_init__()`
  - Method `.param(name, default)` - *Return one parameter value, or default when it is absent.*
  - Method `.to_dict()`
- `class MaterialGraph` - *An immutable, serializable graph that evaluates to one Material.*
  - Method `.__post_init__()`
  - Method `.node(node_id)`
  - Method `.validate()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
  - Method `.evaluate(*, textures, registry)` - *Evaluate the graph and return its Material.*

**Functions:**
- `def _json_value(value)`
- `def _from_json_value(value)`
- `def _evaluate_node(node, values, textures, registry)`

---

### [`keystone/material_library.py`](keystone/material_library.py)
> *File-backed material libraries for editors, tools and AI clients.*

**Size**: `296` lines (`11172` bytes)

**Classes:**
- `class MaterialEntry` - *One library file and its material summary, or why it could not load.*
  - Method `.describe()` - *Return a JSON-safe entry for editor and AI documents.*
- `class MaterialLibrary` - *Discover, save and load ``.kmaterial`` files in one directory.*
  - Method `.__init__(directory, registry)`
  - Method `.asset_id(name)` - *Return the registry id used for a saved material.*
  - Method `.path_for(name)` - *Return the safe file path for one library name.*
  - Method `.save(name, material)` - *Write one material atomically.*
  - Method `.load(name)` - *Load one material or raise KeyError when the entry is absent.*
  - Method `.entry(name)` - *Load one entry's summary, capturing load failures as ``error``.*
  - Method `.delete(name)` - *Move one entry to the library trash and return its former path.*
  - Method `.trash()` - *Return recoverable deleted entries.*
  - Method `.restore(trash_name)` - *Restore one trashed entry and return its summary.*
  - Method `.entries()` - *Return every ``.kmaterial`` file in stable name order.*
  - Method `.register_all(registry)` - *Register every loadable material; invalid entries stay reported.*

**Functions:**
- `def _vec3(value, label)`
- `def _number(value, label)`
- `def material_from_document(data, registry)` - *Build a validated Material from one JSON-safe document.*
- `def material_to_document(name, material, registry)` - *Return a JSON-safe material document, resolving its texture id.*

---

### [`keystone/math3d.py`](keystone/math3d.py)
> *Column-major 3D math primitives shared by the scene, camera and GPU layers.*

**Size**: `377` lines (`13326` bytes)

**Classes:**
- `class Vec3` - *Immutable 3-component vector with the usual right-handed operations.*
  - Method `.__add__(other)`
  - Method `.__sub__(other)`
  - Method `.__mul__(scalar)`
  - Method `.__truediv__(scalar)`
  - Method `.__neg__()`
  - Method `.__iter__()`
  - Method `.dot(other)`
  - Method `.cross(other)`
  - Method `.length()`
  - Method `.length_squared()`
  - Method `.normalized()`
  - Method `.lerp(other, t)`
- `class Mat4` - *Immutable 4x4 matrix stored column-major, ready for OpenGL upload.*
  - Method `.__post_init__()`
  - Method `.__mul__(other)`
  - Method `.__iter__()`
  - Method `.__getitem__(index)`
  - Method `.identity()`
  - Method `.translation(x, y, z)`
  - Method `.scale(x, y, z)`
  - Method `.rotation_x(radians)`
  - Method `.rotation_y(radians)`
  - Method `.rotation_z(radians)`
  - Method `.rotation_axis(axis, radians)`
  - Method `.perspective(fov_y_degrees, aspect, near, far)`
  - Method `.look_at(eye, target, up)`
  - Method `.transform_point(point)`
  - Method `.project_point(point)` - *Transform by a projection and divide by w to obtain normalized device coordinates.*
  - Method `.transform_direction(direction)`
  - Method `.inverse()` - *Invert an affine transform; raise ValueError for perspective matrices.*
  - Method `.flat()`
- `class Quat` - *Unit quaternion (w, x, y, z) for rotation without gimbal lock.*
  - Method `.__mul__(other)`
  - Method `.identity()`
  - Method `.from_axis_angle(axis, radians)`
  - Method `.conjugate()`
  - Method `.normalized()`
  - Method `.rotate(vector)`
  - Method `.to_mat4()`
  - Method `.slerp(other, t)`
  - Method `.almost_equal(other, places)`

---

### [`keystone/mesh_builder.py`](keystone/mesh_builder.py)
> *Compose boxes and quads into a single indexed MeshData.*

**Size**: `189` lines (`8052` bytes)

**Classes:**
- `class MeshBuilder` - *Accumulates flat-shaded quads and boxes, then builds one mesh.*
  - Method `.__init__()`
  - Method `._require_mode(mode)`
  - Method `.add_quad(p0, p1, p2, p3, color)`
  - Method `.add_mesh(mesh, offset, scale, color)` - *Merge another mesh under a uniform scale and translation.*
  - Method `.add_mesh_matrix(mesh, matrix, color)` - *Merge a mesh transformed by a world matrix (positions + normals).*
  - Method `.add_skinned_mesh(mesh)` - *Concatenate a skinned mesh verbatim (positions, joints, weights).*
  - Method `.add_box(cx, cy, cz, sx, sy, sz, color)`
  - Method `.is_empty()`
  - Method `.build()`

---

### [`keystone/obj_loader.py`](keystone/obj_loader.py)
> *Streaming Wavefront OBJ loader producing indexed triangle meshes.*

**Size**: `137` lines (`5953` bytes)

**Functions:**
- `def load_obj(path)` - *Read an OBJ file line by line so file size is never loaded whole.*
- `def parse_obj(text)` - *Parse OBJ text already in memory, mainly for tests and embedded assets.*
- `def _resolve_index(raw, count, kind, number, line)`
- `def _corner(token, number, line, vertices, uvs, normals)`
- `def _parse_lines(lines)`
- `def _build_mesh(positions, normals, uvs, faces)`

---

### [`keystone/particles.py`](keystone/particles.py)
> *Deterministic, game-agnostic CPU particles: emitters, systems and reports.*

**Size**: `477` lines (`19806` bytes)

**Classes:**
- `class Particle` - *One live particle: position, velocity, age, lifetime and size.*
  - Method `.__post_init__()`
  - Method `.alive()`
- `class Emitter` - *Deterministic spawn recipe: rate, lifetime, speed, spread and forces.*
  - Method `.__post_init__()`
  - Method `.spawn(index, origin)` - *Spawn one particle deterministically from the emitter seed and index.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class ParticleSystem` - *Owns emitters and live particles; deterministic under a fixed call order.*
  - Method `.__post_init__()`
  - Method `.add(emitter)`
  - Method `.burst(emitter_name, count, origin)` - *Emit count particles immediately; returns the number actually added.*
  - Method `.step(dt, colliders, restitution, friction, kill_on_contact)` - *Advance all particles by dt; returns the live count afterwards.*
  - Method `._respond_axis(vx, vy, vz, axis, restitution)` - *Reflect one velocity axis with settle snapping; other axes untouched.*
  - Method `._step_free(dt)`
  - Method `.alive_count()`
  - Method `.clear()`
  - Method `._emitter_for(particle)`

**Functions:**
- `def _finite(value, label)`
- `def _vec3_value(value, label)`
- `def _depenetrate_static(px, py, pz, flat)` - *Eject a stationary point from the nearest box face deterministically.*
- `def _move_point_flat(px, py, pz, axis, amount, flat)` - *Float-only swept point move; axis is 0/1/2 for x/y/z.*
- `def particles_report(system)`

---

### [`keystone/physics.py`](keystone/physics.py)
> *Generic collision primitives and ray queries for the engine core.*

**Size**: `184` lines (`7182` bytes)

**Classes:**
- `class Ray`
  - Method `.__post_init__()`
- `class AABB`
  - Method `.__post_init__()`
  - Method `.low()`
  - Method `.high()`
  - Method `.contains(point)`
  - Method `.overlaps(other)`
- `class RayHit`
- `class Sphere`
  - Method `.__post_init__()`

**Functions:**
- `def ray_aabb(ray, box)` - *Return the nearest positive world-space hit distance, or None.*
- `def raycast(ray, colliders, predicate)` - *Return the nearest AABB hit, optionally filtered by key and box.*
- `def ray_sphere(ray, sphere)`
- `def aabb_overlap(first, second)`
- `def sphere_aabb_overlap(sphere, box)`
- `def resolve_sphere_aabb(sphere, box)` - *Push a sphere out of an AABB along the shallowest axis.*

---

### [`keystone/playtest.py`](keystone/playtest.py)
> *Seeded bot playtesting: transcripts, diffing, policies and fairness checks.*

**Size**: `711` lines (`30082` bytes)

**Classes:**
- `class BotPolicy` - *One seeded decision step over the five-operation game contract.*
  - Method `.reset(seed)`
  - Method `.select(snapshot, actions_spec, rng)`
- `class RandomPolicy` - *Uniform baseline: sample axes in [-1, 1], occasionally press a button.*
  - Method `.__init__(press_chance)`
  - Method `.reset(seed)`
  - Method `.select(snapshot, actions_spec, rng)`
- `class GreedyPolicy` - *Stateful bandit: repeat the last action while score improves, else resample.*
  - Method `.__init__()`
  - Method `.reset(seed)`
  - Method `.select(snapshot, actions_spec, rng)`
- `class ScriptedPolicy` - *Replay an action list; hold the final action when the run is longer.*
  - Method `.__init__(actions)`
  - Method `.reset(seed)`
  - Method `.select(snapshot, actions_spec, rng)`

**Functions:**
- `def _canon_value(value)`
- `def canon(snapshot)` - *Project a snapshot to its canonical search form.*
- `def canon_hash(snapshot)` - *Stable hash of the canonical snapshot projection.*
- `def read_outcome(snapshot)` - *Read the opportunistic outcome signal; ``unknown`` when absent.*
- `def read_score(snapshot)` - *Read the opportunistic numeric score signal, if present.*
- `def to_command_log(transcript)` - *Convert a transcript back to a replayable :class:`CommandLog`.*
- `def run_bot(factory, policy, frames, seed, step, max_wall_seconds, trace, scene_loader, on_frame, on_event, events)` - *Play one seeded bot run headlessly and record the transcript.*
- `def diff_transcripts(before, after)` - *Compare two transcripts: hash fast-path, then first divergence.*
- `def _validate_actions_spec(spec)`
- `def _sample_action(rng, axes, buttons)`
- `def load_policy(spec)` - *Resolve ``random``/``greedy``/``scripted`` or a ``module:Factory`` policy.*
- `def make_report(transcript, fairness)` - *Build the frozen schema-1 playtest report shared with web adapters.*
- `def validate_fairness(factory, reference_actions, frames, seeds, step, max_states, max_wall_seconds, time_limit_frames, scene_loader)` - *Judge whether a configuration is winnable, with reasons.*

---

### [`keystone/plugin.py`](keystone/plugin.py)
> *Game-agnostic module contract and loader.*

**Size**: `122` lines (`4624` bytes)

**Classes:**
- `class GameModule` - *The five operations an external game exposes to the engine.*
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`

**Functions:**
- `def describe_game(game)` - *Return a machine-readable capability/action/snapshot description.*
- `def load_game(spec)` - *Load an external game from 'package.module:Factory'.*

---

### [`keystone/png.py`](keystone/png.py)
> *Minimal dependency-free PNG writer for headless frame captures.*

**Size**: `132` lines (`4974` bytes)

**Functions:**
- `def _chunk(kind, payload)`
- `def _paeth(a, b, c)`
- `def read_png(path)` - *Read an 8-bit RGBA non-interlaced PNG and return top-down pixels.*
- `def png_bytes(width, height, rgba, flip_vertical)` - *Encode RGBA bytes as an 8-bit PNG in memory.*
- `def write_png(path, width, height, rgba, flip_vertical)` - *Write RGBA bytes (OpenGL order: bottom-up) as an 8-bit PNG.*

---

### [`keystone/prefab.py`](keystone/prefab.py)
> *Deterministic prefabs: capture, persist and instantiate reusable subtrees.*

**Size**: `505` lines (`20483` bytes)

**Classes:**
- `class Prefab` - *An immutable-name, detached template of one or more scene subtrees.*
  - Method `.__post_init__()`
  - Method `.from_node(node, name)` - *Capture one detached subtree.*
  - Method `.from_nodes(nodes, name)` - *Capture several subtrees as a deterministic multi-root prefab.*
  - Method `.from_scene(scene, name)` - *Capture every child of a scene root as a multi-root prefab.*
  - Method `.copy(name)` - *Return a detached template copy, preserving nested links and IDs.*
  - Property `.node_count`
  - Method `.asset_ids(registry)` - *Return the mesh/material asset ids referenced by this prefab.*
  - Method `.to_dict(registry)` - *Serialize to versioned JSON; mesh/material payloads need registered assets.*
  - Method `.from_dict(data, registry, component_types)` - *Load versioned JSON; asset ids resolve through the registry.*
  - Method `.save(path, registry)` - *Write a versioned JSON prefab atomically.*
  - Method `.load(path, registry, component_types)` - *Load a versioned JSON prefab from disk.*
  - Method `.instantiate(scene, parent, instance)` - *Attach fresh copies to a scene, returning the new root nodes.*
  - Method `.describe()` - *Return a JSON-safe structural summary for AI clients and tooling.*

**Functions:**
- `def _copy_template(node)`
- `def _normalize_template(node, inherited, prefab_name, is_root)`
- `def _capture_template(node, prefab_name)`
- `def _allocate_instance_prefix(scene, base)`
- `def _collect_ids(node)`
- `def _asset_id(registry, payload, label, kind)`
- `def _transform_to_dict(transform)`
- `def _transform_from_dict(value)`

---

### [`keystone/prefab_library.py`](keystone/prefab_library.py)
> *File-backed prefab libraries for editors, tools and AI clients.*

**Size**: `186` lines (`7291` bytes)

**Classes:**
- `class PrefabEntry` - *One library file and its loaded summary, or why it could not load.*
  - Method `.describe()` - *Return a JSON-safe entry for editor and AI documents.*
- `class PrefabLibrary` - *Discover, save and load ``.kprefab`` files in one directory.*
  - Method `.__init__(directory, registry, component_types)`
  - Method `.path_for(name)` - *Return the safe file path for one library name.*
  - Method `.save(name, prefab)` - *Write one prefab atomically; its internal name must match the entry.*
  - Method `.load(name)` - *Load one prefab or raise KeyError when the entry is absent.*
  - Method `.rename(old, new)` - *Rename one entry, updating its internal name and rejecting collisions.*
  - Method `.duplicate(old, new)` - *Copy one entry to a new name, updating its internal name.*
  - Method `.delete(name)` - *Move one entry to the library trash and return its former path.*
  - Method `.trash()` - *Return recoverable deleted entries.*
  - Method `.restore(trash_name)` - *Restore one trashed entry and return its summary.*
  - Method `.entry(name)` - *Load one entry's summary, capturing load failures as ``error``.*
  - Method `.entries()` - *Return every ``.kprefab`` file in stable name order.*
  - Method `.describe()` - *Return JSON-safe summaries for every library file.*

**Functions:**
- `def validate_library_name(name)` - *Validate a portable library name that cannot escape its directory.*

---

### [`keystone/primitives.py`](keystone/primitives.py)
> *Procedural primitives: cube, plane, cone, cylinder and UV sphere.*

**Size**: `170` lines (`7205` bytes)

**Functions:**
- `def _append_quad(positions, normals, uvs, indices, corners, normal)`
- `def cube(size)`
- `def plane(size)`
- `def cone(radius, height, segments)`
- `def cylinder(radius, height, segments)`
- `def sphere(radius, segments, rings)`

---

### [`keystone/project.py`](keystone/project.py)
> *Project manifests and one-command scaffolding for external Keystone games.*

**Size**: `823` lines (`30878` bytes)

**Classes:**
- `class ProjectManifest` - *Versioned, JSON-safe project metadata.*
  - Method `.__post_init__()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class ProjectContext` - *A loaded manifest plus its project directory.*
  - Method `.describe()`

**Functions:**
- `def _module_name(name)`
- `def _manifest_path(path)`
- `def load_project(path)` - *Load ``keystone.json`` from a project directory or manifest file.*
- `def save_project(path, manifest)` - *Write a manifest atomically; accepts a directory or a JSON path.*
- `def set_project_startup_scene(context, name)` - *Persist one optional startup scene name and return the new manifest.*
- `def _relative_asset_path(value)`
- `def project_asset_id(value)` - *Return the deterministic registry id for one manifest asset path.*
- `def resolve_project_asset(context, value)` - *Resolve one asset path and prove it stays inside the project.*
- `def resolve_project_target(context, value)` - *Resolve one writable target path inside the project without requiring it.*
- `def import_project_assets(context, registry, component_types)` - *Load every manifest asset into an existing registry.*
- `def import_project_asset(context, registry, value, component_types)` - *Import one editor-selected file and append it to the project manifest.*
- `def forget_project_asset(context, registry, value)` - *Remove one project asset path from the manifest and registry.*
- `def _restore_registry_records(registry, before)` - *Restore every record replaced or added by a failed import.*
- `def import_project_gltf(context, registry, prefab_library, value, name)` - *Import a project glTF/GLB scene as a prefab and record its source.*
- `def attach_project_assets(game, context, component_types, prefab_library)` - *Import manifest assets, including glTF scenes as prefab entries.*
- `def validate_project(context, game)` - *Validate project assets, scenes and prefabs without writing project files.*
- `def load_project_game(context)` - *Import and validate a project's game after adding its directory to sys.path.*
- `def _game_source(manifest)`
- `def _project_readme(manifest)`
- `def _write_starter_library(directory, module)`
- `def create_project(directory, *, name, game, force)` - *Scaffold a runnable project directory and return its context.*

---

### [`keystone/replay.py`](keystone/replay.py)
> *Deterministic action logs and stable state hashes.*

**Size**: `164` lines (`5924` bytes)

**Classes:**
- `class CommandLog`
  - Method `.__post_init__()`
  - Method `.record(actions)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
  - Method `.save(path)`
  - Method `.load(path)`
  - Method `.replay_actions()`

**Functions:**
- `def _canonical_hash_value(value)`
- `def stable_hash(payload)` - *Hash a JSON-safe payload deterministically; reject process-local values.*
- `def run_log(factory, log, trace, scene_loader)` - *Replay a command log on a fresh game without a window or GL context.*
- `def verify_log(factory, log, scene_loader)` - *Run one log twice from a factory and compare final hashes.*

---

### [`keystone/samples.py`](keystone/samples.py)
> *A minimal game-agnostic sample used to smoke-test the engine.*

**Size**: `157` lines (`6094` bytes)

**Classes:**
- `class CubeDemo` - *A rotating cube scene; contains no combat, puzzles or genre rules.*
  - Method `.__init__()`
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`

---

### [`keystone/scene.py`](keystone/scene.py)
> *Scene graph: hierarchical transforms, identity, components, camera and light.*

**Size**: `554` lines (`21923` bytes)

**Classes:**
- `class Transform` - *Translation, rotation and non-uniform scale composed as T * R * S.*
  - Method `.__post_init__()`
  - Method `.matrix()`
- `class PrefabLink` - *Editor-facing link from a scene node to the prefab instance it came from.*
  - Method `.__post_init__()`
  - Method `.to_dict()` - *Return the JSON-safe link document.*
  - Method `.from_dict(data)` - *Validate one link document.*
- `class SceneGroup` - *Editor-facing metadata for one additively loaded scene container.*
  - Method `.__post_init__()`
  - Method `.to_dict()` - *Return the JSON-safe group document.*
  - Method `.from_dict(data)` - *Validate one scene group document.*
- `class Node` - *A named transform node with identity, tags, components and children.*
  - Method `.__post_init__()`
  - Method `.add_tag(tag)`
  - Method `.remove_tag(tag)`
  - Method `.has_tag(tag)`
  - Method `.add_component(component)`
  - Method `.get_component(component_type)`
  - Method `.require_component(component_type)`
  - Method `.has_component(component_type)`
  - Method `.remove_component(component_type)`
  - Method `.add_child(child)`
  - Method `.remove_child(child)`
  - Method `.is_ancestor_of(other)`
  - Method `.world_matrix()`
  - Method `.world_visible()`
  - Method `.traverse()`
- `class Sprite` - *A camera-facing quad drawn as a billboard at the node's position.*
  - Method `.__post_init__()`
- `class DirectionalLight` - *A direction the light travels in, plus linear color and intensity.*
  - Method `.__post_init__()`
  - Method `.unit_direction()`
  - Method `.radiance()`
- `class PointLight` - *A local light with quadratic falloff, used for torches and lamps.*
  - Method `.__post_init__()`
- `class ShadowSettings` - *Deterministic directional shadow-map toggle (fixed 1024 map, bias 0.005).*
- `class ColorSettings` - *Deterministic sRGB-correct linear pipeline toggle (in-shader, pow 2.2).*
- `class PostSettings` - *Deterministic post color-grade toggle (in-shader exposure + vignette).*
- `class BloomSettings` - *Deterministic bloom glow toggle (in-shader luminance threshold).*
- `class SpriteSettings` - *Deterministic GPU point-sprite toggle (one instanced quad per particle).*
- `class CullingSettings` - *Deterministic CPU view-frustum culling toggle (color pass only).*
- `class Scene` - *Root node, identity allocation, queries, camera, lights and atmosphere.*
  - Method `.add(node)`
  - Property `.point_light` - *The first point light, for scenes that carry exactly one.*
  - Method `.point_light(value)`
  - Method `.traverse()`
  - Method `.query(*, name, tag, layer, component)` - *Return every node matching all supplied filters.*
  - Method `.find(*, name, tag, layer, component)` - *Return the first node matching all supplied filters.*
  - Method `.find_by_id(node_id)`
  - Method `._used_ids(exclude)`
  - Method `.restore_next_id(value)` - *Advance the deterministic ID counter after loading a snapshot.*
  - Method `._prepare(node)`

**Functions:**
- `def _finite_vec3(value, label)`
- `def _root_node()`

---

### [`keystone/scene_diff.py`](keystone/scene_diff.py)
> *Structured diffs between versioned scene snapshot documents.*

**Size**: `93` lines (`3451` bytes)

**Functions:**
- `def _node_map(document)`
- `def _section_diff(before, after)`
- `def diff_scene_documents(before, after)` - *Compare two scene snapshot documents and return a structured diff.*

---

### [`keystone/scene_library.py`](keystone/scene_library.py)
> *File-backed scene libraries for editors, tools and AI clients.*

**Size**: `232` lines (`9342` bytes)

**Classes:**
- `class SceneEntry` - *One library file and its loaded summary, or why it could not load.*
  - Method `.describe()` - *Return a JSON-safe entry for editor and AI documents.*
- `class SceneLibrary` - *Discover, save, load and restore ``.kscene`` files in one directory.*
  - Method `.__init__(directory, registry, component_types)`
  - Method `.path_for(name)` - *Return the safe file path for one library name.*
  - Method `.save(name, scene)` - *Write one scene snapshot atomically.*
  - Method `.document(name)` - *Read one scene document without rebuilding it.*
  - Method `._require_assets(name, data)`
  - Method `.load(name)` - *Load one scene or raise KeyError when the entry is absent.*
  - Method `.load_into(name, scene)` - *Replace one existing Scene in place from a library entry.*
  - Method `.rename(old, new)` - *Rename one entry, updating its internal name and rejecting collisions.*
  - Method `.duplicate(old, new)` - *Copy one entry to a new name, updating its internal name.*
  - Method `.delete(name)` - *Move one entry to the library trash and return its former path.*
  - Method `.trash()` - *Return recoverable deleted entries.*
  - Method `.restore(trash_name)` - *Restore one trashed entry and return its summary.*
  - Method `.entry(name)` - *Load one entry's summary, capturing load failures as ``error``.*
  - Method `.entries()` - *Return every ``.kscene`` file in stable name order.*
  - Method `.describe()` - *Return JSON-safe summaries for every library file.*

**Functions:**
- `def _node_count(scene)`
- `def _asset_refs(data)`

---

### [`keystone/scene_snapshot.py`](keystone/scene_snapshot.py)
> *Versioned, asset-aware snapshots of a Keystone scene.*

**Size**: `514` lines (`21455` bytes)

**Functions:**
- `def _vec3_to_list(value)` - *Serialize a vector as floats.*
- `def _vec3_from_value(value, label, default)`
- `def _light_to_dict(light)`
- `def _light_from_dict(data)`
- `def _point_light_to_dict(light)`
- `def _point_light_from_dict(data)`
- `def _sprite_to_dict(sprite)`
- `def _sprite_from_dict(data)`
- `def _transform_to_dict(transform)`
- `def _transform_from_dict(data)`
- `def _payload_asset_ids(registry)`
- `def _required_node_id(raw)`
- `def _restore_asset(registry, asset_id, expected_kind, label)`
- `def scene_to_dict(scene, registry)` - *Serialize a scene to a versioned, JSON-safe dictionary.*
- `def scene_from_dict(data, registry, component_types)` - *Rebuild a scene from a versioned snapshot.*
- `def restore_scene(target, data, registry, component_types)` - *Replace one Scene's contents in place from a snapshot.*

---

### [`keystone/schema.py`](keystone/schema.py)
> *Core-facing schema versions shared with optional adapters.*

**Size**: `91` lines (`2021` bytes)

---

### [`keystone/serialization.py`](keystone/serialization.py)
> *Atomic JSON persistence for engine and game state.*

**Size**: `72` lines (`2197` bytes)

**Functions:**
- `def _temporary_path(target)`
- `def _replace_with_retry(temporary, target, attempts)`
- `def _fsync_directory(directory)`
- `def write_bytes_atomic(path, payload)` - *Write bytes through a unique temp file, fsync and atomic replace.*
- `def write_json_atomic(path, payload, backup)`
- `def read_json(path)`

---

### [`keystone/skin.py`](keystone/skin.py)
> *Deterministic linear-blend skinning: bone palettes and CPU reference math.*

**Size**: `122` lines (`4823` bytes)

**Functions:**
- `def bone_matrices(scene, mesh)` - *Return world-space bone palettes (joint world matrix times inverse bind).*
- `def _rotate_normal(bone, normal)` - *Transform a normal by transpose(inverse(upper 3x3)) of the bone.*
- `def skin_point(position, normal, joints, weights, bones)` - *Deform one vertex by its influences; mirrors the vertex shader exactly.*
- `def skin_mesh(mesh, bones)` - *Return a deformed copy of the mesh in bind-pose layout (CPU oracle).*

---

### [`keystone/state_machine_library.py`](keystone/state_machine_library.py)
> *File-backed animation state machine libraries for editors and AI clients.*

**Size**: `181` lines (`6719` bytes)

**Classes:**
- `class StateMachineEntry` - *One library file and its state summary, or why it could not load.*
  - Method `.describe()` - *Return a JSON-safe entry for editor and AI documents.*
- `class StateMachineLibrary` - *Discover, save and load ``.kstate`` machines in one directory.*
  - Method `.__init__(directory)`
  - Method `.path_for(name)` - *Return the safe file path for one library name.*
  - Method `.save(name, machine)` - *Write one state machine atomically.*
  - Method `.load(name)` - *Load one machine or raise KeyError when the entry is absent.*
  - Method `.rename(old, new)` - *Rename one entry, rejecting collisions and updating the file.*
  - Method `.duplicate(old, new)` - *Copy one entry to a new name, rejecting collisions.*
  - Method `.delete(name)` - *Move one entry to the library trash and return its former path.*
  - Method `.trash()` - *Return recoverable deleted entries.*
  - Method `.restore(trash_name)` - *Restore one trashed entry and return its summary.*
  - Method `.entry(name)` - *Load one entry's summary, capturing load failures as ``error``.*
  - Method `.entries()` - *Return every ``.kstate`` file in stable name order.*

---

### [`keystone/testing.py`](keystone/testing.py)
> *Deterministic scenario helpers for AI and CI tests.*

**Size**: `176` lines (`5792` bytes)

**Functions:**
- `def run_script(game, actions, frames, step, trace, scene_loader)`
- `def verify_determinism(factory, actions, frames, step, scene_loader)` - *Run one scenario twice from a factory and compare final hashes.*
- `def assert_deterministic(factory, actions, frames, step, scene_loader)`
- `def scene_fingerprint(scene)` - *Return a stable digest of a scene's structure for snapshot assertions.*
- `def assert_scene_budget(scene, max_nodes, max_triangles, max_draw_calls)` - *Assert a scene stays within coarse budgets and return what was measured.*
- `def _vec(value)`
- `def _quat(value)`

---

### [`keystone/texture.py`](keystone/texture.py)
> *Immutable RGBA texture data and dependency-free texture sources.*

**Size**: `250` lines (`9364` bytes)

**Classes:**
- `class TextureData` - *Top-down RGBA8 pixels with a stable name for reports and debugging.*
  - Method `.__post_init__()`
  - Method `.sha256()` - *Return a stable digest of the shape plus the pixel payload.*
  - Method `.from_png(path, name)` - *Load an 8-bit RGBA non-interlaced PNG through the dependency-free reader.*
  - Method `.from_png_bytes(data, name)` - *Load an 8-bit RGBA non-interlaced PNG from bytes.*
  - Method `.pattern(preset, size, dark, light, seed, name)` - *Build a deterministic procedural texture without an image file.*
  - Method `.checker(size, dark, light, cell, name)` - *Build a deterministic RGBA checker texture without an image file.*

**Functions:**
- `def _rgba(color, label)` - *Clamp three linear floats to one opaque RGBA8 tuple.*
- `def _blend(first, second, amount)` - *Mix two opaque RGBA8 tuples by ``amount`` (0 = first, 1 = second).*
- `def _cell(size, base, accent, seed)` - *One flat color for every pixel.*
- `def _grid(size, base, accent, seed)` - *Thin lattice of accent lines every eighth of the texture.*
- `def _panel(size, base, accent, seed)` - *Recessed plate: brighter bevel near the edges, darker centre.*
- `def _rivets(size, base, accent, seed)` - *A panel with four corner studs.*
- `def _noise(size, base, accent, seed)` - *Seeded speckle; the same seed always yields the same pixels.*

---

### [`keystone/triggers.py`](keystone/triggers.py)
> *Game-agnostic trigger volumes with enter/exit tracking.*

**Size**: `49` lines (`1458` bytes)

**Classes:**
- `class TriggerVolume` - *A named AABB that reports when a body enters or leaves it.*
  - Method `.__post_init__()`
  - Method `.contains(body)`
- `class TriggerEvents` - *The enter, exit and active sets for one tracker update.*
- `class TriggerTracker` - *Remember active trigger names across updates.*
  - Method `.update(body, volumes)`
  - Method `.reset()`

---

### [`keystone/ui/__init__.py`](keystone/ui/__init__.py)
> *Dependency-free human UI: bitmap font, canvas and HUD overlay.*

**Size**: `7` lines (`287` bytes)

---

### [`keystone/ui/canvas.py`](keystone/ui/canvas.py)
> *Screen-space 2D canvas built from clipped color quads and bitmap text.*

**Size**: `162` lines (`5704` bytes)

**Classes:**
- `class TextElement` - *One text draw call recorded for AI/UI reports.*
- `class ButtonElement` - *One interactive button recorded for AI/UI reports.*
- `class Canvas` - *Collects UI quads in top-left pixel coordinates and flattens them for GL.*
  - Method `.__init__(width, height)`
  - Property `.labels` - *Return the drawn text values in draw order.*
  - Method `._add(x, y, width, height, color)`
  - Method `.rect(x, y, width, height, color)` - *Append an axis-aligned filled rectangle, clipped to the canvas.*
  - Method `.text(x, y, text, color, scale)` - *Append bitmap text; lowercase is drawn as uppercase.*
  - Method `.text_width(text, scale)` - *Pixel width of a text run at this canvas scale (shared font metric).*
  - Method `.line_height(scale)` - *Pixel height of one text line at this canvas scale.*
  - Method `.fit_text(text, width, scale)` - *Trim text so it fits ``width`` pixels at this scale.*
  - Method `.text_right(right, y, text, color, scale)` - *Append text whose right edge sits at ``right``.*
  - Method `.text_center(center, y, text, color, scale)` - *Append text horizontally centred on ``center``.*
  - Method `.add_button(x, y, width, height, label, action, selected, hovered)` - *Record button metadata; drawing stays with the widgets module.*
  - Method `.vertices()` - *Return interleaved x, y, r, g, b, a vertices for six triangles per quad.*
  - Method `.measured_height(scale)` - *Return the line height matching a text call at the same scale.*

---

### [`keystone/ui/font.py`](keystone/ui/font.py)
> *Embedded 5x7 bitmap font for the dependency-free human overlay.*

**Size**: `92` lines (`5112` bytes)

**Functions:**
- `def glyph(character)` - *Return the 7x5 rows for one character; lowercase maps to uppercase.*
- `def text_width(text, scale)` - *Return the pixel width of text, excluding trailing tracking.*
- `def line_height(scale)` - *Return the pixel height of one uppercase text line.*
- `def truncate_text(text, width, scale)` - *Trim text so it fits width pixels, leaving room for an ellipsis-free cut.*

---

### [`keystone/ui/menu.py`](keystone/ui/menu.py)
> *Game-agnostic pause menu state: items, selection and activation.*

**Size**: `41` lines (`1176` bytes)

**Classes:**
- `class MenuItem` - *One labelled action the human can choose.*
- `class PauseMenu` - *Wraps selection over a fixed item list; contains no rendering or input.*
  - Method `.__init__(items)`
  - Method `.move(delta)` - *Move the selection by delta, wrapping at both ends.*
  - Method `.action()` - *Return the action of the selected item.*

---

### [`keystone/ui/overlay.py`](keystone/ui/overlay.py)
> *Game-agnostic human overlay: HUD, controls help and pause menu.*

**Size**: `172` lines (`7337` bytes)

**Classes:**
- `class HudState` - *Presentation-only snapshot the overlay needs for one frame.*
- `class HumanOverlay` - *Builds the pixel UI, pause menu and button hitboxes.*
  - Method `.__init__()`
  - Method `.toggle()`
  - Method `.hit_test(x, y)` - *Return the action of the button under the pointer, if any.*
  - Method `._menu(canvas, state, scale, line)`
  - Method `.build(state, game_draw)`

---

### [`keystone/ui/report.py`](keystone/ui/report.py)
> *Serialize a rendered UI canvas into machine-readable report metadata.*

**Size**: `38` lines (`1208` bytes)

**Functions:**
- `def describe_canvas(canvas, paused, visible)` - *Return stable top-left pixel metadata for labels and buttons.*

---

### [`keystone/ui/widgets.py`](keystone/ui/widgets.py)
> *Small immediate-mode UI widgets: panels and labelled buttons.*

**Size**: `43` lines (`1436` bytes)

**Functions:**
- `def panel(canvas, x, y, width, height, color)` - *Draw a background panel; non-positive sizes are ignored.*
- `def button(canvas, x, y, width, height, label, scale, selected, hovered)` - *Draw one menu button with selected and pointer-hover states.*

---

### [`keystone/web/__init__.py`](keystone/web/__init__.py)
> *Local web console and JSON API for Keystone.*

**Size**: `19` lines (`673` bytes)

**Functions:**
- `def __getattr__(name)`

---

### [`keystone/web/editor.py`](keystone/web/editor.py)
> *Scene-editor helpers for the local web console.*

**Size**: `3238` lines (`115466` bytes)

**Classes:**
- `class _HistoryEntry`
- `class EditorHistory` - *Bounded, named in-memory undo/redo for scene and environment edits.*
  - Method `.__init__(limit)`
  - Method `.describe()`
  - Method `.apply(scene, operation, label)` - *Run one scene mutation and push its labeled pre-edit snapshot.*
  - Method `.undo(scene, steps)` - *Restore up to `steps` earlier states and return how many were undone.*
  - Method `.redo(scene, steps)` - *Restore up to `steps` redone states and return how many were redone.*
  - Method `.clear()`
  - Method `.rebind_assets(replacements)` - *Swap reloaded asset payloads in every undo and redo snapshot.*
  - Method `.clear_payloads(payload_ids)` - *Remove forgotten payloads from every undo and redo snapshot.*
  - Method `.count_payloads(payload_ids)` - *Count payload references held by undo and redo snapshots.*
  - Method `._push(entry)`
  - Method `._append_undo(entry)`

**Functions:**
- `def _finite_array(value, length, label)`
- `def _node_name(value, default)`
- `def _node_id(value)`
- `def _node_tags(value)`
- `def _transform_from_payload(payload, current)`
- `def _finite_number(value, label)`
- `def _payload_vec3(value, label)`
- `def _unknown_keys(payload, allowed, label)`
- `def _vec3_list(value)`
- `def scene_settings_document(scene)` - *Return JSON-safe camera and environment settings for the editor.*
- `def set_scene(scene, payload)` - *Update camera and/or environment settings after full validation.*
- `def _type_name(value)`
- `def component_schemas(component_types)` - *Return JSON-safe field hints for every game component type.*
- `def _texture_preview(texture, max_size)`
- `def _texture_metadata(texture)`
- `def _asset_metadata(registry, kind, payload)`
- `def asset_entries(registry)` - *Return the registry's JSON-safe asset inventory for the editor.*
- `def _payload_id(registry, payload, kind)`
- `def _asset_payload(registry, value, kind, label)`
- `def _node_snapshot(node)`
- `def _snapshot_nodes(scene)`
- `def _node_from_snapshot(data)`
- `def _restore_nodes(scene, snapshot)`
- `def _clear_node_payloads(node, payload_ids)`
- `def clear_clipboard_payloads(clipboard, payload_ids)` - *Remove forgotten payloads from the selection clipboard.*
- `def _count_node_payloads(node, payload_ids)`
- `def count_prefab_payloads(prefab, payload_ids)` - *Count matching payload references in one detached prefab or clipboard.*
- `def _rebind_snapshot_nodes(nodes, replacements)`
- `def _count_snapshot_payloads(nodes, payload_ids)`
- `def _clear_snapshot_payloads(nodes, payload_ids)`
- `def _scene_snapshot(scene)`
- `def _restore_scene_state(scene, snapshot)`
- `def reload_scene_assets(scene, registry, history, prefabs, clipboard)` - *Reload file-backed assets and rebind scene, history, prefab and clipboard payloads.*
- `def _key_time(value)`
- `def _key_value(channel, value)`
- `def _channel_tracks(clip, channel)`
- `def _replace_channel(clip, channel, tracks)`
- `def _validate_clip_key(clip, node_id, channel, time)`
- `def set_clip_key(clip, node_id, channel, time, value)` - *Insert or replace one keyframe in a clip and return the new clip.*
- `def remove_clip_key(clip, node_id, channel, time)` - *Remove one keyframe within epsilon and return the clip and removal count.*
- `def clip_key_count(clip, node_id, channel)` - *Return the number of keys on one node/channel track.*
- `def _history_label(label)`
- `def _history_steps(steps)`
- `def _component_documents(node)`
- `def _node_locked(node, locked_ids)` - *Whether a node or one of its ancestors is currently locked.*
- `def node_document(node, selected_id, registry, selected_ids, locked_ids)`
- `def editor_document(scene, selected_id, prefabs, history, prefab_entries, scene_entries, registry, assets, component_types, component_schema_documents, play_state, diff, trash, selected_ids, prefab_edit, locked_ids)`
- `def find_node(scene, node_id)`
- `def create_node(scene, payload, parent, registry)` - *Create, validate and attach one node from an editor payload.*
- `def delete_node(scene, node)` - *Detach one node subtree or its whole prefab instance and return the parent.*
- `def duplicate_node(scene, node, name)` - *Clone one node subtree as a sibling with fresh scene-allocated ids.*
- `def reparent_node(scene, node, parent)` - *Move one node subtree or its whole prefab instance below a new parent.*
- `def transform_from_payload(node, payload)`
- `def set_node_properties(node, payload)` - *Update a node's name, visibility, tags or layer atomically.*
- `def set_component(node, type_name, data, component_types)` - *Decode and add/replace one component on a node.*
- `def remove_component(node, type_name, component_types)` - *Remove one named component from a node.*
- `def assign_assets(node, payload, registry)` - *Assign or clear a node's mesh/material through registry asset ids.*
- `def validate_scene(scene, prefabs, registry)` - *Return structured errors and warnings for one authored scene.*
- `def save_prefab(scene, node, name, prefabs)`
- `def save_prefab_nodes(nodes, name, prefabs)` - *Capture top-level selected roots as one multi-root prefab.*
- `def _next_instance_prefix(scene, name)`
- `def _prefab_instance_roots(scene, link)`
- `def insert_prefab(scene, prefabs, name, parent, instance, registry)`
- `def revert_prefab_instance(scene, node, prefabs, registry)` - *Replace the linked instance group with a fresh prefab template.*
- `def apply_prefab_instance(scene, node, prefabs, registry)` - *Capture the linked instance group as the new prefab definition.*
- `def seed_prefab_instance_baselines(scene, node, registry)` - *Rebase one applied group after its prefab write succeeds.*
- `def rename_prefab_links(scene, old, new)` - *Point every instance link at a renamed prefab; return the updates made.*
- `def _instance_groups(scene)`
- `def _containing_instance_link(node)`
- `def _node_override_values(node, registry)`
- `def _seed_node_baselines(nodes, registry)` - *Record each supplied node's current values as its override baseline.*
- `def _seed_instance_baselines(roots, registry)` - *Record a fresh instance subtree, including nested groups, as its baseline.*
- `def _instance_nodes(roots)` - *Return instance nodes without descending into nested prefab groups.*
- `def _map_prefab_templates(prefab, roots, link)` - *Map template and instance nodes by their stable id suffix.*
- `def normalize_prefab_edit_ids(scene, link)` - *Give edit-mode nodes unique ids that survive template normalization.*
- `def _ensure_prefab_baselines(scene, prefabs, registry)` - *Seed missing baselines for legacy or hand-built prefab instances.*
- `def _capture_instance_overrides(roots, registry)` - *Capture field values that differ from each node's stored baseline.*
- `def _apply_override_value(node, field, value, component, registry)` - *Apply one captured override field to a freshly instantiated node.*
- `def _apply_instance_overrides(nodes_by_id, captured, registry)` - *Reapply captured overrides after a refresh; return preserved/dropped.*
- `def _update_baseline_field(scene, prefab_name, template_id, field, value)` - *Move affected instance baselines to the value just applied to a prefab.*
- `def prefab_override_document(scene, prefabs, registry)` - *Return field-level diffs for every linked scene instance group.*
- `def refresh_prefab_instances(scene, prefabs, name, registry, keep_overrides, is_locked)` - *Replace top-level instance groups with the current template.*
- `def _node_path(roots, target)`
- `def _follow_path(roots, path)`
- `def _resolve_prefab_override(scene, node_id, field, prefabs, registry)`
- `def _copy_node_field(source, target, field)`
- `def revert_prefab_override(scene, node_id, field, prefabs, registry)` - *Restore one field on a linked instance from its prefab template.*
- `def apply_prefab_override(scene, node_id, field, prefabs, registry)` - *Return a template copy with one instance field applied to it.*
- `def _clone_scene_node(node)`
- `def scene_group_document(scene)` - *Return one JSON-safe entry for every additive scene group container.*
- `def _rename_colliding_ids(node, used)`
- `def add_scene(scene, name, library, parent)` - *Add one saved scene as a named child group of the current scene.*
- `def unload_scene(scene, node)` - *Remove one scene group container and return its former parent.*
- `def _copy_scene_settings(source, target)`
- `def save_scene_group(scene, node, library, name)` - *Write one scene group's children, settings and transform back to a library scene.*
- `def _top_level_selected(scene, ids)`
- `def _parent_linear_inverse(node)`
- `def _world_position(node)`
- `def _quat_from_basis(x, y, z)`
- `def _parent_rotation(node)`
- `def _world_to_local_position(node, position)`
- `def _apply_group_transform(node, pivot, rotation, scale)`
- `def transform_selection(scene, ids, payload)` - *Apply world position delta, local deltas, or a centroid group transform.*
- `def toggle_selection_visible(scene, ids)` - *Flip the visibility of every selected node in one operation.*
- `def delete_selection(scene, ids)` - *Delete all top-level selected nodes and return a surviving parent.*
- `def _selected_nodes(scene, ids)`
- `def set_selection_properties(scene, ids, payload)` - *Apply the same name/visible/tags/layer values to every selected node.*
- `def set_selection_transform(scene, ids, payload)` - *Apply the same absolute local transform values to every selected node.*
- `def _shared_field(values)`
- `def selection_summary(scene, ids)` - *Return shared versus mixed inspector values for the selection set.*

---

### [`keystone/web/scene.py`](keystone/web/scene.py)
> *Export a game-agnostic scene as a JSON document for the browser viewer.*

**Size**: `162` lines (`5827` bytes)

**Functions:**
- `def _enabled(value)`
- `def _floats(values)`
- `def _mesh_document(mesh)`
- `def _texture_document(texture)`
- `def scene_document(scene, game)` - *Serialize one scene into a deterministic, viewer-ready document.*

---

### [`keystone/web/schema.py`](keystone/web/schema.py)
> *Versioned schemas shared by the web API, AI clients and the browser viewer.*

**Size**: `651` lines (`27053` bytes)

---

### [`keystone/web/server.py`](keystone/web/server.py)
> *A localhost JSON API and static web console for the game-agnostic engine.*

**Size**: `2995` lines (`134366` bytes)

**Classes:**
- `class WebProblem` - *One client-facing error with an actionable fix.*
  - Method `.__init__(status, why, fix)`
- `class GameSession` - *One in-memory game guarded by a lock for concurrent HTTP requests.*
  - Method `.__init__(game, prefab_dir, scene_dir, animation_dir, material_dir, initial_scene, project_dir)`
  - Property `.name`
  - Property `.selected_ids`
  - Method `.selected_ids(value)`
  - Method `._set_selected_ids(ids)`
  - Property `.selected_id`
  - Method `.selected_id(value)`
  - Method `.describe()`
  - Method `.simulate(frames, actions, step, trace)`
  - Method `._scene_locked()`
  - Method `.scene()`
  - Method `._registry_locked()`
  - Method `._node_locked_locked(node)`
  - Method `._ensure_unlocked_locked(nodes)`
  - Method `._ensure_subtree_unlocked_locked(nodes)`
  - Method `._document_asset_ids(value, ids)` - *Collect mesh/material/texture ids from one scene document.*
  - Method `._format_asset_usage(report)`
  - Method `._asset_usage_report_locked(scene, registry, asset_id)` - *Return structured references to one asset across live and saved content.*
  - Method `._parent_locked(scene, value)`
  - Method `._prefab_entries_locked()`
  - Method `._history_label_for(action, payload)`
  - Method `._apply_history(scene, operation)`
  - Method `._batch_locked(scene, payload)`
  - Method `._prefab_edit_document()`
  - Method `._edit_prefab_locked(name)`
  - Method `._save_prefab_edit_locked(scene)`
  - Method `._close_prefab_edit_locked(scene, save)`
  - Method `._persist_prefab_locked(name, prefab, previous)`
  - Method `._ensure_prefab_locked(name)`
  - Method `._lifecycle_state()`
  - Method `._play_state_locked()`
  - Method `._editor_locked(scene)`
  - Method `.editor()`
  - Method `.editor_action(payload)`
  - Method `.inspector()`
- `class KeystoneHTTPServer` - *Threaded server carrying one game session for the request handler.*
  - Method `.__init__(address, session)`
  - Method `.handle_error(request, client_address)`
- `class ConsoleHandler` - *Serve the API and the bundled static console.*
  - Method `.log_message(format, *args)`
  - Method `.do_OPTIONS()`
  - Method `.do_HEAD()`
  - Method `.do_GET()`
  - Method `.do_POST()`
  - Method `.do_PUT()`
  - Method `.do_PATCH()`
  - Method `.do_DELETE()`
  - Property `.session`
  - Method `._index()`
  - Method `._health()`
  - Method `._read_json()`
  - Method `._send_file(name)`
  - Method `._send_problem(problem)`
  - Method `._method_not_allowed()`
  - Method `._send_json(status, payload, extra_headers)`
  - Method `._send(status, body, content_type, extra_headers)`

**Functions:**
- `def _copy_scene_settings(source, target)` - *Copy camera and environment settings without copying scene nodes.*
- `def _enabled(value)`
- `def _action_fix(message)` - *Turn one editor-action failure into the fix that actually applies.*
- `def create_server(game, host, port, prefab_dir, scene_dir, animation_dir, material_dir, initial_scene, project_dir)` - *Create a bound server; port 0 asks the OS for a free port.*
- `def serve(game, host, port, prefab_dir, scene_dir, animation_dir, material_dir, initial_scene, project_dir)` - *Run the local console until interrupted.*

---

### [`tests/support_maze_game.py`](tests/support_maze_game.py)
> *Deterministic grid stub used to prove the bot playtester end to end.*

**Size**: `230` lines (`7021` bytes)

**Classes:**
- `class MazeGame` - *A deterministic grid chase: reach the goal cell before the clock.*
  - Method `.__init__(config)`
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`

**Functions:**
- `def _step(value)`
- `def maze_shortest_path(config)` - *Exact grid BFS ground truth: steps from spawn to goal, or None.*
- `def reachable(config)` - *Fixture-side exact reachability used as fairness ground truth.*
- `def open_config(width, height, time_limit)`
- `def walled_goal_config()` - *Goal fully surrounded: provably unwinnable.*
- `def hazard_spawn_config()` - *Spawn sits on a hazard: terminal loss on frame zero.*
- `def tight_clock_config()` - *Shortest path needs 8 steps; the clock allows 3.*
- `def optimal_actions(config)` - *Greedy reference solution: shortest-path actions, or empty when unreachable.*
- `def Factory(config)`
- `def FairMaze()`
- `def WalledMaze()`
- `def HazardMaze()`
- `def TightMaze()`

---

### [`tests/support_policy.py`](tests/support_policy.py)
> *A tiny external policy used to prove --policy accepts module factories.*

**Size**: `20` lines (`518` bytes)

**Classes:**
- `class SupportPolicy` - *A named random policy registered from outside the engine.*

**Functions:**
- `def make_policy()` - *Factory form, matching the ``module:Factory`` spec.*

---

### [`tests/test_agents.py`](tests/test_agents.py)
> *Tests for AI observation/action adapters, audit trail and input bindings.*

**Size**: `109` lines (`4287` bytes)

**Classes:**
- `class AgentsTest`
  - Method `.test_parse_actions_validates_and_clamps()`
  - Method `.test_observe_is_deterministic_and_auditable()`
  - Method `.test_summarize_report_truncates_and_keeps_pbr()`
  - Method `.test_audit_trail_appends_and_verifies()`
  - Method `.test_audit_trail_loads_and_detects_truncation()`
  - Method `.test_observe_builds_scene_before_snapshot()`
  - Method `.test_input_bindings_round_trip()`

---

### [`tests/test_analysis.py`](tests/test_analysis.py)
> *Tests for the machine-readable frame report.*

**Size**: `345` lines (`14832` bytes)

**Classes:**
- `class Health`
- `class AnalysisTest`
  - Method `.test_pixel_stats_and_content_bbox()`
  - Method `.test_a_surface_crossing_the_near_plane_keeps_a_real_bbox()` - *A floor under the camera must not collapse to a zero-height line.*
  - Method `.test_scene_nodes_have_projected_screen_bounds()`
  - Method `.test_node_on_the_projection_plane_stays_in_the_report()`
  - Method `.test_material_and_texture_metadata_are_reported()`
  - Method `.test_scene_identity_metadata_is_reported()`
  - Method `.test_png_hash_and_atomic_report()`
  - Method `.test_compare_reports_detects_image_and_stats_changes()`
  - Method `.test_ui_metadata_is_hashed_and_compared()`
  - Method `.test_compare_reports_accepts_older_schemas()`
  - Method `.test_compare_reports_detects_identity_metadata_changes()`
  - Method `.test_compare_reports_distinguishes_duplicate_names_by_id()`
  - Method `.test_compare_reports_detects_material_changes()`
  - Method `.test_compare_reports_rejects_unknown_schema()`
  - Method `.test_pixel_diff_writes_an_artifact_and_stats()`
  - Method `.test_pixel_diff_rejects_dimension_mismatch()`
  - Method `.test_rejects_bad_pixel_count()`
  - Method `.test_grid_luma_uses_per_cell_counts()`
  - Method `.test_compare_detects_world_and_triangle_changes()`
  - Method `.test_report_schema_does_not_advertise_missing_diagnostics()`
  - Method `.test_falsy_settings_report_disabled()`
  - Method `.test_pixel_diff_detects_alpha_only_changes()`

---

### [`tests/test_animation.py`](tests/test_animation.py)
> *Tests for deterministic animation clips, controllers and pose application.*

**Size**: `355` lines (`14716` bytes)

**Classes:**
- `class TrackTest`
  - Method `.test_linear_interpolation()`
  - Method `.test_step_interpolation()`
  - Method `.test_validation()`
  - Method `.test_quat_slerp_endpoints()`
  - Method `.test_json_round_trip()`
- `class ClipControllerTest`
  - Method `._clip()`
  - Method `.test_clip_sample_and_duration()`
  - Method `.test_apply_pose_mask_keeps_simulation_owned_channels()` - *A game that simulates position must be able to animate rotation only.*
  - Method `.test_apply_pose_mask_rejects_bad_input()`
  - Method `.test_controller_loops_and_applies()`
  - Method `.test_zero_time_event_fires_on_first_advance_only()`
  - Method `.test_crossfade_from_empty_clip_completes()`
  - Method `.test_unknown_clip_rejected()`
  - Method `.test_events_fire_once_per_crossing()`
  - Method `.test_play_clears_a_caller_supplied_pose_provider()`
  - Method `.test_crossfade_blends_deterministically()`
- `class MergeTest`
  - Method `.test_merge_bakes_static_groups()`
  - Method `.test_merge_excludes_animated_nodes()`
- `class ClipDurationTest`
  - Method `.test_duration_ignores_far_event_when_tracks_exist()`
  - Method `.test_event_only_clip_keeps_event_duration()`
  - Method `.test_duplicate_keyframe_times_rejected()`
- `class AnimationValidationTest`
  - Method `.test_exact_loop_wrap_fires_end_event()`
  - Method `.test_channel_value_type_must_match_channel()`
  - Method `.test_track_rejects_non_finite_values_and_zero_quaternion()`
  - Method `.test_clip_round_trip_is_object_equal_with_unsorted_tracks()`
  - Method `.test_blank_or_non_string_node_ids_are_rejected()`
  - Method `.test_non_finite_time_and_dt_are_rejected()`
  - Method `.test_malformed_track_vectors_raise_value_error()`

**Functions:**
- `def _vec_track(pairs)`

---

### [`tests/test_animation_blend.py`](tests/test_animation_blend.py)
> *Unit tests for deterministic 1D animation blend spaces.*

**Size**: `116` lines (`4050` bytes)

**Classes:**
- `class BlendSpaceTest`
  - Method `.test_samples_and_clamps_parameter()`
  - Method `.test_single_sample_and_reverse_order()`
  - Method `.test_round_trip_and_report()`
  - Method `.test_validation()`

**Functions:**
- `def _clip(name, x)`

---

### [`tests/test_animation_library.py`](tests/test_animation_library.py)
> *Tests for file-backed animation clip libraries.*

**Size**: `44` lines (`1715` bytes)

**Classes:**
- `class AnimationLibraryTest`
  - Method `.test_save_load_entries_delete_and_restore()`
  - Method `.test_invalid_name_and_missing_entries()`

---

### [`tests/test_animation_state.py`](tests/test_animation_state.py)
> *Tests for deterministic parameter-driven animation state machines.*

**Size**: `487` lines (`17021` bytes)

**Classes:**
- `class AnimationStateMachineTest`
  - Method `.test_parameter_transition_and_state_settings()`
  - Method `.test_trigger_transition_and_events()`
  - Method `.test_states_with_same_clip_name_keep_distinct_payloads()`
  - Method `.test_zero_speed_target_still_completes_crossfade()`
  - Method `.test_crossfade_blending_finishes()`
  - Method `.test_serialization_round_trip_and_report()`
  - Method `.test_blend_space_state_samples_parameter_and_round_trips()`
  - Method `.test_blend_space_state_loops_like_a_plain_state()`
  - Method `.test_non_looping_blend_space_state_holds_the_last_frame()`
  - Method `.test_crossfade_into_a_blend_state_targets_the_blended_pose()`
  - Method `.test_blend_space_loops_at_its_own_longest_clip()`
  - Method `.test_crossfade_out_of_a_blend_state_blends_its_sampled_pose()`
  - Method `.test_validation_rejects_bad_shapes()`
  - Method `.test_available_transitions_and_play_errors()`
  - Method `.test_parameter_can_be_added_after_construction()`

**Functions:**
- `def _clip(name, offset, events)`
- `def _machine(duration)`

---

### [`tests/test_app.py`](tests/test_app.py)
> *Tests for the game-agnostic engine loop and CLI.*

**Size**: `658` lines (`26326` bytes)

**Classes:**
- `class HudCube`
  - Method `.draw_ui(canvas, _state)`
- `class BindCube`
  - Method `.__init__()`
  - Method `.bind_input(mapping)`
- `class BadBindCube`
  - Method `.bind_input(mapping)`
- `class SlotCube`
  - Method `.bind_input(mapping)`
  - Method `.actions()`
- `class UnboundCube`
  - Method `.actions()`
- `class EngineTest`
  - Method `.test_engine_lets_the_game_bind_its_own_controls()`
  - Method `.test_a_failing_bind_hook_does_not_leave_the_engine_half_open()`
  - Method `.test_a_game_without_the_bind_hook_keeps_the_defaults()`
  - Method `.test_engine_reports_dead_key_names()`
  - Method `.test_engine_binds_number_keys_and_reports_no_gaps()`
  - Method `.test_engine_reports_declared_buttons_with_no_binding()`
  - Method `.test_headless_engine_runs_fixed_steps_and_saves_a_png()`
  - Method `.test_ui_capture_alpha_is_opaque()`
  - Method `.test_ui_overlay_changes_the_captured_frame()`
  - Method `.test_pause_stops_updates_but_keeps_rendering()`
  - Method `.test_ui_actions_are_drivable_without_real_input()`
  - Method `.test_game_ui_hook_adds_pixels_to_the_capture()`
  - Method `.test_bad_size_is_a_usage_error()`
  - Method `.test_out_requires_headless()`
  - Method `.test_ui_flags_are_limited_to_rendered_runs()`
  - Method `.test_replay_cli_replays_a_log_without_opening_a_window()`
  - Method `.test_serve_is_a_standalone_web_command()`
  - Method `.test_windowless_commands_reject_window_flags()`
  - Method `.test_web_flags_require_serve()`
  - Method `.test_scene_startup_requires_a_library()`
  - Method `.test_validate_project_requires_project()`
  - Method `.test_scene_is_rejected_with_describe()`
  - Method `.test_bad_web_port_is_a_usage_error()`
  - Method `.test_headless_ui_capture_writes_a_report()`
  - Method `.test_start_paused_headless_report_describes_the_menu()`
  - Method `.test_bad_game_spec_reports_why_and_fix()`
  - Method `.test_describe_cli_prints_capabilities_without_opening_a_window()`
  - Method `.test_verify_determinism_cli_is_gpu_free()`
  - Method `.test_expect_hash_gate_matches_and_rejects()`
  - Method `.test_invalid_expected_hash_is_a_usage_error()`
  - Method `.test_simulate_cli_prints_json_without_opening_a_window()`
  - Method `.test_simulate_cli_reads_actions_and_writes_output()`
  - Method `.test_compare_baseline_cli_exits_zero_and_writes_diff()`
  - Method `.test_capture_report_and_png()`
- `class CleanupAndCliTest`
  - Method `.test_close_closes_context_when_release_raises()`
  - Method `.test_version_flag_prints_the_release_and_is_standalone()`
  - Method `.test_standalone_commands_reject_irrelevant_flags()`
  - Method `.test_zero_frames_is_rejected_instead_of_silently_defaulted()` - *`--frames 0` must fail: every mode used a falsy check and ran 1 or 120.*
- `class _CadenceContext`
  - Method `.__init__(times, keys, pointer_step, press_from)`
  - Method `.should_close()`
  - Method `.poll_events()`
  - Method `.framebuffer_size()`
  - Method `.time()`
  - Method `.key_down(name)`
  - Method `.mouse_down(button)`
  - Method `.cursor_position()`
  - Method `.swap_buffers()`
  - Method `.set_title(title)`
  - Method `.set_cursor_captured(captured)`
  - Method `.request_close()`
- `class _CadenceRenderer`
  - Method `.render(scene, particles)`
- `class _CadenceRecorder`
  - Method `.__init__()`
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`
- `class InputCadenceTest`
  - Method `._engine(times, keys, pointer_step, press_from)`
  - Method `.test_look_delta_is_frame_rate_independent()`
  - Method `.test_pressed_edge_survives_zero_step_frames()`
  - Method `.test_pause_menu_mouse_click_resumes()`

---

### [`tests/test_assets.py`](tests/test_assets.py)
> *Unit tests for the asset registry: identity, digests and dependencies.*

**Size**: `696` lines (`30804` bytes)

**Classes:**
- `class PrefabHealth`
- `class AssetRegistryTest`
  - Method `.setUp()`
  - Method `.test_register_infers_kind_and_preserves_order()`
  - Method `.test_register_rejects_bad_ids_kinds_and_payloads()`
  - Method `.test_duplicate_id_requires_replace()`
  - Method `.test_digest_is_content_based_and_duplicates_are_reported()`
  - Method `.test_texture_and_material_digests_follow_their_content()`
  - Method `.test_mesh_digest_covers_skinning()`
  - Method `.test_dependencies_are_sorted_and_missing_ones_reported()`
  - Method `.test_stats_and_describe_are_json_safe()`
  - Method `._prefab_fixture()`
  - Method `.test_prefab_kind_digest_and_dependencies()`
  - Method `.test_prefab_rejects_unregistered_payloads()`
  - Method `.test_public_package_exports_the_registry()`
  - Method `.test_remove_and_clear_dispose_records()`
- `class AssetFileSourceTest`
  - Method `.test_register_file_uses_suffix_and_records_source()`
  - Method `.test_register_file_requires_kind_or_known_suffix()`
  - Method `.test_refresh_reports_unchanged()`
  - Method `.test_refresh_reloads_changed_texture()`
  - Method `.test_reload_rebinds_live_scene_nodes()` - *A plain consumer must not keep stale geometry after a reload.*
  - Method `.test_reload_rejects_a_non_scene_target()`
  - Method `.test_reload_without_a_scene_still_refreshes()`
  - Method `.test_reload_reports_zero_rebound_when_nothing_changed()`
  - Method `.test_refresh_failure_keeps_last_good_payload()`
  - Method `.test_refresh_missing_then_recovers()`
  - Method `.test_refresh_reports_loader_type_error()`
  - Method `.test_dependencies_survive_refresh()`
  - Method `.test_prefab_suffix_and_default_loader()`
  - Method `.test_register_prefab_file_and_refresh()`
  - Method `.test_refresh_reloads_dependencies_before_dependants()`
  - Method `.test_refresh_orders_new_prefab_dependencies_first()`
  - Method `.test_refresh_orders_new_material_texture_edges_first()`
  - Method `.test_register_prefab_file_with_component_types()`
  - Method `.test_prefab_file_requires_registered_assets()`
  - Method `.test_clear_and_remove_drop_sources()`

**Functions:**
- `def _touch(path)`

---

### [`tests/test_audio.py`](tests/test_audio.py)
> *Tests for the game-agnostic audio core.*

**Size**: `215` lines (`8767` bytes)

**Classes:**
- `class AudioTest`
  - Method `.test_synth_clips_are_deterministic()`
  - Method `.test_noise_rejects_nonint_seed_to_keep_determinism()`
  - Method `.test_validation_rejects_bad_params()`
  - Method `.test_mixer_applies_buses_and_renders()`
  - Method `.test_mix_clips_requires_shared_rate()`
  - Method `.test_mix_clips_clamps_once_at_the_end()`
  - Method `.test_wav_round_trip_preserves_negative_and_positive_symmetry()` - *A clip must decode with the same scale on both signs.*
  - Method `.test_wav_round_trip()`
  - Method `.test_clip_json_round_trip()`
  - Method `.test_read_wav_accepts_full_scale_negative()`
  - Method `.test_master_bus_applies_once()`
  - Method `.test_play_rejects_unknown_bus()`
  - Method `.test_non_finite_audio_values_are_rejected()`
  - Method `.test_audio_clip_normalizes_samples_and_rate()`
  - Method `.test_removed_bus_mutes_instead_of_full_gain()`
  - Method `.test_mix_clips_rejects_runaway_pitch()`
  - Method `.test_mix_clips_rejects_none()`
  - Method `.test_read_wav_rejects_truncated_payload()`

---

### [`tests/test_batch.py`](tests/test_batch.py)
> *Tests for the static batch planner and inspector endpoint.*

**Size**: `94` lines (`4047` bytes)

**Classes:**
- `class BatchTest`
  - Method `.test_plan_metrics_name_what_they_count()` - *`draw_calls` in a plan is a node count, so it must say so.*
  - Method `.test_shared_meshes_batch_into_few_groups()`
  - Method `.test_cube_demo_plan_reports_savings()`
  - Method `.test_merge_savings_respect_exclude()`
  - Method `.test_non_material_payloads_use_the_renderer_default()`
- `class InspectorEndpointTest`
  - Method `.test_inspector_returns_batches_and_audio()`

---

### [`tests/test_bloom.py`](tests/test_bloom.py)
> *Tests for the deterministic bloom glow (in-shader luminance threshold).*

**Size**: `200` lines (`7865` bytes)

**Classes:**
- `class BloomMathTest`
  - Method `.test_constants_are_fixed()`
  - Method `.test_blur_size_uses_floor_half_with_min_one()`
  - Method `.test_composite_adds_and_clamps()`
  - Method `.test_dark_has_no_bloom_and_bright_saturates()`
  - Method `.test_bloom_adds_proportionally_and_clamps()`
- `class BloomContractsTest`
  - Method `.test_bloom_settings_default_enabled()`
  - Method `.test_describe_reports_bloom()`
  - Method `.test_report_includes_bloom_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_bloom()`
  - Method `.test_compare_accepts_legacy_without_bloom()`
  - Method `.test_snapshot_round_trips_bloom_flag()`
  - Method `.test_scene_document_and_inspector_expose_bloom()`
- `class BloomDiffusionIntegrationTest`
  - Method `._render_cube(bloom_on, width, height)`
  - Method `.test_diffusion_changes_pixels_without_new_draws()`
  - Method `.test_no_bloom_legacy_path_is_stable()`
  - Method `.test_resize_recreates_diffusion_buffers()`

---

### [`tests/test_boundary.py`](tests/test_boundary.py)
> *Boundary test: the engine core contains no game rules or imports.*

**Size**: `65` lines (`2391` bytes)

**Classes:**
- `class CoreBoundaryTest`
  - Method `.test_core_has_no_genre_modules()`
  - Method `.test_core_does_not_import_the_web_adapter()`
  - Method `.test_core_imports_only_core_modules()`

---

### [`tests/test_broadphase.py`](tests/test_broadphase.py)
> *Tests for the deterministic spatial-grid broadphase.*

**Size**: `78` lines (`3362` bytes)

**Classes:**
- `class SpatialGridTest`
  - Method `.test_query_returns_true_overlaps_in_insertion_order()`
  - Method `.test_same_cell_candidates_are_still_filtered()`
  - Method `.test_update_moves_a_proxy_and_remove_deletes_it()`
  - Method `.test_negative_coordinates_and_large_boxes_use_multiple_cells()`
  - Method `.test_enormous_proxy_is_rejected_instead_of_hanging()`
  - Method `.test_pairs_are_unique_and_ordered_by_insertion()`
  - Method `.test_clear_and_validation()`

---

### [`tests/test_character.py`](tests/test_character.py)
> *Tests for the AABB character controller.*

**Size**: `177` lines (`8541` bytes)

**Classes:**
- `class CharacterControllerTest`
  - Method `.test_body_exposes_its_collision_box()`
  - Method `.test_character_falls_and_rests_on_a_floor()`
  - Method `.test_character_stops_at_a_wall_without_tunneling()`
  - Method `.test_jump_leaves_the_ground()`
  - Method `.test_character_rejects_invalid_configuration_and_step()`
  - Method `.test_character_steps_onto_a_low_step()`
  - Method `.test_character_stops_at_a_tall_step()`
  - Method `.test_platform_carry_pushes_out_of_a_wall()`
  - Method `.test_platform_carry_does_not_move_an_airborne_body()`
  - Method `.test_zero_gravity_body_is_not_grounded_without_a_floor()`
  - Method `.test_platform_carry_off_a_ledge_then_falls()`
  - Method `.test_wall_slide_does_not_double_step_or_report_blocked_velocity()`
  - Method `.test_step_up_preserves_the_full_horizontal_delta_once()`
  - Method `.test_overlapping_start_depenetrates_to_the_nearest_face()`
  - Method `.test_character_rejects_non_finite_inputs()`
  - Method `.test_character_steps_are_deterministic()`

---

### [`tests/test_cli_failure_advice.py`](tests/test_cli_failure_advice.py)
> *A CLI failure must name the action that actually failed.*

**Size**: `157` lines (`6995` bytes)

**Classes:**
- `class CliFailureAdviceTest`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `.test_startup_failure_blames_the_game_factory()`
  - Method `.test_project_start_failure_points_at_keystone_json()` - *With --project the caller never typed a factory string.*
  - Method `.test_corrupt_baseline_names_the_report_not_the_game()`
  - Method `.test_mismatched_diff_dimensions_advise_matching_sizes()`
  - Method `.test_baseline_gate_still_keys_on_pixels()`
  - Method `.test_a_real_change_fails_the_gate_and_writes_a_diff()`

**Functions:**
- `def run(args, timeout, cwd)`

---

### [`tests/test_clock.py`](tests/test_clock.py)
> *Tests for the fixed-step clock.*

**Size**: `44` lines (`1425` bytes)

**Classes:**
- `class FixedStepClockTest`
  - Method `.test_releases_whole_steps_and_bounds_catch_up()`
  - Method `.test_reset_drops_accumulator()`
  - Method `.test_invalid_configuration()`
  - Method `.test_backwards_time_mints_no_debt()`
  - Method `.test_non_finite_time_is_rejected()`

---

### [`tests/test_component_codec.py`](tests/test_component_codec.py)
> *Tests for the shared typed-component JSON codec.*

**Size**: `113` lines (`4116` bytes)

**Classes:**
- `class Health`
- `class ComponentCodecTest`
  - Method `.test_dataclass_round_trip()`
  - Method `.test_primitive_round_trips()`
  - Method `.test_from_dict_rejects_unknown_type_fields()`
  - Method `.test_from_dict_rejects_unknown_document_keys()`
  - Method `.test_from_dict_requires_type_and_data()`
  - Method `.test_from_dict_requires_a_type_map()`
  - Method `.test_from_dict_rejects_unknown_component_type()`
  - Method `.test_to_dict_rejects_an_unserializable_object()`
  - Method `.test_json_safe_rejects_non_finite_and_opaque_values()`
  - Method `.test_validate_component_types_copies_and_rejects_bad_input()`

---

### [`tests/test_culling.py`](tests/test_culling.py)
> *Tests for deterministic CPU view-frustum culling (color pass only).*

**Size**: `223` lines (`8851` bytes)

**Classes:**
- `class CullingMathTest`
  - Method `.test_planes_are_deterministic()`
  - Method `.test_degenerate_frustum_raises()`
  - Method `.test_aabb_touching_plane_is_visible()`
  - Method `.test_world_bounds_follow_translation()`
  - Method `.test_skinned_nodes_are_always_visible()`
- `class CullingSceneTest`
  - Method `.test_front_visible_behind_and_offside_culled()`
  - Method `.test_cull_scene_keeps_front_only()`
  - Method `.test_disabled_culling_returns_everything_visible()`
  - Method `.test_default_enabled()`
  - Method `.test_cull_scene_rejects_bad_size()`
- `class CullingGroupingAgreementTest`
  - Method `.test_group_instances_planes_match_cull_scene()`
  - Method `.test_group_instances_without_planes_is_legacy()`
- `class CullingContractsTest`
  - Method `.test_describe_reports_culling()`
  - Method `.test_public_api_exports_culling_helpers()`
  - Method `.test_report_includes_culling_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_culling()`
  - Method `.test_compare_accepts_legacy_without_culling()`
  - Method `.test_compare_accepts_schema_10_baseline()`
  - Method `.test_snapshot_round_trips_culling_flag()`

**Functions:**
- `def _scene_with_cubes()`
- `def _skinned_quad()`

---

### [`tests/test_export.py`](tests/test_export.py)
> *Tests for deterministic project export bundles.*

**Size**: `148` lines (`6207` bytes)

**Classes:**
- `class ProjectExportTest`
  - Method `.test_export_bundle_structure_hashes_and_launcher()`
  - Method `.test_export_refuses_non_empty_target_and_force_overwrites()`
  - Method `.test_export_cli_and_validation_failures()`
  - Method `.test_export_excludes_development_files_and_nested_target()`

---

### [`tests/test_geometry.py`](tests/test_geometry.py)
> *Unit tests for indexed meshes, built-in primitives and the OBJ loader.*

**Size**: `288` lines (`10779` bytes)

**Classes:**
- `class MeshDataTest`
  - Method `.test_rejects_mismatched_attribute_counts()`
  - Method `.test_rejects_out_of_range_index()`
  - Method `.test_rejects_malformed_position_tuples_at_construction()`
  - Method `.test_bounds_and_counts()`
  - Method `.test_interleaved_has_eleven_floats_per_vertex()`
  - Method `.test_vertex_colors_follow_the_uvs()`
  - Method `.test_rejects_mismatched_vertex_colors()`
- `class PrimitiveTest`
  - Method `.test_cube_normals_are_unit_and_outward()`
  - Method `.test_plane_faces_up_with_six_indices()`
  - Method `.test_sphere_positions_lie_on_radius_and_normals_are_unit()`
  - Method `.test_primitives_reject_invalid_sizes()`
  - Method `.test_cone_and_cylinder_are_unit_and_bounded()`
  - Method `.test_cone_side_normals_point_outward()`
  - Method `.test_cone_winding_matches_stored_normals()`
- `class MeshBuilderTest`
  - Method `.test_box_has_24_vertices_and_36_indices()`
  - Method `.test_quad_normal_follows_winding()`
  - Method `.test_degenerate_quad_is_rejected()`
  - Method `.test_add_mesh_merges_counts_and_offsets()`
  - Method `.test_add_mesh_matrix_uses_inverse_transpose_normals()`
- `class ObjLoaderTest`
  - Method `.test_quad_is_triangulated()`
  - Method `.test_normals_are_computed_when_absent()`
  - Method `.test_authored_normals_are_kept()`
  - Method `.test_negative_indices_are_relative()`
  - Method `.test_missing_file_raises_file_not_found()`
  - Method `.test_bad_index_raises_value_error()`
  - Method `.test_extra_face_slash_is_rejected()`
  - Method `.test_vertex_weight_is_applied()`
  - Method `.test_vertex_junk_is_rejected()`
  - Method `.test_file_round_trip()`
  - Method `.test_bom_prefix_is_stripped()`
- `class MaterialTest`
  - Method `.test_defaults_are_valid()`
  - Method `.test_rejects_negative_specular()`
  - Method `.test_rejects_negative_checker_scale()`
  - Method `.test_mesh_rejects_bool_coordinates()`
  - Method `.test_material_rejects_non_vec3_color()`

---

### [`tests/test_gltf.py`](tests/test_gltf.py)
> *Unit tests for dependency-free glTF 2.0 import.*

**Size**: `308` lines (`13686` bytes)

**Classes:**
- `class GltfImportTest`
  - Method `.test_loads_a_triangle_mesh_and_material()`
  - Method `.test_translation_is_preserved()`
  - Method `.test_loads_from_a_file()`
  - Method `.test_rejects_wrong_version()`
  - Method `.test_rejects_missing_position()`
  - Method `.test_loads_an_embedded_png_texture()`
  - Method `.test_loads_an_external_buffer_file()`
  - Method `.test_registers_assets_when_registry_is_provided()`
  - Method `.test_generated_normals_use_triangle_indices()`
  - Method `.test_normalized_integer_colors_are_converted_to_unit_range()`
  - Method `.test_rejects_non_triangle_primitive_modes()`
  - Method `.test_rejects_unknown_material_indices()`
  - Method `.test_rejects_sparse_accessors_instead_of_silently_zeroing()`
  - Method `.test_rejects_cyclic_node_hierarchies()`
  - Method `.test_loads_a_glb_container()`
  - Method `.test_loads_a_glb_file()`
  - Method `.test_rejects_truncated_glb_data()`
  - Method `.test_rejects_unknown_material_texture_indices()`
  - Method `.test_rejects_negative_accessor_offsets()`
  - Method `.test_rejects_accessor_reads_outside_the_buffer_view()`
  - Method `.test_rejects_negative_accessor_count_without_a_buffer_view()`
  - Method `.test_rejects_float_indices_and_scalar_positions()`
  - Method `.test_reflected_matrix_preserves_the_reflection()`
  - Method `.test_singular_and_non_affine_matrices_are_rejected()`
  - Method `.test_uv_origin_is_converted_from_gltf_top_left()`

**Functions:**
- `def _data_uri(data)`
- `def _glb_bytes(document, binary_chunk)`
- `def _triangle_gltf(*, translation, color, roughness)`

---

### [`tests/test_gltf_import.py`](tests/test_gltf_import.py)
> *Tests for glTF/GLB prefab import and project attachment.*

**Size**: `281` lines (`11640` bytes)

**Classes:**
- `class GltfPrefabImportTest`
  - Method `.test_import_registers_assets_and_saves_a_prefab()`
  - Method `.test_import_replaces_derived_assets_on_reimport()`
  - Method `.test_import_rejects_bad_inputs()`
- `class ProjectGltfEditorImportTest`
  - Method `.test_project_gltf_import_updates_manifest_and_prefab_library()`
  - Method `.test_project_gltf_import_rejects_bad_sources_and_rolls_back()`
  - Method `.test_project_gltf_reimport_failure_restores_replaced_assets()`
- `class ProjectGltfAttachmentTest`
  - Method `.test_project_attachment_imports_gltf_prefab_and_assets()`

**Functions:**
- `def _triangle_gltf()`

---

### [`tests/test_headless.py`](tests/test_headless.py)
> *Tests for no-OpenGL simulation and action scripts.*

**Size**: `188` lines (`6608` bytes)

**Classes:**
- `class HeadlessTest`
  - Method `.test_simulation_advances_without_a_window()`
  - Method `.test_same_script_is_deterministic()`
  - Method `.test_provided_scene_skips_rebuilding()`
  - Method `.test_trace_contains_each_frame()`
  - Method `.test_load_actions_accepts_list_and_object()`
  - Method `.test_load_actions_pins_bad_item_index()`
  - Method `.test_load_actions_rejects_command_logs()`
  - Method `.test_invalid_frames_and_step()`
  - Method `.test_repeated_script_does_not_repeat_edges()`
  - Method `.test_run_simulation_rejects_non_scene_build()`
  - Method `.test_trace_snapshots_are_independent()`
  - Method `.test_load_actions_rejects_non_finite_and_bad_mouse_type()`

---

### [`tests/test_history.py`](tests/test_history.py)
> *Unit tests for bounded undo/redo history.*

**Size**: `81` lines (`2599` bytes)

**Classes:**
- `class HistoryTest`
  - Method `.test_push_undo_redo_restores_values()`
  - Method `.test_new_push_clears_redo_branch()`
  - Method `.test_capacity_drops_oldest_entries()`
  - Method `.test_snapshots_are_deep_copied()`
  - Method `.test_clear_and_empty_behavior()`
  - Method `.test_peek_returns_current_without_moving()`
  - Method `.test_capacity_rejects_non_int()`

---

### [`tests/test_input.py`](tests/test_input.py)
> *Tests for input sampling and action state.*

**Size**: `252` lines (`10447` bytes)

**Classes:**
- `class FakeContext`
  - Method `.__init__()`
  - Method `.key_down(key)`
  - Method `.cursor_position()`
  - Method `.mouse_down(button)`
- `class InputMapTest`
  - Method `.test_unbound_buttons_reports_declared_actions_with_no_binding()`
  - Method `.test_unbound_buttons_counts_bindings_from_every_context()`
  - Method `.test_unbound_buttons_rejects_non_list_input()`
  - Method `.test_unknown_keys_reports_names_a_real_context_cannot_sample()`
  - Method `.test_unknown_keys_rejects_a_bare_string()`
  - Method `.test_axes_and_pressed_edges()`
  - Method `.test_custom_binding()`
  - Method `.test_mouse_delta_feeds_look()`
  - Method `.test_disabled_mouse_ignores_pointer()`
  - Method `.test_mouse_click_is_a_single_frame_edge()`
  - Method `.test_contexts_isolate_menu_and_gameplay()`
  - Method `.test_unbind_survives_context_round_trip()`
  - Method `.test_action_state_round_trip_and_clear()`
  - Method `.test_action_state_rejects_string_pressed_and_bad_pointer()`
  - Method `.test_action_state_rejects_non_finite_and_coerced_values()`
  - Method `.test_context_round_trip_preserves_isolation()`
  - Method `.test_constructor_validates_bindings_and_tuning()`
  - Method `.test_mouse_setter_is_a_noop_when_unchanged()`
  - Method `.test_bind_rejects_blank_context()`
  - Method `.test_from_dict_rejects_non_string_context()`
  - Method `.test_custom_bindings_preserved_in_new_contexts()`
  - Method `.test_from_dict_rejects_blank_action_or_key()`

---

### [`tests/test_input_keys.py`](tests/test_input_keys.py)
> *Tests for the real GL key table exposed to InputMap consumers.*

**Size**: `22` lines (`691` bytes)

**Classes:**
- `class KeyTableTest`
  - Method `.test_number_row_is_bindable_for_slot_actions()`
  - Method `.test_key_names_exposes_the_same_table()`
  - Method `.test_no_two_names_share_one_glfw_code()`

---

### [`tests/test_instancing.py`](tests/test_instancing.py)
> *Game-agnostic tests for hardware-instancing grouping.*

**Size**: `103` lines (`4127` bytes)

**Classes:**
- `class PlanInstancedTest`
  - Method `.test_groups_identical_payloads()`
  - Method `.test_separates_distinct_materials()`
  - Method `.test_skinned_groups_are_not_instanced()`
  - Method `.test_ignores_invisible_and_missing_mesh()`
  - Method `.test_ordering_is_deterministic()`
  - Method `.test_matrices_follow_world_transforms()`
  - Method `.test_empty_scene()`

**Functions:**
- `def make_scene(count, same_material)`

---

### [`tests/test_library_trash.py`](tests/test_library_trash.py)
> *Tests for recoverable library deletes (soft delete and restore).*

**Size**: `166` lines (`6909` bytes)

**Classes:**
- `class LibraryTrashTest`
  - Method `._library(directory)`
  - Method `.test_move_to_trash_relocates_and_hides_the_entry()`
  - Method `.test_trash_entries_is_empty_without_a_trash_directory()`
  - Method `.test_trash_entries_is_stable_and_reports_the_source()`
  - Method `.test_two_deletes_of_the_same_name_do_not_collide()`
  - Method `.test_restore_returns_the_entry_to_the_library()`
  - Method `.test_restore_preserves_dots_in_the_original_name()`
  - Method `.test_restore_rejects_a_path_instead_of_a_file_name()`
  - Method `.test_restore_rejects_a_blank_name()`
  - Method `.test_restore_rejects_a_missing_entry()`
  - Method `.test_restore_rejects_the_wrong_suffix()`
  - Method `.test_restore_never_overwrites_a_live_entry()`
  - Method `.test_restore_uses_the_validator()`

---

### [`tests/test_lifecycle.py`](tests/test_lifecycle.py)
> *Tests for deterministic component start/update/stop lifecycle hooks.*

**Size**: `203` lines (`6438` bytes)

**Classes:**
- `class Alpha`
  - Method `.start(context)`
  - Method `.update(context)`
  - Method `.stop(context)`
- `class Beta`
- `class Plain`
- `class LifecycleTest`
  - Method `.setUp()`
  - Method `._scene()`
  - Method `.test_start_update_stop_order_context_and_counts()`
  - Method `.test_components_added_after_start_begin_on_the_next_tick()`
  - Method `.test_failed_start_stops_components_it_already_started()`
  - Method `.test_components_without_hooks_are_ignored()`
  - Method `.test_lifecycle_hooks_reports_available_methods()`
  - Method `.test_runtime_state_and_dt_validation()`

---

### [`tests/test_material_graph.py`](tests/test_material_graph.py)
> *Unit tests for declarative material graphs.*

**Size**: `185` lines (`6980` bytes)

**Classes:**
- `class MaterialGraphCoreTest`
  - Method `.test_constant_color_and_float_feed_a_material()`
  - Method `.test_checker_node_builds_a_textured_material()`
  - Method `.test_mix_combines_colors()`
  - Method `.test_color_node_accepts_vec3_param()`
  - Method `.test_checker_and_material_accept_vec3_colors()`
  - Method `.test_validation_rejects_cycles_and_bad_graphs()`
  - Method `.test_evaluation_is_deterministic()`
- `class MaterialGraphSerializationTest`
  - Method `.test_round_trip_preserves_evaluation()`
  - Method `.test_texture_node_resolves_by_name()`
  - Method `.test_material_texture_name_must_resolve()`
  - Method `.test_duplicate_parameter_names_are_rejected()`
  - Method `.test_non_finite_parameters_are_rejected_on_serialization()`
  - Method `.test_validate_rejects_cycles()`

**Functions:**
- `def _node(node_id, kind, *, params, inputs)`

---

### [`tests/test_material_library.py`](tests/test_material_library.py)
> *Tests for file-backed material libraries.*

**Size**: `69` lines (`2708` bytes)

**Classes:**
- `class MaterialLibraryTest`
  - Method `.test_save_load_register_and_texture()`
  - Method `.test_delete_trash_and_restore()`
  - Method `.test_invalid_names_and_missing_entries()`

---

### [`tests/test_math3d.py`](tests/test_math3d.py)
> *Unit tests for the Keystone 3D math core.*

**Size**: `147` lines (`5842` bytes)

**Classes:**
- `class Vec3Test`
  - Method `.test_arithmetic_and_dot()`
  - Method `.test_cross_follows_right_hand_rule()`
  - Method `.test_normalized_is_unit_and_zero_safe()`
  - Method `.test_lerp_hits_both_ends()`
  - Method `.test_mul_rejects_vector_operand()`
- `class Mat4Test`
  - Method `.test_identity_leaves_points_and_matrices_unchanged()`
  - Method `.test_translation_and_scale_apply_in_order()`
  - Method `.test_rotation_z_90_degrees()`
  - Method `.test_direction_ignores_translation()`
  - Method `.test_inverse_round_trips_affine_matrix()`
  - Method `.test_inverse_rejects_projective_matrix()`
  - Method `.test_transform_point_rejects_projective_matrix()`
  - Method `.test_perspective_maps_near_and_far_to_ndc()`
  - Method `.test_perspective_rejects_invalid_fov()`
  - Method `.test_look_at_puts_eye_at_origin()`
  - Method `.test_look_at_rejects_degenerate_input()`
  - Method `.test_flat_is_column_major_for_opengl()`
- `class QuatTest`
  - Method `.test_axis_angle_rotates_a_vector()`
  - Method `.test_quaternion_matrix_matches_matrix_rotation()`
  - Method `.test_multiplication_composes_in_order()`
  - Method `.test_slerp_endpoints()`
  - Method `.test_perspective_rejects_non_finite_framing()`

---

### [`tests/test_merge_skin.py`](tests/test_merge_skin.py)
> *Tests for skin-aware batch merging: identical rigs merge into one draw.*

**Size**: `200` lines (`8326` bytes)

**Classes:**
- `class SkinMergeTest`
  - Method `.test_merge_combines_same_rig_groups()`
  - Method `.test_merged_deformation_matches_oracle_exactly()`
  - Method `.test_separates_by_material_joints_and_transform()`
  - Method `.test_plan_reports_skin_counters_without_moving_main_groups()`
  - Method `.test_exclude_applies_to_skin_groups()`
  - Method `.test_builder_rejects_mismatched_skin()`
  - Method `.test_differing_inverse_binds_stay_separate()`
  - Method `.test_builder_rejects_mismatched_inverse_binds()`
- `class RigGame` - *Minimal game module with two identical rigs for pixel-parity proofs.*
  - Method `.__init__(merged)`
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`
- `class SkinPixelParityTest`
  - Method `.test_merged_scene_renders_identical_pixels()`

**Functions:**
- `def _rig_mesh(**overrides)`
- `def _rig_scene(transform, material, mesh)`

---

### [`tests/test_particles.py`](tests/test_particles.py)
> *Tests for the deterministic particle core.*

**Size**: `472` lines (`19071` bytes)

**Classes:**
- `class EmitterTest`
  - Method `.test_spawn_is_deterministic()`
  - Method `.test_validation()`
  - Method `.test_step_rejects_non_finite_dt()`
  - Method `.test_json_round_trip()`
- `class SystemTest`
  - Method `._system()`
  - Method `.test_burst_step_and_cull_are_deterministic()`
  - Method `.test_gravity_and_drag_move_particles()`
  - Method `.test_max_particles_keeps_newest()`
  - Method `.test_errors()`
  - Method `.test_multi_emitter_systems_use_per_emitter_forces()`
  - Method `.test_report()`
  - Method `.test_particle_rests_on_a_floor()`
  - Method `.test_particle_stops_at_a_wall_without_tunneling()`
  - Method `.test_empty_colliders_match_legacy_path()`
  - Method `.test_collision_is_deterministic()`
  - Method `.test_collision_rejects_bad_colliders()`
- `class ResponseTest`
  - Method `._still_system()`
  - Method `.test_defaults_stop_dead_with_clean_zero()`
  - Method `.test_bounce_reflects_with_restitution()`
  - Method `.test_elastic_bounce_preserves_speed()`
  - Method `.test_rest_threshold_settles_micro_bounces()`
  - Method `.test_friction_scales_tangentials_on_hit_only()`
  - Method `.test_kill_on_contact_drops_the_particle()`
  - Method `.test_response_rejects_bad_parameters()`
  - Method `.test_response_is_deterministic()`
  - Method `.test_cube_demo_fountain_bounces_deterministically()`
  - Method `.test_deep_interior_spawn_ejects_through_near_face()`
  - Method `.test_stationary_deep_particle_depenetrates_on_step()`
  - Method `.test_speed_is_velocity_magnitude()`
  - Method `.test_deep_interior_motion_ejects_through_nearest_face()`
  - Method `.test_particle_fields_reject_non_finite_values()`
  - Method `.test_emitter_from_dict_rejects_malformed_payloads()`
  - Method `.test_spawn_rejects_non_vec3_origin_and_system_rejects_bad_emitters()`
  - Method `.test_step_rejects_time_overflow()`
- `class SlideTest`
  - Method `.test_sliding_along_face_preserves_tangential_motion()`
  - Method `.test_sliding_is_deterministic()`

---

### [`tests/test_pbr.py`](tests/test_pbr.py)
> *Tests for PBR material extensions: validation, glTF, graphs and reports.*

**Size**: `82` lines (`3272` bytes)

**Classes:**
- `class PbrMaterialTest`
  - Method `.test_defaults_preserve_legacy_look()`
  - Method `.test_validation_rejects_out_of_range()`
  - Method `.test_gltf_preserves_pbr_factors()`
  - Method `.test_material_graph_pbr_node()`
  - Method `.test_report_and_scene_document_include_pbr()`

---

### [`tests/test_physics.py`](tests/test_physics.py)
> *Tests for generic ray and collision primitives.*

**Size**: `102` lines (`4260` bytes)

**Classes:**
- `class PhysicsTest`
  - Method `.test_ray_hits_aabb_and_sphere()`
  - Method `.test_rays_miss()`
  - Method `.test_ray_from_inside_sphere_returns_zero_like_aabb()`
  - Method `.test_raycast_breaks_equal_distance_ties_by_key()`
  - Method `.test_ray_validation()`
  - Method `.test_overlap_and_sphere_pushout()`
  - Method `.test_non_overlapping_sphere_is_unchanged()`
  - Method `.test_pushout_lands_exactly_outside_the_face()`
  - Method `.test_aabb_helpers_are_consistent_with_overlap()`
  - Method `.test_raycast_returns_the_nearest_hit()`
  - Method `.test_raycast_filter_can_skip_candidates()`

---

### [`tests/test_playtest.py`](tests/test_playtest.py)
> *Tests for the seeded bot playtester: transcripts, diffs, policies and fairness.*

**Size**: `552` lines (`22469` bytes)

**Classes:**
- `class TranscriptTest`
  - Method `.test_run_bot_reports_per_frame_telemetry_to_an_observer()` - *A game must be able to collect its own frame data without forking the runner.*
  - Method `.test_run_bot_reports_events_to_the_observer()`
  - Method `.test_run_bot_rejects_bad_observer_input()`
  - Method `.test_load_policy_accepts_builtins_and_module_factories()`
  - Method `.test_load_policy_rejects_unknown_builtin_and_bad_specs()`
  - Method `.test_outcome_vocabulary_covers_what_the_runner_emits()`
  - Method `.test_read_outcome_round_trips_every_declared_outcome()`
  - Method `.test_timeout_is_reported_for_a_run_that_never_signals()`
  - Method `.test_run_bot_applies_a_scene_loader()`
  - Method `.test_run_bot_records_a_command_log_compatible_transcript()`
  - Method `.test_transcript_hash_matches_simulation_for_the_same_actions()`
  - Method `.test_same_seed_same_transcript()`
  - Method `.test_transcript_replays_through_the_command_log()`
  - Method `.test_terminal_outcome_ends_the_run_early()`
  - Method `.test_invalid_runner_arguments_are_rejected()`
  - Method `.test_run_bot_rejects_non_integer_seed()`
  - Method `.test_fairness_budget_does_not_hide_a_witnessed_win()`
  - Method `.test_run_bot_restores_global_random_state()`
  - Method `.test_canon_drops_time_and_rounds_floats()`
- `class DiffTest`
  - Method `.test_identical_transcripts_match_with_no_divergence()`
  - Method `.test_divergent_transcripts_report_the_first_frame()`
  - Method `.test_schema_mismatches_are_rejected()`
- `class PolicyTest`
  - Method `.test_random_policy_is_bounded_and_seeded()`
  - Method `.test_greedy_policy_repeats_a_winning_action()`
  - Method `.test_greedy_policy_without_a_score_is_random_equivalent()`
  - Method `.test_scripted_policy_holds_its_final_action()`
  - Method `.test_scripted_policy_rejects_an_empty_script()`
- `class FairnessTest`
  - Method `.test_fair_configuration_is_accepted_with_a_witness()`
  - Method `.test_walled_goal_is_rejected()`
  - Method `.test_hazard_spawn_is_rejected_as_terminal()`
  - Method `.test_tight_clock_is_rejected_as_infeasible()`
  - Method `.test_game_without_an_outcome_signal_is_unknown()`
  - Method `.test_no_reference_without_a_win_is_unknown_not_unfair()`
  - Method `.test_nondeterministic_game_is_rejected()`
- `class ReportTest`
  - Method `.test_report_is_frozen_schema_1_and_web_compatible()`
  - Method `.test_report_covers_an_untraced_transcript()`
  - Method `.test_report_rejects_string_reasons_instead_of_splitting_chars()`
  - Method `.test_report_rejects_non_string_reason_elements()`
  - Method `.test_web_simulate_result_assembles_into_the_same_report()` - *A thin adapter wraps POST /api/simulate output; no browser driving.*
- `class PlaytestCliTest`
  - Method `.test_playtest_cli_writes_transcript_and_report()`
  - Method `.test_playtest_cli_rejects_an_unfair_configuration()`
  - Method `.test_playtest_cli_pins_the_transcript_hash()`
  - Method `.test_playtest_cli_flag_guards()`
  - Method `.test_describe_advertises_the_playtest_capability()`
  - Method `.test_fixture_lives_outside_the_engine_core()`

---

### [`tests/test_plugin.py`](tests/test_plugin.py)
> *Tests for the GameModule contract and loader.*

**Size**: `119` lines (`4615` bytes)

**Classes:**
- `class PluginTest`
  - Method `.test_sample_loads_and_implements_the_contract()`
  - Method `.test_describe_exposes_capabilities_actions_and_snapshot()`
  - Method `.test_describe_reports_a_game_ui_hook()`
  - Method `.test_invalid_specs_are_rejected()`
  - Method `.test_loader_rejects_multi_colon_and_noncallable_factory()`
  - Method `.test_missing_methods_are_rejected()`
  - Method `.test_public_api_exports_texture_data()`
  - Method `.test_loader_rejects_missing_or_non_string_name()`
  - Method `.test_describe_lists_health_and_index_endpoints()`
- `class IncompleteGame`
  - Method `.build_scene()`
- `class NoNameGame`
  - Method `.build_scene()`
  - Method `.update(dt, actions)`
  - Method `.snapshot()`
  - Method `.actions()`
  - Method `.status()`
- `class BadNameGame`

---

### [`tests/test_png.py`](tests/test_png.py)
> *Unit tests for the stdlib PNG writer used by headless screenshots.*

**Size**: `119` lines (`4632` bytes)

**Classes:**
- `class PngTest`
  - Method `.test_round_trip_pixels_and_header()`
  - Method `.test_rejects_wrong_pixel_count()`
  - Method `.test_reader_round_trips_writer_pixels()`
  - Method `.test_reader_rejects_non_png()`
  - Method `.test_creates_missing_parent_directory()`
  - Method `.test_reader_rejects_bad_crc()`
  - Method `.test_reader_wraps_corrupt_idat_as_value_error()`
  - Method `.test_reader_rejects_truncated_chunk_and_missing_iend()`

**Functions:**
- `def _chunks(data)`

---

### [`tests/test_post.py`](tests/test_post.py)
> *Tests for the deterministic post color-grade (in-shader exposure + vignette).*

**Size**: `100` lines (`4247` bytes)

**Classes:**
- `class PostMathTest`
  - Method `.test_constants_are_fixed()`
  - Method `.test_vignette_center_is_one_and_corners_dim()`
  - Method `.test_grade_applies_exposure_then_vignette()`
- `class PostContractsTest`
  - Method `.test_post_settings_default_enabled()`
  - Method `.test_describe_reports_post()`
  - Method `.test_report_includes_post_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_post()`
  - Method `.test_compare_accepts_legacy_without_post()`
  - Method `.test_snapshot_round_trips_post_flag()`
  - Method `.test_scene_document_and_inspector_expose_post()`

---

### [`tests/test_prefab.py`](tests/test_prefab.py)
> *Tests for deterministic prefab capture, persistence and instantiation.*

**Size**: `353` lines (`14748` bytes)

**Classes:**
- `class Health`
- `class Counter` - *A component with an explicit codec.*
  - Method `.__init__(value)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class PrefabTest`
  - Method `._scene()`
  - Method `.test_capture_and_instantiate_a_subtree()`
  - Method `.test_instances_are_isolated_and_ids_are_unique()`
  - Method `.test_auto_ids()`
  - Method `.test_capture_and_instantiate_strip_instance_links()`
  - Method `.test_capture_several_roots_and_strip_instance_prefixes()`
  - Method `.test_nested_capture_and_instantiation_rebase_prefixes()`
  - Method `.test_nested_links_round_trip_and_schema_one_migrates()`
  - Method `.test_prefab_rejects_root_links_and_self_references()`
  - Method `.test_describe_is_json_safe()`
  - Method `.test_validation()`
  - Method `._registered_scene()`
  - Method `.test_dict_round_trip_resolves_registered_assets()`
  - Method `.test_save_and_load_versioned_file()`
  - Method `.test_load_errors_are_explicit()`
  - Method `.test_unregistered_payloads_cannot_be_serialized()`
  - Method `.test_json_primitive_components_round_trip()`

---

### [`tests/test_prefab_library.py`](tests/test_prefab_library.py)
> *Tests for file-backed prefab libraries.*

**Size**: `188` lines (`8311` bytes)

**Classes:**
- `class Health`
- `class PrefabLibraryTest`
  - Method `._fixture(directory)`
  - Method `.test_save_load_and_describe()`
  - Method `.test_describe_reports_corrupt_and_invalid_entries()`
  - Method `.test_names_are_safe_and_must_match_the_prefab()`
  - Method `.test_rename_and_delete_entries()`
  - Method `.test_duplicate_entries()`
  - Method `.test_delete_moves_to_trash_and_restore()`
  - Method `.test_load_requires_assets_and_component_types()`

---

### [`tests/test_project.py`](tests/test_project.py)
> *Tests for project manifests, scaffolding and the --project CLI path.*

**Size**: `612` lines (`26077` bytes)

**Classes:**
- `class ProjectManifestTest`
  - Method `.test_round_trip_and_file_paths()`
  - Method `.test_schema_one_manifest_remains_compatible()`
  - Method `.test_startup_scene_name_is_validated()`
  - Method `.test_set_project_startup_scene_persists_and_clears()`
  - Method `.test_validation_rejects_bad_shapes()`
  - Method `.test_missing_manifest_is_actionable()`
- `class ProjectScaffoldTest`
  - Method `._name()`
  - Method `.test_create_project_loads_and_simulates()`
  - Method `._project_with_assets(root, name)`
  - Method `.test_project_assets_import_with_stable_ids()`
  - Method `.test_editor_import_appends_manifest_and_registers()`
  - Method `.test_editor_import_rejects_unsafe_and_unsupported_sources()`
  - Method `.test_editor_import_rolls_back_manifest_on_registration_failure()`
  - Method `.test_forget_asset_removes_manifest_and_registry_but_keeps_file()`
  - Method `.test_forget_asset_rejects_unsupported_and_rolls_back()`
  - Method `.test_project_assets_import_prefab_dependencies_first()`
  - Method `.test_project_game_imports_manifest_assets()`
  - Method `.test_project_assets_reject_unsafe_missing_and_unknown()`
  - Method `.test_cli_project_asset_failure_is_actionable()`
  - Method `.test_non_empty_directory_requires_force()`
  - Method `.test_cli_new_and_project()`
  - Method `.test_cli_simulate_uses_a_saved_scene()`
  - Method `.test_cli_replay_and_playtest_use_a_saved_scene()`
  - Method `.test_validate_project_reports_clean_and_broken_content()`
  - Method `.test_cli_new_is_standalone_and_missing_project_has_why_fix()`

---

### [`tests/test_projected_bbox.py`](tests/test_projected_bbox.py)
> *Direct tests for the projected-bbox clipping helper.*

**Size**: `81` lines (`3388` bytes)

**Classes:**
- `class ProjectedBBoxTest` - *The bbox must describe on-screen extent, including near-plane crossings.*
  - Method `.setUp()`
  - Method `.test_fully_visible_box_projects_directly()`
  - Method `.test_fully_offscreen_box_is_clamped_to_the_frame()`
  - Method `.test_a_box_crossing_the_near_plane_keeps_its_extent()`
  - Method `.test_no_corners_in_front_yields_none()`
  - Method `.test_result_is_always_inside_the_frame()`

**Functions:**
- `def _corners(low, high)`

---

### [`tests/test_renderer.py`](tests/test_renderer.py)
> *Headless OpenGL integration tests for the Keystone renderer.*

**Size**: `243` lines (`9291` bytes)

**Classes:**
- `class RendererIntegrationTest`
  - Method `.setUp()`
  - Method `.test_zero_scale_node_does_not_abort_the_render()`
  - Method `.test_render_fills_the_center_with_a_lit_surface()`
  - Method `.test_empty_scene_draws_a_vertical_sky_gradient()`
  - Method `.test_two_point_lights_both_contribute()` - *A second light must add energy, not replace the first.*
  - Method `.test_more_point_lights_than_the_shader_allows_does_not_fail()`
  - Method `.test_point_light_lights_a_surface_when_the_sun_is_off()`
  - Method `.test_textured_plane_samples_the_texture()`
  - Method `.test_screenshot_is_a_real_png()`
  - Method `.test_shader_compile_error_explains_why_and_fix()`
  - Method `.test_repeated_meshes_render_instanced_with_fewer_calls()`
  - Method `.test_single_nodes_keep_plain_path_and_stats()`
- `class VersionGateTest`
  - Method `.test_rejects_old_opengl()`
  - Method `.test_accepts_33_and_newer()`

**Functions:**
- `def build_scene()`

---

### [`tests/test_replay.py`](tests/test_replay.py)
> *Tests for deterministic action logs and stable hashes.*

**Size**: `110` lines (`4338` bytes)

**Classes:**
- `class ReplayTest`
  - Method `.test_hash_ignores_mapping_order()`
  - Method `.test_hash_canonicalizes_negative_zero()`
  - Method `.test_hash_rejects_non_json_and_non_finite_values()`
  - Method `.test_command_log_constructor_validates_fields()`
  - Method `.test_command_log_round_trip()`
  - Method `.test_scene_loader_restores_each_fresh_scene()`
  - Method `.test_invalid_step_is_rejected()`
  - Method `.test_strict_seed_and_frames_are_rejected()`
  - Method `.test_run_log_restores_global_random_state()`
  - Method `.test_run_log_replays_deterministically()`

---

### [`tests/test_round_trip_stability.py`](tests/test_round_trip_stability.py)
> *Regression: a document must not change after one load/save cycle.*

**Size**: `80` lines (`2851` bytes)

**Classes:**
- `class Health`
- `class RoundTripStabilityTest` - *Vec3/Quat accept ints, so serializers must normalize them to floats.*
  - Method `.test_scene_snapshot_is_stable_across_one_load()`
  - Method `.test_scene_snapshot_lights_are_stable()`
  - Method `.test_animation_clip_is_stable_across_one_load()`
  - Method `.test_serialized_vectors_are_floats()`

**Functions:**
- `def _document(value)`

---

### [`tests/test_samples.py`](tests/test_samples.py)
> *Tests for the engine's sample game.*

**Size**: `63` lines (`2064` bytes)

**Classes:**
- `class SampleTest`
  - Method `.test_scene_contains_only_generic_renderables()`
  - Method `.test_update_rotates_cubes_and_moves_the_camera()`
  - Method `.test_actions_schema_is_generic()`
  - Method `.test_rebuild_resets_time()`
  - Method `.test_update_without_orb_fails_with_message()`

---

### [`tests/test_scene.py`](tests/test_scene.py)
> *Unit tests for the Keystone scene graph and perspective camera.*

**Size**: `360` lines (`13989` bytes)

**Classes:**
- `class Health`
- `class TransformTest`
  - Method `.test_matrix_applies_scale_then_rotation_then_translation()`
  - Method `.test_default_transform_is_identity()`
- `class NodeTest`
  - Method `.test_child_world_matrix_composes_with_parent()`
  - Method `.test_add_child_reparents_instead_of_duplicating()`
  - Method `.test_add_child_rejects_duplicate_ids_at_write_time()`
  - Method `.test_remove_child_clears_parent()`
  - Method `.test_traverse_is_depth_first_in_insertion_order()`
  - Method `.test_add_child_rejects_self_and_cycles()`
  - Method `.test_remove_child_rejects_a_stranger()`
  - Method `.test_world_visible_respects_hidden_ancestor()`
- `class NodeIdentityTest`
  - Method `.test_scene_assigns_unique_ids_on_attach()`
  - Method `.test_ids_are_scene_local_and_survive_reparenting()`
  - Method `.test_explicit_id_is_preserved_and_findable()`
  - Method `.test_duplicate_explicit_id_is_rejected_without_attaching()`
  - Method `.test_scene_add_rejects_attached_node_without_moving_it()`
  - Method `.test_tags_are_copied_and_queryable()`
  - Method `.test_layer_and_component_queries_filter_attached_nodes()`
  - Method `.test_component_access_and_removal()`
  - Method `.test_invalid_identity_fields_are_rejected()`
- `class CameraTest`
  - Method `.test_up_is_orthonormal_to_forward_and_right()`
  - Method `.test_basis_is_a_right_handed_frame()`
  - Method `.test_up_stays_level_when_pitch_is_zero()`
  - Method `.test_forward_yaw_zero_is_minus_z()`
  - Method `.test_forward_yaw_90_points_positive_x()`
  - Method `.test_view_puts_camera_origin_at_world_position()`
  - Method `.test_projection_aspect_changes_horizontal_extent()`
  - Method `.test_move_follows_forward_direction()`
  - Method `.test_rotate_clamps_pitch()`
  - Method `.test_look_at_rejects_its_own_position()`
  - Method `.test_projection_rejects_invalid_aspect()`
  - Method `.test_look_at_points_forward_at_target()`
  - Method `.test_direct_pitch_construction_stays_usable()`
  - Method `.test_direct_pitch_assignment_is_clamped_for_rendering()`
  - Method `.test_look_at_straight_up_stays_usable()`
- `class SceneTest`
  - Method `.test_scene_traverse_starts_at_root()`
  - Method `.test_scene_has_a_sky_color_distinct_from_the_horizon()`
  - Method `.test_point_light_validates_its_radius_and_intensity()`
  - Method `.test_directional_light_normalizes_lookup_direction()`
  - Method `.test_node_validates_public_construction()`
  - Method `.test_node_parent_and_children_are_reciprocal()`
  - Method `.test_transform_rejects_non_finite_and_zero_rotation()`
  - Method `.test_traverse_is_iterative_and_tolerates_removal()`
  - Method `.test_lights_reject_non_finite_and_negative_values()`

---

### [`tests/test_scene_diff.py`](tests/test_scene_diff.py)
> *Tests for structured scene snapshot diffs.*

**Size**: `103` lines (`3848` bytes)

**Classes:**
- `class SceneDiffTest`
  - Method `.test_identical_documents_have_no_changes()`
  - Method `.test_reports_node_and_scene_changes()`
  - Method `.test_reports_prefab_link_changes()`
  - Method `.test_reports_scene_group_changes()`
  - Method `.test_rejects_bad_documents()`

---

### [`tests/test_scene_library.py`](tests/test_scene_library.py)
> *Tests for file-backed scene libraries.*

**Size**: `210` lines (`9125` bytes)

**Classes:**
- `class Health`
- `class SceneLibraryTest`
  - Method `._fixture(directory)`
  - Method `.test_save_load_and_describe()`
  - Method `.test_load_into_preserves_the_scene_object()`
  - Method `.test_describe_reports_corrupt_and_invalid_entries()`
  - Method `.test_names_and_missing_entries()`
  - Method `.test_rename_and_delete_entries()`
  - Method `.test_duplicate_entries()`
  - Method `.test_delete_moves_to_trash_and_restore()`
  - Method `.test_load_requires_assets_and_component_types()`

---

### [`tests/test_scene_snapshot.py`](tests/test_scene_snapshot.py)
> *Unit tests for versioned scene snapshots.*

**Size**: `392` lines (`16006` bytes)

**Classes:**
- `class Health`
- `class SceneSnapshotTest`
  - Method `._scene()`
  - Method `.test_round_trip_preserves_structure_and_transforms()`
  - Method `.test_prefab_links_round_trip_and_older_snapshots_default_to_none()`
  - Method `.test_prefab_baselines_round_trip_and_older_snapshots_default_to_none()`
  - Method `.test_scene_groups_round_trip_and_older_snapshots_default_to_none()`
  - Method `.test_scene_group_source_settings_round_trip()`
  - Method `.test_round_trip_preserves_typed_components()`
  - Method `.test_components_require_a_type_map_and_supported_codec()`
  - Method `.test_round_trip_preserves_camera_lens_and_environment()`
  - Method `.test_multiple_point_lights_round_trip_in_order()`
  - Method `.test_legacy_single_point_light_documents_still_load()` - *A schema-6 file written before point_lights must keep its light.*
  - Method `.test_point_light_assignment_replaces_the_list()`
  - Method `.test_older_schema_one_documents_keep_engine_defaults()`
  - Method `.test_rejects_duplicate_node_ids()`
  - Method `.test_rejects_unknown_parent_reference()`
  - Method `.test_rejects_asset_kind_mismatch()`
  - Method `.test_rejects_non_string_node_ids_and_asset_references()`
  - Method `.test_rejects_non_mapping_camera_and_transform()`
  - Method `.test_rejects_unknown_version()`
  - Method `.test_asset_registry_round_trip_attaches_mesh_and_material()`
  - Method `.test_rejects_non_finite_transform_on_save()`
  - Method `.test_rejects_zero_quaternion_on_load()`
  - Method `.test_preserves_root_transform_visibility_and_next_id()`
  - Method `.test_clamps_camera_pitch_and_rejects_bad_framing()`
  - Method `.test_strict_snapshot_scalars()`

---

### [`tests/test_serialization.py`](tests/test_serialization.py)
> *Tests for atomic JSON persistence.*

**Size**: `63` lines (`2549` bytes)

**Classes:**
- `class SerializationTest`
  - Method `.test_round_trip_and_backup()`
  - Method `.test_missing_file_raises()`
  - Method `.test_bom_prefixed_file_reads()`
  - Method `.test_non_finite_json_is_rejected()`
  - Method `.test_concurrent_writers_use_distinct_temp_files()`

---

### [`tests/test_shadows.py`](tests/test_shadows.py)
> *Tests for deterministic directional shadow mapping (fixed 1024 map, PCF).*

**Size**: `125` lines (`5272` bytes)

**Classes:**
- `class ShadowMathTest`
  - Method `.test_orthographic_is_deterministic()`
  - Method `.test_light_view_and_vp_are_deterministic()`
  - Method `.test_light_vp_matches_manual_composition()`
  - Method `.test_parallel_up_vector_uses_fallback()`
  - Method `.test_shadow_settings_default_enabled()`
  - Method `.test_only_fixed_size_allowed()`
- `class ShadowContractsTest`
  - Method `.test_describe_reports_shadows()`
  - Method `.test_report_includes_shadow_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_shadows()`
  - Method `.test_compare_accepts_legacy_without_shadows()`
  - Method `.test_snapshot_round_trips_shadow_flag()`
  - Method `.test_scene_document_and_inspector_expose_shadows()`
  - Method `.test_shadow_light_helper_accepts_directional_light()`

---

### [`tests/test_skinning.py`](tests/test_skinning.py)
> *Tests for deterministic linear-blend skinning (max 4 influences).*

**Size**: `365` lines (`15042` bytes)

**Classes:**
- `class SkinValidationTest`
  - Method `.test_weights_must_be_finite_non_negative_and_are_normalized()`
  - Method `.test_skinned_normals_use_inverse_transpose()`
  - Method `.test_unskinned_meshes_stay_legacy()`
  - Method `.test_skinned_stream_packs_padded_joints_and_weights()`
  - Method `.test_rejects_partial_and_mismatched_skin()`
- `class SkinMathTest`
  - Method `.test_rigid_identity_keeps_bind_pose()`
  - Method `.test_rigid_translation_moves_vertices()`
  - Method `.test_half_blend_averages_bones()`
  - Method `.test_bone_rotation_turns_normals()`
  - Method `.test_skin_mesh_preserves_layout()`
  - Method `.test_bone_palette_is_deterministic()`
  - Method `.test_missing_joint_raises_with_fix()`
- `class SkinBatchTest`
  - Method `.test_merge_keeps_skinned_meshes_in_rig_groups()`
- `class SkinGltfTest`
  - Method `._skinned_document(bad_joint, normalized_joints, bad_weights)`
  - Method `.test_loads_a_skin()`
  - Method `.test_rejects_bad_joint_index()`
  - Method `.test_rejects_normalized_joints()`
  - Method `.test_rejects_negative_weights()`
  - Method `.test_rejects_fractional_and_duplicate_joint_indices()`
- `class SkinRenderTest`
  - Method `._skinned_scene()`
  - Method `.test_posed_render_differs_from_bind()`
  - Method `.test_holder_transform_does_not_move_skinned_deformation()`
  - Method `.test_release_after_context_close_is_a_noop()`

**Functions:**
- `def _quad_mesh(**overrides)`

---

### [`tests/test_sprite_nodes.py`](tests/test_sprite_nodes.py)
> *Tests for placed sprite nodes: model, round trip and rendering.*

**Size**: `190` lines (`7681` bytes)

**Classes:**
- `class SpriteModelTest`
  - Method `.test_defaults_and_validation()`
  - Method `.test_node_rejects_a_non_sprite_payload()`
  - Method `.test_node_without_a_sprite_still_works()`
- `class SpriteSnapshotTest`
  - Method `.test_sprite_round_trips()`
  - Method `.test_document_is_stable_across_one_load()`
  - Method `.test_a_node_without_a_sprite_writes_null()`
- `class SpriteReportTest` - *A sprite draws pixels, so the frame report must place it on screen.*
  - Method `._report_entry(sprite, width, height)`
  - Method `.test_sprite_only_node_reports_a_bbox()`
  - Method `.test_sprite_bbox_grows_with_size()`
  - Method `.test_report_carries_the_sprite_description()`
  - Method `.test_a_mesh_node_still_uses_its_mesh_bounds()`
- `class SpriteRenderTest`
  - Method `.setUp()`
  - Method `._scene(sprite, visible)`
  - Method `._render(scene)`
  - Method `._lit(pixels)`
  - Method `.test_sprite_draws_without_particles()`
  - Method `.test_sprite_colour_is_per_sprite()`
  - Method `.test_hidden_or_transparent_sprites_draw_nothing()`
  - Method `.test_size_scales_the_covered_area()`

---

### [`tests/test_sprites.py`](tests/test_sprites.py)
> *Tests for deterministic GPU point-sprite particle rendering.*

**Size**: `158` lines (`6884` bytes)

**Classes:**
- `class SpriteMathTest`
  - Method `.test_constants_are_fixed()`
  - Method `.test_scale_attenuates_and_clamps()`
  - Method `.test_soft_alpha_center_and_edge()`
  - Method `.test_sprite_alpha_combines_fade_and_soft()`
  - Method `.test_billboard_corners_are_symmetric()`
- `class SpriteSceneTest`
  - Method `.test_scene_defaults_to_sprites_enabled()`
  - Method `.test_snapshot_round_trips_sprites()`
  - Method `.test_snapshot_rejects_non_mapping_sprites()`
- `class SpriteReportTest`
  - Method `.test_schema_is_11_with_sprites_and_fx()`
  - Method `.test_analyze_frame_reports_sprites_and_fx()`
  - Method `.test_no_sprites_changes_report_hash()`
  - Method `.test_compare_accepts_schema_9_baseline()`
  - Method `.test_describe_reports_sprites_capability()`
- `class SpriteSampleTest`
  - Method `.test_fountain_is_deterministic_and_outside_snapshot()`

---

### [`tests/test_srgb.py`](tests/test_srgb.py)
> *Tests for the deterministic sRGB-correct linear pipeline (in-shader, pow 2.2).*

**Size**: `78` lines (`3292` bytes)

**Classes:**
- `class SrgbContractsTest`
  - Method `.test_color_settings_default_enabled()`
  - Method `.test_describe_reports_srgb()`
  - Method `.test_report_includes_color_metadata_and_hash()`
  - Method `.test_compare_reports_diffs_color()`
  - Method `.test_compare_accepts_legacy_without_color()`
  - Method `.test_snapshot_round_trips_color_flag()`
  - Method `.test_scene_document_and_snapshot_expose_color()`

---

### [`tests/test_state_machine_library.py`](tests/test_state_machine_library.py)
> *Tests for file-backed animation state machine libraries.*

**Size**: `139` lines (`5002` bytes)

**Classes:**
- `class StateMachineLibraryTest`
  - Method `.test_save_load_entries_delete_and_restore()`
  - Method `.test_rename_and_duplicate()`
  - Method `.test_bad_files_and_inputs()`

**Functions:**
- `def _machine()`

---

### [`tests/test_swarm_fixes.py`](tests/test_swarm_fixes.py)
> *Swarm regression pins: one failing-first test per verified Stage-3 fix.*

**Size**: `103` lines (`3573` bytes)

**Classes:**
- `class SwarmFixesTest`
  - Method `.test_shadow_all_exports_light_vp_for()`
  - Method `.test_quat_json_round_trip()`
  - Method `.test_clock_rejects_non_finite()`
  - Method `.test_command_log_to_dict_isolated()`
  - Method `.test_disabled_mouse_suppresses_click()`
  - Method `.test_update_preserves_insertion_order()`
  - Method `.test_none_flags_report_disabled()`
  - Method `.test_hit_test_right_edge_is_exclusive()`

---

### [`tests/test_testing.py`](tests/test_testing.py)
> *Tests for deterministic AI/CI scenario helpers.*

**Size**: `103` lines (`3682` bytes)

**Classes:**
- `class SceneBudgetTest`
  - Method `._scene(count)`
  - Method `.test_fingerprint_is_stable_and_name_independent()`
  - Method `.test_fingerprint_changes_when_a_transform_changes()`
  - Method `.test_budget_passes_under_the_limits()`
  - Method `.test_budget_fails_over_the_limit_with_a_clear_message()`
  - Method `.test_budget_rejects_bad_limits()`
- `class TestingHelpersTest`
  - Method `.test_run_script_uses_action_count_by_default()`
  - Method `.test_verify_determinism_passes_for_the_sample()`
  - Method `.test_assert_deterministic_returns_evidence()`
  - Method `.test_scene_loader_runs_for_each_determinism_pass()`
  - Method `.test_trace_mode_is_available()`

---

### [`tests/test_texture.py`](tests/test_texture.py)
> *Tests for immutable texture data and texture sources.*

**Size**: `153` lines (`6120` bytes)

**Classes:**
- `class PatternCostTest` - *The presets must stay cheap: a per-pixel Python loop scaled badly.*
  - Method `.test_margin_presets_are_fast_at_512()`
  - Method `.test_panel_and_rivets_match_the_reference_definition()`
  - Method `.test_pattern_rejects_an_unbounded_size()`
- `class TextureDataTest`
  - Method `.test_pattern_presets_are_deterministic_and_distinct()`
  - Method `.test_pattern_seed_changes_noise_but_not_grid()`
  - Method `.test_pattern_rejects_bad_input()`
  - Method `.test_checker_is_deterministic_and_has_expected_shape()`
  - Method `.test_png_round_trip_keeps_pixels()`
  - Method `.test_bad_texture_data_is_rejected()`
  - Method `.test_sha256_distinguishes_shapes()`
  - Method `.test_checker_rejects_bad_channel_counts()`
  - Method `.test_texture_rejects_non_bytes_payload()`

---

### [`tests/test_triggers.py`](tests/test_triggers.py)
> *Tests for trigger volumes and enter/exit tracking.*

**Size**: `48` lines (`2043` bytes)

**Classes:**
- `class TriggerTest`
  - Method `.test_trigger_volume_validates_its_name_and_overlap()`
  - Method `.test_tracker_reports_enter_stay_and_exit()`
  - Method `.test_tracker_handles_multiple_volumes_in_sorted_order()`

---

### [`tests/test_ui.py`](tests/test_ui.py)
> *Tests for the dependency-free human UI primitives and overlay.*

**Size**: `213` lines (`8829` bytes)

**Classes:**
- `class FontTest`
  - Method `.test_metrics_match_the_bitmap_grid()`
  - Method `.test_lowercase_and_unknown_characters_are_supported()`
  - Method `.test_truncate_returns_maximal_prefix()`
- `class CanvasTest`
  - Method `.test_canvas_measures_text_through_the_shared_font()`
  - Method `.test_text_right_aligns_to_the_given_edge()`
  - Method `.test_text_center_centres_the_run()`
  - Method `.test_fit_text_never_exceeds_the_requested_width()`
  - Method `.test_rect_is_clipped_to_canvas_bounds()`
  - Method `.test_text_records_labels_and_stays_inside_the_canvas()`
  - Method `.test_invalid_geometry_is_rejected()`
- `class MenuTest`
  - Method `.test_selection_wraps_and_returns_actions()`
  - Method `.test_custom_items_and_empty_menu()`
- `class OverlayTest`
  - Method `.test_overlay_shows_game_status_and_metrics()`
  - Method `.test_pause_banner_and_hidden_overlay()`
  - Method `.test_game_ui_draws_beneath_the_engine_hud()`
  - Method `.test_pause_menu_buttons_are_hit_testable()`
  - Method `.test_canvas_metadata_is_report_ready()`
  - Method `.test_compact_layout_uses_smaller_text()`
  - Method `.test_tiny_canvas_is_clipped_without_errors()`
  - Method `.test_pause_menu_move_rejects_non_integer()`
  - Method `.test_hover_right_edge_is_exclusive()`
  - Method `.test_canvas_text_scale_requires_a_positive_integer()`

**Functions:**
- `def state(**overrides)`

---

### [`tests/test_version.py`](tests/test_version.py)
> *Tests that the version is stated in exactly one place and does not drift.*

**Size**: `57` lines (`2019` bytes)

**Classes:**
- `class VersionTest`
  - Method `.test_package_and_private_version_agree()`
  - Method `.test_pyproject_version_matches_the_package()`
  - Method `.test_architecture_docs_do_not_claim_a_future_version()`
  - Method `.test_changelog_exists_and_lists_the_current_version()`

---

### [`tests/test_web.py`](tests/test_web.py)
> *Tests for scene export, the local JSON API and the browser console assets.*

**Size**: `6195` lines (`254078` bytes)

**Classes:**
- `class Health`
- `class ComponentDemo`
- `class Ticker`
  - Method `.start(context)`
  - Method `.update(context)`
  - Method `.stop(context)`
- `class LifecycleDemo`
- `class SceneDocumentTest`
  - Method `.test_sample_scene_document_has_identity_geometry_and_texture()`
  - Method `.test_world_matrices_and_mesh_references_are_exported()`
  - Method `.test_shared_meshes_are_exported_once()`
  - Method `.test_node_identity_metadata_is_exported()`
  - Method `.test_scene_document_is_deterministic()`
  - Method `.test_editor_schema_examples_cover_every_action()`
  - Method `.test_schema_describes_export_fields()`
  - Method `.test_public_web_exports_are_available()`
  - Method `.test_falsy_settings_are_reported_disabled()`
  - Method `.test_empty_live_scene_is_not_rebuilt()`
- `class WebServerTest`
  - Method `.setUp()`
  - Method `._stop()`
  - Method `._request(path, method, payload)`
  - Method `._json(path, method, payload)`
  - Method `.test_health_and_cors()`
  - Method `.test_describe_includes_the_web_capability()`
  - Method `.test_scene_endpoint_returns_the_scene_document()`
  - Method `.test_simulate_endpoint_returns_a_deterministic_result()`
  - Method `.test_editor_hierarchy_selection_and_transform()`
  - Method `.test_editor_node_authoring_and_undo_redo()`
  - Method `.test_editor_action_failure_fix_matches_the_cause()` - *A 400 must explain the failure it actually reported.*
  - Method `.test_editor_named_history_and_multi_step_undo()`
  - Method `.test_editor_asset_metadata()`
  - Method `.test_editor_asset_inventory_and_assignment()`
  - Method `.test_editor_assign_assets_to_selection()`
  - Method `.test_editor_layer_visibility()`
  - Method `.test_editor_hiding_layer_prunes_selection()`
  - Method `.test_editor_node_locking_blocks_edits()`
  - Method `.test_editor_locked_descendant_blocks_parent_delete()`
  - Method `.test_editor_locked_descendant_blocks_prefab_revert()`
  - Method `.test_editor_locked_descendant_blocks_prefab_apply()`
  - Method `.test_editor_copy_paste_selection()`
  - Method `.test_editor_prefab_capture_and_insert()`
  - Method `.test_editor_prefab_instance_revert_and_apply()`
  - Method `.test_editor_multi_root_prefab_instance_group()`
  - Method `.test_editor_multi_root_group_delete_and_reparent()`
  - Method `.test_editor_nested_prefab_capture_revert_and_apply()`
  - Method `.test_editor_refresh_preserves_nested_instance_overrides()`
  - Method `.test_editor_prefab_override_revert_and_apply()`
  - Method `.test_editor_prefab_component_override_revert_and_apply()`
  - Method `.test_editor_prefab_mesh_override_revert_and_apply()`
  - Method `.test_editor_apply_prefab_override_persists_library()`
  - Method `.test_editor_batch_can_revert_prefab_instance()`
  - Method `.test_editor_prefab_library_persists_and_reloads()`
  - Method `.test_editor_prefab_edit_mode_round_trip()`
  - Method `.test_editor_refresh_prefab_instances()`
  - Method `.test_editor_refresh_seeds_legacy_baselines_from_template()`
  - Method `.test_editor_refresh_merges_field_overrides()`
  - Method `.test_editor_refresh_drops_overrides_for_removed_template_nodes()`
  - Method `.test_editor_apply_outer_prefab_keeps_nested_override_baseline()`
  - Method `.test_editor_apply_prefab_failure_keeps_override_baseline()`
  - Method `.test_editor_apply_prefab_override_failure_keeps_baseline()`
  - Method `.test_editor_override_report_survives_template_child_addition()`
  - Method `.test_editor_refresh_skips_locked_instance_groups()`
  - Method `.test_editor_prefab_overrides_survive_scene_round_trip()`
  - Method `.test_editor_multi_root_prefab_save_from_selection()`
  - Method `.test_editor_library_rename_and_delete()`
  - Method `.test_editor_library_trash_and_restore()`
  - Method `.test_editor_library_duplicate()`
  - Method `.test_editor_scene_diff()`
  - Method `.test_editor_initial_scene_loads_at_startup()`
  - Method `.test_editor_scene_library_persists_and_restores()`
  - Method `.test_editor_add_save_unload_scene_group()`
  - Method `.test_editor_multi_selection_and_batch_actions()`
  - Method `.test_editor_multi_selection_skips_selected_descendants()`
  - Method `.test_editor_multi_selection_shared_properties_and_summary()`
  - Method `.test_editor_multi_selection_absolute_transform()`
  - Method `.test_editor_group_rotation_and_scale_around_selection_pivot()`
  - Method `.test_editor_scene_group_save_as_source_settings_and_transform()`
  - Method `.test_editor_scene_settings_and_undo()`
  - Method `.test_set_scene_accepts_a_point_light_list()` - *The editor can author more than one lamp through the API.*
  - Method `.test_set_scene_rejects_malformed_point_lights()`
  - Method `.test_editor_batch_authoring_is_atomic()`
  - Method `.test_editor_node_property_editing()`
  - Method `.test_editor_play_mode_restores_authored_scene()`
  - Method `.test_editor_play_pause_resume_and_paused_step()`
  - Method `.test_editor_play_state_exposes_snapshot_and_status()`
  - Method `.test_editor_play_state_reports_hook_errors()`
  - Method `.test_editor_validate_scene_reports_issues()`
  - Method `.test_editor_import_asset_updates_manifest_and_registry()`
  - Method `.test_editor_import_gltf_generates_prefab()`
  - Method `.test_editor_scene_dirty_and_revert()`
  - Method `.test_editor_startup_scene_persists_and_clears()`
  - Method `.test_editor_startup_scene_follows_rename_and_delete()`
  - Method `.test_editor_startup_rename_failure_restores_saved_scene()`
  - Method `.test_editor_forget_asset_and_project_inventory()`
  - Method `.test_editor_forget_asset_clears_undo_payloads()`
  - Method `.test_editor_forget_asset_clears_clipboard_payloads()`
  - Method `.test_editor_asset_usages_and_saved_references()`
  - Method `.test_editor_build_project()`
  - Method `.test_editor_reload_assets_rebinds_scene_and_history()`
  - Method `.test_editor_reload_rebinds_unchanged_payload_identity()`
  - Method `.test_editor_reload_rebinds_registry_material_textures()`
  - Method `.test_editor_preview_animation_and_undo()`
  - Method `.test_editor_animation_library_round_trip()`
  - Method `.test_editor_state_machine_library_and_preview()`
  - Method `.test_editor_state_machine_rename_and_duplicate()`
  - Method `.test_editor_state_machine_restore_collision_is_400()`
  - Method `.test_editor_preview_blend_space()`
  - Method `.test_editor_blend_state_console_round_trip()`
  - Method `.test_editor_animation_key_authoring()`
  - Method `.test_editor_material_library_save_assign_and_reload()`
  - Method `.test_editor_component_lifecycle_play_mode()`
  - Method `.test_editor_component_authoring_and_scene_round_trip()`
  - Method `.test_editor_static_controls_and_index()`
  - Method `.test_step_button_documents_its_reset_semantics()`
  - Method `.test_options_preflight_and_static_assets()`
  - Method `.test_api_index_and_errors_are_json()`
  - Method `.test_simulate_rejects_non_finite_step()`
  - Method `.test_non_finite_action_is_400_without_poisoning_the_session()`
  - Method `.test_oversized_step_and_json_number_are_client_errors()`
  - Method `.test_simulate_infers_frames_from_actions()`
  - Method `.test_head_and_method_errors()`

**Functions:**
- `def _triangle_gltf()`
- `def _state_machine_document()`
- `def _blend_space_document()`

---
