"""Provider-neutral contracts for the independent V7 data path."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

ProviderName = Literal["opendota", "stratz"]
HistoryCompleteness = Literal["complete", "truncated"]


@dataclass(frozen=True, slots=True)
class HistoryWindow:
    """Inclusive Unix-second bounds for a bounded provider history read."""

    start_timestamp: int
    end_timestamp: int
    days: int = 365

    @classmethod
    def for_days(cls, days: int = 365, *, end_timestamp: int | None = None) -> HistoryWindow:
        bounded_days = max(1, int(days))
        end = int(end_timestamp if end_timestamp is not None else datetime.now(UTC).timestamp())
        return cls(end - bounded_days * 24 * 60 * 60, end, bounded_days)

    @property
    def start(self) -> int:
        return self.start_timestamp

    @property
    def end(self) -> int:
        return self.end_timestamp

    def as_dict(self) -> dict[str, int]:
        return {
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "days": self.days,
        }


@dataclass(slots=True)
class RequestLedger:
    """Physical request accounting kept separate from analytical features."""

    request_count: int = 0
    success_count: int = 0
    retry_count: int = 0
    page_count: int = 0
    cache_hits: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    operation_counts: dict[str, int] = field(default_factory=dict)

    def record_attempt(self, operation_name: str, status_code: int | None = None) -> None:
        self.request_count += 1
        self.operation_counts[operation_name] = self.operation_counts.get(operation_name, 0) + 1
        if status_code is not None:
            status = str(status_code)
            self.status_counts[status] = self.status_counts.get(status, 0) + 1

    def record_success(self) -> None:
        self.success_count += 1

    def record_retry(self) -> None:
        self.retry_count += 1

    def record_page(self) -> None:
        self.page_count += 1

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count,
            "success_count": self.success_count,
            "retry_count": self.retry_count,
            "page_count": self.page_count,
            "cache_hits": self.cache_hits,
            "status_counts": dict(self.status_counts),
            "operation_counts": dict(self.operation_counts),
        }


@dataclass(frozen=True, slots=True)
class ProviderProvenance:
    provider: str
    provider_schema_version: str
    operation_name: str
    operation_version: str
    document_sha256: str
    normalizer_version: str
    request_count: int
    page_count: int
    fetched_at: str
    raw_payload_sha256: str
    completeness: HistoryCompleteness
    parsed_coverage: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_schema_version": self.provider_schema_version,
            "operation_name": self.operation_name,
            "operation_version": self.operation_version,
            "document_sha256": self.document_sha256,
            "normalizer_version": self.normalizer_version,
            "request_count": self.request_count,
            "page_count": self.page_count,
            "fetched_at": self.fetched_at,
            "raw_payload_sha256": self.raw_payload_sha256,
            "completeness": self.completeness,
            "parsed_coverage": self.parsed_coverage,
        }


@dataclass(frozen=True, slots=True)
class CanonicalProfile:
    provider: str
    provider_schema_version: str
    account_id: int
    display_name: str | None
    avatar_url: str | None
    is_anonymous: bool | None
    is_public: bool | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_schema_version": self.provider_schema_version,
            "account_id": self.account_id,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "is_anonymous": self.is_anonymous,
            "is_public": self.is_public,
        }


@dataclass(frozen=True, slots=True)
class V7CanonicalMatch:
    """Provider-neutral V7 input; native enum values remain unmodified."""

    provider: str
    provider_schema_version: str
    match_id: int
    hero_id: int | None
    started_at: int | None
    duration_seconds: int | None
    side: Literal["radiant", "dire"] | None
    won: bool | None
    kills: int | None
    deaths: int | None
    assists: int | None
    game_version_id: int | None
    position: str | None
    role: str | None
    lane: str | None
    game_mode_native: str | None
    lobby_native: str | None
    leaver_status_native: str | None
    is_parsed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_schema_version": self.provider_schema_version,
            "match_id": self.match_id,
            "hero_id": self.hero_id,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "side": self.side,
            "won": self.won,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "game_version_id": self.game_version_id,
            "position": self.position,
            "role": self.role,
            "lane": self.lane,
            "game_mode_native": self.game_mode_native,
            "lobby_native": self.lobby_native,
            "leaver_status_native": self.leaver_status_native,
            "is_parsed": self.is_parsed,
        }


@dataclass(frozen=True, slots=True)
class V7CanonicalHistory:
    profile: CanonicalProfile
    window: HistoryWindow
    matches: tuple[V7CanonicalMatch, ...]
    provenance: ProviderProvenance
    duplicate_match_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.as_dict(),
            "window": self.window.as_dict(),
            "matches": [match.as_dict() for match in self.matches],
            "provenance": self.provenance.as_dict(),
            "duplicate_match_count": self.duplicate_match_count,
        }


class HistoryProvider(Protocol):
    provider: str

    async def aclose(self) -> None: ...

    async def fetch_profile(self, account_id: int) -> CanonicalProfile: ...

    async def fetch_history(
        self, account_id: int, *, window: HistoryWindow | None = None
    ) -> V7CanonicalHistory: ...

    async def fetch_match_core(
        self, match_id: int, *, account_id: int | None = None
    ) -> V7CanonicalMatch: ...


ProviderHistory = V7CanonicalHistory


def provider_cache_key(provider: str, resource: str, *parts: object) -> str:
    """Build a visibly provider-owned cache identity."""

    values = (provider, resource, *(str(part) for part in parts))
    if any(not value or ":" in value for value in values):
        raise ValueError("provider cache key contains an invalid component")
    return ":".join(values)


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "CanonicalProfile",
    "HistoryCompleteness",
    "HistoryProvider",
    "HistoryWindow",
    "ProviderName",
    "ProviderHistory",
    "ProviderProvenance",
    "RequestLedger",
    "V7CanonicalHistory",
    "V7CanonicalMatch",
    "canonical_json_sha256",
    "provider_cache_key",
]
