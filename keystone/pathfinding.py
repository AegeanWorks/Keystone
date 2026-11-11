"""Deterministic A* pathfinding over a bounded 4- or 8-connected grid.

The grid is plain data: a width, a height and an immutable set of blocked
cells. Nothing here knows about meshes, physics or a scene, so an AI can
author a nav layout, ask for a route and diff the JSON report without a
window. A* is deterministic by construction: neighbours are visited in a
fixed order and ties break on (x, y), so the same grid and endpoints always
yield the same path and the same expansion count.

Diagonal moves cannot cut a corner: a diagonal step is legal only when both
orthogonal cells beside it are open, which keeps agents from clipping through
wall corners.
"""

from __future__ import annotations

import heapq
import itertools
import math
from dataclasses import dataclass

__all__ = ["NavGrid", "PathResult", "find_path", "line_of_sight", "path_report", "smooth_path"]

Cell = tuple[int, int]

_NEIGHBOURS_4: tuple[Cell, ...] = ((1, 0), (0, 1), (-1, 0), (0, -1))
_NEIGHBOURS_8: tuple[Cell, ...] = (
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (-1, -1),
    (0, -1),
    (1, -1),
)
_SQRT2 = math.sqrt(2.0)
_EPSILON = 1e-12


def _check_cell(value: object, label: str) -> Cell:
    if (
        isinstance(value, tuple)
        and len(value) == 2
        and all(isinstance(part, int) and not isinstance(part, bool) for part in value)
    ):
        return (value[0], value[1])
    raise TypeError(f"{label} must be an (x, y) integer tuple")


@dataclass(frozen=True, slots=True)
class NavGrid:
    """A bounded grid with immutable blocked cells."""

    width: int
    height: int
    blocked: frozenset[Cell] = frozenset()

    def __post_init__(self) -> None:
        if isinstance(self.width, bool) or not isinstance(self.width, int) or self.width < 1:
            raise ValueError("nav grid width must be a positive integer")
        if isinstance(self.height, bool) or not isinstance(self.height, int) or self.height < 1:
            raise ValueError("nav grid height must be a positive integer")
        try:
            blocked = frozenset(self.blocked)
        except TypeError as exc:
            raise TypeError("nav grid blocked cells must be (x, y) integer tuples") from exc
        for cell in blocked:
            checked = _check_cell(cell, "blocked cell")
            if not self.in_bounds(checked):
                raise ValueError(f"blocked cell {checked!r} is outside the grid")
        object.__setattr__(self, "blocked", blocked)

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def is_open(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and cell not in self.blocked

    def with_blocked(self, *cells: Cell) -> NavGrid:
        """Return a copy with these cells blocked, leaving this grid unchanged."""
        return NavGrid(self.width, self.height, self.blocked | frozenset(cells))

    def with_open(self, *cells: Cell) -> NavGrid:
        """Return a copy with these cells opened, leaving this grid unchanged."""
        return NavGrid(self.width, self.height, self.blocked - frozenset(cells))

    def to_dict(self) -> dict:
        """Return a JSON-safe document with blocked cells in stable order."""
        return {
            "schema": 1,
            "width": self.width,
            "height": self.height,
            "blocked": [[x, y] for x, y in sorted(self.blocked)],
        }

    @classmethod
    def from_dict(cls, data: dict) -> NavGrid:
        """Load a grid document, rejecting malformed or out-of-bounds cells."""
        if not isinstance(data, dict):
            raise TypeError("nav grid document must be a mapping")
        schema = data.get("schema", 1)
        if isinstance(schema, bool) or not isinstance(schema, int) or schema != 1:
            raise ValueError("unsupported nav grid schema")
        width = data.get("width")
        height = data.get("height")
        for name, value in (("width", width), ("height", height)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"nav grid document {name} must be a positive integer")
        raw = data.get("blocked", ())
        if not isinstance(raw, (list, tuple)):
            raise TypeError("nav grid document blocked cells must be a list")
        blocked: list[Cell] = []
        seen: set[Cell] = set()
        for pair in raw:
            if (
                not isinstance(pair, (list, tuple))
                or len(pair) != 2
                or not all(isinstance(part, int) and not isinstance(part, bool) for part in pair)
            ):
                raise TypeError("nav grid document blocked cells must be [x, y] integer pairs")
            cell = (pair[0], pair[1])
            if cell in seen:
                raise ValueError(f"nav grid document repeats blocked cell {cell!r}")
            seen.add(cell)
            blocked.append(cell)
        return cls(width, height, frozenset(blocked))


@dataclass(frozen=True, slots=True)
class PathResult:
    """The outcome of one search: the route, its cost and the expansion count."""

    start: Cell
    goal: Cell
    path: tuple[Cell, ...] = ()
    expanded: int = 0
    cost: float = 0.0

    @property
    def found(self) -> bool:
        return bool(self.path) and self.path[0] == self.start and self.path[-1] == self.goal


def _heuristic(cell: Cell, goal: Cell, diagonal: bool) -> float:
    dx = abs(goal[0] - cell[0])
    dy = abs(goal[1] - cell[1])
    if diagonal:
        return (dx + dy) + (_SQRT2 - 2.0) * min(dx, dy)
    return float(dx + dy)


def find_path(
    grid: NavGrid,
    start: Cell,
    goal: Cell,
    *,
    diagonal: bool = False,
) -> PathResult:
    """Search from ``start`` to ``goal`` and return a deterministic result.

    A blocked start or an endpoint outside the grid is a configuration error
    and raises; a blocked goal is simply unreachable and returns a not-found
    result, because the caller's map, not the call, is what says "no route".
    """
    if not isinstance(grid, NavGrid):
        raise TypeError("find_path needs a NavGrid")
    start_cell = _check_cell(start, "start")
    goal_cell = _check_cell(goal, "goal")
    for label, cell in (("start", start_cell), ("goal", goal_cell)):
        if not grid.in_bounds(cell):
            raise ValueError(f"{label} {cell!r} is outside the grid")
    if not grid.is_open(start_cell):
        raise ValueError(f"start {start_cell!r} is blocked")
    if not grid.is_open(goal_cell):
        return PathResult(start_cell, goal_cell, (), 0, 0.0)
    if start_cell == goal_cell:
        return PathResult(start_cell, goal_cell, (start_cell,), 1, 0.0)

    neighbours = _NEIGHBOURS_8 if diagonal else _NEIGHBOURS_4
    g_score: dict[Cell, float] = {start_cell: 0.0}
    came_from: dict[Cell, Cell] = {}
    start_h = _heuristic(start_cell, goal_cell, diagonal)
    heap: list[tuple[float, float, float, int, int]] = [
        (start_h, start_h, 0.0, start_cell[0], start_cell[1])
    ]
    expanded = 0
    while heap:
        _f, _h, current_g, x, y = heapq.heappop(heap)
        cell = (int(x), int(y))
        best = g_score.get(cell)
        if best is None or current_g > best + _EPSILON:
            continue
        expanded += 1
        if cell == goal_cell:
            return PathResult(start_cell, goal_cell, _reconstruct(came_from, cell), expanded, best)
        for dx, dy in neighbours:
            neighbour = (cell[0] + dx, cell[1] + dy)
            if not grid.is_open(neighbour):
                continue
            if dx and dy and not (grid.is_open((cell[0] + dx, cell[1])) and grid.is_open((cell[0], cell[1] + dy))):
                continue
            step = _SQRT2 if dx and dy else 1.0
            tentative = best + step
            if tentative < g_score.get(neighbour, math.inf) - _EPSILON:
                g_score[neighbour] = tentative
                came_from[neighbour] = cell
                estimate = _heuristic(neighbour, goal_cell, diagonal)
                heapq.heappush(
                    heap,
                    (
                        tentative + estimate,
                        estimate,
                        tentative,
                        float(neighbour[0]),
                        float(neighbour[1]),
                    ),
                )
    return PathResult(start_cell, goal_cell, (), expanded, 0.0)


def _reconstruct(came_from: dict[Cell, Cell], goal: Cell) -> tuple[Cell, ...]:
    path = [goal]
    cursor = goal
    while cursor in came_from:
        cursor = came_from[cursor]
        path.append(cursor)
    path.reverse()
    return tuple(path)


def _line_cells(start: Cell, goal: Cell) -> tuple[Cell, ...]:
    """Cells crossed by the segment between two cell centres (DDA)."""
    x0 = start[0] + 0.5
    y0 = start[1] + 0.5
    dx = goal[0] - start[0]
    dy = goal[1] - start[1]
    if dx == 0 and dy == 0:
        return (start,)
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    infinity = float("inf")
    delta_x = abs(1.0 / dx) if dx else infinity
    delta_y = abs(1.0 / dy) if dy else infinity
    if dx > 0:
        max_x = (start[0] + 1 - x0) / dx
    elif dx < 0:
        max_x = (start[0] - x0) / dx
    else:
        max_x = infinity
    if dy > 0:
        max_y = (start[1] + 1 - y0) / dy
    elif dy < 0:
        max_y = (start[1] - y0) / dy
    else:
        max_y = infinity
    cells = [start]
    cell = start
    guard = 4 * (abs(dx) + abs(dy) + 2)
    while cell != goal and guard > 0:
        guard -= 1
        if abs(max_x - max_y) <= 1e-12:
            cell = (cell[0] + step_x, cell[1] + step_y)
            max_x += delta_x
            max_y += delta_y
        elif max_x < max_y:
            cell = (cell[0] + step_x, cell[1])
            max_x += delta_x
        else:
            cell = (cell[0], cell[1] + step_y)
            max_y += delta_y
        cells.append(cell)
    return tuple(cells)


def line_of_sight(grid: NavGrid, start: Cell, goal: Cell) -> bool:
    """Whether a straight segment between two open cells crosses only open cells.

    The segment is the line between cell centres. A diagonal crossing is
    rejected when either orthogonal neighbour is blocked, matching the
    corner rule `find_path` uses, so a smoothed route cannot cut a wall
    corner that movement would refuse.
    """
    if not isinstance(grid, NavGrid):
        raise TypeError("line_of_sight needs a NavGrid")
    first = _check_cell(start, "line start")
    second = _check_cell(goal, "line goal")
    for label, cell in (("start", first), ("goal", second)):
        if not grid.in_bounds(cell):
            raise ValueError(f"line {label} {cell!r} is outside the grid")
    if not grid.is_open(first) or not grid.is_open(second):
        return False
    cells = _line_cells(first, second)
    if any(not grid.is_open(cell) for cell in cells):
        return False
    for before, after in itertools.pairwise(cells):
        dx = after[0] - before[0]
        dy = after[1] - before[1]
        if dx and dy and not (
            grid.is_open((before[0] + dx, before[1])) and grid.is_open((before[0], before[1] + dy))
        ):
            return False
    return True


def smooth_path(grid: NavGrid, path: tuple[Cell, ...] | list[Cell]) -> tuple[Cell, ...]:
    """Greedily drop waypoints whose straight replacement stays visible.

    Every segment in the result passes `line_of_sight`, so the route obeys the
    same blocked cells and corner rule as A* while using far fewer waypoints
    for a follower.
    """
    if not isinstance(grid, NavGrid):
        raise TypeError("smooth_path needs a NavGrid")
    try:
        raw = tuple(path)
    except TypeError as exc:
        raise TypeError("path must be an iterable of cells") from exc
    cells: list[Cell] = []
    for item in raw:
        cell = _check_cell(item, "path cell")
        if not grid.in_bounds(cell):
            raise ValueError(f"path cell {cell!r} is outside the grid")
        if not grid.is_open(cell):
            raise ValueError(f"path cell {cell!r} is blocked")
        cells.append(cell)
    if len(cells) <= 2:
        return tuple(cells)
    result = [cells[0]]
    anchor = 0
    last = len(cells) - 1
    while anchor < last:
        target = last
        chosen = anchor + 1
        while target > anchor + 1:
            if line_of_sight(grid, cells[anchor], cells[target]):
                chosen = target
                break
            target -= 1
        result.append(cells[chosen])
        anchor = chosen
    return tuple(result)


def path_report(result: PathResult) -> dict:
    """Return a JSON-safe summary of one search for frame or agent reports."""
    if not isinstance(result, PathResult):
        raise TypeError("path_report needs a PathResult")
    path = [[cell[0], cell[1]] for cell in result.path]
    return {
        "schema": 1,
        "found": result.found,
        "start": [result.start[0], result.start[1]],
        "goal": [result.goal[0], result.goal[1]],
        "path": path,
        "steps": max(0, len(path) - 1),
        "cost": round(result.cost, 6),
        "expanded": result.expanded,
    }
