from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, cast

import httpx

from app.core.config import FREE_HISTORY_LIMIT, FREE_HISTORY_WINDOW_DAYS, Settings, get_settings
from app.core.errors import OpenDotaRateLimited, OpenDotaUnavailable, ProfileUnavailable
from app.core.metrics import record_metric
from app.core.security import safe_endpoint
from app.opendota.cache import CacheBackend, MemoryCache, RedisCache

logger = logging.getLogger(__name__)
Sleep = Callable[[float], Awaitable[None]]
MATCH_HISTORY_PAGE_SIZE = 200
MAX_MATCH_HISTORY_PAGES = 50


class OpenDotaClient:
    """Authenticated server-side OpenDota client.

    The API key is deliberately only materialized in request headers. The client has
    no method for the replay parse endpoint, which keeps the v1 no-auto-parse rule
    enforceable at the transport boundary.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
        cache: CacheBackend | None = None,
        sleep: Sleep = asyncio.sleep,
        rng: Callable[[], float] = random.random,
    ) -> None:
        self.settings = settings or get_settings()
        self._http = http_client
        self._owns_http = http_client is None
        self.cache = cache or (
            RedisCache(self.settings.redis_url, prefix="dota:opendota")
            if self.settings.app_env == "production"
            else MemoryCache()
        )
        self._sleep = sleep
        self._rng = rng
        self._inflight: dict[str, asyncio.Task[Any]] = {}
        self.request_counts: dict[str, int] = {}
        self.cache_hits = 0

    async def __aenter__(self) -> OpenDotaClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.opendota_timeout_seconds)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None

    @property
    def auth_headers(self) -> dict[str, str]:
        if not self.settings.opendota_api_key:
            return {}
        return {"Authorization": f"Bearer {self.settings.opendota_api_key}"}

    async def _request_json(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
        immutable: bool = False,
    ) -> Any:
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.cache_hits += 1
                record_metric("opendota.cache.hit", tags={"key": cache_key.split(":", 1)[0]})
                return cached
            inflight = self._inflight.get(cache_key)
            if inflight is not None:
                record_metric("opendota.cache.singleflight", tags={"key": cache_key.split(":", 1)[0]})
                return await asyncio.shield(inflight)
            inflight = asyncio.create_task(
                self._request_json_uncached(
                    endpoint,
                    params=cast(Any, params),
                    cache_key=cache_key,
                    cache_ttl=cache_ttl,
                    immutable=immutable,
                )
            )
            self._inflight[cache_key] = inflight
            def clear_inflight(completed: asyncio.Task[Any]) -> None:
                if self._inflight.get(cache_key) is inflight:
                    self._inflight.pop(cache_key, None)

            inflight.add_done_callback(clear_inflight)
            return await asyncio.shield(inflight)
        return await self._request_json_uncached(
            endpoint,
            params=params,
            cache_key=cache_key,
            cache_ttl=cache_ttl,
            immutable=immutable,
        )

    async def _request_json_uncached(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
        immutable: bool = False,
    ) -> Any:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.opendota_timeout_seconds)

        url = f"{self.settings.opendota_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        retries = max(0, self.settings.opendota_max_retries)
        for attempt in range(retries + 1):
            record_metric("opendota.request.attempt", tags={"endpoint": safe_endpoint(endpoint)})
            try:
                response = await self._http.get(
                    url,
                    params=cast(Any, params),
                    headers=self.auth_headers,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                record_metric("opendota.request.error", tags={"endpoint": safe_endpoint(endpoint), "kind": type(exc).__name__})
                if attempt >= retries:
                    raise OpenDotaUnavailable("OpenDota is unavailable") from exc
                await self._backoff(attempt)
                continue

            if response.status_code == 429:
                record_metric("opendota.response", tags={"endpoint": safe_endpoint(endpoint), "status": 429})
                if attempt >= retries:
                    raise OpenDotaRateLimited("OpenDota rate limit reached")
                await self._backoff(attempt, retry_after=response.headers.get("Retry-After"))
                continue
            if response.status_code >= 500:
                record_metric("opendota.response", tags={"endpoint": safe_endpoint(endpoint), "status": response.status_code})
                if attempt >= retries:
                    raise OpenDotaUnavailable("OpenDota is unavailable")
                await self._backoff(attempt)
                continue
            if response.status_code == 404:
                record_metric("opendota.response", tags={"endpoint": safe_endpoint(endpoint), "status": 404})
                raise ProfileUnavailable("OpenDota resource was not found")
            if response.status_code >= 400:
                record_metric("opendota.response", tags={"endpoint": safe_endpoint(endpoint), "status": response.status_code})
                raise OpenDotaUnavailable("OpenDota rejected the request")

            try:
                value = response.json()
            except ValueError as exc:
                raise OpenDotaUnavailable("OpenDota returned invalid JSON") from exc
            if cache_key:
                self.cache.set(cache_key, value, cache_ttl, immutable=immutable)
            record_metric("opendota.response", tags={"endpoint": safe_endpoint(endpoint), "status": response.status_code, "cache": "miss"})
            self.request_counts[endpoint] = self.request_counts.get(endpoint, 0) + 1
            logger.info(
                "opendota_request endpoint=%s status=%s",
                safe_endpoint(endpoint),
                response.status_code,
            )
            return value

        raise OpenDotaUnavailable("OpenDota request failed")

    async def _backoff(self, attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                delay = min(float(retry_after), 30.0)
            except ValueError:
                delay = 0.0
        else:
            delay = min(2**attempt, 30) + self._rng() * 0.25
        await self._sleep(delay)

    async def get_player(self, account_id: int) -> dict[str, Any]:
        return await self._request_json(
            f"/players/{account_id}",
            cache_key=f"player:{account_id}",
            cache_ttl=300,
        )

    async def get_matches(
        self,
        account_id: int,
        *,
        limit: int | None = FREE_HISTORY_LIMIT,
        days: int = FREE_HISTORY_WINDOW_DAYS,
        project: str | Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        configured_limit = self.settings.effective_free_history_limit
        effective_limit = limit if limit is not None else configured_limit
        if configured_limit is not None and effective_limit is not None:
            effective_limit = min(effective_limit, configured_limit)
        projects = (
            tuple(value for value in project if value)
            if project is not None and not isinstance(project, str)
            else ((project,) if project else ())
        )
        days_value = max(1, int(days))
        rows: list[dict[str, Any]] = []
        seen_match_ids: set[int] = set()
        offset = 0
        for _page_number in range(MAX_MATCH_HISTORY_PAGES):
            remaining = (
                None if effective_limit is None else max(0, effective_limit - len(rows))
            )
            if remaining == 0:
                break
            page_limit = min(MATCH_HISTORY_PAGE_SIZE, remaining or MATCH_HISTORY_PAGE_SIZE)
            params: list[tuple[str, Any]] = [
                ("date", days_value),
                ("limit", page_limit),
            ]
            if offset:
                params.append(("offset", offset))
            params.extend(("project", value) for value in projects)
            value = await self._request_json(
                f"/players/{account_id}/matches",
                params=params,
                cache_key=(
                    f"matches:{account_id}:{days_value}:{page_limit}:{offset}:"
                    f"{','.join(projects)}"
                ),
                cache_ttl=120,
            )
            page = [row for row in list(value or []) if isinstance(row, dict)]
            if not page:
                break
            added = 0
            for row in page:
                match_id = row.get("match_id")
                if isinstance(match_id, int):
                    if match_id in seen_match_ids:
                        continue
                    seen_match_ids.add(match_id)
                rows.append(row)
                added += 1
            if effective_limit is not None and len(rows) >= effective_limit:
                break
            if len(page) != page_limit or added == 0:
                break
            offset += page_limit
        else:
            raise OpenDotaUnavailable("OpenDota match history exceeded the pagination safety limit")
        return rows if effective_limit is None else rows[:effective_limit]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        return await self._request_json(
            f"/matches/{match_id}",
            cache_key=f"match:{match_id}",
            cache_ttl=None,
            immutable=True,
        )

    async def get_constants(self, resource: str) -> Any:
        if not resource or "/" in resource or "?" in resource:
            raise ValueError("Invalid constants resource")
        return await self._request_json(
            f"/constants/{resource}",
            cache_key=f"constants:{resource}",
            cache_ttl=None,
            immutable=True,
        )

    async def get_hero_stats(self) -> list[dict[str, Any]]:
        return list(
            await self._request_json(
                "/heroStats",
                cache_key="hero_stats",
                cache_ttl=3600,
                immutable=True,
            )
            or []
        )

    async def get_benchmarks(self, hero_id: int) -> dict[str, Any]:
        return dict(
            await self._request_json(
                "/benchmarks",
                params={"hero_id": hero_id},
                cache_key=f"benchmarks:{hero_id}",
                cache_ttl=3600,
                immutable=True,
            )
            or {}
        )

    async def get_public_matches(
        self,
        *,
        limit: int = 100,
        less_than_match_id: int | None = None,
        min_rank: int | None = None,
        max_rank: int | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            key: value
            for key, value in {
                "less_than_match_id": less_than_match_id,
                "min_rank": min_rank,
                "max_rank": max_rank,
                "limit": limit,
            }.items()
            if value is not None
        }
        return list(await self._request_json("/publicMatches", params=params) or [])[:limit]
