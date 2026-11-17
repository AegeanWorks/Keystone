"""Tests for camera path documents and file-backed .kpath libraries."""

import json
import math
import tempfile
import unittest
from pathlib import Path

from keystone import (
    CAMERA_PATH_SCHEMA,
    CAMERA_PATH_SUFFIX,
    CameraKey,
    CameraPath,
    CameraPathLibrary,
    camera_path_from_dict,
    camera_path_to_dict,
)
from keystone.math3d import Quat, Vec3
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _path(*, loop: bool = False) -> CameraPath:
    keys = [
        CameraKey(
            0.0,
            Vec3(0.0, 1.0, 4.0),
            Quat.from_axis_angle(Vec3.UP, -math.pi / 4.0),
        ),
        CameraKey(
            1.5,
            Vec3(2.0, 2.0, 2.0),
            Quat.from_axis_angle(Vec3.UP, -math.pi / 2.0),
            fov_y=50.0,
        ),
        CameraKey(3.0, Vec3(3.0, 1.0, 0.0)),
    ]
    if loop:
        return CameraPath(keys, loop=True, duration=4.5)
    return CameraPath(keys)


class CameraPathDocumentTest(unittest.TestCase):
    def test_one_shot_document_round_trips(self):
        path = _path()
        document = camera_path_to_dict(path)
        self.assertEqual(document["schema"], CAMERA_PATH_SCHEMA)
        self.assertFalse(document["loop"])
        self.assertNotIn("duration", document)
        self.assertEqual(len(document["keys"]), 3)
        restored = camera_path_from_dict(document)
        self.assertFalse(restored.loop)
        self.assertEqual(restored.keys, path.keys)
        self.assertEqual(restored.duration, path.duration)
        for moment in (0.0, 0.25, 1.5, 2.2, 3.0):
            self.assertEqual(restored.sample(moment), path.sample(moment))

    def test_loop_document_round_trips(self):
        path = _path(loop=True)
        document = camera_path_to_dict(path)
        self.assertTrue(document["loop"])
        self.assertEqual(document["duration"], 4.5)
        restored = camera_path_from_dict(document)
        self.assertTrue(restored.loop)
        self.assertEqual(restored.duration, 4.5)
        self.assertEqual(restored.keys, path.keys)
        self.assertEqual(restored.sample(5.0), restored.sample(0.5))

    def test_document_uses_engine_rotation_order(self):
        rotation = Quat.from_axis_angle(Vec3.UP, -math.pi / 2.0)
        path = CameraPath([CameraKey(0.0, Vec3(), rotation)])
        document = camera_path_to_dict(path)
        self.assertEqual(
            document["keys"][0]["rotation"],
            [rotation.x, rotation.y, rotation.z, rotation.w],
        )
        restored = camera_path_from_dict(document)
        self.assertEqual(restored.keys[0].rotation, rotation)

    def test_document_defaults_a_minimal_key(self):
        restored = camera_path_from_dict(
            {"keys": [{"time": 0, "position": [1, 2, 3]}]}
        )
        key = restored.keys[0]
        self.assertEqual(key.time, 0.0)
        self.assertEqual(key.position, Vec3(1.0, 2.0, 3.0))
        self.assertEqual(key.rotation, Quat())
        self.assertEqual(key.fov_y, 60.0)
        self.assertFalse(restored.loop)

    def test_document_is_json_safe(self):
        json.dumps(camera_path_to_dict(_path(loop=True)))

    def test_document_refuses_schema_drift(self):
        base = {"schema": CAMERA_PATH_SCHEMA, "keys": []}
        for schema in (2, 0, True, "1"):
            with self.subTest(schema=schema):
                document = dict(base)
                document["schema"] = schema
                with self.assertRaises(ValueError):
                    camera_path_from_dict(document)

    def test_document_refuses_unknown_fields(self):
        with self.assertRaises(ValueError):
            camera_path_from_dict({"keys": [], "speed": 2.0})
        key = {"time": 0.0, "position": [0.0, 0.0, 0.0], "ease": "linear"}
        with self.assertRaises(ValueError):
            camera_path_from_dict({"keys": [key]})

    def test_document_refuses_malformed_keys(self):
        good = {"time": 0.0, "position": [0.0, 0.0, 0.0]}
        with self.assertRaises(TypeError):
            camera_path_from_dict({"keys": "nope"})
        with self.assertRaises(TypeError):
            camera_path_from_dict({"keys": [0]})
        with self.assertRaises(ValueError):
            camera_path_from_dict({"keys": [{"position": [0.0, 0.0, 0.0]}]})
        with self.assertRaises(ValueError):
            camera_path_from_dict({"keys": [{"time": 0.0}]})
        with self.assertRaises(ValueError):
            camera_path_from_dict(
                {"keys": [{"time": 0.0, "position": [0.0, 0.0]}]}
            )
        with self.assertRaises(TypeError):
            camera_path_from_dict(
                {"keys": [{"time": 0.0, "position": [0.0, True, 0.0]}]}
            )
        with self.assertRaises(ValueError):
            camera_path_from_dict(
                {"keys": [{"time": 0.0, "position": [0.0, math.inf, 0.0]}]}
            )
        with self.assertRaises(ValueError):
            camera_path_from_dict(
                {"keys": [dict(good, rotation=[0.0, 0.0, 0.0])]}
            )
        with self.assertRaises(TypeError):
            camera_path_from_dict(
                {"keys": [dict(good, rotation=[0.0, 0.0, 0.0, "w"])]}
            )
        with self.assertRaises(ValueError):
            camera_path_from_dict({"keys": [dict(good, fov_y=0.0)]})
        with self.assertRaises(ValueError):
            camera_path_from_dict({"keys": [dict(good, fov_y=180.0)]})
        with self.assertRaises(TypeError):
            camera_path_from_dict({"keys": [dict(good, time=True)]})

    def test_document_loop_and_duration_must_agree(self):
        keys = [
            {"time": 0.0, "position": [0.0, 0.0, 0.0]},
            {"time": 1.0, "position": [1.0, 0.0, 0.0]},
        ]
        with self.assertRaises(ValueError):
            camera_path_from_dict({"loop": True, "keys": keys})
        with self.assertRaises(ValueError):
            camera_path_from_dict({"keys": keys, "duration": 2.0})
        with self.assertRaises(ValueError):
            camera_path_from_dict({"loop": True, "duration": 1.0, "keys": keys})
        with self.assertRaises(TypeError):
            camera_path_from_dict({"loop": True, "duration": True, "keys": keys})
        with self.assertRaises(TypeError):
            camera_path_from_dict({"loop": "yes", "keys": keys})
        restored = camera_path_from_dict(
            {"loop": True, "duration": 2.0, "keys": keys}
        )
        self.assertTrue(restored.loop)
        self.assertEqual(restored.duration, 2.0)

    def test_document_requires_a_mapping(self):
        with self.assertRaises(TypeError):
            camera_path_from_dict([])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            camera_path_to_dict(object())  # type: ignore[arg-type]


class CameraPathLibraryTest(unittest.TestCase):
    def test_save_load_entries_and_describe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "paths"
            library = CameraPathLibrary(root)
            self.assertEqual(library.entries(), ())
            path = _path()
            entry = library.save("intro", path)
            self.assertEqual(entry.name, "intro")
            self.assertEqual(entry.duration, 3.0)
            self.assertEqual(entry.keys, 3)
            self.assertFalse(entry.loop)
            self.assertIsNone(entry.error)
            self.assertTrue((root / f"intro{CAMERA_PATH_SUFFIX}").is_file())
            loaded = library.load("intro")
            self.assertEqual(loaded.keys, path.keys)
            self.assertEqual(loaded.sample(0.75), path.sample(0.75))
            library.save("walk", _path(loop=True))
            self.assertEqual([item.name for item in library.entries()], ["intro", "walk"])
            summaries = [item.describe() for item in library.entries()]
            self.assertEqual(summaries[1]["duration"], 4.5)
            self.assertTrue(summaries[1]["loop"])
            json.dumps(summaries)

    def test_save_validates_payload_and_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "paths"
            library = CameraPathLibrary(root)
            with self.assertRaises(TypeError):
                library.save("intro", object())  # type: ignore[arg-type]
            for name in ("", "  ", "../escape", "a/b", "a\\b", ".hidden"):
                with (
                    self.subTest(name=name),
                    self.assertRaises(ValueError),
                ):
                    library.save(name, _path())
            self.assertFalse((Path(directory) / "escape.kpath").exists())
            self.assertFalse(root.exists())

    def test_load_reports_a_missing_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            library = CameraPathLibrary(directory)
            with self.assertRaises(KeyError):
                library.load("absent")

    def test_rename_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            library = CameraPathLibrary(Path(directory) / "paths")
            library.save("intro", _path())
            self.assertEqual(library.rename("intro", "opening").name, "opening")
            self.assertFalse(library.path_for("intro").exists())
            self.assertEqual(library.entry("opening").keys, 3)
            self.assertEqual(library.rename("opening", "opening").name, "opening")
            copied = library.duplicate("opening", "opening-copy")
            self.assertEqual(copied.duration, 3.0)
            self.assertEqual(
                [item.name for item in library.entries()],
                ["opening-copy", "opening"],
            )
            with self.assertRaises(FileExistsError):
                library.rename("opening", "opening-copy")
            with self.assertRaises(FileExistsError):
                library.duplicate("opening", "opening-copy")
            with self.assertRaises(ValueError):
                library.duplicate("opening", "opening")
            with self.assertRaises(KeyError):
                library.rename("absent", "other")
            with self.assertRaises(KeyError):
                library.duplicate("absent", "other")

    def test_delete_trash_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            library = CameraPathLibrary(Path(directory) / "paths")
            library.save("intro", _path())
            former = library.delete("intro")
            self.assertFalse(former.exists())
            self.assertEqual(library.entries(), ())
            trashed = library.trash()
            self.assertEqual(len(trashed), 1)
            self.assertEqual(trashed[0]["name"], "intro")
            restored = library.restore(trashed[0]["trash"])
            self.assertEqual(restored.name, "intro")
            self.assertEqual(restored.keys, 3)
            self.assertEqual(library.trash(), [])
            with self.assertRaises(KeyError):
                library.restore(trashed[0]["trash"])

    def test_restore_refuses_traversal_and_collisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "paths"
            library = CameraPathLibrary(root)
            library.save("intro", _path())
            library.delete("intro")
            entry = library.trash()[0]
            with self.assertRaises(ValueError):
                library.restore("../escape.kpath")
            with self.assertRaises(KeyError):
                library.restore("notes.txt")
            trash_root = root / ".trash"
            (trash_root / "notes.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                library.restore("notes.txt")
            library.save("intro", _path(loop=True))
            with self.assertRaises(FileExistsError):
                library.restore(entry["trash"])
            self.assertTrue(library.path_for("intro").is_file())

    def test_corrupt_and_unsupported_entries_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "paths"
            root.mkdir(parents=True)
            library = CameraPathLibrary(root)
            library.save("good", _path())
            (root / "broken.kpath").write_text("{not json", encoding="utf-8")
            (root / "future.kpath").write_text(
                json.dumps({"schema": 2, "keys": []}), encoding="utf-8"
            )
            (root / "bad key name!.kpath").write_text("{}", encoding="utf-8")
            entries = {item.name: item for item in library.entries()}
            self.assertEqual(entries["good"].keys, 3)
            self.assertIsNone(entries["good"].error)
            self.assertIsNotNone(entries["broken"].error)
            self.assertIsNotNone(entries["future"].error)
            self.assertIsNotNone(entries["bad key name!"].error)
            with self.assertRaises(ValueError):
                library.load("broken")
            with self.assertRaises(ValueError):
                library.load("future")

    def test_missing_directory_lists_empty_and_a_file_is_not_a_library(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = CameraPathLibrary(Path(directory) / "absent")
            self.assertEqual(missing.entries(), ())
            note = Path(directory) / "note.txt"
            note.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                CameraPathLibrary(note).entries()

    def test_discovery_advertises_the_library(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["camera_path_library"])


if __name__ == "__main__":
    unittest.main()
