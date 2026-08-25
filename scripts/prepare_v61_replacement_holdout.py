#!/usr/bin/env python3
"""Precommit the private V6.1 replacement-holdout candidate order."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.ingestion.summary_history_contract import (  # noqa: E402
    SUMMARY_HISTORY_PROJECTION_VERSION,
    SUMMARY_HISTORY_PROVIDER_LIMIT,
    SUMMARY_HISTORY_RETRY_LIMIT,
    SUMMARY_HISTORY_WINDOW_DAYS,
)
from app.player_analysis_v61.calibration_corpus import (  # noqa: E402
    MINIMUM_USABLE_MATCHES,
)

SCHEMA_VERSION = "v61-replacement-holdout-precommit-1.0.0"
ORDERING_NAMESPACE = "v61-new-holdout-reserve-scan-2026-08-25:"
EXPECTED_HISTORICAL_CANDIDATES = 2_364
EXPECTED_ORIGINAL_POPULATION = 1_130
EXPECTED_SCREENED_RESERVE = 10
EXPECTED_UNTOUCHED_RESERVE = 1_224
TARGET_HOLDOUT_PROFILES = 339
EXPECTED_CURRENT_TRAIN = 791
EXPECTED_CURRENT_HOLDOUT = 339
EXPECTED_CURRENT_SPLIT_PROFILE_COUNT = 1_130
EXPECTED_SALT_BYTES = 32
HISTORICAL_SCHEMA_VERSION = "v6-calibration-candidates-1.0.0"
SCREENED_SCHEMA_VERSION = "v61-replacement-candidates-1.0.0"
SCREENED_SELECTION_POLICY = "unused-historical-candidates-sorted-by-profile-id"
ORDER_DIGEST_FORMAT = "decimal-account-id-newline-v1"

if MINIMUM_USABLE_MATCHES != 30:
    raise RuntimeError("V6.1 canonical minimum usable matches must remain 30")
if SUMMARY_HISTORY_RETRY_LIMIT != 0:
    raise RuntimeError("V6.1 replacement collection requires retry_limit=0")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} file is missing") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} file is unreadable") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def load_candidate_ids(path: Path, *, label: str) -> tuple[dict[str, Any], tuple[int, ...]]:
    payload = _read_object(path, label)
    raw = payload.get("candidate_account_ids")
    if not isinstance(raw, list):
        raise ValueError(f"{label} candidate_account_ids must be a list")
    seen: set[int] = set()
    values: list[int] = []
    for index, value in enumerate(raw):
        if type(value) is not int or value <= 0:  # bool is intentionally rejected.
            raise ValueError(f"{label} contains an invalid account ID at index {index}")
        if value in seen:
            raise ValueError(f"{label} contains duplicate account IDs")
        seen.add(value)
        values.append(value)
    return payload, tuple(values)


def validate_historical_candidates(path: Path) -> tuple[dict[str, Any], tuple[int, ...]]:
    payload, values = load_candidate_ids(path, label="historical candidates")
    if payload.get("schema_version") != HISTORICAL_SCHEMA_VERSION:
        raise ValueError("historical candidate schema version is invalid")
    if len(values) != EXPECTED_HISTORICAL_CANDIDATES:
        raise ValueError("historical candidate count is invalid")
    summary = payload.get("summary")
    if isinstance(summary, Mapping) and "unique_candidate_account_ids" in summary:
        if summary["unique_candidate_account_ids"] != len(values):
            raise ValueError("historical candidate summary count is invalid")
    return payload, values


def validate_original_population(path: Path) -> tuple[dict[str, Any], tuple[int, ...]]:
    payload, values = load_candidate_ids(path, label="original population")
    if len(values) != EXPECTED_ORIGINAL_POPULATION:
        raise ValueError("original population count is invalid")
    if "candidate_count" in payload and payload["candidate_count"] != len(values):
        raise ValueError("original population count metadata is invalid")
    return payload, values


def validate_screened_reserve(path: Path) -> tuple[dict[str, Any], tuple[int, ...]]:
    payload, values = load_candidate_ids(path, label="screened reserve")
    if payload.get("schema_version") != SCREENED_SCHEMA_VERSION:
        raise ValueError("screened reserve schema version is invalid")
    if payload.get("batch_index") != 1:
        raise ValueError("screened reserve batch index is invalid")
    if payload.get("selection_policy") != SCREENED_SELECTION_POLICY:
        raise ValueError("screened reserve selection policy is invalid")
    if payload.get("candidate_count") != len(values) or len(values) != EXPECTED_SCREENED_RESERVE:
        raise ValueError("screened reserve count is invalid")
    return payload, values


def _validate_profile_id_list(payload: Mapping[str, Any], key: str, expected: int) -> set[str]:
    raw = payload.get(key)
    if not isinstance(raw, list) or any(not isinstance(value, str) or not value for value in raw):
        raise ValueError(f"current split {key} is invalid")
    values = set(raw)
    if len(values) != len(raw) or len(values) != expected:
        raise ValueError(f"current split {key} count is invalid")
    return values


def validate_current_split(
    path: Path,
    *,
    expected_sha256: str,
) -> tuple[dict[str, Any], set[str], str]:
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ValueError("current split SHA-256 does not match the expected value")
    payload = _read_object(path, "current split")
    train = _validate_profile_id_list(payload, "train_profile_ids", EXPECTED_CURRENT_TRAIN)
    holdout = _validate_profile_id_list(payload, "holdout_profile_ids", EXPECTED_CURRENT_HOLDOUT)
    if train & holdout or len(train | holdout) != EXPECTED_CURRENT_SPLIT_PROFILE_COUNT:
        raise ValueError("current split profile sets are invalid")
    if payload.get("train_profile_count") != EXPECTED_CURRENT_TRAIN:
        raise ValueError("current split train count metadata is invalid")
    if payload.get("holdout_profile_count") != EXPECTED_CURRENT_HOLDOUT:
        raise ValueError("current split holdout count metadata is invalid")
    return payload, train | holdout, actual_sha256


def _pseudonym(account_id: int, salt: bytes) -> str:
    """Match the collector's salted decimal-account-ID pseudonym exactly."""

    return hashlib.sha256(salt + str(account_id).encode("ascii")).hexdigest()


def ordering_key(account_id: int) -> tuple[bytes, int]:
    digest = hashlib.sha256(
        (ORDERING_NAMESPACE + str(account_id)).encode("ascii")
    ).digest()
    return digest, account_id


def _validate_hex(value: str, *, length: int, label: str) -> str:
    if not re.fullmatch(rf"[0-9a-f]{{{length}}}", value):
        raise ValueError(f"{label} must be lowercase hexadecimal")
    return value


def _order_digest(ordered_ids: Sequence[int]) -> str:
    order_bytes = ("\n".join(str(account_id) for account_id in ordered_ids) + "\n").encode(
        "ascii"
    )
    return _sha256_bytes(order_bytes)


def build_precommit_manifest(
    *,
    historical_candidates: Path,
    original_population: Path,
    screened_reserve: Path,
    salt_path: Path,
    current_split: Path,
    expected_current_split_sha256: str,
    release_sha: str,
) -> dict[str, Any]:
    _validate_hex(release_sha, length=40, label="release SHA")
    _validate_hex(expected_current_split_sha256, length=64, label="current split SHA-256")

    _, historical_values = validate_historical_candidates(historical_candidates)
    _, original_values = validate_original_population(original_population)
    _, screened_values = validate_screened_reserve(screened_reserve)
    try:
        salt = salt_path.read_bytes()
    except (FileNotFoundError, OSError) as exc:
        raise ValueError("calibration salt is unreadable") from exc
    if len(salt) < EXPECTED_SALT_BYTES:
        raise ValueError("calibration salt is too short")
    _, current_profile_ids, current_split_sha256 = validate_current_split(
        current_split,
        expected_sha256=expected_current_split_sha256,
    )

    historical = set(historical_values)
    original = set(original_values)
    screened = set(screened_values)
    if not original <= historical:
        raise ValueError("original population is outside the historical candidate pool")
    if not screened <= historical:
        raise ValueError("screened reserve is outside the historical candidate pool")
    exclusion_overlap = original & screened
    if exclusion_overlap:
        raise ValueError("original and screened reserve exclusions overlap")
    untouched = historical - original - screened
    if len(untouched) != EXPECTED_UNTOUCHED_RESERVE:
        raise ValueError("untouched reserve count is invalid")

    untouched_profile_ids = {_pseudonym(account_id, salt) for account_id in untouched}
    current_population_overlap = untouched_profile_ids & current_profile_ids
    if current_population_overlap:
        raise ValueError("untouched reserve overlaps the current population")

    ordered_ids = tuple(sorted(untouched, key=ordering_key))
    if len(ordered_ids) != EXPECTED_UNTOUCHED_RESERVE:
        raise ValueError("ordered reserve count is invalid")
    historical_sha256 = sha256_file(historical_candidates)
    original_sha256 = sha256_file(original_population)
    screened_sha256 = sha256_file(screened_reserve)
    return {
        "schema_version": SCHEMA_VERSION,
        "release_sha": release_sha,
        "purpose": "replacement-sealed-holdout-candidate-scan",
        "privacy": {
            "contains_account_ids": True,
            "git_tracked": False,
            "required_file_mode": "0600",
        },
        "provenance": {
            "historical_candidates": {
                "path": str(historical_candidates),
                "sha256": historical_sha256,
                "candidate_count": len(historical_values),
            },
            "original_population": {
                "path": str(original_population),
                "sha256": original_sha256,
                "candidate_count": len(original_values),
            },
            "previously_screened_reserve": {
                "path": str(screened_reserve),
                "sha256": screened_sha256,
                "candidate_count": len(screened_values),
            },
            "current_split": {
                "path": str(current_split),
                "sha256": current_split_sha256,
                "train_profile_count": EXPECTED_CURRENT_TRAIN,
                "holdout_profile_count": EXPECTED_CURRENT_HOLDOUT,
            },
        },
        "exclusions": {
            "original_population_count": len(original_values),
            "previously_screened_reserve_count": len(screened_values),
            "exclusion_overlap_count": len(exclusion_overlap),
            "current_population_overlap_count": len(current_population_overlap),
            "untouched_reserve_count": len(ordered_ids),
        },
        "selection_protocol": {
            "ordering_namespace": ORDERING_NAMESPACE,
            "ordering_algorithm": "sha256(namespace + decimal_account_id_ascii), then numeric_account_id",
            "eligibility_rule": {
                "canonical_status_required": "eligible",
                "minimum_usable_matches": MINIMUM_USABLE_MATCHES,
            },
            "target_holdout_profile_count": TARGET_HOLDOUT_PROFILES,
            "selection_rule": "first-339-eligible-in-precommitted-order",
            "forbidden_selection_inputs": [
                "v61_outcomes",
                "findings",
                "semantic_results",
                "rank",
                "mmr",
            ],
        },
        "collection_contract": {
            "summary_requests_per_candidate": 1,
            "planned_summary_requests": len(ordered_ids),
            "planned_detail_requests": 0,
            "planned_parse_requests": 0,
            "retry_limit": SUMMARY_HISTORY_RETRY_LIMIT,
            "window_days": SUMMARY_HISTORY_WINDOW_DAYS,
            "provider_limit": SUMMARY_HISTORY_PROVIDER_LIMIT,
            "projection_version": SUMMARY_HISTORY_PROJECTION_VERSION,
            "raw_archive_required": True,
        },
        "candidate_count": len(ordered_ids),
        "candidate_order_digest_format": ORDER_DIGEST_FORMAT,
        "candidate_order_sha256": _order_digest(ordered_ids),
        "candidate_account_ids": list(ordered_ids),
    }


def serialize_manifest(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_private_manifest(path: Path, payload: Mapping[str, Any]) -> tuple[str, str]:
    """Write once, verify identical bytes, and never replace private evidence."""

    expected = serialize_manifest(payload)
    manifest_sha256 = _sha256_bytes(expected)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    if path.exists():
        if (path.stat().st_mode & 0o777) != 0o600:
            raise ValueError("existing manifest has the wrong file mode")
        if path.read_bytes() != expected:
            raise ValueError("existing manifest differs and cannot be replaced")
        return "verified-existing", manifest_sha256
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("manifest appeared during write and cannot be replaced") from exc
    try:
        os.write(descriptor, expected)
        os.fsync(descriptor)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        os.close(descriptor)
    path.chmod(0o600)
    return "created", manifest_sha256


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-candidates", type=Path, required=True)
    parser.add_argument("--original-population", type=Path, required=True)
    parser.add_argument("--screened-reserve", type=Path, required=True)
    parser.add_argument("--salt", type=Path, required=True)
    parser.add_argument("--current-split", type=Path, required=True)
    parser.add_argument("--expected-current-split-sha256", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_precommit_manifest(
            historical_candidates=args.historical_candidates,
            original_population=args.original_population,
            screened_reserve=args.screened_reserve,
            salt_path=args.salt,
            current_split=args.current_split,
            expected_current_split_sha256=args.expected_current_split_sha256,
            release_sha=args.release_sha,
        )
        status, manifest_sha256 = write_private_manifest(args.output, payload)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": status,
                "candidate_count": payload["candidate_count"],
                "candidate_order_sha256": payload["candidate_order_sha256"],
                "manifest_sha256": manifest_sha256,
                "planned_summary_requests": payload["collection_contract"]["planned_summary_requests"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
