"""Small provider-neutral metrics seam for tests and production adapters."""

from __future__ import annotations

from collections.abc import Mapping
from threading import RLock


class Metrics:
    def __init__(self) -> None:
        self._lock = RLock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

    def record_metric(
        self,
        name: str,
        value: int | float = 1,
        *,
        tags: Mapping[str, object] | None = None,
    ) -> None:
        normalized = tuple(sorted((str(key), str(item)) for key, item in (tags or {}).items()))
        with self._lock:
            key = (name, normalized)
            self._counters[key] = self._counters.get(key, 0.0) + float(value)

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            return {
                f"{name}|" + ",".join(f"{key}={value}" for key, value in tags): float(count)
                for (name, tags), count in self._counters.items()
            }

    def clear(self) -> None:
        with self._lock:
            self._counters.clear()


metrics = Metrics()


def record_metric(
    name: str,
    value: int | float = 1,
    *,
    tags: Mapping[str, object] | None = None,
) -> None:
    metrics.record_metric(name, value, tags=tags)
