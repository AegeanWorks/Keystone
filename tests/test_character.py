"""Tests for the AABB character controller."""

import unittest

from keystone.character import CharacterBody, CharacterController
from keystone.math3d import Vec3
from keystone.physics import AABB


class CharacterControllerTest(unittest.TestCase):
    def test_body_exposes_its_collision_box(self):
        body = CharacterBody(Vec3(1, 2, 3), Vec3(0.4, 0.9, 0.4))
        self.assertEqual(body.box(), AABB(Vec3(1, 2, 3), Vec3(0.4, 0.9, 0.4)))

    def test_character_falls_and_rests_on_a_floor(self):
        controller = CharacterController(gravity=24.0)
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        body = CharacterBody(Vec3(0, 3, 0), Vec3(0.35, 0.9, 0.35))
        for _ in range(180):
            body = controller.step(body, Vec3(), 1 / 60, [floor])
        self.assertTrue(body.on_ground)
        self.assertAlmostEqual(body.position.y, 0.5 + 0.9 + controller.skin, places=3)
        self.assertAlmostEqual(body.velocity.y, 0.0)

    def test_character_stops_at_a_wall_without_tunneling(self):
        controller = CharacterController(gravity=24.0)
        wall = AABB(Vec3(0, 1.4, 0), Vec3(0.2, 0.9, 3))
        body = CharacterBody(Vec3(-3, 1.4, 0), Vec3(0.4, 0.9, 0.4))
        body = controller.step(body, Vec3(5, 0, 0), 1.0, [wall])
        self.assertLessEqual(body.position.x, -0.2 - 0.4 - controller.skin + 1e-9)
        self.assertAlmostEqual(body.velocity.x, 0.0)

    def test_jump_leaves_the_ground(self):
        controller = CharacterController(gravity=24.0)
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        body = CharacterBody(
            Vec3(0, 0.5 + 0.9 + controller.skin, 0),
            Vec3(0.35, 0.9, 0.35),
            Vec3(0, 6, 0),
            True,
        )
        body = controller.step(body, Vec3(), 1 / 60, [floor])
        self.assertFalse(body.on_ground)
        self.assertGreater(body.position.y, 0.5 + 0.9)
        self.assertGreater(body.velocity.y, 0.0)

    def test_character_rejects_invalid_configuration_and_step(self):
        with self.assertRaises(ValueError):
            CharacterController(gravity=-1.0)
        with self.assertRaises(ValueError):
            CharacterController(skin=-0.1)
        with self.assertRaises(ValueError):
            CharacterController(slope_rise=-0.1)
        with self.assertRaises(ValueError):
            CharacterController(slope_run=0.0)
        with self.assertRaises(ValueError):
            CharacterController(step_height=-0.1)
        with self.assertRaises(ValueError):
            CharacterBody(Vec3(), Vec3(-1, 1, 1))
        controller = CharacterController()
        with self.assertRaises(ValueError):
            controller.step(CharacterBody(Vec3()), Vec3(), 0.0, [])

    def test_character_steps_onto_a_low_step(self):
        controller = CharacterController(gravity=24.0)
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        step = AABB(Vec3(2.0, 0.65, 0), Vec3(0.5, 0.15, 1.0))
        body = CharacterBody(Vec3(0, 0.5 + 0.9 + controller.skin, 0), Vec3(0.35, 0.9, 0.35))
        climbed = False
        for _ in range(120):
            body = controller.step(body, Vec3(2, 0, 0), 1 / 60, [floor, step])
            if body.position.y > 0.5 + 0.9 + 0.2:
                climbed = True
                break
        self.assertTrue(climbed)
        self.assertAlmostEqual(body.position.y, 0.8 + 0.9, delta=0.05)

    def test_character_stops_at_a_tall_step(self):
        controller = CharacterController(gravity=24.0)
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        wall = AABB(Vec3(2.0, 1.4, 0), Vec3(0.5, 0.9, 1.0))
        body = CharacterBody(Vec3(0, 0.5 + 0.9 + controller.skin, 0), Vec3(0.35, 0.9, 0.35))
        for _ in range(120):
            body = controller.step(body, Vec3(2, 0, 0), 1 / 60, [floor, wall])
        self.assertLess(body.position.x, 2.0 - 0.5 - 0.35)

    def test_platform_carry_pushes_out_of_a_wall(self):
        controller = CharacterController(gravity=0.0)
        wall = AABB(Vec3(0, 1.4, 0), Vec3(0.2, 0.9, 3))
        body = CharacterBody(Vec3(-3, 1.4, 0), Vec3(0.4, 0.9, 0.4))
        carried = controller.step(body, Vec3(), 1.0, [wall], platform_velocity=Vec3(5, 0, 0))
        self.assertLessEqual(carried.position.x, -0.2 - 0.4 - controller.skin + 1e-9)

    def test_platform_carry_off_a_ledge_then_falls(self):
        controller = CharacterController(gravity=24.0)
        floor = AABB(Vec3(0, 0, 0), Vec3(1.0, 0.5, 1.0))
        body = CharacterBody(Vec3(0, 0.5 + 0.9 + controller.skin, 0), Vec3(0.35, 0.9, 0.35), Vec3(), True)
        for _ in range(20):
            body = controller.step(body, Vec3(), 1 / 60, [floor], platform_velocity=Vec3(5, 0, 0))
        self.assertGreater(body.position.x, 1.0)
        start_y = body.position.y
        for _ in range(30):
            body = controller.step(body, Vec3(), 1 / 60, [floor])
        self.assertLess(body.position.y, start_y)
        self.assertFalse(body.on_ground)

    def test_character_steps_are_deterministic(self):
        controller = CharacterController(gravity=24.0)
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        step = AABB(Vec3(2.0, 0.65, 0), Vec3(0.5, 0.15, 1.0))

        def run() -> CharacterBody:
            body = CharacterBody(Vec3(0, 0.5 + 0.9 + controller.skin, 0), Vec3(0.35, 0.9, 0.35))
            for _ in range(60):
                body = controller.step(body, Vec3(2, 0, 0), 1 / 60, [floor, step])
            return body

        first, second = run(), run()
        self.assertEqual(first.position, second.position)
        self.assertEqual(first.velocity, second.velocity)
        self.assertEqual(first.on_ground, second.on_ground)


if __name__ == "__main__":
    unittest.main()
