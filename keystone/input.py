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
    "toggle_ui": "h",
    "pause": "p",
    "confirm": "enter",
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
    mouse_clicked: bool = False

    def without_pressed(self) -> ActionState:
        return replace(self, pressed=frozenset(), mouse_clicked=False)

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
            "mouse_clicked": self.mouse_clicked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActionState:
        pressed = data.get("pressed", ())
        if isinstance(pressed, (str, bytes)) or not isinstance(pressed, (list, tuple, set, frozenset)):
            raise TypeError("pressed must be a list of action names")
        for item in pressed:
            if not isinstance(item, str):
                raise TypeError("pressed must be a list of action names")
        held = data.get("held", ())
        if isinstance(held, (str, bytes)) or not isinstance(held, (list, tuple, set, frozenset)):
            raise TypeError("held must be a list of action names")
        for item in held:
            if not isinstance(item, str):
                raise TypeError("held must be a list of action names")
        pointer_raw = data.get("pointer", (0.0, 0.0))
        if isinstance(pointer_raw, (str, bytes)) or not isinstance(pointer_raw, (list, tuple)):
            raise TypeError("pointer must be a pair of numbers")
        pointer = tuple(pointer_raw)
        if len(pointer) != 2:
            raise ValueError("pointer must be a pair of numbers")
        try:
            pointer_values = (float(pointer[0]), float(pointer[1]))
        except (TypeError, ValueError):
            raise TypeError("pointer must be a pair of numbers")
        return cls(
            forward=float(data.get("forward", 0.0)),
            right=float(data.get("right", 0.0)),
            up=float(data.get("up", 0.0)),
            look_yaw=float(data.get("look_yaw", 0.0)),
            look_pitch=float(data.get("look_pitch", 0.0)),
            pressed=frozenset(pressed),
            held=frozenset(held),
            pointer=pointer_values,
            mouse_clicked=bool(data.get("mouse_clicked", False)),
        )


class InputMap:
    """Maps keys and pointer motion to action names and continuous axes.

    Bindings are additive overlays on the defaults: a context map that omits
    a default key inherits it, so removed defaults reappear after a
    save/load round-trip. Schema-1 documents predate contexts and always
    load into the ``gameplay`` context.
    """

    def __init__(
        self,
        bindings: dict[str, str] | None = None,
        look_speed: float = 1.6,
        mouse_sensitivity: float = 0.0025,
        contexts: dict[str, dict[str, str]] | None = None,
        context: str = "gameplay",
    ) -> None:
        self.bindings = dict(DEFAULT_BINDINGS)
        if bindings:
            self.bindings.update(bindings)
        self.look_speed = look_speed
        self.mouse_sensitivity = mouse_sensitivity
        self.mouse_enabled = True
        self._held: frozenset[str] = frozenset()
        self._last_pointer: tuple[float, float] | None = None
        self._mouse_held = False
        self.contexts: dict[str, dict[str, str]] = {"gameplay": dict(self.bindings)}
        if contexts:
            for name, mapping in contexts.items():
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("context names must be non-blank strings")
                if not isinstance(mapping, dict):
                    raise TypeError("context bindings must be mappings")
                merged = dict(DEFAULT_BINDINGS)
                for action, key in mapping.items():
                    if not isinstance(action, str) or not isinstance(key, str):
                        raise TypeError("context bindings must map action names to key names")
                    merged[action] = key
                self.contexts[name] = merged
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-blank string")
        self.context = context
        if context in self.contexts:
            self.bindings = dict(self.contexts[context])
        else:
            self.contexts[context] = dict(self.bindings)

    def bind(self, action: str, key: str, context: str | None = None) -> None:
        if not isinstance(action, str) or not action.strip():
            raise ValueError("action name must be a non-blank string")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key name must be a non-blank string")
        target = context or self.context
        if not isinstance(target, str) or not target.strip():
            raise ValueError("context must be a non-blank string")
        if target not in self.contexts:
            self.contexts[target] = dict(self.bindings)
        self.contexts[target][action] = key
        if target == self.context:
            self.bindings[action] = key

    def set_context(self, context: str) -> None:
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-blank string")
        if context not in self.contexts:
            self.contexts[context] = dict(self.bindings)
        self.context = context
        self.bindings = dict(self.contexts[context])
        self._held = frozenset()

    def get_context(self) -> str:
        return self.context

    def list_contexts(self) -> list[str]:
        return sorted(self.contexts)

    def unbind(self, action: str) -> bool:
        """Remove a custom binding from the active context; returns False when not bound."""
        removed = self.bindings.pop(action, None) is not None
        context_map = self.contexts.get(self.context)
        if context_map is not None:
            context_map.pop(action, None)
        return removed

    def list_actions(self) -> dict[str, str]:
        """Return a copy of the current action-to-key map for UI and AI clients."""
        return dict(self.bindings)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": 2,
            "bindings": dict(self.bindings),
            "contexts": {name: dict(mapping) for name, mapping in self.contexts.items()},
            "context": self.context,
            "look_speed": self.look_speed,
            "mouse_sensitivity": self.mouse_sensitivity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> InputMap:
        if not isinstance(data, dict):
            raise TypeError("input bindings document must be a mapping")
        schema = data.get("schema", 1)
        if schema not in (1, 2):
            raise ValueError("unsupported input bindings schema")
        raw_bindings = data.get("bindings", {})
        if not isinstance(raw_bindings, dict):
            raise TypeError("input bindings must hold a bindings mapping")
        merged = dict(DEFAULT_BINDINGS)
        for action, key in raw_bindings.items():
            if not isinstance(action, str) or not isinstance(key, str):
                raise TypeError("input bindings must map action names to key names")
            merged[action] = key
        raw_contexts = data.get("contexts", {})
        if not isinstance(raw_contexts, dict):
            raise TypeError("input contexts must hold a mapping")
        context = str(data.get("context", "gameplay"))
        instance = cls(
            bindings=merged,
            look_speed=float(data.get("look_speed", 1.6)),
            mouse_sensitivity=float(data.get("mouse_sensitivity", 0.0025)),
            contexts={name: mapping for name, mapping in raw_contexts.items()} if raw_contexts else None,
            context=context if raw_contexts or "context" in data else "gameplay",
        )
        if schema == 1 and not raw_contexts:
            instance.contexts = {"gameplay": dict(instance.bindings)}
            instance.context = "gameplay"
        return instance

    def save_bindings(self, path: object) -> None:
        from keystone.serialization import write_json_atomic

        write_json_atomic(path, self.to_dict(), backup=False)

    @classmethod
    def load_bindings(cls, path: object) -> InputMap:
        import json
        from pathlib import Path

        try:
            payload = json.loads(Path(str(path)).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"could not read input bindings from {path}: {exc}") from exc
        return cls.from_dict(payload)

    def set_mouse_enabled(self, enabled: bool) -> None:
        self.mouse_enabled = enabled
        self._last_pointer = None

    def sample(self, context: GLContext, dt: float = 0.0) -> ActionState:
        held = frozenset(action for action, key in self.bindings.items() if context.key_down(key))
        pressed = held - self._held
        self._held = held
        mouse = context.mouse_down("left")
        clicked = mouse and not self._mouse_held
        self._mouse_held = mouse
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
            mouse_clicked=clicked,
        )
