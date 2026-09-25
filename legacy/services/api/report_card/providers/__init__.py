"""Provider selection for the isolated V7 path.

The existing analysis service intentionally keeps its OpenDota source seam.
``V7RuntimeService`` consumes the provider returned here.

Note: this content used to live in ``app.providers`` (``services/api/app/providers/__init__.py``).
It moved here because it is only reachable from the legacy /v1 API composition
root (``app.main``), not from ``app.tracker``. ``app.providers.base`` (the
shared canonical-provider protocol/dataclasses that ``app.stratz`` also
depends on) stays in ``app``.
"""

from __future__ import annotations

from typing import Any

from app.providers.base import (
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
        from report_card.stratz import StratzProvider

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
