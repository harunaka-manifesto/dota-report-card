from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any


def payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: datetime | None
    immutable: bool = False


class MemoryCache:
    """Small local cache with the same semantics used by the production adapter."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._values: dict[str, CacheEntry] = {}
        self._lock = RLock()
        self._clock = clock or (lambda: datetime.now(UTC))

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._values.get(key)
            if entry is None:
                return None
            if entry.expires_at and entry.expires_at <= self._clock():
                self._values.pop(key, None)
                return None
            return entry.value

    def set(
        self, key: str, value: Any, ttl_seconds: int | None = None, *, immutable: bool = False
    ) -> None:
        expires_at = (
            self._clock() + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
        )
        with self._lock:
            self._values[key] = CacheEntry(value, expires_at, immutable)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()
