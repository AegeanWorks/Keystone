"""Tests for the versioned persistence store."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from keystone.persistence import LoadResult, VersionedStore
from keystone.plugin import describe_game
from keystone.samples import CubeDemo


def _default() -> dict:
    return {"level": 1, "score": 0, "unlocks": []}


def _store(directory: Path, **kwargs) -> VersionedStore:
    values = {
        "schema": 3,
        "default": _default,
        "migrations": {
            0: lambda state: {**state, "level": 1},
            1: lambda state: {**state, "score": state.get("score", 0)},
            2: lambda state: {**state, "unlocks": list(state.get("unlocks", []))},
        },
    }
    values.update(kwargs)
    return VersionedStore(directory / "profile.json", **values)


class VersionedStoreTest(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_a_missing_file_returns_a_fresh_default(self):
        store = _store(self.directory)
        first = store.load()
        self.assertIsInstance(first, LoadResult)
        self.assertEqual(first.source, "default")
        self.assertEqual(first.state, {"level": 1, "score": 0, "unlocks": []})
        first.state["unlocks"].append("x")
        second = store.load()
        self.assertEqual(second.state["unlocks"], [])

    def test_save_and_load_round_trip(self):
        store = _store(self.directory)
        state = {"level": 4, "score": 120, "unlocks": ["a"]}
        self.assertTrue(store.save(state))
        loaded = store.load()
        self.assertEqual(loaded.source, "file")
        self.assertEqual(loaded.state, state)
        self.assertFalse(loaded.migrated)

    def test_a_corrupt_file_falls_back_to_the_backup_and_is_quarantined(self):
        store = _store(self.directory)
        store.save({"level": 2, "score": 10, "unlocks": []})
        store.save({"level": 3, "score": 20, "unlocks": []})
        self.assertTrue((self.directory / "profile.json.bak").is_file())
        (self.directory / "profile.json").write_text("not json", encoding="utf-8")
        loaded = store.load()
        self.assertEqual(loaded.source, "backup")
        self.assertTrue(loaded.quarantined)
        self.assertEqual(loaded.state["level"], 2)
        quarantined = list((self.directory / "quarantine").iterdir())
        self.assertEqual(len(quarantined), 1)
        self.assertFalse((self.directory / "profile.json").exists())

    def test_a_corrupt_file_without_a_backup_returns_the_default(self):
        store = _store(self.directory)
        (self.directory / "profile.json").write_text("{", encoding="utf-8")
        loaded = store.load()
        self.assertEqual(loaded.source, "default")
        self.assertTrue(loaded.quarantined)
        self.assertEqual(loaded.state, _default())

    def test_old_documents_migrate_through_every_step(self):
        path = self.directory / "profile.json"
        path.write_text(json.dumps({"schema": 0, "data": {}}), encoding="utf-8")
        store = _store(self.directory)
        loaded = store.load()
        self.assertTrue(loaded.migrated)
        self.assertEqual(loaded.state, {"level": 1, "score": 0, "unlocks": []})
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["schema"], 0)

    def test_a_future_schema_is_refused_without_touching_the_file(self):
        path = self.directory / "profile.json"
        original = json.dumps({"schema": 9, "data": {"level": 9}})
        path.write_text(original, encoding="utf-8")
        loaded = _store(self.directory).load()
        self.assertTrue(loaded.unsupported)
        self.assertEqual(loaded.source, "default")
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertFalse((self.directory / "quarantine").exists())

    def test_a_missing_migration_step_is_refused(self):
        path = self.directory / "profile.json"
        path.write_text(json.dumps({"schema": 0, "data": {}}), encoding="utf-8")
        store = VersionedStore(
            path,
            schema=3,
            default=_default,
            migrations={ 1: lambda state: state},
        )
        loaded = store.load()
        self.assertTrue(loaded.unsupported)
        self.assertEqual(loaded.source, "default")

    def test_validation_failure_quarantines_and_uses_the_backup(self):
        store = _store(self.directory, validate=lambda state: {**state, "score": max(0, state["score"])})
        store.save({"level": 1, "score": 5, "unlocks": []})
        store.save({"level": 2, "score": 10, "unlocks": []})
        (self.directory / "profile.json").write_text(
            json.dumps({"schema": 3, "data": {"level": 2, "score": "broken", "unlocks": []}}),
            encoding="utf-8",
        )
        loaded = store.load()
        self.assertEqual(loaded.source, "backup")
        self.assertTrue(loaded.quarantined)

    def test_invalid_state_is_not_saved(self):
        store = _store(self.directory, validate=lambda state: {**state, "score": int(state["score"])})
        with self.assertRaises((TypeError, ValueError)):
            store.save({"level": 1, "score": "bad", "unlocks": []})
        self.assertFalse((self.directory / "profile.json").exists())

    def test_save_is_refused_while_a_fresh_lock_exists(self):
        store = _store(self.directory)
        lock = Path(str(store.path) + ".lock")
        lock.write_text("other", encoding="utf-8")
        self.assertFalse(store.save(_default()))
        self.assertFalse((self.directory / "profile.json").exists())

    def test_a_stale_lock_is_reclaimed(self):
        store = _store(self.directory)
        lock = Path(str(store.path) + ".lock")
        lock.write_text("other", encoding="utf-8")
        stale = time.time() - 60.0
        os.utime(lock, (stale, stale))
        self.assertTrue(store.save(_default()))
        self.assertFalse(lock.exists())
        self.assertTrue((self.directory / "profile.json").is_file())

    def test_a_validated_state_is_normalized_before_saving(self):
        store = _store(self.directory, validate=lambda state: {**state, "score": max(0, state["score"])})
        store.save({"level": 1, "score": -5, "unlocks": []})
        self.assertEqual(store.load().state["score"], 0)

    def test_malformed_documents_are_treated_as_corrupt(self):
        store = _store(self.directory)
        (self.directory / "profile.json").write_text(json.dumps({"data": {}}), encoding="utf-8")
        loaded = store.load()
        self.assertTrue(loaded.quarantined)
        self.assertEqual(loaded.source, "default")

    def test_validation(self):
        with self.assertRaises(ValueError):
            VersionedStore(self.directory / "x.json", schema=0, default=_default)
        with self.assertRaises(TypeError):
            VersionedStore(self.directory / "x.json", schema=1, default=[])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            VersionedStore(self.directory / "x.json", schema=1, default=_default, migrations=[])
        with self.assertRaises(ValueError):
            VersionedStore(self.directory / "x.json", schema=1, default=_default, stale_lock_seconds=0.0)

    def test_describe_advertises_persistence(self):
        capabilities = describe_game(CubeDemo())["capabilities"]
        self.assertTrue(capabilities["persistence"])


if __name__ == "__main__":
    unittest.main()
