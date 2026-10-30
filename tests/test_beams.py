"""Tests for the deterministic light-lock puzzle."""

import unittest

from keystone.beams import GREEN, RED, LightLock, mask_to_rgb


class LightLockTest(unittest.TestCase):
    def test_initial_state_is_unsolved(self):
        for seed in range(8):
            self.assertFalse(LightLock(seed).solved)

    def test_solution_routes_red_through_green_dye_to_the_receiver(self):
        lock = LightLock(7)
        lock.set_orientation(-1, 0, "\\")
        lock.set_orientation(-1, 2, "/")
        self.assertTrue(lock.solved)
        segments = lock.trace()
        self.assertGreater(len(segments), 0)
        self.assertTrue(any(segment.mask == (RED | GREEN) for segment in segments))

    def test_wrong_orientation_stays_sealed(self):
        lock = LightLock(7)
        lock.set_orientation(-1, 0, "/")
        lock.set_orientation(-1, 2, "/")
        self.assertFalse(lock.solved)

    def test_trace_terminates_on_a_cycle(self):
        lock = LightLock(7)
        lock.set_orientation(-1, 0, "/")
        lock.set_orientation(-1, 2, "\\")
        segments = lock.trace()
        self.assertLessEqual(len(segments), 128)

    def test_rotate_toggles_orientation_and_version(self):
        lock = LightLock(7)
        before = lock.mirrors[(-1, 0)]
        version = lock.version
        lock.rotate(-1, 0)
        self.assertNotEqual(lock.mirrors[(-1, 0)], before)
        self.assertEqual(lock.version, version + 1)

    def test_nearest_mirror_uses_world_distance(self):
        lock = LightLock(7, origin=(10.0, 5.0))
        self.assertEqual(lock.nearest_mirror(9.0, 5.0), (-1, 0))
        self.assertIsNone(lock.nearest_mirror(50.0, 50.0))

    def test_snapshot_is_stable(self):
        first = LightLock(7)
        second = LightLock(7)
        self.assertEqual(first.snapshot(), second.snapshot())

    def test_mask_to_rgb(self):
        self.assertEqual(mask_to_rgb(RED | GREEN), (1.0, 1.0, 0.05))
        self.assertEqual(mask_to_rgb(GREEN), (0.05, 1.0, 0.05))


if __name__ == "__main__":
    unittest.main()
