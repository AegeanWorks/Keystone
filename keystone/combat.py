"""Deterministic survivors-style combat: archetypes, waves, auto-fire and bosses."""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field

Standable = Callable[[float, float], bool]


@dataclass(frozen=True, slots=True)
class EnemySpec:
    key: str
    name: str
    hp: float
    speed: float
    damage: float
    radius: float
    color: tuple[float, float, float]
    split: bool = False
    bomber: bool = False
    boss: bool = False


ENEMY_TYPES: dict[str, EnemySpec] = {
    "crawler": EnemySpec("crawler", "Crawler", 26, 2.6, 8, 0.42, (0.92, 0.24, 0.18)),
    "stalker": EnemySpec("stalker", "Stalker", 16, 4.6, 6, 0.34, (1.0, 0.58, 0.12)),
    "bulwark": EnemySpec("bulwark", "Bulwark", 130, 1.8, 18, 0.72, (0.62, 0.38, 0.9)),
    "splitter": EnemySpec("splitter", "Splitter", 60, 2.5, 10, 0.55, (0.95, 0.4, 0.78), split=True),
    "bomber": EnemySpec("bomber", "Bomber", 44, 3.1, 22, 0.5, (1.0, 0.82, 0.12), bomber=True),
    "warlord": EnemySpec("warlord", "Warlord", 620, 2.1, 26, 1.2, (0.9, 0.08, 0.1), boss=True),
}

WAVE_SECONDS = 30.0
BOSS_EVERY = 5
MAX_ENEMIES = 40


@dataclass
class Enemy:
    spec: EnemySpec
    x: float
    z: float
    hp: float
    max_hp: float
    attack_timer: float = 0.0


@dataclass
class Combat:
    """Combat director owned by the world; no rendering, no wall clock."""

    seed: int
    rng: random.Random = field(init=False, repr=False)
    enemies: list[Enemy] = field(default_factory=list)
    player_hp: float = 100.0
    max_hp: float = 100.0
    wave: int = 1
    kills: int = 0
    elapsed: float = 0.0
    spawn_timer: float = 0.0
    attack_timer: float = 0.0
    dead: bool = False
    events: list[str] = field(default_factory=list)
    _last_boss_wave: int = 0

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def spawn_around(self, x: float, z: float, standable: Standable, facing: float | None = None) -> None:
        """Reset the arena around the player after a mode change or death."""
        self.enemies.clear()
        self.player_hp = self.max_hp
        self.wave = 1
        self.kills = 0
        self.elapsed = 0.0
        self.spawn_timer = 1.2
        self.attack_timer = 0.0
        self.dead = False
        self.events = []
        self._last_boss_wave = 0
        if facing is None:
            for _ in range(3):
                self._spawn_at_ring(x, z, standable, "crawler")
            return
        base = facing - math.pi / 2.0
        for index in range(3):
            self._spawn_at_ring(
                x,
                z,
                standable,
                "crawler",
                angle=base + (index - 1) * 0.55,
                radius=6.0 + index * 1.1,
            )

    def update(self, dt: float, px: float, pz: float, standable: Standable) -> None:
        if self.dead or dt < 0.0:
            return
        self.events = []
        self.elapsed += dt
        self.attack_timer -= dt
        self.spawn_timer -= dt
        wave = 1 + int(self.elapsed / WAVE_SECONDS)
        if wave != self.wave:
            self.wave = wave
            self.events.append(f"Wave {wave}")
            if wave % BOSS_EVERY == 0 and self._last_boss_wave != wave:
                self._last_boss_wave = wave
                self._spawn_at_ring(px, pz, standable, "warlord")
                self.events.append("A Warlord enters the field")
        if self.spawn_timer <= 0.0 and len(self.enemies) < MAX_ENEMIES:
            self.spawn_timer = max(0.55, 1.9 - wave * 0.12)
            for _ in range(1 + min(3, wave // 2)):
                self._spawn_at_ring(px, pz, standable, self._pick_type())
        self._attack(px, pz)
        for enemy in list(self.enemies):
            if enemy.hp <= 0:
                continue
            dx, dz = px - enemy.x, pz - enemy.z
            distance = math.hypot(dx, dz) or 1.0
            reach = enemy.spec.radius + 0.55
            if distance > reach:
                step = min(enemy.spec.speed * dt, distance - reach)
                self._move_enemy(enemy, dx / distance * step, dz / distance * step, standable)
            enemy.attack_timer -= dt
            if distance <= reach and enemy.attack_timer <= 0.0:
                enemy.attack_timer = 0.9
                self.player_hp -= enemy.spec.damage
                self.events.append(f"{enemy.spec.name} hits for {enemy.spec.damage:.0f}")
                if enemy.spec.bomber:
                    enemy.hp = 0.0
                    self._remove_dead()
        if self.player_hp <= 0.0:
            self.player_hp = 0.0
            self.dead = True
            self.events.append("You fell")

    def revive(self, x: float, z: float, standable: Standable, facing: float | None = None) -> None:
        self.spawn_around(x, z, standable, facing)

    def snapshot(self) -> dict:
        return {
            "player_hp": round(self.player_hp, 2),
            "max_hp": round(self.max_hp, 2),
            "wave": self.wave,
            "kills": self.kills,
            "dead": self.dead,
            "enemies": [
                {
                    "type": enemy.spec.key,
                    "name": enemy.spec.name,
                    "x": round(enemy.x, 3),
                    "z": round(enemy.z, 3),
                    "hp": round(enemy.hp, 2),
                    "boss": enemy.spec.boss,
                }
                for enemy in self.enemies
                if enemy.hp > 0
            ],
        }

    def status(self) -> str:
        boss = " BOSS" if any(enemy.spec.boss for enemy in self.enemies if enemy.hp > 0) else ""
        return f"HP {self.player_hp:.0f}/{self.max_hp:.0f} W{self.wave} K{self.kills}{boss}"

    def _pick_type(self) -> str:
        roll = self.rng.random()
        if self.wave >= 4 and roll > 0.86:
            return "bulwark"
        if self.wave >= 3 and roll > 0.72:
            return "splitter"
        if self.wave >= 2 and roll > 0.55:
            return "bomber"
        if roll > 0.35:
            return "stalker"
        return "crawler"

    def _spawn_at_ring(
        self,
        x: float,
        z: float,
        standable: Standable,
        key: str,
        angle: float | None = None,
        radius: float | None = None,
    ) -> Enemy | None:
        for _ in range(24):
            angle = self.rng.uniform(0.0, math.tau) if angle is None else angle
            radius = self.rng.uniform(8.0, 12.0) if radius is None else radius
            ex = x + math.cos(angle) * radius
            ez = z + math.sin(angle) * radius
            if standable(ex, ez):
                spec = ENEMY_TYPES[key]
                enemy = Enemy(spec, ex, ez, spec.hp, spec.hp)
                self.enemies.append(enemy)
                return enemy
        return None

    def _attack(self, px: float, pz: float) -> None:
        if self.attack_timer > 0.0:
            return
        candidates = [
            (math.hypot(px - enemy.x, pz - enemy.z), enemy)
            for enemy in self.enemies
            if enemy.hp > 0 and math.hypot(px - enemy.x, pz - enemy.z) <= 13.0
        ]
        if not candidates:
            return
        self.attack_timer = 0.35
        _, target = min(candidates, key=lambda item: item[0])
        target.hp -= 18.0 + self.wave * 0.8
        if target.hp <= 0:
            self.kills += 1
            self.events.append(f"{target.spec.name} down")
            if target.spec.split:
                for _ in range(2):
                    spec = ENEMY_TYPES["stalker"]
                    self.enemies.append(Enemy(spec, target.x, target.z, spec.hp * 0.5, spec.hp * 0.5))
            self._remove_dead()

    def _move_enemy(self, enemy: Enemy, dx: float, dz: float, standable: Standable) -> None:
        if standable(enemy.x + dx, enemy.z + dz):
            enemy.x += dx
            enemy.z += dz
        elif standable(enemy.x + dx, enemy.z):
            enemy.x += dx
        elif standable(enemy.x, enemy.z + dz):
            enemy.z += dz

    def _remove_dead(self) -> None:
        self.enemies = [enemy for enemy in self.enemies if enemy.hp > 0]
