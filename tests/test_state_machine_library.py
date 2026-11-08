"""Tests for file-backed animation state machine libraries."""

import tempfile
import unittest
from pathlib import Path

from keystone import (
    AnimationState,
    AnimationStateMachine,
    AnimationTransition,
)
from keystone.animation import AnimationClip, Track
from keystone.math3d import Vec3
from keystone.state_machine_library import StateMachineLibrary


def _machine():
    idle = AnimationState(
        "idle",
        AnimationClip(
            name="idle",
            position_tracks=(
                (
                    "node",
                    Track(
                        times=(0.0, 1.0),
                        values=(Vec3(0, 0, 0), Vec3(0, 1, 0)),
                    ),
                ),
            ),
        ),
    )
    jump = AnimationState(
        "jump",
        AnimationClip(
            name="jump",
            position_tracks=(
                (
                    "node",
                    Track(
                        times=(0.0, 1.0),
                        values=(Vec3(1, 0, 0), Vec3(1, 2, 0)),
                    ),
                ),
            ),
        ),
    )
    return AnimationStateMachine(
        [idle, jump],
        [AnimationTransition("idle", "jump", "jump", "trigger", duration=0.0)],
        {"jump": False},
    )


class StateMachineLibraryTest(unittest.TestCase):
    def test_save_load_entries_delete_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "animations"
            library = StateMachineLibrary(root)
            self.assertEqual(library.entries(), ())
            machine = _machine()
            entry = library.save("locomotion", machine)
            self.assertEqual(entry.states, 2)
            self.assertEqual(entry.transitions, 1)
            self.assertEqual(entry.current, "idle")
            self.assertTrue((root / "locomotion.kstate").is_file())
            loaded = library.load("locomotion")
            self.assertEqual(loaded.to_dict(), machine.to_dict())
            self.assertEqual(
                [item.name for item in library.entries()], ["locomotion"]
            )

            library.delete("locomotion")
            self.assertFalse((root / "locomotion.kstate").exists())
            trash = library.trash()
            self.assertEqual(len(trash), 1)
            restored = library.restore(trash[0]["trash"])
            self.assertEqual(restored.name, "locomotion")
            self.assertTrue((root / "locomotion.kstate").is_file())

    def test_rename_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "animations"
            library = StateMachineLibrary(root)
            original = _machine()
            library.save("walk", original)

            renamed = library.rename("walk", "run")
            self.assertEqual(renamed.name, "run")
            self.assertFalse((root / "walk.kstate").exists())
            self.assertTrue((root / "run.kstate").is_file())
            self.assertEqual(library.load("run").to_dict(), original.to_dict())

            copied = library.duplicate("run", "run-copy")
            self.assertEqual(copied.name, "run-copy")
            self.assertTrue((root / "run-copy.kstate").is_file())
            self.assertEqual(
                library.load("run-copy").to_dict(), original.to_dict()
            )
            self.assertEqual(
                {item.name for item in library.entries()},
                {"run", "run-copy"},
            )

            with self.assertRaises(FileExistsError):
                library.duplicate("run", "run-copy")
            with self.assertRaises(ValueError):
                library.duplicate("run", "run")
            with self.assertRaises(KeyError):
                library.rename("missing", "other")
            with self.assertRaises(KeyError):
                library.rename("missing", "missing")
            with self.assertRaises(ValueError):
                library.rename("run", "bad name")

    def test_bad_files_and_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "animations"
            root.mkdir()
            library = StateMachineLibrary(root)
            (root / "broken.kstate").write_text("{not json", encoding="utf-8")
            entry = next(
                item for item in library.entries() if item.name == "broken"
            )
            self.assertIsNotNone(entry.error)
            with self.assertRaises(ValueError):
                library.load("broken")
            with self.assertRaises(KeyError):
                library.load("missing")
            with self.assertRaises(TypeError):
                library.save("x", object())
            with self.assertRaises(ValueError):
                library.save("bad name", _machine())
            with self.assertRaises(KeyError):
                library.delete("missing")


if __name__ == "__main__":
    unittest.main()
