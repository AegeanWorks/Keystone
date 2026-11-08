"""Project manifests and one-command scaffolding for external Keystone games.

The engine remains game-agnostic: a project is a directory with a
``keystone.json`` manifest and an external game module. ``load_game`` still
validates the five-operation contract before the engine starts.
"""

from __future__ import annotations

import re
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import util
from pathlib import Path

from keystone.asset_io import kind_from_suffix
from keystone.assets import AssetRecord, AssetRegistry
from keystone.gltf_import import import_gltf_prefab, is_gltf_asset
from keystone.plugin import GameModule, load_game
from keystone.prefab import Prefab
from keystone.prefab_library import PrefabLibrary, validate_library_name
from keystone.scene_library import SceneLibrary
from keystone.serialization import read_json, write_json_atomic

PROJECT_SCHEMA_VERSION = 2
PROJECT_FILE = "keystone.json"
DEFAULT_GAME_SPEC = "game:Game"

__all__ = [
    "PROJECT_FILE",
    "PROJECT_SCHEMA_VERSION",
    "ProjectContext",
    "ProjectManifest",
    "attach_project_assets",
    "create_project",
    "import_project_asset",
    "import_project_assets",
    "import_project_gltf",
    "load_project",
    "load_project_game",
    "project_asset_id",
    "resolve_project_asset",
    "save_project",
    "set_project_startup_scene",
    "validate_project",
]

IMPORTABLE_SUFFIXES = (".obj", ".png", ".kprefab")


def _module_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_")
    if not slug or slug[0].isdigit():
        slug = f"game_{slug}" if slug else "game"
    return slug


def _manifest_path(path: str | Path) -> Path:
    target = Path(path)
    if target.is_dir():
        return target / PROJECT_FILE
    return target


@dataclass(frozen=True, slots=True)
class ProjectManifest:
    """Versioned, JSON-safe project metadata."""

    name: str
    game: str = DEFAULT_GAME_SPEC
    description: str = ""
    assets: tuple[str, ...] = ()
    startup_scene: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("project name must be a non-blank string")
        if not isinstance(self.game, str) or self.game.count(":") != 1:
            raise ValueError("project game must look like 'module:Factory'")
        module, factory = self.game.split(":", 1)
        if not module.strip() or not factory.strip():
            raise ValueError("project game must include a module and factory")
        if not isinstance(self.description, str):
            raise TypeError("project description must be a string")
        if isinstance(self.assets, (str, bytes)):
            raise TypeError("project assets must be a list of paths")
        assets = tuple(self.assets)
        if any(not isinstance(item, str) or not item.strip() for item in assets):
            raise ValueError("project assets must be non-blank strings")
        object.__setattr__(self, "assets", assets)
        if self.startup_scene is not None:
            try:
                validate_library_name(self.startup_scene)
            except ValueError as exc:
                raise ValueError(
                    "project startup_scene must be a valid scene name or null"
                ) from exc

    def to_dict(self) -> dict:
        return {
            "schema": PROJECT_SCHEMA_VERSION,
            "name": self.name,
            "game": self.game,
            "description": self.description,
            "assets": list(self.assets),
            "startup_scene": self.startup_scene,
        }

    @classmethod
    def from_dict(cls, data: object) -> ProjectManifest:
        if not isinstance(data, dict):
            raise TypeError("project manifest must be a JSON object")
        schema = data.get("schema", PROJECT_SCHEMA_VERSION)
        if (
            isinstance(schema, bool)
            or not isinstance(schema, int)
            or schema not in (1, PROJECT_SCHEMA_VERSION)
        ):
            raise ValueError(f"unsupported project schema {schema}")
        unknown = set(data) - {
            "schema",
            "name",
            "game",
            "description",
            "assets",
            "startup_scene",
        }
        if unknown:
            raise ValueError(f"project manifest has unknown keys: {sorted(unknown)}")
        assets = data.get("assets", [])
        if not isinstance(assets, (list, tuple)):
            raise TypeError("project assets must be a list")
        return cls(
            name=data.get("name", ""),
            game=data.get("game", DEFAULT_GAME_SPEC),
            description=data.get("description", ""),
            assets=tuple(assets),
            startup_scene=data.get("startup_scene"),
        )


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """A loaded manifest plus its project directory."""

    manifest: ProjectManifest
    directory: Path

    def describe(self) -> dict:
        return {
            "directory": str(self.directory),
            "manifest": self.manifest.to_dict(),
        }


def load_project(path: str | Path) -> ProjectContext:
    """Load ``keystone.json`` from a project directory or manifest file."""
    target = Path(path)
    source = _manifest_path(target)
    if not source.exists():
        raise FileNotFoundError(
            f"project manifest not found at {source}.\n"
            "Why: a Keystone project needs a keystone.json file.\n"
            "Fix: run python -m keystone --new <directory>, or pass the manifest path."
        )
    if not source.is_file():
        raise ValueError(f"project manifest is not a file: {source}")
    manifest = ProjectManifest.from_dict(read_json(source))
    return ProjectContext(manifest, source.parent.resolve())


def save_project(path: str | Path, manifest: ProjectManifest) -> Path:
    """Write a manifest atomically; accepts a directory or a JSON path."""
    target = _manifest_path(path)
    if target.suffix.lower() != ".json" and not target.exists():
        target = target / PROJECT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(target, manifest.to_dict())
    return target


def set_project_startup_scene(
    context: ProjectContext, name: str | None
) -> ProjectManifest:
    """Persist one optional startup scene name and return the new manifest."""
    if not isinstance(context, ProjectContext):
        raise TypeError("project context must be a ProjectContext")
    manifest = ProjectManifest(
        name=context.manifest.name,
        game=context.manifest.game,
        description=context.manifest.description,
        assets=context.manifest.assets,
        startup_scene=name,
    )
    save_project(context.directory, manifest)
    return manifest


def _relative_asset_path(value: str | Path) -> Path:
    if not isinstance(value, (str, Path)):
        raise TypeError("project asset path must be a string or Path")
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"project asset path must be relative: {value}")
    parts = tuple(part for part in relative.parts if part not in ("", "."))
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"project asset path must stay inside the project: {value}")
    return Path(*parts)


def project_asset_id(value: str | Path) -> str:
    """Return the deterministic registry id for one manifest asset path."""
    return "project:" + _relative_asset_path(value).as_posix()


def resolve_project_asset(
    context: ProjectContext, value: str | Path
) -> tuple[Path, Path]:
    """Resolve one asset path and prove it stays inside the project."""
    if not isinstance(context, ProjectContext):
        raise TypeError("project context must be a ProjectContext")
    root = context.directory.resolve()
    relative = _relative_asset_path(value)
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"project asset escapes the project directory: {value}") from exc
    if not target.is_file():
        raise FileNotFoundError(f"project asset does not exist: {target}")
    return relative, target


def import_project_assets(
    context: ProjectContext,
    registry: AssetRegistry,
    component_types: Mapping[str, type] | None = None,
) -> tuple[AssetRecord, ...]:
    """Load every manifest asset into an existing registry."""
    if not isinstance(context, ProjectContext):
        raise TypeError("project context must be a ProjectContext")
    if not isinstance(registry, AssetRegistry):
        raise TypeError("project assets need an AssetRegistry")
    pending: list[tuple[str, Path, Path, str]] = []
    for value in context.manifest.assets:
        relative, target = resolve_project_asset(context, value)
        if is_gltf_asset(target):
            continue
        pending.append((value, relative, target, kind_from_suffix(target)))
    ordered = [item for item in pending if item[3] != "prefab"] + [
        item for item in pending if item[3] == "prefab"
    ]
    records: dict[str, AssetRecord] = {}
    for _, relative, target, kind in ordered:
        identifier = project_asset_id(relative)
        records[identifier] = registry.register_file(
            identifier,
            target,
            kind=kind,
            component_types=component_types if kind == "prefab" else None,
        )
    return tuple(
        records[project_asset_id(value)]
        for value in context.manifest.assets
        if not is_gltf_asset(value)
    )


def import_project_asset(
    context: ProjectContext,
    registry: AssetRegistry,
    value: str | Path,
    component_types: Mapping[str, type] | None = None,
) -> dict[str, object]:
    """Import one editor-selected file and append it to the project manifest.

    The manifest is saved before registration so a failed load restores the
    previous asset list. Re-importing a listed path refreshes its registry
    record without duplicating the manifest entry.
    """
    if not isinstance(context, ProjectContext):
        raise TypeError("project context must be a ProjectContext")
    if not isinstance(registry, AssetRegistry):
        raise TypeError("project asset import needs an AssetRegistry")
    relative, target = resolve_project_asset(context, value)
    normalized = relative.as_posix()
    if is_gltf_asset(target):
        raise ValueError(
            f"glTF/GLB import is not available in the editor: {normalized}.\n"
            "Why: glTF scenes expand into generated prefabs and registry assets.\n"
            "Fix: add the path to keystone.json assets and restart with --project."
        )
    if target.suffix.lower() not in IMPORTABLE_SUFFIXES:
        raise ValueError(
            f"unsupported asset format for editor import: {normalized}.\n"
            "Fix: import a .obj mesh, .png texture or .kprefab prefab."
        )
    kind = kind_from_suffix(target)
    identifier = project_asset_id(relative)
    duplicate = normalized in {
        Path(item).as_posix() for item in context.manifest.assets
    }
    manifest = context.manifest
    if not duplicate:
        manifest = ProjectManifest(
            name=context.manifest.name,
            game=context.manifest.game,
            description=context.manifest.description,
            assets=(*context.manifest.assets, normalized),
        )
        save_project(context.directory, manifest)
    try:
        record = registry.register_file(
            identifier,
            target,
            kind=kind,
            component_types=component_types if kind == "prefab" else None,
            replace=True,
        )
    except Exception:
        if not duplicate:
            save_project(context.directory, context.manifest)
        raise
    return {
        "path": normalized,
        "asset": record.id,
        "kind": record.kind,
        "duplicate": duplicate,
        "count": len(manifest.assets),
    }


def import_project_gltf(
    context: ProjectContext,
    registry: AssetRegistry,
    prefab_library: PrefabLibrary,
    value: str | Path,
    name: str | None = None,
) -> dict[str, object]:
    """Import a project glTF/GLB scene as a prefab and record its source."""
    if not isinstance(context, ProjectContext):
        raise TypeError("project context must be a ProjectContext")
    if not isinstance(registry, AssetRegistry):
        raise TypeError("glTF import needs an AssetRegistry")
    if not isinstance(prefab_library, PrefabLibrary):
        raise TypeError("glTF import needs a PrefabLibrary")
    relative, target = resolve_project_asset(context, value)
    if not is_gltf_asset(target):
        raise ValueError(
            f"not a glTF/GLB source: {relative.as_posix()}.\n"
            "Fix: use import_asset for .obj, .png or .kprefab files."
        )
    selected = validate_library_name(name or target.stem)
    normalized = relative.as_posix()
    duplicate = normalized in {
        Path(item).as_posix() for item in context.manifest.assets
    }
    replaced = prefab_library.path_for(selected).is_file()
    manifest = context.manifest
    if not duplicate:
        manifest = ProjectManifest(
            name=context.manifest.name,
            game=context.manifest.game,
            description=context.manifest.description,
            assets=(*context.manifest.assets, normalized),
        )
        save_project(context.directory, manifest)
    before = set(registry.ids())
    try:
        prefab = import_gltf_prefab(
            target, registry, prefab_library, name=selected
        )
    except Exception:
        if not duplicate:
            save_project(context.directory, context.manifest)
        for asset_id in tuple(set(registry.ids()) - before):
            registry.remove(asset_id)
        raise
    assets = sorted(
        asset_id
        for asset_id in registry.ids()
        if asset_id.startswith(f"gltf.{selected}.")
    )
    return {
        "path": normalized,
        "prefab": prefab.name,
        "assets": assets,
        "asset_count": len(assets),
        "duplicate": duplicate,
        "replaced_prefab": replaced,
        "count": len(manifest.assets),
    }


def attach_project_assets(
    game: GameModule,
    context: ProjectContext,
    component_types: Mapping[str, type] | None = None,
    prefab_library: PrefabLibrary | None = None,
) -> tuple[AssetRecord, ...]:
    """Import manifest assets, including glTF scenes as prefab entries."""
    if not context.manifest.assets:
        return ()
    registry = getattr(game, "assets", None)
    if not isinstance(registry, AssetRegistry):
        raise TypeError("project declares assets but game.assets is not an AssetRegistry")
    selected = component_types
    if selected is None:
        selected = getattr(game, "component_types", None)
    records = import_project_assets(context, registry, selected)
    gltf_values = [value for value in context.manifest.assets if is_gltf_asset(value)]
    if gltf_values:
        library = prefab_library
        if library is None:
            library = PrefabLibrary(
                context.directory / "prefabs",
                registry=registry,
                component_types=selected,
            )
        elif not isinstance(library, PrefabLibrary):
            raise TypeError("prefab_library must be a PrefabLibrary or None")
        else:
            library.registry = registry
        for value in gltf_values:
            _, target = resolve_project_asset(context, value)
            import_gltf_prefab(target, registry, library)
    return records


def validate_project(
    context: ProjectContext,
    game: GameModule | None = None,
) -> dict[str, object]:
    """Validate project assets, scenes and prefabs without writing project files."""
    if not isinstance(context, ProjectContext):
        raise TypeError("project context must be a ProjectContext")
    errors: list[dict[str, str]] = []
    registry = AssetRegistry()
    if game is not None:
        build = getattr(game, "build_scene", None)
        if callable(build):
            try:
                build()
            except Exception as exc:  # noqa: BLE001 - validation reports failures
                errors.append(
                    {"kind": "game", "message": f"{type(exc).__name__}: {exc}"}
                )
        game_assets = getattr(game, "assets", None)
        if isinstance(game_assets, AssetRegistry):
            for record in game_assets:
                try:
                    registry.register(
                        record.id,
                        record.payload,
                        kind=record.kind,
                        source=record.source,
                        dependencies=record.dependencies,
                        replace=True,
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        {
                            "kind": "game",
                            "message": f"{record.id}: {type(exc).__name__}: {exc}",
                        }
                    )
        else:
            errors.append(
                {"kind": "game", "message": "game.assets is not an AssetRegistry"}
            )
    component_types = (
        getattr(game, "component_types", None) if game is not None else None
    )
    try:
        import_project_assets(context, registry, component_types)
    except Exception as exc:  # noqa: BLE001
        errors.append(
            {"kind": "assets", "message": f"{type(exc).__name__}: {exc}"}
        )
    with tempfile.TemporaryDirectory() as directory:
        library = PrefabLibrary(
            Path(directory) / "prefabs",
            registry=registry,
            component_types=component_types,
        )
        for value in context.manifest.assets:
            if not is_gltf_asset(value):
                continue
            try:
                _, target = resolve_project_asset(context, value)
                import_gltf_prefab(target, registry, library)
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {
                        "kind": "gltf",
                        "message": f"{value}: {type(exc).__name__}: {exc}",
                    }
                )
    prefabs: list[dict[str, object]] = []
    try:
        prefab_library = PrefabLibrary(
            context.directory / "prefabs",
            registry=registry,
            component_types=component_types,
        )
        prefabs = [entry.describe() for entry in prefab_library.entries()]
    except Exception as exc:  # noqa: BLE001
        errors.append(
            {"kind": "prefabs", "message": f"{type(exc).__name__}: {exc}"}
        )
    scenes: list[dict[str, object]] = []
    try:
        scene_library = SceneLibrary(
            context.directory / "scenes",
            registry=registry,
            component_types=component_types,
        )
        scenes = [entry.describe() for entry in scene_library.entries()]
    except Exception as exc:  # noqa: BLE001
        errors.append(
            {"kind": "scenes", "message": f"{type(exc).__name__}: {exc}"}
        )
    ok = not errors and all(
        entry["error"] is None for entry in prefabs + scenes
    )
    return {
        "schema": 1,
        "ok": ok,
        "project": context.describe(),
        "game": getattr(game, "name", None),
        "assets": {
            "count": len(registry),
            "errors": [item for item in errors if item["kind"] in ("assets", "gltf")],
        },
        "prefabs": prefabs,
        "scenes": scenes,
        "errors": errors,
    }


def load_project_game(context: ProjectContext) -> GameModule:
    """Import and validate a project's game after adding its directory to sys.path."""
    directory = str(context.directory)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    game = load_game(context.manifest.game)
    attach_project_assets(game, context)
    return game


def _game_source(manifest: ProjectManifest) -> str:
    return f'''"""Generated Keystone game: {manifest.name}."""

from __future__ import annotations

from keystone import AssetRegistry, Node, Quat, Scene, Transform, Vec3
from keystone.geometry import Material
from keystone.primitives import cube, plane


class Game:
    name = {manifest.name!r}

    def __init__(self) -> None:
        self.scene: Scene | None = None
        self.assets = AssetRegistry()
        self.component_types: dict[str, type] = {{}}
        self.time = 0.0
        self._cube: Node | None = None

    def build_scene(self) -> Scene:
        self.scene = Scene()
        self.scene.camera.position = Vec3(0.0, 2.5, 7.0)
        self.scene.camera.look_at(Vec3(0.0, 0.8, 0.0))
        floor_mesh = plane(20.0)
        cube_mesh = cube(1.5)
        floor_material = Material(color=Vec3(0.18, 0.2, 0.24))
        cube_material = Material(color=Vec3(0.9, 0.45, 0.2))
        self.assets.register("mesh.plane", floor_mesh, replace=True)
        self.assets.register("mesh.cube", cube_mesh, replace=True)
        self.assets.register("material.floor", floor_material, replace=True)
        self.assets.register("material.cube", cube_material, replace=True)
        self.scene.add(Node("floor", id="floor", mesh=floor_mesh, material=floor_material))
        self._cube = self.scene.add(Node("cube", id="cube", mesh=cube_mesh, material=cube_material))
        return self.scene

    def update(self, dt: float, actions: object) -> None:
        self.time += dt
        if self._cube is not None:
            self._cube.transform = Transform(
                position=Vec3(0.0, 0.9, 0.0),
                rotation=Quat.from_axis_angle(Vec3(0.0, 1.0, 0.0), self.time),
                scale=Vec3(1.0, 1.0, 1.0),
            )

    def snapshot(self) -> dict[str, object]:
        return {{"time": round(self.time, 6), "name": self.name}}

    def actions(self) -> dict[str, object]:
        return {{"axes": ["forward", "right", "up", "look_yaw", "look_pitch"], "buttons": []}}

    def status(self) -> str:
        return f"{{self.name}} | {{self.time:.2f}}s"
'''


def _project_readme(manifest: ProjectManifest) -> str:
    return f"""# {manifest.name}

A Keystone game project. The engine is external; this directory owns the game.

## Run

```bash
python -m keystone --project . --describe
python -m keystone --project . --simulate --frames 120
python -m keystone --project . --headless --frames 1 --out frame.png --report frame.json
python -m keystone --project . --serve --scene main
```

The starter `scenes/main.kscene` and `prefabs/cube.kprefab` are generated by `--new`. `keystone.json` records it as the `startup_scene`, so `python -m keystone --project .` opens it unless `--scene NAME` overrides it. Save a different scene in the console, then set it as startup or reopen it with `--scene NAME`.

## Files

- `keystone.json` — versioned project manifest.
- `{_module_name(manifest.name)}.py` — the generated five-operation game module.
- `prefabs/` - editor prefab library; save prefabs here from the console.
- `scenes/` - editor scene library; save scenes here from the console.
- `animations/` - editor animation library; save `.kanim` clips here from the console.
- `materials/` - editor material library; save `.kmaterial` files here from the console.

## Assets

Add relative `.obj`, `.png`, `.kprefab`, `.gltf` or `.glb` paths to `assets`
in `keystone.json`. `--project` imports them when the game exposes
`self.assets = AssetRegistry()`: regular assets use `project:<relative-path>`,
and glTF/GLB scenes become `<prefabs>/<stem>.kprefab` with `gltf.<stem>.*`
mesh/material/texture ids.
"""


def _write_starter_library(directory: Path, module: str) -> None:
    spec = util.spec_from_file_location(
        f"_keystone_project_{module}", directory / f"{module}.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load generated game module {module}")
    generated = util.module_from_spec(spec)
    spec.loader.exec_module(generated)
    game = generated.Game()
    scene = game.build_scene()
    registry = getattr(game, "assets", None)
    if not isinstance(registry, AssetRegistry):
        raise TypeError("generated game must expose an AssetRegistry as assets")
    component_types = getattr(game, "component_types", None)
    SceneLibrary(
        directory / "scenes",
        registry=registry,
        component_types=component_types,
    ).save("main", scene)
    cube = scene.find_by_id("cube")
    if cube is None:
        raise ValueError("generated game scene must contain a cube node")
    PrefabLibrary(
        directory / "prefabs",
        registry=registry,
        component_types=component_types,
    ).save("cube", Prefab.from_node(cube, name="cube"))


def create_project(
    directory: str | Path,
    *,
    name: str | None = None,
    game: str | None = None,
    force: bool = False,
) -> ProjectContext:
    """Scaffold a runnable project directory and return its context."""
    target = Path(directory)
    if target.exists() and not target.is_dir():
        raise ValueError(f"project path is not a directory: {target}")
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(
            f"project directory is not empty: {target}.\n"
            "Why: scaffolding would overwrite an existing project.\n"
            "Fix: choose an empty directory or pass --force."
        )
    target.mkdir(parents=True, exist_ok=True)
    selected_name = name or target.name or "keystone-game"
    module = _module_name(selected_name)
    manifest = ProjectManifest(
        name=selected_name,
        game=game or f"{module}:Game",
        description="A Keystone game project generated by --new.",
        startup_scene="main",
    )
    save_project(target, manifest)
    (target / f"{module}.py").write_text(_game_source(manifest), encoding="utf-8")
    (target / "README.md").write_text(_project_readme(manifest), encoding="utf-8")
    (target / ".gitignore").write_text("__pycache__/\n*.pyc\nframe.png\nframe.json\n", encoding="utf-8")
    (target / "prefabs").mkdir(exist_ok=True)
    (target / "prefabs" / "README.md").write_text(
        "# Prefabs\n\nSaved by the editor as versioned `.kprefab` files.\n",
        encoding="utf-8",
    )
    (target / "scenes").mkdir(exist_ok=True)
    (target / "scenes" / "README.md").write_text(
        "# Scenes\n\nSaved by the editor as versioned `.kscene` files.\n",
        encoding="utf-8",
    )
    (target / "animations").mkdir(exist_ok=True)
    (target / "animations" / "README.md").write_text(
        "# Animations\n\nSaved by the editor as versioned `.kanim` clips.\n",
        encoding="utf-8",
    )
    (target / "materials").mkdir(exist_ok=True)
    (target / "materials" / "README.md").write_text(
        "# Materials\n\nSaved by the editor as versioned `.kmaterial` files.\n",
        encoding="utf-8",
    )
    _write_starter_library(target, module)
    return ProjectContext(manifest, target.resolve())
