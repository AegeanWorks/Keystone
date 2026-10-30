"""Tests for input sampling and action state."""

import unittest

from keystone.input import ActionState, InputMap


class FakeContext:
    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.pointer = (0.0, 0.0)

    def key_down(self, key: str) -> bool:
        return key in self.keys

    def cursor_position(self) -> tuple[float, float]:
        return self.pointer


class InputMapTest(unittest.TestCase):
    def test_axes_and_pressed_edges(self):
        context = FakeContext()
        context.keys = {"w", "d"}
        mapping = InputMap()
        state = mapping.sample(context, 0.1)
        self.assertEqual((state.forward, state.right, state.up), (1.0, 1.0, 0.0))
        self.assertIn("forward", state.pressed)
        second = mapping.sample(context, 0.1)
        self.assertEqual(second.pressed, frozenset())

    def test_custom_binding(self):
        context = FakeContext()
        context.keys = {"i"}
        mapping = InputMap({"forward": "i"})
        self.assertEqual(mapping.sample(context).forward, 1.0)

    def test_mouse_delta_feeds_look(self):
        context = FakeContext()
        mapping = InputMap()
        mapping.sample(context)
        context.pointer = (10.0, -5.0)
        state = mapping.sample(context)
        self.assertGreater(state.look_yaw, 0.0)
        self.assertGreater(state.look_pitch, 0.0)

    def test_disabled_mouse_ignores_pointer(self):
        context = FakeContext()
        mapping = InputMap()
        mapping.set_mouse_enabled(False)
        mapping.sample(context)
        context.pointer = (10.0, 10.0)
        state = mapping.sample(context)
        self.assertEqual((state.look_yaw, state.look_pitch), (0.0, 0.0))

    def test_action_state_round_trip_and_clear(self):
        state = ActionState(forward=1.0, pressed=frozenset({"jump"}), held=frozenset({"jump"}))
        restored = ActionState.from_dict(state.to_dict())
        self.assertEqual(restored, state)
        self.assertEqual(restored.without_pressed().pressed, frozenset())


if __name__ == "__main__":
    unittest.main()
