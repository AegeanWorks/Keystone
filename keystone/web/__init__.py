"""Local web console and JSON API for Keystone."""

from __future__ import annotations

from keystone.web.schema import SCENE_SCHEMA, WEB_API_VERSION

__all__ = ["SCENE_SCHEMA", "WEB_API_VERSION", "create_server", "scene_document", "serve"]


def __getattr__(name: str):
    if name == "scene_document":
        from keystone.web.scene import scene_document

        return scene_document
    if name in ("create_server", "serve"):
        from keystone.web.server import create_server, serve

        return {"create_server": create_server, "serve": serve}[name]
    raise AttributeError(f"module 'keystone.web' has no attribute '{name}'")
