"""Game-agnostic trigger volumes with enter/exit tracking."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from keystone.physics import AABB, aabb_overlap


@dataclass(frozen=True, slots=True)
class TriggerVolume:
    """A named AABB that reports when a body enters or leaves it."""

    name: str
    box: AABB

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("trigger name must be a non-empty string")

    def contains(self, body: AABB) -> bool:
        return aabb_overlap(self.box, body)


@dataclass(frozen=True, slots=True)
class TriggerEvents:
    """The enter, exit and active sets for one tracker update."""

    entered: tuple[str, ...] = ()
    exited: tuple[str, ...] = ()
    active: frozenset[str] = frozenset()


@dataclass(slots=True)
class TriggerTracker:
    """Remember active trigger names across updates."""

    active: set[str] = field(default_factory=set)

    def update(self, body: AABB, volumes: Iterable[TriggerVolume]) -> TriggerEvents:
        current = {volume.name for volume in volumes if volume.contains(body)}
        entered = tuple(sorted(current - self.active))
        exited = tuple(sorted(self.active - current))
        self.active = current
        return TriggerEvents(entered, exited, frozenset(current))

    def reset(self) -> None:
        self.active.clear()
