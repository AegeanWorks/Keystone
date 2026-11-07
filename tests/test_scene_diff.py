"""Tests for structured scene snapshot diffs."""

import unittest

from keystone.math3d import Vec3
from keystone.scene import Node, Scene, Transform
from keystone.scene_diff import SCENE_DIFF_SCHEMA_VERSION, diff_scene_documents
from keystone.scene_snapshot import scene_to_dict


class SceneDiffTest(unittest.TestCase):
    def test_identical_documents_have_no_changes(self):
        scene = Scene()
        scene.add(Node("cube", id="cube"))
        document = scene_to_dict(scene)
        diff = diff_scene_documents(document, document)
        self.assertEqual(diff["schema"], SCENE_DIFF_SCHEMA_VERSION)
        self.assertFalse(diff["has_changes"])
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["removed"], [])
        self.assertEqual(diff["changed"], [])

    def test_reports_node_and_scene_changes(self):
        before_scene = Scene()
        before_scene.add(Node("a", id="a", tags={"old"}))
        before_scene.add(Node("b", id="b"))
        before_scene.camera.position = Vec3(0.0, 1.0, 5.0)
        before_scene.background = Vec3(0.05, 0.06, 0.08)

        after_scene = Scene()
        after_scene.add(
            Node(
                "a2",
                id="a",
                tags={"new"},
                transform=Transform(position=Vec3(1.0, 2.0, 3.0)),
            )
        )
        after_scene.add(Node("c", id="c"))
        after_scene.camera.position = Vec3(1.0, 2.0, 6.0)
        after_scene.background = Vec3(0.1, 0.2, 0.3)

        diff = diff_scene_documents(
            scene_to_dict(before_scene), scene_to_dict(after_scene)
        )
        self.assertTrue(diff["has_changes"])
        self.assertEqual(diff["added"], ["c"])
        self.assertEqual(diff["removed"], ["b"])
        self.assertEqual([item["id"] for item in diff["changed"]], ["a"])
        fields = diff["changed"][0]["fields"]
        self.assertIn("name", fields)
        self.assertIn("tags", fields)
        self.assertIn("transform", fields)
        self.assertIn("position", diff["camera"])
        self.assertIn("background", diff["environment"])
        self.assertTrue(diff["has_changes"])

    def test_rejects_bad_documents(self):
        with self.assertRaises(TypeError):
            diff_scene_documents([], {})
        with self.assertRaises(ValueError):
            diff_scene_documents({"nodes": [{"id": ""}]}, {"nodes": []})
        with self.assertRaises(ValueError):
            diff_scene_documents(
                {"nodes": [{"id": "a"}, {"id": "a"}]}, {"nodes": []}
            )


if __name__ == "__main__":
    unittest.main()
