"""Tests for the deterministic combat director."""

import unittest

from keystone.combat import ENEMY_TYPES, Combat, Enemy


def flat(x: float, z: float) -> bool:
    return True


class CombatTest(unittest.TestCase):
    def make(self, seed: int = 7) -> Combat:
        combat = Combat(seed)
        combat.spawn_around(0.0, 0.0, flat)
        return combat

    def test_spawn_is_seeded_and_deterministic(self):
        first = self.make()
        second = self.make()
        self.assertEqual(len(first.enemies), 3)
        self.assertEqual(first.snapshot(), second.snapshot())
        third = self.make(8)
        self.assertNotEqual(first.snapshot()["enemies"], third.snapshot()["enemies"])

    def test_auto_fire_kills_a_nearby_enemy(self):
        combat = self.make()
        target = combat.enemies[0]
        target.x, target.z, target.hp = 0.0, 0.0, 5.0
        combat.update(0.4, 0.0, 0.0, flat)
        self.assertEqual(combat.kills, 1)
        self.assertNotIn(target, combat.enemies)

    def test_contact_damages_the_player(self):
        combat = self.make()
        combat.enemies = [Enemy(ENEMY_TYPES["crawler"], 0.2, 0.0, 26.0, 26.0)]
        combat.update(1.0, 0.0, 0.0, flat)
        self.assertLess(combat.player_hp, combat.max_hp)

    def test_wave_five_spawns_a_boss(self):
        combat = self.make()
        combat.elapsed = 120.0
        combat.update(0.1, 0.0, 0.0, flat)
        self.assertEqual(combat.wave, 5)
        self.assertTrue(any(enemy.spec.boss for enemy in combat.enemies))

    def test_player_death_sets_the_flag(self):
        combat = self.make()
        combat.player_hp = 1.0
        combat.enemies = [Enemy(ENEMY_TYPES["crawler"], 0.2, 0.0, 26.0, 26.0)]
        combat.update(1.0, 0.0, 0.0, flat)
        self.assertTrue(combat.dead)
        self.assertEqual(combat.player_hp, 0.0)

    def test_snapshot_is_stable_after_the_same_steps(self):
        first = self.make()
        second = self.make()
        for _ in range(10):
            first.update(0.1, 0.0, 0.0, flat)
            second.update(0.1, 0.0, 0.0, flat)
        self.assertEqual(first.snapshot(), second.snapshot())


if __name__ == "__main__":
    unittest.main()
