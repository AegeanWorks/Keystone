"""Tests for recoverable library deletes (soft delete and restore)."""

import tempfile
import unittest
from pathlib import Path

from keystone.library_trash import (
    TRASH_DIRECTORY,
    move_to_trash,
    restore_from_trash,
    trash_entries,
)


class LibraryTrashTest(unittest.TestCase):
    def _library(self, directory: str) -> Path:
        root = Path(directory) / "library"
        root.mkdir()
        return root

    def test_move_to_trash_relocates_and_hides_the_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            entry = library / "hero.kprefab"
            entry.write_text("{}", encoding="utf-8")

            trashed = move_to_trash(entry, ".kprefab")

            self.assertFalse(entry.exists())
            self.assertTrue(trashed.is_file())
            self.assertEqual(trashed.parent, library / TRASH_DIRECTORY)
            self.assertEqual(trashed.suffix, ".kprefab")
            self.assertEqual(trash_entries(library, ".kprefab")[0]["name"], "hero")

    def test_trash_entries_is_empty_without_a_trash_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            self.assertEqual(trash_entries(library, ".kprefab"), [])
            self.assertFalse((library / TRASH_DIRECTORY).exists())

    def test_trash_entries_is_stable_and_reports_the_source(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            names = []
            for name in ("b", "a", "c"):
                entry = library / f"{name}.kprefab"
                entry.write_text("{}", encoding="utf-8")
                names.append(move_to_trash(entry, ".kprefab").name)

            entries = trash_entries(library, ".kprefab")

            self.assertEqual([entry["name"] for entry in entries], ["a", "b", "c"])
            self.assertEqual(sorted(entry["trash"] for entry in entries), sorted(names))
            for entry in entries:
                self.assertTrue(Path(entry["source"]).is_file())

    def test_two_deletes_of_the_same_name_do_not_collide(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            first = library / "hero.kprefab"
            first.write_text("{}", encoding="utf-8")
            first_trash = move_to_trash(first, ".kprefab")
            second = library / "hero.kprefab"
            second.write_text("{}", encoding="utf-8")
            second_trash = move_to_trash(second, ".kprefab")

            self.assertNotEqual(first_trash, second_trash)
            self.assertEqual(len(trash_entries(library, ".kprefab")), 2)

    def test_restore_returns_the_entry_to_the_library(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            entry = library / "hero.kprefab"
            entry.write_text('{"a": 1}', encoding="utf-8")
            trashed = move_to_trash(entry, ".kprefab")

            restored = restore_from_trash(
                library, trashed.name, ".kprefab", lambda value: str(value)
            )

            self.assertEqual(restored, entry)
            self.assertEqual(entry.read_text(encoding="utf-8"), '{"a": 1}')
            self.assertEqual(trash_entries(library, ".kprefab"), [])

    def test_restore_preserves_dots_in_the_original_name(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            entry = library / "my.scene.kprefab"
            entry.write_text("{}", encoding="utf-8")
            trashed = move_to_trash(entry, ".kprefab")

            restored = restore_from_trash(
                library, trashed.name, ".kprefab", lambda value: str(value)
            )

            self.assertEqual(restored.name, "my.scene.kprefab")

    def test_restore_rejects_a_path_instead_of_a_file_name(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            for trash_name in ("../escape.kprefab", "sub/dir.kprefab"):
                with self.subTest(trash_name=trash_name), self.assertRaises(ValueError):
                    restore_from_trash(
                        library, trash_name, ".kprefab", lambda value: str(value)
                    )

    def test_restore_rejects_a_blank_name(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            for trash_name in ("", "   ", None):
                with self.subTest(trash_name=trash_name), self.assertRaises(ValueError):
                    restore_from_trash(
                        library, trash_name, ".kprefab", lambda value: str(value)
                    )

    def test_restore_rejects_a_missing_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            with self.assertRaises(KeyError):
                restore_from_trash(
                    library, "gone.kprefab", ".kprefab", lambda value: str(value)
                )

    def test_restore_rejects_the_wrong_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            entry = library / "hero.kprefab"
            entry.write_text("{}", encoding="utf-8")
            trashed = move_to_trash(entry, ".kprefab")
            with self.assertRaises(ValueError):
                restore_from_trash(
                    library, trashed.name, ".kstate", lambda value: str(value)
                )

    def test_restore_never_overwrites_a_live_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            entry = library / "hero.kprefab"
            entry.write_text("{}", encoding="utf-8")
            trashed = move_to_trash(entry, ".kprefab")
            entry.write_text('{"live": true}', encoding="utf-8")

            with self.assertRaises(FileExistsError):
                restore_from_trash(
                    library, trashed.name, ".kprefab", lambda value: str(value)
                )

            self.assertEqual(entry.read_text(encoding="utf-8"), '{"live": true}')
            self.assertTrue(trashed.is_file())

    def test_restore_uses_the_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            library = self._library(directory)
            entry = library / "hero.kprefab"
            entry.write_text("{}", encoding="utf-8")
            trashed = move_to_trash(entry, ".kprefab")

            def reject(_value):
                raise ValueError("bad name")

            with self.assertRaises(ValueError):
                restore_from_trash(library, trashed.name, ".kprefab", reject)


if __name__ == "__main__":
    unittest.main()
