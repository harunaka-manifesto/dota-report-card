"""Bounded HTTP client shared by the official and website adapters."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from .cache import DiskCache
from .config import Settings, isoformat
from .errors import FetchError


@dataclass(frozen=True, slots=True)
class ResponsePayload:
    url: str
    params: dict[str, Any]
    status_code: int
    headers: dict[str, str]
    body: str
    fetched_at: str
    cache_hit: bool = False

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()

    def json(self) -> Any:
        return json.loads(self.body)


class _RateLimiter:
    def __init__(self, minimum_delay: float, sleeper: Callable[[float], None]) -> None:
        self.minimum_delay = minimum_delay
        self.sleeper = sleeper
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        if self.minimum_delay <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_allowed - now)
            self._next_allowed = max(now, self._next_allowed) + self.minimum_delay
        if delay:
            self.sleeper(delay)


class SourceHttpClient:
    """HTTP client with cache, user-agent, pacing, and finite retries."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        self.settings = settings
        self.cache = DiskCache(settings.cache_root, enabled=settings.cache_enabled)
        self.limiter = _RateLimiter(settings.min_delay_seconds, sleeper)
        self.sleeper = sleeper
        headers = {
            "User-Agent": settings.user_agent,
            "Accept": "application/json, text/html;q=0.9",
        }
        headers.update({str(key): str(value) for key, value in (extra_headers or {}).items()})
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=settings.timeout_seconds,
            headers=headers,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SourceHttpClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def request(
        self, url: str, params: dict[str, Any] | None = None, *, force_refresh: bool = False
    ) -> ResponsePayload:
        query = {str(key): value for key, value in (params or {}).items()}
        if not force_refresh:
            cached = self.cache.get(url, query)
            if cached is not None:
                return ResponsePayload(
                    url=cached.url,
                    params=cached.params,
                    status_code=cached.status_code,
                    headers=cached.headers,
                    body=cached.body,
                    fetched_at=cached.fetched_at,
                    cache_hit=True,
                )

        transient_statuses = {429, 500, 502, 503, 504}
        attempts = self.settings.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            self.limiter.wait()
            try:
                response = self._client.get(url, params=query)
                if response.status_code in transient_statuses and attempt + 1 < attempts:
                    self.sleeper(min(8.0, 0.5 * (2**attempt)))
                    continue
                response.raise_for_status()
                fetched_at = isoformat()
                headers = {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower() in {"content-type", "etag", "last-modified", "date"}
                }
                body = response.text
                self.cache.put(
                    url,
                    query,
                    status_code=response.status_code,
                    headers=headers,
                    body=body,
                    fetched_at=fetched_at,
                )
                return ResponsePayload(
                    url=url,
                    params=query,
                    status_code=response.status_code,
                    headers=headers,
                    body=body,
                    fetched_at=fetched_at,
                )
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                status = (
                    exc.response.status_code
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response
                    else None
                )
                retryable = (
                    isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))
                    or status in transient_statuses
                )
                if not retryable or attempt + 1 >= attempts:
                    break
                self.sleeper(min(8.0, 0.5 * (2**attempt)))
        raise FetchError(
            f"GET {url} failed after {attempts} attempt(s): {last_error}"
        ) from last_error

    def get_json(
        self, url: str, params: dict[str, Any] | None = None, *, force_refresh: bool = False
    ) -> ResponsePayload:
        response = self.request(url, params, force_refresh=force_refresh)
        try:
            response.json()
        except ValueError as exc:
            raise FetchError(f"GET {url} returned invalid JSON") from exc
        return response

    def get_text(
        self, url: str, params: dict[str, Any] | None = None, *, force_refresh: bool = False
    ) -> ResponsePayload:
        return self.request(url, params, force_refresh=force_refresh)
