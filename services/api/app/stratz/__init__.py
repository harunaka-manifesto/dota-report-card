"""STRATZ-native provider for the independent V7 data path."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.providers.base import (
    CanonicalProfile,
    HistoryProvider,
    HistoryWindow,
    V7CanonicalHistory,
    V7CanonicalMatch,
)

from .client import (
    RateLimitSnapshot,
    StratzClient,
    parse_rate_limit_headers,
    stratz_cache_key,
)
from .models import (
    STRATZ_ENUM_VOCABULARY,
    STRATZ_PROVIDER,
    STRATZ_PROVIDER_SCHEMA_VERSION,
    StratzHistory,
    StratzHistoryPage,
    StratzMatch,
    StratzMatchCore,
    StratzMatchPlayer,
    StratzPlayerProfile,
)
from .normalize import (
    STRATZ_NORMALIZER_VERSION,
    normalize_stratz_history,
    normalize_stratz_match,
    normalize_stratz_page,
    normalize_stratz_profile,
)
from .queries import (
    GET_MATCH_CORE,
    GET_PARSED_MATCH_CORE,
    GET_PARSED_MATCHES_BATCH,
    GET_PLAYER_HISTORY_PAGE,
    GET_PLAYER_PROFILE,
    STRATZ_OPERATIONS,
    GraphQLOperation,
    get_operation,
)


class StratzProvider:
    """Adapt STRATZ transport/models to the V7 canonical boundary."""

    provider = STRATZ_PROVIDER

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: Any | None = None,
        cache: Any | None = None,
        client: StratzClient | None = None,
    ) -> None:
        self.client = client or StratzClient(
            settings,
            http_client=http_client,
            cache=cache,
        )

    async def __aenter__(self) -> StratzProvider:
        await self.client.__aenter__()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self.client.aclose()

    async def fetch_profile(self, account_id: int) -> CanonicalProfile:
        profile = await self.client.get_player_profile(account_id)
        return normalize_stratz_profile(profile)

    async def fetch_history(
        self,
        account_id: int,
        *,
        window: HistoryWindow | None = None,
    ) -> V7CanonicalHistory:
        history = await self.client.get_player_history(account_id, window=window)
        return normalize_stratz_history(history, account_id=account_id)

    async def fetch_match_core(
        self,
        match_id: int,
        *,
        account_id: int | None = None,
    ) -> V7CanonicalMatch:
        match = await self.client.get_match_core(match_id, account_id=account_id)
        return normalize_stratz_match(match, account_id=account_id)


__all__ = [
    "GET_MATCH_CORE",
    "GET_PARSED_MATCH_CORE",
    "GET_PARSED_MATCHES_BATCH",
    "GET_PLAYER_HISTORY_PAGE",
    "GET_PLAYER_PROFILE",
    "GraphQLOperation",
    "HistoryProvider",
    "HistoryWindow",
    "RateLimitSnapshot",
    "STRATZ_ENUM_VOCABULARY",
    "STRATZ_NORMALIZER_VERSION",
    "STRATZ_OPERATIONS",
    "STRATZ_PROVIDER",
    "STRATZ_PROVIDER_SCHEMA_VERSION",
    "StratzClient",
    "StratzHistory",
    "StratzHistoryPage",
    "StratzMatch",
    "StratzMatchCore",
    "StratzMatchPlayer",
    "StratzPlayerProfile",
    "StratzProvider",
    "V7CanonicalHistory",
    "V7CanonicalMatch",
    "get_operation",
    "normalize_stratz_history",
    "normalize_stratz_match",
    "normalize_stratz_page",
    "normalize_stratz_profile",
    "parse_rate_limit_headers",
    "stratz_cache_key",
]
