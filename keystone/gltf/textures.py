"""glTF image and texture decoding."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from keystone.texture import TextureData


def _image_bytes(
    image: Mapping[str, Any],
    buffers: list[bytes],
    buffer_views: list[Any],
    base_dir: Path,
) -> tuple[bytes, str]:
    if "uri" in image:
        uri = str(image["uri"])
        if uri.startswith("data:"):
            from keystone.gltf.io import decode_data_uri

            return decode_data_uri(uri), str(image.get("mimeType", ""))
        path = Path(uri)
        if not path.is_absolute():
            path = base_dir / path
        if not path.is_file():
            raise FileNotFoundError(f"glTF image file not found: {path}")
        return path.read_bytes(), str(image.get("mimeType", "")) or _mime_from_path(path)
    if "bufferView" in image:
        view_index = int(image["bufferView"])
        if view_index < 0 or view_index >= len(buffer_views):
            raise ValueError("glTF image references an unknown bufferView")
        view = buffer_views[view_index]
        if not isinstance(view, Mapping):
            raise TypeError("glTF bufferView must be an object")
        buffer_index = int(view.get("buffer", 0))
        if buffer_index < 0 or buffer_index >= len(buffers):
            raise ValueError("glTF image bufferView references an unknown buffer")
        buffer = buffers[buffer_index]
        offset = int(view.get("byteOffset", 0))
        length = int(view.get("byteLength", 0))
        if offset + length > len(buffer):
            raise ValueError("glTF image reads past the end of its buffer")
        return buffer[offset:offset + length], str(image.get("mimeType", ""))
    raise ValueError("glTF image must have a uri or bufferView")


def _mime_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    return ""


def _texture_from_bytes(data: bytes, mime_type: str, name: str) -> TextureData:
    if mime_type == "image/png" or data.startswith(b"\x89PNG\r\n\x1a\n"):
        return TextureData.from_png_bytes(data, name)
    raise ValueError("glTF only supports PNG images in this engine; JPEG images are not supported")


def load_textures(
    document: Mapping[str, Any],
    buffers: list[bytes],
    buffer_views: list[Any],
    base_dir: Path,
) -> list[TextureData]:
    images = document.get("images", [])
    if not isinstance(images, list):
        raise TypeError("glTF images must be a list")
    image_textures: list[TextureData | None] = [None] * len(images)
    for index, raw in enumerate(images):
        if not isinstance(raw, Mapping):
            raise TypeError(f"glTF image {index} must be an object")
        data, mime_type = _image_bytes(raw, buffers, buffer_views, base_dir)
        name = str(raw.get("name", f"image-{index}"))
        image_textures[index] = _texture_from_bytes(data, mime_type, name)

    raw_textures = document.get("textures", [])
    if not isinstance(raw_textures, list):
        raise TypeError("glTF textures must be a list")
    textures: list[TextureData] = []
    for index, raw in enumerate(raw_textures):
        if not isinstance(raw, Mapping):
            raise TypeError(f"glTF texture {index} must be an object")
        source = raw.get("source")
        if source is None:
            textures.append(TextureData.checker(8, name=f"texture-{index}"))
            continue
        source_index = int(source)
        if source_index < 0 or source_index >= len(image_textures):
            raise ValueError(f"glTF texture {index} references an unknown image")
        image_texture = image_textures[source_index]
        if image_texture is None:
            raise ValueError(f"glTF texture {index} has no decoded image")
        textures.append(image_texture)
    return textures