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
_NORMALIZE_DIVISORS = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}
_SIGNED_COMPONENTS = (5120, 5122)

_GLB_MAGIC = b"glTF"
_GLB_JSON_CHUNK = 0x4E4F534A
_GLB_BIN_CHUNK = 0x004E4942


def _decode_glb(data: bytes) -> tuple[bytes, bytes | None]:
    if len(data) < 12:
        raise ValueError("glTF GLB header is truncated")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != _GLB_MAGIC:
        raise ValueError("glTF GLB magic is invalid")
    if version != 2:
        raise ValueError(f"glTF GLB version must be 2, got {version}")
    if length < 12 or length > len(data):
        raise ValueError("glTF GLB declared length is invalid")
    offset = 12
    json_chunk: bytes | None = None
    binary_chunk: bytes | None = None
    while offset < length:
        if offset + 8 > length:
            raise ValueError("glTF GLB chunk header is truncated")
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        end = offset + chunk_length
        if end > length:
            raise ValueError("glTF GLB chunk reads past the container length")
        if chunk_type == _GLB_JSON_CHUNK:
            if json_chunk is not None:
                raise ValueError("glTF GLB contains more than one JSON chunk")
            json_chunk = data[offset:end]
        elif chunk_type == _GLB_BIN_CHUNK and binary_chunk is None:
            binary_chunk = data[offset:end]
        offset = end
    if json_chunk is None:
        raise ValueError("glTF GLB is missing its JSON chunk")
    return json_chunk, binary_chunk


def _decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("glTF source must be UTF-8 JSON or a GLB container") from exc


def read_source(source: object) -> tuple[str, Path, bytes | None]:
    """Return (json text, base directory, GLB binary chunk) for a source."""
    if isinstance(source, Mapping):
        return json.dumps(source), Path.cwd(), None
    if isinstance(source, (bytes, bytearray)):
        data = bytes(source)
        if data.startswith(_GLB_MAGIC):
            json_data, binary_chunk = _decode_glb(data)
            return _decode_text(json_data), Path.cwd(), binary_chunk
        return _decode_text(data), Path.cwd(), None
    if isinstance(source, Path):
        path = source
    elif isinstance(source, str):
        path = Path(source)
        if not path.exists():
            return source, Path.cwd(), None
    else:
        raise TypeError("glTF source must be a path, JSON text or bytes")
    if not path.is_file():
        raise FileNotFoundError(f"glTF file not found: {path}")
    data = path.read_bytes()
    if data.startswith(_GLB_MAGIC):
        json_data, binary_chunk = _decode_glb(data)
        return _decode_text(json_data), path.parent, binary_chunk
    return _decode_text(data), path.parent, None


def decode_data_uri(uri: str) -> bytes:
    match = re.match(r"data:([^;]*);base64,(.*)", uri, re.DOTALL)
    if match is None:
        raise ValueError("glTF data URI must be base64 encoded")
    return base64.b64decode(match.group(2))


def load_buffers(
    document: Mapping[str, Any],
    base_dir: Path,
    binary_chunk: bytes | None = None,
) -> list[bytes]:
    raw_buffers = document.get("buffers", [])
    if not isinstance(raw_buffers, list):
        raise TypeError("glTF buffers must be a list")
    buffers: list[bytes] = []
    binary_used = False
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
            continue
        if binary_chunk is None:
            raise ValueError(
                f"glTF buffer {index} has no uri and no GLB binary chunk"
            )
        if binary_used or index != 0:
            raise ValueError("only the first glTF buffer may use the GLB binary chunk")
        length = int(raw.get("byteLength", 0))
        if length < 0 or length > len(binary_chunk):
            raise ValueError("glTF buffer byteLength exceeds the GLB binary chunk")
        buffers.append(binary_chunk[:length])
        binary_used = True
    return buffers


def read_accessor(
    accessor: Mapping[str, Any],
    buffer_views: list[Any],
    buffers: list[bytes],
) -> list[Any]:
    if not isinstance(accessor, Mapping):
        raise TypeError("glTF accessor must be an object")
    if "sparse" in accessor:
        raise ValueError("glTF sparse accessors are not supported")
    count = int(accessor.get("count", 0))
    if count < 0:
        raise ValueError("glTF accessor count must be non-negative")
    if "bufferView" not in accessor:
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
    normalized = bool(accessor.get("normalized", False))
    if normalized and component_type not in _NORMALIZE_DIVISORS:
        raise ValueError(
            f"glTF accessor component type {component_type} cannot be normalized"
        )
    normalize_divisor = _NORMALIZE_DIVISORS.get(component_type) if normalized else None
    count = int(accessor.get("count", 0))
    if count < 0:
        raise ValueError("glTF accessor count must be non-negative")
    view_offset = int(view.get("byteOffset", 0))
    accessor_offset = int(accessor.get("byteOffset", 0))
    if view_offset < 0 or accessor_offset < 0:
        raise ValueError("glTF bufferView and accessor offsets must be non-negative")
    view_length = int(view.get("byteLength", len(buffer) - view_offset))
    if view_length < 0:
        raise ValueError("glTF bufferView byteLength must be non-negative")
    view_end = view_offset + view_length
    if view_end > len(buffer):
        raise ValueError("glTF bufferView reads past the end of its buffer")
    stride = int(view.get("byteStride", 0))
    if stride == 0:
        stride = comp_size * type_count
    if stride < comp_size * type_count:
        raise ValueError("glTF bufferView stride is too small")
    start = view_offset + accessor_offset
    result: list[Any] = []
    for i in range(count):
        offset = start + i * stride
        if offset < view_offset or offset + comp_size * type_count > view_end:
            raise ValueError("glTF accessor reads outside its bufferView")
        values = list(struct.unpack_from(f"<{type_count}{comp_format}", buffer, offset))
        if normalize_divisor is not None:
            if component_type in _SIGNED_COMPONENTS:
                values = [max(-1.0, value / normalize_divisor) for value in values]
            else:
                values = [value / normalize_divisor for value in values]
        result.append(values[0] if type_count == 1 else tuple(values))
    return result
