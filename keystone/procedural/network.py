"""Seeded cyber network: terminals, links, hack progress and a living alert."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from keystone.procedural.dungeon import Dungeon


@dataclass
class Terminal:
    terminal_id: str
    x: float
    z: float
    progress: float = 0.0
    hacked: bool = False


@dataclass
class Network:
    seed: int
    terminals: tuple[Terminal, ...]
    links: tuple[tuple[str, str], ...]
    alert: float = 0.0
    version: int = 0
    _by_id: dict[str, Terminal] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._by_id = {terminal.terminal_id: terminal for terminal in self.terminals}

    @classmethod
    def generate(cls, seed: int, dungeon: Dungeon, count: int = 4) -> Network:
        excluded = {dungeon.spawn, dungeon.exit}
        candidates = [room for room in dungeon.rooms if room.center not in excluded]
        rng = random.Random(seed)
        rng.shuffle(candidates)
        chosen = candidates[: min(count, len(candidates))]
        chosen.sort(key=lambda room: (room.center[0], room.center[1]))
        terminals = tuple(
            Terminal(f"node-{index + 1:02d}", room.center[0] + 0.5, room.center[1] + 0.5)
            for index, room in enumerate(chosen)
        )
        links: list[tuple[str, str]] = []
        for index in range(1, len(terminals)):
            previous = min(
                terminals[:index],
                key=lambda terminal: abs(terminal.x - terminals[index].x) + abs(terminal.z - terminals[index].z),
            )
            links.append((previous.terminal_id, terminals[index].terminal_id))
        if len(terminals) >= 3:
            extra = (terminals[0].terminal_id, terminals[-1].terminal_id)
            if extra not in links and (extra[1], extra[0]) not in links:
                links.append(extra)
        return cls(seed, terminals, tuple(links))

    @property
    def complete(self) -> bool:
        return all(terminal.hacked for terminal in self.terminals)

    @property
    def hacked_count(self) -> int:
        return sum(1 for terminal in self.terminals if terminal.hacked)

    def terminal(self, terminal_id: str) -> Terminal:
        if terminal_id not in self._by_id:
            raise ValueError(f"unknown terminal '{terminal_id}'")
        return self._by_id[terminal_id]

    def near_terminal(self, x: float, z: float, radius: float = 1.8) -> Terminal | None:
        best: Terminal | None = None
        best_distance = radius
        for terminal in self.terminals:
            distance = math.hypot(terminal.x - x, terminal.z - z)
            if distance <= best_distance:
                best, best_distance = terminal, distance
        return best

    def hack(self, terminal_id: str) -> str | None:
        terminal = self.terminal(terminal_id)
        if terminal.hacked:
            return None
        terminal.progress = min(1.0, terminal.progress + 0.25)
        terminal.hacked = terminal.progress >= 1.0
        self.alert = min(100.0, self.alert + 8.0)
        self.version += 1
        if terminal.hacked:
            return f"Terminal {terminal_id} compromised."
        return f"Terminal {terminal_id} at {terminal.progress:.0%}."

    def update(self, dt: float) -> None:
        if dt < 0.0:
            raise ValueError("dt cannot be negative")
        self.alert = max(0.0, self.alert - dt * 0.6)

    def snapshot(self) -> dict:
        return {
            "alert": round(self.alert, 2),
            "hacked": self.hacked_count,
            "complete": self.complete,
            "terminals": [
                {
                    "id": terminal.terminal_id,
                    "x": round(terminal.x, 2),
                    "z": round(terminal.z, 2),
                    "progress": round(terminal.progress, 2),
                    "hacked": terminal.hacked,
                }
                for terminal in self.terminals
            ],
            "links": [list(link) for link in self.links],
        }
