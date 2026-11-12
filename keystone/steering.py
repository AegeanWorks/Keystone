"""Deterministic local steering for moving agents.

Navigation answers where an agent should go; this module shapes how it gets
there when other agents are in the way. It is intentionally small and pure:
``seek`` and ``arrive`` turn a target into a wish velocity, ``separation``
pushes an agent out of its neighbours' contact radius, and ``steer`` combines
the two and clamps to the agent's speed.

All functions are CPU-only, finite-validated and deterministic. There is no
time step and no hidden state, so a game owns integration and collision
response exactly as it does with ``PathFollower``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from keystone.math3d import Vec3

__all__ = ["Agent", "arrive", "seek", "separation", "steer", "steering_report"]


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


@dataclass(frozen=True, slots=True)
class Agent:
    """One steering body: a position, an optional velocity, a radius and a speed."""

    position: Vec3 = Vec3()
    velocity: Vec3 = Vec3()
    radius: float = 0.35
    max_speed: float = 3.0

    def __post_init__(self) -> None:
        _point("agent position", self.position)
        _point("agent velocity", self.velocity)
        if _finite("agent radius", self.radius) <= 0.0:
            raise ValueError("agent radius must be positive")
        if _finite("agent max speed", self.max_speed) <= 0.0:
            raise ValueError("agent max speed must be positive")


def seek(position: Vec3, target: Vec3, max_speed: float) -> Vec3:
    """Return a velocity of ``max_speed`` toward ``target``, or zero at it."""
    here = _point("seek position", position)
    goal = _point("seek target", target)
    speed = _finite("seek max speed", max_speed)
    if speed <= 0.0:
        raise ValueError("seek max speed must be positive")
    offset = goal - here
    distance = offset.length()
    if distance <= 1e-12:
        return Vec3()
    return offset * (speed / distance)


def arrive(position: Vec3, target: Vec3, max_speed: float, slow_radius: float) -> Vec3:
    """Seek at full speed outside ``slow_radius`` and linearly slow to zero."""
    here = _point("arrive position", position)
    goal = _point("arrive target", target)
    speed = _finite("arrive max speed", max_speed)
    if speed <= 0.0:
        raise ValueError("arrive max speed must be positive")
    radius = _finite("arrive slow radius", slow_radius)
    if radius <= 0.0:
        raise ValueError("arrive slow radius must be positive")
    offset = goal - here
    distance = offset.length()
    if distance <= 1e-12:
        return Vec3()
    if distance >= radius:
        return offset * (speed / distance)
    return offset * (speed * (distance / radius) / distance)


def _neighbours(value: object) -> tuple[tuple[Vec3, float], ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError("neighbours must be an iterable of (position, radius) pairs")
    try:
        items = tuple(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError("neighbours must be an iterable of (position, radius) pairs") from exc
    pairs: list[tuple[Vec3, float]] = []
    for item in items:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise TypeError("neighbours must be (position, radius) pairs")
        point = _point("neighbour position", item[0])
        radius = _finite("neighbour radius", item[1])
        if radius < 0.0:
            raise ValueError("neighbour radius must be non-negative")
        pairs.append((point, radius))
    return tuple(pairs)


def separation(
    position: Vec3,
    neighbours: Iterable[tuple[Vec3, float]],
    radius: float,
    *,
    strength: float = 1.0,
    margin: float = 0.0,
) -> Vec3:
    """Sum a repulsion from every neighbour within contact distance.

    The limit for each neighbour is ``radius + neighbour radius + margin``.
    The push points away from the neighbour and falls off quadratically to
    zero at the limit; a coincident neighbour contributes nothing because
    there is no deterministic direction to choose.
    """
    here = _point("separation position", position)
    own_radius = _finite("separation radius", radius)
    if own_radius < 0.0:
        raise ValueError("separation radius must be non-negative")
    force = _finite("separation strength", strength)
    if force < 0.0:
        raise ValueError("separation strength must be non-negative")
    extra = _finite("separation margin", margin)
    if extra < 0.0:
        raise ValueError("separation margin must be non-negative")
    push = Vec3()
    for point, other_radius in _neighbours(neighbours):
        offset = here - point
        distance = offset.length()
        limit = own_radius + other_radius + extra
        if distance <= 1e-12 or distance >= limit:
            continue
        weight = (limit - distance) / limit
        push = push + offset * (force * weight * weight / distance)
    return push


def steer(
    agent: Agent,
    wish: Vec3,
    neighbours: Iterable[Agent] = (),
    *,
    separation_weight: float = 1.0,
    margin: float = 0.0,
) -> Vec3:
    """Combine a wish velocity with agent separation and clamp to max speed."""
    if not isinstance(agent, Agent):
        raise TypeError("steer needs an Agent")
    velocity = _point("steer wish", wish)
    weight = _finite("steer separation weight", separation_weight)
    if weight < 0.0:
        raise ValueError("steer separation weight must be non-negative")
    others = []
    for other in neighbours:
        if not isinstance(other, Agent):
            raise TypeError("steer neighbours must be Agents")
        if other is agent:
            continue
        others.append((other.position, other.radius))
    adjusted = velocity + separation(
        agent.position,
        others,
        agent.radius,
        strength=weight,
        margin=margin,
    )
    speed = adjusted.length()
    if speed > agent.max_speed:
        return adjusted * (agent.max_speed / speed)
    return adjusted


def steering_report(agent: Agent, wish: Vec3) -> dict:
    """Return a JSON-safe summary of one steering wish."""
    if not isinstance(agent, Agent):
        raise TypeError("steering_report needs an Agent")
    velocity = _point("steering report wish", wish)
    speed = velocity.length()
    return {
        "schema": 1,
        "wish": [velocity.x, velocity.y, velocity.z],
        "speed": round(speed, 6),
        "max_speed": agent.max_speed,
        "limited": speed > agent.max_speed + 1e-12,
    }
