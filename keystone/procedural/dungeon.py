"""Seeded room-and-corridor dungeon generation with FOV and pathfinding."""

from __future__ import annotations

import collections
import math
import random
from dataclasses import dataclass, field
from typing import Any


class Tile:
    WALL = 0
    FLOOR = 1
    EXIT = 2


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def intersects(self, other: Room, padding: int = 1) -> bool:
        return (
            self.x - padding < other.x + other.w
            and self.x + self.w + padding > other.x
            and self.y - padding < other.y + other.h
            and self.y + self.h + padding > other.y
        )


@dataclass
class Dungeon:
    width: int
    height: int
    seed: int
    tiles: list[list[int]]
    rooms: list[Room] = field(default_factory=list)
    spawn: tuple[int, int] = (0, 0)
    exit: tuple[int, int] = (0, 0)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        if not self.in_bounds(x, y):
            return False
        return self.tiles[y][x] in (Tile.FLOOR, Tile.EXIT)

    def compute_fov(self, px: int, py: int, radius: int = 8) -> set[tuple[int, int]]:
        """Symmetric raycasting with distance attenuation, as in Crypt-Crawler."""
        visible: set[tuple[int, int]] = set()
        if not self.in_bounds(px, py):
            return visible
        visible.add((px, py))
        for index in range(max(64, radius * 16)):
            angle = math.tau * index / max(64, radius * 16)
            dx, dy = math.cos(angle), math.sin(angle)
            cx, cy = px + 0.5, py + 0.5
            for _ in range(radius):
                cx += dx
                cy += dy
                tx, ty = math.floor(cx), math.floor(cy)
                if not self.in_bounds(tx, ty):
                    break
                if (tx - px) ** 2 + (ty - py) ** 2 <= radius * radius:
                    visible.add((tx, ty))
                if not self.is_walkable(tx, ty):
                    break
        return visible

    def find_path(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
        if not self.is_walkable(*start) or not self.is_walkable(*goal):
            return None
        if start == goal:
            return [start]
        queue = collections.deque([start])
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                neighbour = (current[0] + dx, current[1] + dy)
                if self.is_walkable(*neighbour) and neighbour not in came_from:
                    came_from[neighbour] = current
                    queue.append(neighbour)
        if goal not in came_from:
            return None
        path: list[tuple[int, int]] = []
        node: tuple[int, int] | None = goal
        while node is not None:
            path.append(node)
            node = came_from[node]
        return list(reversed(path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "spawn": list(self.spawn),
            "exit": list(self.exit),
            "rooms": [
                {"x": room.x, "y": room.y, "w": room.w, "h": room.h}
                for room in self.rooms
            ],
            "tiles": self.tiles,
        }


class DungeonGenerator:
    """Carve non-overlapping rooms and connect them with L-shaped corridors."""

    def __init__(
        self,
        width: int = 33,
        height: int = 21,
        min_room: int = 4,
        max_room: int = 7,
        max_rooms: int = 8,
    ) -> None:
        if width < 16 or height < 12:
            raise ValueError("dungeon must be at least 16x12")
        if min_room < 3 or max_room < min_room:
            raise ValueError("room sizes must satisfy 3 <= min_room <= max_room")
        self.width = width
        self.height = height
        self.min_room = min_room
        self.max_room = max_room
        self.max_rooms = max_rooms

    def generate(self, seed: int) -> Dungeon:
        rng = random.Random(seed)
        dungeon = Dungeon(
            self.width,
            self.height,
            seed,
            [[Tile.WALL for _ in range(self.width)] for _ in range(self.height)],
        )
        for _ in range(300):
            if len(dungeon.rooms) >= self.max_rooms:
                break
            width = rng.randint(self.min_room, self.max_room)
            height = rng.randint(self.min_room, self.max_room)
            room = Room(
                rng.randint(1, self.width - width - 2),
                rng.randint(1, self.height - height - 2),
                width,
                height,
            )
            if any(room.intersects(other) for other in dungeon.rooms):
                continue
            for y in range(room.y, room.y + room.h):
                for x in range(room.x, room.x + room.w):
                    dungeon.tiles[y][x] = Tile.FLOOR
            if dungeon.rooms:
                self._carve_corridor(dungeon, dungeon.rooms[-1].center, room.center, rng)
            dungeon.rooms.append(room)
        if len(dungeon.rooms) < 2:
            raise ValueError("dungeon generation found fewer than two rooms")
        dungeon.spawn = dungeon.rooms[0].center
        dungeon.exit = max(
            dungeon.rooms[1:],
            key=lambda room: abs(room.center[0] - dungeon.spawn[0])
            + abs(room.center[1] - dungeon.spawn[1]),
        ).center
        dungeon.tiles[dungeon.exit[1]][dungeon.exit[0]] = Tile.EXIT
        return dungeon

    def _carve_corridor(
        self,
        dungeon: Dungeon,
        start: tuple[int, int],
        end: tuple[int, int],
        rng: random.Random,
    ) -> None:
        if rng.random() < 0.5:
            self._carve_h(dungeon, start[0], end[0], start[1])
            self._carve_v(dungeon, start[1], end[1], end[0])
        else:
            self._carve_v(dungeon, start[1], end[1], start[0])
            self._carve_h(dungeon, start[0], end[0], end[1])

    @staticmethod
    def _carve_h(dungeon: Dungeon, x0: int, x1: int, y: int) -> None:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            dungeon.tiles[y][x] = Tile.FLOOR

    @staticmethod
    def _carve_v(dungeon: Dungeon, y0: int, y1: int, x: int) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            dungeon.tiles[y][x] = Tile.FLOOR
