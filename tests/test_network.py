"""Tests for the seeded cyber network and alert state."""

import unittest

from keystone.procedural.dungeon import DungeonGenerator
from keystone.procedural.network import Network


class NetworkTest(unittest.TestCase):
    def setUp(self):
        self.dungeon = DungeonGenerator(width=33, height=21).generate(42)
        self.network = Network.generate(7, self.dungeon)

    def test_generates_reachable_terminals_outside_spawn_and_exit(self):
        self.assertEqual(len(self.network.terminals), 4)
        for terminal in self.network.terminals:
            self.assertTrue(self.dungeon.is_walkable(int(terminal.x), int(terminal.z)))
            self.assertNotEqual((int(terminal.x), int(terminal.z)), self.dungeon.spawn)
            self.assertNotEqual((int(terminal.x), int(terminal.z)), self.dungeon.exit)

    def test_same_seed_is_deterministic(self):
        again = Network.generate(7, self.dungeon)
        self.assertEqual(self.network.snapshot(), again.snapshot())
        self.assertNotEqual(self.network.snapshot(), Network.generate(8, self.dungeon).snapshot())

    def test_hacking_needs_four_steps_and_raises_alert(self):
        terminal = self.network.terminals[0]
        for _ in range(3):
            self.network.hack(terminal.terminal_id)
        self.assertTrue(0.0 < terminal.progress < 1.0)
        self.assertFalse(terminal.hacked)
        self.network.hack(terminal.terminal_id)
        self.assertTrue(terminal.hacked)
        self.assertEqual(self.network.hacked_count, 1)
        self.assertGreater(self.network.alert, 0.0)
        self.assertEqual(self.network.version, 4)

    def test_alert_decays_over_time(self):
        self.network.hack(self.network.terminals[0].terminal_id)
        before = self.network.alert
        self.network.update(1.0)
        self.assertLess(self.network.alert, before)

    def test_complete_network(self):
        for terminal in self.network.terminals:
            while not terminal.hacked:
                self.network.hack(terminal.terminal_id)
        self.assertTrue(self.network.complete)
        self.assertEqual(self.network.hacked_count, len(self.network.terminals))

    def test_links_reference_known_terminals(self):
        known = {terminal.terminal_id for terminal in self.network.terminals}
        self.assertGreaterEqual(len(self.network.links), 3)
        for first, second in self.network.links:
            self.assertIn(first, known)
            self.assertIn(second, known)

    def test_unknown_terminal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.network.hack("node-99")

    def test_near_terminal_uses_radius(self):
        terminal = self.network.terminals[0]
        self.assertIs(self.network.near_terminal(terminal.x, terminal.z), terminal)
        self.assertIsNone(self.network.near_terminal(terminal.x + 10.0, terminal.z))


if __name__ == "__main__":
    unittest.main()
