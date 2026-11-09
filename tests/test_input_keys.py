"""Tests for the real GL key table exposed to InputMap consumers."""

import unittest

import glfw

from keystone.gpu.context import _KEYS, key_names


class KeyTableTest(unittest.TestCase):
    def test_number_row_is_bindable_for_slot_actions(self):
        for digit in "0123456789":
            self.assertIn(digit, _KEYS)
        self.assertEqual(_KEYS["1"], glfw.KEY_1)
        self.assertEqual(_KEYS["9"], glfw.KEY_9)

    def test_key_names_exposes_the_same_table(self):
        self.assertEqual(key_names(), tuple(_KEYS))
        self.assertIn("space", key_names())

    def test_no_two_names_share_one_glfw_code(self):
        self.assertEqual(len(_KEYS), len(set(_KEYS.values())))
