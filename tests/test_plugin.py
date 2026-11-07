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
        self.assertTrue(payload["capabilities"]["shadows"])
        self.assertTrue(payload["capabilities"]["srgb"])
        self.assertTrue(payload["capabilities"]["post"])
        self.assertTrue(payload["capabilities"]["bloom"])
        self.assertTrue(payload["capabilities"]["sprites"])
        self.assertTrue(payload["capabilities"]["skin"])
        self.assertTrue(payload["capabilities"]["prefabs"])
        self.assertEqual(payload["capabilities"]["report_schema"]["version"], 11)
        self.assertEqual(payload["capabilities"]["web"]["api_version"], 1)
        self.assertIn("/api/scene", payload["capabilities"]["web"]["endpoints"])
        self.assertEqual(payload["capabilities"]["editor"]["schema"], 14)
        self.assertIn("create_node", payload["capabilities"]["editor"]["actions"])
        self.assertIn("undo", payload["capabilities"]["editor"]["actions"])
        self.assertIn("/api/editor", payload["capabilities"]["web"]["endpoints"])
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
        for spec in (None, 7, b"keystone.samples:CubeDemo"):
            with self.assertRaises(ValueError):
                load_game(spec)

    def test_loader_rejects_multi_colon_and_noncallable_factory(self):
        with self.assertRaises(ValueError):
            load_game("keystone.samples:CubeDemo:extra")
        with self.assertRaises(TypeError) as ctx:
            load_game("keystone.samples:__name__")
        self.assertIn("keystone.samples:__name__", str(ctx.exception))

    def test_missing_methods_are_rejected(self):
        with self.assertRaises(TypeError):
            load_game("tests.test_plugin:IncompleteGame")

    def test_public_api_exports_texture_data(self):
        import keystone

        self.assertIn("TextureData", keystone.__all__)
        self.assertIs(keystone.TextureData, __import__("keystone.texture", fromlist=["TextureData"]).TextureData)

    def test_loader_rejects_missing_or_non_string_name(self):
        for spec in ("tests.test_plugin:NoNameGame", "tests.test_plugin:BadNameGame"):
            with self.assertRaises(ValueError) as caught:
                load_game(spec)
            self.assertIn("name", str(caught.exception))

    def test_describe_lists_health_and_index_endpoints(self):
        endpoints = describe_game(CubeDemo())["capabilities"]["web"]["endpoints"]
        self.assertIn("/api", endpoints)
        self.assertIn("/api/health", endpoints)


class IncompleteGame:
    name = "incomplete"

    def build_scene(self):
        return None


class NoNameGame:
    def build_scene(self):
        return None

    def update(self, dt, actions):
        return None

    def snapshot(self):
        return {}

    def actions(self):
        return {}

    def status(self):
        return "no-name"


class BadNameGame(NoNameGame):
    name = object()


if __name__ == "__main__":
    unittest.main()
