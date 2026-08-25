#!/usr/bin/env python3
"""Materialize the deterministic offline V6.1 replacement corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.player_analysis_v61.calibration_corpus import (  # noqa: E402
    CANONICAL_SCHEMA_VERSION,
    CANONICAL_WINDOW_DAYS,
    CANONICAL_WINDOW_SECONDS,
    LEGACY_CANONICAL_SCHEMA_VERSION,
    MINIMUM_USABLE_MATCHES,
    PER_PROFILE_WINDOW_MODE,
    CanonicalCorpusError,
    load_canonical_corpus,
    validate_canonical_corpus,
)
from app.player_analysis_v61.corpus_reuse import profile_digest  # noqa: E402

from scripts.prepare_v61_replacement_holdout import (  # noqa: E402
    ORDER_DIGEST_FORMAT,
    _order_digest,
    serialize_manifest,
    sha256_file,
    write_private_manifest,
)
from scripts.prepare_v61_replacement_holdout import (  # noqa: E402
    SCHEMA_VERSION as PRECOMMIT_SCHEMA_VERSION,
)

COLLECTION_RELEASE_SHA = "48de08d851df083b6ab3282cd6231618a90fbbb1"
SCHEMA_RELEASE_SHA = "7908f21c7f812ee72065c378abd97bfaa1270a97"
EXPECTED_PRECOMMIT_SHA256 = "c6323d3da5eb93501b1f998ae80c5e780ab49e4eaddaa36221b571e8a25e3cda2"
EXPECTED_REPLACEMENT_SCAN_SHA256 = "22a01603aff371db87207c77ed055c775975adaefa5998bcc975b3dcc67611ad"
EXPECTED_CANDIDATE_ORDER_SHA256 = "7957c80bdd059013eac188e8244441289c2fe5165f161ceba0fd4b8e889d79fe"
EXPECTED_HISTORICAL_CORPUS_SHA256 = "273ef68f46746567530a4cb6c6520a5b9b257c8ac35007adb87bedc7ab6ece3e"
EXPECTED_HISTORICAL_SPLIT_SHA256 = "174caebdaf13b45f70423002216007abac00510aeecc1a1df686152c52aec1c5"
EXPECTED_CANDIDATE_COUNT = 1_224
EXPECTED_SCAN_ELIGIBLE_COUNT = 379
EXPECTED_SELECTED_COUNT = 339
EXPECTED_SELECTED_LAST_INDEX = 1_070
EXPECTED_UNUSED_ELIGIBLE_COUNT = 40
EXPECTED_TRAIN_COUNT = 791
EXPECTED_HOLDOUT_COUNT = 339
EXPECTED_POPULATION_COUNT = 1_130
EXPECTED_SPLIT_SEED = 6_000
REPLACEMENT_WINDOW = {
    "days": CANONICAL_WINDOW_DAYS,
    "start_time": 1_756_101_756,
    "end_time": 1_787_637_756,
}
MATERIALIZATION_TIMESTAMP = "2026-08-25T00:00:00+00:00"
PROFILE_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RELEASE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SCAN_SCHEMA_VERSION = "v61-replacement-holdout-scan-1.0.0"
SELECTION_SCHEMA_VERSION = "v61-replacement-selection-1.0.0"
RAW_SPLIT_VERSION = "v61-replacement-split-1.0.0"


class SelectionError(ValueError):
    """Raised when immutable replacement-selection inputs fail closed."""


@dataclass(frozen=True, slots=True)
class SelectionResult:
    corpus: dict[str, Any]
    raw_split: dict[str, Any]
    evidence: dict[str, Any]
    corpus_sha256: str
    raw_split_sha256: str
    bound_split_sha256: str


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SelectionError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise SelectionError(f"{label} must be a JSON object")
    return value


def _require_sha(value: str, *, label: str, length: int = 64) -> str:
    pattern = SHA256_PATTERN if length == 64 else RELEASE_SHA_PATTERN
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise SelectionError(f"{label} is not a lowercase SHA-256/release SHA")
    return value


def _same_sha(path: Path, expected: str, *, label: str) -> str:
    _require_sha(expected, label=f"expected {label}")
    actual = sha256_file(path)
    if actual != expected:
        raise SelectionError(f"{label} SHA-256 differs")
    return actual


def _profile_ids(value: Any, *, label: str, expected_count: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) != expected_count:
        raise SelectionError(f"{label} count is invalid")
    result: list[str] = []
    seen: set[str] = set()
    for profile_id in value:
        if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.fullmatch(profile_id):
            raise SelectionError(f"{label} contains an invalid profile ID")
        if profile_id in seen:
            raise SelectionError(f"{label} contains duplicate profile IDs")
        seen.add(profile_id)
        result.append(profile_id)
    return tuple(result)


def _validate_precommit(
    path: Path,
    *,
    expected_sha256: str = EXPECTED_PRECOMMIT_SHA256,
    expected_order_sha256: str = EXPECTED_CANDIDATE_ORDER_SHA256,
    expected_candidate_count: int = EXPECTED_CANDIDATE_COUNT,
    collection_release_sha: str = COLLECTION_RELEASE_SHA,
) -> tuple[dict[str, Any], tuple[int, ...], str]:
    actual_sha256 = _same_sha(path, expected_sha256, label="precommit manifest")
    payload = _read_object(path, "precommit manifest")
    raw_ids = payload.get("candidate_account_ids")
    if not isinstance(raw_ids, list) or len(raw_ids) != expected_candidate_count:
        raise SelectionError("precommit candidate count is invalid")
    account_ids: list[int] = []
    seen: set[int] = set()
    for value in raw_ids:
        if type(value) is not int or value <= 0:
            raise SelectionError("precommit account ID is invalid")
        if value in seen:
            raise SelectionError("precommit contains duplicate account IDs")
        seen.add(value)
        account_ids.append(value)
    if payload.get("schema_version") != PRECOMMIT_SCHEMA_VERSION:
        raise SelectionError("precommit schema is invalid")
    if payload.get("release_sha") != collection_release_sha:
        raise SelectionError("precommit collection release SHA differs")
    if payload.get("candidate_count") != expected_candidate_count:
        raise SelectionError("precommit candidate count metadata is invalid")
    if payload.get("candidate_order_digest_format") != ORDER_DIGEST_FORMAT:
        raise SelectionError("precommit candidate order format is invalid")
    order_sha256 = _order_digest(account_ids)
    if payload.get("candidate_order_sha256") != order_sha256 or order_sha256 != expected_order_sha256:
        raise SelectionError("precommit candidate order SHA-256 differs")
    exclusions = payload.get("exclusions")
    if not isinstance(exclusions, Mapping) or exclusions.get("current_population_overlap_count") != 0:
        raise SelectionError("precommit overlap invariant failed")
    return payload, tuple(account_ids), actual_sha256


def _validate_historical_inputs(
    corpus_path: Path,
    split_path: Path,
    *,
    expected_corpus_sha256: str,
    expected_split_sha256: str,
) -> tuple[Any, dict[str, Any], tuple[str, ...], tuple[str, ...], str, str]:
    corpus_sha256 = _same_sha(corpus_path, expected_corpus_sha256, label="historical corpus")
    split_sha256 = _same_sha(split_path, expected_split_sha256, label="historical split")
    try:
        corpus = load_canonical_corpus(corpus_path)
    except CanonicalCorpusError as exc:
        raise SelectionError("historical corpus is not canonical") from exc
    if corpus.payload.get("schema_version") != LEGACY_CANONICAL_SCHEMA_VERSION:
        raise SelectionError("historical corpus must be V2.0")
    if len(corpus.profile_ids) != EXPECTED_POPULATION_COUNT or len(corpus.usable_profile_ids) != EXPECTED_POPULATION_COUNT:
        raise SelectionError("historical corpus population is invalid")
    historical_window = corpus.payload.get("window")
    if not isinstance(historical_window, Mapping) or not _exact_window(historical_window):
        raise SelectionError("historical corpus window is invalid")
    split = _read_object(split_path, "historical split")
    train_ids = _profile_ids(split.get("train_profile_ids"), label="historical train", expected_count=EXPECTED_TRAIN_COUNT)
    holdout_ids = _profile_ids(split.get("holdout_profile_ids"), label="historical holdout", expected_count=EXPECTED_HOLDOUT_COUNT)
    train_set, holdout_set = set(train_ids), set(holdout_ids)
    if split.get("seed") != EXPECTED_SPLIT_SEED or split.get("corpus_schema") != LEGACY_CANONICAL_SCHEMA_VERSION:
        raise SelectionError("historical split contract is invalid")
    if split.get("corpus_sha256") != corpus_sha256:
        raise SelectionError("historical split is not bound to the historical corpus")
    if split.get("train_profile_count") != EXPECTED_TRAIN_COUNT or split.get("holdout_profile_count") != EXPECTED_HOLDOUT_COUNT:
        raise SelectionError("historical split count metadata is invalid")
    if train_set & holdout_set or train_set | holdout_set != set(corpus.profile_ids):
        raise SelectionError("historical split population is invalid")
    if split.get("train_digest") != profile_digest(train_ids) or split.get("holdout_digest") != profile_digest(holdout_ids):
        raise SelectionError("historical split profile digest is invalid")
    return corpus, split, train_ids, holdout_ids, corpus_sha256, split_sha256


def _exact_window(value: Mapping[str, Any]) -> bool:
    try:
        return (
            value.get("days") == CANONICAL_WINDOW_DAYS
            and type(value.get("start_time")) is int
            and type(value.get("end_time")) is int
            and value["start_time"] < value["end_time"]
            and value["end_time"] - value["start_time"] == CANONICAL_WINDOW_SECONDS
        )
    except (KeyError, TypeError):
        return False


def _scan_corpus_payload(
    profiles: Sequence[Mapping[str, Any]],
    *,
    source: Mapping[str, Any],
    request_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    eligible_match_count = sum(int(profile.get("eligible_match_count", 0)) for profile in profiles)
    return {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "generated_at": MATERIALIZATION_TIMESTAMP,
        "request_manifest": copy.deepcopy(dict(request_manifest)),
        "source": copy.deepcopy(dict(source)),
        "window_policy": {
            "mode": PER_PROFILE_WINDOW_MODE,
            "days": CANONICAL_WINDOW_DAYS,
            "profile_window_field": "collection_window",
        },
        "profile_count": len(profiles),
        "summary": {
            "profile_count": len(profiles),
            "eligible_profile_count": sum(profile.get("status") == "eligible" for profile in profiles),
            "eligible_match_count": eligible_match_count,
        },
        "raw_identifiers_present": False,
        "profiles": [copy.deepcopy(dict(profile)) for profile in profiles],
    }


def _validate_scan(
    path: Path,
    *,
    precommit_sha256: str,
    expected_scan_sha256: str = EXPECTED_REPLACEMENT_SCAN_SHA256,
    expected_candidate_order_sha256: str = EXPECTED_CANDIDATE_ORDER_SHA256,
    expected_candidate_count: int = EXPECTED_CANDIDATE_COUNT,
    expected_eligible_count: int = EXPECTED_SCAN_ELIGIBLE_COUNT,
    expected_window: Mapping[str, Any] = REPLACEMENT_WINDOW,
    source: Mapping[str, Any],
    request_manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], dict[str, Any], str]:
    scan_sha256 = _same_sha(path, expected_scan_sha256, label="replacement scan")
    payload = _read_object(path, "replacement scan")
    if payload.get("schema_version") != SCAN_SCHEMA_VERSION:
        raise SelectionError("replacement scan schema is invalid")
    if payload.get("release_sha") != COLLECTION_RELEASE_SHA:
        raise SelectionError("replacement scan collection release SHA differs")
    if payload.get("precommit_manifest_sha256") != precommit_sha256:
        raise SelectionError("replacement scan precommit SHA differs")
    if payload.get("candidate_order_sha256") != expected_candidate_order_sha256:
        raise SelectionError("replacement scan candidate order SHA differs")
    if payload.get("candidate_count") != expected_candidate_count or payload.get("requested_candidate_count") != expected_candidate_count:
        raise SelectionError("replacement scan candidate count is invalid")
    window = payload.get("window")
    if not isinstance(window, Mapping) or dict(window) != dict(expected_window):
        raise SelectionError("replacement scan window differs")
    if payload.get("window_start") != expected_window["start_time"] or payload.get("window_end") != expected_window["end_time"] or payload.get("window_days") not in (None, expected_window["days"]):
        raise SelectionError("replacement scan window metadata is invalid")
    if (
        payload.get("success_count") != expected_candidate_count
        or payload.get("failure_count") != 0
        or payload.get("indeterminate_count") != 0
        or payload.get("eligible_count") != expected_eligible_count
        or payload.get("ineligible_count") != expected_candidate_count - expected_eligible_count
        or payload.get("detail_requests") != 0
        or payload.get("parse_requests") != 0
        or payload.get("rank_or_mmr_used") is not False
        or payload.get("raw_identifiers_present") is not False
    ):
        raise SelectionError("replacement scan aggregate invariants failed")
    accounting = payload.get("request_accounting")
    if not isinstance(accounting, Mapping) or any(
        accounting.get(key) != value
        for key, value in {
            "summary_requests_per_candidate": 1,
            "planned_summary_requests": expected_candidate_count,
            "attempted_summary_requests": expected_candidate_count,
            "known_terminal_summary_requests": expected_candidate_count,
            "indeterminate_summary_requests": 0,
            "detail_requests": 0,
            "parse_requests": 0,
            "retry_limit": 0,
        }.items()
    ):
        raise SelectionError("replacement scan request accounting is invalid")
    statuses = payload.get("candidate_statuses")
    profiles = payload.get("profiles")
    if not isinstance(statuses, list) or len(statuses) != expected_candidate_count or not isinstance(profiles, list) or len(profiles) != expected_candidate_count:
        raise SelectionError("replacement scan candidate/profile arrays are invalid")
    status_by_profile: dict[str, Mapping[str, Any]] = {}
    ordered_statuses: list[Mapping[str, Any]] = []
    for index, raw_status in enumerate(statuses):
        if not isinstance(raw_status, Mapping):
            raise SelectionError("replacement scan status is invalid")
        if raw_status.get("candidate_index") != index or raw_status.get("status") != "success":
            raise SelectionError("replacement scan has a non-success candidate")
        profile_id = raw_status.get("profile_id")
        if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.fullmatch(profile_id) or profile_id in status_by_profile:
            raise SelectionError("replacement scan has duplicate/invalid profile IDs")
        if raw_status.get("eligibility") not in {"eligible", "ineligible"}:
            raise SelectionError("replacement scan eligibility is invalid")
        status_by_profile[profile_id] = raw_status
        ordered_statuses.append(raw_status)
    profiles_by_id: dict[str, dict[str, Any]] = {}
    for raw_profile in profiles:
        if not isinstance(raw_profile, Mapping):
            raise SelectionError("replacement scan normalized profile is invalid")
        profile = dict(raw_profile)
        profile_id = profile.get("profile_id")
        if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.fullmatch(profile_id) or profile_id in profiles_by_id:
            raise SelectionError("replacement scan has duplicate/invalid normalized profiles")
        if profile_id not in status_by_profile or profile.get("status") != status_by_profile[profile_id].get("eligibility"):
            raise SelectionError("replacement scan status/profile binding is invalid")
        if "collection_window" in profile and profile["collection_window"] != dict(expected_window):
            raise SelectionError("replacement profile carries a different window")
        profiles_by_id[profile_id] = profile
    if set(profiles_by_id) != set(status_by_profile):
        raise SelectionError("replacement scan status/profile population differs")
    ordered_profiles: list[dict[str, Any]] = []
    for raw_status in ordered_statuses:
        profile = copy.deepcopy(profiles_by_id[str(raw_status["profile_id"])])
        profile["collection_window"] = dict(expected_window)
        ordered_profiles.append(profile)
    scan_payload = _scan_corpus_payload(
        ordered_profiles,
        source=source,
        request_manifest=request_manifest,
    )
    try:
        scan_corpus = validate_canonical_corpus(scan_payload, checksum=scan_sha256)
    except CanonicalCorpusError as exc:
        raise SelectionError("replacement scan profiles are not canonical") from exc
    if len(scan_corpus.profile_ids) != expected_candidate_count or len(scan_corpus.usable_profile_ids) != expected_eligible_count:
        raise SelectionError("replacement scan usable population is invalid")
    return payload, tuple(ordered_profiles), dict(expected_window), scan_sha256


def _build_corpus(
    historical: Any,
    train_ids: Sequence[str],
    selected_profiles: Sequence[Mapping[str, Any]],
    *,
    historical_window: Mapping[str, Any],
) -> dict[str, Any]:
    train_profiles: list[dict[str, Any]] = []
    for profile_id in train_ids:
        profile = copy.deepcopy(dict(historical.profile_summaries[profile_id]))
        if "collection_window" in profile:
            raise SelectionError("historical profile already has a collection window")
        profile["collection_window"] = copy.deepcopy(dict(historical_window))
        train_profiles.append(profile)
    profiles = train_profiles + [copy.deepcopy(dict(profile)) for profile in selected_profiles]
    payload = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "generated_at": MATERIALIZATION_TIMESTAMP,
        "request_manifest": copy.deepcopy(dict(historical.payload["request_manifest"])),
        "source": copy.deepcopy(dict(historical.payload["source"])),
        "window_policy": {
            "mode": PER_PROFILE_WINDOW_MODE,
            "days": CANONICAL_WINDOW_DAYS,
            "profile_window_field": "collection_window",
        },
        "profile_count": len(profiles),
        "summary": {
            "profile_count": len(profiles),
            "eligible_profile_count": sum(profile.get("status") == "eligible" for profile in profiles),
            "eligible_match_count": sum(int(profile.get("eligible_match_count", 0)) for profile in profiles),
        },
        "raw_identifiers_present": False,
        "profiles": profiles,
    }
    try:
        corpus = validate_canonical_corpus(payload)
    except CanonicalCorpusError as exc:
        raise SelectionError("materialized V2.1 corpus is invalid") from exc
    if len(corpus.profile_ids) != EXPECTED_POPULATION_COUNT or len(corpus.usable_profile_ids) != EXPECTED_POPULATION_COUNT:
        raise SelectionError("materialized corpus population is invalid")
    diagnostics = corpus.aggregate_diagnostics()
    if diagnostics["window_mode"] != PER_PROFILE_WINDOW_MODE or not diagnostics["all_profile_windows_exact_365_days"]:
        raise SelectionError("materialized profile windows are invalid")
    return payload


def _build_split(
    train_ids: Sequence[str],
    selected_ids: Sequence[str],
    *,
    corpus_sha256: str,
    historical_corpus_sha256: str,
    historical_split_sha256: str,
    candidate_order_sha256: str,
    selection_release_sha: str,
) -> dict[str, Any]:
    return {
        "version": RAW_SPLIT_VERSION,
        "algorithm": "historical_train_plus_precommitted_replacement",
        "seed": EXPECTED_SPLIT_SEED,
        "train_profile_ids": list(train_ids),
        "holdout_profile_ids": list(selected_ids),
        "train_profile_count": len(train_ids),
        "holdout_profile_count": len(selected_ids),
        "overlap_count": 0,
        "train_digest": profile_digest(train_ids),
        "holdout_digest": profile_digest(selected_ids),
        "corpus_schema": CANONICAL_SCHEMA_VERSION,
        "corpus_sha256": corpus_sha256,
        "selection_method": "precommitted_first_339_eligible",
        "selection_release_sha": selection_release_sha,
        "candidate_order_sha256": candidate_order_sha256,
        "historical_corpus_sha256": historical_corpus_sha256,
        "historical_split_sha256": historical_split_sha256,
        "population_profile_count": EXPECTED_POPULATION_COUNT,
    }


def _bound_split_sha256(raw_split: Mapping[str, Any], corpus_sha256: str) -> str:
    bound = dict(raw_split)
    bound["corpus_schema"] = CANONICAL_SCHEMA_VERSION
    bound["corpus_sha256"] = corpus_sha256
    return hashlib.sha256(serialize_manifest(bound)).hexdigest()


def _build_evidence(
    *,
    collection_release_sha: str,
    schema_release_sha: str,
    selection_release_sha: str,
    precommit_sha256: str,
    scan_sha256: str,
    candidate_order_sha256: str,
    historical_corpus_sha256: str,
    historical_split_sha256: str,
    corpus_sha256: str,
    raw_split_sha256: str,
    bound_split_sha256: str,
    historical_window: Mapping[str, Any],
    replacement_window: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "materialized_at": MATERIALIZATION_TIMESTAMP,
        "collection_release_sha": collection_release_sha,
        "schema_release_sha": schema_release_sha,
        "selection_release_sha": selection_release_sha,
        "precommit_manifest_sha256": precommit_sha256,
        "replacement_scan_sha256": scan_sha256,
        "candidate_order_sha256": candidate_order_sha256,
        "historical_corpus_sha256": historical_corpus_sha256,
        "historical_split_sha256": historical_split_sha256,
        "scan_candidate_count": EXPECTED_CANDIDATE_COUNT,
        "scan_eligible_count": EXPECTED_SCAN_ELIGIBLE_COUNT,
        "selected_holdout_count": EXPECTED_SELECTED_COUNT,
        "unused_eligible_reserve_count": EXPECTED_UNUSED_ELIGIBLE_COUNT,
        "selected_339th_candidate_index": EXPECTED_SELECTED_LAST_INDEX,
        "index_convention": "zero-based",
        "historical_training_count": EXPECTED_TRAIN_COUNT,
        "new_population_count": EXPECTED_POPULATION_COUNT,
        "historical_revealed_holdout_included": 0,
        "window_model": PER_PROFILE_WINDOW_MODE,
        "historical_window_count": EXPECTED_TRAIN_COUNT,
        "replacement_window_count": EXPECTED_HOLDOUT_COUNT,
        "historical_window": dict(historical_window),
        "replacement_window": dict(replacement_window),
        "selection_method": "precommitted_first_339_eligible",
        "selection_inputs_used": "collection status + canonical eligibility only",
        "rank_or_mmr_used": False,
        "new_network_requests": 0,
        "detail_requests": 0,
        "parse_requests": 0,
        "corpus_sha256": corpus_sha256,
        "raw_split_sha256": raw_split_sha256,
        "bound_split_sha256": bound_split_sha256,
        "population_overlap_count": 0,
        "duplicate_profile_count": 0,
        "raw_identifiers_present": False,
    }


def build_selection(
    *,
    precommit_manifest: Path,
    replacement_scan: Path,
    current_corpus: Path,
    current_split: Path,
    expected_current_corpus_sha256: str,
    expected_current_split_sha256: str,
    expected_historical_corpus_sha256: str = EXPECTED_HISTORICAL_CORPUS_SHA256,
    expected_historical_split_sha256: str = EXPECTED_HISTORICAL_SPLIT_SHA256,
    collection_release_sha: str = COLLECTION_RELEASE_SHA,
    schema_release_sha: str = SCHEMA_RELEASE_SHA,
    selection_release_sha: str,
    expected_precommit_sha256: str = EXPECTED_PRECOMMIT_SHA256,
    expected_replacement_scan_sha256: str = EXPECTED_REPLACEMENT_SCAN_SHA256,
    expected_candidate_order_sha256: str = EXPECTED_CANDIDATE_ORDER_SHA256,
    expected_candidate_count: int = EXPECTED_CANDIDATE_COUNT,
    expected_scan_eligible_count: int = EXPECTED_SCAN_ELIGIBLE_COUNT,
    expected_selected_last_index: int = EXPECTED_SELECTED_LAST_INDEX,
    expected_unused_eligible_count: int = EXPECTED_UNUSED_ELIGIBLE_COUNT,
) -> SelectionResult:
    for value, label, length in (
        (collection_release_sha, "collection release SHA", 40),
        (schema_release_sha, "schema release SHA", 40),
        (selection_release_sha, "selection release SHA", 40),
    ):
        _require_sha(value, label=label, length=length)
    if collection_release_sha != COLLECTION_RELEASE_SHA or schema_release_sha != SCHEMA_RELEASE_SHA:
        raise SelectionError("release provenance SHA differs")
    if (
        expected_current_corpus_sha256 != expected_historical_corpus_sha256
        or expected_current_split_sha256 != expected_historical_split_sha256
    ):
        raise SelectionError("historical evidence SHA differs from the sealed input")
    precommit, _account_ids, precommit_sha256 = _validate_precommit(
        precommit_manifest,
        expected_sha256=expected_precommit_sha256,
        expected_order_sha256=expected_candidate_order_sha256,
        expected_candidate_count=expected_candidate_count,
        collection_release_sha=collection_release_sha,
    )
    historical, _historical_split, train_ids, _revealed_holdout_ids, historical_corpus_sha256, historical_split_sha256 = _validate_historical_inputs(
        current_corpus,
        current_split,
        expected_corpus_sha256=expected_current_corpus_sha256,
        expected_split_sha256=expected_current_split_sha256,
    )
    _ = precommit, _historical_split, _revealed_holdout_ids
    scan, ordered_profiles, replacement_window, scan_sha256 = _validate_scan(
        replacement_scan,
        precommit_sha256=precommit_sha256,
        expected_scan_sha256=expected_replacement_scan_sha256,
        expected_candidate_order_sha256=expected_candidate_order_sha256,
        expected_candidate_count=expected_candidate_count,
        expected_eligible_count=expected_scan_eligible_count,
        source=historical.payload["source"],
        request_manifest=historical.payload["request_manifest"],
    )
    if scan.get("precommit_manifest_sha256") != precommit_sha256:
        raise SelectionError("replacement scan is not bound to precommit bytes")
    historical_ids = set(historical.profile_ids)
    scan_ids = {str(profile["profile_id"]) for profile in ordered_profiles}
    if scan_ids & historical_ids:
        raise SelectionError("replacement scan overlaps the historical population")
    status_by_index = {int(status["candidate_index"]): status for status in scan["candidate_statuses"]}
    profiles_by_id = {str(profile["profile_id"]): profile for profile in ordered_profiles}
    eligible: list[tuple[int, Mapping[str, Any]]] = []
    for index in range(expected_candidate_count):
        status = status_by_index[index]
        profile = profiles_by_id[str(status["profile_id"])]
        if status["eligibility"] == "eligible" and profile["status"] == "eligible" and int(profile["eligible_match_count"]) >= MINIMUM_USABLE_MATCHES:
            eligible.append((index, profile))
    if len(eligible) != expected_scan_eligible_count:
        raise SelectionError("replacement eligible count differs")
    if len(eligible) < EXPECTED_SELECTED_COUNT:
        raise SelectionError("replacement scan has fewer than 339 eligible profiles")
    selected = eligible[:EXPECTED_SELECTED_COUNT]
    unused = eligible[EXPECTED_SELECTED_COUNT:]
    if selected[-1][0] != expected_selected_last_index or len(unused) != expected_unused_eligible_count:
        raise SelectionError("replacement selection boundary differs")
    selected_profiles = [profile for _index, profile in selected]
    selected_ids = [str(profile["profile_id"]) for profile in selected_profiles]
    unused_ids = {str(profile["profile_id"]) for _index, profile in unused}
    if set(selected_ids) & historical_ids or unused_ids & historical_ids or set(selected_ids) & unused_ids:
        raise SelectionError("replacement selection population overlap is nonzero")
    historical_window = dict(historical.payload["window"])
    corpus = _build_corpus(
        historical,
        train_ids,
        selected_profiles,
        historical_window=historical_window,
    )
    try:
        corpus_checksum = hashlib.sha256(serialize_manifest(corpus)).hexdigest()
    except (TypeError, ValueError) as exc:
        raise SelectionError("materialized corpus cannot be serialized") from exc
    raw_split = _build_split(
        train_ids,
        selected_ids,
        corpus_sha256=corpus_checksum,
        historical_corpus_sha256=historical_corpus_sha256,
        historical_split_sha256=historical_split_sha256,
        candidate_order_sha256=expected_candidate_order_sha256,
        selection_release_sha=selection_release_sha,
    )
    raw_split_checksum = hashlib.sha256(serialize_manifest(raw_split)).hexdigest()
    bound_checksum = _bound_split_sha256(raw_split, corpus_checksum)
    evidence = _build_evidence(
        collection_release_sha=collection_release_sha,
        schema_release_sha=schema_release_sha,
        selection_release_sha=selection_release_sha,
        precommit_sha256=precommit_sha256,
        scan_sha256=scan_sha256,
        candidate_order_sha256=expected_candidate_order_sha256,
        historical_corpus_sha256=historical_corpus_sha256,
        historical_split_sha256=historical_split_sha256,
        corpus_sha256=corpus_checksum,
        raw_split_sha256=raw_split_checksum,
        bound_split_sha256=bound_checksum,
        historical_window=historical_window,
        replacement_window=replacement_window,
    )
    return SelectionResult(corpus, raw_split, evidence, corpus_checksum, raw_split_checksum, bound_checksum)


def write_selection_outputs(
    result: SelectionResult,
    *,
    output_corpus: Path,
    output_split: Path,
    output_selection_evidence: Path,
) -> dict[str, str]:
    expected = {
        output_corpus: (result.corpus, result.corpus_sha256),
        output_split: (result.raw_split, result.raw_split_sha256),
        output_selection_evidence: (result.evidence, hashlib.sha256(serialize_manifest(result.evidence)).hexdigest()),
    }
    for path, (payload, expected_sha256) in expected.items():
        serialized = serialize_manifest(payload)
        if hashlib.sha256(serialized).hexdigest() != expected_sha256:
            raise SelectionError("selection output checksum construction failed")
        if path.exists() and path.read_bytes() != serialized:
            raise SelectionError("existing selection output differs and cannot be replaced")
    statuses: dict[str, str] = {}
    for path, (payload, _expected_sha256) in expected.items():
        status, _ = write_private_manifest(path, payload)
        statuses[str(path)] = status
    return statuses


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--precommit-manifest", type=Path, required=True)
    parser.add_argument("--replacement-scan", type=Path, required=True)
    parser.add_argument("--current-corpus", type=Path, required=True)
    parser.add_argument("--current-split", type=Path, required=True)
    parser.add_argument("--expected-current-corpus-sha256", required=True)
    parser.add_argument("--expected-current-split-sha256", required=True)
    parser.add_argument("--collection-release-sha", required=True)
    parser.add_argument("--schema-release-sha", required=True)
    parser.add_argument("--selection-release-sha", required=True)
    parser.add_argument("--output-corpus", type=Path, required=True)
    parser.add_argument("--output-split", type=Path, required=True)
    parser.add_argument("--output-selection-evidence", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = build_selection(
            precommit_manifest=args.precommit_manifest,
            replacement_scan=args.replacement_scan,
            current_corpus=args.current_corpus,
            current_split=args.current_split,
            expected_current_corpus_sha256=args.expected_current_corpus_sha256,
            expected_current_split_sha256=args.expected_current_split_sha256,
            expected_historical_corpus_sha256=EXPECTED_HISTORICAL_CORPUS_SHA256,
            expected_historical_split_sha256=EXPECTED_HISTORICAL_SPLIT_SHA256,
            collection_release_sha=args.collection_release_sha,
            schema_release_sha=args.schema_release_sha,
            selection_release_sha=args.selection_release_sha,
            expected_precommit_sha256=EXPECTED_PRECOMMIT_SHA256,
            expected_replacement_scan_sha256=EXPECTED_REPLACEMENT_SCAN_SHA256,
            expected_candidate_order_sha256=EXPECTED_CANDIDATE_ORDER_SHA256,
        )
        statuses = write_selection_outputs(
            result,
            output_corpus=args.output_corpus,
            output_split=args.output_split,
            output_selection_evidence=args.output_selection_evidence,
        )
    except (OSError, SelectionError):
        print(json.dumps({"status": "blocked", "error": "selection validation failed"}, sort_keys=True), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": "complete",
                "output_statuses": statuses,
                "scan_candidate_count": EXPECTED_CANDIDATE_COUNT,
                "scan_eligible_count": EXPECTED_SCAN_ELIGIBLE_COUNT,
                "selected_holdout_count": EXPECTED_SELECTED_COUNT,
                "unused_eligible_reserve_count": EXPECTED_UNUSED_ELIGIBLE_COUNT,
                "selected_339th_candidate_index": EXPECTED_SELECTED_LAST_INDEX,
                "corpus_sha256": result.corpus_sha256,
                "raw_split_sha256": result.raw_split_sha256,
                "bound_split_sha256": result.bound_split_sha256,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
