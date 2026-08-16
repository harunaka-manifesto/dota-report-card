from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any, Protocol


def payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: datetime | None
    immutable: bool = False


class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(
        self, key: str, value: Any, ttl_seconds: int | None = None, *, immutable: bool = False
    ) -> None: ...


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


class RedisCache:
    """Best-effort shared cache for production replicas.

    Cache outages must never turn a report request into an application outage;
    callers simply fall back to the upstream request when Redis is unavailable.
    The prefix keeps OpenDota, Steam, and any future cache users isolated.
    """

    def __init__(
        self,
        url: str,
        *,
        prefix: str,
        socket_timeout_seconds: float = 0.25,
    ) -> None:
        import redis

        self.prefix = prefix.rstrip(":")
        self._client: Any = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=socket_timeout_seconds,
            socket_timeout=socket_timeout_seconds,
        )

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Any | None:
        try:
            value = self._client.get(self._key(key))
        except Exception:
            return None
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None

    def set(
        self, key: str, value: Any, ttl_seconds: int | None = None, *, immutable: bool = False
    ) -> None:
        del immutable  # Redis TTL is controlled explicitly by the caller.
        try:
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
            if ttl_seconds is None:
                self._client.set(self._key(key), encoded)
            else:
                self._client.set(self._key(key), encoded, ex=max(1, int(ttl_seconds)))
        except Exception:
            return

    def clear(self) -> None:
        try:
            keys = list(self._client.scan_iter(match=f"{self.prefix}:*"))
            if keys:
                self._client.delete(*keys)
        except Exception:
            return
