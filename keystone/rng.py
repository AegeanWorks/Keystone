"""Deterministic random streams for replays, saves and AI-authored games.

Python's `random` module is stable in practice but not a contract; a game
that must replay byte-for-byte should not depend on it. This module implements
SplitMix64 (Steele, Lea and Flood), a small documented generator with a
64-bit state and fixed mixing constants. The first outputs for seed 0 are
pinned by tests against the published reference sequence.

Streams can be snapshotted and restored, so a save can resume the exact draw
sequence, and `fork()` derives labelled child streams for independent systems
(enemies, loot, particles) without sharing one global sequence order.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["RandomStream", "RandomStreamState"]

_MASK64 = (1 << 64) - 1
_GAMMA = 0x9E3779B97F4A7C15
_MIX_A = 0xBF58476D1CE4E5B9
_MIX_B = 0x94D049BB133111EB
_INV_2_53 = 2.0 ** -53


@dataclass(frozen=True, slots=True)
class RandomStreamState:
    """A JSON-safe snapshot of a stream's seed and current state."""

    seed: int
    state: int

    def to_dict(self) -> dict:
        return {"schema": 1, "seed": self.seed, "state": self.state}


class RandomStream:
    """One deterministic SplitMix64 stream.

    ``seed`` may be any integer; it is masked to 64 bits. Two streams with the
    same seed produce the same sequence on every platform that has 64-bit
    integers, because only additions, shifts and multiplications are used.
    """

    def __init__(self, seed: int = 0) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("random stream seed must be an integer")
        self._seed = seed & _MASK64
        self._state = self._seed

    @classmethod
    def from_snapshot(cls, data: object) -> RandomStream:
        """Restore a stream from a snapshot document."""
        if isinstance(data, RandomStreamState):
            return cls._from_parts(data.seed, data.state)
        if not isinstance(data, dict):
            raise TypeError("random stream snapshot must be a mapping")
        expected = {"schema", "seed", "state"}
        unknown = sorted(set(data) - expected)
        if unknown:
            raise ValueError(f"random stream snapshot has unknown fields: {', '.join(unknown)}")
        schema = data.get("schema", 1)
        if isinstance(schema, bool) or not isinstance(schema, int) or schema != 1:
            raise ValueError("unsupported random stream snapshot schema")
        seed = data.get("seed", 0)
        state = data.get("state", 0)
        for name, value in (("seed", seed), ("state", state)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"random stream snapshot {name} must be an integer")
        return cls._from_parts(seed, state)

    @classmethod
    def _from_parts(cls, seed: int, state: int) -> RandomStream:
        stream = cls(seed)
        stream._restore(state)
        return stream

    def _restore(self, state: int) -> None:
        self._state = state & _MASK64

    def snapshot(self) -> RandomStreamState:
        """Return the seed and state needed to resume this exact sequence."""
        return RandomStreamState(seed=self._seed, state=self._state)

    def next_u64(self) -> int:
        """Advance the stream and return the next 64-bit value."""
        self._state = (self._state + _GAMMA) & _MASK64
        value = self._state
        value = ((value ^ (value >> 30)) * _MIX_A) & _MASK64
        value = ((value ^ (value >> 27)) * _MIX_B) & _MASK64
        return (value ^ (value >> 31)) & _MASK64

    def random(self) -> float:
        """Return a float in ``[0, 1)`` built from the top 53 bits."""
        return (self.next_u64() >> 11) * _INV_2_53

    def uniform(self, low: float, high: float) -> float:
        """Return a float in ``[low, high]``; reversed bounds raise."""
        low_value = _finite(low, "uniform low")
        high_value = _finite(high, "uniform high")
        if low_value > high_value:
            raise ValueError("uniform low must not exceed high")
        return low_value + (high_value - low_value) * self.random()

    def randint(self, low: int, high: int) -> int:
        """Return an integer in ``[low, high]`` without modulo bias."""
        for name, value in (("low", low), ("high", high)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"randint {name} must be an integer")
        if low > high:
            raise ValueError("randint low must not exceed high")
        span = high - low + 1
        limit = (1 << 64) - ((1 << 64) % span)
        while True:
            draw = self.next_u64()
            if draw < limit:
                return low + draw % span

    def choice(self, items: Sequence) -> object:
        """Return one item from a non-empty sequence."""
        if not isinstance(items, Sequence):
            raise TypeError("choice needs a non-empty sequence")
        if len(items) == 0:
            raise ValueError("choice needs a non-empty sequence")
        return items[self.randint(0, len(items) - 1)]

    def shuffled(self, items: Sequence) -> tuple:
        """Return a Fisher-Yates permutation without modifying the input."""
        if not isinstance(items, Sequence):
            raise TypeError("shuffled needs a sequence")
        result = list(items)
        for index in range(len(result) - 1, 0, -1):
            swap = self.randint(0, index)
            result[index], result[swap] = result[swap], result[index]
        return tuple(result)

    def fork(self, label: str) -> RandomStream:
        """Derive a labelled child stream, consuming one draw from this one.

        The label is hashed with SHA-256, so ``fork("enemies")`` and
        ``fork("props")`` separate even when called from the same state.
        """
        if not isinstance(label, str):
            raise TypeError("random stream fork label must be a string")
        if not label.strip():
            raise ValueError("random stream fork label must be a non-blank string")
        digest = hashlib.sha256(label.encode("utf-8")).digest()
        mixed = int.from_bytes(digest[:8], "little")
        return RandomStream(self.next_u64() ^ mixed)


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result
