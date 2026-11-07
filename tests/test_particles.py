"""Tests for the deterministic particle core."""

import unittest

from keystone.math3d import Vec3
from keystone.particles import (
    POINT_SKIN,
    Emitter,
    Particle,
    ParticleSystem,
    particles_report,
)


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

    def test_step_rejects_non_finite_dt(self):
        system = ParticleSystem()
        system.add(Emitter(name="sparks", seed=5))
        system.burst("sparks", 1)
        with self.assertRaises(ValueError):
            system.step(float("nan"))
        with self.assertRaises(ValueError):
            system.step(float("inf"))
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


class ResponseTest(unittest.TestCase):
    def _still_system(self) -> ParticleSystem:
        system = ParticleSystem()
        system.add(Emitter(name="still", speed=0.0, gravity=Vec3(0.0, 0.0, 0.0), lifetime=10.0, seed=4))
        return system

    def test_defaults_stop_dead_with_clean_zero(self):
        from keystone.physics import AABB

        system = self._still_system()
        system.burst("still", 1)
        system.particles[0] = Particle(Vec3(-3, 0, 0), Vec3(60, 0, 0), 0.0, 10.0, 1.0, 0, "still")
        wall = AABB(Vec3(0, 0, 0), Vec3(0.5, 5, 5))
        system.step(1.0, [wall])
        stopped = system.particles[0]
        self.assertEqual(stopped.velocity.x, 0.0)
        self.assertEqual(repr(stopped.velocity.x), "0.0")

    def test_bounce_reflects_with_restitution(self):
        from keystone.physics import AABB

        system = self._still_system()
        system.burst("still", 1)
        system.particles[0] = Particle(Vec3(0, 3, 0), Vec3(0, -10, 0), 0.0, 10.0, 1.0, 0, "still")
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        system.step(0.5, [floor], restitution=0.5)
        bounced = system.particles[0]
        self.assertAlmostEqual(bounced.position.y, 0.5, places=6)
        self.assertEqual(bounced.velocity.y, 5.0)

    def test_elastic_bounce_preserves_speed(self):
        from keystone.physics import AABB

        system = self._still_system()
        system.burst("still", 1)
        system.particles[0] = Particle(Vec3(0, 3, 0), Vec3(0, -10, 0), 0.0, 10.0, 1.0, 0, "still")
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        system.step(0.5, [floor], restitution=1.0)
        self.assertEqual(system.particles[0].velocity.y, 10.0)

    def test_rest_threshold_settles_micro_bounces(self):
        from keystone.physics import AABB

        system = self._still_system()
        system.burst("still", 1)
        system.particles[0] = Particle(Vec3(0, 0.54, 0), Vec3(0, -0.08, 0), 0.0, 10.0, 1.0, 0, "still")
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        system.step(0.5, [floor], restitution=0.5)
        settled = system.particles[0]
        self.assertEqual(settled.velocity.y, 0.0)
        self.assertEqual(repr(settled.velocity.y), "0.0")

    def test_friction_scales_tangentials_on_hit_only(self):
        from keystone.physics import AABB

        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))

        def run(mu: float, boxes: list) -> Particle:
            system = self._still_system()
            system.burst("still", 1)
            system.particles[0] = Particle(Vec3(0, 3, 0), Vec3(6, -8, 0), 0.0, 10.0, 1.0, 0, "still")
            system.step(0.5, boxes, friction=mu)
            return system.particles[0]

        hit = run(0.25, [floor])
        self.assertAlmostEqual(hit.position.y, 0.5)
        self.assertEqual(hit.velocity.x, 4.5)
        self.assertEqual(hit.velocity.y, 0.0)
        self.assertEqual(hit.velocity.z, 0.0)
        missed = run(0.25, [])
        plain = run(0.0, [])
        self.assertEqual(
            (missed.velocity.x, missed.velocity.y, missed.velocity.z),
            (plain.velocity.x, plain.velocity.y, plain.velocity.z),
        )

    def test_kill_on_contact_drops_the_particle(self):
        from keystone.physics import AABB

        system = self._still_system()
        system.burst("still", 1)
        system.particles[0] = Particle(Vec3(0, 3, 0), Vec3(0, -10, 0), 0.0, 10.0, 1.0, 0, "still")
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        self.assertEqual(system.step(0.5, [floor], kill_on_contact=True), 0)
        system.burst("still", 1)
        system.particles[0] = Particle(Vec3(0, 3, 0), Vec3(0, -10, 0), 0.0, 10.0, 1.0, 0, "still")
        self.assertEqual(system.step(0.5, [floor]), 1)

    def test_response_rejects_bad_parameters(self):
        from keystone.physics import AABB

        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        for kwargs in (
            {"restitution": 1.5},
            {"restitution": -0.1},
            {"restitution": float("nan")},
            {"friction": 1.5},
            {"friction": -0.1},
            {"friction": float("nan")},
        ):
            system = self._still_system()
            system.burst("still", 1)
            with self.assertRaises(ValueError):
                system.step(1 / 60, [floor], **kwargs)
        system = self._still_system()
        system.burst("still", 1)
        with self.assertRaises(ValueError):
            system.step(1 / 60, [], restitution=2.0)

    def test_response_is_deterministic(self):
        from keystone.physics import AABB

        def run() -> ParticleSystem:
            system = ParticleSystem()
            system.add(Emitter(name="hail", speed=0.0, gravity=Vec3(0.0, -10.0, 0.0), seed=9))
            system.burst("hail", 6)
            floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
            for _ in range(90):
                system.step(1 / 60, [floor], restitution=0.45, friction=0.1)
            return system

        first, second = run(), run()
        self.assertEqual(
            [(p.position.x, p.position.y, p.velocity.x, p.velocity.y) for p in first.particles],
            [(p.position.x, p.position.y, p.velocity.x, p.velocity.y) for p in second.particles],
        )

    def test_cube_demo_fountain_bounces_deterministically(self):
        from keystone.samples import CubeDemo

        class Actions:
            forward = 0.0
            right = 0.0
            up = 0.0
            look_yaw = 0.0
            look_pitch = 0.0

        first, second = CubeDemo(), CubeDemo()
        first.build_scene()
        second.build_scene()
        for _ in range(120):
            first.update(1 / 60, Actions())
            second.update(1 / 60, Actions())
        self.assertEqual(len(first.particles.particles), len(second.particles.particles))
        self.assertEqual(
            [(p.position.x, p.position.y, p.position.z) for p in first.particles.particles],
            [(p.position.x, p.position.y, p.position.z) for p in second.particles.particles],
        )
        self.assertNotIn("particles", first.snapshot())
        self.assertEqual(first.snapshot(), second.snapshot())


    def test_deep_interior_spawn_ejects_through_near_face(self):
        from keystone.physics import AABB

        system = self._still_system()
        system.burst("still", 1)
        system.particles[0] = Particle(Vec3(0, 0, 0), Vec3(0, -1, 0), 0.0, 10.0, 1.0, 0, "still")
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        system.step(0.5, [floor])
        pushed = system.particles[0]
        self.assertAlmostEqual(pushed.position.y, 0.5)
        self.assertEqual(pushed.velocity.y, 0.0)

    def test_stationary_deep_particle_depenetrates_on_step(self):
        from keystone.physics import AABB

        system = ParticleSystem()
        system.add(Emitter(name="still", speed=0.0, gravity=Vec3(0.0, 0.0, 0.0), seed=1))
        system.burst("still", 1)
        system.particles[0] = Particle(Vec3(0, 0, 0), Vec3(), 0.0, 10.0, 1.0, 0, "still")
        box = AABB(Vec3(0, 0, 0), Vec3(5, 5, 5))
        system.step(1 / 60, [box])
        pushed = system.particles[0]
        self.assertFalse(box.contains(pushed.position))

    def test_speed_is_velocity_magnitude(self):
        emitter = Emitter(direction=Vec3(3, 4, 0), speed=1.0, spread=0.0, seed=1)
        self.assertAlmostEqual(emitter.spawn(0).velocity.length(), 1.0)
        emitter = Emitter(direction=Vec3(0, 1, 0), speed=2.0, spread=0.5, seed=1)
        for index in range(20):
            self.assertAlmostEqual(emitter.spawn(index).velocity.length(), 2.0, places=6)

    def test_deep_interior_motion_ejects_through_nearest_face(self):
        from keystone.physics import AABB

        system = self._still_system()
        system.burst("still", 1)
        box = AABB(Vec3(0, 0, 0), Vec3(5, 5, 5))
        system.particles[0] = Particle(Vec3(4.4, 0, 0), Vec3(10, 0, 0), 0.0, 10.0, 1.0, 0, "still")
        system.step(0.1, [box])
        pushed = system.particles[0]
        self.assertGreater(pushed.position.x, 5.0)
        self.assertLess(pushed.position.x, 5.001)

    def test_particle_fields_reject_non_finite_values(self):
        with self.assertRaises(ValueError):
            Particle(lifetime=float("nan"))
        with self.assertRaises(ValueError):
            Particle(age=float("inf"))
        with self.assertRaises(ValueError):
            Particle(position=Vec3(float("nan"), 0.0, 0.0))
        with self.assertRaises(ValueError):
            Emitter(rate=float("nan"))
        with self.assertRaises(ValueError):
            Emitter(lifetime=float("inf"))
        with self.assertRaises(ValueError):
            Emitter(gravity=Vec3(float("nan"), 0.0, 0.0))
        with self.assertRaises(ValueError):
            ParticleSystem(max_particles=2.5)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            ParticleSystem(time=float("nan"))

    def test_emitter_from_dict_rejects_malformed_payloads(self):
        for payload in (
            {"direction": [1.0, 2.0]},
            {"direction": None},
            {"direction": "123"},
            {"name": None},
            {"seed": 3.7},
            {"rate": "10"},
            {"gravity": [0.0, float("nan"), 0.0]},
        ):
            with self.assertRaises((TypeError, ValueError), msg=repr(payload)):
                Emitter.from_dict(payload)

    def test_spawn_rejects_non_vec3_origin_and_system_rejects_bad_emitters(self):
        emitter = Emitter()
        with self.assertRaises(TypeError):
            emitter.spawn(0, (0.0, 1.0, 2.0))  # type: ignore[arg-type]
        with self.assertRaises((TypeError, ValueError)):
            ParticleSystem(emitters={"bad": object()})  # type: ignore[dict-item]
        with self.assertRaises(ValueError):
            ParticleSystem(emitters={"other": Emitter(name="e")})

    def test_step_rejects_time_overflow(self):
        system = ParticleSystem()
        system.add(Emitter(name="e"))
        system.step(1e308)
        with self.assertRaises(ValueError):
            system.step(1e308)


class SlideTest(unittest.TestCase):
    def test_sliding_along_face_preserves_tangential_motion(self):
        from keystone.physics import AABB

        system = ParticleSystem()
        system.add(Emitter(name="slide", speed=0.0, gravity=Vec3(0.0, 0.0, 0.0), lifetime=10.0, seed=6))
        system.burst("slide", 1)
        system.particles[0] = Particle(
            Vec3(0, 0.5 + POINT_SKIN, 0), Vec3(2.0, -0.01, 1.0), 0.0, 10.0, 1.0, 0, "slide"
        )
        floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
        system.step(1 / 60, [floor])
        slid = system.particles[0]
        self.assertAlmostEqual(slid.position.x, 2.0 / 60, places=9)
        self.assertAlmostEqual(slid.position.z, 1.0 / 60, places=9)
        self.assertAlmostEqual(slid.position.y, 0.5)
        self.assertEqual((slid.velocity.x, slid.velocity.y, slid.velocity.z), (2.0, 0.0, 1.0))

    def test_sliding_is_deterministic(self):
        from keystone.physics import AABB

        def run() -> Particle:
            system = ParticleSystem()
            system.add(Emitter(name="slide", speed=0.0, gravity=Vec3(0.0, -2.0, 0.0), lifetime=10.0, seed=6))
            system.burst("slide", 1)
            system.particles[0] = Particle(
                Vec3(0, 0.5 + POINT_SKIN, 0), Vec3(2.0, -0.01, 1.0), 0.0, 10.0, 1.0, 0, "slide"
            )
            floor = AABB(Vec3(0, 0, 0), Vec3(5, 0.5, 5))
            for _ in range(30):
                system.step(1 / 60, [floor], restitution=0.45, friction=0.1)
            return system.particles[0]

        first, second = run(), run()
        self.assertEqual(
            (first.position.x, first.position.y, first.position.z),
            (second.position.x, second.position.y, second.position.z),
        )
        self.assertGreater(first.position.x, 0.2)


if __name__ == "__main__":
    unittest.main()
