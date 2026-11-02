"""Deterministic, game-agnostic CPU particles: emitters, systems and reports.

No window, GL context or third-party dependency is required. Spawning uses a
seeded RNG per particle index so the same call sequence always yields the
same trajectories. Games own their systems; the engine owns integration.
Rendering integration is a later step; systems already drive HUD, inspector
and AI reports through counts and snapshots.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from keystone.math3d import Vec3

__all__ = ["Emitter", "Particle", "ParticleSystem", "particles_report"]


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

    def step(self, dt: float) -> int:
        """Advance all particles by dt; returns the live count afterwards."""
        if dt < 0.0:
            raise ValueError("dt must be non-negative")
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
