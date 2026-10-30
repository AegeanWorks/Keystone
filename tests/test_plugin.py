"""Tests for the GameModule contract and loader."""

import unittest

from keystone.plugin import GameModule, load_game
from keystone.samples import CubeDemo


class PluginTest(unittest.TestCase):
    def test_sample_loads_and_implements_the_contract(self):
        game = load_game("keystone.samples:CubeDemo")
        self.assertIsInstance(game, CubeDemo)
        self.assertIsInstance(game, GameModule)
        self.assertEqual(game.name, "cube-demo")

    def test_invalid_specs_are_rejected(self):
        for spec in ("keystone.samples", "missing.module:Factory", "keystone.samples:Missing"):
            with self.assertRaises(ValueError):
                load_game(spec)

    def test_missing_methods_are_rejected(self):
        with self.assertRaises(TypeError):
            load_game("tests.test_plugin:IncompleteGame")


class IncompleteGame:
    name = "incomplete"

    def build_scene(self):
        return None


if __name__ == "__main__":
    unittest.main()
