"""STRATZ-native provider for the independent V7 data path.

Note: this content used to live in ``app.stratz`` (``services/api/app/stratz/__init__.py``).
It moved here because ``StratzProvider`` and this package's aggregate re-exports
are only reachable from the legacy /v1 API composition root
(``report_card.providers.build_v7_provider``), never from ``app.tracker``.
The transport, models, GraphQL queries and fail-closed normalizer that the
fresh tracker path also depends on (``app.stratz.client``, ``app.stratz.models``,
``app.stratz.queries``, ``app.stratz.deep``, ``app.stratz.field_policy``) stay
in ``app.stratz``. ``normalize.py`` and ``item_vocabulary.py`` are legacy-only
and moved alongside this file.
"""

from __future__ import annotations

from typing import Any

from app.providers.base import (
    CanonicalProfile,
    HistoryProvider,
    HistoryWindow,
    V7CanonicalHistory,
    V7CanonicalMatch,
)
from app.stratz.client import (
    RateLimitSnapshot,
    StratzClient,
    parse_rate_limit_headers,
    stratz_cache_key,
)
from app.stratz.models import (
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
from app.stratz.queries import (
    GET_DEEP_MATCH_BATCH,
    GET_MATCH_CORE,
    GET_PARSED_ACQUISITION_BATCH,
    GET_PARSED_MATCH_CORE,
    GET_PARSED_MATCHES_BATCH,
    GET_PLAYER_HISTORY_PAGE,
    GET_PLAYER_PROFILE,
    GET_ROLE_METRIC_MATCH_BATCH,
    STRATZ_OPERATIONS,
    GraphQLOperation,
    get_operation,
)

from .normalize import (
    STRATZ_NORMALIZER_VERSION,
    normalize_stratz_history,
    normalize_stratz_match,
    normalize_stratz_page,
    normalize_stratz_profile,
)


class StratzProvider:
    """Adapt STRATZ transport/models to the V7 canonical boundary."""

    provider = STRATZ_PROVIDER

    def __init__(
        self,
        settings: Any,
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

    async def fetch_deep_matches(
        self, account_id: int, match_ids: list[int] | tuple[int, ...]
    ) -> list[dict[str, Any]]:
        return await self.client.get_deep_matches(account_id, match_ids)

    async def fetch_role_metric_matches(
        self, account_id: int, match_ids: list[int] | tuple[int, ...]
    ) -> list[dict[str, Any]]:
        return await self.client.get_role_metric_matches(account_id, match_ids)


__all__ = [
    "GET_DEEP_MATCH_BATCH",
    "GET_MATCH_CORE",
    "GET_PARSED_ACQUISITION_BATCH",
    "GET_PARSED_MATCH_CORE",
    "GET_PARSED_MATCHES_BATCH",
    "GET_PLAYER_HISTORY_PAGE",
    "GET_PLAYER_PROFILE",
    "GET_ROLE_METRIC_MATCH_BATCH",
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
