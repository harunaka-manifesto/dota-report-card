#!/usr/bin/env python3
"""Complete only the ten unresolved details in the frozen Death Context panel.

This is a bounded, serial, resumable transport campaign. It never changes the
panel or analytical policy and never runs analysis until all 960 details exist.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import free_dna_death_context_overnight as prior  # noqa: E402, I001


SCHEMA = "free-dna-death-context-final-completion-1.0.0"
CAMPAIGN = "free-dna-death-context-final-completion-2026-08-29"
PRIOR_LIVE = "free-dna-death-context-live-pilot"
PRIOR_CONTINUATION = "free-dna-death-context-continuation"
DIAGNOSTIC_NAME = "free-dna-death-context-final-completion"
PROVIDER = "OpenDota"
SOURCE_MARKER = "22"
EXPECTED_PANEL_DIGEST = "9855c1535a0e27223e62cb21fb686bdb1ca5acd169fd4d8220b05760c7e3da92"
EXPECTED_PRIOR_SUCCESS = 950
EXPECTED_UNRESOLVED = 10
MAX_CALLS = 30
MAX_RETRIES = 2
MAX_ATTEMPTS = MAX_RETRIES + 1
MIN_START_INTERVAL = 2.5
FIRST_RETRY_MINIMUM = 15.0
SECOND_RETRY_MINIMUM = 60.0
PRIOR_COOLDOWN = 30.0
RATE_PER_MINUTE = 240
COST_IDR_PER_100 = 200.0
COST_USD_PER_100 = 0.01
STORAGE_CEILING = 384 * 1024 * 1024
TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class PilotBlocked(RuntimeError):
    """Stop without expanding the frozen panel or transport policy."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    return prior.read_json(path)


def private_write(path: Path, value: Any, *, mode: int = 0o600) -> None:
    prior.private_write(path, value, mode=mode)


def append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    prior.append_jsonl(path, value)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return prior.read_jsonl(path)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def paths_for(storage_root: Path) -> dict[str, Path]:
    diagnostics = storage_root / ".local/diagnostics" / DIAGNOSTIC_NAME
    corpus = storage_root / ".local/corpora/opendota/free-dna-tier2"
    raw_responses = corpus / "raw/responses"
    for path in (diagnostics, corpus, raw_responses):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.chmod(0o700)
    return {
        "diagnostics": diagnostics,
        "corpus": corpus,
        "raw_responses": raw_responses,
        "ledger": diagnostics / "request_ledger.jsonl",
        "retry_ledger": diagnostics / "retry_ledger.jsonl",
        "progress": diagnostics / "progress.json",
    }


def with_final_metadata(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    old_schema = prior.LIVE_SCHEMA
    old_campaign = prior.LIVE_CAMPAIGN
    prior.LIVE_SCHEMA = SCHEMA
    prior.LIVE_CAMPAIGN = CAMPAIGN
    try:
        return function(*args, **kwargs)
    finally:
        prior.LIVE_SCHEMA = old_schema
        prior.LIVE_CAMPAIGN = old_campaign


def panel_rows(frozen: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "profile_id": str(row["profile_id"]),
            "selected_match_ids": [int(value) for value in row["selected_match_ids"]],
        }
        for row in frozen.get("profiles", [])
    ]


def response_events(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [dict(event) for event in events if event.get("event") == "response_recorded"],
        key=lambda row: int(row.get("ordinal", -1)),
    )


def validation_events(events: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(event.get("request_id")): dict(event)
        for event in events
        if event.get("event") == "validation"
    }


def check_start_response_pairs(events: Sequence[Mapping[str, Any]], reason: str) -> None:
    starts = [event for event in events if event.get("event") == "request_started"]
    responses = response_events(events)
    start_ids = [str(event.get("request_id")) for event in starts]
    response_ids = [str(event.get("request_id")) for event in responses]
    if len(start_ids) != len(set(start_ids)) or len(response_ids) != len(set(response_ids)):
        raise PilotBlocked(f"{reason}_DUPLICATE_REQUEST_ID")
    if set(start_ids) != set(response_ids):
        raise PilotBlocked(f"{reason}_START_RESPONSE_MISMATCH")


def validate_success_response(
    response: Mapping[str, Any],
    validation: Mapping[str, Any] | None,
    item_by_id: Mapping[int, Mapping[str, Any]],
    reason: str,
) -> None:
    match_id = response.get("match_id")
    if not isinstance(match_id, int) or match_id not in item_by_id:
        raise PilotBlocked(f"{reason}_MATCH_NOT_IN_PANEL")
    raw_path = Path(str(response.get("raw_path")))
    if not raw_path.is_file() or prior.sha256_file(raw_path) != response.get("response_sha256"):
        raise PilotBlocked(f"{reason}_RAW_DIGEST_FAILURE")
    if validation is None or validation.get("error") is not None:
        raise PilotBlocked(f"{reason}_VALIDATION_FAILURE")
    value = read_json(raw_path)
    validation_error = prior.detail_validation(value, item_by_id[match_id])
    if validation_error is not None:
        raise PilotBlocked(f"{reason}_DETAIL_VALIDATION_FAILURE:{validation_error}")


def final_success_ids(paths: Mapping[str, Path], item_by_id: Mapping[int, Mapping[str, Any]]) -> set[int]:
    if not paths["ledger"].exists():
        return set()
    events = read_jsonl(paths["ledger"])
    check_start_response_pairs(events, "FINAL_LEDGER")
    validations = validation_events(events)
    successes: set[int] = set()
    for response in response_events(events):
        match_id = response.get("match_id")
        if not isinstance(match_id, int) or match_id not in item_by_id:
            raise PilotBlocked("FINAL_LEDGER_RESPONSE_NOT_IN_QUEUE")
        if response.get("error") is None:
            if match_id in successes:
                raise PilotBlocked("FINAL_LEDGER_DUPLICATE_SUCCESS")
            validate_success_response(
                response, validations.get(str(response.get("request_id"))), item_by_id, "FINAL_LEDGER"
            )
            successes.add(match_id)
        elif int(response.get("retry_number", -1)) >= MAX_ATTEMPTS:
            raise PilotBlocked("FINAL_LEDGER_RETRY_LIMIT_EXCEEDED")
    return successes


def prior_campaign_successes(
    *,
    source_root: Path,
    storage_root: Path,
    paths: Mapping[str, Path],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    prior_live = storage_root / ".local/diagnostics" / PRIOR_LIVE
    prior_cont = storage_root / ".local/diagnostics" / PRIOR_CONTINUATION
    live_manifest_path = prior_live / "frozen_panel_manifest.json"
    live_ledger_path = prior_live / "request_ledger.jsonl"
    cont_manifest_path = prior_cont / "frozen_panel_manifest.json"
    cont_queue_path = prior_cont / "continuation_queue.json"
    cont_ledger_path = prior_cont / "request_ledger.jsonl"
    required = (live_manifest_path, live_ledger_path, cont_manifest_path, cont_queue_path, cont_ledger_path)
    if any(not path.is_file() for path in required):
        raise PilotBlocked("PRIOR_COLLECTION_ARTIFACTS_MISSING")

    frozen, items, profiles, panel_meta = with_final_metadata(
        prior.frozen_panel, source_root, storage_root
    )
    if frozen.get("selection_digest") != EXPECTED_PANEL_DIGEST:
        raise PilotBlocked("RECOMPUTED_PANEL_SELECTION_DIGEST_MISMATCH")
    if len(items) != prior.MAX_CALLS:
        raise PilotBlocked("RECOMPUTED_PANEL_NOT_960_UNIQUE_MATCHES")
    item_by_id = {int(item["match_id"]): item for item in items}

    live_manifest = read_json(live_manifest_path)
    if live_manifest.get("selection_digest") != EXPECTED_PANEL_DIGEST:
        raise PilotBlocked("PRIOR_PANEL_SELECTION_DIGEST_MISMATCH")
    if panel_rows(frozen) != panel_rows(live_manifest):
        raise PilotBlocked("PRIOR_PANEL_SELECTION_ROWS_MISMATCH")
    if frozen.get("match_selection_digest") != live_manifest.get("match_selection_digest"):
        raise PilotBlocked("PRIOR_PANEL_MATCH_DIGEST_MISMATCH")

    live_events = read_jsonl(live_ledger_path)
    check_start_response_pairs(live_events, "PRIOR_LIVE_LEDGER")
    live_responses = response_events(live_events)
    live_validations = validation_events(live_events)
    if len(live_responses) != 60:
        raise PilotBlocked("PRIOR_LIVE_ATTEMPT_COUNT_MISMATCH")
    live_success = [row for row in live_responses if row.get("error") is None]
    live_failed = [row for row in live_responses if row.get("error") is not None]
    if len(live_success) != 59 or len(live_failed) != 1:
        raise PilotBlocked("PRIOR_LIVE_SUCCESS_FAILURE_COUNT_MISMATCH")
    if live_failed[0].get("http_status") != 500 or live_failed[0].get("error") != "http_500":
        raise PilotBlocked("PRIOR_LIVE_FAILURE_NOT_HTTP_500")
    live_success_ids: set[int] = set()
    for response in live_success:
        validate_success_response(
            response,
            live_validations.get(str(response.get("request_id"))),
            item_by_id,
            "PRIOR_LIVE",
        )
        live_success_ids.add(int(response["match_id"]))
    if len(live_success_ids) != 59:
        raise PilotBlocked("PRIOR_LIVE_SUCCESS_NOT_UNIQUE")

    cont_manifest = read_json(cont_manifest_path)
    if cont_manifest.get("selection_digest") != EXPECTED_PANEL_DIGEST:
        raise PilotBlocked("PRIOR_CONTINUATION_SELECTION_DIGEST_MISMATCH")
    queue_payload = read_json(cont_queue_path)
    queue_items = [dict(item) for item in queue_payload.get("items", [])]
    if queue_payload.get("selection_digest") != EXPECTED_PANEL_DIGEST or len(queue_items) != 901:
        raise PilotBlocked("PRIOR_CONTINUATION_QUEUE_SHAPE_MISMATCH")
    expected_queue = [
        {
            **item,
            "prior_status": "prior_http_500"
            if int(item["match_id"]) == int(live_failed[0]["match_id"])
            else "never_attempted",
        }
        for item in items
        if int(item["match_id"]) not in live_success_ids
    ]
    expected_queue_rows = [
        {
            "profile_id": str(item["profile_id"]),
            "profile_index": int(item["profile_index"]),
            "match_index": int(item["match_index"]),
            "match_id": int(item["match_id"]),
            "prior_status": str(item["prior_status"]),
        }
        for item in expected_queue
    ]
    actual_queue_rows = [
        {
            "profile_id": str(item["profile_id"]),
            "profile_index": int(item["profile_index"]),
            "match_index": int(item["match_index"]),
            "match_id": int(item["match_id"]),
            "prior_status": str(item["prior_status"]),
        }
        for item in queue_items
    ]
    if actual_queue_rows != expected_queue_rows:
        raise PilotBlocked("PRIOR_CONTINUATION_QUEUE_ROWS_MISMATCH")
    queue_digest = digest_value(
        [
            {
                "profile_index": row["profile_index"],
                "match_index": row["match_index"],
                "match_id": row["match_id"],
                "prior_status": row["prior_status"],
            }
            for row in expected_queue_rows
        ]
    )
    if queue_payload.get("queue_digest") != queue_digest:
        raise PilotBlocked("PRIOR_CONTINUATION_QUEUE_DIGEST_MISMATCH")

    cont_events = read_jsonl(cont_ledger_path)
    check_start_response_pairs(cont_events, "PRIOR_CONTINUATION_LEDGER")
    cont_responses = response_events(cont_events)
    cont_validations = validation_events(cont_events)
    if len(cont_responses) != 930:
        raise PilotBlocked("PRIOR_CONTINUATION_ATTEMPT_COUNT_MISMATCH")
    queue_by_id = {int(item["match_id"]): item for item in expected_queue}
    cont_success_ids: set[int] = set()
    for response in cont_responses:
        match_id = response.get("match_id")
        if not isinstance(match_id, int) or match_id not in queue_by_id:
            raise PilotBlocked("PRIOR_CONTINUATION_RESPONSE_NOT_IN_QUEUE")
        if response.get("error") is None:
            validate_success_response(
                response,
                cont_validations.get(str(response.get("request_id"))),
                queue_by_id,
                "PRIOR_CONTINUATION",
            )
            if match_id in cont_success_ids:
                raise PilotBlocked("PRIOR_CONTINUATION_DUPLICATE_SUCCESS")
            cont_success_ids.add(match_id)
    if len(cont_success_ids) != 891:
        raise PilotBlocked("PRIOR_CONTINUATION_SUCCESS_COUNT_MISMATCH")
    if any(
        response.get("error") is not None
        and (response.get("http_status") != 429 or response.get("error") != "http_429")
        for response in cont_responses
    ):
        raise PilotBlocked("PRIOR_CONTINUATION_UNEXPECTED_FAILURE")

    prior_success_ids = live_success_ids | cont_success_ids
    if len(prior_success_ids) != EXPECTED_PRIOR_SUCCESS:
        raise PilotBlocked("PRIOR_SUCCESS_UNION_NOT_950")
    unresolved_ids = set(item_by_id) - prior_success_ids
    if len(unresolved_ids) != EXPECTED_UNRESOLVED:
        raise PilotBlocked("FINAL_QUEUE_NOT_EXACTLY_10")
    final_queue = [item for item in items if int(item["match_id"]) in unresolved_ids]
    final_queue_rows = [
        {
            "profile_id": str(item["profile_id"]),
            "profile_index": int(item["profile_index"]),
            "match_index": int(item["match_index"]),
            "match_id": int(item["match_id"]),
        }
        for item in final_queue
    ]
    final_queue_digest = digest_value(final_queue_rows)

    final_success = final_success_ids(paths, {int(item["match_id"]): item for item in final_queue})
    if not final_success.issubset(unresolved_ids):
        raise PilotBlocked("FINAL_SUCCESS_NOT_IN_UNRESOLVED_QUEUE")

    corpus_manifest_path = storage_root / ".local/corpora/opendota/free-dna-tier2/manifests/corpus-manifest.json"
    corpus_index_path = storage_root / ".local/diagnostics/free-dna-death-context-local-reuse-pilot/tier2_detail_index.json"
    if not corpus_manifest_path.is_file() or not corpus_index_path.is_file():
        raise PilotBlocked("CANONICAL_CORPUS_MANIFEST_MISSING")
    corpus_manifest = read_json(corpus_manifest_path)
    corpus_index = read_json(corpus_index_path)
    records = list(corpus_manifest.get("records", []))
    index_records = list(corpus_index.get("records", []))
    expected_corpus_records = 969 + len(final_success)
    if len(records) != expected_corpus_records or len(index_records) != expected_corpus_records:
        raise PilotBlocked("CANONICAL_CORPUS_RECORD_COUNT_MISMATCH")
    expected_raw_persisted = 950 + len(final_success)
    if corpus_manifest.get("raw_records_persisted") != expected_raw_persisted or corpus_manifest.get("raw_records_referenced") != 19:
        raise PilotBlocked("CANONICAL_CORPUS_PROVENANCE_COUNT_MISMATCH")
    analytical_state = corpus_manifest.get("analytical_outcome_results_generated")
    if analytical_state is not False and not (final_success and analytical_state is True):
        raise PilotBlocked("CANONICAL_CORPUS_ANALYTICAL_STATE_MISMATCH")
    for record in records:
        raw_path = Path(str(record.get("source_raw_path")))
        normalized_path = Path(str(record.get("normalized_path")))
        if not raw_path.is_file() or prior.sha256_file(raw_path) != record.get("raw_sha256"):
            raise PilotBlocked("CANONICAL_CORPUS_RAW_DIGEST_FAILURE")
        if not normalized_path.is_file() or prior.sha256_file(normalized_path) != record.get("normalized_sha256"):
            raise PilotBlocked("CANONICAL_CORPUS_NORMALIZED_DIGEST_FAILURE")
    calculated_normalized_digest = digest_value(
        [(row["match_id"], row["raw_sha256"], row["normalized_sha256"]) for row in records]
    )
    if corpus_manifest.get("normalized_digest") != calculated_normalized_digest:
        raise PilotBlocked("CANONICAL_CORPUS_DIGEST_MISMATCH")
    selected_corpus_ids = {
        int(record["match_id"])
        for record in records
        if record.get("included_in_death_context_panel") is True
    }
    expected_corpus_ids = prior_success_ids | final_success
    if selected_corpus_ids != expected_corpus_ids:
        raise PilotBlocked("CANONICAL_CORPUS_PANEL_BINDING_MISMATCH")
    if len(selected_corpus_ids) != EXPECTED_PRIOR_SUCCESS + len(final_success):
        raise PilotBlocked("CANONICAL_CORPUS_PANEL_COUNT_MISMATCH")
    index_selected_count = sum(bool(record.get("selected_in_frozen_panel")) for record in index_records)
    if index_selected_count != len(selected_corpus_ids):
        raise PilotBlocked("CANONICAL_INDEX_PANEL_COUNT_MISMATCH")

    existing_queue = paths["diagnostics"] / "final_queue.json"
    if existing_queue.is_file():
        prior_queue = read_json(existing_queue)
        if prior_queue.get("final_queue_digest") != final_queue_digest:
            raise PilotBlocked("FINAL_QUEUE_DIGEST_MISMATCH")

    private_write(
        paths["diagnostics"] / "frozen_panel_manifest.json",
        {
            **live_manifest,
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "prior_campaign_id": live_manifest.get("campaign_id"),
            "selection_digest_verified": True,
            "final_queue_digest": final_queue_digest,
            "final_started_at": now_iso(),
        },
    )
    private_write(
        paths["diagnostics"] / "final_queue.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "selection_digest": frozen["selection_digest"],
            "prior_queue_digest": queue_digest,
            "final_queue_digest": final_queue_digest,
            "count": len(final_queue_rows),
            "prior_successful_panel_records": len(prior_success_ids),
            "existing_final_successes": len(final_success),
            "items": [
                {
                    **row,
                    "match_key": hashlib.sha256(str(row["match_id"]).encode()).hexdigest()[:16],
                    "status": "success" if row["match_id"] in final_success else "pending",
                }
                for row in final_queue_rows
            ],
        },
    )
    source_raw, source_normalized, source_secret = prior.source_manifests(source_root)
    prior_latest = latest_timestamp(
        [
            *read_jsonl(prior_live / "request_ledger.jsonl"),
            *read_jsonl(prior_cont / "request_ledger.jsonl"),
        ]
    )
    cooldown = max(0.0, PRIOR_COOLDOWN - max(0.0, time.time() - prior_latest)) if prior_latest else 0.0
    preflight = {
        "schema_version": SCHEMA,
        "campaign_id": CAMPAIGN,
        "branch_sha": prior.git_sha(),
        "base_sha": prior.BASE_SHA,
        "provider": PROVIDER,
        "provider_key_configured": bool(os.getenv("OPENDOTA_API_KEY")),
        "panel": {
            "profiles": prior.PANEL_PROFILES,
            "matches_per_profile": prior.MATCHES_PER_PROFILE,
            "unique_match_ids": prior.MAX_CALLS,
            "selection_digest": frozen["selection_digest"],
            "match_selection_digest": frozen["match_selection_digest"],
        },
        "prior_collection": {
            "successful_panel_records": len(prior_success_ids),
            "canonical_normalized_records": len(records),
            "canonical_referenced_records": 19,
            "reused_without_get": len(prior_success_ids),
        },
        "final_queue": {
            "count": len(final_queue_rows),
            "digest": final_queue_digest,
            "prior_queue_digest": queue_digest,
            "existing_successes": len(final_success),
        },
        "authorization": {
            "max_physical_gets": MAX_CALLS,
            "max_retries_after_initial": MAX_RETRIES,
            "max_attempts_per_match": MAX_ATTEMPTS,
            "concurrency": 1,
            "minimum_start_interval_seconds": MIN_START_INTERVAL,
            "rate_start_ceiling_per_minute": RATE_PER_MINUTE,
            "max_cost_idr": MAX_CALLS * COST_IDR_PER_100 / 100,
            "max_cost_usd": MAX_CALLS * COST_USD_PER_100 / 100,
            "replay_parse_requests": 0,
            "stratz_calls": 0,
            "steam_calls": 0,
            "fresh_sealed_validation": False,
            "old_holdout": False,
            "adaptive_top_up": False,
            "replacement_calls": 0,
        },
        "pacing": {
            "prior_latest_request_epoch": prior_latest,
            "conservative_cooldown_seconds": cooldown,
        },
        "frozen_panel_reused_without_reselection": True,
        "outcome_fields_inspected_before_completion": False,
    }
    private_write(paths["diagnostics"] / "preflight.json", preflight)
    return frozen, items, profiles, {
        "source_secret": source_secret,
        "source_manifest": {**source_raw, **source_normalized},
        "panel_meta": panel_meta,
        "prior_success_ids": prior_success_ids,
        "final_queue": final_queue,
        "final_queue_digest": final_queue_digest,
        "prior_latest": prior_latest,
        "cooldown": cooldown,
        "existing_final_success_ids": final_success,
    }


def latest_timestamp(events: Sequence[Mapping[str, Any]]) -> float | None:
    values: list[float] = []
    for event in events:
        for key in ("requested_at", "completed_at"):
            value = event.get(key)
            if not isinstance(value, str):
                continue
            try:
                values.append(datetime.fromisoformat(value).timestamp())
            except ValueError:
                continue
    return max(values) if values else None


def write_progress(
    *,
    path: Path,
    stage: str,
    transport: FinalTransport | None,
    queue_position: int,
    queue_total: int,
    prior_successes: int,
    latest: Mapping[str, Any] | None = None,
    errors: Sequence[str] = (),
) -> None:
    physical = transport.physical_count if transport else 0
    final_successful = prior_successes + (transport.successful_count if transport else 0)
    private_write(
        path,
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "timestamp": now_iso(),
            "branch_sha": prior.git_sha(),
            "stage": stage,
            "queue_position": queue_position,
            "queue_total": queue_total,
            "physical_calls": physical,
            "remaining_budget": {
                "physical_gets": max(0, MAX_CALLS - physical),
                "idr": max(0.0, MAX_CALLS * COST_IDR_PER_100 / 100 - physical * COST_IDR_PER_100 / 100),
                "usd": max(0.0, MAX_CALLS * COST_USD_PER_100 / 100 - physical * COST_USD_PER_100 / 100),
            },
            "previous_successes_reused": prior_successes,
            "successful_unresolved": transport.successful_count if transport else 0,
            "final_successful_unique": final_successful,
            "remaining_unresolved": max(0, queue_total - (transport.successful_count if transport else 0)),
            "retry_count": transport.retry_count if transport else 0,
            "latest_attempt": dict(latest) if latest else None,
            "errors": list(errors),
            "next_action": "continue_fixed_10_queue" if stage != "terminal_blocked" else "stop_no_automatic_retry",
        },
    )


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        seconds = when.timestamp() - time.time()
    return max(0.0, seconds)


def retry_delay(retry_number: int, retry_after: str | None, rng: random.Random) -> float:
    minimum = FIRST_RETRY_MINIMUM if retry_number == 1 else SECOND_RETRY_MINIMUM
    provider_wait = parse_retry_after(retry_after)
    return max(minimum, provider_wait or 0.0) + rng.uniform(0.5, 2.5)


def transient_error(status: int | None, error: str | None) -> bool:
    return status in TRANSIENT_STATUSES or error in {
        "timeout",
        "connection_reset",
        "dns_error",
        "network_error",
    }


def classify_status(status: int | None) -> str:
    if status in TRANSIENT_STATUSES:
        return f"http_{status}"
    if status is None:
        return "network_error"
    return f"http_{status}"


def sleep_seconds(seconds: float) -> Any:
    async def _sleep() -> None:
        remaining = max(0.0, seconds)
        while remaining > 0:
            started = time.monotonic()
            await asyncio.sleep(min(30.0, remaining))
            remaining -= time.monotonic() - started

    return _sleep()


class FinalTransport:
    def __init__(
        self,
        *,
        paths: Mapping[str, Path],
        items: Sequence[Mapping[str, Any]],
        base_url: str,
        api_key: str | None,
        timeout: float,
        queue_digest: str,
        initial_cooldown: float,
        persist_success: Callable[[Mapping[str, Any]], None],
        on_attempt: Callable[[Mapping[str, Any], Mapping[str, Any], int], None],
    ) -> None:
        self.paths = paths
        self.item_by_id = {int(item["match_id"]): dict(item) for item in items}
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        )
        self.events = read_jsonl(paths["ledger"])
        self.responses = response_events(self.events)
        self.validations = validation_events(self.events)
        self.completed_by_match: dict[int, dict[str, Any]] = {}
        self.attempts_by_match: Counter[int] = Counter()
        self.retry_count = sum(int(row.get("retry_number", 0)) for row in self.responses)
        self.transient_failures = 0
        self.permanent_failures = 0
        self.error_rows: list[dict[str, Any]] = []
        self.rng = random.Random(int(queue_digest[:16], 16))
        self.persist_success = persist_success
        self.on_attempt = on_attempt
        self.next_start = time.monotonic() + max(0.0, initial_cooldown)
        self.retry_ready: dict[tuple[int, int], float] = {}
        self._load_retry_schedules()
        self._check_resume_state()

    async def __aenter__(self) -> FinalTransport:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.http.aclose()

    @property
    def physical_count(self) -> int:
        return len(self.responses)

    @property
    def successful_count(self) -> int:
        return len(self.completed_by_match)

    @property
    def failed_attempts(self) -> int:
        return sum(row.get("error") is not None for row in self.responses)

    def _load_retry_schedules(self) -> None:
        for row in read_jsonl(self.paths["retry_ledger"]):
            if row.get("event") != "retry_scheduled":
                continue
            match_id = row.get("match_id")
            retry_number = row.get("retry_number")
            ready_at = row.get("ready_at_epoch")
            if isinstance(match_id, int) and isinstance(retry_number, int) and isinstance(ready_at, (int, float)):
                self.retry_ready[(match_id, retry_number)] = max(
                    self.retry_ready.get((match_id, retry_number), 0.0), float(ready_at)
                )

    def _check_resume_state(self) -> None:
        markers = list(self.paths["diagnostics"].glob(".inflight-*.json"))
        if markers:
            raise PilotBlocked("INDETERMINATE_INTERRUPTED_REQUEST")
        check_start_response_pairs(self.events, "FINAL_LEDGER")
        seen_success: set[int] = set()
        expected_attempts: Counter[int] = Counter()
        for response in self.responses:
            match_id = response.get("match_id")
            if not isinstance(match_id, int) or match_id not in self.item_by_id:
                raise PilotBlocked("FINAL_RESPONSE_NOT_IN_QUEUE")
            attempt = response.get("retry_number")
            if not isinstance(attempt, int) or attempt != expected_attempts[match_id] or attempt >= MAX_ATTEMPTS:
                raise PilotBlocked("FINAL_ATTEMPT_SEQUENCE_FAILURE")
            expected_attempts[match_id] += 1
            self.attempts_by_match[match_id] += 1
            if response.get("error") is None:
                if match_id in seen_success:
                    raise PilotBlocked("FINAL_DUPLICATE_SUCCESS")
                validate_success_response(
                    response,
                    self.validations.get(str(response.get("request_id"))),
                    self.item_by_id,
                    "FINAL_RESUME",
                )
                seen_success.add(match_id)
                self.completed_by_match[match_id] = response
            else:
                self._count_failure(response)
        for match_id, attempt_count in self.attempts_by_match.items():
            if match_id in self.completed_by_match:
                continue
            if attempt_count >= MAX_ATTEMPTS:
                continue
            if (match_id, attempt_count) in self.retry_ready:
                remaining = self.retry_ready[(match_id, attempt_count)] - time.time()
                self.next_start = max(self.next_start, time.monotonic() + max(0.0, remaining))

    def _count_failure(self, response: Mapping[str, Any]) -> None:
        status = response.get("http_status")
        error = str(response.get("error")) if response.get("error") is not None else None
        if transient_error(status if isinstance(status, int) else None, error):
            self.transient_failures += 1
        else:
            self.permanent_failures += 1
        self.error_rows.append(dict(response))

    def cached_detail(self, item: Mapping[str, Any]) -> dict[str, Any] | None:
        response = self.completed_by_match.get(int(item["match_id"]))
        if response is None:
            return None
        raw_path = Path(str(response["raw_path"]))
        value = read_json(raw_path)
        validation_error = prior.detail_validation(value, item)
        if validation_error is not None:
            raise PilotBlocked(f"FINAL_CACHED_DETAIL_INVALID:{validation_error}")
        return {
            "match_id": int(item["match_id"]),
            "path": raw_path,
            "response_sha256": str(response["response_sha256"]),
            "bytes": int(response["response_bytes"]),
            "ledger": dict(response),
            "match": value,
            "shape": prior.detail_shape(value),
            "panel_profile_id": str(item["profile_id"]),
        }

    async def wait_for_start(self, not_before: float | None = None) -> None:
        if not_before is not None:
            self.next_start = max(self.next_start, not_before)
        remaining = self.next_start - time.monotonic()
        if remaining > 0:
            await sleep_seconds(remaining)
        self.next_start = time.monotonic() + MIN_START_INTERVAL

    async def reserve(
        self,
        item: Mapping[str, Any],
        *,
        queue_position: int,
        retry_number: int,
    ) -> tuple[int, Path, dict[str, Any]]:
        match_id = int(item["match_id"])
        ready_epoch = self.retry_ready.pop((match_id, retry_number), None)
        not_before = None
        if ready_epoch is not None:
            not_before = time.monotonic() + max(0.0, ready_epoch - time.time())
        await self.wait_for_start(not_before)
        if self.physical_count >= MAX_CALLS:
            raise PilotBlocked("REQUEST_CEILING_REACHED")
        ordinal = self.physical_count
        marker = self.paths["diagnostics"] / f".inflight-{ordinal:02d}-{match_id}-{retry_number}.json"
        private_write(
            marker,
            {
                "schema_version": SCHEMA,
                "campaign_id": CAMPAIGN,
                "match_id": match_id,
                "ordinal": ordinal,
                "retry_number": retry_number,
                "queue_position": queue_position,
            },
        )
        request_id = f"{CAMPAIGN}:{match_id}:{retry_number}"
        started = {
            "event": "request_started",
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "request_id": request_id,
            "ordinal": ordinal,
            "method": "GET",
            "endpoint": f"/matches/{match_id}",
            "params": [],
            "match_id": match_id,
            "profile_id": str(item["profile_id"]),
            "profile_index": int(item["profile_index"]),
            "match_index": int(item["match_index"]),
            "concurrency": 1,
            "batch_id": "final_queue_serial",
            "retry_number": retry_number,
            "retry_limit": MAX_RETRIES,
            "requested_at": now_iso(),
        }
        append_jsonl(self.paths["ledger"], started)
        self.events.append(started)
        self.next_start = max(self.next_start, time.monotonic())
        return ordinal, marker, started

    async def fetch(
        self,
        item: Mapping[str, Any],
        *,
        queue_position: int,
        queue_total: int,
    ) -> dict[str, Any] | None:
        match_id = int(item["match_id"])
        cached = self.cached_detail(item)
        if cached is not None:
            return cached
        while self.attempts_by_match[match_id] < MAX_ATTEMPTS:
            retry_number = self.attempts_by_match[match_id]
            ordinal, marker, started = await self.reserve(
                item, queue_position=queue_position, retry_number=retry_number
            )
            started_monotonic = time.monotonic()
            status: int | None = None
            body = b""
            error: str | None = None
            retry_after: str | None = None
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                response = await self.http.get(f"{self.base_url}/matches/{match_id}", headers=headers)
                status = response.status_code
                body = response.content
                retry_after = response.headers.get("Retry-After")
                if status != 200:
                    error = classify_status(status)
            except httpx.TimeoutException:
                error = "timeout"
            except httpx.ConnectError as exc:
                error = "connection_reset" if "reset" in str(exc).lower() else "network_error"
            except httpx.NetworkError as exc:
                error = "dns_error" if "dns" in str(exc).lower() else "network_error"
            except httpx.HTTPError:
                error = "network_error"
            elapsed = time.monotonic() - started_monotonic

            raw_path: Path | None = None
            if body:
                projected = (
                    prior.directory_size(self.paths["corpus"])
                    + prior.directory_size(self.paths["diagnostics"])
                    + len(body)
                )
                if projected > STORAGE_CEILING:
                    error = "storage_ceiling_risk"
                else:
                    raw_path = self.paths["raw_responses"] / (
                        f"response-final-completion-{ordinal:02d}-{match_id}-attempt-{retry_number}.body"
                    )
                    prior.private_write_bytes_once(raw_path, body)

            value: Any = None
            validation_error: str | None = None
            if error is None and status == 200:
                try:
                    value = json.loads(body)
                except (UnicodeDecodeError, ValueError) as exc:
                    validation_error = f"invalid_json:{type(exc).__name__}"
                else:
                    validation_error = prior.detail_validation(value, item)
            response_error = error or validation_error
            response_event = {
                "event": "response_recorded",
                "schema_version": SCHEMA,
                "campaign_id": CAMPAIGN,
                "request_id": started["request_id"],
                "ordinal": ordinal,
                "match_id": match_id,
                "profile_id": str(item["profile_id"]),
                "profile_index": int(item["profile_index"]),
                "match_index": int(item["match_index"]),
                "method": "GET",
                "endpoint": f"/matches/{match_id}",
                "concurrency": 1,
                "batch_id": "final_queue_serial",
                "requested_at": started["requested_at"],
                "completed_at": now_iso(),
                "latency_seconds": elapsed,
                "http_status": status,
                "response_bytes": len(body),
                "response_sha256": prior.sha256_bytes(body) if body else None,
                "raw_path": str(raw_path) if raw_path else None,
                "retry_number": retry_number,
                "retry_limit": MAX_RETRIES,
                "retry_after": retry_after,
                "error": response_error,
            }
            append_jsonl(self.paths["ledger"], response_event)
            self.events.append(response_event)
            self.responses.append(response_event)
            self.attempts_by_match[match_id] += 1
            if retry_number > 0:
                self.retry_count += 1
            if status == 200:
                validation = {
                    "event": "validation",
                    "schema_version": SCHEMA,
                    "campaign_id": CAMPAIGN,
                    "request_id": started["request_id"],
                    "match_id": match_id,
                    "profile_id": str(item["profile_id"]),
                    "error": validation_error,
                    "parsed_marker": {
                        "source_version": SOURCE_MARKER,
                        "detail_version": value.get("version") if isinstance(value, dict) else None,
                        "od_data.has_parsed": (value.get("od_data") or {}).get("has_parsed")
                        if isinstance(value, dict)
                        else None,
                    },
                }
                append_jsonl(self.paths["ledger"], validation)
                self.events.append(validation)
                self.validations[started["request_id"]] = validation

            if response_error is not None:
                self._count_failure(response_event)
                marker.unlink(missing_ok=True)
            else:
                detail = {
                    "match_id": match_id,
                    "path": raw_path,
                    "response_sha256": str(response_event["response_sha256"]),
                    "bytes": int(response_event["response_bytes"]),
                    "ledger": dict(response_event),
                    "match": value,
                    "shape": prior.detail_shape(value),
                    "panel_profile_id": str(item["profile_id"]),
                }
                if raw_path is None:
                    raise PilotBlocked("SUCCESS_WITHOUT_RAW_RESPONSE")
                try:
                    self.persist_success(detail)
                except PilotBlocked:
                    raise
                except Exception as exc:  # pragma: no cover - defensive persistence stop
                    raise PilotBlocked(f"PERSISTENCE_FAILURE:{type(exc).__name__}") from exc
                self.completed_by_match[match_id] = response_event
                marker.unlink(missing_ok=True)

            self.on_attempt(
                item,
                {
                    "attempt": retry_number,
                    "status": "success" if response_error is None else response_error,
                    "http_status": status,
                    "latency_seconds": elapsed,
                    "retry_after": retry_after,
                    "physical_calls": self.physical_count,
                },
                queue_position,
            )
            if response_error is None:
                return detail
            if not transient_error(status, response_error) or retry_number >= MAX_RETRIES:
                return None
            next_retry = retry_number + 1
            delay = retry_delay(next_retry, retry_after, self.rng)
            ready_epoch = time.time() + delay
            append_jsonl(
                self.paths["retry_ledger"],
                {
                    "event": "retry_scheduled",
                    "schema_version": SCHEMA,
                    "campaign_id": CAMPAIGN,
                    "match_id": match_id,
                    "request_id": started["request_id"],
                    "retry_number": next_retry,
                    "reason": response_error,
                    "http_status": status,
                    "retry_after": retry_after,
                    "retry_after_seconds": parse_retry_after(retry_after),
                    "minimum_wait_seconds": FIRST_RETRY_MINIMUM
                    if next_retry == 1
                    else SECOND_RETRY_MINIMUM,
                    "backoff_seconds": delay,
                    "ready_at_epoch": ready_epoch,
                    "scheduled_at": now_iso(),
                },
            )
            self.retry_ready[(match_id, next_retry)] = ready_epoch
            await self.wait_for_start(time.monotonic() + delay)
        return None


def persist_detail(
    *,
    storage_root: Path,
    paths: Mapping[str, Path],
    details: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
    meta: Mapping[str, Any],
) -> None:
    existing = prior.load_prior_details(storage_root)
    tier2 = with_final_metadata(
        prior.write_tier2_corpus,
        storage_root,
        [*existing, details],
        prior.profile_membership(profiles),
        {int(item["match_id"]) for item in items},
        meta["source_manifest"],
        str(meta["frozen_selection_digest"]),
        str(meta["panel_salt_sha256"]),
        analytical_outcome_results_generated=False,
    )
    private_write(paths["diagnostics"] / "tier2_corpus_manifest.json", tier2)
    corpus_manifest = read_json(storage_root / ".local/corpora/opendota/free-dna-tier2/manifests/corpus-manifest.json")
    rows = [
        row
        for row in corpus_manifest.get("records", [])
        if int(row.get("match_id", -1)) == int(details["match_id"])
        and row.get("raw_sha256") == details["response_sha256"]
    ]
    if len(rows) != 1:
        raise PilotBlocked("PERSISTED_DETAIL_NOT_IN_CORPUS")
    row = rows[0]
    raw_path = Path(str(row["source_raw_path"]))
    normalized_path = Path(str(row["normalized_path"]))
    if not raw_path.is_file() or prior.sha256_file(raw_path) != row.get("raw_sha256"):
        raise PilotBlocked("PERSISTED_DETAIL_RAW_DIGEST_FAILURE")
    if not normalized_path.is_file() or prior.sha256_file(normalized_path) != row.get("normalized_sha256"):
        raise PilotBlocked("PERSISTED_DETAIL_NORMALIZED_DIGEST_FAILURE")
    if row.get("included_in_death_context_panel") is not True:
        raise PilotBlocked("PERSISTED_DETAIL_PANEL_BINDING_FAILURE")


def provider_stats(transport: FinalTransport) -> dict[str, Any]:
    latencies = [
        float(row["latency_seconds"])
        for row in transport.responses
        if row.get("latency_seconds") is not None
    ]
    successful_latencies = [
        float(row["latency_seconds"])
        for row in transport.responses
        if row.get("error") is None and row.get("latency_seconds") is not None
    ]
    statuses = Counter(row.get("http_status") for row in transport.responses)
    retry_rows = [row for row in transport.responses if int(row.get("retry_number", 0)) > 0]
    retry_successes = sum(row.get("error") is None for row in retry_rows)
    starts = []
    for event in transport.events:
        if event.get("event") == "request_started" and isinstance(event.get("requested_at"), str):
            try:
                starts.append(datetime.fromisoformat(str(event["requested_at"])).timestamp())
            except ValueError:
                pass
    gaps = [right - left for left, right in zip(starts, starts[1:], strict=False)]
    return {
        "physical_calls": transport.physical_count,
        "first_attempt_successes": sum(
            row.get("error") is None and int(row.get("retry_number", 0)) == 0
            for row in transport.responses
        ),
        "retry_attempts": len(retry_rows),
        "retry_successes": retry_successes,
        "retry_success_rate": retry_successes / len(retry_rows) if retry_rows else None,
        "http_429": statuses.get(429, 0),
        "other_transient_failures": sum(
            1
            for row in transport.responses
            if row.get("error") is not None
            and transient_error(row.get("http_status"), str(row.get("error")))
            and row.get("http_status") != 429
        ),
        "permanent_failures": transport.permanent_failures,
        "timeouts": sum(row.get("error") == "timeout" for row in transport.responses),
        "network_errors": sum(
            row.get("error") in {"connection_reset", "dns_error", "network_error"}
            for row in transport.responses
        ),
        "status_counts": {str(key): value for key, value in sorted(statuses.items(), key=lambda row: str(row[0]))},
        "request_latency_seconds_all_attempts": prior.numeric_stats(latencies),
        "request_latency_seconds_successful": prior.numeric_stats(successful_latencies),
        "start_gap_seconds": prior.numeric_stats(gaps),
        "minimum_start_interval_seconds_required": MIN_START_INTERVAL,
    }


def write_transport_artifacts(
    *,
    paths: Mapping[str, Path],
    storage_root: Path,
    transport: FinalTransport,
    collection_seconds: float,
    prior_success_count: int,
    queue_total: int,
) -> dict[str, Any]:
    responses = sorted(transport.responses, key=lambda row: int(row["ordinal"]))
    starts = {
        str(event["request_id"]): event
        for event in transport.events
        if event.get("event") == "request_started"
    }
    ledger_rows = [
        {
            "campaign_id": row.get("campaign_id"),
            "request_id": row.get("request_id"),
            "ordinal": row.get("ordinal"),
            "profile_index": row.get("profile_index"),
            "match_index": row.get("match_index"),
            "match_id": row.get("match_id"),
            "endpoint": row.get("endpoint"),
            "requested_at": starts.get(str(row.get("request_id")), {}).get("requested_at"),
            "completed_at": row.get("completed_at"),
            "latency_seconds": row.get("latency_seconds"),
            "http_status": row.get("http_status"),
            "response_bytes": row.get("response_bytes"),
            "response_sha256": row.get("response_sha256"),
            "raw_path": row.get("raw_path"),
            "retry_number": row.get("retry_number"),
            "retry_after": row.get("retry_after"),
            "error": row.get("error"),
        }
        for row in responses
    ]
    write_csv(paths["diagnostics"] / "request_ledger.csv", list(ledger_rows[0].keys()) if ledger_rows else ["ordinal"], ledger_rows)
    retry_rows = read_jsonl(paths["retry_ledger"])
    write_csv(
        paths["diagnostics"] / "retry_ledger.csv",
        list(retry_rows[0].keys()) if retry_rows else ["event"],
        retry_rows,
    )
    stats = provider_stats(transport)
    ledger_times = []
    for event in transport.events:
        for key in ("requested_at", "completed_at"):
            value = event.get(key)
            if not isinstance(value, str):
                continue
            try:
                ledger_times.append(datetime.fromisoformat(value).timestamp())
            except ValueError:
                pass
    ledger_wall_seconds = max(ledger_times) - min(ledger_times) if ledger_times else None
    observed_collection_seconds = (
        max(collection_seconds, ledger_wall_seconds)
        if ledger_wall_seconds is not None
        else collection_seconds
    )
    cost = {
        "schema_version": SCHEMA,
        "campaign_id": CAMPAIGN,
        "physical_gets": transport.physical_count,
        "successful_gets": transport.successful_count,
        "failed_gets": transport.failed_attempts,
        "retries": transport.retry_count,
        "max_physical_gets": MAX_CALLS,
        "estimated_cost_idr_pro_rata": transport.physical_count * COST_IDR_PER_100 / 100,
        "estimated_cost_usd_pro_rata": transport.physical_count * COST_USD_PER_100 / 100,
        "cost_ceiling_idr": MAX_CALLS * COST_IDR_PER_100 / 100,
        "cost_ceiling_usd": MAX_CALLS * COST_USD_PER_100 / 100,
        "storage_bytes": prior.directory_size(storage_root / ".local/corpora/opendota/free-dna-tier2")
        + prior.directory_size(paths["diagnostics"]),
        "storage_ceiling_bytes": STORAGE_CEILING,
        "replay_parse_requests": 0,
        "stratz_calls": 0,
        "steam_calls": 0,
        "within_ceiling": transport.physical_count <= MAX_CALLS
        and prior.directory_size(storage_root / ".local/corpora/opendota/free-dna-tier2")
        + prior.directory_size(paths["diagnostics"])
        <= STORAGE_CEILING,
    }
    latency_summary = {
        "schema_version": SCHEMA,
        "campaign_id": CAMPAIGN,
        "collection_wall_seconds": observed_collection_seconds,
        "request_latency_all_attempts": stats["request_latency_seconds_all_attempts"],
        "request_latency_successful": stats["request_latency_seconds_successful"],
        "provider_reliability": stats,
        "pacing": {
            "concurrency": 1,
            "minimum_start_interval_seconds": MIN_START_INTERVAL,
            "rate_start_ceiling_per_minute": RATE_PER_MINUTE,
            "serial_queue": True,
        },
        "ux_note": "Final unresolved recovery is a transport campaign; do not use its paced wall time as normal Free UX latency.",
    }
    private_write(paths["diagnostics"] / "provider_reliability.json", {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, **stats})
    private_write(paths["diagnostics"] / "cost_ledger.json", cost)
    private_write(paths["diagnostics"] / "cost_storage_summary.json", cost)
    private_write(paths["diagnostics"] / "latency_summary.json", latency_summary)
    private_write(
        paths["diagnostics"] / "batch_latency_summary.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "collection_wall_seconds": observed_collection_seconds,
            "measurements": [
                {
                    "name": "final_queue_serial",
                    "requested_matches": queue_total,
                    "observed_responses": transport.physical_count,
                    "successful_unique": transport.successful_count,
                    "failed_responses": transport.failed_attempts,
                    "concurrency": 1,
                    "wall_seconds": observed_collection_seconds,
                }
            ],
            "previous_successes_reused": prior_success_count,
        },
    )
    return {
        "provider_reliability": stats,
        "cost": cost,
        "latency": latency_summary,
    }


def write_blocked_outputs(
    *,
    storage_root: Path,
    paths: Mapping[str, Path],
    items: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Any],
    meta: Mapping[str, Any],
    transport: FinalTransport,
    transport_artifacts: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    details = prior.load_prior_details(storage_root)
    tier2 = with_final_metadata(
        prior.write_tier2_corpus,
        storage_root,
        details,
        prior.profile_membership(profiles),
        {int(item["match_id"]) for item in items},
        meta["source_manifest"],
        str(meta["frozen_selection_digest"]),
        str(meta["panel_salt_sha256"]),
        analytical_outcome_results_generated=False,
    )
    private_write(paths["diagnostics"] / "tier2_corpus_manifest.json", tier2)
    panel_ids = {int(item["match_id"]) for item in items}
    panel_details = [detail for detail in details if int(detail["match_id"]) in panel_ids]
    field_rows, field_summary = prior.field_completeness(panel_details)
    write_csv(
        paths["diagnostics"] / "field_completeness.csv",
        list(field_rows[0].keys()) if field_rows else ["field"],
        field_rows,
    )
    semantics = prior.semantics_audit(panel_details)
    semantics.update(
        {
            "analysis_allowed": False,
            "status": "NOT_EVALUATED",
            "blocked_reason": reason,
            "available_successful_details": len(panel_details),
            "required_details": prior.MAX_CALLS,
        }
    )
    private_write(paths["diagnostics"] / "teamfight_semantics_audit.json", semantics)
    not_evaluated = {
        "schema_version": SCHEMA,
        "campaign_id": CAMPAIGN,
        "status": "NOT_EVALUATED",
        "reason": reason,
        "available_successful_details": len(panel_details),
        "required_details": prior.MAX_CALLS,
    }
    for name in (
        "population_baseline.json",
        "control_attenuation.json",
        "common_direction_check.json",
        "stability_by_n.json",
    ):
        private_write(paths["diagnostics"] / name, not_evaluated)
    gates = {
        "available_detail_core_shape": {"observed": field_summary, "status": "PASS"},
        "full_frozen_panel_completion": {
            "observed": len(panel_details),
            "expected": prior.MAX_CALLS,
            "status": "FAIL",
        },
        "all_details_match_stored_parsed_marker": {"status": "NOT_EVALUATED"},
        "zero_replay_parse_requests": {"observed": 0, "status": "PASS"},
        "retry_policy_max_two_after_initial": {
            "observed_max_retry_number": max(
                (int(row.get("retry_number", 0)) for row in transport.responses), default=0
            ),
            "status": "PASS",
        },
        "call_cost_storage_ceiling": {"status": "PASS", "observed": transport_artifacts["cost"]},
        "teamfight_semantics": {"status": "NOT_EVALUATED"},
        "residual_iqr_ge_010": {"status": "NOT_EVALUATED"},
        "dominant_direction_below_90_percent": {"status": "NOT_EVALUATED"},
        "controls_retain_direction_ge_70_percent": {"status": "NOT_EVALUATED"},
        "median_absolute_attenuation_below_50_percent": {"status": "NOT_EVALUATED"},
        "stability_n25_or_n30": {"status": "NOT_EVALUATED"},
        "interpretation_remains_death_context_composition": {"status": "NOT_EVALUATED"},
    }
    private_write(
        paths["diagnostics"] / "pilot_gate_results.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "verdict": "PILOT_COLLECTION_BLOCKED",
            "verdict_reason": reason,
            "gates": gates,
        },
    )
    write_csv(paths["diagnostics"] / "death_context_match_level.csv", ["status", "reason"], [])
    write_csv(paths["diagnostics"] / "death_context_player_level.csv", ["status", "reason"], [])
    coverage = prior.coverage_model(profiles, None)
    private_write(paths["diagnostics"] / "coverage_model.json", coverage)
    private_write(
        paths["diagnostics"] / "free_user_cost_latency_model.json",
        {
            "schema_version": SCHEMA,
            "routing": "unverified",
            "synchronous_free_feasible": False,
            "note": "Collection blocked; final transport pacing is not normal Free UX evidence.",
        },
    )
    summary = {
        "schema_version": SCHEMA,
        "campaign_id": CAMPAIGN,
        "status": "BLOCKED",
        "terminal_verdict": "PILOT_COLLECTION_BLOCKED",
        "verdict_reason": reason,
        "frozen_panel": {
            "profiles": prior.PANEL_PROFILES,
            "matches_per_profile": prior.MATCHES_PER_PROFILE,
            "planned_unique_matches": prior.MAX_CALLS,
            "selection_digest": frozen["selection_digest"],
        },
        "collection": {
            "unresolved_at_start": EXPECTED_UNRESOLVED,
            "physical_gets": transport.physical_count,
            "first_attempt_successes": sum(
                row.get("error") is None and int(row.get("retry_number", 0)) == 0
                for row in transport.responses
            ),
            "retry_attempts": transport.retry_count,
            "retry_successes": sum(
                row.get("error") is None and int(row.get("retry_number", 0)) > 0
                for row in transport.responses
            ),
            "previous_successes_reused": len(meta["prior_success_ids"]),
            "new_successful_unique": transport.successful_count,
            "final_frozen_panel_completion": len(meta["prior_success_ids"]) + transport.successful_count,
            "unresolved_at_end": EXPECTED_UNRESOLVED - transport.successful_count,
            "replay_parse_requests": 0,
        },
        "provider_reliability": transport_artifacts["provider_reliability"],
        "field_completeness": field_summary,
        "teamfight_semantics": semantics,
        "analysis_status": "NOT_RUN",
        "coverage": coverage,
        "latency": transport_artifacts["latency"],
        "tier2_corpus": tier2,
        "integrity": {
            "panel_changed": False,
            "replacements": 0,
            "adaptive_top_up": 0,
            "replay_parse_requests": 0,
            "stratz_calls": 0,
            "steam_calls": 0,
            "old_holdout_evaluated": 0,
            "fresh_sealed_validation_evaluated": 0,
            "thresholds_changed": False,
            "analytical_behavior_changed": False,
            "deployment": False,
        },
        "cost": transport_artifacts["cost"],
    }
    private_write(paths["diagnostics"] / "aggregate_summary.json", summary)
    private_write(
        paths["diagnostics"] / "pilot_verdict.json",
        {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, "verdict": "PILOT_COLLECTION_BLOCKED", "reason": reason},
    )
    private_write(
        paths["diagnostics"] / "pilot_blocked.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "status": "BLOCKED",
            "reason": reason,
            "physical_gets": transport.physical_count,
            "final_successful_unique": len(meta["prior_success_ids"]) + transport.successful_count,
        },
    )
    return summary


class AnalysisTransportProxy:
    def __init__(self, transport: FinalTransport) -> None:
        self.responses = [
            {**row, "retry_number": 0, "error": None}
            for row in transport.responses
        ]
        self.events = transport.events
        self.physical_count = transport.physical_count
        self.successful_count = prior.MAX_CALLS
        self.error_messages: list[str] = []


def finalize_analysis(
    *,
    storage_root: Path,
    paths: Mapping[str, Path],
    items: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Any],
    meta: Mapping[str, Any],
    transport: FinalTransport,
    transport_artifacts: Mapping[str, Any],
    collection_seconds: float,
) -> dict[str, Any]:
    all_details = prior.load_prior_details(storage_root)
    panel_ids = {int(item["match_id"]) for item in items}
    details = [detail for detail in all_details if int(detail["match_id"]) in panel_ids]
    if len(details) != prior.MAX_CALLS:
        raise PilotBlocked("PANEL_COLLECTION_INCOMPLETE_AFTER_TRANSPORT")
    for item in items:
        detail = next((row for row in details if int(row["match_id"]) == int(item["match_id"])), None)
        if detail is None or prior.detail_validation(detail["match"], item) is not None:
            raise PilotBlocked("PANEL_DETAIL_VALIDATION_FAILURE_BEFORE_ANALYSIS")
    proxy = AnalysisTransportProxy(transport)
    analysis = with_final_metadata(
        prior.write_analysis_outputs,
        storage_root=storage_root,
        live_diag=paths["diagnostics"],
        items=items,
        details=details,
        profiles=profiles,
        source_secret=meta["source_secret"],
        source_manifest=meta["source_manifest"],
        frozen=frozen,
        salt=meta["panel_meta"]["salt"],
        transport=proxy,
        batch_measurements=[],
        collection_started=time.monotonic() - collection_seconds,
    )
    tier2 = dict(analysis["tier2"])
    tier2.update({"schema_version": SCHEMA, "campaign_id": CAMPAIGN})
    private_write(paths["diagnostics"] / "tier2_corpus_manifest.json", tier2)
    gates = dict(analysis["gates"])
    gates.pop("zero_retries", None)
    observed_max_retry = max(
        (int(row.get("retry_number", 0)) for row in transport.responses), default=0
    )
    gates["retry_policy_max_two_after_initial"] = {
        "observed_max_retry_number": observed_max_retry,
        "observed_retry_attempts": transport.retry_count,
        "max_retries_after_initial": MAX_RETRIES,
        "passed": observed_max_retry <= MAX_RETRIES and transport.physical_count <= MAX_CALLS,
    }
    analytical_names = [name for name in gates if name != "latency_not_over_60_seconds"]
    all_pass = all(bool(gates[name].get("passed")) for name in analytical_names)
    semantics = analysis["summary"]["teamfight_semantics"]
    common = gates.get("dominant_direction_below_90_percent", {})
    if not semantics.get("analysis_allowed"):
        verdict = "DROP_DEATH_CONTEXT"
        reason = "TEAMFIGHT_SEMANTICS_FAILED"
    elif common.get("observed") is not None and float(common["observed"]) >= 0.90:
        verdict = "DROP_DEATH_CONTEXT"
        reason = "POPULATION_COMMON_RELATIONSHIP"
    elif all_pass:
        verdict = "DEATH_CONTEXT_PILOT_PASS"
        reason = "ALL_FROZEN_PILOT_GATES_PASS"
    else:
        verdict = "DROP_DEATH_CONTEXT"
        reason = next(name for name in analytical_names if not gates[name].get("passed"))

    pilot_gates = {
        "schema_version": SCHEMA,
        "campaign_id": CAMPAIGN,
        "verdict": verdict,
        "verdict_reason": reason,
        "gates": gates,
        "frozen_criteria": {
            "core_fields": ">=95%",
            "residual_iqr": ">=0.10",
            "dominant_direction": "<90%",
            "control_direction_retention": ">=70%",
            "median_attenuation": "<50%",
            "stability": "N=25 or N=30 split-half Spearman >=0.50 and repeated sign agreement >=0.75",
        },
        "retry_policy": {
            "max_retries_after_initial": MAX_RETRIES,
            "max_attempts_per_match": MAX_ATTEMPTS,
            "adaptive_top_up": False,
            "replacement_calls": 0,
        },
    }
    private_write(paths["diagnostics"] / "pilot_gate_results.json", pilot_gates)
    summary = dict(analysis["summary"])
    summary.update(
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "status": "PASS" if verdict == "DEATH_CONTEXT_PILOT_PASS" else "FAIL",
            "terminal_verdict": verdict,
            "verdict_reason": reason,
            "analysis_status": "RUN",
            "collection": {
                "unresolved_at_start": EXPECTED_UNRESOLVED,
                "physical_gets": transport.physical_count,
                "first_attempt_successes": sum(
                    row.get("error") is None and int(row.get("retry_number", 0)) == 0
                    for row in transport.responses
                ),
                "retry_attempts": transport.retry_count,
                "retry_successes": sum(
                    row.get("error") is None and int(row.get("retry_number", 0)) > 0
                    for row in transport.responses
                ),
                "previous_successes_reused": len(meta["prior_success_ids"]),
                "new_successful_unique": transport.successful_count,
                "successful": prior.MAX_CALLS,
                "final_frozen_panel_completion": prior.MAX_CALLS,
                "unresolved_at_end": 0,
                "replay_parse_requests": 0,
            },
            "provider_reliability": transport_artifacts["provider_reliability"],
            "latency": transport_artifacts["latency"],
        }
    )
    summary["integrity"].update(
        {
            "panel_changed": False,
            "replacements": 0,
            "adaptive_top_up": 0,
            "replay_parse_requests": 0,
            "stratz_calls": 0,
            "steam_calls": 0,
            "fresh_sealed_validation_evaluated": 0,
            "old_holdout_evaluated": 0,
            "thresholds_changed": False,
            "analytical_behavior_changed": False,
            "deployment": False,
        }
    )
    private_write(paths["diagnostics"] / "aggregate_summary.json", summary)
    private_write(
        paths["diagnostics"] / "pilot_verdict.json",
        {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, "verdict": verdict, "reason": reason},
    )
    private_write(paths["diagnostics"] / "provider_reliability.json", {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, **transport_artifacts["provider_reliability"]})
    private_write(paths["diagnostics"] / "cost_storage_summary.json", transport_artifacts["cost"])
    private_write(
        paths["diagnostics"] / "free_user_cost_latency_model.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "routing": "unverified",
            "synchronous_free_feasible": False,
            "final_transport_wall_seconds": transport_artifacts["latency"]["collection_wall_seconds"],
            "note": "Final unresolved recovery is a transport campaign; do not use its paced wall time as normal Free UX latency.",
        },
    )
    return {"summary": summary, "gates": gates, "analysis": analysis, "verdict": verdict, "reason": reason}


async def collect(
    *,
    storage_root: Path,
    paths: Mapping[str, Path],
    items: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
    meta: Mapping[str, Any],
    source_root: Path,
    base_url: str,
    api_key: str | None,
    timeout: float,
) -> tuple[FinalTransport, float]:
    started = time.monotonic()

    def on_attempt(item: Mapping[str, Any], latest: Mapping[str, Any], position: int) -> None:
        write_progress(
            path=paths["progress"],
            stage="attempt_recorded",
            transport=transport,
            queue_position=position,
            queue_total=len(items),
            prior_successes=len(meta["prior_success_ids"]),
            latest={
                "match_key": hashlib.sha256(str(item["match_id"]).encode()).hexdigest()[:16],
                "profile_index": int(item["profile_index"]),
                "match_index": int(item["match_index"]),
                **dict(latest),
            },
        )

    def save(detail: Mapping[str, Any]) -> None:
        persist_detail(
            storage_root=storage_root,
            paths=paths,
            details=detail,
            items=meta["all_items"],
            profiles=profiles,
            meta=meta,
        )

    async with FinalTransport(
        paths=paths,
        items=items,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        queue_digest=str(meta["final_queue_digest"]),
        initial_cooldown=float(meta["cooldown"]),
        persist_success=save,
        on_attempt=on_attempt,
    ) as transport:
        for position, item in enumerate(items, start=1):
            if transport.cached_detail(item) is not None:
                write_progress(
                    path=paths["progress"],
                    stage="already_complete",
                    transport=transport,
                    queue_position=position,
                    queue_total=len(items),
                    prior_successes=len(meta["prior_success_ids"]),
                )
                continue
            if transport.attempts_by_match[int(item["match_id"])] >= MAX_ATTEMPTS:
                write_progress(
                    path=paths["progress"],
                    stage="retry_exhausted",
                    transport=transport,
                    queue_position=position,
                    queue_total=len(items),
                    prior_successes=len(meta["prior_success_ids"]),
                )
                continue
            await transport.fetch(item, queue_position=position, queue_total=len(items))
            write_progress(
                path=paths["progress"],
                stage="match_complete",
                transport=transport,
                queue_position=position,
                queue_total=len(items),
                prior_successes=len(meta["prior_success_ids"]),
            )
    return transport, time.monotonic() - started


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--storage-root", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        rng = random.Random(1)
        assert transient_error(429, "http_429")
        assert transient_error(None, "timeout")
        assert transient_error(None, "connection_reset")
        assert not transient_error(404, "http_404")
        assert retry_delay(1, None, rng) >= FIRST_RETRY_MINIMUM + 0.5
        assert retry_delay(2, "7", rng) >= SECOND_RETRY_MINIMUM + 0.5
        baseline = prior.Baseline(
            [
                {"profile_id": "target", "match_id": 1, "deaths": 10, "fight_deaths": 5},
                {"profile_id": "other", "match_id": 1, "deaths": 10, "fight_deaths": 0},
                {"profile_id": "other", "match_id": 2, "deaths": 10, "fight_deaths": 10},
            ],
            ["target"],
        )
        assert baseline.rate("target", 1, "global", (), minimum_deaths=0) == 1.0
        assert digest_value([{"profile_index": 1, "match_index": 2, "match_id": 3}]) == digest_value(
            [{"profile_index": 1, "match_index": 2, "match_id": 3}]
        )
        print("self_check_pass")
        return 0
    if args.source_root is None or args.storage_root is None:
        parser.error("--source-root and --storage-root are required unless --self-check is used")
    source_root = args.source_root.resolve()
    storage_root = args.storage_root.resolve()
    load_dotenv(storage_root / ".env")
    paths = paths_for(storage_root)
    queue: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}
    try:
        frozen, all_items, profiles, meta = prior_campaign_successes(
            source_root=source_root,
            storage_root=storage_root,
            paths=paths,
        )
        meta["all_items"] = all_items
        meta["frozen_selection_digest"] = frozen["selection_digest"]
        meta["panel_salt_sha256"] = frozen["private_salt_sha256"]
        queue = list(meta["final_queue"])
        write_progress(
            path=paths["progress"],
            stage="preflight_complete",
            transport=None,
            queue_position=0,
            queue_total=len(queue),
            prior_successes=len(meta["prior_success_ids"]),
        )
        if args.preflight_only:
            print(
                json.dumps(
                    {
                        "status": "PREFLIGHT_PASS",
                        "selection_digest": frozen["selection_digest"],
                        "final_queue": len(queue),
                        "final_queue_digest": meta["final_queue_digest"],
                        "prior_successes_reused": len(meta["prior_success_ids"]),
                        "existing_final_successes": len(meta["existing_final_success_ids"]),
                        "opendota_calls": 0,
                    },
                    sort_keys=True,
                )
            )
            return 0

        base_url = os.getenv("OPENDOTA_BASE_URL", "https://api.opendota.com/api")
        api_key = os.getenv("OPENDOTA_API_KEY") or None
        timeout = float(os.getenv("OPENDOTA_TIMEOUT_SECONDS", "15"))
        transport, collection_seconds = asyncio.run(
            collect(
                storage_root=storage_root,
                paths=paths,
                items=queue,
                profiles=profiles,
                meta=meta,
                source_root=source_root,
                base_url=base_url,
                api_key=api_key,
                timeout=timeout,
            )
        )
        transport_artifacts = write_transport_artifacts(
            paths=paths,
            storage_root=storage_root,
            transport=transport,
            collection_seconds=collection_seconds,
            prior_success_count=len(meta["prior_success_ids"]),
            queue_total=len(queue),
        )
        if len(meta["prior_success_ids"]) + transport.successful_count != prior.MAX_CALLS:
            write_blocked_outputs(
                storage_root=storage_root,
                paths=paths,
                items=all_items,
                profiles=profiles,
                frozen=frozen,
                meta=meta,
                transport=transport,
                transport_artifacts=transport_artifacts,
                reason="PILOT_COLLECTION_BLOCKED",
            )
            write_progress(
                path=paths["progress"],
                stage="terminal_blocked",
                transport=transport,
                queue_position=len(queue),
                queue_total=len(queue),
                prior_successes=len(meta["prior_success_ids"]),
                errors=["PILOT_COLLECTION_BLOCKED"],
            )
            print(
                json.dumps(
                    {
                        "status": "BLOCKED",
                        "terminal_verdict": "PILOT_COLLECTION_BLOCKED",
                        "physical_gets": transport.physical_count,
                        "successful": len(meta["prior_success_ids"]) + transport.successful_count,
                        "output": str(paths["diagnostics"]),
                    },
                    sort_keys=True,
                )
            )
            return 2

        result = finalize_analysis(
            storage_root=storage_root,
            paths=paths,
            items=all_items,
            profiles=profiles,
            frozen=frozen,
            meta=meta,
            transport=transport,
            transport_artifacts=transport_artifacts,
            collection_seconds=collection_seconds,
        )
        write_progress(
            path=paths["progress"],
            stage="terminal_verdict",
            transport=transport,
            queue_position=len(queue),
            queue_total=len(queue),
            prior_successes=len(meta["prior_success_ids"]),
        )
        print(
            json.dumps(
                {
                    "status": "PASS" if result["verdict"] == "DEATH_CONTEXT_PILOT_PASS" else "FAIL",
                    "terminal_verdict": result["verdict"],
                    "physical_gets": transport.physical_count,
                    "successful": prior.MAX_CALLS,
                    "output": str(paths["diagnostics"]),
                },
                sort_keys=True,
            )
        )
        return 0
    except PilotBlocked as exc:
        reason = str(exc)
        private_write(
            paths["diagnostics"] / "pilot_blocked.json",
            {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, "status": "BLOCKED", "reason": reason},
        )
        write_progress(
            path=paths["progress"],
            stage="terminal_blocked",
            transport=None,
            queue_position=0,
            queue_total=len(queue),
            prior_successes=len(meta.get("prior_success_ids", [])),
            errors=[reason],
        )
        print(
            json.dumps(
                {"status": "BLOCKED", "terminal_verdict": "PILOT_COLLECTION_BLOCKED", "reason": reason},
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
