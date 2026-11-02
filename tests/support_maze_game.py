"""Deterministic grid stub used to prove the bot playtester end to end.

This is a test fixture, not engine code: it lives outside ``keystone/``
so the core stays game-agnostic and ``test_boundary.py`` stays green.
The game owns its grid rules; the engine only sees the five operations
plus the opportunistic ``outcome``/``score`` snapshot keys.

Movement maps the generic ``forward``/``right`` axes to grid steps, the
same way any external game maps generic input to its own rules.
"""

from __future__ import annotations

from collections import deque

from keystone.scene import Node, Scene


def _step(value: float) -> int:
    if value > 0.5:
        return 1
    if value < -0.5:
        return -1
    return 0


def maze_shortest_path(config: dict) -> int | None:
    """Exact grid BFS ground truth: steps from spawn to goal, or None."""
    width = int(config["width"])
    height = int(config["height"])
    walls = {tuple(cell) for cell in config.get("walls", [])}
    hazards = {tuple(cell) for cell in config.get("hazards", [])}
    spawn = tuple(config["spawn"])
    goal = tuple(config["goal"])
    if spawn == goal:
        return 0
    if spawn in walls or spawn in hazards or goal in walls:
        return None
    seen = {spawn}
    queue = deque([(spawn, 0)])
    while queue:
        (x, y), dist = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if (nx, ny) in walls or (nx, ny) in hazards or (nx, ny) in seen:
                continue
            if (nx, ny) == goal:
                return dist + 1
            seen.add((nx, ny))
            queue.append(((nx, ny), dist + 1))
    return None


def reachable(config: dict) -> bool:
    """Fixture-side exact reachability used as fairness ground truth."""
    return maze_shortest_path(config) is not None


def open_config(width: int = 5, height: int = 5, time_limit: int = 100) -> dict:
    return {
        "width": width,
        "height": height,
        "walls": [],
        "hazards": [],
        "spawn": [0, 0],
        "goal": [width - 1, height - 1],
        "time_limit": time_limit,
    }


def walled_goal_config() -> dict:
    """Goal fully surrounded: provably unwinnable."""
    return {
        "width": 5,
        "height": 5,
        "walls": [[3, 4], [4, 3], [3, 3]],
        "hazards": [],
        "spawn": [0, 0],
        "goal": [4, 4],
        "time_limit": 100,
    }


def hazard_spawn_config() -> dict:
    """Spawn sits on a hazard: terminal loss on frame zero."""
    return {
        "width": 5,
        "height": 5,
        "walls": [],
        "hazards": [[0, 0]],
        "spawn": [0, 0],
        "goal": [4, 4],
        "time_limit": 100,
    }


def tight_clock_config() -> dict:
    """Shortest path needs 8 steps; the clock allows 3."""
    return {
        "width": 5,
        "height": 5,
        "walls": [],
        "hazards": [],
        "spawn": [0, 0],
        "goal": [4, 4],
        "time_limit": 3,
    }


def optimal_actions(config: dict) -> list[dict]:
    """Greedy reference solution: shortest-path actions, or empty when unreachable."""
    width = int(config["width"])
    height = int(config["height"])
    walls = {tuple(cell) for cell in config.get("walls", [])}
    hazards = {tuple(cell) for cell in config.get("hazards", [])}
    spawn = tuple(config["spawn"])
    goal = tuple(config["goal"])
    previous: dict[tuple[int, int], tuple[int, int] | None] = {spawn: None}
    queue = deque([spawn])
    while queue:
        current = queue.popleft()
        if current == goal:
            break
        x, y = current
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nxt[0] < width and 0 <= nxt[1] < height):
                continue
            if nxt in walls or nxt in hazards or nxt in previous:
                continue
            previous[nxt] = current
            queue.append(nxt)
    if goal not in previous:
        return []
    path: list[tuple[int, int]] = []
    node: tuple[int, int] | None = goal
    while node is not None and node != spawn:
        path.append(node)
        node = previous[node]
    path.reverse()
    actions: list[dict] = []
    position = spawn
    for cell in path:
        actions.append(
            {
                "forward": float(cell[1] - position[1]),
                "right": float(cell[0] - position[0]),
            }
        )
        position = cell
    return actions


class MazeGame:
    """A deterministic grid chase: reach the goal cell before the clock."""

    name = "maze-stub"

    def __init__(self, config: dict | None = None) -> None:
        self.config = dict(open_config() if config is None else config)
        self._pos = list(self.config["spawn"])
        self._steps = 0
        self.scene = Scene()

    def build_scene(self) -> Scene:
        self.scene = Scene()
        self.scene.add(Node("maze-floor", id="maze-floor"))
        self._pos = list(self.config["spawn"])
        self._steps = 0
        return self.scene

    def update(self, dt: float, actions: object) -> None:
        width = int(self.config["width"])
        height = int(self.config["height"])
        walls = {tuple(cell) for cell in self.config.get("walls", [])}
        dx = _step(getattr(actions, "right", 0.0))
        dy = _step(getattr(actions, "forward", 0.0))
        if dx != 0 and dy != 0:
            dy = 0
        target = [self._pos[0] + dx, self._pos[1] + dy]
        if 0 <= target[0] < width and 0 <= target[1] < height and tuple(target) not in walls:
            self._pos = target
        self._steps += 1

    def snapshot(self) -> dict[str, object]:
        hazards = {tuple(cell) for cell in self.config.get("hazards", [])}
        goal = list(self.config["goal"])
        if tuple(self._pos) in hazards:
            outcome = "lose"
        elif self._pos == goal:
            outcome = "win"
        elif self._steps >= int(self.config.get("time_limit", 100)):
            outcome = "lose"
        else:
            outcome = "ongoing"
        score = max(0, 100 - self._steps) if outcome == "win" else -self._steps
        return {
            "pos": list(self._pos),
            "goal": goal,
            "steps": self._steps,
            "time_limit": int(self.config.get("time_limit", 100)),
            "outcome": outcome,
            "score": score,
        }

    def actions(self) -> dict[str, object]:
        return {"axes": ["forward", "right"], "buttons": ["wait"]}

    def status(self) -> str:
        return f"maze {self._pos} steps={self._steps}"


def Factory(config: dict | None = None) -> MazeGame:
    return MazeGame(config)


def FairMaze() -> MazeGame:
    return MazeGame(open_config())


def WalledMaze() -> MazeGame:
    return MazeGame(walled_goal_config())


def HazardMaze() -> MazeGame:
    return MazeGame(hazard_spawn_config())


def TightMaze() -> MazeGame:
    return MazeGame(tight_clock_config())
