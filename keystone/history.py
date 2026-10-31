"""Bounded undo/redo history for engine and game state."""

from __future__ import annotations

import copy
from typing import Any


class History:
    """A small, bounded undo/redo stack.

    Snapshots are deep-copied on push and on read, so a caller can never mutate a stored
    state by changing the object it passed in. ``capacity`` is the maximum number of
    snapshots retained; older entries are dropped when it is exceeded.
    """

    def __init__(self, capacity: int = 64) -> None:
        if capacity < 1:
            raise ValueError("history capacity must be positive")
        self._capacity = capacity
        self._values: list[Any] = []
        self._index = -1

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return 0 <= self._index < len(self._values) - 1

    @property
    def redo_available(self) -> bool:
        return self.can_redo

    def push(self, value: Any) -> None:
        """Record a new snapshot and discard any redo branch."""
        if self._index < len(self._values) - 1:
            del self._values[self._index + 1:]
        self._values.append(copy.deepcopy(value))
        self._index = len(self._values) - 1
        while len(self._values) > self._capacity:
            self._values.pop(0)
            if self._index > 0:
                self._index -= 1
            elif self._values:
                self._index = 0
            else:
                self._index = -1

    def undo(self) -> Any:
        """Move to the previous snapshot and return it, or None when at the bottom."""
        if not self.can_undo:
            return None
        self._index -= 1
        return copy.deepcopy(self._values[self._index]) if self._index >= 0 else None

    def redo(self) -> Any:
        """Move to the next snapshot and return it, or None when at the top."""
        if not self.can_redo:
            return None
        self._index += 1
        return copy.deepcopy(self._values[self._index])

    def peek(self) -> Any:
        """Return the current snapshot without moving, or None when empty."""
        if self._index < 0 or self._index >= len(self._values):
            return None
        return copy.deepcopy(self._values[self._index])

    def values(self) -> list[Any]:
        """Return all retained snapshots in chronological order."""
        return [copy.deepcopy(value) for value in self._values]

    def clear(self) -> None:
        self._values.clear()
        self._index = -1

    def __len__(self) -> int:
        return len(self._values)