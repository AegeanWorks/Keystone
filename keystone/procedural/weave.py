"""Weft-style Hamiltonian weave routes that become a chain of dungeon rooms."""

from __future__ import annotations

import random
from dataclasses import dataclass

from keystone.procedural.dungeon import Dungeon, Room, Tile

THREAD_COLORS = (
    (0.92, 0.3, 0.28),
    (0.25, 0.55, 0.9),
    (0.3, 0.8, 0.45),
    (0.95, 0.7, 0.2),
    (0.7, 0.4, 0.85),
    (0.2, 0.8, 0.8),
)

Point = tuple[int, int]


def _neighbours(cell: Point, cols: int, rows: int) -> list[Point]:
    x, z = cell
    candidates = ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1))
    return [(nx, nz) for nx, nz in candidates if 0 <= nx < cols and 0 <= nz < rows]


def _remaining_connected(cols: int, rows: int, visited: set[Point]) -> bool:
    unvisited = {(x, z) for x in range(cols) for z in range(rows)} - visited
    if not unvisited:
        return True
    start = next(iter(unvisited))
    seen = {start}
    queue = [start]
    while queue:
        current = queue.pop()
        for neighbour in _neighbours(current, cols, rows):
            if neighbour in unvisited and neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return seen == unvisited


def _search_path(
    cols: int,
    rows: int,
    rng: random.Random,
    path: list[Point],
    visited: set[Point],
    nodes: list[int],
    total: int,
) -> bool:
    if len(path) == total:
        return True
    nodes[0] += 1
    if nodes[0] > 120_000:
        return False
    current = path[-1]
    candidates = [point for point in _neighbours(current, cols, rows) if point not in visited]
    candidates.sort(
        key=lambda point: (
            sum(1 for neighbour in _neighbours(point, cols, rows) if neighbour not in visited),
            rng.random(),
        )
    )
    for candidate in candidates:
        visited.add(candidate)
        path.append(candidate)
        if (len(path) == total or _remaining_connected(cols, rows, visited)) and _search_path(
            cols, rows, rng, path, visited, nodes, total
        ):
            return True
        path.pop()
        visited.remove(candidate)
    return False


def _hamiltonian_path(cols: int, rows: int, rng: random.Random) -> tuple[Point, ...]:
    total = cols * rows
    for _ in range(24):
        start = (rng.randrange(cols), rng.randrange(rows))
        path: list[Point] = [start]
        visited: set[Point] = {start}
        if _search_path(cols, rows, rng, path, visited, [0], total):
            return tuple(path)
    raise ValueError(f"no Hamiltonian path found for {cols}x{rows}")


@dataclass(frozen=True, slots=True)
class WeaveLayout:
    seed: int
    cols: int
    rows: int
    path: tuple[Point, ...]
    segments: tuple[tuple[Point, ...], ...]
    colors: tuple[tuple[float, float, float], ...]

    @classmethod
    def generate(cls, seed: int, cols: int = 4, rows: int = 3, threads: int = 3) -> WeaveLayout:
        if cols * rows < threads * 3:
            raise ValueError("a weave needs at least three cells per thread")
        if threads > len(THREAD_COLORS):
            raise ValueError("not enough thread colors")
        rng = random.Random(seed)
        path = _hamiltonian_path(cols, rows, rng)
        base, extra = divmod(len(path), threads)
        segments: list[tuple[Point, ...]] = []
        offset = 0
        for index in range(threads):
            length = base + (1 if index < extra else 0)
            segments.append(path[offset : offset + length])
            offset += length
        return cls(seed, cols, rows, path, tuple(segments), THREAD_COLORS[:threads])

    def _segment_index(self, step: int) -> int:
        offset = 0
        for index, segment in enumerate(self.segments):
            if step < offset + len(segment):
                return index
            offset += len(segment)
        return len(self.segments) - 1

    @property
    def width(self) -> int:
        return self.cols * 8 + 1

    @property
    def height(self) -> int:
        return self.rows * 8 + 1

    def room_for(self, cell: Point) -> Room:
        return Room(1 + cell[0] * 8, 1 + cell[1] * 8, 7, 7)

    def floor_color(self, x: int, z: int) -> tuple[float, float, float] | None:
        if x < 1 or z < 1:
            return None
        cx, cz = (x - 1) // 8, (z - 1) // 8
        if (cx, cz) not in self.path:
            return None
        if not (1 <= x - cx * 8 <= 7 and 1 <= z - cz * 8 <= 7):
            return None
        step = self.path.index((cx, cz))
        return self.colors[self._segment_index(step)]

    def to_dungeon(self) -> Dungeon:
        tiles = [[Tile.WALL for _ in range(self.width)] for _ in range(self.height)]
        rooms = [self.room_for(cell) for cell in self.path]
        for room in rooms:
            for z in range(room.y, room.y + room.h):
                for x in range(room.x, room.x + room.w):
                    tiles[z][x] = Tile.FLOOR
        for first, second in zip(self.path, self.path[1:]):
            self._carve(tiles, self.room_for(first).center, self.room_for(second).center)
        spawn = self.room_for(self.path[0]).center
        exit_cell = self.room_for(self.path[-1]).center
        tiles[exit_cell[1]][exit_cell[0]] = Tile.EXIT
        return Dungeon(self.width, self.height, self.seed, tiles, rooms, spawn, exit_cell)

    def _carve(self, tiles: list[list[int]], start: Point, end: Point) -> None:
        x, z = start
        while x != end[0]:
            x += 1 if end[0] > x else -1
            tiles[z][x] = Tile.FLOOR
        while z != end[1]:
            z += 1 if end[1] > z else -1
            tiles[z][x] = Tile.FLOOR

    def snapshot(self) -> dict:
        return {
            "cols": self.cols,
            "rows": self.rows,
            "path": [list(point) for point in self.path],
            "segments": [[list(point) for point in segment] for segment in self.segments],
            "colors": [list(color) for color in self.colors],
        }
