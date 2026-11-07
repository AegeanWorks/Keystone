"""Project manifests and one-command scaffolding for external Keystone games.

The engine remains game-agnostic: a project is a directory with a
``keystone.json`` manifest and an external game module. ``load_game`` still
validates the five-operation contract before the engine starts.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from keystone.plugin import GameModule, load_game
from keystone.serialization import read_json, write_json_atomic

PROJECT_SCHEMA_VERSION = 1
PROJECT_FILE = "keystone.json"
DEFAULT_GAME_SPEC = "game:Game"

__all__ = [
    "PROJECT_FILE",
    "PROJECT_SCHEMA_VERSION",
    "ProjectContext",
    "ProjectManifest",
    "create_project",
    "load_project",
    "load_project_game",
    "save_project",
]


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

    def to_dict(self) -> dict:
        return {
            "schema": PROJECT_SCHEMA_VERSION,
            "name": self.name,
            "game": self.game,
            "description": self.description,
            "assets": list(self.assets),
        }

    @classmethod
    def from_dict(cls, data: object) -> ProjectManifest:
        if not isinstance(data, dict):
            raise TypeError("project manifest must be a JSON object")
        schema = data.get("schema", PROJECT_SCHEMA_VERSION)
        if isinstance(schema, bool) or not isinstance(schema, int) or schema != PROJECT_SCHEMA_VERSION:
            raise ValueError(f"unsupported project schema {schema}")
        unknown = set(data) - {"schema", "name", "game", "description", "assets"}
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


def load_project_game(context: ProjectContext) -> GameModule:
    """Import and validate a project's game after adding its directory to sys.path."""
    directory = str(context.directory)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    return load_game(context.manifest.game)


def _game_source(manifest: ProjectManifest) -> str:
    return f'''"""Generated Keystone game: {manifest.name}."""

from __future__ import annotations

from keystone import Node, Quat, Scene, Transform, Vec3
from keystone.geometry import Material
from keystone.primitives import cube, plane


class Game:
    name = {manifest.name!r}

    def __init__(self) -> None:
        self.scene: Scene | None = None
        self.time = 0.0
        self._cube: Node | None = None

    def build_scene(self) -> Scene:
        self.scene = Scene()
        self.scene.camera.position = Vec3(0.0, 2.5, 7.0)
        self.scene.camera.look_at(Vec3(0.0, 0.8, 0.0))
        self.scene.add(Node("floor", id="floor", mesh=plane(20.0), material=Material(color=Vec3(0.18, 0.2, 0.24))))
        self._cube = self.scene.add(Node("cube", id="cube", mesh=cube(1.5), material=Material(color=Vec3(0.9, 0.45, 0.2))))
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
python -m keystone --project . --serve
```

## Files

- `keystone.json` — versioned project manifest.
- `{_module_name(manifest.name)}.py` — the generated five-operation game module.
"""


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
    )
    save_project(target, manifest)
    (target / f"{module}.py").write_text(_game_source(manifest), encoding="utf-8")
    (target / "README.md").write_text(_project_readme(manifest), encoding="utf-8")
    (target / ".gitignore").write_text("__pycache__/\n*.pyc\nframe.png\nframe.json\n", encoding="utf-8")
    return ProjectContext(manifest, target.resolve())
