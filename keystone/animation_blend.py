"""Deterministic one-dimensional animation blend spaces.

A blend space places clips at ordered thresholds. Sampling clamps outside the
range and linearly blends the two neighbouring poses in between, so locomotion
or any scalar parameter can drive animation without game-specific pose code.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from keystone.animation import AnimationClip, blend_poses
from keystone.scene import Transform

__all__ = ["BlendSample", "BlendSpace1D"]

_BLEND_KEYS = frozenset({"schema", "samples"})
_SAMPLE_KEYS = frozenset({"clip", "threshold"})


def _finite(label: str, value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _schema(data: Mapping[str, object]) -> None:
    schema = data.get("schema", 1)
    if isinstance(schema, bool) or schema != 1:
        raise ValueError("unsupported animation blend space schema")


@dataclass(frozen=True, slots=True)
class BlendSample:
    """One clip anchored at a scalar threshold."""

    clip: AnimationClip
    threshold: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.clip, AnimationClip):
            raise TypeError("blend sample clip must be an AnimationClip")
        _finite("blend sample threshold", self.threshold)

    def to_dict(self) -> dict[str, object]:
        return {"clip": self.clip.to_dict(), "threshold": self.threshold}

    @classmethod
    def from_dict(cls, data: object) -> BlendSample:
        if not isinstance(data, Mapping):
            raise TypeError("blend sample must be a JSON object")
        unknown = sorted(set(data) - _SAMPLE_KEYS)
        if unknown:
            raise ValueError(
                f"blend sample has unknown fields: {', '.join(unknown)}"
            )
        if "clip" not in data:
            raise ValueError("blend sample needs a clip")
        return cls(
            clip=AnimationClip.from_dict(data["clip"]),
            threshold=data.get("threshold", 0.0),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class BlendSpace1D:
    """Ordered clips blended by one finite scalar parameter."""

    samples: tuple[BlendSample, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.samples, (tuple, list)) or not self.samples:
            raise ValueError("blend space needs at least one sample")
        items = tuple(self.samples)
        if any(not isinstance(item, BlendSample) for item in items):
            raise TypeError("blend space samples must be BlendSample instances")
        ordered = tuple(sorted(items, key=lambda item: item.threshold))
        thresholds = [item.threshold for item in ordered]
        if len(set(thresholds)) != len(thresholds):
            raise ValueError("blend space thresholds must be unique")
        object.__setattr__(self, "samples", ordered)

    @property
    def thresholds(self) -> tuple[float, ...]:
        return tuple(sample.threshold for sample in self.samples)

    @property
    def duration(self) -> float:
        return max(sample.clip.duration() for sample in self.samples)

    def sample(self, parameter: float, time: float) -> dict[str, Transform]:
        """Return a blended pose for one scalar parameter and clip time."""
        value = _finite("blend parameter", parameter)
        at = _finite("blend sample time", time)
        at = max(at, 0.0)
        first = self.samples[0]
        last = self.samples[-1]
        if value <= first.threshold:
            return first.clip.sample(at)
        if value >= last.threshold:
            return last.clip.sample(at)
        for left, right in zip(self.samples, self.samples[1:]):
            if left.threshold <= value <= right.threshold:
                span = right.threshold - left.threshold
                factor = 0.0 if span == 0.0 else (value - left.threshold) / span
                return blend_poses(
                    left.clip.sample(at),
                    right.clip.sample(at),
                    factor,
                )
        return last.clip.sample(at)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": 1,
            "samples": [sample.to_dict() for sample in self.samples],
        }

    @classmethod
    def from_dict(cls, data: object) -> BlendSpace1D:
        if not isinstance(data, Mapping):
            raise TypeError("blend space must be a JSON object")
        _schema(data)
        unknown = sorted(set(data) - _BLEND_KEYS)
        if unknown:
            raise ValueError(
                f"blend space has unknown fields: {', '.join(unknown)}"
            )
        raw = data.get("samples")
        if not isinstance(raw, list) or not raw:
            raise ValueError("blend space samples must be a non-empty list")
        return cls(tuple(BlendSample.from_dict(item) for item in raw))

    def report(self) -> dict[str, object]:
        """Return a JSON-safe summary for AI clients and diagnostics."""
        return {
            "schema": 1,
            "samples": [
                {
                    "clip": sample.clip.name,
                    "threshold": sample.threshold,
                    "duration": sample.clip.duration(),
                }
                for sample in self.samples
            ],
            "thresholds": list(self.thresholds),
            "duration": self.duration,
        }
