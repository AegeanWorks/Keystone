"""glTF source reading, buffers and typed accessor decoding."""

from __future__ import annotations

import base64
import json
import re
import struct
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_COMPONENT_FORMATS = {
    5120: ("b", 1),
    5121: ("B", 1),
    5122: ("h", 2),
    5123: ("H", 2),
    5125: ("I", 4),
    5126: ("f", 4),
}
_TYPE_COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_source(source: object) -> tuple[str, Path]:
    """Return (json text, base directory) for a path, JSON text or bytes."""
    if isinstance(source, Mapping):
        return json.dumps(source), Path.cwd()
    if isinstance(source, (bytes, bytearray)):
        return bytes(source).decode("utf-8"), Path.cwd()
    if isinstance(source, Path):
        path = source
    elif isinstance(source, str):
        path = Path(source)
        if not path.exists():
            return source, Path.cwd()
    else:
        raise TypeError("glTF source must be a path, JSON text or bytes")
    if not path.is_file():
        raise FileNotFoundError(f"glTF file not found: {path}")
    return path.read_text(encoding="utf-8"), path.parent


def decode_data_uri(uri: str) -> bytes:
    match = re.match(r"data:([^;]*);base64,(.*)", uri, re.DOTALL)
    if match is None:
        raise ValueError("glTF data URI must be base64 encoded")
    return base64.b64decode(match.group(2))


def load_buffers(document: Mapping[str, Any], base_dir: Path) -> list[bytes]:
    raw_buffers = document.get("buffers", [])
    if not isinstance(raw_buffers, list):
        raise TypeError("glTF buffers must be a list")
    buffers: list[bytes] = []
    for index, raw in enumerate(raw_buffers):
        if not isinstance(raw, Mapping):
            raise TypeError(f"glTF buffer {index} must be an object")
        if "uri" in raw:
            uri = str(raw["uri"])
            if uri.startswith("data:"):
                buffers.append(decode_data_uri(uri))
            else:
                path = Path(uri)
                if not path.is_absolute():
                    path = base_dir / path
                if not path.is_file():
                    raise FileNotFoundError(f"glTF buffer file not found: {path}")
                buffers.append(path.read_bytes())
        else:
            length = int(raw.get("byteLength", 0))
            buffers.append(b"\x00" * length)
    return buffers


def read_accessor(
    accessor: Mapping[str, Any],
    buffer_views: list[Any],
    buffers: list[bytes],
) -> list[Any]:
    if not isinstance(accessor, Mapping):
        raise TypeError("glTF accessor must be an object")
    if "bufferView" not in accessor:
        count = int(accessor.get("count", 0))
        return [0] * count
    view_index = int(accessor["bufferView"])
    if view_index < 0 or view_index >= len(buffer_views):
        raise ValueError("glTF accessor references an unknown bufferView")
    view = buffer_views[view_index]
    if not isinstance(view, Mapping):
        raise TypeError("glTF bufferView must be an object")
    buffer_index = int(view.get("buffer", 0))
    if buffer_index < 0 or buffer_index >= len(buffers):
        raise ValueError("glTF bufferView references an unknown buffer")
    buffer = buffers[buffer_index]
    component_type = int(accessor.get("componentType", 5126))
    if component_type not in _COMPONENT_FORMATS:
        raise ValueError(f"unsupported glTF component type {component_type}")
    type_name = str(accessor.get("type", "SCALAR"))
    if type_name not in _TYPE_COUNTS:
        raise ValueError(f"unsupported glTF accessor type {type_name}")
    comp_format, comp_size = _COMPONENT_FORMATS[component_type]
    type_count = _TYPE_COUNTS[type_name]
    count = int(accessor.get("count", 0))
    if count < 0:
        raise ValueError("glTF accessor count must be non-negative")
    view_offset = int(view.get("byteOffset", 0))
    accessor_offset = int(accessor.get("byteOffset", 0))
    stride = int(view.get("byteStride", 0))
    if stride == 0:
        stride = comp_size * type_count
    if stride < comp_size * type_count:
        raise ValueError("glTF bufferView stride is too small")
    start = view_offset + accessor_offset
    result: list[Any] = []
    for i in range(count):
        offset = start + i * stride
        if offset + comp_size * type_count > len(buffer):
            raise ValueError("glTF accessor reads past the end of its buffer")
        values = list(struct.unpack_from(f"<{type_count}{comp_format}", buffer, offset))
        result.append(values[0] if type_count == 1 else tuple(values))
    return result