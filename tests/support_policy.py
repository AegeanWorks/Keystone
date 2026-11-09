"""A tiny external policy used to prove --policy accepts module factories."""

from __future__ import annotations

from keystone.input import ActionState
from keystone.playtest import RandomPolicy


class SupportPolicy(RandomPolicy):
    """A named random policy registered from outside the engine."""

    name = "support-policy"


def make_policy() -> SupportPolicy:
    """Factory form, matching the ``module:Factory`` spec."""
    return SupportPolicy()


__all__ = ["ActionState", "SupportPolicy", "make_policy"]
