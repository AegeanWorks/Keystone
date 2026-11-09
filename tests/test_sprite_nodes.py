"""Tests for placed sprite nodes: model, round trip and rendering."""

import unittest

from keystone.gpu.context import GLContext
from keystone.gpu.renderer import Renderer
from keystone.math3d import Vec3
from keystone.scene import DirectionalLight, Node, Scene, Sprite
from keystone.scene_snapshot import scene_from_dict, scene_to_dict


class SpriteModelTest(unittest.TestCase):
    def test_defaults_and_validation(self):
        sprite = Sprite()
        self.assertEqual(sprite.size, 1.0)
        self.assertEqual(sprite.alpha, 1.0)
        self.assertEqual(sprite.color, Vec3(1.0, 0.9, 0.7))

        for bad in (
            {"size": -1.0},
            {"alpha": 1.5},
            {"alpha": -0.1},
            {"size": "big"},
            {"alpha": True},
            {"color": Vec3(float("inf"), 0.0, 0.0)},
        ):
            with self.subTest(payload=bad), self.assertRaises((ValueError, TypeError)):
                Sprite(**bad)

    def test_node_rejects_a_non_sprite_payload(self):
        with self.assertRaises(TypeError):
            Node("bad", sprite="not a sprite")

    def test_node_without_a_sprite_still_works(self):
        node = Node("plain")
        self.assertIsNone(node.sprite)
        self.assertIsNone(node.material)


class SpriteSnapshotTest(unittest.TestCase):
    def test_sprite_round_trips(self):
        scene = Scene()
        node = scene.add(Node("glow", id="glow", sprite=Sprite(size=0.75, alpha=0.5)))
        document = scene_to_dict(scene)
        entry = next(n for n in document["nodes"] if n["id"] == "glow")
        self.assertEqual(entry["sprite"]["size"], 0.75)
        self.assertEqual(entry["sprite"]["alpha"], 0.5)

        restored = scene_from_dict(document)
        glow = restored.find_by_id("glow")
        self.assertEqual(glow.sprite, node.sprite)

    def test_document_is_stable_across_one_load(self):
        import json

        scene = Scene()
        scene.add(Node("glow", id="glow", sprite=Sprite(size=2.0)))
        first = scene_to_dict(scene)
        second = scene_to_dict(scene_from_dict(first))
        self.assertEqual(
            json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True)
        )

    def test_a_node_without_a_sprite_writes_null(self):
        scene = Scene()
        scene.add(Node("plain", id="plain"))
        entry = next(n for n in scene_to_dict(scene)["nodes"] if n["id"] == "plain")
        self.assertIsNone(entry["sprite"])


class SpriteRenderTest(unittest.TestCase):
    def setUp(self):
        self.context = GLContext(64, 48, visible=False)
        self.addCleanup(self.context.close)
        self.renderer = Renderer(64, 48)
        self.addCleanup(self.renderer.release)

    def _scene(self, sprite=None, visible=True):
        scene = Scene()
        scene.background = Vec3(0.0, 0.0, 0.0)
        scene.sky = Vec3(0.0, 0.0, 0.0)
        scene.ambient = Vec3(0.0, 0.0, 0.0)
        scene.light = DirectionalLight(intensity=0.0)
        scene.camera.position = Vec3(0.0, 0.0, 5.0)
        scene.camera.look_at(Vec3(0.0, 0.0, 0.0))
        if sprite is not None:
            node = scene.add(Node("glow", id="glow", sprite=sprite))
            node.visible = visible
        return scene

    def _render(self, scene):
        stats = self.renderer.render(scene)
        return bytes(self.renderer.read_pixels()), stats

    @staticmethod
    def _lit(pixels):
        count = 0
        for offset in range(0, len(pixels) - 3, 4):
            if pixels[offset] + pixels[offset + 1] + pixels[offset + 2] > 12:
                count += 1
        return count

    def test_sprite_draws_without_particles(self):
        empty, empty_stats = self._render(self._scene())
        drawn, drawn_stats = self._render(
            self._scene(Sprite(size=1.0, color=Vec3(1.0, 0.2, 0.2)))
        )
        self.assertEqual(empty_stats["sprites"], 0)
        self.assertEqual(drawn_stats["sprites"], 1)
        self.assertEqual(self._lit(empty), 0, "the sky must be black for this test")
        self.assertGreater(self._lit(drawn), 0)
        center = 24 * 64 * 4 + 32 * 4
        red, green, blue, alpha = drawn[center : center + 4]
        self.assertGreater(alpha, 0)
        self.assertGreater(red, green, "a red sprite must be red at its centre")
        self.assertGreater(red, blue)

    def test_sprite_colour_is_per_sprite(self):
        red, _ = self._render(self._scene(Sprite(size=1.0, color=Vec3(1.0, 0.0, 0.0))))
        green, _ = self._render(self._scene(Sprite(size=1.0, color=Vec3(0.0, 1.0, 0.0))))
        self.assertNotEqual(red, green, "the tint must not be shared across sprites")

    def test_hidden_or_transparent_sprites_draw_nothing(self):
        empty, _ = self._render(self._scene())
        zero_alpha, zero_stats = self._render(self._scene(Sprite(size=1.0, alpha=0.0)))
        hidden, hidden_stats = self._render(self._scene(Sprite(size=1.0), visible=False))
        self.assertEqual(zero_stats["sprites"], 0)
        self.assertEqual(hidden_stats["sprites"], 0)
        self.assertEqual(zero_alpha, empty)
        self.assertEqual(hidden, empty)

    def test_size_scales_the_covered_area(self):
        small, _ = self._render(self._scene(Sprite(size=0.4, color=Vec3(1, 1, 1))))
        large, _ = self._render(self._scene(Sprite(size=2.0, color=Vec3(1, 1, 1))))
        self.assertGreater(
            self._lit(large), self._lit(small), "a larger sprite must cover more pixels"
        )
