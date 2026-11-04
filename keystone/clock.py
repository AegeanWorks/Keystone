"""Fixed-step clock with a bounded catch-up budget."""

from __future__ import annotations

import math


class FixedStepClock:
    """Accumulates wall time and releases whole deterministic simulation steps."""

    def __init__(self, step: float = 1.0 / 60.0, max_frame: float = 0.25) -> None:
        if not math.isfinite(step) or step <= 0.0:
            raise ValueError("step must be positive and finite")
        if not math.isfinite(max_frame) or max_frame < step:
            raise ValueError("max_frame must be at least one step and finite")
        self.step = step
        self.max_frame = max_frame
        self._last: float | None = None
        self._accumulator = 0.0

    def reset(self, now: float | None = None) -> None:
        if now is not None and not math.isfinite(now):
            raise ValueError("now must be finite")
        self._last = now
        self._accumulator = 0.0

    def advance(self, now: float) -> list[float]:
        if not math.isfinite(now):
            raise ValueError("now must be finite")
        if self._last is None:
            self._last = now
            return []
        if now < self._last:
            return []
        delta = min(now - self._last, self.max_frame)
        self._last = now
        self._accumulator += delta
        steps: list[float] = []
        while self._accumulator >= self.step - 1e-12:
            steps.append(self.step)
            self._accumulator = max(0.0, self._accumulator - self.step)
        return steps
