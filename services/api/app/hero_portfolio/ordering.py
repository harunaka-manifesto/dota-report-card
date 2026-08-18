"""Deterministic, position-unbiased ordering for Portfolio answer choices."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def stable_pseudo_shuffle(
    items: Iterable[T],
    *,
    seed: str,
    key: Callable[[T], str],
) -> tuple[T, ...]:
    """Order choices stably without exposing or depending on raw match IDs."""

    decorated = [
        (hashlib.sha256(f"{seed}|{key(item)}".encode()).hexdigest(), key(item), item)
        for item in items
    ]
    return tuple(item for _, _, item in sorted(decorated, key=lambda value: (value[0], value[1])))


__all__ = ["stable_pseudo_shuffle"]
