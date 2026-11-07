"""glTF skin parsing: joint nodes and inverse bind matrices."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from keystone.gltf.io import read_accessor

__all__ = ["load_skins"]


def load_skins(
    document: Mapping[str, Any],
    buffers: list[bytes],
    buffer_views: list[Any],
    node_count: int,
) -> list[dict[str, Any]]:
    """Parse the glTF skins array into joint indices and inverse bind matrices."""
    raw_skins = document.get("skins", [])
    if raw_skins is None:
        raw_skins = []
    if not isinstance(raw_skins, list):
        raise TypeError("glTF skins must be a list")
    skins: list[dict[str, Any]] = []
    for skin_index, raw in enumerate(raw_skins):
        if not isinstance(raw, Mapping):
            raise TypeError(f"glTF skin {skin_index} must be an object")
        joints_raw = raw.get("joints", [])
        if not isinstance(joints_raw, list) or not joints_raw:
            raise ValueError(f"glTF skin {skin_index} has no joints")
        joints = [int(joint) for joint in joints_raw]
        if any(joint < 0 or joint >= node_count for joint in joints):
            raise ValueError(f"glTF skin {skin_index} references an unknown node")
        if len(joints) > 64:
            raise ValueError(f"glTF skin {skin_index} exceeds 64 joints")
        inverse_bind: list[tuple[float, ...]] = [(1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)] * len(joints)
        if "inverseBindMatrices" in raw:
            accessor_index = int(raw["inverseBindMatrices"])
            matrices_raw = read_accessor(
                _accessor(document, accessor_index),
                buffer_views,
                buffers,
            )
            if matrices_raw is None or len(matrices_raw) < len(joints):
                raise ValueError(f"glTF skin {skin_index} inverse bind count is smaller than the joint count")
            parsed: list[tuple[float, ...]] = []
            for matrix in matrices_raw[: len(joints)]:
                if not isinstance(matrix, (tuple, list)) or len(matrix) != 16:
                    raise ValueError(f"glTF skin {skin_index} inverse bind matrices must be MAT4")
                values = tuple(float(value) for value in matrix)
                parsed.append(values)
            inverse_bind = parsed
        skins.append({"joints": joints, "inverse_bind": inverse_bind})
    return skins


def _accessor(document: Mapping[str, Any], index: int) -> Mapping[str, Any]:
    accessors = document.get("accessors", [])
    if not isinstance(accessors, list) or index < 0 or index >= len(accessors):
        raise TypeError("glTF accessor index is out of range")
    accessor = accessors[index]
    if not isinstance(accessor, Mapping):
        raise TypeError("glTF accessor must be an object")
    return accessor
