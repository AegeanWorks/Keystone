"""Tests for deterministic parameter-driven animation state machines."""

import json
import math
import unittest

from keystone import (
    AnimationState,
    AnimationStateMachine,
    AnimationTransition,
)
from keystone.animation import AnimationClip, Track
from keystone.animation_blend import BlendSample, BlendSpace1D
from keystone.math3d import Vec3


def _clip(name, offset=0.0, events=()):
    return AnimationClip(
        name=name,
        position_tracks=(
            (
                "node",
                Track(
                    times=(0.0, 1.0),
                    values=(
                        Vec3(offset, 0.0, 0.0),
                        Vec3(offset + 1.0, 0.0, 0.0),
                    ),
                ),
            ),
        ),
        events=tuple(events),
    )


def _machine(duration=0.0):
    idle = AnimationState("idle", _clip("idle", 0.0))
    run = AnimationState("run", _clip("run", 10.0), speed=2.0)
    transition = AnimationTransition(
        "idle", "run", "speed", "greater", 0.5, duration
    )
    return AnimationStateMachine(
        [idle, run], [transition], {"speed": 0.0}
    )


class AnimationStateMachineTest(unittest.TestCase):
    def test_parameter_transition_and_state_settings(self):
        machine = _machine()
        pose = machine.advance(0.25)
        self.assertEqual(machine.current, "idle")
        self.assertAlmostEqual(pose["node"].position.x, 0.25)

        machine.set_parameter("speed", 1.0)
        machine.advance(0.0)
        self.assertEqual(machine.current, "run")
        self.assertEqual(machine.controller.current, "run")
        self.assertEqual(machine.controller.speed, 2.0)
        pose = machine.advance(0.25)
        self.assertAlmostEqual(pose["node"].position.x, 10.5)

    def test_trigger_transition_and_events(self):
        idle = AnimationState("idle", _clip("idle"))
        jump = AnimationState(
            "jump", _clip("jump", 5.0, events=((0.0, "land"),))
        )
        transition = AnimationTransition(
            "idle", "jump", "jump", "trigger", duration=0.0
        )
        machine = AnimationStateMachine(
            [idle, jump], [transition], {"jump": False}
        )
        machine.set_trigger("jump")
        machine.advance(0.1)
        self.assertEqual(machine.current, "jump")
        self.assertFalse(machine.parameters["jump"])
        self.assertEqual(machine.take_events(), ["land"])
        self.assertEqual(machine.take_events(), [])

    def test_states_with_same_clip_name_keep_distinct_payloads(self):
        first = AnimationClip(
            name="shared",
            position_tracks=(
                (
                    "node",
                    Track(times=(0.0,), values=(Vec3(0.0, 0.0, 0.0),)),
                ),
            ),
        )
        second = AnimationClip(
            name="shared",
            position_tracks=(
                (
                    "node",
                    Track(times=(0.0,), values=(Vec3(10.0, 0.0, 0.0),)),
                ),
            ),
        )
        machine = AnimationStateMachine(
            [AnimationState("a", first), AnimationState("b", second)],
            [AnimationTransition("a", "b", "go", "trigger", duration=0.0)],
            {"go": False},
        )
        pose = machine.advance(0.0)
        self.assertAlmostEqual(pose["node"].position.x, 0.0)
        machine.set_trigger("go")
        pose = machine.advance(0.0)
        self.assertAlmostEqual(pose["node"].position.x, 10.0)
        self.assertEqual(machine.report()["clip"], "shared")

    def test_zero_speed_target_still_completes_crossfade(self):
        idle = AnimationState("idle", _clip("idle"))
        frozen = AnimationState("frozen", _clip("frozen"), speed=0.0)
        machine = AnimationStateMachine(
            [idle, frozen],
            [
                AnimationTransition(
                    "idle", "frozen", "go", "trigger", duration=1.0
                )
            ],
            {"go": False},
        )
        machine.set_trigger("go")
        machine.advance(0.5)
        self.assertTrue(machine.controller.blending)
        machine.advance(0.5)
        self.assertFalse(machine.controller.blending)

    def test_crossfade_blending_finishes(self):
        machine = _machine(duration=1.0)
        machine.set_parameter("speed", 1.0)
        machine.advance(0.25)
        self.assertTrue(machine.controller.blending)
        machine.advance(0.75)
        self.assertFalse(machine.controller.blending)

    def test_serialization_round_trip_and_report(self):
        machine = _machine()
        machine.set_parameter("speed", 0.25)
        document = machine.to_dict()
        json.dumps(document)
        restored = AnimationStateMachine.from_dict(document)
        self.assertEqual(restored.to_dict(), document)
        self.assertEqual(restored.report()["current"], "idle")
        self.assertEqual(
            restored.report()["parameters"], {"speed": 0.25}
        )
        self.assertEqual(restored.report()["states"], ["idle", "run"])
        self.assertEqual(restored.report()["transitions"], 1)

    def test_blend_space_state_samples_parameter_and_round_trips(self):
        walk = _clip("walk", 0.0)
        run = _clip("run", 10.0)
        space = BlendSpace1D(
            (BlendSample(walk, 0.0), BlendSample(run, 10.0))
        )
        state = AnimationState(
            "locomotion",
            walk,
            blend_space=space,
            blend_parameter="speed",
        )
        machine = AnimationStateMachine([state], parameters={"speed": 5.0})
        pose = machine.advance(0.0)
        self.assertEqual(pose["node"].position, Vec3(5.0, 0.0, 0.0))
        machine.set_parameter("speed", 10.0)
        pose = machine.advance(0.0)
        self.assertEqual(pose["node"].position, Vec3(10.0, 0.0, 0.0))

        document = machine.to_dict()
        self.assertIn("blend_space", document["states"][0])
        restored = AnimationStateMachine.from_dict(document)
        report = restored.report()
        self.assertEqual(report["blend_parameter"], "speed")
        self.assertEqual(report["blend_space"]["thresholds"], [0.0, 10.0])
        self.assertEqual(restored.advance(0.0)["node"].position, Vec3(10.0, 0.0, 0.0))

        without_clip = state.to_dict()
        without_clip.pop("clip")
        rebuilt = AnimationState.from_dict(without_clip)
        self.assertEqual(rebuilt.clip.name, "walk")

    def test_validation_rejects_bad_shapes(self):
        idle = AnimationState("idle", _clip("idle"))
        with self.assertRaises(ValueError):
            AnimationStateMachine([])
        with self.assertRaises(ValueError):
            AnimationStateMachine(
                [idle, AnimationState("idle", _clip("other"))]
            )
        with self.assertRaises(ValueError):
            AnimationStateMachine([idle], current="missing")
        with self.assertRaises(ValueError):
            AnimationStateMachine(
                [idle], [AnimationTransition("idle", "missing", "speed")]
            )
        with self.assertRaises(ValueError):
            AnimationStateMachine(
                [idle], [AnimationTransition("idle", "idle", "speed")]
            )
        with self.assertRaises(TypeError):
            AnimationStateMachine([idle], parameters=[])
        with self.assertRaises(ValueError):
            AnimationTransition("idle", "run", "speed", operator="bad")
        with self.assertRaises(ValueError):
            AnimationTransition("idle", "run", "speed", duration=-1.0)
        with self.assertRaises(ValueError):
            AnimationState("bad", _clip("x"), speed=-1.0)
        with self.assertRaises(TypeError):
            AnimationState("bad", object())
        with self.assertRaises(TypeError):
            AnimationState("bad", _clip("x"), loop=1)
        with self.assertRaises(ValueError):
            AnimationStateMachine.from_dict({"schema": True, "states": []})
        with self.assertRaises(ValueError):
            AnimationStateMachine.from_dict(
                {"schema": 2, "states": [idle.to_dict()]}
            )
        with self.assertRaises(ValueError):
            AnimationStateMachine.from_dict(
                {"schema": 1, "states": [idle.to_dict()], "unknown": 1}
            )
        with self.assertRaises(ValueError):
            AnimationStateMachine.from_dict(
                {"schema": 1, "states": []}
            )

    def test_available_transitions_and_play_errors(self):
        machine = _machine()
        self.assertEqual(machine.available_transitions(), ())
        machine.set_parameter("speed", 1.0)
        self.assertEqual(len(machine.available_transitions()), 1)
        machine.play("run")
        self.assertEqual(machine.current, "run")
        with self.assertRaises(KeyError):
            machine.play("missing")
        with self.assertRaises(ValueError):
            machine.set_parameter("bad", math.nan)
        with self.assertRaises(ValueError):
            machine.advance(-0.1)
        with self.assertRaises(ValueError):
            machine.advance(math.inf)

    def test_parameter_can_be_added_after_construction(self):
        machine = _machine()
        machine.set_parameter("moving", True)
        self.assertTrue(machine.parameters["moving"])
        machine.set_parameter("moving", False)
        self.assertFalse(machine.parameters["moving"])


if __name__ == "__main__":
    unittest.main()
