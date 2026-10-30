"""Tests for the GameModule contract and loader."""

import unittest

from keystone.plugin import GameModule, describe_game, load_game
from keystone.samples import CubeDemo


class PluginTest(unittest.TestCase):
    def test_sample_loads_and_implements_the_contract(self):
        game = load_game("keystone.samples:CubeDemo")
        self.assertIsInstance(game, CubeDemo)
        self.assertIsInstance(game, GameModule)
        self.assertEqual(game.name, "cube-demo")

    def test_describe_exposes_capabilities_actions_and_snapshot(self):
        payload = describe_game(CubeDemo())
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(payload["game"], "cube-demo")
        self.assertTrue(payload["capabilities"]["simulate"])
        self.assertTrue(payload["capabilities"]["human_ui"]["overlay"])
        self.assertIn("resume", payload["capabilities"]["human_ui"]["menu"])
        self.assertFalse(payload["capabilities"]["game_ui"])
        self.assertEqual(payload["capabilities"]["report_schema"]["version"], 2)
        self.assertIn("axes", payload["actions"])
        self.assertIn("time", payload["snapshot"])

    def test_describe_reports_a_game_ui_hook(self):
        class HudGame(CubeDemo):
            def draw_ui(self, canvas, _state):
                canvas.rect(0, 0, 4, 4, (1.0, 1.0, 1.0, 1.0))

        self.assertTrue(describe_game(HudGame())["capabilities"]["game_ui"])

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
