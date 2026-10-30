"""Tests for the fixed-step clock."""

import unittest

from keystone.clock import FixedStepClock


class FixedStepClockTest(unittest.TestCase):
    def test_releases_whole_steps_and_bounds_catch_up(self):
        clock = FixedStepClock(step=0.1, max_frame=0.25)
        self.assertEqual(clock.advance(0.0), [])
        self.assertEqual(clock.advance(0.05), [])
        self.assertEqual(clock.advance(0.15), [0.1])
        self.assertEqual(clock.advance(0.55), [0.1, 0.1, 0.1])

    def test_reset_drops_accumulator(self):
        clock = FixedStepClock(step=0.1)
        clock.advance(0.0)
        clock.advance(0.09)
        clock.reset(10.0)
        self.assertEqual(clock.advance(10.05), [])

    def test_invalid_configuration(self):
        with self.assertRaises(ValueError):
            FixedStepClock(step=0.0)
        with self.assertRaises(ValueError):
            FixedStepClock(step=0.2, max_frame=0.1)


if __name__ == "__main__":
    unittest.main()
