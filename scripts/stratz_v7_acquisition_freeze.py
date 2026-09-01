#!/usr/bin/env python3
"""Freeze the offline V7 STRATZ acquisition frame, packs, and economics.

This script never contacts a provider.  Raw account IDs are read only long
enough to derive salted HMAC pseudonyms and are not written to any output.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import secrets
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1] / "services/api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.stratz.queries import (  # noqa: E402
    GET_PARSED_ACQUISITION_BATCH,
    GET_PLAYER_HISTORY_PAGE,
    get_operation,
)

SCHEMA_VERSION = "stratz-v7-acquisition-freeze-1.0.0"
SOURCE_FRAME_PATH = Path(
    "/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/"
    "corpora/opendota/v61-session-drift-expansion/manifests/fixed-frame-manifest.json"
)
DEFAULT_OUTPUT_DIR = Path(".local/corpora/stratz/v7-acquisition-freeze-2026-09-01")
EXPECTED_FRAME_COUNT = 4_135
SAMPLE_SIZE = 1_200
SPLIT_COUNTS = {
    "DISCOVERY": 600,
    "CANDIDATE_TEST": 300,
    "CALIBRATION_RESERVED": 150,
    "SEALED_VALIDATION": 150,
}
PARSED_SUBSET_COUNTS = {
    "DISCOVERY": 128,
    "CANDIDATE_TEST": 128,
    "CALIBRATION_RESERVED": 0,
    "SEALED_VALIDATION": 0,
}
EXPECTED_MATCHES_PER_PLAYER_YEAR = 293
HISTORY_PAGE_SIZE = 100
PARSED_BATCH_SIZE = 8
OBSERVED_HISTORY_PAGE_BYTES = 103_441
OBSERVED_HISTORY_PAGE_MATCHES = 100
OBSERVED_PARSED_BATCH_BYTES = 28_099
OBSERVED_PARSED_BATCH_MATCHES = 8
PROVIDER_LIMITS = {"second": 8, "minute": 150, "hour": 1_500, "day": 15_000}
ORCHESTRATION_LIMITS = {"second": 5, "minute": 100, "hour": 1_000, "day": 10_000}
DAILY_RESERVE_FRACTION = 0.10
HMAC_NAMESPACE = "stratz-v7-acquisition-freeze"
UNKNOWN_COMPLEXITY = (
    "UNKNOWN: STRATZ exposed no per-field or query complexity value in the live probe"
)


@dataclass(frozen=True, slots=True)
class FrameRecord:
    account_id: int
    source_position: int


@dataclass(frozen=True, slots=True)
class SourceFrame:
    path: Path
    digest: str
    schema_version: str
    frame_count: int
    positive_public_account_count: int
    records: tuple[FrameRecord, ...]

    def public_summary(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "frame_count": self.frame_count,
            "positive_public_account_count": self.positive_public_account_count,
            "sha256": self.digest,
        }


@dataclass(frozen=True, slots=True)
class FieldSpec:
    path: str
    semantic_class: str
    meaning: str
    alignment: str
    null_behavior: str
    parsed_required: bool
    complexity_contribution: str
    candidate_consumers: tuple[str, ...]
    disposition: str = "KEEP"
    privacy_scope: str = "AGGREGATE_METADATA"

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_path": self.path,
            "semantic_class": self.semantic_class,
            "meaning": self.meaning,
            "alignment": self.alignment,
            "null_behavior": self.null_behavior,
            "parsed_required": self.parsed_required,
            "complexity_contribution": self.complexity_contribution,
            "candidate_consumers": list(self.candidate_consumers),
            "disposition": self.disposition,
            "privacy_scope": self.privacy_scope,
        }


@dataclass(frozen=True, slots=True)
class PackSpec:
    name: str
    version: str
    operation_name: str
    purpose: str
    candidate_consumers: tuple[str, ...]
    fields: tuple[FieldSpec, ...]

    def as_dict(self) -> dict[str, Any]:
        operation = get_operation(self.operation_name)
        return {
            "name": self.name,
            "version": self.version,
            "purpose": self.purpose,
            "operation": {
                "name": operation.name,
                "version": operation.version,
                "document_sha256": operation.document_sha256,
            },
            "candidate_consumers": list(self.candidate_consumers),
            "fields": [field.as_dict() for field in self.fields],
        }


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def load_source_frame(path: Path = SOURCE_FRAME_PATH) -> SourceFrame:
    """Validate the already-paid public-match-derived frame without exposing IDs."""

    if not path.is_file():
        raise FileNotFoundError(f"source frame not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("source frame is not readable JSON") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("source frame must be an object")
    rows = raw.get("ranked_frame")
    if not isinstance(rows, list):
        raise ValueError("source frame ranked_frame must be a list")
    if len(rows) != EXPECTED_FRAME_COUNT:
        raise ValueError(f"source frame must contain {EXPECTED_FRAME_COUNT} accounts")
    if raw.get("adaptive_top_up") is not False:
        raise ValueError("source frame must disable adaptive top-up")
    selection = raw.get("selection")
    if not isinstance(selection, str):
        raise ValueError("source frame selection provenance is missing")
    lowered_selection = selection.lower()
    if "/publicmatches" not in lowered_selection or "hmac" not in lowered_selection:
        raise ValueError("source frame is not the required public-match HMAC frame")
    if any(token in lowered_selection for token in ("mmr", "finding", "output")):
        raise ValueError("source frame selection contains a forbidden selection basis")
    positive_count = raw.get("positive_public_account_count")
    if isinstance(positive_count, bool) or not isinstance(positive_count, int):
        raise ValueError("source frame positive account count is invalid")
    if positive_count < len(rows):
        raise ValueError("source frame count exceeds its positive public account count")

    records: list[FrameRecord] = []
    seen: set[int] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError("source frame entry must be an object")
        account_id = _positive_int(row.get("account_id"), "source account ID")
        if account_id in seen:
            raise ValueError("source frame contains duplicate accounts")
        seen.add(account_id)
        position = row.get("position", index)
        if isinstance(position, bool) or not isinstance(position, int) or position != index:
            raise ValueError("source frame positions must be contiguous and stable")
        for key in row:
            key_lower = str(key).lower()
            if key_lower in {"mmr", "rank", "rank_tier", "finding", "score", "behavior"}:
                raise ValueError("source frame contains a forbidden analytical field")
        records.append(FrameRecord(account_id=account_id, source_position=position))

    return SourceFrame(
        path=path,
        digest=sha256_file(path),
        schema_version=str(raw.get("schema_version", "unknown")),
        frame_count=len(records),
        positive_public_account_count=positive_count,
        records=tuple(records),
    )


def _hmac_hex(salt: bytes, purpose: str, account_id: int) -> str:
    if len(salt) != 32:
        raise ValueError("salt must be exactly 32 bytes")
    message = f"{HMAC_NAMESPACE}:{purpose}:{account_id}".encode("ascii")
    return hmac.new(salt, message, hashlib.sha256).hexdigest()


def pseudonymize_account(account_id: int, salt: bytes) -> str:
    """Return an opaque, non-reversible research key for a positive account ID."""

    _positive_int(account_id, "account ID")
    return f"v7p_{_hmac_hex(salt, 'pseudonym', account_id)}"


def hmac_rank(account_id: int, salt: bytes) -> str:
    _positive_int(account_id, "account ID")
    return _hmac_hex(salt, "rank", account_id)


def _ordered_records(frame: SourceFrame, salt: bytes) -> list[tuple[FrameRecord, str, str]]:
    ranked = [
        (record, hmac_rank(record.account_id, salt), pseudonymize_account(record.account_id, salt))
        for record in frame.records
    ]
    ranked.sort(key=lambda item: (item[1], item[2]))
    return ranked


def _validate_split_counts(
    sample_size: int,
    split_counts: Mapping[str, int],
    parsed_subset_counts: Mapping[str, int],
) -> None:
    expected_splits = tuple(SPLIT_COUNTS)
    if tuple(split_counts) != expected_splits or tuple(parsed_subset_counts) != expected_splits:
        raise ValueError("split partitions must use the four frozen names in order")
    if sum(split_counts.values()) != sample_size:
        raise ValueError("split counts must sum to sample size")
    if any(value < 0 for value in split_counts.values()) or any(
        value < 0 for value in parsed_subset_counts.values()
    ):
        raise ValueError("split counts cannot be negative")
    for split, count in parsed_subset_counts.items():
        if count > split_counts[split]:
            raise ValueError(f"parsed subset exceeds {split} split")


def build_split_manifest(
    frame: SourceFrame,
    salt: bytes,
    *,
    sample_size: int = SAMPLE_SIZE,
    split_counts: Mapping[str, int] = SPLIT_COUNTS,
    parsed_subset_counts: Mapping[str, int] = PARSED_SUBSET_COUNTS,
) -> dict[str, Any]:
    """Build a deterministic manifest containing pseudonyms only, never raw IDs."""

    _validate_split_counts(sample_size, split_counts, parsed_subset_counts)
    if sample_size > frame.frame_count:
        raise ValueError("sample size exceeds source frame")
    ordered = _ordered_records(frame, salt)[:sample_size]
    partitioned: dict[str, list[tuple[FrameRecord, str, str]]] = {}
    cursor = 0
    for split, count in split_counts.items():
        partitioned[split] = ordered[cursor : cursor + count]
        cursor += count

    entries: list[dict[str, Any]] = []
    for split, members in partitioned.items():
        parsed_count = parsed_subset_counts[split]
        parsed_order = sorted(
            members,
            key=lambda item: (_hmac_hex(salt, "parsed-subset", item[0].account_id), item[2]),
        )[:parsed_count]
        parsed_keys = {item[2]: index for index, item in enumerate(parsed_order)}
        for record, rank_digest, pseudonym in members:
            entries.append(
                {
                    "pseudonym": pseudonym,
                    "rank_digest": rank_digest,
                    "source_position": record.source_position,
                    "split": split,
                    "parsed_subset": pseudonym in parsed_keys,
                    "parsed_subset_order": parsed_keys.get(pseudonym),
                }
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "source_frame": frame.public_summary(),
        "sample_size": sample_size,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "hmac_namespace": HMAC_NAMESPACE,
        "split_counts": dict(split_counts),
        "parsed_subset_counts": dict(parsed_subset_counts),
        "selection_rule": {
            "sample": "first N accounts after ascending HMAC-SHA256 rank using a new 32-byte salt",
            "partitions": "fixed contiguous counts in that order; no output- or yield-based replacement",
            "parsed_subset": "independent HMAC-SHA256 subrank within DISCOVERY and CANDIDATE_TEST only",
        },
        "members": entries,
    }


def verify_no_split_overlap(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Verify partition counts, pseudonym uniqueness, and parsed subset declarations."""

    split_counts = manifest.get("split_counts")
    parsed_counts = manifest.get("parsed_subset_counts")
    members = manifest.get("members")
    if not isinstance(split_counts, Mapping) or not isinstance(parsed_counts, Mapping):
        raise ValueError("manifest split counts are missing")
    if not isinstance(members, list):
        raise ValueError("manifest members are missing")
    seen: set[str] = set()
    observed: dict[str, int] = {str(split): 0 for split in split_counts}
    parsed_observed: dict[str, int] = {str(split): 0 for split in split_counts}
    for member in members:
        if not isinstance(member, Mapping):
            raise ValueError("manifest member is not an object")
        pseudonym = member.get("pseudonym")
        split = member.get("split")
        if not isinstance(pseudonym, str) or not isinstance(split, str):
            raise ValueError("manifest member lacks pseudonym or split")
        if pseudonym in seen:
            raise ValueError("split overlap detected")
        seen.add(pseudonym)
        if split not in observed:
            raise ValueError("manifest contains an unknown split")
        observed[split] += 1
        if member.get("parsed_subset"):
            parsed_observed[split] += 1
        if "account_id" in member or "steamAccountId" in member:
            raise ValueError("manifest contains a raw account identifier")
    expected = {str(key): int(value) for key, value in split_counts.items()}
    expected_parsed = {str(key): int(value) for key, value in parsed_counts.items()}
    if observed != expected or parsed_observed != expected_parsed:
        raise ValueError("manifest partition counts do not match declarations")
    return {
        "passed": True,
        "member_count": len(members),
        "split_counts": observed,
        "parsed_subset_counts": parsed_observed,
        "overlap_count": 0,
    }


def max_proportion_se(sample_size: int, population_size: int, *, proportion: float = 0.5) -> float:
    """Worst-case finite-population standard error for a simple proportion."""

    if sample_size <= 0 or population_size <= 1 or sample_size > population_size:
        raise ValueError("sample size must be positive and no larger than the population")
    if not 0 <= proportion <= 1:
        raise ValueError("proportion must be between zero and one")
    if sample_size == population_size:
        return 0.0
    return math.sqrt(
        proportion * (1 - proportion) / sample_size
        * (population_size - sample_size)
        / (population_size - 1)
    )


def calculate_economics(
    *,
    sample_size: int = SAMPLE_SIZE,
    split_counts: Mapping[str, int] = SPLIT_COUNTS,
    parsed_subset_counts: Mapping[str, int] = PARSED_SUBSET_COUNTS,
    population_size: int = EXPECTED_FRAME_COUNT,
    matches_per_player_year: int = EXPECTED_MATCHES_PER_PLAYER_YEAR,
    history_page_size: int = HISTORY_PAGE_SIZE,
    parsed_batch_size: int = PARSED_BATCH_SIZE,
) -> dict[str, Any]:
    """Return a planning scenario using observed payload sizes and safe quotas."""

    parsed_discovery = int(parsed_subset_counts["DISCOVERY"])
    parsed_candidate_test = int(parsed_subset_counts["CANDIDATE_TEST"])
    candidate_test_size = int(split_counts["CANDIDATE_TEST"])
    history_pages = math.ceil(matches_per_player_year / history_page_size)
    parsed_batches = math.ceil(matches_per_player_year / parsed_batch_size)
    history_calls = sample_size * history_pages
    parsed_calls_by_wave = {
        "DISCOVERY": parsed_discovery * parsed_batches,
        "CANDIDATE_TEST": parsed_candidate_test * parsed_batches,
    }
    parsed_calls = sum(parsed_calls_by_wave.values())
    total_calls = history_calls + parsed_calls
    daily_planned_cap = int(ORCHESTRATION_LIMITS["day"] * (1 - DAILY_RESERVE_FRACTION))
    history_bytes_per_match = OBSERVED_HISTORY_PAGE_BYTES / OBSERVED_HISTORY_PAGE_MATCHES
    parsed_bytes_per_match = OBSERVED_PARSED_BATCH_BYTES / OBSERVED_PARSED_BATCH_MATCHES
    history_bytes = history_calls * OBSERVED_HISTORY_PAGE_BYTES
    parsed_bytes = parsed_calls * OBSERVED_PARSED_BATCH_BYTES
    hourly_bound = min(
        ORCHESTRATION_LIMITS["second"] * 3_600,
        ORCHESTRATION_LIMITS["minute"] * 60,
        ORCHESTRATION_LIMITS["hour"],
    )
    daily_history_and_discovery = history_calls + parsed_calls_by_wave["DISCOVERY"]
    if daily_history_and_discovery > daily_planned_cap:
        raise ValueError("frozen plan exceeds the first daily safe budget")
    if parsed_calls_by_wave["CANDIDATE_TEST"] > daily_planned_cap:
        raise ValueError("frozen candidate-test parsed wave exceeds the daily safe budget")
    return {
        "population_frame_count": population_size,
        "sample_size": sample_size,
        "max_reach_standard_error": max_proportion_se(sample_size, population_size),
        "max_reach_95_percent_margin": 1.96 * max_proportion_se(sample_size, population_size),
        "candidate_test_max_standard_error": max_proportion_se(
            candidate_test_size, population_size
        ),
        "candidate_test_max_95_percent_margin": 1.96
        * max_proportion_se(candidate_test_size, population_size),
        "planning_scenario": {
            "matches_per_player_year": matches_per_player_year,
            "label": "specimen-derived planning input, not a population estimate",
            "history_page_size": history_page_size,
            "parsed_batch_size": parsed_batch_size,
        },
        "context_opportunities": {
            "history_match_rows": sample_size * matches_per_player_year,
            "parsed_match_rows_upper_bound": (parsed_discovery + parsed_candidate_test)
            * matches_per_player_year,
            "role_position_lane_population_rates": {
                "role": {"specimen_observed": 0.93, "population": "unknown"},
                "position": {"specimen_observed": 0.91, "population": "unknown"},
                "lane": {"specimen_observed": 0.93, "population": "unknown"},
            },
        },
        "calls": {
            "history_pages_per_account": history_pages,
            "history_calls": history_calls,
            "parsed_batches_per_account_upper_bound": parsed_batches,
            "parsed_calls_by_wave": parsed_calls_by_wave,
            "parsed_calls": parsed_calls,
            "total_planned_calls": total_calls,
            "opendota_calls": 0,
            "stratz_calls_now": 0,
        },
        "bytes": {
            "history_observation": {
                "source": "recovered q3 history specimen",
                "bytes_per_100_match_page": OBSERVED_HISTORY_PAGE_BYTES,
                "bytes_per_match_proxy": history_bytes_per_match,
            },
            "parsed_observation": {
                "source": "live microprobe safe batch",
                "bytes_per_8_match_batch": OBSERVED_PARSED_BATCH_BYTES,
                "bytes_per_match_proxy": parsed_bytes_per_match,
            },
            "history_raw_bytes_proxy": history_bytes,
            "parsed_raw_bytes_upper_bound": parsed_bytes,
            "combined_raw_bytes_upper_bound": history_bytes + parsed_bytes,
            "combined_raw_mib_upper_bound": (history_bytes + parsed_bytes) / (1024**2),
        },
        "wall_clock": {
            "effective_orchestration_calls_per_hour": hourly_bound,
            "day_1_calls": daily_history_and_discovery,
            "day_1_hours_at_hour_ceiling": daily_history_and_discovery / hourly_bound,
            "day_2_calls": parsed_calls_by_wave["CANDIDATE_TEST"],
            "day_2_hours_at_hour_ceiling": parsed_calls_by_wave["CANDIDATE_TEST"] / hourly_bound,
            "total_hours_at_hour_ceiling": total_calls / hourly_bound,
            "note": "Retries are physical attempts and consume the reserved daily budget.",
        },
        "quotas": {
            "provider_observed": dict(PROVIDER_LIMITS),
            "orchestration_ceiling": dict(ORCHESTRATION_LIMITS),
            "daily_reserve_fraction": DAILY_RESERVE_FRACTION,
            "daily_planned_cap": daily_planned_cap,
        },
        "daily_schedule": {
            "DAY_1": {
                "waves": {"HISTORY_CORE": history_calls, "PARSED_DISCOVERY": parsed_calls_by_wave["DISCOVERY"]},
                "planned_calls": daily_history_and_discovery,
                "reserve_calls": daily_planned_cap - daily_history_and_discovery,
            },
            "DAY_2": {
                "waves": {"PARSED_CANDIDATE_TEST": parsed_calls_by_wave["CANDIDATE_TEST"]},
                "planned_calls": parsed_calls_by_wave["CANDIDATE_TEST"],
                "reserve_calls": daily_planned_cap - parsed_calls_by_wave["CANDIDATE_TEST"],
            },
        },
    }


def _field(
    path: str,
    semantic_class: str,
    meaning: str,
    alignment: str,
    null_behavior: str,
    parsed_required: bool,
    consumers: Iterable[str],
    *,
    privacy_scope: str = "AGGREGATE_METADATA",
) -> FieldSpec:
    return FieldSpec(
        path=path,
        semantic_class=semantic_class,
        meaning=meaning,
        alignment=alignment,
        null_behavior=null_behavior,
        parsed_required=parsed_required,
        complexity_contribution=UNKNOWN_COMPLEXITY,
        candidate_consumers=tuple(consumers),
        privacy_scope=privacy_scope,
    )


HISTORY_CORE_FIELDS = (
    _field("profile.isAnonymous", "PRIVACY", "Provider privacy state.", "profile", "null fails public eligibility", False, ("product eligibility",)),
    _field("profile.isStratzPublic", "PRIVACY", "Provider public-profile state.", "profile", "null fails public eligibility", False, ("product eligibility",)),
    _field("match.id", "META", "Opaque local match key for parsed joins.", "one match", "missing row fails closed", False, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record"), privacy_scope="LOCAL_ONLY"),
    _field("match.startDateTime", "META", "Provider match start timestamp.", "one match", "null excludes chronology use", False, ("T1-A Role Shape", "T1-B Post-loss control matching")),
    _field("match.endDateTime", "META", "Provider match end timestamp.", "one match", "null excludes chronology use", False, ("T1-B Post-loss control matching",)),
    _field("match.durationSeconds", "META", "Provider match duration.", "one match", "null excludes duration use", False, ("structural eligibility", "T1-B Post-loss control matching")),
    _field("match.didRadiantWin", "META", "Match-level winning side.", "one match", "null excludes outcome use", False, ("T1-B Post-loss control matching",)),
    _field("match.gameMode", "META", "Native game-mode enum.", "one match", "null fails mode eligibility", False, ("structural eligibility",)),
    _field("match.lobbyType", "META", "Native lobby enum.", "one match", "null fails lobby eligibility", False, ("structural eligibility",)),
    _field("match.gameVersionId", "META", "Native game-version identifier; not a human patch claim.", "one match", "null excludes context stratification", False, ("T1-B Post-loss control matching", "context baselines")),
    _field("match.parsedDateTime", "META", "Parsed availability timestamp.", "one match", "null means parsed evidence unavailable", False, ("parsed-availability denominator",)),
    _field("player.heroId", "PLAYER", "Player hero identity.", "one player row per match", "null excludes hero comparisons", False, ("T1-A Role Shape", "T1-B Post-loss control matching")),
    _field("player.isRadiant", "PLAYER", "Player-relative side.", "one player row per match", "null excludes side use", False, ("T1-B Post-loss control matching",)),
    _field("player.isVictory", "PLAYER", "Player-relative match outcome.", "one player row per match", "null excludes outcome use", False, ("T1-B Post-loss control matching",)),
    _field("player.kills", "PLAYER", "Scoreboard kills.", "one player row per match", "null excludes combat summary", False, ("T1-B Post-loss control matching",)),
    _field("player.deaths", "PLAYER", "Scoreboard deaths.", "one player row per match", "null excludes exposure summary", False, ("T1-B Post-loss control matching",)),
    _field("player.assists", "PLAYER", "Scoreboard assists.", "one player row per match", "null excludes combat summary", False, ("T1-B Post-loss control matching",)),
    _field("player.leaverStatus", "PLAYER", "Native leaver enum; V7 mapping remains unresolved.", "one player row per match", "null or unresolved value fails eligibility", False, ("structural eligibility",)),
    _field("player.position", "REPLAY", "Native position observation.", "one player row per match", "null on unparsed/unavailable row", True, ("T1-A Role Shape", "T1-B Post-loss control matching")),
    _field("player.role", "REPLAY", "Native role observation, independent of position and lane.", "one player row per match", "null on unparsed/unavailable row", True, ("T1-A Role Shape", "T1-B Post-loss control matching")),
    _field("player.lane", "REPLAY", "Native lane observation, not a role conversion.", "one player row per match", "null on unparsed/unavailable row", True, ("T1-B Post-loss control matching",)),
)

PARSED_CORE_FIELDS = (
    _field("match.id", "META", "Opaque local match key for parsed joins.", "one match", "missing row fails closed", True, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record"), privacy_scope="LOCAL_ONLY"),
    _field("match.durationSeconds", "META", "Provider match duration.", "one match", "null excludes match use", True, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record")),
    _field("match.startDateTime", "META", "Provider match start timestamp.", "one match", "null excludes chronology use", True, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record")),
    _field("match.endDateTime", "META", "Provider match end timestamp.", "one match", "null excludes chronology use", True, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record")),
    _field("match.didRadiantWin", "META", "Match-level winning side.", "one match", "null excludes outcome use", True, ("T2-B Lane Outcome Record",)),
    _field("match.gameVersionId", "META", "Native game-version identifier.", "one match", "null excludes context stratification", True, ("T2-B Lane Outcome Record",)),
    _field("match.parsedDateTime", "META", "Parsed availability timestamp.", "one match", "null fails parsed eligibility", True, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record")),
    _field("match.radiantKills", "REPLAY", "Team radiant hero-death denominator, not scoreboard kills.", "one match", "null excludes participation denominator", True, ("T2-A Kill Participation Share",)),
    _field("match.direKills", "REPLAY", "Team dire hero-death denominator, not scoreboard kills.", "one match", "null excludes participation denominator", True, ("T2-A Kill Participation Share",)),
    _field("match.radiantNetworthLeads", "REPLAY", "Match-level radiant net-worth lead trajectory.", "one match trajectory", "null excludes state context", True, ("T2-B Lane Outcome Record",)),
    _field("match.bottomLaneOutcome", "REPLAY", "Native bottom-lane outcome enum.", "one match", "null means lane outcome unavailable", True, ("T2-B Lane Outcome Record",)),
    _field("match.midLaneOutcome", "REPLAY", "Native mid-lane outcome enum.", "one match", "null means lane outcome unavailable", True, ("T2-B Lane Outcome Record",)),
    _field("match.topLaneOutcome", "REPLAY", "Native top-lane outcome enum.", "one match", "null means lane outcome unavailable", True, ("T2-B Lane Outcome Record",)),
    _field("player.isRadiant", "PLAYER", "Player-relative side.", "one player row per match", "null excludes side mapping", True, ("T2-B Lane Outcome Record",)),
    _field("player.isVictory", "PLAYER", "Player-relative match outcome.", "one player row per match", "null excludes outcome use", True, ("T2-B Lane Outcome Record",)),
    _field("player.heroId", "PLAYER", "Player hero identity.", "one player row per match", "null excludes hero control", True, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record")),
    _field("player.position", "REPLAY", "Native position observation.", "one player row per match", "null excludes role stratification", True, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record")),
    _field("player.role", "REPLAY", "Native role observation.", "one player row per match", "null excludes role stratification", True, ("T2-A Kill Participation Share", "T2-B Lane Outcome Record")),
    _field("player.lane", "REPLAY", "Native lane observation.", "one player row per match", "null excludes lane mapping", True, ("T2-B Lane Outcome Record",)),
    _field("stats.killEvents[].time", "REPLAY", "Timestamped player kill events.", "one player-match event list", "null/missing excludes event evidence; empty means zero observed events", True, ("T2-A Kill Participation Share",)),
    _field("stats.assistEvents[].time", "REPLAY", "Timestamped player assist events.", "one player-match event list", "null/missing excludes event evidence; empty means zero observed events", True, ("T2-A Kill Participation Share",)),
)

PARSED_EXTENDED_FIELDS = (
    _field("stats.itemPurchases[].time", "REPLAY", "Timestamp of a recorded item purchase.", "one player-match event list", "null/missing excludes item evidence; empty means zero observed purchases", True, ("T3 Item Signature (research-only)",)),
    _field("stats.itemPurchases[].itemId", "REPLAY", "Native item identifier attached to a purchase event.", "one player-match event list", "null/missing excludes item evidence; empty means zero observed purchases", True, ("T3 Item Signature (research-only)",)),
)

PACKS = (
    PackSpec(
        name="History Core",
        version="stratz-history-core-1.0.0",
        operation_name=GET_PLAYER_HISTORY_PAGE.name,
        purpose="History metadata and native player context for eligibility, baselines, and history-tier candidates.",
        candidate_consumers=("T1-A Role Shape", "T1-B Post-loss control matching"),
        fields=HISTORY_CORE_FIELDS,
    ),
    PackSpec(
        name="Parsed Core",
        version="stratz-parsed-core-1.0.0",
        operation_name=GET_PARSED_ACQUISITION_BATCH.name,
        purpose="Minimum parsed match/player/event evidence for the two credible Tier 2 candidates.",
        candidate_consumers=("T2-A Kill Participation Share", "T2-B Lane Outcome Record"),
        fields=PARSED_CORE_FIELDS,
    ),
    PackSpec(
        name="Parsed Extended",
        version="stratz-parsed-extended-1.0.0",
        operation_name=GET_PARSED_ACQUISITION_BATCH.name,
        purpose="One research-only extension retained because Item Signature has a credible candidate question.",
        candidate_consumers=("T3 Item Signature (research-only)",),
        fields=PARSED_EXTENDED_FIELDS,
    ),
)


def validate_pack_registry() -> dict[str, Any]:
    """Check pack operation identity and reject forbidden field selections."""

    forbidden_tokens = ("rank", "mmr", "chat", "playback", "rolebasic", "behavior", "imp")
    seen_versions: set[str] = set()
    result: list[dict[str, Any]] = []
    for pack in PACKS:
        if pack.version in seen_versions:
            raise ValueError("pack versions must be unique")
        seen_versions.add(pack.version)
        operation = get_operation(pack.operation_name)
        paths = [field.path for field in pack.fields]
        if len(paths) != len(set(paths)):
            raise ValueError(f"duplicate field in {pack.name}")
        forbidden = [
            path for path in paths if any(token in path.lower() for token in forbidden_tokens)
        ]
        if forbidden:
            raise ValueError(f"forbidden field in {pack.name}: {forbidden}")
        result.append(
            {
                "name": pack.name,
                "version": pack.version,
                "operation": operation.name,
                "operation_version": operation.version,
                "operation_sha256": operation.document_sha256,
                "field_count": len(paths),
            }
        )
    return {"passed": True, "packs": result}


def build_corpus_plan(
    frame: SourceFrame,
    split_manifest: Mapping[str, Any],
    *,
    split_manifest_digest: str,
) -> dict[str, Any]:
    overlap = verify_no_split_overlap(split_manifest)
    sample_size = int(split_manifest["sample_size"])
    split_counts = {str(key): int(value) for key, value in split_manifest["split_counts"].items()}
    parsed_subset_counts = {
        str(key): int(value) for key, value in split_manifest["parsed_subset_counts"].items()
    }
    economics = calculate_economics(
        sample_size=sample_size,
        split_counts=split_counts,
        parsed_subset_counts=parsed_subset_counts,
    )
    pack_check = validate_pack_registry()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PREDECLARED_OFFLINE_RESEARCH_PLAN",
        "source_frame": frame.public_summary(),
        "split_manifest_sha256": split_manifest_digest,
        "split_counts": split_counts,
        "parsed_subset_counts": parsed_subset_counts,
        "partitions": {
            "DISCOVERY": "May be inspected for candidate discovery and feature design.",
            "CANDIDATE_TEST": "One predeclared confirmation pass remains viable; no adaptive top-up.",
            "CALIBRATION_RESERVED": "Reserved and not inspected or used in this phase.",
            "SEALED_VALIDATION": "Reserved and not inspected or used in this phase.",
        },
        "denominators": {
            "sampled_frame": {
                "count": frame.frame_count,
                "meaning": "accounts in the already-paid public-match-derived source frame",
                "representativeness": "not established",
            },
            "selected_preselection": {
                "count": SAMPLE_SIZE,
                "meaning": "fixed HMAC-selected accounts before discovery",
            },
            "product_eligible": {
                "count": None,
                "meaning": "public profile and product consent/availability after collection",
                "status": "unknown_until_collection",
            },
            "structural_eligible": {
                "count": None,
                "meaning": "declared mode/lobby/leaver/history support after native validation",
                "status": "unknown_until_collection; leaver semantics unresolved",
            },
            "information_eligible": {
                "count": None,
                "meaning": "candidate-specific non-null field opportunities after acquisition",
                "status": "unknown_until_collection; parsed availability is not assumed",
            },
        },
        "candidate_test_confirmation": {
            "history_accounts": split_counts["CANDIDATE_TEST"],
            "parsed_accounts": parsed_subset_counts["CANDIDATE_TEST"],
            "pass": "viable only if predeclared support and information gates pass; no final tails promised",
        },
        "packs": [pack.as_dict() for pack in PACKS],
        "pack_registry_check": pack_check,
        "split_overlap_check": overlap,
        "economics": economics,
        "policy": {
            "provider": "STRATZ",
            "storage": "ignored local-only raw archive with minimum retention",
            "public_commit": "aggregate-only; no raw/row-level data or identities",
            "rank_or_mmr_used": False,
            "finding_output_selection": False,
            "network_calls_during_freeze": {"stratz": 0, "opendota": 0},
        },
    }


def build_public_summary(
    frame: SourceFrame,
    split_manifest: Mapping[str, Any],
    *,
    split_manifest_digest: str,
    corpus_plan_digest: str | None = None,
) -> dict[str, Any]:
    """Emit only aggregate facts suitable for a committed evidence document."""

    verify_no_split_overlap(split_manifest)
    sample_size = int(split_manifest["sample_size"])
    split_counts = {str(key): int(value) for key, value in split_manifest["split_counts"].items()}
    parsed_subset_counts = {
        str(key): int(value) for key, value in split_manifest["parsed_subset_counts"].items()
    }
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_frame": frame.public_summary(),
        "selected_count": sample_size,
        "split_counts": split_counts,
        "parsed_subset_counts": parsed_subset_counts,
        "split_manifest_sha256": split_manifest_digest,
        "corpus_plan_sha256": corpus_plan_digest,
        "pack_registry": validate_pack_registry(),
        "economics": calculate_economics(
            sample_size=sample_size,
            split_counts=split_counts,
            parsed_subset_counts=parsed_subset_counts,
        ),
        "network_calls": {"stratz": 0, "opendota": 0},
    }
    encoded = json.dumps(summary, sort_keys=True, separators=(",", ":"))
    if any(str(record.account_id) in encoded for record in frame.records if record.account_id >= 1_000_000):
        raise ValueError("public summary contains a raw account identifier")
    return summary


def _write_private_json(path: Path, value: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    path.write_text(payload, encoding="utf-8")
    path.chmod(0o600)
    return sha256_file(path)


def _write_private_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    path.chmod(0o600)


def _write_private_digest(path: Path, digest_value: str) -> None:
    path.write_text(f"{digest_value}  {path.stem}.json\n", encoding="utf-8")
    path.chmod(0o600)


def generate_local_manifests(
    *,
    source_frame_path: Path = SOURCE_FRAME_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    salt: bytes | None = None,
) -> dict[str, Any]:
    """Generate a fresh local salt, private manifests, and sanitized summary."""

    frame = load_source_frame(source_frame_path)
    active_salt = secrets.token_bytes(32) if salt is None else salt
    if len(active_salt) != 32:
        raise ValueError("salt must be exactly 32 bytes")
    output_dir.mkdir(parents=True, exist_ok=True)
    salt_path = output_dir / "salt.bin"
    _write_private_bytes(salt_path, active_salt)
    split_manifest = build_split_manifest(frame, active_salt)
    split_path = output_dir / "manifests/split-manifest.json"
    split_digest = _write_private_json(split_path, split_manifest)
    _write_private_digest(output_dir / "manifests/split-manifest.sha256", split_digest)
    plan = build_corpus_plan(frame, split_manifest, split_manifest_digest=split_digest)
    plan_path = output_dir / "manifests/corpus-plan.json"
    plan_digest = _write_private_json(plan_path, plan)
    _write_private_digest(output_dir / "manifests/corpus-plan.sha256", plan_digest)
    summary = build_public_summary(
        frame,
        split_manifest,
        split_manifest_digest=split_digest,
        corpus_plan_digest=plan_digest,
    )
    summary_path = output_dir / "summary.json"
    _write_private_json(summary_path, summary)
    return {
        "output_dir": str(output_dir),
        "salt_sha256": hashlib.sha256(active_salt).hexdigest(),
        "split_manifest_sha256": split_digest,
        "corpus_plan_sha256": plan_digest,
        "summary": summary,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-frame", type=Path, default=SOURCE_FRAME_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    result = generate_local_manifests(source_frame_path=args.source_frame, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
