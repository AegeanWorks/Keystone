"""A versioned JSON store with migrations, quarantine and backup fallback.

Games persist progress, and the failure modes are subtle: a schema bump that
reads an old file, a truncated write, a corrupt document that must not be
silently replaced, and two processes saving at once. `serialization` already
provides atomic writes and a ``.bak`` copy; this module adds the policy on top:

- documents are ``{"schema": <int>, "data": <mapping>}``;
- older schemas migrate through every registered step, in order;
- a future schema or a missing migration is refused without touching the file;
- corrupt or invalid documents are moved into ``quarantine/`` and the backup
  is tried before falling back to a fresh default;
- saves take an advisory ``.lock`` file that is reclaimed after a stale
  timeout, and return False when another writer holds it.

Loading never rewrites a valid document, so a read is safe for a game that
only wants to inspect state. The store is otherwise policies, not storage
format: callers pass a default factory, migrations and an optional normalizer.
"""

from __future__ import annotations

import copy
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from keystone.serialization import read_json, write_json_atomic

__all__ = ["LoadResult", "VersionedStore"]


@dataclass(frozen=True, slots=True)
class LoadResult:
    """The loaded state plus how it was obtained."""

    state: dict
    source: str
    migrated: bool = False
    quarantined: bool = False
    unsupported: bool = False


def _constant(label: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a real number")
    number = float(value)
    if number <= 0.0 or not (number < float("inf")):
        raise ValueError(f"{label} must be finite and positive")
    return number


class VersionedStore:
    """Load and save one versioned JSON document with recovery policy."""

    def __init__(
        self,
        path: str | Path,
        *,
        schema: int,
        default: Mapping | Callable[[], Mapping],
        migrations: Mapping[int, Callable[[dict], Mapping]] | None = None,
        validate: Callable[[dict], Mapping] | None = None,
        stale_lock_seconds: float = 30.0,
    ) -> None:
        if isinstance(schema, bool) or not isinstance(schema, int) or schema < 1:
            raise ValueError("store schema must be a positive integer")
        if not callable(default) and not isinstance(default, Mapping):
            raise TypeError("store default must be a mapping or a callable returning one")
        if migrations is not None and not isinstance(migrations, Mapping):
            raise TypeError("store migrations must be a mapping of step to callable")
        if migrations is not None:
            for step, migrate in migrations.items():
                if isinstance(step, bool) or not isinstance(step, int) or step < 0:
                    raise ValueError("store migration steps must be non-negative integers")
                if not callable(migrate):
                    raise TypeError("store migration values must be callable")
        if validate is not None and not callable(validate):
            raise TypeError("store validate must be callable or None")
        self.path = Path(path)
        self.schema = schema
        self.default = default
        self.migrations = dict(migrations or {})
        self.validate = validate
        self.stale_lock_seconds = _constant("store stale lock seconds", stale_lock_seconds)

    def _default_state(self) -> dict:
        value = self.default() if callable(self.default) else copy.deepcopy(self.default)
        if not isinstance(value, Mapping):
            raise TypeError("store default must produce a mapping")
        return self._normalized(dict(value))

    def _normalized(self, state: Mapping) -> dict:
        if not isinstance(state, Mapping):
            raise TypeError("store state must be a mapping")
        result = dict(state)
        if self.validate is not None:
            normalized = self.validate(result)
            if not isinstance(normalized, Mapping):
                raise TypeError("store validate must return a mapping")
            result = dict(normalized)
        return result

    def _read_document(self, path: Path) -> tuple[str, dict | None, bool]:
        """Return ``(status, state, migrated)``; status is missing/ok/corrupt/unsupported."""
        if not path.is_file():
            return ("missing", None, False)
        try:
            document = read_json(path)
        except (OSError, ValueError, TypeError):
            return ("corrupt", None, False)
        if not isinstance(document, dict):
            return ("corrupt", None, False)
        schema = document.get("schema")
        data = document.get("data")
        if isinstance(schema, bool) or not isinstance(schema, int) or not isinstance(data, Mapping):
            return ("corrupt", None, False)
        if schema > self.schema:
            return ("unsupported", None, False)
        state = dict(data)
        migrated = schema < self.schema
        try:
            for step in range(schema, self.schema):
                migrate = self.migrations.get(step)
                if migrate is None:
                    return ("unsupported", None, False)
                migrated_state = migrate(dict(state))
                if not isinstance(migrated_state, Mapping):
                    return ("corrupt", None, False)
                state = dict(migrated_state)
            state = self._normalized(state)
        except (TypeError, ValueError, KeyError, IndexError, ArithmeticError):
            return ("corrupt", None, False)
        return ("ok", state, migrated)

    def _quarantine(self, path: Path) -> bool:
        if not path.is_file():
            return False
        directory = path.parent / "quarantine"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            destination = directory / f"{path.stem}.{time.time_ns()}{path.suffix}"
            os.replace(path, destination)
        except OSError:
            return False
        return True

    def _lock_path(self) -> Path:
        return Path(str(self.path) + ".lock")

    def _acquire_lock(self) -> Path | None:
        lock = self._lock_path()
        lock.parent.mkdir(parents=True, exist_ok=True)
        for _attempt in range(2):
            try:
                descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    age = time.time() - lock.stat().st_mtime
                except OSError:
                    continue
                if age <= self.stale_lock_seconds:
                    return None
                try:
                    lock.unlink()
                except OSError:
                    return None
                continue
            try:
                os.write(descriptor, str(os.getpid()).encode("ascii"))
            finally:
                os.close(descriptor)
            return lock
        return None

    def load(self) -> LoadResult:
        """Load the document, migrating or recovering as configured."""
        status, state, migrated = self._read_document(self.path)
        if status == "missing":
            return LoadResult(self._default_state(), "default")
        if status == "unsupported":
            return LoadResult(self._default_state(), "default", unsupported=True)
        if status == "ok":
            assert state is not None
            return LoadResult(state, "file", migrated=migrated)
        quarantined = self._quarantine(self.path)
        backup = self.path.with_name(self.path.name + ".bak")
        backup_status, backup_state, backup_migrated = self._read_document(backup)
        if backup_status == "ok":
            assert backup_state is not None
            return LoadResult(
                backup_state,
                "backup",
                migrated=backup_migrated,
                quarantined=quarantined,
            )
        return LoadResult(self._default_state(), "default", quarantined=quarantined)

    def save(self, state: Mapping) -> bool:
        """Normalize and atomically save; False when another writer holds the lock."""
        normalized = self._normalized(state)
        lock = self._acquire_lock()
        if lock is None:
            return False
        try:
            write_json_atomic(
                self.path,
                {"schema": self.schema, "data": normalized},
            )
        finally:
            try:
                lock.unlink()
            # hygiene: allow a failed release must not mask a successful save; a stale lock is reclaimed
            except OSError:
                pass
        return True
