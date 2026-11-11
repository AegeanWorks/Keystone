"""Waypoint following that turns a path route into movement.

`keystone.pathfinding` answers where to go; this module turns that route into
a wish velocity a character controller can consume. The follower advances by
the position the caller reports back, not by time, so collision response stays
in charge: if a wall holds a body in place, the follower keeps pointing at the
same waypoint instead of skipping ahead.

Waypoints are plain world-space ``Vec3`` points. ``grid_path_points`` is the
convenience bridge from ``NavGrid`` cells to those points; the follower itself
does not know what produced its route.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from keystone.math3d import Vec3

__all__ = ["PathFollower", "grid_path_points", "navigation_report"]

Cell = tuple[int, int]


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _finite_vec3(value: object, label: str) -> Vec3:
    if not isinstance(value, Vec3):
        raise TypeError(f"{label} must be a Vec3")
    if not all(math.isfinite(component) for component in (value.x, value.y, value.z)):
        raise ValueError(f"{label} must contain finite components")
    return value


def _cell(value: object) -> Cell:
    if (
        isinstance(value, tuple)
        and len(value) == 2
        and all(isinstance(part, int) and not isinstance(part, bool) for part in value)
    ):
        return (value[0], value[1])
    raise ValueError("nav cells must be (x, y) integer tuples")


@dataclass
class PathFollower:
    """Follow a world-space waypoint route with a fixed speed.

    ``advance(position)`` returns ``(wish_velocity, done)``. The next waypoint
    is the first one farther than ``arrive_radius`` from the reported position,
    so a route that starts on the first cell skips it automatically, and a
    route consumed to the end reports ``done`` forever.
    """

    path: tuple[Vec3, ...] = ()
    speed: float = 3.0
    arrive_radius: float = 0.12
    index: int = 0

    def __post_init__(self) -> None:
        try:
            path = tuple(self.path)
        except TypeError as exc:
            raise TypeError("path must be an iterable of Vec3 waypoints") from exc
        for point in path:
            _finite_vec3(point, "waypoint")
        object.__setattr__(self, "path", path)
        if _finite(self.speed, "speed") <= 0.0:
            raise ValueError("follower speed must be positive")
        if _finite(self.arrive_radius, "arrive radius") <= 0.0:
            raise ValueError("follower arrive radius must be positive")
        if isinstance(self.index, bool) or not isinstance(self.index, int):
            raise TypeError("follower index must be an integer")
        if not 0 <= self.index <= len(path):
            raise ValueError("follower index must point inside the path")

    @property
    def done(self) -> bool:
        return self.index >= len(self.path)

    @property
    def target(self) -> Vec3 | None:
        return None if self.done else self.path[self.index]

    def _skip_reached(self, position: Vec3) -> None:
        while not self.done:
            if (self.path[self.index] - position).length() > self.arrive_radius:
                return
            self.index += 1

    def advance(self, position: Vec3) -> tuple[Vec3, bool]:
        """Return the wish velocity toward the next waypoint and the done flag."""
        here = _finite_vec3(position, "follower position")
        self._skip_reached(here)
        if self.done:
            return (Vec3(), True)
        offset = self.path[self.index] - here
        distance = offset.length()
        if distance <= 1e-12:
            return (Vec3(), False)
        return (offset * (self.speed / distance), False)

    def remaining_distance(self, position: Vec3) -> float:
        """Straight-line distance from ``position`` through the route ahead."""
        here = _finite_vec3(position, "follower position")
        if self.done:
            return 0.0
        total = (self.path[self.index] - here).length()
        for current, following in zip(self.path[self.index :], self.path[self.index + 1 :]):
            total += (following - current).length()
        return total


def grid_path_points(
    cells: Iterable[Cell],
    *,
    cell_size: float = 1.0,
    origin: Vec3 | None = None,
    height: float = 0.0,
) -> tuple[Vec3, ...]:
    """Convert grid cells to world-space cell centres on a horizontal plane."""
    if _finite(cell_size, "cell size") <= 0.0:
        raise ValueError("cell size must be positive")
    start = Vec3() if origin is None else _finite_vec3(origin, "grid origin")
    y = _finite(height, "route height")
    points: list[Vec3] = []
    for raw in cells:
        x, z = _cell(raw)
        points.append(
            Vec3(
                start.x + (x + 0.5) * cell_size,
                start.y + y,
                start.z + (z + 0.5) * cell_size,
            )
        )
    return tuple(points)


def navigation_report(follower: PathFollower, position: Vec3) -> dict:
    """Return a JSON-safe follower state for frame or agent reports."""
    if not isinstance(follower, PathFollower):
        raise TypeError("navigation_report needs a PathFollower")
    here = _finite_vec3(position, "follower position")
    target = follower.target
    return {
        "schema": 1,
        "done": follower.done,
        "waypoint": follower.index,
        "waypoints": len(follower.path),
        "target": None if target is None else [target.x, target.y, target.z],
        "remaining_distance": round(follower.remaining_distance(here), 6),
        "speed": follower.speed,
    }
