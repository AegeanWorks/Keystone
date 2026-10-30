"""Tests for the machine-readable frame report."""

import tempfile
import unittest
from pathlib import Path

from keystone.analysis import analyze_frame, write_report
from keystone.math3d import Vec3
from keystone.png import write_png
from keystone.samples import CubeDemo


class AnalysisTest(unittest.TestCase):
    def test_pixel_stats_and_content_bbox(self):
        game = CubeDemo()
        scene = game.build_scene()
        scene.background = Vec3(0.0, 0.0, 0.0)
        pixels = bytes(
            (
                0, 0, 0, 255,
                255, 0, 0, 255,
                0, 0, 0, 255,
                0, 0, 0, 255,
            )
        )
        report = analyze_frame(scene, pixels, 2, 2)
        stats = report["stats"]
        self.assertEqual(stats["content_pixels"], 1)
        self.assertEqual(stats["content_bbox"], [1, 1, 1, 1])
        self.assertEqual(stats["dominant_colors"][0]["pixels"], 3)
        self.assertGreater(stats["mean_luma"], 0.0)
        self.assertEqual(len(stats["grid_luma"]), 8)

    def test_scene_nodes_have_projected_screen_bounds(self):
        game = CubeDemo()
        scene = game.build_scene()
        scene.camera.position = Vec3(0.0, 0.0, 5.0)
        scene.camera.yaw = 0.0
        scene.camera.pitch = 0.0
        pixels = bytes((0, 0, 0, 255)) * (64 * 48)
        report = analyze_frame(scene, pixels, 64, 48)
        cube = next(node for node in report["scene"]["nodes"] if node["name"] == "cube-0")
        self.assertIsNotNone(cube["screen"])
        self.assertIsNotNone(cube["bbox"])
        self.assertGreater(cube["triangles"], 0)
        self.assertIn("hash", report)

    def test_png_hash_and_atomic_report(self):
        game = CubeDemo()
        scene = game.build_scene()
        pixels = bytes((0, 0, 0, 255)) * (8 * 6)
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "frame.png"
            write_png(image, 8, 6, pixels)
            report = analyze_frame(scene, pixels, 8, 6, image)
            self.assertIsNotNone(report["image"]["png_sha256"])
            out = Path(directory) / "report.json"
            write_report(out, report)
            self.assertTrue(out.exists())

    def test_rejects_bad_pixel_count(self):
        game = CubeDemo()
        with self.assertRaises(ValueError):
            analyze_frame(game.build_scene(), b"\x00", 2, 2)


if __name__ == "__main__":
    unittest.main()
