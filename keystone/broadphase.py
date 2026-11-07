"""Deterministic spatial-grid broadphase for nearby AABB candidates."""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterator

from keystone.math3d import Vec3
from keystone.physics import AABB, aabb_overlap

Cell = tuple[int, int, int]

#: A single proxy may not span more cells than this; beyond it the grid
#: degrades into a hang and callers should use a larger cell_size.
MAX_PROXY_CELLS = 100_000


class SpatialGrid:
    """A uniform grid of AABB proxies with exact overlap filtering.

    Results preserve insertion order so callers get deterministic output even
    when several proxies share a cell. Cell size is a performance trade-off,
    not a correctness setting: every exact overlap is still returned.
    """

    def __init__(self, cell_size: float = 2.0) -> None:
        if isinstance(cell_size, bool) or not isinstance(cell_size, (int, float)):
            raise TypeError("cell_size must be a real number")
        if not math.isfinite(cell_size) or cell_size <= 0.0:
            raise ValueError("cell_size must be positive and finite")
        self.cell_size = float(cell_size)
        self._boxes: dict[Hashable, AABB] = {}
        self._order: dict[Hashable, int] = {}
        self._cells: dict[Cell, set[Hashable]] = {}
        self._next_order = 0

    def __len__(self) -> int:
        return len(self._boxes)

    def __contains__(self, key: object) -> bool:
        return key in self._boxes

    def get(self, key: Hashable) -> AABB | None:
        return self._boxes.get(key)

    def insert(self, key: Hashable, box: AABB) -> None:
        """Insert or replace a proxy and its current bounds."""
        cells = list(self._cells_for(box))
        if key in self._boxes:
            order = self._order[key]
            self.remove(key)
            self._boxes[key] = box
            self._order[key] = order
        else:
            self._boxes[key] = box
            self._order[key] = self._next_order
            self._next_order += 1
        for cell in cells:
            self._cells.setdefault(cell, set()).add(key)

    def update(self, key: Hashable, box: AABB) -> None:
        """Move a proxy; unknown keys are inserted."""
        self.insert(key, box)

    def remove(self, key: Hashable) -> bool:
        """Remove a proxy; return whether it existed."""
        box = self._boxes.pop(key, None)
        if box is None:
            return False
        self._order.pop(key, None)
        for cell in self._cells_for(box):
            members = self._cells.get(cell)
            if members is None:
                continue
            members.discard(key)
            if not members:
                del self._cells[cell]
        return True

    def clear(self) -> None:
        self._boxes.clear()
        self._order.clear()
        self._cells.clear()
        self._next_order = 0

    def query(self, box: AABB) -> list[Hashable]:
        """Return proxies whose bounds overlap ``box`` in insertion order."""
        candidates = self._candidates(box)
        return [
            key
            for key in sorted(candidates, key=self._order.__getitem__)
            if aabb_overlap(self._boxes[key], box)
        ]

    def query_point(self, point: Vec3) -> list[Hashable]:
        return self.query(AABB(point, Vec3()))

    def pairs(self) -> list[tuple[Hashable, Hashable]]:
        """Return every exact overlapping proxy pair, once, in insertion order."""
        found: set[tuple[Hashable, Hashable]] = set()
        for members in self._cells.values():
            ordered = sorted(members, key=self._order.__getitem__)
            for first_index, first in enumerate(ordered):
                for second in ordered[first_index + 1 :]:
                    if first not in self._boxes or second not in self._boxes:
                        continue
                    if not aabb_overlap(self._boxes[first], self._boxes[second]):
                        continue
                    pair = (first, second)
                    if self._order[pair[0]] > self._order[pair[1]]:
                        pair = (pair[1], pair[0])
                    found.add(pair)
        return sorted(found, key=lambda pair: (self._order[pair[0]], self._order[pair[1]]))

    def _cells_for(self, box: AABB) -> Iterator[Cell]:
        low = box.low() / self.cell_size
        high = box.high() / self.cell_size
        corners = (low.x, low.y, low.z, high.x, high.y, high.z)
        if not all(math.isfinite(value) for value in corners):
            raise ValueError("broadphase bounds must be finite")
        low_cell = (math.floor(low.x), math.floor(low.y), math.floor(low.z))
        high_cell = (math.floor(high.x), math.floor(high.y), math.floor(high.z))
        total = (high_cell[0] - low_cell[0] + 1) * (high_cell[1] - low_cell[1] + 1) * (high_cell[2] - low_cell[2] + 1)
        if total > MAX_PROXY_CELLS:
            raise ValueError(
                f"broadphase box spans {total} cells (limit {MAX_PROXY_CELLS}); "
                "use a larger cell_size or a smaller proxy"
            )
        for x in range(low_cell[0], high_cell[0] + 1):
            for y in range(low_cell[1], high_cell[1] + 1):
                for z in range(low_cell[2], high_cell[2] + 1):
                    yield (x, y, z)

    def _candidates(self, box: AABB) -> set[Hashable]:
        found: set[Hashable] = set()
        try:
            for cell in self._cells_for(box):
                found.update(self._cells.get(cell, ()))
        except ValueError:
            # A query larger than the cell budget degrades to a linear scan;
            # correctness never depends on cell_size.
            return set(self._boxes)
        return found
