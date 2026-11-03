"""Deterministic, game-agnostic CPU particles: emitters, systems and reports.

No window, GL context or third-party dependency is required. Spawning uses a
seeded RNG per particle index so the same call sequence always yields the
same trajectories. Games own their systems; the engine owns integration.
Rendering integration is a later step; systems already drive HUD, inspector
and AI reports through counts and snapshots.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass, field

from keystone.math3d import Vec3
from keystone.physics import AABB

__all__ = ["Emitter", "Particle", "ParticleSystem", "particles_report"]

POINT_SKIN = 1e-9

_AXES = ("x", "y", "z")


def _move_point_flat(
    px: float, py: float, pz: float, axis: int, amount: float, flat: list[tuple[float, float, float, float, float, float]]
) -> tuple[float, bool]:
    """Float-only swept point move; axis is 0/1/2 for x/y/z."""
    if abs(amount) < 1e-12:
        if axis == 0:
            return px, False
        if axis == 1:
            return py, False
        return pz, False
    if axis == 0:
        start = px
    elif axis == 1:
        start = py
    else:
        start = pz
    end = start + amount
    hit = False
    for (cx, cy, cz, hx, hy, hz) in flat:
        if axis == 0:
            if abs(py - cy) > hy + POINT_SKIN or abs(pz - cz) > hz + POINT_SKIN:
                continue
            low = cx - hx
            high = cx + hx
        elif axis == 1:
            if abs(px - cx) > hx + POINT_SKIN or abs(pz - cz) > hz + POINT_SKIN:
                continue
            low = cy - hy
            high = cy + hy
        else:
            if abs(px - cx) > hx + POINT_SKIN or abs(py - cy) > hy + POINT_SKIN:
                continue
            low = cz - hz
            high = cz + hz
        if amount > 0.0:
            if (end >= low - POINT_SKIN and start <= low + POINT_SKIN) or (low < start < high):
                end = min(end, low - POINT_SKIN)
                hit = True
        else:
            if (end <= high + POINT_SKIN and start >= high - POINT_SKIN) or (low < start < high):
                end = max(end, high + POINT_SKIN)
                hit = True
    return end, hit


@dataclass(frozen=True, slots=True)
class Particle:
    """One live particle: position, velocity, age, lifetime and size."""

    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    age: float = 0.0
    lifetime: float = 1.0
    size: float = 1.0
    seed: int = 0
    emitter: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.position, Vec3) or not isinstance(self.velocity, Vec3):
            raise TypeError("particle position and velocity must be Vec3")
        if self.age < 0.0 or self.lifetime <= 0.0:
            raise ValueError("particle age must be non-negative and lifetime positive")
        if self.size <= 0.0:
            raise ValueError("particle size must be positive")

    def alive(self) -> bool:
        return self.age < self.lifetime


@dataclass(frozen=True, slots=True)
class Emitter:
    """Deterministic spawn recipe: rate, lifetime, speed, spread and forces."""

    name: str = "emitter"
    rate: float = 10.0
    lifetime: float = 1.0
    speed: float = 2.0
    spread: float = 0.5
    direction: Vec3 = field(default_factory=lambda: Vec3(0.0, 1.0, 0.0))
    gravity: Vec3 = field(default_factory=lambda: Vec3(0.0, -2.0, 0.0))
    drag: float = 0.0
    size: float = 1.0
    seed: int = 7

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("emitter name must be a non-blank string")
        if self.rate < 0.0 or self.lifetime <= 0.0 or self.speed < 0.0:
            raise ValueError("emitter rate/lifetime/speed must be non-negative with positive lifetime")
        if self.spread < 0.0 or self.drag < 0.0 or self.size <= 0.0:
            raise ValueError("emitter spread/drag must be non-negative with positive size")
        if not isinstance(self.direction, Vec3) or not isinstance(self.gravity, Vec3):
            raise TypeError("emitter direction and gravity must be Vec3")

    def spawn(self, index: int, origin: Vec3 | None = None) -> Particle:
        """Spawn one particle deterministically from the emitter seed and index."""
        if index < 0:
            raise ValueError("particle index must be non-negative")
        rng = random.Random((self.seed * 2654435761 + index * 40503) & 0xFFFFFFFF)
        base = origin if isinstance(origin, Vec3) else Vec3()
        direction = Vec3(
            self.direction.x + rng.uniform(-self.spread, self.spread),
            self.direction.y + rng.uniform(-self.spread, self.spread),
            self.direction.z + rng.uniform(-self.spread, self.spread),
        )
        lifetime = self.lifetime * rng.uniform(0.75, 1.25)
        return Particle(
            position=base,
            velocity=Vec3(direction.x * self.speed, direction.y * self.speed, direction.z * self.speed),
            age=0.0,
            lifetime=lifetime,
            size=self.size,
            seed=index,
            emitter=self.name,
        )

    def to_dict(self) -> dict:
        return {
            "schema": 1,
            "name": self.name,
            "rate": self.rate,
            "lifetime": self.lifetime,
            "speed": self.speed,
            "spread": self.spread,
            "direction": [self.direction.x, self.direction.y, self.direction.z],
            "gravity": [self.gravity.x, self.gravity.y, self.gravity.z],
            "drag": self.drag,
            "size": self.size,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Emitter:
        if not isinstance(data, dict):
            raise TypeError("emitter document must be a mapping")
        if data.get("schema", 1) != 1:
            raise ValueError("unsupported emitter schema")
        direction = data.get("direction", [0.0, 1.0, 0.0])
        gravity = data.get("gravity", [0.0, -2.0, 0.0])
        return cls(
            name=str(data.get("name", "emitter")),
            rate=float(data.get("rate", 10.0)),
            lifetime=float(data.get("lifetime", 1.0)),
            speed=float(data.get("speed", 2.0)),
            spread=float(data.get("spread", 0.5)),
            direction=Vec3(float(direction[0]), float(direction[1]), float(direction[2])),
            gravity=Vec3(float(gravity[0]), float(gravity[1]), float(gravity[2])),
            drag=float(data.get("drag", 0.0)),
            size=float(data.get("size", 1.0)),
            seed=int(data.get("seed", 7)),
        )


@dataclass
class ParticleSystem:
    """Owns emitters and live particles; deterministic under a fixed call order."""

    emitters: dict[str, Emitter] = field(default_factory=dict)
    max_particles: int = 4096
    time: float = 0.0
    particles: list[Particle] = field(default_factory=list)
    _emitted: int = 0

    def __post_init__(self) -> None:
        if self.max_particles <= 0:
            raise ValueError("max_particles must be positive")
        self.emitters = dict(self.emitters)

    def add(self, emitter: Emitter) -> None:
        if not isinstance(emitter, Emitter):
            raise TypeError("system emitters must be Emitter instances")
        self.emitters[emitter.name] = emitter

    def burst(self, emitter_name: str, count: int, origin: Vec3 | None = None) -> int:
        """Emit count particles immediately; returns the number actually added."""
        if count < 0:
            raise ValueError("burst count must be non-negative")
        emitter = self.emitters.get(emitter_name)
        if emitter is None:
            raise KeyError(f"unknown emitter {emitter_name!r}")
        added = 0
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                self.particles.pop(0)
            self.particles.append(emitter.spawn(self._emitted, origin))
            self._emitted += 1
            added += 1
        return added

    def step(self, dt: float, colliders: Iterable[AABB] = ()) -> int:
        """Advance all particles by dt; returns the live count afterwards."""
        if dt < 0.0:
            raise ValueError("dt must be non-negative")
        boxes = list(colliders)
        for box in boxes:
            if not isinstance(box, AABB):
                raise TypeError("particle colliders must be AABB instances")
        if not boxes:
            return self._step_free(dt)
        flat: list[tuple[float, float, float, float, float, float]] = [
            (box.center.x, box.center.y, box.center.z,
             box.half_extents.x, box.half_extents.y, box.half_extents.z)
            for box in boxes
        ]
        self.time += dt
        live: list[Particle] = []
        for particle in self.particles:
            age = particle.age + dt
            if age >= particle.lifetime:
                continue
            emitter = self._emitter_for(particle)
            gravity = emitter.gravity if emitter else Vec3(0.0, -2.0, 0.0)
            drag = emitter.drag if emitter else 0.0
            velocity = Vec3(
                particle.velocity.x + gravity.x * dt,
                particle.velocity.y + gravity.y * dt,
                particle.velocity.z + gravity.z * dt,
            )
            if drag > 0.0:
                keep = max(0.0, 1.0 - drag * dt)
                velocity = Vec3(velocity.x * keep, velocity.y * keep, velocity.z * keep)
            px, py, pz = particle.position.x, particle.position.y, particle.position.z
            px, hit_x = _move_point_flat(px, py, pz, 0, velocity.x * dt, flat)
            pz, hit_z = _move_point_flat(px, py, pz, 2, velocity.z * dt, flat)
            py, hit_y = _move_point_flat(px, py, pz, 1, velocity.y * dt, flat)
            position = Vec3(px, py, pz)
            if hit_x:
                velocity = Vec3(0.0, velocity.y, velocity.z)
            if hit_z:
                velocity = Vec3(velocity.x, velocity.y, 0.0)
            if hit_y:
                velocity = Vec3(velocity.x, 0.0, velocity.z)
            live.append(Particle(position, velocity, age, particle.lifetime, particle.size, particle.seed, particle.emitter))
        self.particles = live
        return len(self.particles)

    def _step_free(self, dt: float) -> int:
        self.time += dt
        live: list[Particle] = []
        for particle in self.particles:
            age = particle.age + dt
            if age >= particle.lifetime:
                continue
            emitter = self._emitter_for(particle)
            gravity = emitter.gravity if emitter else Vec3(0.0, -2.0, 0.0)
            drag = emitter.drag if emitter else 0.0
            velocity = Vec3(
                particle.velocity.x + gravity.x * dt,
                particle.velocity.y + gravity.y * dt,
                particle.velocity.z + gravity.z * dt,
            )
            if drag > 0.0:
                keep = max(0.0, 1.0 - drag * dt)
                velocity = Vec3(velocity.x * keep, velocity.y * keep, velocity.z * keep)
            position = Vec3(
                particle.position.x + velocity.x * dt,
                particle.position.y + velocity.y * dt,
                particle.position.z + velocity.z * dt,
            )
            live.append(Particle(position, velocity, age, particle.lifetime, particle.size, particle.seed, particle.emitter))
        self.particles = live
        return len(self.particles)

    def alive_count(self) -> int:
        return len(self.particles)

    def clear(self) -> None:
        self.particles.clear()

    def _emitter_for(self, particle: Particle) -> Emitter | None:
        if particle.emitter and particle.emitter in self.emitters:
            return self.emitters[particle.emitter]
        if len(self.emitters) == 1:
            return next(iter(self.emitters.values()))
        return None


def particles_report(system: ParticleSystem) -> dict:
    return {
        "schema": 1,
        "emitters": sorted(system.emitters),
        "alive": len(system.particles),
        "emitted": system._emitted,
        "time": round(system.time, 4),
        "max_particles": system.max_particles,
    }
