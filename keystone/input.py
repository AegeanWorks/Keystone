"""Generic input mapping: named actions, axes and pointer look."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keystone.gpu.context import GLContext

DEFAULT_BINDINGS = {
    "forward": "w",
    "back": "s",
    "left": "a",
    "right": "d",
    "up": "e",
    "down": "q",
    "look_left": "left",
    "look_right": "right",
    "look_up": "up",
    "look_down": "down",
    "sprint": "left_shift",
    "toggle_capture": "f1",
    "quit": "escape",
}


@dataclass(frozen=True, slots=True)
class ActionState:
    """One sampled input frame; games translate names into their own rules."""

    forward: float = 0.0
    right: float = 0.0
    up: float = 0.0
    look_yaw: float = 0.0
    look_pitch: float = 0.0
    pressed: frozenset[str] = frozenset()
    held: frozenset[str] = frozenset()
    pointer: tuple[float, float] = (0.0, 0.0)

    def without_pressed(self) -> ActionState:
        return replace(self, pressed=frozenset())

    def to_dict(self) -> dict:
        return {
            "forward": self.forward,
            "right": self.right,
            "up": self.up,
            "look_yaw": self.look_yaw,
            "look_pitch": self.look_pitch,
            "pressed": sorted(self.pressed),
            "held": sorted(self.held),
            "pointer": list(self.pointer),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActionState:
        return cls(
            forward=float(data.get("forward", 0.0)),
            right=float(data.get("right", 0.0)),
            up=float(data.get("up", 0.0)),
            look_yaw=float(data.get("look_yaw", 0.0)),
            look_pitch=float(data.get("look_pitch", 0.0)),
            pressed=frozenset(data.get("pressed", ())),
            held=frozenset(data.get("held", ())),
            pointer=tuple(data.get("pointer", (0.0, 0.0))),
        )


class InputMap:
    """Maps keys and pointer motion to action names and continuous axes."""

    def __init__(self, bindings: dict[str, str] | None = None, look_speed: float = 1.6, mouse_sensitivity: float = 0.0025) -> None:
        self.bindings = dict(DEFAULT_BINDINGS)
        if bindings:
            self.bindings.update(bindings)
        self.look_speed = look_speed
        self.mouse_sensitivity = mouse_sensitivity
        self.mouse_enabled = True
        self._held: frozenset[str] = frozenset()
        self._last_pointer: tuple[float, float] | None = None

    def bind(self, action: str, key: str) -> None:
        self.bindings[action] = key

    def set_mouse_enabled(self, enabled: bool) -> None:
        self.mouse_enabled = enabled
        self._last_pointer = None

    def sample(self, context: GLContext, dt: float = 0.0) -> ActionState:
        held = frozenset(action for action, key in self.bindings.items() if context.key_down(key))
        pressed = held - self._held
        self._held = held
        x, y = context.cursor_position()
        if self._last_pointer is None or not self.mouse_enabled:
            dx = dy = 0.0
        else:
            dx, dy = x - self._last_pointer[0], y - self._last_pointer[1]
        self._last_pointer = (x, y)
        forward = float("forward" in held) - float("back" in held)
        right = float("right" in held) - float("left" in held)
        up = float("up" in held) - float("down" in held)
        yaw = (float("look_right" in held) - float("look_left" in held)) * self.look_speed * dt
        pitch = (float("look_up" in held) - float("look_down" in held)) * self.look_speed * dt
        if self.mouse_enabled:
            yaw += dx * self.mouse_sensitivity
            pitch -= dy * self.mouse_sensitivity
        return ActionState(
            forward=forward,
            right=right,
            up=up,
            look_yaw=yaw,
            look_pitch=pitch,
            pressed=pressed,
            held=held,
            pointer=(x, y),
        )
