"""Tests for the machine-readable frame report."""

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from keystone.analysis import (
    REPORT_SCHEMA,
    analyze_frame,
    compare_reports,
    diff_images,
    write_report,
)
from keystone.geometry import Material
from keystone.math3d import Vec3
from keystone.png import write_png
from keystone.samples import CubeDemo
from keystone.scene import Node, Scene


@dataclass(frozen=True)
class Health:
    value: int


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

    def test_node_on_the_projection_plane_stays_in_the_report(self):
        from keystone.scene import Transform

        scene = Scene()
        scene.camera.position = Vec3(0.0, 0.0, 5.0)
        scene.camera.look_at(Vec3(0.0, 0.0, 0.0))
        scene.add(Node("at-eye", transform=Transform(position=Vec3(0.0, 0.0, 5.0))))
        scene.add(Node("origin"))
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * (64 * 48), 64, 48)
        names = [node["name"] for node in report["scene"]["nodes"]]
        self.assertIn("at-eye", names)
        self.assertIn("origin", names)
        at_eye = next(node for node in report["scene"]["nodes"] if node["name"] == "at-eye")
        self.assertIsNone(at_eye["screen"])

    def test_material_and_texture_metadata_are_reported(self):
        scene = CubeDemo().build_scene()
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        floor = next(node for node in report["scene"]["nodes"] if node["name"] == "floor")
        material = floor["material"]
        texture = material["texture"]
        self.assertEqual(texture["name"], "floor-checker")
        self.assertEqual((texture["width"], texture["height"]), (64, 64))
        self.assertEqual(len(texture["sha256"]), 64)
        self.assertGreater(material["shininess"], 0)
        root = next(node for node in report["scene"]["nodes"] if node["name"] == "")
        self.assertNotIn("material", root)

    def test_scene_identity_metadata_is_reported(self):
        scene = Scene()
        scene.camera.position = Vec3(0.0, 0.0, 5.0)
        hero = scene.add(Node("hero", id="hero-1", tags={"player", "lit"}, layer="actors"))
        hero.add_component(Health(3))
        report = analyze_frame(scene, bytes((0, 0, 0, 255)) * 4, 2, 2)
        entry = next(node for node in report["scene"]["nodes"] if node["id"] == "hero-1")
        self.assertEqual(entry["name"], "hero")
        self.assertEqual(entry["parent_id"], "root")
        self.assertEqual(entry["tags"], ["lit", "player"])
        self.assertEqual(entry["layer"], "actors")
        self.assertEqual(entry["components"], ["Health"])
        root = next(node for node in report["scene"]["nodes"] if node["id"] == "root")
        self.assertEqual(root["tags"], [])
        self.assertEqual(root["components"], [])

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

    def test_compare_reports_detects_image_and_stats_changes(self):
        first = analyze_frame(CubeDemo().build_scene(), bytes((0, 0, 0, 255)) * 4, 2, 2)
        second = analyze_frame(CubeDemo().build_scene(), bytes((255, 0, 0, 255)) * 4, 2, 2)
        diff = compare_reports(first, second)
        self.assertFalse(diff["same_image"])
        self.assertTrue(diff["same_image"] is False)
        self.assertNotEqual(diff["mean_luma_delta"], 0.0)
        self.assertIn("changed_nodes", diff)

    def test_ui_metadata_is_hashed_and_compared(self):
        self.assertEqual(REPORT_SCHEMA["version"], 11)
        game = CubeDemo()
        pixels = bytes((0, 0, 0, 255)) * 4
        first = analyze_frame(
            game.build_scene(),
            pixels,
            2,
            2,
            ui={
                "visible": True,
                "paused": False,
                "labels": [{"text": "HUD", "x": 1, "y": 2, "scale": 2, "color": [1.0, 1.0, 1.0, 1.0]}],
                "buttons": [],
            },
        )
        second = analyze_frame(
            game.build_scene(),
            pixels,
            2,
            2,
            ui={
                "visible": True,
                "paused": True,
                "labels": [{"text": "MENU", "x": 1, "y": 2, "scale": 2, "color": [1.0, 1.0, 1.0, 1.0]}],
                "buttons": [
                    {
                        "label": "RESUME",
                        "action": "resume",
                        "rect": [4, 4, 40, 20],
                        "selected": True,
                        "hovered": False,
                    }
                ],
            },
        )
        self.assertNotEqual(first["hash"], second["hash"])
        diff = compare_reports(first, second)
        self.assertTrue(diff["same_image"])
        self.assertFalse(diff["same_ui"])
        self.assertEqual(diff["ui"]["added_labels"], ["MENU"])
        self.assertEqual(diff["ui"]["removed_labels"], ["HUD"])
        self.assertEqual(diff["ui"]["added_buttons"], ["resume"])
        self.assertTrue(diff["ui"]["paused"]["after"])

    def test_compare_reports_accepts_older_schemas(self):
        report = analyze_frame(CubeDemo().build_scene(), bytes((0, 0, 0, 255)) * 4, 2, 2)
        for version in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            legacy = dict(report)
            legacy["schema"] = version
            legacy.pop("ui")
            diff = compare_reports(legacy, report)
            self.assertTrue(diff["same_ui"])
            self.assertEqual(diff["schema"], 11)

    def test_compare_reports_detects_identity_metadata_changes(self):
        first_scene = Scene()
        first_scene.camera.position = Vec3(0.0, 0.0, 5.0)
        first_scene.add(Node("hero", id="hero-1", tags={"player"}, layer="actors"))
        second_scene = Scene()
        second_scene.camera.position = Vec3(0.0, 0.0, 5.0)
        hero = second_scene.add(Node("hero", id="hero-1", tags={"enemy"}, layer="props"))
        hero.add_component(Health(9))
        diff = compare_reports(
            analyze_frame(first_scene, bytes((0, 0, 0, 255)) * 4, 2, 2),
            analyze_frame(second_scene, bytes((0, 0, 0, 255)) * 4, 2, 2),
        )
        self.assertIn("hero-1", diff["changed_nodes"])

    def test_compare_reports_distinguishes_duplicate_names_by_id(self):
        first_scene = Scene()
        first_scene.camera.position = Vec3(0.0, 0.0, 5.0)
        first_scene.add(Node("duplicate", id="first"))
        first_scene.add(Node("duplicate", id="second"))
        second_scene = Scene()
        second_scene.camera.position = Vec3(0.0, 0.0, 5.0)
        second_scene.add(Node("duplicate", id="first"))
        pixels = bytes((0, 0, 0, 255)) * 4
        diff = compare_reports(
            analyze_frame(first_scene, pixels, 2, 2),
            analyze_frame(second_scene, pixels, 2, 2),
        )
        self.assertEqual(diff["removed_nodes"], ["second"])
        self.assertEqual(diff["added_nodes"], [])
        self.assertNotIn("first", diff["changed_nodes"])

    def test_compare_reports_detects_material_changes(self):
        pixels = bytes((0, 0, 0, 255)) * 4
        first_scene = CubeDemo().build_scene()
        second_scene = CubeDemo().build_scene()
        floor = next(node for node in second_scene.traverse() if node.name == "floor")
        floor.material = Material(color=Vec3(1.0, 0.0, 0.0))
        diff = compare_reports(
            analyze_frame(first_scene, pixels, 2, 2),
            analyze_frame(second_scene, pixels, 2, 2),
        )
        self.assertIn("floor", diff["changed_nodes"])

    def test_compare_reports_rejects_unknown_schema(self):
        with self.assertRaises(ValueError):
            compare_reports({}, {})

    def test_pixel_diff_writes_an_artifact_and_stats(self):
        first = bytes((0, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 255))
        second = bytes((0, 0, 0, 255, 255, 255, 255, 255, 0, 0, 0, 255, 0, 0, 0, 255))
        with tempfile.TemporaryDirectory() as directory:
            before = Path(directory) / "before.png"
            after = Path(directory) / "after.png"
            diff = Path(directory) / "diff.png"
            write_png(before, 2, 2, first)
            write_png(after, 2, 2, second)
            result = diff_images(before, after, diff, threshold=8)
            self.assertEqual(result["changed_pixels"], 1)
            self.assertEqual(result["bbox"], [1, 1, 1, 1])
            self.assertTrue(diff.exists())

    def test_pixel_diff_rejects_dimension_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.png"
            second = Path(directory) / "b.png"
            write_png(first, 1, 1, bytes((0, 0, 0, 255)))
            write_png(second, 2, 1, bytes((0, 0, 0, 255)) * 2)
            with self.assertRaises(ValueError):
                diff_images(first, second, Path(directory) / "diff.png")

    def test_rejects_bad_pixel_count(self):
        game = CubeDemo()
        with self.assertRaises(ValueError):
            analyze_frame(game.build_scene(), b"\x00", 2, 2)

    def test_grid_luma_uses_per_cell_counts(self):
        scene = Scene()
        pixels = bytes((255, 255, 255, 255)) * (10 * 10)
        report = analyze_frame(scene, pixels, 10, 10)
        self.assertEqual(report["stats"]["grid_luma"][1][1], 255.0)


if __name__ == "__main__":
    unittest.main()
