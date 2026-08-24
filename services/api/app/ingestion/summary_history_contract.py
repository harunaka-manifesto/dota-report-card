"""Canonical one-request summary-history contract for Free DNA V6.1.

This module is the only owner of the provider projection used by runtime,
calibration, fixtures, and documentation.  It deliberately separates the
physical request contract from the existing paginated OpenDota history API so
V6.0 behavior remains immutable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .summary_normalize import NormalizationResult, normalize_summary_rows

SUMMARY_HISTORY_SCHEMA_VERSION = "summary-history-schema-3.0.0"
SUMMARY_HISTORY_PROJECTION_VERSION = "summary-projection-3.0.0"
SUMMARY_HISTORY_NORMALIZATION_VERSION = "summary-normalization-2.0.0"
SUMMARY_HISTORY_PROVIDER_VERSION = "opendota-summary-2.0.0"
SUMMARY_HISTORY_WINDOW_DAYS = 365
# OpenDota accepts a caller-selected limit on this endpoint.  This is a
# transport ceiling, not a product match cap; reaching it is treated as
# possible truncation and suppresses completeness-dependent claims.
SUMMARY_HISTORY_PROVIDER_LIMIT = 10_000

SUMMARY_HISTORY_PROJECTION = (
    "match_id",
    "player_slot",
    "radiant_win",
    "duration",
    "game_mode",
    "lobby_type",
    "hero_id",
    "start_time",
    "version",
    "kills",
    "deaths",
    "assists",
    "leaver_status",
    "party_size",
    "hero_variant",
    "leagueid",
    "cluster",
    "lane",
    "lane_role",
    "is_roaming",
)

REQUIRED_FIELDS = frozenset(
    {
        "match_id",
        "player_slot",
        "radiant_win",
        "duration",
        "game_mode",
        "lobby_type",
        "hero_id",
        "start_time",
        "kills",
        "deaths",
        "assists",
        "leaver_status",
    }
)
OPTIONAL_FIELDS = frozenset(set(SUMMARY_HISTORY_PROJECTION) - REQUIRED_FIELDS)
FORBIDDEN_ANALYTICAL_FIELDS = frozenset(
    {"average_rank", "rank_tier", "rank", "mmr", "skill", "skill_bracket"}
)
# Provider-returned fields outside the ordered projection are ignored before
# hashing or normalization. This is a policy, not a competing exhaustive list.
IGNORED_FIELDS = frozenset({"account_id", "personaname", "avatar", "raw_match_data"})
OPTIONAL_PUBLIC_COVERAGE_MINIMUMS: Mapping[str, float] = {
    "version": 0.80,
    "party_size": 0.80,
    "hero_variant": 0.80,
    "lane": 0.80,
    "lane_role": 0.80,
    "is_roaming": 0.80,
}

HistoryCompleteness = Literal["complete", "possibly_truncated", "unknown"]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def field_coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    denominator = len(rows)
    return {
        field: (
            sum(row.get(field) is not None for row in rows) / denominator
            if denominator
            else 0.0
        )
        for field in SUMMARY_HISTORY_PROJECTION
    }


def public_optional_availability(coverage: Mapping[str, float]) -> dict[str, bool]:
    return {
        field: coverage.get(field, 0.0) >= minimum
        for field, minimum in OPTIONAL_PUBLIC_COVERAGE_MINIMUMS.items()
    }


def history_completeness(raw_count: int, *, provider_limit: int | None) -> HistoryCompleteness:
    if provider_limit is None:
        return "unknown"
    return "possibly_truncated" if raw_count >= provider_limit else "complete"


@dataclass(frozen=True, slots=True)
class SummaryHistoryAudit:
    request_count: int
    raw_payload_sha256: str
    normalized_payload_sha256: str
    raw_count: int
    normalized_count: int
    eligible_count: int
    deduplicated_count: int
    earliest_start_time: int | None
    latest_start_time: int | None
    required_field_coverage: Mapping[str, float]
    optional_field_coverage: Mapping[str, float]
    optional_public_availability: Mapping[str, bool]
    completeness: HistoryCompleteness
    projection_version: str = SUMMARY_HISTORY_PROJECTION_VERSION
    normalization_version: str = SUMMARY_HISTORY_NORMALIZATION_VERSION
    provider_version: str = SUMMARY_HISTORY_PROVIDER_VERSION
    schema_version: str = SUMMARY_HISTORY_SCHEMA_VERSION
    rank_or_mmr_used: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_version": self.provider_version,
            "projection_version": self.projection_version,
            "normalization_version": self.normalization_version,
            "request_count": self.request_count,
            "raw_payload_sha256": self.raw_payload_sha256,
            "normalized_payload_sha256": self.normalized_payload_sha256,
            "raw_count": self.raw_count,
            "normalized_count": self.normalized_count,
            "eligible_count": self.eligible_count,
            "deduplicated_count": self.deduplicated_count,
            "earliest_start_time": self.earliest_start_time,
            "latest_start_time": self.latest_start_time,
            "required_field_coverage": dict(self.required_field_coverage),
            "optional_field_coverage": dict(self.optional_field_coverage),
            "optional_public_availability": dict(self.optional_public_availability),
            "completeness": self.completeness,
            "rank_or_mmr_used": self.rank_or_mmr_used,
        }


@dataclass(frozen=True, slots=True)
class CanonicalSummaryHistory:
    normalization: NormalizationResult
    audit: SummaryHistoryAudit


def normalize_canonical_summary_history(
    rows: Sequence[Mapping[str, Any]],
    account_id: int,
    *,
    request_count: int = 1,
    provider_limit: int | None = SUMMARY_HISTORY_PROVIDER_LIMIT,
) -> CanonicalSummaryHistory:
    if request_count != 1:
        raise ValueError("Free DNA V6.1 requires exactly one physical history request")
    raw_rows = [
        {field: row.get(field) for field in SUMMARY_HISTORY_PROJECTION if field in row}
        for row in rows
    ]
    normalized = normalize_summary_rows(raw_rows, account_id)
    coverage = field_coverage(raw_rows)
    starts = [item.started_at for item in normalized.matches if item.started_at is not None]
    normalized_projection = [
        {
            "match_id": item.match_id,
            "start_time": item.started_at,
            "duration_seconds": item.duration_seconds,
            "hero_id": item.hero_id,
            "won": item.won,
            "kills": item.kills,
            "deaths": item.deaths,
            "assists": item.assists,
            "session_id": item.session_id,
        }
        for item in normalized.matches
    ]
    audit = SummaryHistoryAudit(
        request_count=request_count,
        raw_payload_sha256=sha256_payload(raw_rows),
        normalized_payload_sha256=sha256_payload(normalized_projection),
        raw_count=len(raw_rows),
        normalized_count=len(normalized.matches),
        eligible_count=len(normalized.eligible_matches),
        deduplicated_count=max(0, len(raw_rows) - len(normalized.matches)),
        earliest_start_time=min(starts) if starts else None,
        latest_start_time=max(starts) if starts else None,
        required_field_coverage={key: coverage[key] for key in sorted(REQUIRED_FIELDS)},
        optional_field_coverage={key: coverage[key] for key in sorted(OPTIONAL_FIELDS)},
        optional_public_availability=public_optional_availability(coverage),
        completeness=history_completeness(len(raw_rows), provider_limit=provider_limit),
    )
    return CanonicalSummaryHistory(normalized, audit)


def request_manifest() -> dict[str, Any]:
    """Return the public, secret-free canonical transport manifest."""

    return {
        "schema_version": SUMMARY_HISTORY_SCHEMA_VERSION,
        "provider_version": SUMMARY_HISTORY_PROVIDER_VERSION,
        "projection_version": SUMMARY_HISTORY_PROJECTION_VERSION,
        "window_days": SUMMARY_HISTORY_WINDOW_DAYS,
        "provider_limit": SUMMARY_HISTORY_PROVIDER_LIMIT,
        "projection": list(SUMMARY_HISTORY_PROJECTION),
        "required_fields": sorted(REQUIRED_FIELDS),
        "optional_fields": sorted(OPTIONAL_FIELDS),
        "ignored_fields": sorted(IGNORED_FIELDS),
        "forbidden_analytical_fields": sorted(FORBIDDEN_ANALYTICAL_FIELDS),
        "optional_public_coverage_minimums": dict(OPTIONAL_PUBLIC_COVERAGE_MINIMUMS),
        "request_parameters": {
            "date": SUMMARY_HISTORY_WINDOW_DAYS,
            "limit": SUMMARY_HISTORY_PROVIDER_LIMIT,
            "project": list(SUMMARY_HISTORY_PROJECTION),
        },
        "physical_request_count": 1,
        "rank_or_mmr_used": False,
    }


__all__ = [
    "CanonicalSummaryHistory",
    "FORBIDDEN_ANALYTICAL_FIELDS",
    "IGNORED_FIELDS",
    "OPTIONAL_FIELDS",
    "OPTIONAL_PUBLIC_COVERAGE_MINIMUMS",
    "REQUIRED_FIELDS",
    "SUMMARY_HISTORY_NORMALIZATION_VERSION",
    "SUMMARY_HISTORY_PROJECTION",
    "SUMMARY_HISTORY_PROJECTION_VERSION",
    "SUMMARY_HISTORY_PROVIDER_LIMIT",
    "SUMMARY_HISTORY_PROVIDER_VERSION",
    "SUMMARY_HISTORY_SCHEMA_VERSION",
    "SUMMARY_HISTORY_WINDOW_DAYS",
    "SummaryHistoryAudit",
    "field_coverage",
    "history_completeness",
    "normalize_canonical_summary_history",
    "request_manifest",
    "sha256_payload",
]
