"""Deterministic parameter-driven animation state machines.

Games and AI tools describe states, clips and parameter transitions in JSON;
the machine owns one AnimationController and advances it deterministically.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace

from keystone.animation import AnimationClip, AnimationController
from keystone.scene import Transform

__all__ = ["AnimationState", "AnimationStateMachine", "AnimationTransition"]

OPERATORS = ("greater", "less", "equal", "not_equal", "trigger")
PARAMETER = float | bool
_STATE_KEYS = frozenset({"name", "clip", "loop", "speed"})
_TRANSITION_KEYS = frozenset(
    {"source", "target", "parameter", "operator", "value", "duration"}
)
_MACHINE_KEYS = frozenset(
    {"schema", "states", "transitions", "parameters", "current"}
)


def _name(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-blank string")
    return value


def _finite(label: str, value: object, *, minimum: float | None = None) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} must be a finite number")
    number = float(value)
    if minimum is not None and number < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return number


def _parameter_value(label: str, value: object) -> PARAMETER:
    if isinstance(value, bool):
        return value
    return _finite(label, value)


@dataclass(frozen=True, slots=True)
class AnimationState:
    """One named clip with its loop and speed settings."""

    name: str
    clip: AnimationClip
    loop: bool = True
    speed: float = 1.0

    def __post_init__(self) -> None:
        _name("state name", self.name)
        if not isinstance(self.clip, AnimationClip):
            raise TypeError("state clip must be an AnimationClip")
        if not isinstance(self.loop, bool):
            raise TypeError("state loop must be a boolean")
        _finite("state speed", self.speed, minimum=0.0)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "clip": self.clip.to_dict(),
            "loop": self.loop,
            "speed": self.speed,
        }

    @classmethod
    def from_dict(cls, data: object) -> AnimationState:
        if not isinstance(data, dict):
            raise TypeError("animation state must be a JSON object")
        unknown = set(data) - _STATE_KEYS
        if unknown:
            raise ValueError(f"animation state has unknown keys: {sorted(unknown)}")
        if "name" not in data or "clip" not in data:
            raise ValueError("animation state needs a name and clip")
        return cls(
            name=data["name"],
            clip=AnimationClip.from_dict(data["clip"]),
            loop=data.get("loop", True),
            speed=data.get("speed", 1.0),
        )


@dataclass(frozen=True, slots=True)
class AnimationTransition:
    """One parameter condition that moves between states."""

    source: str
    target: str
    parameter: str
    operator: str = "greater"
    value: float = 0.0
    duration: float = 0.2

    def __post_init__(self) -> None:
        _name("transition source", self.source)
        _name("transition target", self.target)
        _name("transition parameter", self.parameter)
        if self.operator not in OPERATORS:
            raise ValueError(
                "transition operator must be one of " + ", ".join(OPERATORS)
            )
        _finite("transition value", self.value)
        _finite("transition duration", self.duration, minimum=0.0)

    def matches(self, parameters: Mapping[str, PARAMETER]) -> bool:
        """Return whether the parameter condition currently passes."""
        actual = parameters.get(self.parameter, 0.0)
        if self.operator == "trigger":
            return bool(actual)
        number = 1.0 if isinstance(actual, bool) else float(actual)
        if self.operator == "greater":
            return number > self.value
        if self.operator == "less":
            return number < self.value
        if self.operator == "equal":
            return number == self.value
        return number != self.value

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "parameter": self.parameter,
            "operator": self.operator,
            "value": self.value,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: object) -> AnimationTransition:
        if not isinstance(data, dict):
            raise TypeError("animation transition must be a JSON object")
        unknown = set(data) - _TRANSITION_KEYS
        if unknown:
            raise ValueError(
                f"animation transition has unknown keys: {sorted(unknown)}"
            )
        for required in ("source", "target", "parameter"):
            if required not in data:
                raise ValueError(
                    f"animation transition needs {required!r}"
                )
        return cls(
            source=data["source"],
            target=data["target"],
            parameter=data["parameter"],
            operator=data.get("operator", "greater"),
            value=data.get("value", 0.0),
            duration=data.get("duration", 0.2),
        )


class AnimationStateMachine:
    """One deterministic controller driven by named states and transitions."""

    def __init__(
        self,
        states: object,
        transitions: object = (),
        parameters: object = None,
        current: object = None,
    ) -> None:
        state_items = tuple(states)  # type: ignore[arg-type]
        if not state_items:
            raise ValueError("state machine needs at least one state")
        if any(not isinstance(item, AnimationState) for item in state_items):
            raise TypeError(
                "state machine states must be AnimationState instances"
            )
        names = [item.name for item in state_items]
        if len(set(names)) != len(names):
            raise ValueError("state machine state names must be unique")
        self.states = {item.name: item for item in state_items}
        transition_items = tuple(transitions)  # type: ignore[arg-type]
        if any(
            not isinstance(item, AnimationTransition)
            for item in transition_items
        ):
            raise TypeError(
                "state machine transitions must be AnimationTransition instances"
            )
        for transition in transition_items:
            if transition.source not in self.states:
                raise ValueError(
                    f"transition source {transition.source!r} is not a state"
                )
            if transition.target not in self.states:
                raise ValueError(
                    f"transition target {transition.target!r} is not a state"
                )
            if transition.source == transition.target:
                raise ValueError("self transitions are not supported")
        self.transitions = transition_items
        if parameters is None:
            raw_parameters: Mapping[str, object] = {}
        elif isinstance(parameters, Mapping):
            raw_parameters = parameters
        else:
            raise TypeError("state machine parameters must be a mapping")
        self.parameters = {
            _name("parameter name", key): _parameter_value(
                f"parameter {key!r}", value
            )
            for key, value in raw_parameters.items()
        }
        selected = names[0] if current is None else _name(
            "current state", current
        )
        if selected not in self.states:
            raise ValueError(f"current state {selected!r} is not defined")
        self.events: list[str] = []
        self.controller = AnimationController()
        for state in state_items:
            self.controller.add(replace(state.clip, name=state.name))
        self.current = ""
        self.play(selected, restart=True)

    def _state(self, name: str) -> AnimationState:
        if name not in self.states:
            raise KeyError(f"unknown animation state {name!r}")
        return self.states[name]

    def play(self, name: str, restart: bool = True) -> None:
        if not isinstance(restart, bool):
            raise TypeError("restart must be a boolean")
        state = self._state(name)
        self.current = state.name
        self.controller.play(state.name, restart=restart)
        self.controller.loop = state.loop
        self.controller.speed = state.speed

    def set_parameter(self, name: str, value: object) -> None:
        key = _name("parameter name", name)
        self.parameters[key] = _parameter_value(f"parameter {key!r}", value)

    def set_trigger(self, name: str) -> None:
        self.set_parameter(name, True)

    def available_transitions(self) -> tuple[AnimationTransition, ...]:
        return tuple(
            transition
            for transition in self.transitions
            if transition.source == self.current
            and transition.matches(self.parameters)
        )

    def advance(self, dt: float) -> dict[str, Transform]:
        _finite("animation dt", dt, minimum=0.0)
        for transition in self.transitions:
            if transition.source != self.current:
                continue
            if not transition.matches(self.parameters):
                continue
            target = self._state(transition.target)
            self.current = target.name
            self.controller.crossfade(
                target.name, transition.duration
            )
            self.controller.loop = target.loop
            self.controller.speed = target.speed
            if transition.operator == "trigger":
                self.parameters[transition.parameter] = False
            break
        pose, events = self.controller.advance_with_events(float(dt))
        self.events.extend(events)
        return pose

    def take_events(self) -> list[str]:
        events = list(self.events)
        self.events.clear()
        return events

    def report(self) -> dict[str, object]:
        state = self.states[self.current]
        return {
            "schema": 1,
            "current": self.current,
            "clip": state.clip.name,
            "time": round(self.controller.time, 6),
            "states": sorted(self.states),
            "transitions": len(self.transitions),
            "parameters": dict(sorted(self.parameters.items())),
            "blending": self.controller.blending,
            "events": list(self.events),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": 1,
            "states": [state.to_dict() for state in self.states.values()],
            "transitions": [
                transition.to_dict() for transition in self.transitions
            ],
            "parameters": dict(sorted(self.parameters.items())),
            "current": self.current,
        }

    @classmethod
    def from_dict(cls, data: object) -> AnimationStateMachine:
        if not isinstance(data, dict):
            raise TypeError("state machine document must be a JSON object")
        schema = data.get("schema", 1)
        if isinstance(schema, bool) or schema != 1:
            raise ValueError("unsupported state machine schema")
        unknown = set(data) - _MACHINE_KEYS
        if unknown:
            raise ValueError(
                f"state machine has unknown keys: {sorted(unknown)}"
            )
        raw_states = data.get("states")
        if not isinstance(raw_states, list) or not raw_states:
            raise ValueError("state machine states must be a non-empty list")
        states = [AnimationState.from_dict(item) for item in raw_states]
        raw_transitions = data.get("transitions", [])
        if not isinstance(raw_transitions, list):
            raise TypeError("state machine transitions must be a list")
        transitions = [
            AnimationTransition.from_dict(item) for item in raw_transitions
        ]
        raw_parameters = data.get("parameters", {})
        if not isinstance(raw_parameters, dict):
            raise TypeError("state machine parameters must be a mapping")
        return cls(
            states=states,
            transitions=transitions,
            parameters=raw_parameters,
            current=data.get("current"),
        )
