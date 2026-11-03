"""Tests for the engine's sample game."""

import unittest

from keystone.samples import CubeDemo


class SampleTest(unittest.TestCase):
    def test_scene_contains_only_generic_renderables(self):
        game = CubeDemo()
        scene = game.build_scene()
        names = [node.name for node in scene.traverse()]
        self.assertIn("floor", names)
        self.assertGreaterEqual(sum(name.startswith("cube-") for name in names), 3)
        self.assertIn("orb", names)

    def test_update_rotates_cubes_and_moves_the_camera(self):
        game = CubeDemo()
        game.build_scene()
        cube = next(node for node in game.scene.traverse() if node.name == "cube-0")
        before = cube.transform.rotation
        camera_before = game.scene.camera.position

        class Actions:
            forward = 1.0
            right = 0.0
            up = 0.0
            look_yaw = 0.2
            look_pitch = 0.0

        game.update(0.5, Actions())
        self.assertNotEqual(cube.transform.rotation, before)
        self.assertNotEqual(game.scene.camera.position, camera_before)
        self.assertIn("time", game.snapshot())

    def test_actions_schema_is_generic(self):
        schema = CubeDemo().actions()
        self.assertIn("forward", schema["axes"])
        self.assertNotIn("combat", str(schema).lower())

    def test_rebuild_resets_time(self):
        from keystone.input import ActionState

        game = CubeDemo()
        game.build_scene()
        game.update(1.0, ActionState())
        self.assertNotEqual(game.snapshot()["time"], 0.0)
        game.build_scene()
        self.assertEqual(game.snapshot()["time"], 0.0)


if __name__ == "__main__":
    unittest.main()
