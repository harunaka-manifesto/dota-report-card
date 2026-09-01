"""Provider selection for the isolated V7 path.

The existing analysis service intentionally keeps its OpenDota source seam.
Only a future V7 assembler should consume the provider returned here.
"""

from __future__ import annotations

from typing import Any

from .base import (
    CanonicalProfile,
    HistoryProvider,
    HistoryWindow,
    ProviderHistory,
    ProviderProvenance,
    RequestLedger,
    V7CanonicalHistory,
    V7CanonicalMatch,
    canonical_json_sha256,
    provider_cache_key,
)


def build_v7_provider(
    settings: Any,
    *,
    http_client: Any | None = None,
    cache: Any | None = None,
) -> HistoryProvider | None:
    """Return the explicitly selected V7 provider.

    ``opendota`` returns ``None`` because the existing OpenDota source is the
    legacy V6/V6.1 runtime path, not a V7 canonical adapter.
    """

    if settings.data_provider == "stratz":
        from app.stratz import StratzProvider

        return StratzProvider(settings, http_client=http_client, cache=cache)
    return None


select_v7_provider = build_v7_provider


__all__ = [
    "CanonicalProfile",
    "HistoryProvider",
    "HistoryWindow",
    "ProviderProvenance",
    "ProviderHistory",
    "RequestLedger",
    "V7CanonicalHistory",
    "V7CanonicalMatch",
    "build_v7_provider",
    "canonical_json_sha256",
    "provider_cache_key",
    "select_v7_provider",
]
