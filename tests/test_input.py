"""Tests for input sampling and action state."""

import unittest

from keystone.input import ActionState, InputMap


class FakeContext:
    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.pointer = (0.0, 0.0)
        self.mouse = False

    def key_down(self, key: str) -> bool:
        return key in self.keys

    def cursor_position(self) -> tuple[float, float]:
        return self.pointer

    def mouse_down(self, button: str = "left") -> bool:
        return self.mouse


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

    def test_mouse_click_is_a_single_frame_edge(self):
        context = FakeContext()
        mapping = InputMap()
        self.assertFalse(mapping.sample(context).mouse_clicked)
        context.mouse = True
        self.assertTrue(mapping.sample(context).mouse_clicked)
        self.assertFalse(mapping.sample(context).mouse_clicked)
        context.mouse = False
        mapping.sample(context)
        context.mouse = True
        self.assertTrue(mapping.sample(context).mouse_clicked)

    def test_contexts_isolate_menu_and_gameplay(self):
        mapping = InputMap()
        mapping.bind("confirm", "enter", context="menu")
        mapping.bind("confirm", "space", context="gameplay")
        mapping.set_context("menu")
        self.assertEqual(mapping.bindings["confirm"], "enter")
        mapping.set_context("gameplay")
        self.assertEqual(mapping.bindings["confirm"], "space")
        self.assertIn("menu", mapping.list_contexts())
        restored = InputMap.from_dict(mapping.to_dict())
        self.assertEqual(restored.bindings["confirm"], "space")
        restored.set_context("menu")
        self.assertEqual(restored.bindings["confirm"], "enter")
        legacy = InputMap.from_dict({"bindings": {"forward": "i"}})
        self.assertEqual(legacy.bindings["forward"], "i")

    def test_unbind_survives_context_round_trip(self):
        mapping = InputMap()
        mapping.bind("dash", "left_shift")
        mapping.set_context("menu")
        mapping.set_context("gameplay")
        self.assertTrue(mapping.unbind("dash"))
        self.assertNotIn("dash", mapping.bindings)
        mapping.set_context("menu")
        mapping.set_context("gameplay")
        self.assertNotIn("dash", mapping.bindings)
        restored = InputMap.from_dict(mapping.to_dict())
        restored.set_context("menu")
        restored.set_context("gameplay")
        self.assertNotIn("dash", restored.bindings)

    def test_action_state_round_trip_and_clear(self):
        state = ActionState(
            forward=1.0,
            pressed=frozenset({"jump"}),
            held=frozenset({"jump"}),
            mouse_clicked=True,
        )
        restored = ActionState.from_dict(state.to_dict())
        self.assertEqual(restored, state)
        cleared = restored.without_pressed()
        self.assertEqual(cleared.pressed, frozenset())
        self.assertFalse(cleared.mouse_clicked)


if __name__ == "__main__":
    unittest.main()
