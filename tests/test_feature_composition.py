"""Composition tests across the features added in this delivery batch.

Each feature has focused tests; these check the seams a game actually crosses:
a camera rig driven by a staged route, and content-keyed instancing inside the
overlay pass.
"""

import json
import tempfile
import unittest
from pathlib import Path

from keystone.app import Engine
from keystone.camera_rig import CameraRig
from keystone.evidence import Checkpoint, Route, capture_route
from keystone.geometry import Material
from keystone.gpu.context import GLContext
from keystone.gpu.renderer import Renderer
from keystone.math3d import Vec3
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import OVERLAY_LAYER, Node, Scene, Transform


class CameraRigRouteTest(unittest.TestCase):
    def test_a_staged_route_keeps_the_rig_part_screen_anchored(self):
        engine = Engine(CubeDemo(), 160, 120, visible=False)
        try:
            rig = CameraRig(engine.scene.camera)
            rig.attach(
                "viewmodel",
                position=Vec3(0.0, 0.0, -1.0),
                mesh=cube(0.4),
                material=Material(color=Vec3(0.1, 0.1, 1.0), specular=0.0),
            )
            rig.attach_to(engine.scene)
            rig.sync()

            def stage(frame: int, _scene) -> None:
                if frame >= 2:
                    engine.scene.camera.move(1.5, 0.0, 0.0)
                    engine.scene.camera.rotate(0.2, 0.05)
                    rig.sync()

            route = Route(
                name="rig-route",
                frames=4,
                checkpoints=(Checkpoint(1, "before"), Checkpoint(4, "after")),
                stage=stage,
            )
            with tempfile.TemporaryDirectory() as directory:
                summary = capture_route(engine, route, Path(directory))
                samples = {sample["label"]: sample for sample in summary["checkpoints"]}
                before = _node(samples["before"], Path(directory), "viewmodel")
                after = _node(samples["after"], Path(directory), "viewmodel")
                self.assertEqual(before["layer"], OVERLAY_LAYER)
                self.assertEqual(after["layer"], OVERLAY_LAYER)
                self.assertIsNotNone(before["bbox"])
                self.assertIsNotNone(after["bbox"])
                self.assertLess(_center_shift(before["bbox"], after["bbox"]), 1.0)
                world_before = _node(samples["before"], Path(directory), "cube-0")
                world_after = _node(samples["after"], Path(directory), "cube-0")
                self.assertGreater(_center_shift(world_before["bbox"], world_after["bbox"]), 1.0)
        finally:
            engine.close()


class OverlayContentBatchTest(unittest.TestCase):
    def setUp(self):
        self.context = GLContext(64, 48, visible=False)
        self.addCleanup(self.context.close)
        self.renderer = Renderer(64, 48)
        self.addCleanup(self.renderer.release)

    def test_separately_built_overlay_copies_batch_in_the_overlay_pass(self):
        scene = Scene()
        for index, offset in enumerate((-0.3, 0.3)):
            scene.add(
                Node(
                    f"view-{index}",
                    transform=Transform(position=Vec3(offset, 0.0, -1.0)),
                    mesh=cube(0.25),
                    material=Material(),
                    layer=OVERLAY_LAYER,
                )
            )
        stats = self.renderer.render(scene)
        self.assertEqual(stats["overlay_nodes"], 2)
        self.assertEqual(stats["overlay_calls"], 1, "equal overlay payloads must share one draw")
        self.assertEqual(stats["draw_calls"], 0, "overlay must stay out of world draws")


def _node(sample: dict, directory: Path, name: str) -> dict:
    report = json.loads((directory / sample["report"]).read_text(encoding="utf-8"))
    for node in report["scene"]["nodes"]:
        if node["name"] == name:
            return node
    raise AssertionError(f"no node {name!r} in checkpoint {sample['label']!r}")


def _center_shift(first: list[float], second: list[float]) -> float:
    first_x = (first[0] + first[2]) * 0.5
    first_y = (first[1] + first[3]) * 0.5
    second_x = (second[0] + second[2]) * 0.5
    second_y = (second[1] + second[3]) * 0.5
    return ((second_x - first_x) ** 2 + (second_y - first_y) ** 2) ** 0.5


if __name__ == "__main__":
    unittest.main()
