#!/usr/bin/env python3
"""Continue the frozen Death Context OpenDota detail campaign.

Only the 901 missing IDs from the prior frozen panel are eligible for GETs.
The prior 59 validated details are reused from the canonical Tier-2 corpus.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import free_dna_death_context_overnight as prior  # noqa: E402, I001


SCHEMA = "free-dna-death-context-continuation-1.0.0"
CAMPAIGN = "free-dna-death-context-tier2-continuation-2026-08-29"
PRIOR_CAMPAIGN = "free-dna-death-context-tier2-pilot-2026-08-28"
PRIOR_LIVE = "free-dna-death-context-live-pilot"
DIAGNOSTIC_NAME = "free-dna-death-context-continuation"
PROVIDER = "OpenDota"
SOURCE_MARKER = "22"
MAX_NEW_GETS = 960
MAX_RETRIES = 2
MAX_ATTEMPTS = MAX_RETRIES + 1
DEFAULT_CONCURRENCY = 5
RATE_PER_MINUTE = 240
COST_IDR_PER_100 = 200.0
COST_USD_PER_100 = 0.01
STORAGE_CEILING = 384 * 1024 * 1024
EXPECTED_PRIOR_SUCCESSES = 59
EXPECTED_PRIOR_ATTEMPTS = 60
EXPECTED_MISSING = 901
EXPECTED_PRIOR_SELECTION_DIGEST = "9855c1535a0e27223e62cb21fb686bdb1ca5acd169fd4d8220b05760c7e3da92"
TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class PilotBlocked(RuntimeError):
    """Stop without expanding the frozen panel or retry policy."""


def private_write(path: Path, value: Any, *, mode: int = 0o600) -> None:
    prior.private_write(path, value, mode=mode)


def append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    prior.append_jsonl(path, value)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return prior.read_jsonl(path)


def read_json(path: Path) -> Any:
    return prior.read_json(path)


def digest_value(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def now_iso() -> str:
    return prior.now_iso()


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    prior.write_csv(path, fieldnames, rows)


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


def panel_rows(frozen: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "profile_id": str(row["profile_id"]),
            "selected_match_ids": [int(value) for value in row["selected_match_ids"]],
        }
        for row in frozen.get("profiles", [])
    ]


def prior_panel_and_queue(
    *, source_root: Path, storage_root: Path, paths: Mapping[str, Path]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    prior_live = storage_root / ".local/diagnostics" / PRIOR_LIVE
    prior_manifest_path = prior_live / "frozen_panel_manifest.json"
    prior_ledger_path = prior_live / "request_ledger.jsonl"
    if not prior_manifest_path.is_file() or not prior_ledger_path.is_file():
        raise PilotBlocked("PRIOR_COLLECTION_ARTIFACTS_MISSING")

    frozen, items, profiles, panel_meta = prior.frozen_panel(source_root, storage_root)
    prior_frozen = read_json(prior_manifest_path)
    if prior_frozen.get("selection_digest") != EXPECTED_PRIOR_SELECTION_DIGEST:
        raise PilotBlocked("PRIOR_PANEL_SELECTION_DIGEST_MISMATCH")
    if frozen.get("selection_digest") != EXPECTED_PRIOR_SELECTION_DIGEST:
        raise PilotBlocked("RECOMPUTED_PANEL_SELECTION_DIGEST_MISMATCH")
    if panel_rows(frozen) != panel_rows(prior_frozen):
        raise PilotBlocked("PRIOR_PANEL_SELECTION_ROWS_MISMATCH")
    if frozen.get("match_selection_digest") != prior_frozen.get("match_selection_digest"):
        raise PilotBlocked("PRIOR_PANEL_MATCH_DIGEST_MISMATCH")
    if len(items) != prior.MAX_CALLS:
        raise PilotBlocked("PRIOR_PANEL_NOT_960_UNIQUE_MATCHES")

    item_by_id = {int(item["match_id"]): item for item in items}
    events = read_jsonl(prior_ledger_path)
    responses = [event for event in events if event.get("event") == "response_recorded"]
    validations = {
        str(event.get("request_id")): event
        for event in events
        if event.get("event") == "validation"
    }
    if len(responses) != EXPECTED_PRIOR_ATTEMPTS:
        raise PilotBlocked("PRIOR_ATTEMPT_COUNT_MISMATCH")
    successful = [event for event in responses if event.get("error") is None]
    failed = [event for event in responses if event.get("error") is not None]
    if len(successful) != EXPECTED_PRIOR_SUCCESSES or len(failed) != 1:
        raise PilotBlocked("PRIOR_SUCCESS_FAILURE_COUNT_MISMATCH")
    failed_row = failed[0]
    if failed_row.get("error") != "http_500" or failed_row.get("http_status") != 500:
        raise PilotBlocked("PRIOR_FAILURE_NOT_EXPECTED_HTTP_500")
    success_ids = {int(event["match_id"]) for event in successful}
    if len(success_ids) != EXPECTED_PRIOR_SUCCESSES or not success_ids.issubset(item_by_id):
        raise PilotBlocked("PRIOR_SUCCESS_NOT_BOUND_TO_FROZEN_PANEL")
    if int(failed_row["match_id"]) in success_ids or int(failed_row["match_id"]) not in item_by_id:
        raise PilotBlocked("PRIOR_FAILED_MATCH_BINDING_MISMATCH")

    for event in successful:
        raw_path = Path(str(event.get("raw_path")))
        request_id = str(event.get("request_id"))
        validation = validations.get(request_id)
        if not raw_path.is_file() or prior.sha256_file(raw_path) != event.get("response_sha256"):
            raise PilotBlocked("PRIOR_SUCCESS_RAW_DIGEST_FAILURE")
        if validation is None or validation.get("error") is not None:
            raise PilotBlocked("PRIOR_SUCCESS_VALIDATION_FAILURE")

    failed_id = int(failed_row["match_id"])
    queue = [
        {
            **item,
            "prior_status": "prior_http_500" if int(item["match_id"]) == failed_id else "never_attempted",
        }
        for item in items
        if int(item["match_id"]) not in success_ids
    ]
    if len(queue) != EXPECTED_MISSING or int(queue[0]["match_id"]) != failed_id:
        raise PilotBlocked("CONTINUATION_QUEUE_NOT_901_OR_PRIOR_FAILURE_FIRST")
    if sum(item["prior_status"] == "never_attempted" for item in queue) != 900:
        raise PilotBlocked("CONTINUATION_NEVER_ATTEMPTED_COUNT_MISMATCH")

    queue_digest = digest_value(
        [
            {
                "profile_index": int(item["profile_index"]),
                "match_index": int(item["match_index"]),
                "match_id": int(item["match_id"]),
                "prior_status": item["prior_status"],
            }
            for item in queue
        ]
    )
    private_write(
        paths["diagnostics"] / "frozen_panel_manifest.json",
        {
            **prior_frozen,
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "prior_campaign_id": prior_frozen.get("campaign_id", PRIOR_CAMPAIGN),
            "selection_digest_verified": True,
            "continuation_queue_digest": queue_digest,
            "continuation_started_at": now_iso(),
        },
    )
    private_write(
        paths["diagnostics"] / "continuation_queue.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "prior_campaign_id": PRIOR_CAMPAIGN,
            "queue_digest": queue_digest,
            "selection_digest": frozen["selection_digest"],
            "count": len(queue),
            "items": [
                {
                    "profile_id": str(item["profile_id"]),
                    "profile_index": int(item["profile_index"]),
                    "match_index": int(item["match_index"]),
                    "match_id": int(item["match_id"]),
                    "prior_status": item["prior_status"],
                }
                for item in queue
            ],
        },
    )
    source_raw, source_normalized, source_secret = prior.source_manifests(source_root)
    meta = {
        "source_secret": source_secret,
        "source_manifest": {**source_raw, **source_normalized},
        "panel_meta": panel_meta,
        "prior_events": events,
        "prior_success_ids": success_ids,
        "prior_failed_id": failed_id,
        "queue_digest": queue_digest,
    }
    private_write(
        paths["diagnostics"] / "preflight.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "prior_campaign_id": PRIOR_CAMPAIGN,
            "branch_sha": prior.git_sha(),
            "base_sha": prior.BASE_SHA,
            "provider": PROVIDER,
            "panel": {
                "profiles": prior.PANEL_PROFILES,
                "matches_per_profile": prior.MATCHES_PER_PROFILE,
                "unique_match_ids": prior.MAX_CALLS,
                "selection_digest": frozen["selection_digest"],
                "match_selection_digest": frozen["match_selection_digest"],
            },
            "prior_collection": {
                "attempts": len(responses),
                "successful_unique": len(success_ids),
                "http_500_match_count": 1,
                "never_attempted_count": 900,
                "reused_without_get": len(success_ids),
            },
            "continuation_authorization": {
                "max_new_physical_gets_including_retries": MAX_NEW_GETS,
                "max_retries_after_initial": MAX_RETRIES,
                "max_attempts_per_match": MAX_ATTEMPTS,
                "concurrency": DEFAULT_CONCURRENCY,
                "rate_start_ceiling_per_minute": RATE_PER_MINUTE,
                "max_cost_idr": MAX_NEW_GETS * COST_IDR_PER_100 / 100,
                "max_cost_usd": MAX_NEW_GETS * COST_USD_PER_100 / 100,
                "replay_parse_requests": 0,
                "stratz_calls": 0,
                "steam_calls": 0,
                "fresh_sealed_validation": False,
                "old_holdout": False,
            },
            "provider_key_configured": bool(os.getenv("OPENDOTA_API_KEY")),
            "queue": {
                "count": len(queue),
                "prior_http_500_first": True,
                "never_attempted": 900,
                "digest": queue_digest,
            },
            "frozen_panel_reused_without_reselection": True,
        },
    )
    return frozen, items, profiles, meta


def progress(
    path: Path,
    *,
    stage: str,
    transport: ContinuationTransport | None,
    queue_position: int,
    queue_total: int,
    prior_successes: int,
    next_action: str,
    errors: Sequence[str] = (),
) -> None:
    physical = transport.physical_count if transport else 0
    new_successes = transport.successful_count if transport else 0
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
            "remaining_budget": max(0, MAX_NEW_GETS - physical),
            "previous_successes_reused": prior_successes,
            "new_successful_unique": new_successes,
            "final_successful_unique": prior_successes + new_successes,
            "transient_failures": transport.transient_failures if transport else 0,
            "permanent_failures": transport.permanent_failures if transport else 0,
            "retry_count": transport.retry_count if transport else 0,
            "errors": list(errors),
            "next_action": next_action,
        },
    )


def transient_error(status: int | None, error: str | None) -> bool:
    if status in TRANSIENT_STATUSES:
        return True
    return error in {"timeout", "network_error", "connection_reset", "dns_error"}


def classify_status(status: int | None) -> str:
    if status == 429:
        return "http_429"
    if status in {500, 502, 503, 504}:
        return f"http_{status}"
    if status is None:
        return "network_error"
    return f"http_{status}"


def retry_delay(retry_number: int, retry_after: str | None, rng: random.Random) -> float:
    if retry_after:
        try:
            value = float(retry_after)
        except ValueError:
            value = -1
        if value >= 0:
            return min(value, 60.0)
    low, high = ((2.0, 5.0), (8.0, 15.0))[max(0, retry_number - 1)]
    return rng.uniform(low, high)


class ContinuationTransport:
    def __init__(
        self,
        *,
        paths: Mapping[str, Path],
        items: Sequence[Mapping[str, Any]],
        base_url: str,
        api_key: str | None,
        timeout: float,
        queue_digest: str,
    ) -> None:
        self.paths = paths
        self.item_by_id = {int(item["match_id"]): dict(item) for item in items}
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=DEFAULT_CONCURRENCY, max_keepalive_connections=DEFAULT_CONCURRENCY),
        )
        self.ledger_path = paths["ledger"]
        self.retry_ledger_path = paths["retry_ledger"]
        self.events = read_jsonl(self.ledger_path)
        self.responses = [event for event in self.events if event.get("event") == "response_recorded"]
        self.validations = {
            str(event.get("request_id")): event
            for event in self.events
            if event.get("event") == "validation"
        }
        self.completed_by_match: dict[int, dict[str, Any]] = {}
        self.error_by_match: dict[int, str] = {}
        self.attempts_by_match: Counter[int] = Counter()
        self.error_messages: list[str] = []
        self.transient_failures = 0
        self.permanent_failures = 0
        self.retry_count = sum(int(row.get("retry_number", 0)) for row in self.responses)
        self.seen_429 = False
        self.ceiling_hit = False
        self.state_lock = asyncio.Lock()
        self.rate_gate = prior.RateGate(RATE_PER_MINUTE)
        self.next_ordinal = len(self.responses)
        self.rng = random.Random(int(queue_digest[:16], 16))
        self._check_resume_state()

    async def __aenter__(self) -> ContinuationTransport:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.http.aclose()

    @property
    def physical_count(self) -> int:
        return len(self.responses)

    @property
    def successful_count(self) -> int:
        return len(self.completed_by_match)

    def _check_resume_state(self) -> None:
        markers = list(self.paths["diagnostics"].glob(".inflight-*.json"))
        if markers:
            raise PilotBlocked("INDETERMINATE_INTERRUPTED_REQUEST")
        starts = {
            str(event.get("request_id"))
            for event in self.events
            if event.get("event") == "request_started"
        }
        response_ids = {str(event.get("request_id")) for event in self.responses}
        if starts != response_ids or len(starts) != len(self.events_for("request_started")):
            raise PilotBlocked("CONTINUATION_LEDGER_START_RESPONSE_MISMATCH")
        seen_success: set[int] = set()
        for response in self.responses:
            match_id = response.get("match_id")
            if not isinstance(match_id, int) or match_id not in self.item_by_id:
                raise PilotBlocked("CONTINUATION_RESPONSE_NOT_IN_QUEUE_PANEL")
            self.attempts_by_match[match_id] += 1
            if int(response.get("retry_number", -1)) >= MAX_ATTEMPTS:
                raise PilotBlocked("CONTINUATION_RETRY_LIMIT_EXCEEDED")
            if response.get("error") is None:
                request_id = str(response.get("request_id"))
                validation = self.validations.get(request_id)
                raw_path = Path(str(response.get("raw_path")))
                if (
                    match_id in seen_success
                    or not raw_path.is_file()
                    or prior.sha256_file(raw_path) != response.get("response_sha256")
                    or validation is None
                    or validation.get("error") is not None
                ):
                    raise PilotBlocked("CONTINUATION_SUCCESS_DIGEST_OR_VALIDATION_FAILURE")
                seen_success.add(match_id)
                self.completed_by_match[match_id] = response
            else:
                self.error_by_match[match_id] = str(response.get("error"))
                self._count_failure(response)
        self.error_messages = [
            f"match_{match_id}:{error}"
            for match_id, error in sorted(self.error_by_match.items())
            if match_id not in self.completed_by_match
        ]

    def events_for(self, name: str) -> list[dict[str, Any]]:
        return [event for event in self.events if event.get("event") == name]

    def _count_failure(self, response: Mapping[str, Any]) -> None:
        status = response.get("http_status")
        error = str(response.get("error")) if response.get("error") is not None else None
        if transient_error(status if isinstance(status, int) else None, error):
            self.transient_failures += 1
            if status == 429:
                self.seen_429 = True
        else:
            self.permanent_failures += 1

    def cached_detail(self, item: Mapping[str, Any]) -> dict[str, Any] | None:
        response = self.completed_by_match.get(int(item["match_id"]))
        if response is None:
            return None
        raw_path = Path(str(response["raw_path"]))
        try:
            value = json.loads(raw_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PilotBlocked(f"CONTINUATION_CACHED_RESPONSE_READ_FAILURE:{type(exc).__name__}") from exc
        return self.detail_record(item, value, response)

    def detail_record(
        self, item: Mapping[str, Any], value: Any, response: Mapping[str, Any]
    ) -> dict[str, Any]:
        path = Path(str(response["raw_path"]))
        return {
            "match_id": int(item["match_id"]),
            "path": path,
            "response_sha256": str(response["response_sha256"]),
            "bytes": int(response["response_bytes"]),
            "ledger": dict(response),
            "match": value,
            "shape": prior.detail_shape(value),
            "panel_profile_id": str(item["profile_id"]),
        }

    async def reserve(self, item: Mapping[str, Any], *, concurrency: int, batch_id: str, retry_number: int) -> tuple[int, Path, dict[str, Any]]:
        async with self.state_lock:
            if self.next_ordinal >= MAX_NEW_GETS:
                self.ceiling_hit = True
                raise PilotBlocked("REQUEST_CEILING_REACHED")
            ordinal = self.next_ordinal
            self.next_ordinal += 1
            match_id = int(item["match_id"])
            marker = self.paths["diagnostics"] / f".inflight-{ordinal:04d}-{match_id}-{retry_number}.json"
            private_write(
                marker,
                {
                    "schema_version": SCHEMA,
                    "campaign_id": CAMPAIGN,
                    "match_id": match_id,
                    "ordinal": ordinal,
                    "retry_number": retry_number,
                },
            )
            await self.rate_gate.wait_for_slot()
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
                "concurrency": concurrency,
                "batch_id": batch_id,
                "retry_number": retry_number,
                "retry_limit": MAX_RETRIES,
                "requested_at": now_iso(),
            }
            append_jsonl(self.ledger_path, started)
            self.events.append(started)
            return ordinal, marker, started

    async def fetch(
        self, item: Mapping[str, Any], *, concurrency: int, batch_id: str
    ) -> dict[str, Any] | None:
        match_id = int(item["match_id"])
        cached = self.cached_detail(item)
        if cached is not None:
            return cached
        retry_number = self.attempts_by_match[match_id]
        while retry_number < MAX_ATTEMPTS:
            try:
                ordinal, marker, started = await self.reserve(
                    item, concurrency=concurrency, batch_id=batch_id, retry_number=retry_number
                )
            except PilotBlocked:
                self.ceiling_hit = True
                return None
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
            except httpx.NetworkError:
                error = "network_error"
            except httpx.HTTPError:
                error = "http_error"
            elapsed = time.monotonic() - started_monotonic
            raw_path: Path | None = None
            if body:
                if (
                    prior.directory_size(self.paths["corpus"])
                    + prior.directory_size(self.paths["diagnostics"])
                    + len(body)
                    > STORAGE_CEILING
                ):
                    error = "storage_ceiling_risk"
                else:
                    raw_path = self.paths["raw_responses"] / (
                        f"response-continuation-{ordinal:04d}-{match_id}-attempt-{retry_number}.body"
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
                "concurrency": concurrency,
                "batch_id": batch_id,
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
            append_jsonl(self.ledger_path, response_event)
            self.events.append(response_event)
            self.responses.append(response_event)
            if retry_number > 0:
                self.retry_count += 1
            self.attempts_by_match[match_id] += 1
            marker.unlink(missing_ok=True)
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
                append_jsonl(self.ledger_path, validation)
                self.events.append(validation)
                self.validations[started["request_id"]] = validation
            if response_error is not None:
                self.error_by_match[match_id] = response_error
                self._count_failure(response_event)
                if error is not None and transient_error(status, error) and retry_number < MAX_RETRIES:
                    next_retry = retry_number + 1
                    delay = retry_delay(next_retry, retry_after, self.rng)
                    append_jsonl(
                        self.retry_ledger_path,
                        {
                            "event": "retry_scheduled",
                            "schema_version": SCHEMA,
                            "campaign_id": CAMPAIGN,
                            "match_id": match_id,
                            "request_id": started["request_id"],
                            "retry_number": next_retry,
                            "reason": response_error,
                            "http_status": status,
                            "retry_after_seconds": retry_after,
                            "backoff_seconds": delay,
                            "scheduled_at": now_iso(),
                        },
                    )
                    await asyncio.sleep(delay)
                    retry_number = next_retry
                    continue
                return None
            self.completed_by_match[match_id] = response_event
            if retry_number > 0:
                append_jsonl(
                    self.retry_ledger_path,
                    {
                        "event": "retry_succeeded",
                        "schema_version": SCHEMA,
                        "campaign_id": CAMPAIGN,
                        "match_id": match_id,
                        "retry_number": retry_number,
                        "completed_at": now_iso(),
                    },
                )
            return self.detail_record(item, value, response_event)
        return None


def prior_success_details(
    *, storage_root: Path, items: Sequence[Mapping[str, Any]], prior_events: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    responses = {
        int(event["match_id"]): event
        for event in prior_events
        if event.get("event") == "response_recorded" and event.get("error") is None
    }
    details: list[dict[str, Any]] = []
    for item in items:
        response = responses.get(int(item["match_id"]))
        if response is None:
            continue
        raw_path = Path(str(response["raw_path"]))
        value = read_json(raw_path)
        error = prior.detail_validation(value, item)
        if error is not None:
            raise PilotBlocked(f"PRIOR_REUSED_DETAIL_VALIDATION_FAILURE:{error}")
        details.append(
            {
                "match_id": int(item["match_id"]),
                "path": raw_path,
                "response_sha256": str(response["response_sha256"]),
                "bytes": int(response["response_bytes"]),
                "ledger": dict(response),
                "match": value,
                "shape": prior.detail_shape(value),
                "panel_profile_id": str(item["profile_id"]),
            }
        )
    if len(details) != EXPECTED_PRIOR_SUCCESSES:
        raise PilotBlocked("PRIOR_REUSED_DETAIL_COUNT_MISMATCH")
    return details


def provider_stats(transport: ContinuationTransport) -> dict[str, Any]:
    responses = transport.responses
    latency = [
        float(row["latency_seconds"])
        for row in responses
        if row.get("latency_seconds") is not None
    ]
    retries = [row for row in responses if int(row.get("retry_number", 0)) > 0]
    retry_successes = sum(row.get("error") is None for row in retries)
    status_counts = Counter(row.get("http_status") for row in responses)
    return {
        "physical_calls": len(responses),
        "http_429": status_counts.get(429, 0),
        "http_5xx": sum(status_counts.get(code, 0) for code in (500, 502, 503, 504)),
        "timeouts": sum(row.get("error") == "timeout" for row in responses),
        "network_errors": sum(row.get("error") == "network_error" for row in responses),
        "transient_failure_attempts": transport.transient_failures,
        "permanent_failure_attempts": transport.permanent_failures,
        "retry_attempts": len(retries),
        "retry_successes": retry_successes,
        "retry_success_rate": retry_successes / len(retries) if retries else None,
        "request_latency_seconds": prior.numeric_stats(latency),
        "status_counts": {str(key): value for key, value in sorted(status_counts.items(), key=lambda row: str(row[0]))},
    }


def retry_rows(paths: Mapping[str, Path]) -> list[dict[str, Any]]:
    rows = read_jsonl(paths["retry_ledger"])
    return [
        {
            "event": row.get("event"),
            "match_id": row.get("match_id"),
            "retry_number": row.get("retry_number"),
            "reason": row.get("reason"),
            "http_status": row.get("http_status"),
            "retry_after_seconds": row.get("retry_after_seconds"),
            "backoff_seconds": row.get("backoff_seconds"),
            "scheduled_at": row.get("scheduled_at", row.get("completed_at")),
        }
        for row in rows
    ]


def continuation_metadata(value: Any) -> Any:
    if isinstance(value, list):
        return [continuation_metadata(item) for item in value]
    if isinstance(value, dict):
        return {
            key: SCHEMA
            if key == "schema_version"
            else CAMPAIGN
            if key == "campaign_id"
            else continuation_metadata(item)
            for key, item in value.items()
        }
    return value


def write_collection_artifacts(
    *,
    paths: Mapping[str, Path],
    storage_root: Path,
    transport: ContinuationTransport,
    batch_measurements: Sequence[Mapping[str, Any]],
    collection_seconds: float,
    prior_success_count: int,
    queue_digest: str,
) -> dict[str, Any]:
    write_csv(
        paths["diagnostics"] / "request_ledger.csv",
        [
            "campaign_id",
            "request_id",
            "ordinal",
            "profile_id",
            "profile_index",
            "match_index",
            "match_id",
            "method",
            "endpoint",
            "concurrency",
            "batch_id",
            "requested_at",
            "completed_at",
            "latency_seconds",
            "http_status",
            "response_bytes",
            "response_sha256",
            "raw_path",
            "retry_number",
            "retry_limit",
            "error",
        ],
        [
            {
                **row,
                "requested_at": next(
                    (
                        event.get("requested_at")
                        for event in transport.events
                        if event.get("event") == "request_started"
                        and event.get("request_id") == row.get("request_id")
                    ),
                    None,
                ),
            }
            for row in sorted(transport.responses, key=lambda value: int(value["ordinal"]))
        ],
    )
    failures = [row for row in transport.responses if row.get("error") is not None]
    private_write(
        paths["diagnostics"] / "request_failure_ledger.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "failures": failures,
            "failure_count": len(failures),
        },
    )
    write_csv(
        paths["diagnostics"] / "retry_ledger.csv",
        [
            "event",
            "match_id",
            "retry_number",
            "reason",
            "http_status",
            "retry_after_seconds",
            "backoff_seconds",
            "scheduled_at",
        ],
        retry_rows(paths),
    )
    stats = provider_stats(transport)
    private_write(paths["diagnostics"] / "provider_reliability.json", {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, **stats})
    private_write(
        paths["diagnostics"] / "batch_latency_summary.json",
        {
            "schema_version": SCHEMA,
            "campaign_id": CAMPAIGN,
            "measurements": list(batch_measurements),
            "collection_wall_seconds": collection_seconds,
            "concurrency_modes": sorted({row.get("concurrency") for row in transport.responses}),
            "initial_concurrency": DEFAULT_CONCURRENCY,
            "rate_start_ceiling_per_minute": RATE_PER_MINUTE,
            "concurrency_adjustments": "reduced to 1 after HTTP 429" if transport.seen_429 else [],
        },
    )
    storage_bytes = prior.directory_size(storage_root / ".local/corpora/opendota/free-dna-tier2") + prior.directory_size(paths["diagnostics"])
    cost = {
        "schema_version": SCHEMA,
        "campaign_id": CAMPAIGN,
        "physical_gets": transport.physical_count,
        "previous_successes_reused": prior_success_count,
        "new_successful_unique": transport.successful_count,
        "final_successful_unique": prior_success_count + transport.successful_count,
        "failed_attempts": len(failures),
        "retries": transport.retry_count,
        "max_physical_gets": MAX_NEW_GETS,
        "estimated_cost_idr": transport.physical_count * COST_IDR_PER_100 / 100,
        "estimated_cost_usd": transport.physical_count * COST_USD_PER_100 / 100,
        "cost_ceiling_idr": MAX_NEW_GETS * COST_IDR_PER_100 / 100,
        "cost_ceiling_usd": MAX_NEW_GETS * COST_USD_PER_100 / 100,
        "storage_bytes": storage_bytes,
        "storage_mib": storage_bytes / (1024 * 1024),
        "storage_ceiling_bytes": STORAGE_CEILING,
        "within_ceiling": transport.physical_count <= MAX_NEW_GETS and storage_bytes <= STORAGE_CEILING,
        "replay_parse_requests": 0,
        "stratz_calls": 0,
        "steam_calls": 0,
        "queue_digest": queue_digest,
    }
    private_write(paths["diagnostics"] / "cost_ledger.json", cost)
    private_write(paths["diagnostics"] / "cost_storage_summary.json", cost)
    return cost


async def run_group(
    transport: ContinuationTransport,
    group: Sequence[Mapping[str, Any]],
    *,
    concurrency: int,
    batch_id: str,
) -> tuple[list[dict[str, Any]], float]:
    started = time.monotonic()
    semaphore = asyncio.Semaphore(concurrency)

    async def one(item: Mapping[str, Any]) -> dict[str, Any] | None:
        async with semaphore:
            return await transport.fetch(item, concurrency=concurrency, batch_id=batch_id)

    results = await asyncio.gather(*(one(item) for item in group))
    return [result for result in results if result is not None], time.monotonic() - started


async def collect(
    *,
    storage_root: Path,
    paths: Mapping[str, Path],
    items: Sequence[Mapping[str, Any]],
    queue: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
    meta: Mapping[str, Any],
) -> tuple[ContinuationTransport, list[dict[str, Any]], list[dict[str, Any]], float]:
    load_dotenv()
    base_url = os.getenv("OPENDOTA_BASE_URL", "https://api.opendota.com/api")
    api_key = os.getenv("OPENDOTA_API_KEY") or None
    timeout = float(os.getenv("OPENDOTA_TIMEOUT_SECONDS", "15"))
    existing_batch = read_json(paths["diagnostics"] / "batch_latency_summary.json") if (paths["diagnostics"] / "batch_latency_summary.json").exists() else {}
    measurements: list[dict[str, Any]] = list(existing_batch.get("measurements", []))
    collection_started = time.monotonic()
    new_details: dict[int, dict[str, Any]] = {}
    async with ContinuationTransport(
        paths=paths,
        items=queue,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        queue_digest=str(meta["queue_digest"]),
    ) as transport:
        for item in queue:
            cached = transport.cached_detail(item)
            if cached is not None:
                new_details[int(item["match_id"])] = cached

        def final_successes() -> int:
            return len(meta["prior_success_ids"]) + len(new_details)

        def profile_completed() -> int:
            selected: dict[int, set[int]] = {}
            complete = set(meta["prior_success_ids"]) | set(new_details)
            for item in items:
                selected.setdefault(int(item["profile_index"]), set()).add(int(item["match_id"]))
            return sum(panel.issubset(complete) for panel in selected.values())

        progress(
            paths["progress"],
            stage="collection_ready",
            transport=transport,
            queue_position=0,
            queue_total=len(queue),
            prior_successes=len(meta["prior_success_ids"]),
            next_action="request_prior_http_500_match_first",
            errors=transport.error_messages,
        )
        ordered_queue = [
            item
            for item in queue
            if transport.cached_detail(item) is None
            and transport.attempts_by_match[int(item["match_id"])] < MAX_ATTEMPTS
        ]
        current_concurrency = DEFAULT_CONCURRENCY
        queue_position = 0
        if ordered_queue and int(ordered_queue[0]["match_id"]) == int(meta["prior_failed_id"]):
            item = ordered_queue.pop(0)
            before = transport.physical_count
            results, wall = await run_group(
                transport, [item], concurrency=1, batch_id="prior_http500_first_retry"
            )
            queue_position += 1
            new_details.update({int(row["match_id"]): row for row in results})
            measurements.append(
                {
                    "name": "prior_http500_first_retry",
                    "profile_index": int(item["profile_index"]),
                    "requested_matches": 1,
                    "observed_responses": transport.physical_count - before,
                    "failed_responses": sum(
                        row.get("error") is not None
                        for row in transport.responses
                        if int(row["ordinal"]) >= before
                    ),
                    "concurrency": 1,
                    "wall_seconds": wall,
                }
            )
            progress(
                paths["progress"],
                stage="prior_http500_retried",
                transport=transport,
                queue_position=queue_position,
                queue_total=len(queue),
                prior_successes=len(meta["prior_success_ids"]),
                next_action="continue_deterministic_missing_queue",
                errors=transport.error_messages,
            )

        groups: list[list[Mapping[str, Any]]] = []
        for item in ordered_queue:
            if not groups or int(groups[-1][0]["profile_index"]) != int(item["profile_index"]):
                groups.append([])
            groups[-1].append(item)
        for group in groups:
            if transport.ceiling_hit:
                break
            group_start = time.monotonic()
            before = transport.physical_count
            results, wall = await run_group(
                transport,
                group,
                concurrency=current_concurrency,
                batch_id=f"profile_{int(group[0]['profile_index'])}_continuation_c{current_concurrency}",
            )
            new_details.update({int(row["match_id"]): row for row in results})
            queue_position += len(group)
            observed = transport.responses[before:]
            profile_index = int(group[0]["profile_index"])
            measurements.append(
                {
                    "name": f"profile_{profile_index}_30" if len(group) == prior.MATCHES_PER_PROFILE else f"profile_{profile_index}_missing_{len(group)}",
                    "profile_index": profile_index,
                    "requested_matches": len(group),
                    "observed_responses": len(observed),
                    "successful_unique": len(results),
                    "failed_responses": sum(row.get("error") is not None for row in observed),
                    "concurrency": current_concurrency,
                    "wall_seconds": wall,
                    "group_started_monotonic": group_start,
                }
            )
            if transport.seen_429 and current_concurrency != 1:
                current_concurrency = 1
            progress(
                paths["progress"],
                stage=f"profile_{profile_index}_complete" if len(results) == len(group) else f"profile_{profile_index}_partial",
                transport=transport,
                queue_position=queue_position,
                queue_total=len(queue),
                prior_successes=len(meta["prior_success_ids"]),
                next_action="continue_deterministic_missing_queue",
                errors=transport.error_messages,
            )

        collection_seconds = (
            float(existing_batch["collection_wall_seconds"])
            if not ordered_queue and isinstance(existing_batch.get("collection_wall_seconds"), (int, float))
            else time.monotonic() - collection_started
        )
        write_collection_artifacts(
            paths=paths,
            storage_root=storage_root,
            transport=transport,
            batch_measurements=measurements,
            collection_seconds=collection_seconds,
            prior_success_count=len(meta["prior_success_ids"]),
            queue_digest=str(meta["queue_digest"]),
        )
        private_write(
            paths["diagnostics"] / "collection_summary.json",
            {
                "schema_version": SCHEMA,
                "campaign_id": CAMPAIGN,
                "queue_total": len(queue),
                "queue_processed": queue_position,
                "previous_successes_reused": len(meta["prior_success_ids"]),
                "new_successful_unique": len(new_details),
                "final_successful_unique": final_successes(),
                "profiles_completed": profile_completed(),
                "physical_calls": transport.physical_count,
                "retry_count": transport.retry_count,
                "collection_wall_seconds": collection_seconds,
                "complete": final_successes() == prior.MAX_CALLS and not transport.error_messages,
            },
        )
        return transport, list(new_details.values()), measurements, collection_seconds


def with_continuation_metadata(function: Any, *args: Any, **kwargs: Any) -> Any:
    old_schema = prior.LIVE_SCHEMA
    old_campaign = prior.LIVE_CAMPAIGN
    prior.LIVE_SCHEMA = SCHEMA
    prior.LIVE_CAMPAIGN = CAMPAIGN
    try:
        return function(*args, **kwargs)
    finally:
        prior.LIVE_SCHEMA = old_schema
        prior.LIVE_CAMPAIGN = old_campaign


class AnalysisTransportProxy:
    def __init__(self, transport: ContinuationTransport, *, total_successes: int, errors: Sequence[str]) -> None:
        self.responses = transport.responses
        self.events = transport.events
        self.physical_count = transport.physical_count
        self.successful_count = total_successes
        self.error_messages = list(errors)


def write_blocked_outputs(
    *,
    storage_root: Path,
    paths: Mapping[str, Path],
    items: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Any],
    meta: Mapping[str, Any],
    transport: ContinuationTransport,
    new_details: Sequence[Mapping[str, Any]],
    measurements: Sequence[Mapping[str, Any]],
    collection_seconds: float,
    reason: str,
) -> dict[str, Any]:
    prior_details = prior.load_prior_details(storage_root)
    all_details = [*prior_details, *new_details]
    tier2 = with_continuation_metadata(
        prior.write_tier2_corpus,
        storage_root,
        all_details,
        prior.profile_membership(profiles),
        {int(item["match_id"]) for item in items},
        meta["source_manifest"],
        str(frozen["selection_digest"]),
        str(frozen["private_salt_sha256"]),
        analytical_outcome_results_generated=False,
    )
    tier2.update({"schema_version": SCHEMA, "campaign_id": CAMPAIGN})
    details = [
        detail
        for detail in all_details
        if int(detail["match_id"]) in {int(item["match_id"]) for item in items}
    ]
    field_rows, field_summary = prior.field_completeness(details)
    private_write(paths["diagnostics"] / "tier2_corpus_manifest.json", tier2)
    write_csv(paths["diagnostics"] / "field_completeness.csv", list(field_rows[0].keys()) if field_rows else ["field"], field_rows)
    semantics = continuation_metadata(prior.semantics_audit(details))
    semantics.update({"analysis_allowed": False, "blocked_reason": reason, "available_successful_details": len(details), "required_details": prior.MAX_CALLS})
    private_write(paths["diagnostics"] / "teamfight_semantics_audit.json", semantics)
    not_evaluated = {"schema_version": SCHEMA, "status": "NOT_EVALUATED", "reason": reason, "available_successful_details": len(details), "required_details": prior.MAX_CALLS}
    for name in ("population_baseline.json", "control_attenuation.json", "common_direction_check.json", "stability_by_n.json", "pilot_gate_results.json"):
        private_write(paths["diagnostics"] / name, not_evaluated)
    write_csv(paths["diagnostics"] / "death_context_match_level.csv", ["status", "reason"], [])
    write_csv(paths["diagnostics"] / "death_context_player_level.csv", ["status", "reason"], [])
    write_csv(paths["diagnostics"] / "profile_batch_latency.csv", ["name", "profile_index", "requested_matches", "observed_responses", "successful_unique", "failed_responses", "concurrency", "wall_seconds"], measurements)
    latency, latency_rows = prior.latency_outputs(transport, measurements, None, collection_seconds)
    latency = continuation_metadata(latency)
    coverage = continuation_metadata(prior.coverage_model(profiles, None))
    model = continuation_metadata(prior.free_user_model(latency, measurements, None))
    private_write(paths["diagnostics"] / "latency_summary.json", latency)
    private_write(paths["diagnostics"] / "coverage_model.json", coverage)
    private_write(paths["diagnostics"] / "free_user_cost_latency_model.json", model)
    write_csv(paths["diagnostics"] / "latency_measurements.csv", list(latency_rows[0].keys()) if latency_rows else ["ordinal"], latency_rows)
    stats = provider_stats(transport)
    cost = read_json(paths["diagnostics"] / "cost_ledger.json")
    summary = {
        "schema_version": SCHEMA,
        "status": "BLOCKED",
        "terminal_verdict": "PILOT_COLLECTION_BLOCKED",
        "verdict_reason": reason,
        "campaign_id": CAMPAIGN,
        "frozen_panel": {"profiles": prior.PANEL_PROFILES, "matches_per_profile": prior.MATCHES_PER_PROFILE, "planned_unique_matches": prior.MAX_CALLS, "selection_digest": frozen["selection_digest"]},
        "collection": {"physical_gets": transport.physical_count, "previous_successes_reused": len(meta["prior_success_ids"]), "new_successful_unique": len(new_details), "successful": len(meta["prior_success_ids"]) + len(new_details), "failed_attempts": len([row for row in transport.responses if row.get("error") is not None]), "transient_retries": transport.retry_count, "final_frozen_panel_completion": len(meta["prior_success_ids"]) + len(new_details) == prior.MAX_CALLS, "replay_parse_requests": 0},
        "provider_reliability": stats,
        "field_completeness": field_summary,
        "teamfight_semantics": semantics,
        "analysis_status": "NOT_RUN",
        "coverage": coverage,
        "latency": latency,
        "tier2_corpus": tier2,
        "integrity": {"old_holdout_evaluated": 0, "fresh_sealed_validation_analytically_evaluated": 0, "replay_parse_requests": 0, "stratz_calls": 0, "steam_calls": 0, "analytical_behavior_changed": False, "deployment": False},
        "cost": cost,
    }
    private_write(paths["diagnostics"] / "aggregate_summary.json", summary)
    private_write(paths["diagnostics"] / "pilot_verdict.json", {"schema_version": SCHEMA, "verdict": "PILOT_COLLECTION_BLOCKED", "reason": reason})
    private_write(paths["diagnostics"] / "pilot_blocked.json", {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, "status": "BLOCKED", "reason": reason, "physical_gets": transport.physical_count, "final_successful_unique": len(meta["prior_success_ids"]) + len(new_details)})
    return summary


def finalize_analysis(
    *,
    storage_root: Path,
    paths: Mapping[str, Path],
    items: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Any],
    meta: Mapping[str, Any],
    transport: ContinuationTransport,
    new_details: Sequence[Mapping[str, Any]],
    measurements: Sequence[Mapping[str, Any]],
    collection_seconds: float,
) -> dict[str, Any]:
    prior_details = prior_success_details(
        storage_root=storage_root, items=items, prior_events=meta["prior_events"]
    )
    details = [*prior_details, *new_details]
    if len(details) != prior.MAX_CALLS:
        raise PilotBlocked("PANEL_COLLECTION_INCOMPLETE")
    proxy = AnalysisTransportProxy(transport, total_successes=prior.MAX_CALLS, errors=[])
    analysis = with_continuation_metadata(
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
        batch_measurements=measurements,
        collection_started=time.monotonic() - collection_seconds,
    )
    gates = dict(analysis["gates"])
    gates.pop("zero_retries", None)
    retry_policy_pass = (
        max((int(row.get("retry_number", 0)) for row in transport.responses), default=0) <= MAX_RETRIES
        and transport.physical_count <= MAX_NEW_GETS
    )
    gates["retry_policy_max_two_after_initial"] = {
        "observed_max_retry_number": max((int(row.get("retry_number", 0)) for row in transport.responses), default=0),
        "observed_retries": transport.retry_count,
        "passed": retry_policy_pass,
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
    gate_payload = {
        "schema_version": SCHEMA,
        "campaign_id": CAMPAIGN,
        "verdict": verdict,
        "verdict_reason": reason,
        "gates": gates,
        "retry_policy": {"max_retries_after_initial": MAX_RETRIES, "max_attempts_per_match": MAX_ATTEMPTS, "adaptive_top_up": False},
    }
    private_write(paths["diagnostics"] / "pilot_gate_results.json", gate_payload)
    summary = dict(analysis["summary"])
    summary.update({"schema_version": SCHEMA, "campaign_id": CAMPAIGN, "status": "PASS" if verdict == "DEATH_CONTEXT_PILOT_PASS" else "FAIL", "terminal_verdict": verdict, "verdict_reason": reason})
    summary["collection"] = {
        "physical_gets": transport.physical_count,
        "previous_successes_reused": len(meta["prior_success_ids"]),
        "new_successful_unique": len(new_details),
        "successful": prior.MAX_CALLS,
        "failed_attempts": len([row for row in transport.responses if row.get("error") is not None]),
        "transient_retries": transport.retry_count,
        "final_frozen_panel_completion": True,
        "replay_parse_requests": 0,
    }
    summary["provider_reliability"] = provider_stats(transport)
    summary["integrity"].update({"replay_parse_requests": 0, "stratz_calls": 0, "steam_calls": 0, "fresh_sealed_validation_analytically_evaluated": 0, "old_holdout_evaluated": 0, "adaptive_top_up": False, "outcome_based_replacements": False, "analytical_behavior_changed": False, "deployment": False})
    private_write(paths["diagnostics"] / "aggregate_summary.json", summary)
    private_write(paths["diagnostics"] / "pilot_verdict.json", {"schema_version": SCHEMA, "verdict": verdict, "reason": reason})
    write_csv(paths["diagnostics"] / "profile_batch_latency.csv", ["name", "profile_index", "requested_matches", "observed_responses", "successful_unique", "failed_responses", "concurrency", "wall_seconds"], measurements)
    private_write(paths["diagnostics"] / "provider_reliability.json", {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, **provider_stats(transport)})
    return {"summary": summary, "gates": gates, "analysis": analysis}


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--storage-root", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        rng = random.Random(1)
        assert transient_error(500, "http_500")
        assert transient_error(None, "timeout")
        assert not transient_error(404, "http_404")
        assert 2.0 <= retry_delay(1, None, rng) <= 5.0
        assert retry_delay(2, "7", rng) == 7.0
        print("self_check_pass")
        return 0
    if args.source_root is None or args.storage_root is None:
        parser.error("--source-root and --storage-root are required unless --self-check is used")
    source_root = args.source_root.resolve()
    storage_root = args.storage_root.resolve()
    paths = paths_for(storage_root)
    frozen: dict[str, Any] = {}
    items: list[dict[str, Any]] = []
    queue: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}
    try:
        frozen, items, profiles, meta = prior_panel_and_queue(source_root=source_root, storage_root=storage_root, paths=paths)
        queue_payload = read_json(paths["diagnostics"] / "continuation_queue.json")
        queue = [dict(item) for item in queue_payload["items"]]
        progress(paths["progress"], stage="preflight_complete", transport=None, queue_position=0, queue_total=len(queue), prior_successes=len(meta["prior_success_ids"]), next_action="execute_prior_http500_then_900_missing_gets")
        if args.preflight_only:
            print(json.dumps({"status": "PREFLIGHT_PASS", "selection_digest": frozen["selection_digest"], "queue": len(queue), "prior_successes_reused": len(meta["prior_success_ids"]), "opendota_calls": 0}, sort_keys=True))
            return 0
        transport, new_details, measurements, collection_seconds = asyncio.run(
            collect(storage_root=storage_root, paths=paths, items=items, queue=queue, profiles=profiles, meta=meta)
        )
        complete = len(meta["prior_success_ids"]) + len(new_details) == prior.MAX_CALLS and not transport.error_messages
        if not complete:
            reason = "PILOT_COLLECTION_BLOCKED"
            summary = write_blocked_outputs(storage_root=storage_root, paths=paths, items=items, profiles=profiles, frozen=frozen, meta=meta, transport=transport, new_details=new_details, measurements=measurements, collection_seconds=collection_seconds, reason=reason)
            progress(paths["progress"], stage="terminal_blocked", transport=transport, queue_position=len(queue), queue_total=len(queue), prior_successes=len(meta["prior_success_ids"]), next_action="write_blocked_evidence_and_stop", errors=[reason, *transport.error_messages])
            print(json.dumps({"status": summary["status"], "terminal_verdict": summary["terminal_verdict"], "physical_gets": transport.physical_count, "successful": summary["collection"]["successful"], "output": str(paths["diagnostics"])}, sort_keys=True))
            return 2
        analysis = finalize_analysis(storage_root=storage_root, paths=paths, items=items, profiles=profiles, frozen=frozen, meta=meta, transport=transport, new_details=new_details, measurements=measurements, collection_seconds=collection_seconds)
        progress(paths["progress"], stage="terminal_verdict", transport=transport, queue_position=len(queue), queue_total=len(queue), prior_successes=len(meta["prior_success_ids"]), next_action="write_tracked_evidence_and_review_branch", errors=[])
        print(json.dumps({"status": analysis["summary"]["status"], "terminal_verdict": analysis["summary"]["terminal_verdict"], "physical_gets": transport.physical_count, "successful": transport.successful_count + len(meta["prior_success_ids"]), "output": str(paths["diagnostics"])}, sort_keys=True))
        return 0
    except PilotBlocked as exc:
        reason = str(exc)
        private_write(paths["diagnostics"] / "pilot_blocked.json", {"schema_version": SCHEMA, "campaign_id": CAMPAIGN, "status": "BLOCKED", "reason": reason})
        progress(paths["progress"], stage="terminal_blocked", transport=None, queue_position=0, queue_total=len(queue), prior_successes=len(meta.get("prior_success_ids", [])), next_action="stop_and_review_blocker", errors=[reason])
        print(json.dumps({"status": "BLOCKED", "terminal_verdict": "PILOT_COLLECTION_BLOCKED", "reason": reason}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
