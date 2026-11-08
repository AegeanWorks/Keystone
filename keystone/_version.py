"""The single source of truth for the engine version.

``pyproject.toml`` carries the same literal because a build backend cannot
import the package before it is built; ``tests/test_version.py`` fails when the
two drift, so there is exactly one value to edit.
"""

from __future__ import annotations

__version__ = "0.45.0"
