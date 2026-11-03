"""Tests for the deterministic particle core."""

import unittest

from keystone.math3d import Vec3
from keystone.particles import Emitter, Particle, ParticleSystem, particles_report


class EmitterTest(unittest.TestCase):
    def test_spawn_is_deterministic(self):
        emitter = Emitter(name="sparks")
        first = emitter.spawn(3)
        second = emitter.spawn(3)
        self.assertEqual(first.position, second.position)
        self.assertEqual(first.velocity, second.velocity)
        self.assertNotEqual(emitter.spawn(3).velocity, emitter.spawn(4).velocity)

    def test_validation(self):
        with self.assertRaises(ValueError):
            Emitter(name="  ")
        with self.assertRaises(ValueError):
            Emitter(name="x", rate=-1.0)
        with self.assertRaises(ValueError):
            Particle(age=-0.1)
        with self.assertRaises(ValueError):
            Particle(lifetime=0.0)

    def test_json_round_trip(self):
        emitter = Emitter(name="puff", rate=24.0, seed=11)
        restored = Emitter.from_dict(emitter.to_dict())
        self.assertEqual(restored.name, "puff")
        self.assertEqual(restored.rate, 24.0)
        self.assertEqual(restored.seed, 11)
        self.assertEqual(restored.spawn(1).position, emitter.spawn(1).position)


class SystemTest(unittest.TestCase):
    def _system(self) -> ParticleSystem:
        system = ParticleSystem()
        system.add(Emitter(name="sparks", rate=60.0, lifetime=1.0, speed=0.0, seed=5))
        return system

    def test_burst_step_and_cull_are_deterministic(self):
        first, second = self._system(), self._system()
        for system in (first, second):
            system.burst("sparks", 8)
            system.step(0.5)
        self.assertEqual(first.alive_count(), second.alive_count())
        self.assertEqual(
            [(p.position.x, p.position.y) for p in first.particles],
            [(p.position.x, p.position.y) for p in second.particles],
        )
        first.step(5.0)
        self.assertEqual(first.alive_count(), 0)

    def test_gravity_and_drag_move_particles(self):
        system = ParticleSystem()
        system.add(Emitter(name="rain", speed=0.0, gravity=Vec3(0.0, -10.0, 0.0), seed=9))
        system.burst("rain", 2)
        before = [p.position.y for p in system.particles]
        system.step(0.25)
        after = [p.position.y for p in system.particles]
        self.assertTrue(all(b < a for a, b in zip(before, after)))

    def test_max_particles_keeps_newest(self):
        system = ParticleSystem(max_particles=4)
        system.add(Emitter(name="s", speed=0.0, seed=1))
        system.burst("s", 6)
        self.assertEqual(system.alive_count(), 4)

    def test_errors(self):
        system = self._system()
        with self.assertRaises(ValueError):
            system.step(-0.1)
        with self.assertRaises(ValueError):
            system.burst("sparks", -1)
        with self.assertRaises(KeyError):
            system.burst("missing", 1)

    def test_multi_emitter_systems_use_per_emitter_forces(self):
        system = ParticleSystem()
        system.add(Emitter(name="float", speed=0.0, gravity=Vec3(0.0, 0.0, 0.0), seed=1))
        system.add(Emitter(name="fall", speed=0.0, gravity=Vec3(0.0, -10.0, 0.0), seed=2))
        system.burst("float", 1)
        system.burst("fall", 1)
        system.step(0.5)
        positions = {p.emitter: p.position.y for p in system.particles}
        self.assertAlmostEqual(positions["float"], 0.0)
        self.assertLess(positions["fall"], 0.0)

    def test_report(self):
        system = self._system()
        system.burst("sparks", 3)
        report = particles_report(system)
        self.assertEqual(report["schema"], 1)
        self.assertEqual(report["alive"], 3)
        self.assertEqual(report["emitters"], ["sparks"])

    def test_particle_rests_on_a_floor(self):
        from keystone.physics import AABB

        system = ParticleSystem()
        system.add(Emitter(name="rain", speed=0.0, gravity=Vec3(0.0, -10.0, 0.0), lifetime=5.0, seed=9))
        system.burst("rain", 1, origin=Vec3(0, 3, 0))
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        for _ in range(120):
            system.step(1 / 60, [floor])
        self.assertEqual(system.alive_count(), 1)
        resting = system.particles[0]
        self.assertAlmostEqual(resting.position.y, 0.5, places=6)
        self.assertAlmostEqual(resting.velocity.y, 0.0, places=9)

    def test_particle_stops_at_a_wall_without_tunneling(self):
        from keystone.physics import AABB

        system = ParticleSystem()
        system.add(Emitter(name="shot", speed=0.0, gravity=Vec3(0.0, 0.0, 0.0), seed=3))
        system.burst("shot", 1)
        system.particles[0] = Particle(Vec3(-3, 0, 0), Vec3(60, 0, 0), 0.0, 10.0, 1.0, 0, "shot")
        wall = AABB(Vec3(0, 0, 0), Vec3(0.5, 5, 5))
        system.step(1.0, [wall])
        stopped = system.particles[0]
        self.assertLessEqual(stopped.position.x, -0.5)
        self.assertAlmostEqual(stopped.velocity.x, 0.0, places=9)
        self.assertAlmostEqual(stopped.velocity.y, 0.0, places=9)

    def test_empty_colliders_match_legacy_path(self):
        from keystone.physics import AABB

        first, second = self._system(), self._system()
        for system in (first, second):
            system.burst("sparks", 8)
        first.step(0.5)
        second.step(0.5, [])
        self.assertEqual(
            [(p.position.x, p.position.y) for p in first.particles],
            [(p.position.x, p.position.y) for p in second.particles],
        )
        floor = AABB(Vec3(0, -10, 0), Vec3(5, 0.5, 5))
        first.step(0.5)
        second.step(0.5, [floor])
        self.assertEqual(
            [(p.position.x, p.position.y) for p in first.particles],
            [(p.position.x, p.position.y) for p in second.particles],
        )

    def test_collision_is_deterministic(self):
        from keystone.physics import AABB

        def run() -> ParticleSystem:
            system = ParticleSystem()
            system.add(Emitter(name="rain", speed=0.0, gravity=Vec3(0.0, -10.0, 0.0), seed=9))
            system.burst("rain", 4)
            floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
            for _ in range(60):
                system.step(1 / 60, [floor])
            return system

        first, second = run(), run()
        self.assertEqual(
            [(p.position.x, p.position.y) for p in first.particles],
            [(p.position.x, p.position.y) for p in second.particles],
        )

    def test_collision_rejects_bad_colliders(self):
        system = self._system()
        system.burst("sparks", 1)
        with self.assertRaises(TypeError):
            system.step(1 / 60, ["not-a-box"])


if __name__ == "__main__":
    unittest.main()
