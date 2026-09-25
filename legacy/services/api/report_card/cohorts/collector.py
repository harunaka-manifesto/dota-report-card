from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CollectorPolicy:
    batch_size: int = 100
    max_requests_per_minute: int = 30
    minimum_rank: int | None = None
    maximum_rank: int | None = None


class PublicMatchCollector:
    """Quota-aware boundary for future warehouse population.

    The collector deliberately accepts an injected client and never submits replay
    parse requests. Persisting its rows is left to the storage adapter.
    """

    def __init__(self, client: Any, policy: CollectorPolicy | None = None) -> None:
        self.client = client
        self.policy = policy or CollectorPolicy()
        self._request_times: list[float] = []
        self._quota_lock = asyncio.Lock()

    async def collect_page(self, *, less_than_match_id: int | None = None) -> list[dict[str, Any]]:
        await self._wait_for_quota()
        rows = await self.client.get_public_matches(
            limit=self.policy.batch_size,
            less_than_match_id=less_than_match_id,
            min_rank=self.policy.minimum_rank,
            max_rank=self.policy.maximum_rank,
        )
        return list(rows or [])[: self.policy.batch_size]

    async def _wait_for_quota(self) -> None:
        window_seconds = 60.0
        max_requests = max(1, self.policy.max_requests_per_minute)
        async with self._quota_lock:
            while True:
                now = time.monotonic()
                self._request_times = [
                    timestamp
                    for timestamp in self._request_times
                    if now - timestamp < window_seconds
                ]
                if len(self._request_times) < max_requests:
                    self._request_times.append(now)
                    return
                await asyncio.sleep(window_seconds - (now - self._request_times[0]))
