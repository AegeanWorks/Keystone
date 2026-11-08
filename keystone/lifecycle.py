"""Deterministic start/update/stop lifecycle for scene components.

Components opt in by defining ``start(context)``, ``update(context)`` and/or
``stop(context)`` methods. Components are visited in scene traversal order and,
within one node, by component type. Started components update once per tick and
stop in reverse start order. Hooks receive a frozen :class:`LifecycleContext`
with the scene, node, component, fixed ``dt`` and frame number.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from keystone.scene import Node, Scene

__all__ = [
    "LIFECYCLE_HOOKS",
    "ComponentRuntime",
    "LifecycleContext",
    "lifecycle_hooks",
]

LIFECYCLE_HOOKS = ("start", "update", "stop")


def lifecycle_hooks(value: object) -> tuple[str, ...]:
    """Return the lifecycle hook names implemented by a component or type."""
    return tuple(
        name for name in LIFECYCLE_HOOKS if callable(getattr(value, name, None))
    )


@dataclass(frozen=True, slots=True)
class LifecycleContext:
    """Arguments passed to one component lifecycle hook."""

    scene: Scene
    node: Node
    component: object
    dt: float
    frame: int


class ComponentRuntime:
    """Run deterministic component lifecycle hooks for one scene."""

    def __init__(self, scene: Scene) -> None:
        if not isinstance(scene, Scene):
            raise TypeError("lifecycle target must be a Scene")
        self.scene = scene
        self.frame = 0
        self.running = False
        self._started: list[tuple[Node, object]] = []
        self._started_keys: set[tuple[int, int]] = set()

    def _entries(self) -> list[tuple[Node, object]]:
        entries: list[tuple[Node, object]] = []
        for node in self.scene.traverse():
            if node is self.scene.root:
                continue
            components = sorted(
                node.components.values(),
                key=lambda item: (type(item).__module__, type(item).__qualname__),
            )
            for component in components:
                entries.append((node, component))
        return entries

    def _context(
        self, node: Node, component: object, dt: float
    ) -> LifecycleContext:
        return LifecycleContext(self.scene, node, component, dt, self.frame)

    def _start_component(self, node: Node, component: object) -> bool:
        key = (id(node), id(component))
        if key in self._started_keys:
            return False
        if not lifecycle_hooks(component):
            return False
        start = getattr(component, "start", None)
        if callable(start):
            start(self._context(node, component, 0.0))
        self._started.append((node, component))
        self._started_keys.add(key)
        return True

    def start(self) -> int:
        """Start every hook-bearing component once and return the count."""
        if self.running:
            raise ValueError("lifecycle runtime is already running")
        self.running = True
        self.frame = 0
        started = 0
        for node, component in self._entries():
            if self._start_component(node, component):
                started += 1
        return started

    def update(self, dt: float) -> int:
        """Advance one fixed tick and return the number of update hooks run."""
        if not self.running:
            raise ValueError("lifecycle runtime is not running")
        if isinstance(dt, bool) or not isinstance(dt, (int, float)):
            raise TypeError("lifecycle dt must be a number")
        if not math.isfinite(dt) or dt < 0.0:
            raise ValueError("lifecycle dt must be finite and non-negative")
        self.frame += 1
        updated = 0
        for node, component in self._entries():
            self._start_component(node, component)
            update = getattr(component, "update", None)
            if callable(update):
                update(self._context(node, component, float(dt)))
                updated += 1
        return updated

    def stop(self) -> int:
        """Stop started components in reverse order and return the count."""
        if not self.running:
            raise ValueError("lifecycle runtime is not running")
        stopped = 0
        try:
            for node, component in reversed(self._started):
                stop = getattr(component, "stop", None)
                if callable(stop):
                    stop(self._context(node, component, 0.0))
                    stopped += 1
        finally:
            self._started.clear()
            self._started_keys.clear()
            self.running = False
        return stopped

    def describe(self) -> dict[str, object]:
        """Return the JSON-safe runtime summary for editor documents."""
        available = {
            hook
            for _, component in self._started
            for hook in lifecycle_hooks(component)
        }
        hooks = [hook for hook in LIFECYCLE_HOOKS if hook in available]
        return {
            "active": self.running,
            "frame": self.frame,
            "started": len(self._started),
            "hooks": hooks,
        }
