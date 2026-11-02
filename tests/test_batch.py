"""Tests for the static batch planner and inspector endpoint."""

import json
import threading
import unittest
import urllib.request

from keystone.batch import plan_batches
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.primitives import cube
from keystone.samples import CubeDemo
from keystone.scene import Node, Scene
from keystone.web.server import create_server


class BatchTest(unittest.TestCase):
    def test_shared_meshes_batch_into_few_groups(self):
        scene = Scene()
        mesh = cube(1.0)
        material = Material(color=Vec3(1.0, 0.0, 0.0))
        for index in range(4):
            scene.add(Node(f"box-{index}", id=f"box-{index}", mesh=mesh, material=material))
        plan = plan_batches(scene)
        self.assertEqual(plan["schema"], 1)
        self.assertEqual(plan["draw_calls"], 4)
        self.assertEqual(plan["batched_calls"], 1)
        self.assertEqual(plan["saved_calls"], 3)

    def test_cube_demo_plan_reports_savings(self):
        plan = plan_batches(CubeDemo().build_scene())
        self.assertGreaterEqual(plan["draw_calls"], 5)
        self.assertLessEqual(plan["batched_calls"], plan["draw_calls"])
        self.assertEqual(plan["triangles"], sum(item["triangles"] for item in plan["batches"]))


class InspectorEndpointTest(unittest.TestCase):
    def test_inspector_returns_batches_and_audio(self):
        server = create_server(CubeDemo(), host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}/api/inspector"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(payload["game"], "cube-demo")
        self.assertIn("batches", payload)
        self.assertIn("draw_calls", payload["batches"])
        self.assertIn("merged", payload)
        self.assertIn("assets", payload)
        self.assertGreater(payload["assets"]["total"], 0)
        self.assertIn("particles", payload)


if __name__ == "__main__":
    unittest.main()
