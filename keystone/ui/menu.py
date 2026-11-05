"""Game-agnostic pause menu state: items, selection and activation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MenuItem:
    """One labelled action the human can choose."""

    label: str
    action: str


DEFAULT_ITEMS = (
    MenuItem("RESUME", "resume"),
    MenuItem("HIDE HUD", "toggle_ui"),
    MenuItem("QUIT", "quit"),
)


class PauseMenu:
    """Wraps selection over a fixed item list; contains no rendering or input."""

    def __init__(self, items: tuple[MenuItem, ...] = DEFAULT_ITEMS) -> None:
        if not items:
            raise ValueError("pause menu needs at least one item")
        self.items = items
        self.index = 0

    def move(self, delta: int) -> int:
        """Move the selection by delta, wrapping at both ends."""
        if isinstance(delta, bool) or not isinstance(delta, int):
            raise TypeError("menu move delta must be an integer")
        self.index = (self.index + delta) % len(self.items)
        return self.index

    def action(self) -> str:
        """Return the action of the selected item."""
        return self.items[self.index].action
