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


class SpriteReachTest(unittest.TestCase):
    """A sprite must survive every path that carries scene content."""

    def test_sprite_to_dict_round_trips(self):
        sprite = Sprite(size=0.75, color=Vec3(0.1, 0.2, 0.3), alpha=0.5)
        self.assertEqual(Sprite.from_dict(sprite.to_dict()), sprite)

    def test_sprite_from_dict_rejects_bad_documents(self):
        for bad in (
            "nope",
            [],
            {"color": [1.0, 0.0]},
            {"color": "red"},
            {"size": "big"},
        ):
            with self.subTest(payload=bad), self.assertRaises((TypeError, ValueError)):
                Sprite.from_dict(bad)

    def test_prefab_document_and_instance_carry_the_sprite(self):
        from keystone.prefab import Prefab

        scene = Scene()
        root = scene.add(Node("glow", id="glow", sprite=Sprite(size=0.5)))
        prefab = Prefab.from_node(root, name="glow")

        document = prefab.to_dict()
        self.assertIsNotNone(document["roots"][0]["sprite"])

        target = Scene()
        created = prefab.instantiate(target)
        self.assertIsNotNone(
            created[0].sprite, "instantiating a prefab must keep its sprite"
        )
        self.assertEqual(created[0].sprite.size, 0.5)

    def test_prefab_round_trip_through_json_keeps_the_sprite(self):
        import json

        from keystone.prefab import Prefab

        scene = Scene()
        root = scene.add(Node("glow", id="glow", sprite=Sprite(size=1.25, alpha=0.25)))
        prefab = Prefab.from_node(root, name="glow")
        reloaded = Prefab.from_dict(json.loads(json.dumps(prefab.to_dict())))
        target = Scene()
        created = reloaded.instantiate(target)
        self.assertEqual(created[0].sprite.size, 1.25)
        self.assertEqual(created[0].sprite.alpha, 0.25)

    def test_editor_exposes_and_sets_a_sprite(self):
        from keystone.samples import CubeDemo
        from keystone.web.server import GameSession

        session = GameSession(CubeDemo())
        created = session.editor_action({"action": "create_node", "name": "glow"})
        node_id = next(n["id"] for n in created["nodes"] if n["name"] == "glow")
        node = next(n for n in created["nodes"] if n["id"] == node_id)
        self.assertIn("sprite", node, "the editor must report the sprite field")
        self.assertIsNone(node["sprite"])

        result = session.editor_action(
            {
                "action": "set_node",
                "id": node_id,
                "sprite": {"size": 0.5, "color": [1.0, 0.0, 0.0], "alpha": 0.8},
            }
        )
        updated = next(n for n in result["nodes"] if n["id"] == node_id)
        self.assertEqual(updated["sprite"]["size"], 0.5)
        self.assertEqual(updated["sprite"]["alpha"], 0.8)

        # A partial payload updates only the named field.
        partial = session.editor_action(
            {"action": "set_node", "id": node_id, "sprite": {"alpha": 0.25}}
        )
        merged = next(n for n in partial["nodes"] if n["id"] == node_id)
        self.assertEqual(merged["sprite"]["size"], 0.5, "size must be preserved")
        self.assertEqual(merged["sprite"]["alpha"], 0.25)

        cleared = session.editor_action(
            {"action": "set_node", "id": node_id, "sprite": None}
        )
        gone = next(n for n in cleared["nodes"] if n["id"] == node_id)
        self.assertIsNone(gone["sprite"])

    def test_editor_rejects_a_malformed_sprite(self):
        from keystone.samples import CubeDemo
        from keystone.web.server import GameSession, WebProblem

        session = GameSession(CubeDemo())
        created = session.editor_action({"action": "create_node", "name": "glow"})
        node_id = next(n["id"] for n in created["nodes"] if n["name"] == "glow")
        for bad in ("nope", {"size": -1.0}, {"unknown": 1}, {"color": [1.0]}):
            with self.subTest(payload=bad), self.assertRaises((WebProblem, ValueError, TypeError)):
                session.editor_action(
                    {"action": "set_node", "id": node_id, "sprite": bad}
                )

    def test_undo_restores_the_previous_sprite(self):
        from keystone.samples import CubeDemo
        from keystone.web.server import GameSession

        session = GameSession(CubeDemo())
        created = session.editor_action({"action": "create_node", "name": "glow"})
        node_id = next(n["id"] for n in created["nodes"] if n["name"] == "glow")
        session.editor_action(
            {"action": "set_node", "id": node_id, "sprite": {"size": 1.0}}
        )
        undone = session.editor_action({"action": "undo"})
        node = next(n for n in undone["nodes"] if n["id"] == node_id)
        self.assertIsNone(node["sprite"], "undo must drop the sprite it added")


class SpriteDiscoveryTest(unittest.TestCase):
    """An AI can only use a feature it can find in the schema."""

    def test_describe_advertises_sprite_nodes_and_point_lights(self):
        from keystone.gpu.renderer import MAX_POINT_LIGHTS
        from keystone.plugin import describe_game
        from keystone.samples import CubeDemo

        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities.get("sprite_nodes"), "sprite nodes must be advertised")
        self.assertEqual(capabilities.get("point_lights"), MAX_POINT_LIGHTS)

    def test_every_carrier_document_lists_sprite_in_its_schema(self):
        from keystone.web.schema import EDITOR_SCHEMA, SCENE_SCHEMA

        self.assertIn("sprite", EDITOR_SCHEMA["fields"]["node"])
        self.assertIn("sprite", EDITOR_SCHEMA["fields"]["set_node"])
        self.assertIn("sprite", SCENE_SCHEMA["fields"]["node"])

    def test_scene_export_emits_the_sprite_it_promises(self):
        from keystone.web.scene import scene_document

        scene = Scene()
        scene.add(Node("glow", id="glow", sprite=Sprite(size=0.5)))
        entry = next(
            node for node in scene_document(scene)["nodes"] if node["id"] == "glow"
        )
        self.assertEqual(entry["sprite"]["size"], 0.5)

    def test_editor_document_reports_the_sprite_field(self):
        from keystone.samples import CubeDemo
        from keystone.web.server import GameSession

        session = GameSession(CubeDemo())
        created = session.editor_action({"action": "create_node", "name": "probe"})
        node = next(n for n in created["nodes"] if n["name"] == "probe")
        self.assertIn("sprite", node)


class SpriteReportTest(unittest.TestCase):
    """A sprite draws pixels, so the frame report must place it on screen."""

    def _report_entry(self, sprite, width=96, height=64):
        from keystone.analysis import _node_report

        scene = Scene()
        scene.camera.position = Vec3(0.0, 0.0, 5.0)
        scene.camera.look_at(Vec3(0.0, 0.0, 0.0))
        scene.add(Node("beacon", id="beacon", sprite=sprite))
        return next(
            entry
            for entry in _node_report(scene, width, height)
            if entry["id"] == "beacon"
        )

    def test_sprite_only_node_reports_a_bbox(self):
        entry = self._report_entry(Sprite(size=1.0))
        self.assertIsNotNone(
            entry["bbox"], "a sprite that draws pixels must not report bbox=None"
        )
        min_x, min_y, max_x, max_y = entry["bbox"]
        self.assertGreater(max_x - min_x, 1.0)
        self.assertGreater(max_y - min_y, 1.0)
        # The quad is square at this orientation, so the box is roughly square.
        self.assertAlmostEqual(max_x - min_x, max_y - min_y, delta=2.0)

    def test_sprite_bbox_grows_with_size(self):
        small = self._report_entry(Sprite(size=0.5))["bbox"]
        large = self._report_entry(Sprite(size=2.0))["bbox"]
        self.assertGreater(large[2] - large[0], small[2] - small[0])

    def test_report_carries_the_sprite_description(self):
        entry = self._report_entry(Sprite(size=0.75, alpha=0.5))
        sprite = entry["sprite"]
        self.assertEqual(sprite["size"], 0.75)
        self.assertEqual(sprite["alpha"], 0.5)
        self.assertEqual(len(sprite["color"]), 3)

    def test_a_mesh_node_still_uses_its_mesh_bounds(self):
        from keystone.primitives import cube

        scene = Scene()
        scene.camera.position = Vec3(0.0, 0.0, 5.0)
        scene.camera.look_at(Vec3(0.0, 0.0, 0.0))
        scene.add(Node("box", id="box", mesh=cube(1.5), sprite=Sprite(size=4.0)))
        from keystone.analysis import _node_report

        entry = next(e for e in _node_report(scene, 96, 64) if e["id"] == "box")
        # Mesh takes precedence, so the oversized sprite does not inflate the box.
        self.assertLess(entry["bbox"][2] - entry["bbox"][0], 60.0)


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
