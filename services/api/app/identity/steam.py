from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

import httpx

from app.core.errors import InvalidPlayerIdentifier, SteamIdentityUnavailable

if TYPE_CHECKING:
    from app.opendota.cache import CacheBackend

STEAM64_OFFSET = 76561197960265728
STEAM_VANITY_CACHE_SECONDS = 30 * 24 * 60 * 60


class SteamVanityResolver(Protocol):
    async def resolve(self, vanity: str) -> int: ...


def steam64_to_account_id(value: int | str) -> int:
    """Convert a numeric Steam64 ID to the OpenDota/Steam32 account ID."""

    try:
        steam64 = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidPlayerIdentifier("Steam64 ID must be numeric") from exc
    account_id = steam64 - STEAM64_OFFSET
    if account_id <= 0 or account_id > 2**32 - 1:
        raise InvalidPlayerIdentifier("Steam64 ID is out of range")
    return account_id


@dataclass(slots=True)
class _CacheEntry:
    account_id: int
    expires_at: float


class SteamWebResolver:
    """Small, cache-first Steam vanity resolver.

    Vanity resolution is intentionally separate from OpenDota history reads.
    It is only constructed in deployments that provide a Steam Web API key.
    """

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = "https://api.steampowered.com",
        http_client: httpx.AsyncClient | None = None,
        cache_ttl_seconds: int = STEAM_VANITY_CACHE_SECONDS,
        cache: CacheBackend | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._http = http_client
        self._owns_http = http_client is None
        self.cache_ttl_seconds = max(60, cache_ttl_seconds)
        self._shared_cache = cache
        self._cache: dict[str, _CacheEntry] = {}
        self._inflight: dict[str, asyncio.Task[int]] = {}

    async def resolve(self, vanity: str) -> int:
        key = _validate_vanity(vanity)
        if self._shared_cache is not None:
            shared = self._shared_cache.get(f"vanity:{key}")
            if isinstance(shared, int) and shared > 0:
                return shared
        cached = self._cache.get(key)
        now = asyncio.get_running_loop().time()
        if cached and cached.expires_at > now:
            return cached.account_id
        if not self.api_key:
            raise SteamIdentityUnavailable(
                "Steam vanity URLs require STEAM_API_KEY configuration"
            )
        pending = self._inflight.get(key)
        if pending is not None:
            return await asyncio.shield(pending)
        pending = asyncio.create_task(self._resolve_uncached(key))
        self._inflight[key] = pending
        try:
            return await asyncio.shield(pending)
        finally:
            if self._inflight.get(key) is pending:
                self._inflight.pop(key, None)

    async def _resolve_uncached(self, vanity: str) -> int:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=10.0)
        try:
            response = await self._http.get(
                f"{self.base_url}/ISteamUser/ResolveVanityURL/v1/",
                params={"key": self.api_key, "vanityurl": vanity, "format": "json"},
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise SteamIdentityUnavailable("Steam identity service is unavailable") from exc
        if response.status_code >= 500 or response.status_code == 429:
            raise SteamIdentityUnavailable("Steam identity service is unavailable")
        if response.status_code >= 400:
            raise InvalidPlayerIdentifier("Steam vanity URL could not be resolved")
        try:
            value = response.json()
        except ValueError as exc:
            raise SteamIdentityUnavailable("Steam identity service returned invalid JSON") from exc
        account_id = _account_id_from_response(value)
        if account_id is None:
            raise InvalidPlayerIdentifier("Steam vanity URL could not be resolved")
        self._cache[vanity] = _CacheEntry(
            account_id=account_id,
            expires_at=asyncio.get_running_loop().time() + self.cache_ttl_seconds,
        )
        if self._shared_cache is not None:
            self._shared_cache.set(
                f"vanity:{vanity}", account_id, ttl_seconds=self.cache_ttl_seconds
            )
        return account_id

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None


def _validate_vanity(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized or len(normalized) > 64 or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for character in normalized
    ):
        raise InvalidPlayerIdentifier("Steam vanity URL contains an unsupported name")
    return normalized.lower()


def _account_id_from_response(value: Any) -> int | None:
    if not isinstance(value, Mapping):
        return None
    response = value.get("response")
    if not isinstance(response, Mapping):
        return None
    success = response.get("success")
    if success not in (1, "1", True):
        return None
    raw = response.get("steamid")
    if raw is None:
        return None
    try:
        return steam64_to_account_id(raw)
    except InvalidPlayerIdentifier:
        return None
