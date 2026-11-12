"""Tests for animation states that drive a 2D blend space."""

import json
import unittest

from keystone import AnimationState, AnimationStateMachine, AnimationTransition
from keystone.animation import AnimationClip, Track
from keystone.animation_blend import (
    BlendSample,
    BlendSample2D,
    BlendSpace1D,
    BlendSpace2D,
)
from keystone.math3d import Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _clip(name: str, x: float) -> AnimationClip:
    return AnimationClip(
        name=name,
        position_tracks=(("node", Track(times=(0.0, 1.0), values=(Vec3(x, 0.0, 0.0), Vec3(x, 1.0, 0.0)))),),
    )


def _grid() -> BlendSpace2D:
    return BlendSpace2D(
        (
            BlendSample2D(_clip("bl", 0.0), 0.0, 0.0),
            BlendSample2D(_clip("br", 10.0), 1.0, 0.0),
            BlendSample2D(_clip("tl", 20.0), 0.0, 1.0),
            BlendSample2D(_clip("tr", 30.0), 1.0, 1.0),
        )
    )


class StateBlend2DTest(unittest.TestCase):
    def test_a_state_samples_two_parameters(self):
        machine = AnimationStateMachine(
            [
                AnimationState(
                    "locomotion",
                    _clip("base", 0.0),
                    blend_space2d=_grid(),
                    blend_parameters=("speed", "strafe"),
                )
            ],
            [],
            {"speed": 0.5, "strafe": 0.5},
        )
        pose = machine.advance(0.0)
        self.assertEqual(pose["node"].position, Vec3(15.0, 0.0, 0.0))

    def test_parameter_changes_move_the_pose(self):
        machine = AnimationStateMachine(
            [
                AnimationState(
                    "locomotion",
                    _clip("base", 0.0),
                    blend_space2d=_grid(),
                    blend_parameters=("speed", "strafe"),
                )
            ],
            [],
            {"speed": 0.0, "strafe": 0.0},
        )
        self.assertEqual(machine.advance(0.0)["node"].position.x, 0.0)
        machine.set_parameter("speed", 1.0)
        self.assertEqual(machine.advance(0.0)["node"].position.x, 10.0)
        machine.set_parameter("strafe", 1.0)
        self.assertEqual(machine.advance(0.0)["node"].position.x, 30.0)

    def test_transitions_still_work_with_a_2d_state(self):
        machine = AnimationStateMachine(
            [
                AnimationState(
                    "locomotion",
                    _clip("base", 0.0),
                    blend_space2d=_grid(),
                    blend_parameters=("speed", "strafe"),
                ),
                AnimationState("idle", _clip("idle", 5.0)),
            ],
            [AnimationTransition("locomotion", "idle", "stopped", "trigger", 0.0, 0.0)],
            {"speed": 0.0, "strafe": 0.0},
        )
        self.assertEqual(machine.advance(0.0)["node"].position.x, 0.0)
        machine.set_trigger("stopped")
        self.assertEqual(machine.advance(0.0)["node"].position.x, 5.0)

    def test_only_one_space_kind_is_allowed(self):
        with self.assertRaises(ValueError):
            AnimationState(
                "mixed",
                _clip("base", 0.0),
                blend_space2d=_grid(),
                blend_space=BlendSpace1D((BlendSample(_clip("base", 0.0), 0.0),)),
            )

    def test_blend_parameters_are_validated(self):
        with self.assertRaises(ValueError):
            AnimationState("x", _clip("base", 0.0), blend_space2d=_grid(), blend_parameters=("speed",))
        with self.assertRaises(ValueError):
            AnimationState("x", _clip("base", 0.0), blend_space2d=_grid(), blend_parameters=("speed", " "))
        with self.assertRaises(TypeError):
            AnimationState("x", _clip("base", 0.0), blend_space2d=_grid(), blend_parameters="speed")
        with self.assertRaises(TypeError):
            AnimationState("x", _clip("base", 0.0), blend_space2d=object())

    def test_state_documents_round_trip(self):
        state = AnimationState(
            "locomotion",
            _clip("base", 0.0),
            blend_space2d=_grid(),
            blend_parameters=("speed", "strafe"),
        )
        document = state.to_dict()
        self.assertEqual(document["blend_space2d"]["schema"], 1)
        self.assertEqual(document["blend_parameters"], ["speed", "strafe"])
        self.assertEqual(json.loads(json.dumps(document)), document)
        restored = AnimationState.from_dict(document)
        self.assertEqual(restored.blend_parameters, ("speed", "strafe"))
        machine = AnimationStateMachine([restored], [], {"speed": 0.5, "strafe": 0.5})
        self.assertEqual(machine.advance(0.0)["node"].position.x, 15.0)

    def test_documents_reject_both_spaces(self):
        document = {
            "name": "mixed",
            "clip": _clip("base", 0.0).to_dict(),
            "blend_space2d": _grid().to_dict(),
            "blend_space": {"schema": 1, "samples": [{"clip": _clip("base", 0.0).to_dict(), "threshold": 0.0}]},
        }
        with self.assertRaises(ValueError):
            AnimationState.from_dict(document)

    def test_report_exposes_the_2d_space(self):
        machine = AnimationStateMachine(
            [
                AnimationState(
                    "locomotion",
                    _clip("base", 0.0),
                    blend_space2d=_grid(),
                    blend_parameters=("speed", "strafe"),
                )
            ],
            [],
            {"speed": 0.5, "strafe": 0.5},
        )
        machine.advance(0.0)
        report = machine.report()
        self.assertEqual(report["blend_space2d"]["schema"], 1)
        self.assertEqual(report["blend_space2d"]["xs"], [0.0, 1.0])
        self.assertEqual(report["blend_parameters"], ["speed", "strafe"])
        self.assertIsNone(report["blend_space"])

    def test_describe_advertises_state_blending(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["animation_state_blend_2d"])


if __name__ == "__main__":
    unittest.main()
