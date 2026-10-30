"""Deterministic 2D light-routing lock: mirrors, dye, color masks and receivers."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

RED = 1
GREEN = 2
BLUE = 4

DIRECTIONS = {"n": (0, -1), "e": (1, 0), "s": (0, 1), "w": (-1, 0)}
FORWARD = {"/": {"n": "e", "e": "n", "s": "w", "w": "s"}}
BACKSLASH = {"\\": {"n": "w", "e": "s", "s": "e", "w": "n"}}
COLOR_NAMES = {0: "none", 1: "red", 2: "green", 3: "yellow", 4: "blue", 5: "magenta", 6: "cyan", 7: "white"}


@dataclass(frozen=True, slots=True)
class BeamSegment:
    start: tuple[int, int]
    end: tuple[int, int]
    mask: int


class LightLock:
    """A fixed five-cell light circuit whose mirrors seal the crypt portal."""

    X_MIN, X_MAX = -4, 2
    Z_MIN, Z_MAX = -1, 4

    def __init__(self, seed: int, origin: tuple[float, float] = (0.0, 0.0)) -> None:
        self.seed = int(seed)
        self.origin = origin
        self.emitter = (-3, 0, "e", RED)
        self.receiver = (-3, 2, RED | GREEN)
        self.dye = {(-1, 1): GREEN}
        rng = random.Random(self.seed)
        self.mirrors = {
            (-1, 0): rng.choice(("/", "\\")),
            (-1, 2): rng.choice(("/", "\\")),
        }
        self.version = 0
        self._solved = False
        self.trace()
        if self._solved:
            self.set_orientation(-1, 0, "/" if self.mirrors[(-1, 0)] == "\\" else "\\")

    def in_bounds(self, x: int, z: int) -> bool:
        return self.X_MIN <= x <= self.X_MAX and self.Z_MIN <= z <= self.Z_MAX

    def trace(self) -> tuple[BeamSegment, ...]:
        x, z, direction, mask = self.emitter
        segments: list[BeamSegment] = []
        seen: set[tuple[int, int, str, int]] = set()
        self._solved = False
        for _ in range(128):
            state = (x, z, direction, mask)
            if state in seen:
                break
            seen.add(state)
            dx, dz = DIRECTIONS[direction]
            nx, nz = x + dx, z + dz
            if not self.in_bounds(nx, nz):
                break
            segments.append(BeamSegment((x, z), (nx, nz), mask))
            x, z = nx, nz
            if (x, z) in self.dye:
                mask |= self.dye[(x, z)]
            if (x, z) in self.mirrors:
                table = FORWARD if self.mirrors[(x, z)] == "/" else BACKSLASH
                direction = table[self.mirrors[(x, z)]][direction]
            if (x, z) == self.receiver[:2]:
                self._solved = mask == self.receiver[2]
                break
        return tuple(segments)

    @property
    def solved(self) -> bool:
        self.trace()
        return self._solved

    def rotate(self, x: int, z: int) -> None:
        if (x, z) not in self.mirrors:
            raise ValueError(f"no mirror at {x},{z}")
        self.mirrors[(x, z)] = "/" if self.mirrors[(x, z)] == "\\" else "\\"
        self.version += 1
        self.trace()

    def set_orientation(self, x: int, z: int, orientation: str) -> None:
        if (x, z) not in self.mirrors:
            raise ValueError(f"no mirror at {x},{z}")
        if orientation not in ("/", "\\"):
            raise ValueError("mirror orientation must be '/' or '\\'")
        self.mirrors[(x, z)] = orientation
        self.version += 1
        self.trace()

    def nearest_mirror(self, world_x: float, world_z: float, radius: float = 1.6) -> tuple[int, int] | None:
        local_x, local_z = world_x - self.origin[0], world_z - self.origin[1]
        best: tuple[int, int] | None = None
        best_distance = radius
        for x, z in self.mirrors:
            distance = math.hypot(local_x - x, local_z - z)
            if distance <= best_distance:
                best, best_distance = (x, z), distance
        return best

    def snapshot(self) -> dict:
        return {
            "origin": [round(value, 3) for value in self.origin],
            "emitter": list(self.emitter),
            "receiver": [self.receiver[0], self.receiver[1], self.receiver[2]],
            "dye": [[x, z, mask] for (x, z), mask in sorted(self.dye.items())],
            "mirrors": [
                {"x": x, "z": z, "orientation": orientation}
                for (x, z), orientation in sorted(self.mirrors.items())
            ],
            "solved": self.solved,
        }


def mask_to_rgb(mask: int) -> tuple[float, float, float]:
    return (
        1.0 if mask & RED else 0.05,
        1.0 if mask & GREEN else 0.05,
        1.0 if mask & BLUE else 0.05,
    )
