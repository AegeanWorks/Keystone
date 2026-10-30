"""Seeded star systems, orbiting bodies and hyperlane connections."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from itertools import pairwise

SYSTEM_NAMES = ("Vela", "Orion", "Kepler", "Lyra", "Draco", "Cygnus")
BODY_NAMES = ("Aster", "Cinder", "Neri", "Talon", "Vesper", "Morrow")
PLANET_KINDS = (
    ("terrestrial", (0.3, 0.65, 0.32), 1.1),
    ("oceanic", (0.2, 0.45, 0.75), 1.3),
    ("desert", (0.78, 0.6, 0.3), 1.2),
    ("ice", (0.65, 0.82, 0.95), 1.0),
    ("gas_giant", (0.55, 0.4, 0.72), 2.0),
)


@dataclass
class Body:
    body_id: str
    name: str
    kind: str
    orbit_radius: float
    orbit_speed: float
    phase: float
    radius: float
    color: tuple[float, float, float]
    scanned: bool = False

    def position(self, time: float) -> tuple[float, float, float]:
        if self.orbit_radius == 0.0:
            return (0.0, 0.0, 0.0)
        angle = self.phase + self.orbit_speed * time
        return (math.cos(angle) * self.orbit_radius, 0.0, math.sin(angle) * self.orbit_radius)


@dataclass
class StarSystem:
    system_id: str
    name: str
    seed: int
    bodies: tuple[Body, ...]
    connections: tuple[str, ...]

    @property
    def star(self) -> Body:
        return self.bodies[0]

    def body(self, body_id: str) -> Body:
        for body in self.bodies:
            if body.body_id == body_id:
                return body
        raise ValueError(f"unknown body '{body_id}'")


@dataclass
class Galaxy:
    seed: int
    systems: dict[str, StarSystem]
    start_id: str

    @classmethod
    def generate(cls, seed: int, count: int = 6) -> Galaxy:
        if count < 2:
            raise ValueError("a galaxy needs at least two systems")
        rng = random.Random(seed)
        systems: dict[str, StarSystem] = {}
        ids = [f"sys-{index + 1}" for index in range(count)]
        for index, system_id in enumerate(ids):
            bodies: list[Body] = [
                Body(f"{system_id}-star", f"{SYSTEM_NAMES[index % len(SYSTEM_NAMES)]} Prime", "star", 0.0, 0.0, 0.0, 2.4, (1.0, 0.8, 0.3))
            ]
            for body_index, (kind, color, radius) in enumerate(PLANET_KINDS):
                bodies.append(
                    Body(
                        f"{system_id}-body-{body_index + 1}",
                        f"{BODY_NAMES[body_index]} {'I' * (body_index + 1)}",
                        kind,
                        8.0 + body_index * 4.5,
                        0.045 + body_index * 0.012,
                        rng.uniform(0.0, math.tau),
                        radius,
                        color,
                    )
                )
            systems[system_id] = StarSystem(
                system_id,
                SYSTEM_NAMES[index % len(SYSTEM_NAMES)],
                rng.randrange(1, 1_000_000),
                tuple(bodies),
                (),
            )
        connections: dict[str, list[str]] = {system_id: [] for system_id in ids}
        for first, second in pairwise(ids):
            connections[first].append(second)
            connections[second].append(first)
        connections[ids[0]].append(ids[-1])
        connections[ids[-1]].append(ids[0])
        for system_id in ids:
            system = systems[system_id]
            systems[system_id] = StarSystem(
                system.system_id,
                system.name,
                system.seed,
                system.bodies,
                tuple(sorted(set(connections[system_id]))),
            )
        return cls(seed, systems, ids[0])

    def system(self, system_id: str) -> StarSystem:
        if system_id not in self.systems:
            raise ValueError(f"unknown system '{system_id}'")
        return self.systems[system_id]


def body_snapshot(body: Body, time: float) -> dict:
    x, y, z = body.position(time)
    return {
        "id": body.body_id,
        "name": body.name,
        "kind": body.kind,
        "x": round(x, 3),
        "y": round(y, 3),
        "z": round(z, 3),
        "radius": body.radius,
        "scanned": body.scanned,
    }
