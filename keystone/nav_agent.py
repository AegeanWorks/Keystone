"""A reusable agent that walks a nav route with collision and local avoidance.

This is the integration layer over route planning, smoothing, waypoint
following, steering and `CharacterController`: a game creates one agent per
character and calls `step(dt, obstacles, neighbours)`. The agent owns its
body, reports JSON-safe progress, and replans only when asked, so a game keeps
control of when navigation data changes.

The agent is deliberately not a component and not tied to a scene node; it
takes plain values, which keeps it testable without a window.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from keystone.character import CharacterBody, CharacterController
from keystone.math3d import Vec3
from keystone.navigation import PathFollower, grid_path_points, navigation_report
from keystone.pathfinding import Cell, NavGrid, find_path, smooth_path
from keystone.steering import Agent, steer

__all__ = ["NavAgent", "nav_agent_report"]


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


def _agent_cell(grid: NavGrid, position: Vec3, cell_size: float, origin: Vec3) -> Cell:
    x = math.floor((position.x - origin.x) / cell_size)
    z = math.floor((position.z - origin.z) / cell_size)
    cell = (int(x), int(z))
    if not grid.in_bounds(cell):
        raise ValueError(f"agent position is outside the nav grid (cell {cell!r})")
    if not grid.is_open(cell):
        raise ValueError(f"agent start cell {cell!r} is blocked")
    return cell


class NavAgent:
    """One character that walks a `NavGrid` route with a controller.

    ``set_goal`` plans and smooths a route; ``step`` advances the body and
    returns a report. The agent recomputes the route only on ``set_goal`` or
    ``replan``, because a grid change is a game decision, not a per-frame one.
    """

    def __init__(
        self,
        grid: NavGrid,
        controller: CharacterController,
        body: CharacterBody,
        *,
        cell_size: float = 1.0,
        origin: Vec3 | None = None,
        height: float | None = None,
        speed: float = 3.0,
        arrive_radius: float = 0.12,
        diagonal: bool = True,
        smooth: bool = True,
        separation_weight: float = 1.5,
    ) -> None:
        if not isinstance(grid, NavGrid):
            raise TypeError("nav agent needs a NavGrid")
        if not isinstance(controller, CharacterController):
            raise TypeError("nav agent needs a CharacterController")
        if not isinstance(body, CharacterBody):
            raise TypeError("nav agent needs a CharacterBody")
        size = _finite("nav agent cell size", cell_size)
        if size <= 0.0:
            raise ValueError("nav agent cell size must be positive")
        start = Vec3() if origin is None else _point("nav agent origin", origin)
        level = body.position.y if height is None else _finite("nav agent height", height)
        if _finite("nav agent speed", speed) <= 0.0:
            raise ValueError("nav agent speed must be positive")
        if _finite("nav agent arrive radius", arrive_radius) <= 0.0:
            raise ValueError("nav agent arrive radius must be positive")
        if not isinstance(diagonal, bool):
            raise TypeError("nav agent diagonal must be a boolean")
        if not isinstance(smooth, bool):
            raise TypeError("nav agent smooth must be a boolean")
        if _finite("nav agent separation weight", separation_weight) < 0.0:
            raise ValueError("nav agent separation weight must be non-negative")
        self.grid = grid
        self.controller = controller
        self.body = body
        self.cell_size = size
        self.origin = start
        self.height = level
        self.speed = speed
        self.arrive_radius = arrive_radius
        self.diagonal = diagonal
        self.smooth = smooth
        self.separation_weight = separation_weight
        self.follower = PathFollower((), speed, arrive_radius)
        self.goal: Cell | None = None
        self.last_plan_found = False

    @property
    def position(self) -> Vec3:
        return self.body.position

    @property
    def done(self) -> bool:
        return self.goal is None or self.follower.done

    def current_cell(self) -> Cell:
        return _agent_cell(self.grid, self.body.position, self.cell_size, self.origin)

    def set_goal(self, goal: Cell) -> bool:
        """Plan to ``goal``; return False and clear the route when unreachable."""
        if (
            not isinstance(goal, tuple)
            or len(goal) != 2
            or not all(isinstance(part, int) and not isinstance(part, bool) for part in goal)
        ):
            raise TypeError("nav agent goal must be an (x, y) integer tuple")
        if not self.grid.in_bounds(goal):
            raise ValueError(f"nav agent goal {goal!r} is outside the grid")
        if not self.grid.is_open(goal):
            raise ValueError(f"nav agent goal {goal!r} is blocked")
        start = self.current_cell()
        result = find_path(self.grid, start, goal, diagonal=self.diagonal)
        if not result.found:
            self.goal = None
            self.last_plan_found = False
            self.follower = PathFollower((), self.speed, self.arrive_radius)
            return False
        cells = smooth_path(self.grid, result.path) if self.smooth else result.path
        points = grid_path_points(
            cells,
            cell_size=self.cell_size,
            origin=self.origin,
            height=self.height,
        )
        self.follower = PathFollower(points, self.speed, self.arrive_radius)
        self.goal = goal
        self.last_plan_found = True
        return True

    def replan(self) -> bool:
        """Recompute the route to the current goal, if one is set."""
        if self.goal is None:
            return False
        return self.set_goal(self.goal)

    def step(
        self,
        dt: float,
        obstacles: Iterable[object] = (),
        neighbours: Iterable[NavAgent] = (),
    ) -> dict:
        """Advance the body one step and return a JSON-safe progress report."""
        seconds = _finite("nav agent dt", dt)
        if seconds <= 0.0:
            raise ValueError("nav agent dt must be positive")
        wish, finished = self.follower.advance(self.body.position)
        if finished:
            self.goal = None
            return nav_agent_report(self)
        if self.separation_weight > 0.0:
            others = []
            for other in neighbours:
                if not isinstance(other, NavAgent):
                    raise TypeError("nav agent neighbours must be NavAgents")
                if other is self:
                    continue
                others.append(
                    Agent(
                        position=other.body.position,
                        radius=max(other.body.half_extents.x, other.body.half_extents.z),
                        max_speed=other.speed,
                    )
                )
            if others:
                own = Agent(
                    position=self.body.position,
                    radius=max(self.body.half_extents.x, self.body.half_extents.z),
                    max_speed=self.speed,
                )
                wish = steer(
                    own,
                    wish,
                    others,
                    separation_weight=self.separation_weight,
                )
        self.body = self.controller.step(self.body, wish, seconds, obstacles)
        if self.follower.done:
            self.goal = None
        return nav_agent_report(self)


def nav_agent_report(agent: NavAgent) -> dict:
    """Return a JSON-safe summary of an agent's progress and body."""
    if not isinstance(agent, NavAgent):
        raise TypeError("nav_agent_report needs a NavAgent")
    body = agent.body
    following = navigation_report(agent.follower, body.position)
    return {
        "schema": 1,
        "done": agent.done,
        "goal": None if agent.goal is None else [agent.goal[0], agent.goal[1]],
        "plan_found": agent.last_plan_found,
        "position": [round(body.position.x, 6), round(body.position.y, 6), round(body.position.z, 6)],
        "velocity": [round(body.velocity.x, 6), round(body.velocity.y, 6), round(body.velocity.z, 6)],
        "on_ground": body.on_ground,
        "waypoint": following["waypoint"],
        "waypoints": following["waypoints"],
        "remaining_distance": following["remaining_distance"],
    }
