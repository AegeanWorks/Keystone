"""Seeded expedition state: player, terrain, dungeon, movement and replay hash."""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from dataclasses import dataclass

from keystone.beams import LightLock
from keystone.combat import Combat
from keystone.math3d import Vec3
from keystone.procedural.dungeon import Dungeon, DungeonGenerator
from keystone.procedural.network import Network
from keystone.procedural.terrain import Terrain
from keystone.procedural.weave import WeaveLayout

DAY_SECONDS = 240.0
EYE_HEIGHT = 1.75
PLAYER_RADIUS = 0.3
MAX_PITCH = math.radians(89.0)


@dataclass(frozen=True, slots=True)
class MoveIntent:
    """One frame of player intent, in local forward/right and radians."""

    forward: float = 0.0
    right: float = 0.0
    up: float = 0.0
    turn: float = 0.0
    pitch: float = 0.0
    interact: bool = False
    scan: bool = False
    jump: bool = False
    sprint: bool = False


@dataclass
class Player:
    x: float
    z: float
    yaw: float = 0.0
    pitch: float = 0.0


class World:
    """The authoritative expedition state; it never imports OpenGL."""

    def __init__(self, seed: int, size: int = 96, layout: str = "auto") -> None:
        if layout not in ("auto", "crypt", "weave"):
            raise ValueError("layout must be 'auto', 'crypt' or 'weave'")
        self.seed = int(seed)
        self.terrain: Terrain = Terrain.generate(self.seed, size=size)
        self.layout = ("weave" if self.seed % 2 == 0 else "crypt") if layout == "auto" else layout
        self.weave: WeaveLayout | None = None
        if self.layout == "weave":
            self.weave = WeaveLayout.generate(self.seed ^ 0x5745)
            self.dungeon: Dungeon = self.weave.to_dungeon()
        else:
            self.dungeon = DungeonGenerator().generate(self.seed ^ 0x5EED)
        self.network = Network.generate(self.seed ^ 0xA17E, self.dungeon)
        self.mode = "overworld"
        self.time = DAY_SECONDS * 0.35
        self.player = Player(self.terrain.spawn[0], self.terrain.spawn[1])
        dx = self.terrain.entrance[0] - self.player.x
        dz = self.terrain.entrance[1] - self.player.z
        self.player.yaw = math.atan2(dx, -dz)
        self.messages: deque[str] = deque(maxlen=8)
        self.events: list[str] = []
        self.light_lock = LightLock(self.seed ^ 0x11A7, self.terrain.entrance)
        self.combat = Combat(self.seed ^ 0xC0FFEE)
        self.combat.spawn_around(self.player.x, self.player.z, self.is_standable, self.player.yaw)

    @property
    def day_fraction(self) -> float:
        return (self.time / DAY_SECONDS) % 1.0

    @property
    def near_entrance(self) -> bool:
        if self.mode != "overworld":
            return False
        dx = self.player.x - self.terrain.entrance[0]
        dz = self.player.z - self.terrain.entrance[1]
        return dx * dx + dz * dz <= 2.8 * 2.8

    @property
    def near_exit(self) -> bool:
        if self.mode != "dungeon":
            return False
        dx = self.player.x - (self.dungeon.exit[0] + 0.5)
        dz = self.player.z - (self.dungeon.exit[1] + 0.5)
        return dx * dx + dz * dz <= 1.4 * 1.4

    def eye_position(self) -> Vec3:
        if self.mode == "dungeon":
            return Vec3(self.player.x, 1.7, self.player.z)
        height = self.terrain.height_at(self.player.x, self.player.z)
        return Vec3(self.player.x, max(height, self.terrain.water) + EYE_HEIGHT, self.player.z)

    def step(self, dt: float, intent: MoveIntent | None = None) -> list[str]:
        if dt < 0.0:
            raise ValueError("dt cannot be negative")
        self.events = []
        self.time += dt
        intent = intent or MoveIntent()
        self.player.yaw = (self.player.yaw + intent.turn) % math.tau
        self.player.pitch = max(-MAX_PITCH, min(MAX_PITCH, self.player.pitch + intent.pitch))
        speed = (3.2 if self.mode == "dungeon" else 5.0) * (1.7 if intent.sprint else 1.0)
        distance = speed * dt
        fx, fz = math.sin(self.player.yaw), -math.cos(self.player.yaw)
        rx, rz = math.cos(self.player.yaw), math.sin(self.player.yaw)
        self._move(
            (fx * intent.forward + rx * intent.right) * distance,
            (fz * intent.forward + rz * intent.right) * distance,
        )
        if intent.interact:
            self.interact()
        self.network.update(dt)
        self.combat.update(dt, self.player.x, self.player.z, self.is_standable)
        if self.combat.dead:
            self._respawn()
        for event in self.combat.events:
            self.messages.append(event)
        return list(self.events)

    def _hack_nearby_terminal(self) -> bool:
        terminal = self.network.near_terminal(self.player.x, self.player.z)
        if terminal is None:
            return False
        message = self.network.hack(terminal.terminal_id)
        if message:
            self._record(message)
            if self.network.alert >= 50.0 and not terminal.hacked:
                self._spawn_hunter()
        return True

    def _spawn_hunter(self) -> None:
        for index in range(12):
            angle = math.tau * index / 12.0
            x = self.player.x + math.cos(angle) * 3.0
            z = self.player.z + math.sin(angle) * 3.0
            if self.is_standable(x, z):
                self.combat.spawn_at("stalker", x, z)
                self._record("NetWatch hunter inbound.")
                return

    def rotate_mirror(self) -> bool:
        if self.mode != "overworld":
            return False
        mirror = self.light_lock.nearest_mirror(self.player.x, self.player.z)
        if mirror is None:
            return False
        self.light_lock.rotate(*mirror)
        if self.light_lock.solved:
            self._record("The rune answers. The portal is open.")
        else:
            self._record("Mirror turned.")
        return True

    def interact(self) -> None:
        if self.mode == "overworld" and self.near_entrance and self.light_lock.solved:
            self.mode = "dungeon"
            self.player.x = self.dungeon.spawn[0] + 0.5
            self.player.z = self.dungeon.spawn[1] + 0.5
            path = self.dungeon.find_path(self.dungeon.spawn, self.dungeon.exit) or []
            step = path[1] if len(path) > 1 else self.dungeon.exit
            self.player.pitch = 0.0
            self.player.yaw = math.atan2(
                step[0] + 0.5 - self.player.x,
                -(step[1] + 0.5 - self.player.z),
            )
            self.combat.spawn_around(self.player.x, self.player.z, self.is_standable, self.player.yaw)
            self._record("Entered the sunken crypt.")
        elif self.mode == "overworld" and self.rotate_mirror():
            return
        elif self.mode == "overworld" and self.near_entrance:
            self._record("The portal is sealed. Align the light with the rune.")
        elif self.mode == "dungeon" and self._hack_nearby_terminal():
            return
        elif self.mode == "dungeon" and self.near_exit and not self.network.complete:
            self._record(
                f"The exit rune is sealed. Network {self.network.hacked_count}/{len(self.network.terminals)} compromised."
            )
        elif self.mode == "dungeon" and self.near_exit:
            self.mode = "overworld"
            self.player.x = self.terrain.entrance[0]
            self.player.z = self.terrain.entrance[1] + 1.2
            self.combat.spawn_around(self.player.x, self.player.z, self.is_standable, self.player.yaw)
            self._record("Returned to the vale.")

    def _record(self, message: str) -> None:
        self.events.append(message)
        self.messages.append(message)

    def _move(self, dx: float, dz: float) -> None:
        if dx == 0.0 and dz == 0.0:
            return
        if self._free(self.player.x + dx, self.player.z + dz):
            self.player.x += dx
            self.player.z += dz
        elif self._free(self.player.x + dx, self.player.z):
            self.player.x += dx
        elif self._free(self.player.x, self.player.z + dz):
            self.player.z += dz

    def is_standable(self, x: float, z: float) -> bool:
        """Public walkability query shared by combat and future mechanics."""
        return self._free(x, z)

    def _free(self, x: float, z: float) -> bool:
        if self.mode == "dungeon":
            return self._dungeon_free(x, z)
        return self.terrain.is_walkable(x, z)

    def _respawn(self) -> None:
        if self.mode == "dungeon":
            self.player.x = self.dungeon.spawn[0] + 0.5
            self.player.z = self.dungeon.spawn[1] + 0.5
            self.player.yaw = 0.0
        else:
            self.player.x, self.player.z = self.terrain.spawn
            dx = self.terrain.entrance[0] - self.player.x
            dz = self.terrain.entrance[1] - self.player.z
            self.player.yaw = math.atan2(dx, -dz)
        self.player.pitch = 0.0
        self.combat.revive(self.player.x, self.player.z, self.is_standable, self.player.yaw)
        self._record("You fell. The expedition restarts at the last safe point.")

    def _dungeon_free(self, x: float, z: float) -> bool:
        offsets = (
            (0.0, 0.0),
            (PLAYER_RADIUS, 0.0),
            (-PLAYER_RADIUS, 0.0),
            (0.0, PLAYER_RADIUS),
            (0.0, -PLAYER_RADIUS),
            (PLAYER_RADIUS, PLAYER_RADIUS),
            (PLAYER_RADIUS, -PLAYER_RADIUS),
            (-PLAYER_RADIUS, PLAYER_RADIUS),
            (-PLAYER_RADIUS, -PLAYER_RADIUS),
        )
        for ox, oz in offsets:
            if not self.dungeon.is_walkable(math.floor(x + ox), math.floor(z + oz)):
                return False
        return True

    def snapshot(self) -> dict:
        return {
            "seed": self.seed,
            "time": round(self.time, 3),
            "day_fraction": round(self.day_fraction, 4),
            "mode": self.mode,
            "layout": self.layout,
            "weave": self.weave.snapshot() if self.weave else None,
            "player": {
                "x": round(self.player.x, 4),
                "z": round(self.player.z, 4),
                "yaw": round(self.player.yaw, 4),
                "pitch": round(self.player.pitch, 4),
            },
            "terrain": {
                "size": self.terrain.size,
                "water": round(self.terrain.water, 4),
                "spawn": [round(value, 3) for value in self.terrain.spawn],
                "entrance": [round(value, 3) for value in self.terrain.entrance],
            },
            "dungeon": {
                "width": self.dungeon.width,
                "height": self.dungeon.height,
                "spawn": list(self.dungeon.spawn),
                "exit": list(self.dungeon.exit),
            },
            "near_entrance": self.near_entrance,
            "near_exit": self.near_exit,
            "light_lock": self.light_lock.snapshot(),
            "network": self.network.snapshot(),
            "combat": self.combat.snapshot(),
            "events": list(self.events),
        }

    def state_hash(self) -> str:
        payload = json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":"))
        layout = json.dumps(self.dungeon.tiles, separators=(",", ":"))
        digest = hashlib.blake2b((payload + layout).encode("utf-8"), digest_size=16)
        return digest.hexdigest()
