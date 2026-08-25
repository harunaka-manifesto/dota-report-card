"""Compatibility/provenance audit for reuse of the private V6 corpus.

The audit is intentionally aggregate-only.  It validates the legacy compact
corpus and the already-frozen split without returning profile or match keys.
The input bytes are never rewritten.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.ingestion.summary_history_contract import (
    OPTIONAL_FIELDS,
    OPTIONAL_PUBLIC_COVERAGE_MINIMUMS,
    REQUIRED_FIELDS,
    SUMMARY_HISTORY_PROJECTION,
    SUMMARY_HISTORY_PROJECTION_VERSION,
)
from app.player_analysis_v6.calibration_corpus import (
    CalibrationCorpusError,
    validate_calibration_corpus,
)
from app.player_analysis_v61.calibration_corpus import (
    CANONICAL_SCHEMA_VERSION,
    CANONICAL_WINDOW_DAYS,
    CANONICAL_WINDOW_SECONDS,
    LEGACY_CANONICAL_SCHEMA_VERSION,
    MINIMUM_USABLE_MATCHES,
    PER_PROFILE_WINDOW_MODE,
    SUPPORTED_CANONICAL_SCHEMA_VERSIONS,
    CanonicalCorpusError,
    load_canonical_corpus,
)

AUDIT_VERSION = "v61-corpus-compatibility-1.0.0"
CANONICAL_AUDIT_VERSION = "v61-canonical-corpus-audit-1.1.0"
EXPECTED_CORPUS_SHA256 = "1cbce329f903ccad922aeddb93046b6aa2e505004937ebaaec1b854d853e41bd"
EXPECTED_SPLIT_SEED = 6000
EXPECTED_TRAIN_COUNT = 791
EXPECTED_HOLDOUT_COUNT = 339
EXPECTED_PROFILE_COUNT = EXPECTED_TRAIN_COUNT + EXPECTED_HOLDOUT_COUNT
EXPECTED_WINDOW_DAYS = 365
PROFILE_HASH = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_DIMENSION_KEYS = frozenset(
    {"rank", "rank_tier", "average_rank", "mmr", "mmr_bucket", "skill", "skill_bracket", "medal"}
)
IDENTIFIER_KEYS = frozenset({"profile_id", "match_id", "account_id", "player_id", "steam_id", "ids"})

PROVENANCE = {
    "collection_transport": "legacy_paginated",
    "analytical_compatibility": "canonical_projection_compact_normalized",
    "one_physical_request_proven": False,
    "raw_payload_hash_available": False,
}


class CompatibilityAuditError(ValueError):
    """Raised when existing-corpus reuse cannot satisfy the V6.1 contract."""


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def audit_checksum(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "audit_checksum"}
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def profile_digest(values: Sequence[Any]) -> str:
    return hashlib.sha256("\n".join(sorted(map(str, values))).encode("utf-8")).hexdigest()


def _walk_forbidden(value: Any, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            folded = str(key).casefold()
            if folded in FORBIDDEN_DIMENSION_KEYS or "mmr" in folded or folded.startswith("rank"):
                if folded == "rank_or_mmr_used" and item is False:
                    continue
                raise CompatibilityAuditError(f"forbidden rank/MMR field at {path}")
            if isinstance(item, float) and not math.isfinite(item):
                raise CompatibilityAuditError(f"non-finite value at {path}.{key}")
            _walk_forbidden(item, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _walk_forbidden(item, path=f"{path}[{index}]")


def _assert_aggregate_privacy(value: Any, *, private_values: set[str]) -> None:
    """Reject raw identifier keys/values from an aggregate audit payload."""

    def visit(item: Any, path: str) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                if (
                    str(key).casefold() in IDENTIFIER_KEYS
                    and not path.endswith("canonical_required_field_coverage")
                ):
                    raise CompatibilityAuditError(f"aggregate contains identifier field at {path}")
                visit(nested, f"{path}.{key}")
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            for index, nested in enumerate(item):
                visit(nested, f"{path}[{index}]")
        elif isinstance(item, str) and item in private_values:
            raise CompatibilityAuditError(f"aggregate contains a private identifier at {path}")

    visit(value, "root")


def _load_json(path: str | Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompatibilityAuditError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, Mapping):
        raise CompatibilityAuditError(f"{label} must be an object")
    return value


def _canonical_coverage(
    profiles: Sequence[Mapping[str, Any]],
    field: str,
    *,
    section: str = "required_field_coverage",
) -> float:
    numerator = denominator = 0.0
    for profile in profiles:
        audit = profile.get("history_audit")
        if not isinstance(audit, Mapping):
            continue
        raw_count = audit.get("raw_count")
        coverage = audit.get(section)
        if isinstance(raw_count, int) and raw_count > 0 and isinstance(coverage, Mapping):
            denominator += raw_count
            value = coverage.get(field)
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                numerator += raw_count * float(value)
    return numerator / denominator if denominator else 0.0


def _canonical_window_audit(corpus: Any) -> dict[str, Any]:
    if corpus.payload["schema_version"] == LEGACY_CANONICAL_SCHEMA_VERSION:
        window = corpus.payload["window"]
        return {
            "days": window.get("days"),
            "ordered": int(window["start_time"]) < int(window["end_time"]),
            "exact_365_days": window.get("days") == EXPECTED_WINDOW_DAYS,
        }

    windows = [
        corpus.collection_window_for_profile(profile_id)
        for profile_id in corpus.profile_ids
    ]
    distinct_windows = {
        (
            int(window["days"]),
            int(window["start_time"]),
            int(window["end_time"]),
        )
        for window in windows
    }
    all_ordered = all(
        int(window["start_time"]) < int(window["end_time"])
        for window in windows
    )
    all_exact = all(
        window.get("days") == CANONICAL_WINDOW_DAYS
        and int(window["end_time"]) - int(window["start_time"]) == CANONICAL_WINDOW_SECONDS
        for window in windows
    )
    all_matches_within_window = all(
        int(window["start_time"]) <= int(row["start_time"]) <= int(window["end_time"])
        for row in corpus.matches
        for window in [corpus.collection_window_for_profile(str(row["profile_id"]))]
    )
    return {
        "mode": PER_PROFILE_WINDOW_MODE,
        "days": CANONICAL_WINDOW_DAYS,
        "profile_window_count": len(windows),
        "distinct_window_count": len(distinct_windows),
        "all_ordered": all_ordered,
        "all_exact_365_days": all_exact,
        "all_matches_within_declared_profile_window": all_matches_within_window,
    }


def audit_canonical(
    corpus_path: str | Path,
    split_manifest_path: str | Path,
    *,
    authorization_reference: str | None = None,
) -> dict[str, Any]:
    """Audit the newly collected canonical bytes without an expected SHA."""

    try:
        corpus = load_canonical_corpus(corpus_path)
    except CanonicalCorpusError as exc:
        raise CompatibilityAuditError(str(exc)) from exc
    split = _load_json(split_manifest_path, "split manifest")
    corpus_sha256 = sha256_file(corpus_path)
    profile_ids = set(corpus.profile_ids)
    train_raw, holdout_raw = split.get("train_profile_ids"), split.get("holdout_profile_ids")
    if not isinstance(train_raw, list) or not isinstance(holdout_raw, list):
        raise CompatibilityAuditError("split manifest must contain train and holdout profile lists")
    train, holdout = set(map(str, train_raw)), set(map(str, holdout_raw))
    split_integrity = {
        "seed": split.get("seed"),
        "algorithm": split.get("algorithm"),
        "train_profile_count": len(train),
        "holdout_profile_count": len(holdout),
        "overlap_count": len(train & holdout),
        "population_match": train | holdout == profile_ids,
        "usable_population_match": train | holdout == set(corpus.usable_profile_ids),
        "train_digest": profile_digest(tuple(train)),
        "holdout_digest": profile_digest(tuple(holdout)),
        "manifest_train_digest_match": split.get("train_digest") == profile_digest(tuple(train)),
        "manifest_holdout_digest_match": split.get("holdout_digest") == profile_digest(tuple(holdout)),
        "corpus_checksum_match": split.get("corpus_sha256") == corpus_sha256,
        "split_checksum": sha256_file(split_manifest_path),
    }
    split_integrity["passed"] = bool(
        split_integrity["seed"] == EXPECTED_SPLIT_SEED
        and split_integrity["train_profile_count"] == EXPECTED_TRAIN_COUNT
        and split_integrity["holdout_profile_count"] == EXPECTED_HOLDOUT_COUNT
        and split_integrity["overlap_count"] == 0
        and split_integrity["population_match"]
        and split_integrity["usable_population_match"]
        and split_integrity["manifest_train_digest_match"]
        and split_integrity["manifest_holdout_digest_match"]
        and split_integrity["corpus_checksum_match"]
    )
    profiles = tuple(corpus.profile_summaries.values())
    exclusion_reasons = Counter(
        str(reason)
        for profile in profiles
        for reason, count in (profile.get("eligibility_audit", {}).get("exclusion_reasons", {}) or {}).items()
        for _ in range(int(count) if isinstance(count, int) and count > 0 else 0)
    )
    profile_rules = {
        "pseudonymous_profile_ids": all(PROFILE_HASH.fullmatch(profile_id) for profile_id in profile_ids),
        "duplicate_profile_ids": len(profile_ids) == len(profiles),
        "minimum_usable_match_count": all(
            int(profile.get("eligible_match_count", 0) or 0) >= MINIMUM_USABLE_MATCHES
            for profile in profiles
        ),
        "profile_row_counts_match": all(
            sum(str(row["profile_id"]) == str(profile["profile_id"]) for row in corpus.matches)
            == int(profile.get("eligible_match_count", 0) or 0)
            for profile in profiles
        ),
    }
    source = corpus.payload["source"]
    manifest = corpus.payload["request_manifest"]
    schema_version = corpus.payload["schema_version"]
    source_projection = {
        "exact": manifest.get("projection") == list(SUMMARY_HISTORY_PROJECTION),
        "canonical_projection_version": SUMMARY_HISTORY_PROJECTION_VERSION,
        "canonical_schema_version": schema_version,
        "provider_limit": manifest.get("provider_limit"),
        "retry_limit": manifest.get("retry_limit"),
    }
    window_audit = _canonical_window_audit(corpus)
    leaver_audit = {
        "raw_coverage": _canonical_coverage(profiles, "leaver_status"),
        "included_count": len(corpus.matches),
        "included_valid_count": sum(row.get("leaver_status") in {0, 1} for row in corpus.matches),
        "excluded_missing_count": exclusion_reasons.get("missing_leaver_status", 0),
        "excluded_invalid_count": exclusion_reasons.get("invalid_leaver_status", 0),
        "excluded_abandoned_count": exclusion_reasons.get("abandoned", 0),
        "excluded_rows_audited": True,
    }
    failure_reasons: list[str] = []
    if len(profile_ids) != EXPECTED_PROFILE_COUNT:
        failure_reasons.append("canonical_profile_population_count_failed")
    if len(corpus.usable_profile_ids) != EXPECTED_PROFILE_COUNT:
        failure_reasons.append("canonical_usable_profile_count_failed")
    if not split_integrity["population_match"] or not split_integrity["usable_population_match"]:
        failure_reasons.append("new_approved_split_or_population_required")
    if not split_integrity["corpus_checksum_match"]:
        failure_reasons.append("split_must_be_rebound_to_actual_corpus_checksum")
    core_passed = bool(
        len(profile_ids) == EXPECTED_PROFILE_COUNT
        and len(corpus.usable_profile_ids) == EXPECTED_PROFILE_COUNT
        and split_integrity["passed"]
        and all(profile_rules.values())
        and source_projection["exact"]
        and source.get("request_count_per_profile") == 1
        and source.get("detail_requests") == 0
        and source.get("parse_requests") == 0
        and source.get("rank_or_mmr_used") is False
        and (
            (
                window_audit["ordered"]
                and window_audit["exact_365_days"]
            )
            if schema_version == LEGACY_CANONICAL_SCHEMA_VERSION
            else (
                window_audit["all_ordered"]
                and window_audit["all_exact_365_days"]
                and window_audit["all_matches_within_declared_profile_window"]
            )
        )
        and leaver_audit["included_count"] == leaver_audit["included_valid_count"]
        and leaver_audit["excluded_rows_audited"]
    )
    audit: dict[str, Any] = {
        "version": CANONICAL_AUDIT_VERSION,
        "corpus_schema": schema_version,
        "corpus_sha256": corpus_sha256,
        "corpus_population": {
            "profile_count": len(profile_ids),
            "usable_profile_count": len(corpus.usable_profile_ids),
            "match_count": len(corpus.matches),
            "profile_population_digest": profile_digest(tuple(profile_ids)),
        },
        "split": split_integrity,
        "window": window_audit,
        "profile_rules": profile_rules,
        "canonical_required_field_coverage": {
            field: _canonical_coverage(profiles, field)
            for field in sorted(REQUIRED_FIELDS)
        },
        "optional_field_coverage": {
            field: _canonical_coverage(profiles, field, section="optional_field_coverage")
            for field in sorted(OPTIONAL_FIELDS)
        },
        "leaver_status": leaver_audit,
        "exclusion_reasons": dict(sorted(exclusion_reasons.items())),
        "source_projection": source_projection,
        "provenance": {
            "collection_transport": "canonical_one_request_summary_history",
            "analytical_compatibility": "canonical_v61_materialized",
            "one_physical_request_proven": True,
            "raw_payload_hash_available": True,
            "detail_requests": 0,
            "parse_requests": 0,
            "rank_or_mmr_used": False,
        },
        "v6_0_comparison_context": {"present": False, "previously_evaluated": False},
        "v61_holdout_evaluated": False,
        "core_passed": core_passed,
        "failure_reasons": sorted(set(failure_reasons)),
        "authorization": {
            "reuse_reference": str(authorization_reference).strip() if authorization_reference else "",
            "reuse_authorized": bool(str(authorization_reference).strip()),
            "statistical_approval": False,
            "dota_language_approval": False,
            "data_basis_approval": False,
        },
        "aggregate_identifier_free": True,
    }
    _assert_aggregate_privacy(audit, private_values=profile_ids)
    audit["audit_checksum"] = audit_checksum(audit)
    return audit


def _source_projection_audit(source: Mapping[str, Any]) -> dict[str, Any]:
    observed = source.get("projections")
    exact = observed == list(SUMMARY_HISTORY_PROJECTION)
    return {
        "exact": exact,
        "observed_count": len(observed) if isinstance(observed, list) else 0,
        "canonical_count": len(SUMMARY_HISTORY_PROJECTION),
        "canonical_projection_version": SUMMARY_HISTORY_PROJECTION_VERSION,
        "legacy_projection_version": "summary-projection-2.0.0",
    }


def _profile_field_coverage(rows: Sequence[Mapping[str, Any]], field: str) -> float:
    return sum(row.get(field) is not None for row in rows) / len(rows) if rows else 0.0


def _session_audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    sessions: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        sessions[(str(row["profile_id"]), str(row["session_id"]))].append(row)
    invalid = 0
    for session_rows in sessions.values():
        ordered = sorted(session_rows, key=lambda row: (int(row["start_time"]), int(row["match_id"])))
        indices = [int(row["session_index"]) for row in ordered]
        if indices != list(range(1, len(indices) + 1)):
            invalid += 1
    return {
        "session_count": len(sessions),
        "invalid_session_count": invalid,
        "chronology_valid": invalid == 0,
        "corrupt_match_count": sum(bool(row.get("session_corrupt")) for row in rows),
    }


def _v60_evidence(path: Path, corpus_sha256: str) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "previously_evaluated": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"present": False, "previously_evaluated": False, "invalid": True}
    corpus = payload.get("corpus") if isinstance(payload, Mapping) else None
    if not isinstance(corpus, Mapping):
        return {"present": False, "previously_evaluated": False, "invalid": True}
    matches = corpus.get("holdout_match_count")
    valid = (
        corpus.get("checksum") == corpus_sha256
        and corpus.get("train_profile_count") == EXPECTED_TRAIN_COUNT
        and corpus.get("holdout_profile_count") == EXPECTED_HOLDOUT_COUNT
        and corpus.get("sealed_holdout_profile_count") == EXPECTED_HOLDOUT_COUNT
    )
    return {
        "present": True,
        "previously_evaluated": bool(valid),
        "version": payload.get("version"),
        "holdout_match_count": matches if isinstance(matches, int) else None,
        "evaluation_checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def audit_reuse(
    corpus_path: str | Path,
    split_manifest_path: str | Path,
    *,
    expected_corpus_sha256: str = EXPECTED_CORPUS_SHA256,
    authorization_reference: str | None = None,
    v60_evaluation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return a deterministic aggregate compatibility audit.

    The function may pass core compatibility without an authorization
    reference.  That deliberately blocks State B while allowing the audit and
    implementation work to proceed.
    """

    corpus_path = Path(corpus_path)
    split_path = Path(split_manifest_path)
    raw = corpus_path.read_bytes()
    try:
        canonical_payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CompatibilityAuditError("corpus is not valid JSON") from exc
    if (
        isinstance(canonical_payload, Mapping)
        and canonical_payload.get("schema_version") in SUPPORTED_CANONICAL_SCHEMA_VERSIONS
    ):
        return audit_canonical(
            corpus_path,
            split_path,
            authorization_reference=authorization_reference,
        )
    corpus_sha256 = hashlib.sha256(raw).hexdigest()
    if corpus_sha256 != expected_corpus_sha256:
        raise CompatibilityAuditError(
            f"corpus checksum mismatch: expected {expected_corpus_sha256}, observed {corpus_sha256}"
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CompatibilityAuditError("corpus is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise CompatibilityAuditError("corpus must be an object")
    try:
        validated = validate_calibration_corpus(payload, checksum=corpus_sha256)
    except CalibrationCorpusError as exc:
        raise CompatibilityAuditError(str(exc)) from exc
    split = _load_json(split_path, "split manifest")
    _walk_forbidden(payload)
    _walk_forbidden(split)

    corpus_profiles = set(validated.profile_ids)
    train = split.get("train_profile_ids")
    holdout = split.get("holdout_profile_ids")
    if not isinstance(train, list) or not isinstance(holdout, list):
        raise CompatibilityAuditError("split manifest must contain train and holdout profile lists")
    train_set, holdout_set = set(map(str, train)), set(map(str, holdout))
    split_integrity = {
        "seed": split.get("seed"),
        "algorithm": split.get("algorithm"),
        "train_profile_count": len(train_set),
        "holdout_profile_count": len(holdout_set),
        "overlap_count": len(train_set & holdout_set),
        "population_match": train_set | holdout_set == corpus_profiles,
        "train_digest": profile_digest(tuple(train_set)),
        "holdout_digest": profile_digest(tuple(holdout_set)),
        "manifest_train_digest_match": split.get("train_digest") == profile_digest(tuple(train_set)),
        "manifest_holdout_digest_match": split.get("holdout_digest") == profile_digest(tuple(holdout_set)),
        "corpus_checksum_match": split.get("corpus_sha256") == corpus_sha256,
        "split_checksum": hashlib.sha256(split_path.read_bytes()).hexdigest(),
    }
    split_integrity["passed"] = bool(
        split_integrity["seed"] == EXPECTED_SPLIT_SEED
        and split_integrity["train_profile_count"] == EXPECTED_TRAIN_COUNT
        and split_integrity["holdout_profile_count"] == EXPECTED_HOLDOUT_COUNT
        and split_integrity["overlap_count"] == 0
        and split_integrity["population_match"]
        and split_integrity["manifest_train_digest_match"]
        and split_integrity["manifest_holdout_digest_match"]
        and split_integrity["corpus_checksum_match"]
    )

    rows = tuple(validated.matches)
    profiles = tuple(validated.profile_summaries.values())
    profile_source_counts = [int(profile.get("source_match_count", 0) or 0) for profile in profiles]
    profile_rows: Counter[str] = Counter(str(row["profile_id"]) for row in rows)
    pseudonymous = all(isinstance(profile, str) and PROFILE_HASH.fullmatch(profile) for profile in corpus_profiles)
    profile_rules = {
        "pseudonymous_profile_ids": pseudonymous,
        "duplicate_profile_ids": len(corpus_profiles) == len(profiles),
        "history_count_below_10000": max(profile_source_counts, default=0) < 10_000,
        "missing_pagination_tag_under_200": all(
            profile.get("history_pagination_version") not in (None, "")
            or int(profile.get("source_match_count", 0) or 0) < 200
            for profile in profiles
        ),
        "profile_row_counts_match": all(profile_rows[str(profile["profile_id"])] == int(profile["eligible_match_count"]) for profile in profiles),
    }
    required_coverage = {
        field: sum(row.get({
            "match_id": "match_id",
            "player_slot": "_missing",
            "radiant_win": "_missing",
            "duration": "duration_seconds",
            "game_mode": "game_mode",
            "lobby_type": "lobby_type",
            "hero_id": "hero_id",
            "start_time": "start_time",
            "kills": "kills",
            "deaths": "deaths",
            "assists": "assists",
            "leaver_status": "_missing",
        }.get(field, field)) is not None for row in rows) / len(rows)
        if rows
        else 0.0
        for field in sorted(REQUIRED_FIELDS)
    }
    # Compact V6 rows intentionally no longer carry raw transport-only fields.
    required_compact = {
        field: _profile_field_coverage(rows, field)
        for field in (
            "start_time", "duration_seconds", "won", "kills", "deaths", "assists",
            "hero_id", "patch", "session_id", "session_index", "session_corrupt",
        )
    }
    optional_coverage = {
        field: _profile_field_coverage(rows, field)
        for field in sorted(set(OPTIONAL_FIELDS) | {"lane_context", "region", "source_version"})
    }
    optional_availability = {
        field: optional_coverage.get(field, 0.0) >= OPTIONAL_PUBLIC_COVERAGE_MINIMUMS.get(field, 1.0)
        for field in sorted(optional_coverage)
    }
    unavailable_branches = []
    if not optional_availability.get("lane", False) and not optional_availability.get("lane_context", False):
        unavailable_branches.append("lane-dependent")
    if not optional_availability.get("party_size", False):
        unavailable_branches.append("party-dependent")
    if not optional_availability.get("hero_variant", False):
        unavailable_branches.append("variant-dependent")
    if "leagueid" not in optional_coverage or optional_coverage.get("leagueid", 0.0) == 0.0:
        unavailable_branches.append("league-dependent")

    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise CompatibilityAuditError("corpus source metadata is missing")
    source_projection = _source_projection_audit(source)
    session = _session_audit(rows)
    window = payload.get("window")
    window_audit = {
        "days": window.get("days") if isinstance(window, Mapping) else None,
        "ordered": bool(isinstance(window, Mapping) and window.get("start_time", 0) < window.get("end_time", 0)),
        "exact_365_days": bool(isinstance(window, Mapping) and window.get("days") == EXPECTED_WINDOW_DAYS),
    }
    core_passed = bool(
        corpus_sha256 == expected_corpus_sha256
        and len(corpus_profiles) == EXPECTED_PROFILE_COUNT
        and split_integrity["passed"]
        and profile_rules["pseudonymous_profile_ids"]
        and profile_rules["history_count_below_10000"]
        and profile_rules["missing_pagination_tag_under_200"]
        and profile_rules["profile_row_counts_match"]
        and source_projection["exact"]
        and window_audit["ordered"]
        and window_audit["exact_365_days"]
        and session["chronology_valid"]
        and all(value >= 1.0 for value in required_compact.values())
    )
    v60_path = Path(v60_evaluation_path) if v60_evaluation_path else corpus_path.parent / "evaluation" / "holdout-6.0.0-reviewable.json"
    audit: dict[str, Any] = {
        "version": AUDIT_VERSION,
        "corpus_schema": payload.get("schema_version"),
        "corpus_sha256": corpus_sha256,
        "expected_corpus_sha256": expected_corpus_sha256,
        "corpus_population": {
            "profile_count": len(corpus_profiles),
            "match_count": len(rows),
            "profile_population_digest": profile_digest(tuple(corpus_profiles)),
        },
        "split": split_integrity,
        "window": window_audit,
        "profile_rules": profile_rules,
        "required_compact_field_coverage": required_compact,
        "canonical_required_field_coverage": required_coverage,
        "optional_field_coverage": optional_coverage,
        "optional_public_availability": optional_availability,
        "forced_suppression": {
            "unavailable_branches": sorted(set(unavailable_branches)),
            "lane_context_coverage_gate": optional_coverage.get("lane_context", 0.0),
            "party_size_coverage_gate": optional_coverage.get("party_size", 0.0),
            "hero_variant_coverage_gate": optional_coverage.get("hero_variant", 0.0),
        },
        "source_projection": source_projection,
        "session_chronology": session,
        "taxonomy": {"version": "current-runtime-taxonomy", "legacy_disagreement_count": None},
        "provenance": dict(PROVENANCE),
        "v6_0_comparison_context": _v60_evidence(v60_path, corpus_sha256),
        "v61_holdout_evaluated": False,
        "core_passed": core_passed,
        "authorization": {
            "reuse_reference": str(authorization_reference).strip() if authorization_reference else "",
            "reuse_authorized": bool(str(authorization_reference).strip()),
            "statistical_approval": False,
            "dota_language_approval": False,
            "data_basis_approval": False,
        },
        "aggregate_identifier_free": True,
    }
    _assert_aggregate_privacy(audit, private_values=corpus_profiles)
    audit["audit_checksum"] = audit_checksum(audit)
    return audit


def load_compatibility_audit(path: str | Path) -> dict[str, Any]:
    payload = dict(_load_json(path, "compatibility audit"))
    observed = payload.get("audit_checksum")
    if not isinstance(observed, str) or observed != audit_checksum(payload):
        raise CompatibilityAuditError("compatibility audit checksum is missing or invalid")
    if payload.get("aggregate_identifier_free") is not True:
        raise CompatibilityAuditError("compatibility audit is not identifier-free")
    return payload


def require_compatible_audit(
    audit_path: str | Path,
    *,
    corpus_path: str | Path,
    split_manifest_path: str | Path,
    require_authorization: bool = False,
    canonical_only: bool = False,
) -> dict[str, Any]:
    audit = load_compatibility_audit(audit_path)
    if audit.get("corpus_sha256") != sha256_file(corpus_path):
        raise CompatibilityAuditError("compatibility audit does not match corpus bytes")
    if canonical_only and audit.get("corpus_schema") != CANONICAL_SCHEMA_VERSION:
        raise CompatibilityAuditError(
            "latest canonical V6.1 corpus audit is required; "
            "legacy or superseded schema evidence cannot authorize release"
        )
    if audit.get("split", {}).get("split_checksum") != sha256_file(split_manifest_path):
        raise CompatibilityAuditError("compatibility audit does not match split bytes")
    if audit.get("core_passed") is not True:
        raise CompatibilityAuditError("compatibility audit core requirements did not pass")
    if require_authorization and audit.get("authorization", {}).get("reuse_authorized") is not True:
        raise CompatibilityAuditError("reuse authorization reference is required before State B")
    return audit


__all__ = [
    "AUDIT_VERSION",
    "CANONICAL_AUDIT_VERSION",
    "CompatibilityAuditError",
    "EXPECTED_CORPUS_SHA256",
    "EXPECTED_HOLDOUT_COUNT",
    "EXPECTED_PROFILE_COUNT",
    "EXPECTED_SPLIT_SEED",
    "EXPECTED_TRAIN_COUNT",
    "PROVENANCE",
    "audit_checksum",
    "audit_reuse",
    "audit_canonical",
    "load_compatibility_audit",
    "profile_digest",
    "require_compatible_audit",
    "sha256_file",
]
