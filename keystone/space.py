"""Renderer-independent space flight, body surveys and hyperlane jumps."""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from dataclasses import dataclass

from keystone.math3d import Vec3
from keystone.procedural.space import Body, Galaxy, StarSystem, body_snapshot
from keystone.sim.world import MAX_PITCH, MoveIntent

GATE = Vec3(0.0, 0.0, 60.0)
FLIGHT_SPEED = 12.0


@dataclass
class Ship:
    position: Vec3 = Vec3(0.0, 0.0, 22.0)
    yaw: float = 0.0
    pitch: float = 0.0

    def forward(self) -> Vec3:
        cos_pitch = math.cos(self.pitch)
        return Vec3(
            math.sin(self.yaw) * cos_pitch,
            math.sin(self.pitch),
            -math.cos(self.yaw) * cos_pitch,
        )


class SpaceWorld:
    def __init__(self, seed: int) -> None:
        self.seed = int(seed)
        self.galaxy: Galaxy = Galaxy.generate(self.seed)
        self.system_id = self.galaxy.start_id
        self.ship = Ship()
        self.time = 0.0
        self.credits = 0
        self.events: list[str] = []
        self.messages: deque[str] = deque(maxlen=8)

    @property
    def system(self) -> StarSystem:
        return self.galaxy.system(self.system_id)

    @property
    def scanned_count(self) -> int:
        return sum(1 for body in self.system.bodies if body.scanned)

    @property
    def complete(self) -> bool:
        return self.scanned_count == len(self.system.bodies)

    def step(self, dt: float, intent: MoveIntent | None = None) -> list[str]:
        if dt < 0.0:
            raise ValueError("dt cannot be negative")
        self.events = []
        self.time += dt
        intent = intent or MoveIntent()
        self.ship.yaw = (self.ship.yaw + intent.turn) % math.tau
        self.ship.pitch = max(-MAX_PITCH, min(MAX_PITCH, self.ship.pitch + intent.pitch))
        speed = FLIGHT_SPEED * (1.8 if intent.sprint else 1.0)
        forward = self.ship.forward()
        right = forward.cross(Vec3.UP).normalized()
        self.ship.position = self.ship.position + forward * (intent.forward * speed * dt)
        self.ship.position = self.ship.position + right * (intent.right * speed * dt)
        self.ship.position = self.ship.position + Vec3.UP * (intent.up * speed * dt)
        if self.ship.position.length() > 90.0:
            self.ship.position = self.ship.position.normalized() * 90.0
        if intent.scan:
            self.scan()
        if intent.jump:
            self.jump()
        return list(self.events)

    def scan(self) -> None:
        closest: Body | None = None
        closest_distance = float("inf")
        for body in self.system.bodies:
            if body.scanned:
                continue
            bx, by, bz = body.position(self.time)
            distance = (self.ship.position - Vec3(bx, by, bz)).length()
            if distance <= body.radius + 6.0 and distance < closest_distance:
                closest, closest_distance = body, distance
        if closest is None:
            self._record("No unscanned body in sensor range.")
            return
        closest.scanned = True
        self.credits += 80 + int(closest.radius * 40)
        self._record(f"Surveyed {closest.name} ({closest.kind}).")
        if self.complete:
            self._record(f"{self.system.name} survey complete. Gate is ready.")

    def jump(self) -> None:
        if (self.ship.position - GATE).length() > 12.0:
            self._record("Move within 12 units of the jump gate.")
            return
        options = [system_id for system_id in self.system.connections if system_id != self.system_id]
        if not options:
            self._record("No hyperlane leaves this system.")
            return
        self.system_id = options[0]
        self.ship = Ship()
        self._record(f"Jumped to {self.system.name}.")

    def _record(self, message: str) -> None:
        self.events.append(message)
        self.messages.append(message)

    def snapshot(self) -> dict:
        return {
            "seed": self.seed,
            "time": round(self.time, 3),
            "system": self.system.system_id,
            "system_name": self.system.name,
            "connections": list(self.system.connections),
            "ship": {
                "x": round(self.ship.position.x, 3),
                "y": round(self.ship.position.y, 3),
                "z": round(self.ship.position.z, 3),
                "yaw": round(self.ship.yaw, 4),
                "pitch": round(self.ship.pitch, 4),
            },
            "gate": [GATE.x, GATE.y, GATE.z],
            "credits": self.credits,
            "scanned": self.scanned_count,
            "total": len(self.system.bodies),
            "complete": self.complete,
            "bodies": [body_snapshot(body, self.time) for body in self.system.bodies],
            "events": list(self.events),
        }

    def state_hash(self) -> str:
        payload = json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":"))
        return hashlib.blake2b(payload.encode("utf-8"), digest_size=16).hexdigest()

    def status(self) -> str:
        return f"{self.system.name} | scanned {self.scanned_count}/{len(self.system.bodies)} | {self.credits} cr"
