"""The private, canonical V6.1 calibration-corpus contract.

The collector materializes one profile object per pseudonym. Consumers use this
module to validate those bytes and obtain flattened analytical rows; no
consumer needs to know how the private JSON is laid out.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from app.dna.sessions import SessionPolicy, infer_sessions
from app.ingestion.summary_history_contract import (
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    SUMMARY_HISTORY_PROJECTION,
    SUMMARY_HISTORY_PROJECTION_VERSION,
    SUMMARY_HISTORY_PROVIDER_LIMIT,
    SUMMARY_HISTORY_SCHEMA_VERSION,
    CanonicalSummaryHistory,
    SummaryHistoryAudit,
    field_coverage,
    history_completeness,
    normalize_canonical_summary_history,
    public_optional_availability,
    sha256_payload,
)
from app.ingestion.summary_normalize import (
    EligibilityFlag,
    NormalizationResult,
    NormalizedSummaryMatch,
)

LEGACY_CANONICAL_SCHEMA_VERSION = "v61-calibration-corpus-2.0.0"
CANONICAL_SCHEMA_VERSION = "v61-calibration-corpus-2.1.0"
SUPPORTED_CANONICAL_SCHEMA_VERSIONS = frozenset(
    {LEGACY_CANONICAL_SCHEMA_VERSION, CANONICAL_SCHEMA_VERSION}
)
CANONICAL_WINDOW_DAYS = 365
CANONICAL_WINDOW_SECONDS = 31_536_000
PER_PROFILE_WINDOW_MODE = "per_profile_365_day"
MINIMUM_USABLE_MATCHES = 30
CANONICAL_SESSION_POLICY = SessionPolicy(gap_minutes=90)
PROFILE_HASH = re.compile(r"^[0-9a-f]{64}$")
VALID_LEAVER_STATUSES = frozenset({0, 1})
SUPPORTED_GAME_MODES = frozenset({1, 22})
SUPPORTED_LOBBY_TYPES = frozenset({0, 7})

CANONICAL_MATCH_FIELDS = frozenset(
    {
        "match_id",
        "start_time",
        "duration_seconds",
        "won",
        "hero_id",
        "kills",
        "deaths",
        "assists",
        "leaver_status",
        "game_mode",
        "lobby_type",
        "session_id",
        "session_index",
        "session_corrupt",
    }
)
CANONICAL_OPTIONAL_MATCH_FIELDS = frozenset(
    {
        "hero_variant",
        "party_size",
        "lane",
        "lane_role",
        "is_roaming",
        "source_version",
        "patch",
        "region",
        "lane_context",
        "hero_function",
    }
)
FORBIDDEN_DIMENSION_KEYS = frozenset(
    {
        "rank",
        "rank_tier",
        "average_rank",
        "mmr",
        "mmr_bucket",
        "skill",
        "skill_bracket",
        "medal",
    }
)
PRIVATE_IDENTIFIER_KEYS = frozenset(
    {"account_id", "account_ids", "steam_id", "player_id", "player_ids"}
)


class CanonicalCorpusError(ValueError):
    """Raised when canonical V6.1 corpus bytes cannot authorize calibration."""


@dataclass(frozen=True, slots=True)
class CanonicalCalibrationCorpus:
    payload: Mapping[str, Any]
    matches: tuple[Mapping[str, Any], ...]
    profile_summaries: Mapping[str, Mapping[str, Any]]
    completed_sessions_by_profile: Mapping[str, Mapping[str, bool]]
    checksum: str

    @property
    def profile_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.profile_summaries))

    @property
    def usable_profile_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                profile_id
                for profile_id, profile in self.profile_summaries.items()
                if profile.get("status") == "eligible"
                and int(profile.get("eligible_match_count", 0) or 0) >= MINIMUM_USABLE_MATCHES
            )
        )

    @property
    def window_mode(self) -> str:
        if self.payload.get("schema_version") == CANONICAL_SCHEMA_VERSION:
            return PER_PROFILE_WINDOW_MODE
        return "single_365_day"

    def collection_window_for_profile(self, profile_id: str) -> Mapping[str, Any]:
        profile = self.profile_summaries[profile_id]
        if self.window_mode == PER_PROFILE_WINDOW_MODE:
            return profile["collection_window"]
        return self.payload["window"]

    def completion_for_profile(self, profile_id: str) -> Mapping[str, bool]:
        return self.completed_sessions_by_profile.get(profile_id, {})

    def aggregate_diagnostics(self) -> dict[str, Any]:
        reasons = Counter(
            str(reason)
            for profile in self.profile_summaries.values()
            for reason, count in (profile.get("eligibility_audit", {}).get("exclusion_reasons", {}) or {}).items()
            for _ in range(int(count) if isinstance(count, int) and count > 0 else 0)
        )
        windows = [self.collection_window_for_profile(profile_id) for profile_id in self.profile_ids]
        distinct_windows = {
            (
                int(window["days"]),
                int(window["start_time"]),
                int(window["end_time"]),
            )
            for window in windows
        }
        exact_windows = all(
            window.get("days") == CANONICAL_WINDOW_DAYS
            and int(window["end_time"]) - int(window["start_time"]) == CANONICAL_WINDOW_SECONDS
            for window in windows
        )
        return {
            "schema_version": self.payload["schema_version"],
            "window_mode": self.window_mode,
            "profile_window_count": len(windows),
            "distinct_window_count": len(distinct_windows),
            "all_profile_windows_exact_365_days": exact_windows,
            "profile_count": len(self.profile_summaries),
            "usable_profile_count": len(self.usable_profile_ids),
            "below_minimum_profile_count": len(self.profile_summaries) - len(self.usable_profile_ids),
            "match_count": len(self.matches),
            "session_count": len({(row["profile_id"], row["session_id"]) for row in self.matches}),
            "leaver_status": {
                "included_match_count": len(self.matches),
                "excluded_missing_count": reasons.get("missing_leaver_status", 0),
                "excluded_invalid_count": reasons.get("invalid_leaver_status", 0),
                "excluded_abandoned_count": reasons.get("abandoned", 0),
            },
            "checksum": self.checksum,
            "rank_or_mmr_used": False,
            "raw_identifiers_present": False,
        }


def _walk(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            folded = str(key).casefold()
            if folded in PRIVATE_IDENTIFIER_KEYS:
                raise CanonicalCorpusError(f"private account identifier at {path}.{key}")
            if folded in FORBIDDEN_DIMENSION_KEYS or "mmr" in folded or folded.startswith("rank"):
                if folded == "rank_or_mmr_used" and nested is False:
                    continue
                raise CanonicalCorpusError(f"forbidden rank/MMR field at {path}.{key}")
            _walk(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _walk(nested, f"{path}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise CanonicalCorpusError(f"non-finite value at {path}")


def _integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CanonicalCorpusError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise CanonicalCorpusError(f"{label} must be >= {minimum}")
    return value


def _validate_window(
    window: Any,
    label: str,
    *,
    exact_duration: bool,
) -> Mapping[str, Any]:
    if not isinstance(window, Mapping):
        raise CanonicalCorpusError(f"{label} must be an object")
    if window.get("days") != CANONICAL_WINDOW_DAYS:
        raise CanonicalCorpusError(f"{label}.days must be 365")
    start = _integer(window.get("start_time"), f"{label}.start_time")
    end = _integer(window.get("end_time"), f"{label}.end_time")
    if start >= end:
        raise CanonicalCorpusError(f"{label} is not ordered")
    if exact_duration and end - start != CANONICAL_WINDOW_SECONDS:
        raise CanonicalCorpusError(f"{label} must span exactly 365 days")
    return window


def _profile_rows(profile: Mapping[str, Any], profile_id: str) -> list[dict[str, Any]]:
    raw_rows = profile.get("matches")
    if not isinstance(raw_rows, list):
        raise CanonicalCorpusError("canonical profile matches must be an array")
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, Mapping):
            raise CanonicalCorpusError("canonical match rows must be objects")
        row = dict(raw)
        if row.get("profile_id") not in (None, profile_id):
            raise CanonicalCorpusError("nested match profile ownership mismatch")
        row["profile_id"] = profile_id
        rows.append(row)
    return rows


def _summary_raw_row(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = {
        "match_id": row.get("match_id"),
        "player_slot": row.get("player_slot"),
        "radiant_win": row.get("radiant_win"),
        "duration": row.get("duration_seconds"),
        "game_mode": row.get("game_mode"),
        "lobby_type": row.get("lobby_type"),
        "hero_id": row.get("hero_id"),
        "start_time": row.get("start_time"),
        "version": row.get("source_version"),
        "kills": row.get("kills"),
        "deaths": row.get("deaths"),
        "assists": row.get("assists"),
        "leaver_status": row.get("leaver_status"),
        "party_size": row.get("party_size"),
        "hero_variant": row.get("hero_variant"),
        "lane": row.get("lane"),
        "lane_role": row.get("lane_role"),
        "is_roaming": row.get("is_roaming"),
    }
    if raw["player_slot"] is None and raw["radiant_win"] is None:
        raw["won"] = row.get("won")
    return raw


def _direct_match(row: Mapping[str, Any], source_index: int, account_id: int) -> NormalizedSummaryMatch:
    player_slot = row.get("player_slot")
    side: Literal["radiant", "dire"] | None = None
    if isinstance(player_slot, int) and not isinstance(player_slot, bool):
        side = "radiant" if player_slot < 128 else "dire"
    role_hint = row.get("hero_function")
    if role_hint is not None:
        role_hint = str(role_hint)
    role_available = role_hint is not None or row.get("lane_role") is not None or row.get("is_roaming") is True
    kda_available = all(
        isinstance(row.get(field), int) and not isinstance(row.get(field), bool)
        for field in ("kills", "deaths", "assists")
    )
    flags = {
        "overall": EligibilityFlag(True),
        "breadth": EligibilityFlag(True),
        "role": EligibilityFlag(role_available, () if role_available else ("missing_role_hint",)),
        "adaptability": EligibilityFlag(True),
        "activity": EligibilityFlag(
            kda_available and int(row["duration_seconds"]) >= 600,
            () if kda_available else ("missing_kda",),
        ),
        "orientation": EligibilityFlag(
            kda_available and int(row["kills"]) + int(row["assists"]) > 0,
            () if kda_available else ("missing_kda",),
        ),
        "resilience": EligibilityFlag(True),
        "endurance": EligibilityFlag(True),
        "rhythm": EligibilityFlag(True),
    }
    return NormalizedSummaryMatch(
        match_id=int(row["match_id"]),
        source_index=source_index,
        account_id=account_id,
        hero_id=int(row["hero_id"]),
        hero_variant=row.get("hero_variant") if isinstance(row.get("hero_variant"), int) else None,
        started_at=int(row["start_time"]),
        duration_seconds=int(row["duration_seconds"]),
        ended_at=int(row["start_time"]) + int(row["duration_seconds"]),
        side=side,
        won=bool(row["won"]),
        game_mode=int(row["game_mode"]),
        lobby_type=int(row["lobby_type"]),
        leaver_status=int(row["leaver_status"]),
        kills=int(row["kills"]),
        deaths=int(row["deaths"]),
        assists=int(row["assists"]),
        party_size=row.get("party_size") if isinstance(row.get("party_size"), int) else None,
        lane_role=row.get("lane_role") if isinstance(row.get("lane_role"), int) else None,
        lane=row.get("lane") if isinstance(row.get("lane"), int) else None,
        is_roaming=row.get("is_roaming") if isinstance(row.get("is_roaming"), bool) else None,
        role_hint=role_hint,
        role_confidence=None,
        patch=row.get("patch"),
        source_version=row.get("source_version"),
        skill_bracket=None,
        region=row.get("region") if isinstance(row.get("region"), int) else None,
        eligibility=flags,
    )


def normalize_calibration_history(
    rows: Sequence[Mapping[str, Any]], account_id: int
) -> dict[str, Any]:
    """Keep the existing runtime contract helper on the shared normalizer."""

    canonical = normalize_canonical_summary_history(
        rows,
        account_id,
        request_count=1,
        provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
    )
    return {
        "normalized_payload_sha256": canonical.audit.normalized_payload_sha256,
        "eligibility_audit": {
            "raw_count": canonical.audit.raw_count,
            "normalized_count": canonical.audit.normalized_count,
            "eligible_count": canonical.audit.eligible_count,
            "deduplicated_count": canonical.audit.deduplicated_count,
        },
        "coverage": {
            "required": dict(canonical.audit.required_field_coverage),
            "optional": dict(canonical.audit.optional_field_coverage),
        },
        "matches": canonical.normalization.matches,
    }


def canonical_history(
    rows: Sequence[Mapping[str, Any]],
    account_id: int,
    *,
    window_start: int | None = None,
    window_end: int | None = None,
) -> CanonicalSummaryHistory:
    """Build runtime history directly from canonical rows.

    With source-side fields present, the exact runtime normalizer is used.
    Minimal synthetic rows use the already-derived ``won`` field and the same
    eligibility/session contract without inventing provider values.
    """

    ordered = sorted(rows, key=lambda row: (int(row["start_time"]), int(row["match_id"])))
    has_source_side = all(
        row.get("player_slot") is not None and row.get("radiant_win") is not None
        for row in ordered
    )
    if has_source_side:
        history = normalize_canonical_summary_history(
            [_summary_raw_row(row) for row in ordered],
            account_id,
            request_count=1,
            provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
        )
        if len(history.normalization.eligible_matches) != len(ordered):
            raise CanonicalCorpusError("canonical rows do not satisfy the runtime eligibility boundary")
    else:
        normalized = tuple(_direct_match(row, index, account_id) for index, row in enumerate(ordered))
        raw_rows = [_summary_raw_row(row) for row in ordered]
        coverage = field_coverage(raw_rows)
        starts = [int(row["start_time"]) for row in ordered]
        projection = [
            {
                "match_id": int(row["match_id"]),
                "start_time": int(row["start_time"]),
                "duration_seconds": int(row["duration_seconds"]),
                "hero_id": int(row["hero_id"]),
                "won": bool(row["won"]),
                "kills": int(row["kills"]),
                "deaths": int(row["deaths"]),
                "assists": int(row["assists"]),
            }
            for row in ordered
        ]
        history = CanonicalSummaryHistory(
            NormalizationResult(normalized, (), (), len(normalized)),
            SummaryHistoryAudit(
                request_count=1,
                raw_payload_sha256=sha256_payload(raw_rows),
                normalized_payload_sha256=sha256_payload(projection),
                raw_count=len(raw_rows),
                normalized_count=len(normalized),
                eligible_count=len(normalized),
                deduplicated_count=0,
                earliest_start_time=min(starts) if starts else None,
                latest_start_time=max(starts) if starts else None,
                required_field_coverage={key: coverage.get(key, 0.0) for key in sorted(REQUIRED_FIELDS)},
                optional_field_coverage={key: coverage.get(key, 0.0) for key in sorted(OPTIONAL_FIELDS)},
                optional_public_availability=public_optional_availability(coverage),
                completeness=history_completeness(
                    len(raw_rows), provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT
                ),
            ),
        )

    sessions = infer_sessions(
        history.normalization.eligible_matches,
        CANONICAL_SESSION_POLICY,
        window_start=window_start,
        window_end=window_end,
    )
    by_match = {item.match_id: item for item in sessions.matches}
    enriched = tuple(by_match.get(item.match_id, item) for item in history.normalization.matches)
    return replace(history, normalization=replace(history.normalization, matches=enriched))


def _validate_match(row: Mapping[str, Any], profile_id: str, window: Mapping[str, Any]) -> None:
    for field in CANONICAL_MATCH_FIELDS:
        if field not in row:
            raise CanonicalCorpusError(f"canonical match is missing required field {field}")
    if not isinstance(row.get("profile_id"), str) or row["profile_id"] != profile_id:
        raise CanonicalCorpusError("canonical match profile ownership is invalid")
    _integer(row["match_id"], "match_id", minimum=1)
    start = _integer(row["start_time"], "start_time")
    _integer(row["duration_seconds"], "duration_seconds", minimum=300)
    if start < int(window["start_time"]) or start > int(window["end_time"]):
        raise CanonicalCorpusError("canonical match lies outside the declared 365-day window")
    if not isinstance(row["won"], bool):
        raise CanonicalCorpusError("won must be boolean")
    for field in ("hero_id", "kills", "deaths", "assists"):
        _integer(row[field], field, minimum=0)
    if row["hero_id"] == 0:
        raise CanonicalCorpusError("hero_id must be positive")
    leaver = _integer(row["leaver_status"], "leaver_status", minimum=0)
    if leaver not in VALID_LEAVER_STATUSES:
        raise CanonicalCorpusError(
            "canonical corpus cannot materialize invalid or abandoning leaver_status"
        )
    if _integer(row["game_mode"], "game_mode") not in SUPPORTED_GAME_MODES:
        raise CanonicalCorpusError("canonical corpus contains an unsupported game_mode")
    if _integer(row["lobby_type"], "lobby_type") not in SUPPORTED_LOBBY_TYPES:
        raise CanonicalCorpusError("canonical corpus contains an unsupported lobby_type")
    if not isinstance(row["session_id"], str) or not row["session_id"]:
        raise CanonicalCorpusError("session_id must be a non-empty string")
    _integer(row["session_index"], "session_index", minimum=1)
    if not isinstance(row["session_corrupt"], bool):
        raise CanonicalCorpusError("session_corrupt must be boolean")
    slot = _integer(row["player_slot"], "player_slot", minimum=0)
    if not isinstance(row["radiant_win"], bool):
        raise CanonicalCorpusError("radiant_win must be boolean")
    derived = bool(row["radiant_win"]) == (slot < 128)
    if derived != row["won"]:
        raise CanonicalCorpusError("won does not match canonical source-side outcome")


def _validate_history_audit(profile: Mapping[str, Any], row_count: int) -> int:
    audit = profile.get("history_audit")
    if not isinstance(audit, Mapping):
        raise CanonicalCorpusError("canonical profile history audit is required")
    if (
        audit.get("schema_version") != SUMMARY_HISTORY_SCHEMA_VERSION
        or audit.get("projection_version") != SUMMARY_HISTORY_PROJECTION_VERSION
        or audit.get("request_count") != 1
        or audit.get("rank_or_mmr_used") is not False
    ):
        raise CanonicalCorpusError("canonical profile history audit is not bound to the runtime request")
    raw_count = _integer(audit.get("raw_count"), "history_audit.raw_count", minimum=0)
    normalized_count = _integer(audit.get("normalized_count"), "history_audit.normalized_count", minimum=0)
    eligible_count = _integer(audit.get("eligible_count"), "history_audit.eligible_count", minimum=0)
    if not raw_count >= normalized_count >= eligible_count >= row_count:
        raise CanonicalCorpusError("canonical profile history audit counts are inconsistent")
    coverage = audit.get("required_field_coverage")
    if not isinstance(coverage, Mapping) or any(
        field not in coverage
        or not isinstance(coverage[field], (int, float))
        or not math.isfinite(float(coverage[field]))
        or not 0.0 <= float(coverage[field]) <= 1.0
        for field in REQUIRED_FIELDS
    ):
        raise CanonicalCorpusError("canonical profile required-field coverage is invalid")
    return raw_count


def validate_canonical_corpus(
    payload: Mapping[str, Any],
    *,
    checksum: str = "",
) -> CanonicalCalibrationCorpus:
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_CANONICAL_SCHEMA_VERSIONS:
        raise CanonicalCorpusError(
            "canonical corpus schema must be one of "
            f"{sorted(SUPPORTED_CANONICAL_SCHEMA_VERSIONS)}"
        )
    _walk(payload)
    if payload.get("raw_identifiers_present") is not False:
        raise CanonicalCorpusError("canonical corpus must declare raw_identifiers_present=false")
    manifest = payload.get("request_manifest")
    if not isinstance(manifest, Mapping):
        raise CanonicalCorpusError("canonical corpus request manifest is missing")
    if manifest.get("schema_version") != SUMMARY_HISTORY_SCHEMA_VERSION or manifest.get("physical_request_count") != 1:
        raise CanonicalCorpusError("canonical corpus is not bound to the one-request summary contract")
    if manifest.get("provider_limit") != SUMMARY_HISTORY_PROVIDER_LIMIT or manifest.get("retry_limit") != 0:
        raise CanonicalCorpusError("canonical corpus request manifest has the wrong provider/retry boundary")
    if manifest.get("projection") != list(SUMMARY_HISTORY_PROJECTION):
        raise CanonicalCorpusError("canonical corpus projection does not match runtime")
    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise CanonicalCorpusError("canonical corpus source metadata is missing")
    if source.get("endpoint") != "/players/{account_id}/matches":
        raise CanonicalCorpusError("canonical corpus source endpoint is not summary history")
    if source.get("request_count_per_profile") != 1 or source.get("detail_requests") != 0 or source.get("parse_requests") != 0:
        raise CanonicalCorpusError("canonical corpus source request counts are invalid")
    if source.get("rank_or_mmr_used") is not False:
        raise CanonicalCorpusError("canonical corpus source must declare rank_or_mmr_used=false")
    if schema_version == LEGACY_CANONICAL_SCHEMA_VERSION:
        corpus_window = _validate_window(payload.get("window"), "window", exact_duration=False)
    else:
        if "window" in payload:
            raise CanonicalCorpusError("V2.1 canonical corpus cannot declare a top-level window")
        policy = payload.get("window_policy")
        if not isinstance(policy, Mapping):
            raise CanonicalCorpusError("V2.1 canonical corpus window_policy is required")
        if (
            policy.get("mode") != PER_PROFILE_WINDOW_MODE
            or policy.get("days") != CANONICAL_WINDOW_DAYS
            or policy.get("profile_window_field") != "collection_window"
        ):
            raise CanonicalCorpusError("V2.1 canonical corpus window_policy is invalid")
        corpus_window = None
    profiles = payload.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise CanonicalCorpusError("canonical corpus profiles must be a non-empty array")

    summaries: dict[str, Mapping[str, Any]] = {}
    flat_rows: list[dict[str, Any]] = []
    completion: dict[str, dict[str, bool]] = {}
    for profile in profiles:
        if not isinstance(profile, Mapping):
            raise CanonicalCorpusError("canonical profile summaries must be objects")
        profile_id = profile.get("profile_id")
        if not isinstance(profile_id, str) or not PROFILE_HASH.fullmatch(profile_id):
            raise CanonicalCorpusError("canonical profile IDs must be salted lowercase hashes")
        if profile_id in summaries:
            raise CanonicalCorpusError("duplicate canonical profile summary")
        status = profile.get("status")
        if status not in {"eligible", "ineligible"}:
            raise CanonicalCorpusError("canonical profile status is invalid")
        rows = _profile_rows(profile, profile_id)
        if schema_version == LEGACY_CANONICAL_SCHEMA_VERSION:
            if corpus_window is None:
                raise CanonicalCorpusError("canonical corpus window is required")
            profile_window = corpus_window
        else:
            profile_window = _validate_window(
                profile.get("collection_window"),
                f"profile {profile_id} collection_window",
                exact_duration=True,
            )
        if profile.get("eligible_match_count") != len(rows):
            raise CanonicalCorpusError("canonical profile eligible match count mismatch")
        raw_count = _validate_history_audit(profile, len(rows))
        eligibility_audit = profile.get("eligibility_audit")
        if not isinstance(eligibility_audit, Mapping):
            raise CanonicalCorpusError("canonical profile eligibility audit is required")
        if eligibility_audit.get("minimum_usable_matches") != MINIMUM_USABLE_MATCHES:
            raise CanonicalCorpusError("canonical profile minimum usable-match policy is invalid")
        excluded_count = _integer(
            eligibility_audit.get("excluded_match_count"),
            "eligibility_audit.excluded_match_count",
            minimum=0,
        )
        if excluded_count != raw_count - len(rows):
            raise CanonicalCorpusError("canonical profile exclusion count does not match history audit")
        duplicate_count = _integer(
            eligibility_audit.get("duplicate_conflict_count"),
            "eligibility_audit.duplicate_conflict_count",
            minimum=0,
        )
        if not isinstance(eligibility_audit.get("exclusion_reasons"), Mapping) or duplicate_count < 0:
            raise CanonicalCorpusError("canonical profile exclusion audit is invalid")
        if status == "eligible" and len(rows) < MINIMUM_USABLE_MATCHES:
            raise CanonicalCorpusError(
                "canonical profile count failed: a profile has fewer than 30 usable matches; "
                "a new approved split/population is required"
            )
        if status == "ineligible" and len(rows) >= MINIMUM_USABLE_MATCHES:
            raise CanonicalCorpusError("canonical profile is marked ineligible despite usable match support")
        session_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            _validate_match(row, profile_id, profile_window)
            session_rows[str(row["session_id"])].append(row)
            flat_rows.append(row)
        if profile.get("session_count") != len(session_rows):
            raise CanonicalCorpusError("canonical profile session count mismatch")
        completed_count = profile.get("completed_session_count")
        if isinstance(completed_count, bool) or not isinstance(completed_count, int):
            raise CanonicalCorpusError("canonical profile completed-session count is required")
        observed = (
            canonical_history(
                rows,
                account_id=1,
                window_start=int(profile_window["start_time"]),
                window_end=int(profile_window["end_time"]),
            )
            if rows
            else None
        )
        expected_by_match = {
            match.match_id: match
            for match in (observed.normalization.matches if observed is not None else ())
        }
        for row in rows:
            expected = expected_by_match.get(int(row["match_id"]))
            if (
                expected is None
                or expected.session_id != row["session_id"]
                or expected.session_index != row["session_index"]
                or expected.session_corrupt != row["session_corrupt"]
            ):
                raise CanonicalCorpusError("canonical session fields do not match runtime session inference")
        completed_count_expected = (
            len(
                infer_sessions(
                    observed.normalization.eligible_matches,
                    CANONICAL_SESSION_POLICY,
                    window_start=int(profile_window["start_time"]),
                    window_end=int(profile_window["end_time"]),
                ).completed_sessions
            )
            if observed is not None
            else 0
        )
        if completed_count != completed_count_expected:
            raise CanonicalCorpusError("canonical profile completed-session count does not match runtime policy")
        ordered_sessions = sorted(
            (
                sid,
                min(int(row["start_time"]) for row in session),
                any(bool(row.get("session_corrupt")) for row in session),
            )
            for sid, session in session_rows.items()
        )
        noncorrupt_ids = [sid for sid, _start, corrupt in ordered_sessions if not corrupt]
        completed_ids = set(noncorrupt_ids[:completed_count])
        completion[profile_id] = {
            sid: sid in completed_ids and not corrupt
            for sid, _start, corrupt in ordered_sessions
        }
        summaries[profile_id] = profile

    summary = payload.get("summary")
    if not isinstance(summary, Mapping):
        raise CanonicalCorpusError("canonical corpus summary is missing")
    usable_count = sum(
        profile.get("status") == "eligible"
        and int(profile.get("eligible_match_count", 0) or 0) >= MINIMUM_USABLE_MATCHES
        for profile in summaries.values()
    )
    expected_summary = {
        "profile_count": len(summaries),
        "eligible_profile_count": usable_count,
        "eligible_match_count": len(flat_rows),
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise CanonicalCorpusError("canonical corpus summary count mismatch")
    flat_rows.sort(key=lambda row: (str(row["profile_id"]), int(row["start_time"]), int(row["match_id"])))
    return CanonicalCalibrationCorpus(payload, tuple(flat_rows), summaries, completion, checksum)


def load_canonical_corpus(path: str | Path) -> CanonicalCalibrationCorpus:
    corpus_path = Path(path)
    try:
        raw = corpus_path.read_bytes()
        payload = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise CanonicalCorpusError(f"cannot read canonical V6.1 corpus: {corpus_path}") from exc
    if not isinstance(payload, Mapping):
        raise CanonicalCorpusError("canonical corpus must be an object")
    return validate_canonical_corpus(payload, checksum=hashlib.sha256(raw).hexdigest())


def canonical_rows(corpus: CanonicalCalibrationCorpus) -> list[dict[str, Any]]:
    """Return flattened rows only after canonical bytes have been validated."""

    return [dict(row) for row in corpus.matches]


__all__ = [
    "CANONICAL_MATCH_FIELDS",
    "CANONICAL_OPTIONAL_MATCH_FIELDS",
    "CANONICAL_SCHEMA_VERSION",
    "CANONICAL_SESSION_POLICY",
    "CANONICAL_WINDOW_DAYS",
    "CANONICAL_WINDOW_SECONDS",
    "CanonicalCalibrationCorpus",
    "CanonicalCorpusError",
    "LEGACY_CANONICAL_SCHEMA_VERSION",
    "MINIMUM_USABLE_MATCHES",
    "PER_PROFILE_WINDOW_MODE",
    "SUPPORTED_CANONICAL_SCHEMA_VERSIONS",
    "canonical_history",
    "canonical_rows",
    "load_canonical_corpus",
    "normalize_calibration_history",
    "validate_canonical_corpus",
]
