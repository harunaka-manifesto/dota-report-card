"""Read-only adapter for the existing V6 compact calibration corpus.

The V6 corpus was produced by the legacy paginated collector.  It already
contains eligibility-filtered, compact rows, so sending it through the raw
summary normalizer would be both lossy and incorrect (the compact rows do not
carry ``player_slot``, ``radiant_win``, or ``leaver_status``).  This module is
the narrow compatibility seam used by calibration only.

The adapter deliberately keeps private profile/match keys in memory for
deduplication and estimator execution.  Callers that write aggregate output
must use :func:`redact_aggregate` or the aggregate privacy validator in the
reuse-audit module.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from app.heroes.taxonomy import load_default_taxonomy
from app.ingestion.summary_history_contract import (
    SUMMARY_HISTORY_NORMALIZATION_VERSION,
    SUMMARY_HISTORY_PROJECTION_VERSION,
    SUMMARY_HISTORY_PROVIDER_VERSION,
    CanonicalSummaryHistory,
    SummaryHistoryAudit,
    sha256_payload,
)
from app.ingestion.summary_normalize import (
    EligibilityFlag,
    NormalizationResult,
    NormalizedSummaryMatch,
)
from app.player_analysis_v6.hero_portfolio import load_v6_hero_taxonomy
from app.player_analysis_v6.metrics import (
    death_exposure_per_ten_minutes,
    finishing_share,
    involvement_per_minute,
)

LEGACY_TO_ANALYTICAL = {
    "start_time": "chronology",
    "duration_seconds": "duration_exposure",
    "won": "player_relative_outcome",
    "kills/deaths/assists": "expression_and_finishing_events",
    "hero_id": "portfolio_and_distance",
    "hero_function": "legacy_audit_only",
    "patch": "patch_fallback_context",
    "region": "region_fallback_context",
    "lane_context": "optional_literal_context",
    "session_id/session_index": "independence_and_chronology",
    "session_corrupt": "session_completion_censoring",
}

CORE_ANALYTICAL_FIELDS = (
    "profile_id",
    "match_id",
    "start_time",
    "duration_seconds",
    "won",
    "kills",
    "deaths",
    "assists",
    "hero_id",
    "patch",
    "session_id",
    "session_index",
    "session_corrupt",
)

OPTIONAL_ANALYTICAL_FIELDS = (
    "lane_context",
    "party_size",
    "hero_variant",
    "region",
    "source_version",
    "game_mode",
    "lobby_type",
)

_METRIC_ALIASES = {
    "involvement_adjusted": "involvement_per_minute",
    "finishing_adjusted": "finishing_share",
    "death_exposure_adjusted": "death_exposure_per_ten",
}


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _taxonomy_jobs(entry: Any) -> tuple[str, ...]:
    if entry is None:
        return ()
    if isinstance(entry, Mapping):
        values = (
            entry.get("functional_jobs")
            or entry.get("jobs")
            or entry.get("labels")
            or entry.get("primary_functions")
            or entry.get("roles")
        )
        primary = entry.get("hero_function") or entry.get("function")
        if primary:
            values = (primary, *(values or ()))
    else:
        values = getattr(entry, "roles", ())
    if isinstance(values, str):
        values = (values,)
    if values is None:
        values = ()
    try:
        return tuple(dict.fromkeys(str(value) for value in values if value not in (None, "")))
    except TypeError:
        return ()


def current_taxonomy_mapping() -> dict[int, dict[str, Any]]:
    """Return the exact reviewed taxonomy shape used by V6.1 runtime code."""

    try:
        return load_v6_hero_taxonomy()
    except (OSError, ValueError):
        taxonomy = load_default_taxonomy()
        return {
            hero_id: {
                "hero_function": roles[0] if (roles := tuple(hero.roles)) else None,
                "functional_jobs": list(roles),
                "source_version": taxonomy.version,
            }
            for hero_id, hero in taxonomy.heroes.items()
        }


def _hero_taxonomy_entry(hero_id: Any, taxonomy_by_hero: Mapping[Any, Any] | None) -> Any:
    if taxonomy_by_hero is None:
        return None
    return taxonomy_by_hero.get(hero_id)


def rederive_hero_function(
    hero_id: Any,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
) -> tuple[str | None, tuple[str, ...]]:
    jobs = _taxonomy_jobs(_hero_taxonomy_entry(hero_id, taxonomy_by_hero))
    return (jobs[0] if jobs else None), jobs


def _metric_value(row: Mapping[str, Any], key: str) -> float | None:
    direct = _finite(row.get(key))
    if direct is not None:
        return direct
    metrics = row.get("metrics")
    if isinstance(metrics, Mapping):
        value = _finite(metrics.get(key))
        if value is not None:
            return value
        alias = _METRIC_ALIASES.get(key)
        if alias:
            return _finite(metrics.get(alias))
    alias = _METRIC_ALIASES.get(key)
    return _finite(row.get(alias)) if alias else None


def _raw_metric(row: Mapping[str, Any], key: str) -> float | None:
    if key == "involvement_adjusted":
        return involvement_per_minute(row.get("kills"), row.get("assists"), row.get("duration_seconds"))
    if key == "finishing_adjusted":
        return finishing_share(row.get("kills"), row.get("assists"))
    if key == "death_exposure_adjusted":
        return death_exposure_per_ten_minutes(row.get("deaths"), row.get("duration_seconds"))
    if key == "outcome":
        value = row.get("won")
        return float(value) if isinstance(value, bool) else _finite(value)
    return _metric_value(row, key)


def adapt_legacy_row(
    row: Mapping[str, Any],
    *,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
    keep_private_identifiers: bool = True,
) -> dict[str, Any]:
    """Map one already-normalized V6 row into a V6.1 analytical record.

    No raw-normalization eligibility rules are applied here.  Missing optional
    values remain missing; in particular they are never turned into zero or a
    neutral category.
    """

    required = {key for key in CORE_ANALYTICAL_FIELDS if key not in {"profile_id", "match_id"}}
    missing = sorted(key for key in required if row.get(key) is None)
    if missing:
        raise ValueError(f"legacy row is missing core analytical fields: {missing}")
    hero_function, jobs = rederive_hero_function(row.get("hero_id"), taxonomy_by_hero)
    result: dict[str, Any] = {
        "start_time": int(row["start_time"]),
        "duration_seconds": int(row["duration_seconds"]),
        "won": bool(row["won"]),
        "kills": int(row["kills"]),
        "deaths": int(row["deaths"]),
        "assists": int(row["assists"]),
        "hero_id": int(row["hero_id"]),
        "hero_function": hero_function,
        "functional_jobs": jobs,
        "patch": row.get("patch"),
        "region": row.get("region"),
        "lane_context": row.get("lane_context"),
        "session_id": str(row["session_id"]),
        "session_index": int(row["session_index"]),
        "session_corrupt": bool(row["session_corrupt"]),
        "party_size": row.get("party_size"),
        "hero_variant": row.get("hero_variant"),
        "source_version": row.get("source_version"),
        "game_mode": row.get("game_mode"),
        "lobby_type": row.get("lobby_type"),
        "metrics": {},
        "adapter": "legacy-v6-compact-to-v61-1.0.0",
    }
    for metric in ("outcome", "involvement_adjusted", "finishing_adjusted", "death_exposure_adjusted"):
        value = _raw_metric(row, metric)
        if value is not None and math.isfinite(value):
            result["metrics"][metric] = value
            alias = _METRIC_ALIASES.get(metric)
            if alias:
                result["metrics"][alias] = value
    if keep_private_identifiers:
        result["profile_id"] = row.get("profile_id")
        result["match_id"] = row.get("match_id")
    return result


def adapt_legacy_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
    keep_private_identifiers: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Adapt rows deterministically and return private taxonomy disagreement counts."""

    disagreement: Counter[str] = Counter()
    adapted: list[dict[str, Any]] = []
    for row in rows:
        current, _jobs = rederive_hero_function(row.get("hero_id"), taxonomy_by_hero)
        legacy = row.get("hero_function")
        if legacy not in (None, "") and current not in (None, "") and str(legacy) != current:
            disagreement["legacy_vs_current_hero_function"] += 1
        if current is None:
            disagreement["taxonomy_unavailable"] += 1
        adapted.append(
            adapt_legacy_row(
                row,
                taxonomy_by_hero=taxonomy_by_hero,
                keep_private_identifiers=keep_private_identifiers,
            )
        )
    adapted.sort(key=lambda item: (str(item.get("profile_id", "")), int(item["start_time"]), int(item["match_id"])))
    return adapted, dict(sorted(disagreement.items()))


def legacy_canonical_history(
    rows: Sequence[Mapping[str, Any]],
    *,
    account_id: int,
    completeness: str = "complete",
) -> CanonicalSummaryHistory:
    """Wrap compact eligible rows in the runtime history contract.

    This is a constructor, not the raw summary normalizer: the corpus has
    already passed V6 eligibility and does not contain the raw
    ``player_slot``/``radiant_win`` transport fields.  The resulting object is
    used only for the exact report assembly path during offline evaluation.
    """

    adapted, _disagreement = adapt_legacy_rows(
        rows,
        taxonomy_by_hero=current_taxonomy_mapping(),
        keep_private_identifiers=True,
    )
    normalized: list[NormalizedSummaryMatch] = []
    projection: list[dict[str, Any]] = []
    for index, row in enumerate(adapted):
        match_id = int(row["match_id"])
        start_time = int(row["start_time"])
        duration = int(row["duration_seconds"])
        projection.append(
            {
                "match_id": match_id,
                "start_time": start_time,
                "duration_seconds": duration,
                "hero_id": int(row["hero_id"]),
                "won": bool(row["won"]),
                "kills": int(row["kills"]),
                "deaths": int(row["deaths"]),
                "assists": int(row["assists"]),
                "session_id": str(row["session_id"]),
            }
        )
        normalized.append(
            NormalizedSummaryMatch(
                match_id=match_id,
                source_index=index,
                account_id=account_id,
                hero_id=int(row["hero_id"]),
                hero_variant=(
                    int(row["hero_variant"])
                    if isinstance(row.get("hero_variant"), int)
                    else None
                ),
                started_at=start_time,
                duration_seconds=duration,
                ended_at=start_time + duration,
                side=None,
                won=bool(row["won"]),
                game_mode=(
                    int(row["game_mode"])
                    if isinstance(row.get("game_mode"), int)
                    else None
                ),
                lobby_type=(
                    int(row["lobby_type"])
                    if isinstance(row.get("lobby_type"), int)
                    else None
                ),
                leaver_status=None,
                kills=int(row["kills"]),
                deaths=int(row["deaths"]),
                assists=int(row["assists"]),
                party_size=(
                    int(row["party_size"])
                    if isinstance(row.get("party_size"), int)
                    else None
                ),
                lane_role=None,
                lane=None,
                is_roaming=None,
                role_hint=row.get("hero_function"),
                role_confidence=None,
                patch=row.get("patch"),
                source_version=row.get("source_version"),
                skill_bracket=None,
                region=(
                    int(row["region"])
                    if isinstance(row.get("region"), int)
                    else None
                ),
                session_id=str(row["session_id"]),
                session_index=int(row["session_index"]),
                session_corrupt=bool(row["session_corrupt"]),
                eligibility={"overall": EligibilityFlag(True)},
            )
        )
    if not normalized:
        raise ValueError("compact legacy history cannot be empty")
    starts = [item.started_at for item in normalized if item.started_at is not None]
    optional_fields = (
        "party_size", "hero_variant", "region", "patch", "source_version",
        "lane_context", "lane_role", "is_roaming",
    )
    optional_coverage = {
        field: sum(row.get(field) is not None for row in adapted) / len(adapted)
        for field in optional_fields
    }
    audit = SummaryHistoryAudit(
        request_count=1,
        raw_payload_sha256=sha256_payload(projection),
        normalized_payload_sha256=sha256_payload(projection),
        raw_count=len(adapted),
        normalized_count=len(normalized),
        eligible_count=len(normalized),
        deduplicated_count=0,
        earliest_start_time=min(starts) if starts else None,
        latest_start_time=max(starts) if starts else None,
        required_field_coverage={
            "match_id": 1.0,
            "player_slot": 0.0,
            "radiant_win": 0.0,
            "duration": 1.0,
            "game_mode": sum(row.get("game_mode") is not None for row in adapted) / len(adapted),
            "lobby_type": sum(row.get("lobby_type") is not None for row in adapted) / len(adapted),
            "hero_id": 1.0,
            "start_time": 1.0,
            "kills": 1.0,
            "deaths": 1.0,
            "assists": 1.0,
            "leaver_status": 0.0,
        },
        optional_field_coverage=optional_coverage,
        optional_public_availability={field: False for field in optional_fields},
        completeness=completeness,  # type: ignore[arg-type]
        projection_version=SUMMARY_HISTORY_PROJECTION_VERSION,
        normalization_version=SUMMARY_HISTORY_NORMALIZATION_VERSION,
        provider_version=SUMMARY_HISTORY_PROVIDER_VERSION,
        rank_or_mmr_used=False,
    )
    return CanonicalSummaryHistory(
        NormalizationResult(tuple(normalized), (), (), len(adapted)),
        audit,
    )


def redacted_runtime_record(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return the identifier-free record shape safe for aggregate diagnostics."""

    return {
        key: value
        for key, value in row.items()
        if key not in {"profile_id", "match_id", "session_id", "adapter"}
    }


__all__ = [
    "CORE_ANALYTICAL_FIELDS",
    "LEGACY_TO_ANALYTICAL",
    "OPTIONAL_ANALYTICAL_FIELDS",
    "adapt_legacy_row",
    "adapt_legacy_rows",
    "current_taxonomy_mapping",
    "legacy_canonical_history",
    "redacted_runtime_record",
    "rederive_hero_function",
]
