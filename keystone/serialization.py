"""Atomic JSON persistence for engine and game state."""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from pathlib import Path


def _temporary_path(target: Path) -> Path:
    suffix = f".{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
    return target.with_name(f".{target.name}{suffix}")


def _replace_with_retry(temporary: Path, target: Path, attempts: int = 5) -> None:
    for attempt in range(attempts):
        try:
            os.replace(temporary, target)
            return
        except OSError:
            if attempt + 1 >= attempts:
                raise
            time.sleep(0.01 * (attempt + 1))


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_bytes_atomic(path: str | Path, payload: bytes) -> None:
    """Write bytes through a unique temp file, fsync and atomic replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(target)
    try:
        # hygiene: allow binary payload; text encoding does not apply to bytes
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(temporary, target)
        _fsync_directory(target.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json_atomic(path: str | Path, payload: object, backup: bool = True) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if backup and target.exists():
        shutil.copy2(target, target.with_name(target.name + ".bak"))
    write_bytes_atomic(target, text.encode("utf-8"))


def read_json(path: str | Path) -> object:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)
