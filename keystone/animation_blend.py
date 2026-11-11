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

__all__ = ["BlendSample", "BlendSample2D", "BlendSpace1D", "BlendSpace2D"]

_BLEND_KEYS = frozenset({"schema", "samples"})
_SAMPLE_KEYS = frozenset({"clip", "threshold"})
_SAMPLE_2D_KEYS = frozenset({"clip", "x", "y"})


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

@dataclass(frozen=True, slots=True)
class BlendSample2D:
    """One clip anchored at a point in a two-parameter plane."""

    clip: AnimationClip
    x: float = 0.0
    y: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.clip, AnimationClip):
            raise TypeError("blend sample clip must be an AnimationClip")
        _finite("blend sample x", self.x)
        _finite("blend sample y", self.y)

    def to_dict(self) -> dict[str, object]:
        return {"clip": self.clip.to_dict(), "x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: object) -> BlendSample2D:
        if not isinstance(data, Mapping):
            raise TypeError("2D blend sample must be a JSON object")
        unknown = sorted(set(data) - _SAMPLE_2D_KEYS)
        if unknown:
            raise ValueError(f"2D blend sample has unknown fields: {', '.join(unknown)}")
        if "clip" not in data:
            raise ValueError("2D blend sample needs a clip")
        return cls(
            clip=AnimationClip.from_dict(data["clip"]),
            x=data.get("x", 0.0),  # type: ignore[arg-type]
            y=data.get("y", 0.0),  # type: ignore[arg-type]
        )


def _cell(axis: tuple[float, ...], value: float) -> tuple[int, int, float]:
    """Return the bracketing indices and blend factor on one axis."""
    if len(axis) == 1:
        return (0, 0, 0.0)
    for index in range(len(axis) - 1):
        if axis[index] <= value <= axis[index + 1]:
            span = axis[index + 1] - axis[index]
            return (index, index + 1, 0.0 if span == 0.0 else (value - axis[index]) / span)
    last = len(axis) - 1
    return (last, last, 0.0)


@dataclass(frozen=True, slots=True)
class BlendSpace2D:
    """A rectangular grid of clips blended bilinearly in two parameters.

    Unity and Unreal author 2D locomotion on a speed/direction plane. This
    space requires a complete rectangle of samples, which makes the weights
    exact and deterministic: each corner of the surrounding cell contributes
    bilinearly. Outside the grid the nearest edge wins, so a caller may clamp
    parameters itself or let the space do it.
    """

    samples: tuple[BlendSample2D, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.samples, (tuple, list)) or not self.samples:
            raise ValueError("2D blend space needs at least one sample")
        items = tuple(self.samples)
        if any(not isinstance(item, BlendSample2D) for item in items):
            raise TypeError("2D blend space samples must be BlendSample2D instances")
        coords = {(item.x, item.y) for item in items}
        if len(coords) != len(items):
            raise ValueError("2D blend space coordinates must be unique")
        xs = tuple(sorted({item.x for item in items}))
        ys = tuple(sorted({item.y for item in items}))
        if len(items) != len(xs) * len(ys):
            raise ValueError(
                "2D blend space samples must form a complete rectangular grid; "
                f"got {len(items)} samples for {len(xs)}x{len(ys)} coordinates"
            )
        lookup = {(item.x, item.y): item for item in items}
        for x in xs:
            for y in ys:
                if (x, y) not in lookup:
                    raise ValueError(
                        "2D blend space samples must form a complete rectangular grid; "
                        f"missing ({x}, {y})"
                    )
        object.__setattr__(self, "samples", tuple(lookup[(x, y)] for x in xs for y in ys))

    @property
    def xs(self) -> tuple[float, ...]:
        return tuple(sorted({sample.x for sample in self.samples}))

    @property
    def ys(self) -> tuple[float, ...]:
        return tuple(sorted({sample.y for sample in self.samples}))

    @property
    def duration(self) -> float:
        return max(sample.clip.duration() for sample in self.samples)

    def sample(self, x_parameter: float, y_parameter: float, time: float) -> dict[str, Transform]:
        """Return the bilinearly blended pose at one point and clip time."""
        x_value = _finite("blend x parameter", x_parameter)
        y_value = _finite("blend y parameter", y_parameter)
        at = max(_finite("blend sample time", time), 0.0)
        xs = self.xs
        ys = self.ys
        if len(xs) == 1 and len(ys) == 1:
            return self.samples[0].clip.sample(at)
        x0, x1, fx = _cell(xs, max(xs[0], min(xs[-1], x_value)))
        y0, y1, fy = _cell(ys, max(ys[0], min(ys[-1], y_value)))
        width = len(ys)
        bottom_left = self.samples[x0 * width + y0].clip.sample(at)
        bottom_right = self.samples[x1 * width + y0].clip.sample(at)
        top_left = self.samples[x0 * width + y1].clip.sample(at)
        top_right = self.samples[x1 * width + y1].clip.sample(at)
        bottom = blend_poses(bottom_left, bottom_right, fx)
        top = blend_poses(top_left, top_right, fx)
        return blend_poses(bottom, top, fy)

    def to_dict(self) -> dict[str, object]:
        return {"schema": 1, "samples": [sample.to_dict() for sample in self.samples]}

    @classmethod
    def from_dict(cls, data: object) -> BlendSpace2D:
        if not isinstance(data, Mapping):
            raise TypeError("2D blend space must be a JSON object")
        _schema(data)
        unknown = sorted(set(data) - _BLEND_KEYS)
        if unknown:
            raise ValueError(f"2D blend space has unknown fields: {', '.join(unknown)}")
        raw = data.get("samples")
        if not isinstance(raw, list) or not raw:
            raise ValueError("2D blend space samples must be a non-empty list")
        return cls(tuple(BlendSample2D.from_dict(item) for item in raw))

    def report(self) -> dict[str, object]:
        """Return a JSON-safe summary for AI clients and diagnostics."""
        return {
            "schema": 1,
            "xs": list(self.xs),
            "ys": list(self.ys),
            "samples": [
                {
                    "clip": sample.clip.name,
                    "x": sample.x,
                    "y": sample.y,
                    "duration": sample.clip.duration(),
                }
                for sample in self.samples
            ],
            "duration": self.duration,
        }
