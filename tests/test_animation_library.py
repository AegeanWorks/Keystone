"""Tests for file-backed animation clip libraries."""

import tempfile
import unittest
from pathlib import Path

from keystone.animation import AnimationClip
from keystone.animation_library import AnimationLibrary


class AnimationLibraryTest(unittest.TestCase):
    def test_save_load_entries_delete_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            library = AnimationLibrary(Path(directory) / "animations")
            clip = AnimationClip(name="bob")
            entry = library.save("bob", clip)
            self.assertEqual(entry.name, "bob")
            self.assertEqual(entry.track_count, 0)
            self.assertEqual(library.load("bob"), clip)
            self.assertEqual([item.name for item in library.entries()], ["bob"])

            library.delete("bob")
            self.assertEqual(library.entries(), ())
            trashed = library.trash()
            self.assertEqual(len(trashed), 1)
            restored = library.restore(trashed[0]["trash"])
            self.assertEqual(restored.name, "bob")
            self.assertEqual(library.load("bob"), clip)

    def test_invalid_name_and_missing_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            library = AnimationLibrary(directory)
            with self.assertRaises(ValueError):
                library.save("../escape", AnimationClip(name="../escape"))
            with self.assertRaises(KeyError):
                library.load("missing")
            with self.assertRaises(KeyError):
                library.delete("missing")
            with self.assertRaises(KeyError):
                library.restore("missing.kanim")


if __name__ == "__main__":
    unittest.main()
