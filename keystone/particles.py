"""Deterministic, game-agnostic CPU particles: emitters, systems and reports.

No window, GL context or third-party dependency is required. Spawning uses a
seeded RNG per particle index so the same call sequence always yields the
same trajectories. Games own their systems; the engine owns integration.
Rendering integration is a later step; systems already drive HUD, inspector
and AI reports through counts and snapshots.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass, field

from keystone.math3d import Vec3
from keystone.physics import AABB

__all__ = ["Emitter", "Particle", "ParticleSystem", "particles_report"]

POINT_SKIN = 1e-9

#: Bounce speed below which a reflected axis settles to rest (m/s).
REST_SPEED = 0.05


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _vec3_value(value: object, label: str) -> Vec3:
    if not isinstance(value, Vec3):
        raise TypeError(f"{label} must be a Vec3")
    if not all(math.isfinite(component) for component in (value.x, value.y, value.z)):
        raise ValueError(f"{label} must contain finite components")
    return value


def _depenetrate_static(
    px: float, py: float, pz: float, flat: list[tuple[float, float, float, float, float, float]]
) -> tuple[float, float, float]:
    """Eject a stationary point from the nearest box face deterministically."""
    best_distance = math.inf
    best = (px, py, pz)
    for (cx, cy, cz, hx, hy, hz) in flat:
        if not (cx - hx < px < cx + hx and cy - hy < py < cy + hy and cz - hz < pz < cz + hz):
            continue
        candidates = (
            ((cy + hy) - py, (px, cy + hy + POINT_SKIN, pz)),
            (py - (cy - hy), (px, cy - hy - POINT_SKIN, pz)),
            ((cx + hx) - px, (cx + hx + POINT_SKIN, py, pz)),
            (px - (cx - hx), (cx - hx - POINT_SKIN, py, pz)),
            ((cz + hz) - pz, (px, py, cz + hz + POINT_SKIN)),
            (pz - (cz - hz), (px, py, cz - hz - POINT_SKIN)),
        )
        for distance, position in candidates:
            if distance < best_distance:
                best_distance = distance
                best = position
    return best


def _move_point_flat(
    px: float, py: float, pz: float, axis: int, amount: float, flat: list[tuple[float, float, float, float, float, float]]
) -> tuple[float, bool]:
    """Float-only swept point move; axis is 0/1/2 for x/y/z.

    The interior-start clause only fires for points strictly inside the
    box on every axis. Points resting on a face (within POINT_SKIN) slide
    instead of relocating to the min face.
    """
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
            deep = cy - hy < py < cy + hy and cz - hz < pz < cz + hz
        elif axis == 1:
            if abs(px - cx) > hx + POINT_SKIN or abs(pz - cz) > hz + POINT_SKIN:
                continue
            low = cy - hy
            high = cy + hy
            deep = cx - hx < px < cx + hx and cz - hz < pz < cz + hz
        else:
            if abs(px - cx) > hx + POINT_SKIN or abs(py - cy) > hy + POINT_SKIN:
                continue
            low = cz - hz
            high = cz + hz
            deep = cx - hx < px < cx + hx and cy - hy < py < cy + hy
        if deep and low < start < high:
            low_distance = start - low
            high_distance = high - start
            if low_distance < high_distance:
                end = low - POINT_SKIN
            elif high_distance < low_distance:
                end = high + POINT_SKIN
            elif amount > 0.0:
                end = low - POINT_SKIN
            else:
                end = high + POINT_SKIN
            hit = True
        elif amount > 0.0:
            if end >= low - POINT_SKIN and start <= low + POINT_SKIN:
                end = min(end, low - POINT_SKIN)
                hit = True
        else:
            if end <= high + POINT_SKIN and start >= high - POINT_SKIN:
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
        _vec3_value(self.position, "particle position")
        _vec3_value(self.velocity, "particle velocity")
        if _finite(self.age, "particle age") < 0.0:
            raise ValueError("particle age must be non-negative")
        if _finite(self.lifetime, "particle lifetime") <= 0.0:
            raise ValueError("particle lifetime must be positive")
        if _finite(self.size, "particle size") <= 0.0:
            raise ValueError("particle size must be positive")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("particle seed must be an integer")

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
        if _finite(self.rate, "emitter rate") < 0.0:
            raise ValueError("emitter rate must be non-negative")
        if _finite(self.lifetime, "emitter lifetime") <= 0.0:
            raise ValueError("emitter lifetime must be positive")
        if _finite(self.speed, "emitter speed") < 0.0:
            raise ValueError("emitter speed must be non-negative")
        if _finite(self.spread, "emitter spread") < 0.0:
            raise ValueError("emitter spread must be non-negative")
        if _finite(self.drag, "emitter drag") < 0.0:
            raise ValueError("emitter drag must be non-negative")
        if _finite(self.size, "emitter size") <= 0.0:
            raise ValueError("emitter size must be positive")
        _vec3_value(self.direction, "emitter direction")
        _vec3_value(self.gravity, "emitter gravity")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("emitter seed must be an integer")

    def spawn(self, index: int, origin: Vec3 | None = None) -> Particle:
        """Spawn one particle deterministically from the emitter seed and index."""
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("particle index must be an integer")
        if index < 0:
            raise ValueError("particle index must be non-negative")
        if origin is None:
            base = Vec3()
        elif isinstance(origin, Vec3):
            _vec3_value(origin, "particle origin")
            base = origin
        else:
            raise TypeError("particle origin must be a Vec3 or None")
        rng = random.Random((self.seed * 2654435761 + index * 40503) & 0xFFFFFFFF)
        direction = Vec3(
            self.direction.x + rng.uniform(-self.spread, self.spread),
            self.direction.y + rng.uniform(-self.spread, self.spread),
            self.direction.z + rng.uniform(-self.spread, self.spread),
        )
        length = direction.length()
        if length < 1e-12:
            direction = self.direction.normalized()
            if direction.length_squared() < 1e-12:
                direction = Vec3(0.0, 1.0, 0.0)
        else:
            direction = direction / length
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
        schema = data.get("schema", 1)
        if isinstance(schema, bool) or not isinstance(schema, int) or schema != 1:
            raise ValueError("unsupported emitter schema")

        def number(key: str, default: float) -> float:
            return _finite(data.get(key, default), f"emitter {key}")

        def vector(key: str, default: tuple[float, float, float]) -> Vec3:
            raw = data.get(key, list(default))
            if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                raise ValueError(f"emitter {key} must have three values")
            return Vec3(*(_finite(component, f"emitter {key}") for component in raw))

        name = data.get("name", "emitter")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("emitter name must be a non-blank string")
        seed = data.get("seed", 7)
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("emitter seed must be an integer")
        return cls(
            name=name,
            rate=number("rate", 10.0),
            lifetime=number("lifetime", 1.0),
            speed=number("speed", 2.0),
            spread=number("spread", 0.5),
            direction=vector("direction", (0.0, 1.0, 0.0)),
            gravity=vector("gravity", (0.0, -2.0, 0.0)),
            drag=number("drag", 0.0),
            size=number("size", 1.0),
            seed=seed,
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
        if isinstance(self.max_particles, bool) or not isinstance(self.max_particles, int) or self.max_particles <= 0:
            raise ValueError("max_particles must be a positive integer")
        if not math.isfinite(self.time):
            raise ValueError("particle system time must be finite")
        self.emitters = dict(self.emitters)
        for name, emitter in self.emitters.items():
            if not isinstance(emitter, Emitter):
                raise TypeError("system emitters must be Emitter instances")
            if name != emitter.name:
                raise ValueError("emitter table keys must match emitter names")

    def add(self, emitter: Emitter) -> None:
        if not isinstance(emitter, Emitter):
            raise TypeError("system emitters must be Emitter instances")
        self.emitters[emitter.name] = emitter

    def burst(self, emitter_name: str, count: int, origin: Vec3 | None = None) -> int:
        """Emit count particles immediately; returns the number actually added."""
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("burst count must be an integer")
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

    def step(
        self,
        dt: float,
        colliders: Iterable[AABB] = (),
        restitution: float = 0.0,
        friction: float = 0.0,
        kill_on_contact: bool = False,
    ) -> int:
        """Advance all particles by dt; returns the live count afterwards.

        Contact response is deterministic: hits use the swept X-Z-Y pass in
        caller box order; restitution reflects the hit axis (0 keeps the
        legacy dead stop), friction scales tangential velocity on hit steps
        only, and kill_on_contact drops the particle on its first hit.
        """
        if dt < 0.0 or not math.isfinite(dt):
            raise ValueError("dt must be non-negative and finite")
        if not 0.0 <= restitution <= 1.0:
            raise ValueError("restitution must be within [0, 1]")
        if not 0.0 <= friction <= 1.0:
            raise ValueError("friction must be within [0, 1]")
        if not math.isfinite(self.time + dt):
            raise ValueError("particle system time overflowed")
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
        legacy = restitution == 0.0 and friction == 0.0 and not kill_on_contact
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
            if abs(velocity.x) < 1e-12 and abs(velocity.y) < 1e-12 and abs(velocity.z) < 1e-12:
                px, py, pz = _depenetrate_static(px, py, pz, flat)
            px, hit_x = _move_point_flat(px, py, pz, 0, velocity.x * dt, flat)
            pz, hit_z = _move_point_flat(px, py, pz, 2, velocity.z * dt, flat)
            py, hit_y = _move_point_flat(px, py, pz, 1, velocity.y * dt, flat)
            position = Vec3(px, py, pz)
            if legacy:
                if hit_x:
                    velocity = Vec3(0.0, velocity.y, velocity.z)
                if hit_z:
                    velocity = Vec3(velocity.x, velocity.y, 0.0)
                if hit_y:
                    velocity = Vec3(velocity.x, 0.0, velocity.z)
            else:
                if hit_x or hit_y or hit_z:
                    if kill_on_contact:
                        continue
                    if hit_x:
                        velocity = self._respond_axis(velocity.x, velocity.y, velocity.z, 0, restitution)
                    if hit_z:
                        velocity = self._respond_axis(velocity.x, velocity.y, velocity.z, 2, restitution)
                    if hit_y:
                        velocity = self._respond_axis(velocity.x, velocity.y, velocity.z, 1, restitution)
                    if friction > 0.0:
                        grip = 1.0 - friction
                        velocity = Vec3(
                            velocity.x if hit_x else velocity.x * grip,
                            velocity.y if hit_y else velocity.y * grip,
                            velocity.z if hit_z else velocity.z * grip,
                        )
            live.append(Particle(position, velocity, age, particle.lifetime, particle.size, particle.seed, particle.emitter))
        self.particles = live
        return len(self.particles)

    @staticmethod
    def _respond_axis(vx: float, vy: float, vz: float, axis: int, restitution: float) -> Vec3:
        """Reflect one velocity axis with settle snapping; other axes untouched."""
        components = [vx, vy, vz]
        reflected = -components[axis] * restitution
        if abs(reflected) < REST_SPEED:
            reflected = 0.0
        components[axis] = reflected
        return Vec3(components[0], components[1], components[2])

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
