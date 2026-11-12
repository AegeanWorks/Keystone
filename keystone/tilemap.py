"""Grid tile maps: collision boxes, a merged level mesh and JSON documents.

Tile maps are the simplest level format an author or an AI can edit cell by
cell. This module keeps the map immutable, turns solid cells into exact
``AABB`` colliders for physics and navigation, and builds one merged
``MeshData`` with a floor quad per free cell and a wall box per solid cell,
so a whole level renders in one draw.

The map deliberately does not own a scene node or a renderer handle: add the
mesh to a node, feed ``colliders()`` to ``grid_from_boxes``, or raycast against
them, exactly as with any other level geometry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from keystone.geometry import MeshData
from keystone.math3d import Vec3
from keystone.mesh_builder import MeshBuilder
from keystone.physics import AABB

__all__ = ["TileMap", "tilemap_report"]

Cell = tuple[int, int]
_DOCUMENT_KEYS = frozenset(
    {
        "schema",
        "width",
        "height",
        "tile_size",
        "origin",
        "solid",
        "floor_color",
        "wall_color",
        "wall_height",
    }
)


def _positive_int(label: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _finite(label: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _point(label: str, value: object) -> Vec3:
    if not isinstance(value, Vec3):
        raise TypeError(f"{label} must be a Vec3")
    for axis in ("x", "y", "z"):
        _finite(f"{label} {axis}", getattr(value, axis))
    return value


def _color(label: str, value: object) -> Vec3:
    point = _point(label, value)
    for axis in ("x", "y", "z"):
        component = getattr(point, axis)
        if not 0.0 <= component <= 1.0:
            raise ValueError(f"{label} {axis} must be between 0 and 1")
    return point


def _cell(label: str, value: object) -> Cell:
    if (
        isinstance(value, tuple)
        and len(value) == 2
        and all(isinstance(part, int) and not isinstance(part, bool) for part in value)
    ):
        return (value[0], value[1])
    raise TypeError(f"{label} must be an (x, y) integer tuple")


@dataclass(frozen=True, slots=True)
class TileMap:
    """An immutable grid of free and solid cells with one wall height."""

    width: int
    height: int
    tile_size: float = 1.0
    origin: Vec3 = Vec3()
    solid: frozenset[Cell] = frozenset()
    floor_color: Vec3 = Vec3(0.30, 0.33, 0.38)
    wall_color: Vec3 = Vec3(0.55, 0.45, 0.35)
    wall_height: float = 1.0

    def __post_init__(self) -> None:
        _positive_int("tile map width", self.width)
        _positive_int("tile map height", self.height)
        if _finite("tile map tile size", self.tile_size) <= 0.0:
            raise ValueError("tile map tile size must be positive")
        _point("tile map origin", self.origin)
        _color("tile map floor color", self.floor_color)
        _color("tile map wall color", self.wall_color)
        if _finite("tile map wall height", self.wall_height) <= 0.0:
            raise ValueError("tile map wall height must be positive")
        try:
            solid = frozenset(self.solid)
        except TypeError as exc:
            raise TypeError("tile map solid cells must be (x, y) integer tuples") from exc
        for cell in solid:
            checked = _cell("tile map solid cell", cell)
            if not self.in_bounds(checked):
                raise ValueError(f"tile map solid cell {checked!r} is outside the grid")
        object.__setattr__(self, "solid", solid)

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def is_solid(self, cell: Cell) -> bool:
        checked = _cell("tile map cell", cell)
        return self.in_bounds(checked) and checked in self.solid

    def cell_center(self, cell: Cell) -> Vec3:
        checked = _cell("tile map cell", cell)
        if not self.in_bounds(checked):
            raise ValueError(f"tile map cell {checked!r} is outside the grid")
        return Vec3(
            self.origin.x + (checked[0] + 0.5) * self.tile_size,
            self.origin.y,
            self.origin.z + (checked[1] + 0.5) * self.tile_size,
        )

    def with_cell(self, cell: Cell, solid: bool) -> TileMap:
        """Return a copy with one cell made solid or free."""
        checked = _cell("tile map cell", cell)
        if not self.in_bounds(checked):
            raise ValueError(f"tile map cell {checked!r} is outside the grid")
        if not isinstance(solid, bool):
            raise TypeError("tile map cell solid flag must be a boolean")
        cells = self.solid | {checked} if solid else self.solid - {checked}
        return replace(self, solid=frozenset(cells))

    def colliders(self) -> tuple[AABB, ...]:
        """One world AABB per solid cell, ordered by cell y then x."""
        half = Vec3(self.tile_size / 2.0, self.wall_height / 2.0, self.tile_size / 2.0)
        boxes: list[AABB] = []
        for x, y in sorted(self.solid):
            boxes.append(
                AABB(
                    Vec3(
                        self.origin.x + (x + 0.5) * self.tile_size,
                        self.origin.y + self.wall_height / 2.0,
                        self.origin.z + (y + 0.5) * self.tile_size,
                    ),
                    half,
                )
            )
        return tuple(boxes)

    def mesh(self) -> MeshData:
        """Merge a floor quad per free cell and a wall box per solid cell."""
        builder = MeshBuilder()
        floor = (self.floor_color.x, self.floor_color.y, self.floor_color.z)
        wall = (self.wall_color.x, self.wall_color.y, self.wall_color.z)
        size = self.tile_size
        for y in range(self.height):
            for x in range(self.width):
                cx = self.origin.x + (x + 0.5) * size
                cz = self.origin.z + (y + 0.5) * size
                if (x, y) in self.solid:
                    builder.add_box(
                        cx,
                        self.origin.y + self.wall_height / 2.0,
                        cz,
                        size,
                        self.wall_height,
                        size,
                        wall,
                    )
                    continue
                x0, x1 = cx - size / 2.0, cx + size / 2.0
                z0, z1 = cz - size / 2.0, cz + size / 2.0
                y0 = self.origin.y
                builder.add_quad(
                    (x0, y0, z0),
                    (x0, y0, z1),
                    (x1, y0, z1),
                    (x1, y0, z0),
                    floor,
                )
        return builder.build()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": 1,
            "width": self.width,
            "height": self.height,
            "tile_size": self.tile_size,
            "origin": [self.origin.x, self.origin.y, self.origin.z],
            "solid": [[x, y] for x, y in sorted(self.solid)],
            "floor_color": [self.floor_color.x, self.floor_color.y, self.floor_color.z],
            "wall_color": [self.wall_color.x, self.wall_color.y, self.wall_color.z],
            "wall_height": self.wall_height,
        }

    @classmethod
    def from_dict(cls, data: object) -> TileMap:
        if not isinstance(data, dict):
            raise TypeError("tile map document must be a mapping")
        unknown = sorted(set(data) - _DOCUMENT_KEYS)
        if unknown:
            raise ValueError(f"tile map document has unknown fields: {', '.join(unknown)}")
        schema = data.get("schema", 1)
        if isinstance(schema, bool) or not isinstance(schema, int) or schema != 1:
            raise ValueError("unsupported tile map document schema")
        raw_solid = data.get("solid", ())
        if not isinstance(raw_solid, (list, tuple)):
            raise TypeError("tile map document solid cells must be a list")
        solid: list[Cell] = []
        for pair in raw_solid:
            if (
                not isinstance(pair, (list, tuple))
                or len(pair) != 2
                or not all(isinstance(part, int) and not isinstance(part, bool) for part in pair)
            ):
                raise TypeError("tile map document solid cells must be [x, y] integer pairs")
            solid.append((pair[0], pair[1]))
        raw_origin = data.get("origin", (0.0, 0.0, 0.0))
        raw_floor = data.get("floor_color", (0.30, 0.33, 0.38))
        raw_wall = data.get("wall_color", (0.55, 0.45, 0.35))
        for label, value in (("origin", raw_origin), ("floor_color", raw_floor), ("wall_color", raw_wall)):
            if not isinstance(value, (list, tuple)) or len(value) != 3:
                raise ValueError(f"tile map document {label} must hold three numbers")
        return cls(
            width=_positive_int("tile map width", data.get("width")),
            height=_positive_int("tile map height", data.get("height")),
            tile_size=data.get("tile_size", 1.0),  # type: ignore[arg-type]
            origin=Vec3(*raw_origin),
            solid=frozenset(solid),
            floor_color=Vec3(*raw_floor),
            wall_color=Vec3(*raw_wall),
            wall_height=data.get("wall_height", 1.0),  # type: ignore[arg-type]
        )


def tilemap_report(tiles: TileMap) -> dict:
    """Return a JSON-safe summary of a tile map for agents and diagnostics."""
    if not isinstance(tiles, TileMap):
        raise TypeError("tilemap_report needs a TileMap")
    solid = len(tiles.solid)
    return {
        "schema": 1,
        "width": tiles.width,
        "height": tiles.height,
        "tile_size": tiles.tile_size,
        "wall_height": tiles.wall_height,
        "solid": solid,
        "free": tiles.width * tiles.height - solid,
        "bounds": {
            "min": [tiles.origin.x, tiles.origin.y, tiles.origin.z],
            "max": [
                tiles.origin.x + tiles.width * tiles.tile_size,
                tiles.origin.y + tiles.wall_height,
                tiles.origin.z + tiles.height * tiles.tile_size,
            ],
        },
    }
