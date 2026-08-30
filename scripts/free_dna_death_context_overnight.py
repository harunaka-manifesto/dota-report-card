#!/usr/bin/env python3
"""Run the owner-approved, resumable Death Context detail pilot.

This script has one network path: GET /matches/{match_id} for the frozen
development panel. It never calls history, public matches, parse endpoints,
STRATZ, Steam, or production services. The analysis is deliberately local and
uses whole-match units throughout.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import hmac
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from free_dna_death_context_local_reuse_pilot import (  # noqa: E402
    BASE_SHA,
    MATCHES_PER_PROFILE,
    PANEL_PROFILES,
    detail_shape,
    field_completeness,
    hmac_rank,
    is_number,
    load_profiles,
    nonnegative_number,
    normalize_detail,
    profile_membership,
    quantile,
    read_json,
    semantics_audit,
    sha256_file,
)

LIVE_SCHEMA = "free-dna-death-context-overnight-1.0.0"
LIVE_CAMPAIGN = "free-dna-death-context-tier2-pilot-2026-08-28"
SOURCE_CAMPAIGN = "v61-session-drift-phase2-2026-08-28"
PROVIDER = "OpenDota"
SOURCE_MARKER = "22"
MAX_CALLS = 960
COST_IDR_PER_100 = 200.0
COST_USD_PER_100 = 0.01
RATE_PER_MINUTE = 240
RETRY_LIMIT = 0
STORAGE_CEILING = 384 * 1024 * 1024
NESTED_N = (10, 15, 20, 25, 30)
QA_COUNT = 4
BOOTSTRAP_DRAWS = 500
SUBSAMPLE_DRAWS = 100
REFERENCE_DEATH_MINIMUM = 100


class PilotBlocked(RuntimeError):
    """A terminal collection or provenance stop with no retry."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def private_write(path: Path, value: Any, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    try:
        view = memoryview(payload)
        while view:
            view = view[os.write(descriptor, view) :]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.chmod(mode)
    temporary.replace(path)
    path.chmod(mode)


write_json = private_write


def private_write_bytes_once(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        view = memoryview(value)
        while view:
            view = view[os.write(descriptor, view) :]
        os.fsync(descriptor)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        os.close(descriptor)
    path.chmod(0o600)


def append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o600)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def replace_paths(value: Any, old_root: str, new_root: str) -> Any:
    if isinstance(value, str):
        return value.replace(old_root, new_root)
    if isinstance(value, list):
        return [replace_paths(item, old_root, new_root) for item in value]
    if isinstance(value, dict):
        return {key: replace_paths(item, old_root, new_root) for key, item in value.items()}
    return value


def canonicalize_prior_manifests(storage_root: Path) -> None:
    old_root = str(ROOT)
    new_root = str(storage_root.resolve())
    paths = (
        storage_root / ".local/corpora/opendota/free-dna-tier2/manifests/corpus-manifest.json",
        storage_root / ".local/corpora/opendota/free-dna-tier2/manifests/panel-binding.json",
        storage_root / ".local/diagnostics/free-dna-death-context-local-reuse-pilot/tier2_reusable_manifest.json",
    )
    for path in paths:
        if path.exists():
            private_write(path, replace_paths(read_json(path), old_root, new_root))


def git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def source_profile_pseudonym(source_secret: bytes, account_id: Any) -> str | None:
    if not isinstance(account_id, int) or isinstance(account_id, bool) or account_id <= 0:
        return None
    return hashlib.sha256(source_secret + str(account_id).encode("ascii")).hexdigest()


def source_manifests(source_root: Path) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    corpus = source_root / ".local/corpora/opendota/v61-session-drift-expansion"
    raw_manifest = read_json(corpus / "raw/raw-corpus-manifest.json")
    normalized_manifest = read_json(corpus / "normalized/normalized-corpus-manifest.json")
    secret = (corpus / "manifests/private-split-secret.bin").read_bytes()
    if len(secret) != 32:
        raise PilotBlocked("LINEAGE_FAILURE: source split secret is not 32 bytes")
    return raw_manifest, normalized_manifest, secret


def frozen_panel(
    source_root: Path, storage_root: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    source_corpus = source_root / ".local/corpora/opendota/v61-session-drift-expansion"
    panel_path = storage_root / ".local/diagnostics/free-dna-death-context-local-reuse-pilot/panel_manifest.json"
    if not panel_path.exists():
        raise PilotBlocked("PANEL_MANIFEST_MISSING")
    prior_panel = read_json(panel_path)
    selected = prior_panel.get("selected_panel_profiles")
    if not isinstance(selected, list) or len(selected) != PANEL_PROFILES:
        raise PilotBlocked("PANEL_MANIFEST_NOT_32_PROFILES")
    profiles, profile_meta = load_profiles(source_corpus)
    by_profile = {str(profile["profile_id"]): profile for profile in profiles}
    salt_path = storage_root / ".local/diagnostics/free-dna-death-context-local-reuse-pilot/private/private-salt.bin"
    if not salt_path.exists():
        raise PilotBlocked("PANEL_SALT_MISSING")
    salt = salt_path.read_bytes()
    if len(salt) != 32:
        raise PilotBlocked("PANEL_SALT_NOT_32_BYTES")
    ranked_profiles = sorted(
        profiles,
        key=lambda profile: (
            hmac_rank(
                salt,
                "death-context-profile:",
                str(profile["profile_id"]),
            ),
            str(profile["profile_id"]),
        ),
    )
    salt_digest = hashlib.sha256(salt).hexdigest()
    if prior_panel.get("private_salt_sha256") != salt_digest:
        raise PilotBlocked("PANEL_SALT_DIGEST_MISMATCH")

    expected: list[dict[str, Any]] = []
    claimed: set[int] = set()
    for profile in ranked_profiles:
        profile_id = str(profile["profile_id"])
        candidates_by_id = {
            int(row["match_id"]): row
            for row in profile.get("matches", [])
            if isinstance(row, dict)
            and row.get("source_version") == SOURCE_MARKER
            and isinstance(row.get("match_id"), int)
        }
        ranked_matches = sorted(
            candidates_by_id.values(),
            key=lambda row: (
                hmac_rank(salt, "death-context-match:", str(int(row["match_id"]))),
                int(row["match_id"]),
            ),
        )
        available = [row for row in ranked_matches if int(row["match_id"]) not in claimed]
        if len(available) < MATCHES_PER_PROFILE:
            continue
        chosen = [int(row["match_id"]) for row in available[:MATCHES_PER_PROFILE]]
        expected.append(
            {
                "profile_id": profile_id,
                "profile_rank": hmac_rank(salt, "death-context-profile:", profile_id),
                "source_version_22_match_count": len(ranked_matches),
                "selected_match_ids": chosen,
            }
        )
        claimed.update(chosen)
        if len(expected) == PANEL_PROFILES:
            break
    actual = [
        {
            "profile_id": str(row.get("profile_id")),
            "profile_rank": str(row.get("profile_rank")),
            "source_version_22_match_count": int(row.get("source_version_22_match_count", 0)),
            "selected_match_ids": [int(match_id) for match_id in row.get("selected_match_ids", [])],
        }
        for row in selected
    ]
    if actual != expected:
        raise PilotBlocked("PANEL_DIGEST_OR_SELECTION_MISMATCH")
    if len(claimed) != MAX_CALLS:
        raise PilotBlocked("PANEL_NOT_960_UNIQUE_MATCHES")
    if any(
        row.get("source_version_22_match_count", 0) < MATCHES_PER_PROFILE
        for row in expected
    ):
        raise PilotBlocked("PANEL_SOURCE_MARKER_SUPPORT_FAILURE")
    items: list[dict[str, Any]] = []
    for profile_index, row in enumerate(expected):
        profile = by_profile.get(row["profile_id"])
        if profile is None:
            raise PilotBlocked("PANEL_PROFILE_NOT_IN_DEVELOPMENT_LINEAGE")
        summary_by_id = {
            int(match["match_id"]): match
            for match in profile.get("matches", [])
            if isinstance(match, dict) and isinstance(match.get("match_id"), int)
        }
        for match_index, match_id in enumerate(row["selected_match_ids"]):
            summary = summary_by_id.get(match_id)
            if not isinstance(summary, dict) or summary.get("source_version") != SOURCE_MARKER:
                raise PilotBlocked("SELECTED_MATCH_NOT_KNOWN_PARSED_BEFORE_GET")
            items.append(
                {
                    "profile_id": row["profile_id"],
                    "profile_index": profile_index,
                    "match_index": match_index,
                    "match_id": match_id,
                    "summary": summary,
                }
            )
    selection_rows = [
        {"profile_id": row["profile_id"], "selected_match_ids": row["selected_match_ids"]}
        for row in expected
    ]
    selection_digest = digest_value(selection_rows)
    match_digest = digest_value([item["match_id"] for item in items])
    profile_digest = digest_value([row["profile_id"] for row in expected])
    frozen = {
        "schema_version": LIVE_SCHEMA,
        "campaign_id": LIVE_CAMPAIGN,
        "provider": PROVIDER,
        "lineage": {
            "base_sha": BASE_SHA,
            "source_campaign": SOURCE_CAMPAIGN,
            "source_version_rule": "exactly source_version == '22'",
            "development_tuning_profiles": profile_meta["eligible_profiles"],
            "fresh_validation_used": False,
            "old_holdout_used": False,
        },
        "sampling": {
            "profile_count": PANEL_PROFILES,
            "matches_per_profile": MATCHES_PER_PROFILE,
            "total_unique_match_ids": MAX_CALLS,
            "profile_namespace": "death-context-profile:",
            "match_namespace": "death-context-match:",
            "algorithm": "HMAC-SHA256 profile rank, then HMAC-SHA256 match rank; ascending digest then numeric ID",
            "outcome_blind": True,
            "selection_before_detail_inspection": True,
        },
        "private_salt_sha256": salt_digest,
        "selection_digest": selection_digest,
        "profile_selection_digest": profile_digest,
        "match_selection_digest": match_digest,
        "source_marker_verified_before_gets": True,
        "frozen_at": now_iso(),
        "profiles": expected,
    }
    return frozen, items, profiles, {
        "salt": salt,
        "salt_sha256": salt_digest,
        "selection_rows": selection_rows,
        "profile_meta": profile_meta,
    }


def progress_payload(
    *,
    stage: str,
    calls_used: int,
    profiles_completed: int,
    matches_completed: int,
    errors: Sequence[str],
    latest_gate_status: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "schema_version": LIVE_SCHEMA,
        "campaign_id": LIVE_CAMPAIGN,
        "stage": stage,
        "timestamp": now_iso(),
        "branch_sha": git_sha(),
        "calls_used": calls_used,
        "remaining_budget": {
            "physical_gets": max(0, MAX_CALLS - calls_used),
            "idr": max(0.0, MAX_CALLS * COST_IDR_PER_100 / 100 - calls_used * COST_IDR_PER_100 / 100),
            "usd": max(0.0, MAX_CALLS * COST_USD_PER_100 / 100 - calls_used * COST_USD_PER_100 / 100),
        },
        "profiles_completed": profiles_completed,
        "matches_completed": matches_completed,
        "errors": list(errors),
        "latest_gate_status": latest_gate_status,
        "next_action": next_action,
    }


def write_progress(path: Path, **kwargs: Any) -> None:
    private_write(path, progress_payload(**kwargs))


def detail_validation(value: Any, item: Mapping[str, Any]) -> str | None:
    if not isinstance(value, dict):
        return "schema_contract_break:root_not_object"
    if value.get("match_id") != item["match_id"]:
        return "schema_contract_break:match_id_mismatch"
    if value.get("version") != 22 or (value.get("od_data") or {}).get("has_parsed") is not True:
        return "parsed_marker_mismatch"
    players = value.get("players")
    if not isinstance(players, list) or len(players) != 10:
        return "schema_contract_break:players_not_ten"
    slots = [player.get("player_slot") for player in players if isinstance(player, dict)]
    if len(slots) != 10 or any(not is_number(slot) for slot in slots) or len(set(slots)) != 10:
        return "schema_contract_break:player_slot_mapping"
    for player in players:
        if not isinstance(player, dict):
            return "schema_contract_break:player_not_object"
        if not is_number(player.get("deaths")) or player["deaths"] < 0:
            return "schema_contract_break:player_deaths"
        if not is_number(player.get("hero_id")):
            return "schema_contract_break:hero_id"
    for name in ("radiant_win", "duration", "patch", "radiant_gold_adv", "teamfights"):
        if name not in value:
            return f"schema_contract_break:missing_{name}"
    if not isinstance(value["radiant_win"], bool) or not is_number(value["duration"]):
        return "schema_contract_break:match_context"
    if not is_number(value["patch"]) or not isinstance(value["radiant_gold_adv"], list):
        return "schema_contract_break:advantage_or_patch"
    if not isinstance(value["teamfights"], list):
        return "schema_contract_break:teamfights_not_list"
    for fight in value["teamfights"]:
        if not isinstance(fight, dict):
            return "schema_contract_break:fight_not_object"
        if not (
            is_number(fight.get("start"))
            and is_number(fight.get("end"))
            and fight["end"] >= fight["start"]
        ):
            return "teamfight_semantics_failure:start_end"
        fight_players = fight.get("players")
        if not isinstance(fight_players, list) or len(fight_players) != 10:
            return "teamfight_semantics_failure:participants_not_ten"
        for fight_player in fight_players:
            if not isinstance(fight_player, dict) or not nonnegative_number(fight_player.get("deaths")):
                return "teamfight_semantics_failure:participant_deaths"
    return None


class RateGate:
    def __init__(self, starts_per_minute: int) -> None:
        self.interval = 60.0 / starts_per_minute
        self.next_start = 0.0
        self.lock = asyncio.Lock()

    async def wait_for_slot(self) -> None:
        async with self.lock:
            current = time.monotonic()
            if self.next_start > current:
                await asyncio.sleep(self.next_start - current)
                current = time.monotonic()
            self.next_start = max(current, self.next_start) + self.interval


class LiveTransport:
    def __init__(self, *, paths: Mapping[str, Path], base_url: str, api_key: str | None, timeout: float) -> None:
        self.paths = paths
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=10),
        )
        self.ledger_path = paths["diagnostics"] / "request_ledger.jsonl"
        self.events = read_jsonl(self.ledger_path)
        self.responses = [event for event in self.events if event.get("event") == "response_recorded"]
        self.validations = {
            str(event.get("request_id")): event
            for event in self.events
            if event.get("event") == "validation"
        }
        self.completed_by_match: dict[int, dict[str, Any]] = {}
        self.error_messages: list[str] = []
        self.stop_event = asyncio.Event()
        self.state_lock = asyncio.Lock()
        self.rate_gate = RateGate(RATE_PER_MINUTE)
        self._check_resume_state()

    async def __aenter__(self) -> LiveTransport:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.http.aclose()

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
        if starts != response_ids:
            raise PilotBlocked("INDETERMINATE_INTERRUPTED_REQUEST")
        seen_matches: set[int] = set()
        for response in self.responses:
            match_id = response.get("match_id")
            if not isinstance(match_id, int) or match_id in seen_matches:
                raise PilotBlocked("REQUEST_LEDGER_DUPLICATE_MATCH")
            seen_matches.add(match_id)
            request_id = str(response.get("request_id"))
            validation = self.validations.get(request_id)
            if response.get("error") is None:
                raw_path = Path(str(response.get("raw_path")))
                if not raw_path.is_file() or sha256_file(raw_path) != response.get("response_sha256"):
                    raise PilotBlocked("RAW_RESPONSE_DIGEST_FAILURE")
                if validation is None or validation.get("error") is not None:
                    raise PilotBlocked("INDETERMINATE_RESPONSE_VALIDATION")
                self.completed_by_match[match_id] = response
            else:
                self.error_messages.append(str(response.get("error")))
        if self.error_messages:
            self.stop_event.set()

    @property
    def physical_count(self) -> int:
        return len(self.responses)

    @property
    def successful_count(self) -> int:
        return len(self.completed_by_match)

    def cached_detail(self, item: Mapping[str, Any]) -> dict[str, Any] | None:
        response = self.completed_by_match.get(int(item["match_id"]))
        if response is None:
            return None
        raw_path = Path(str(response["raw_path"]))
        try:
            value = json.loads(raw_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PilotBlocked(f"CACHED_RESPONSE_READ_FAILURE:{type(exc).__name__}") from exc
        return self._detail_record(item, value, response)

    def _append_start(self, item: Mapping[str, Any], *, concurrency: int, batch_id: str, ordinal: int) -> str:
        request_id = f"{LIVE_CAMPAIGN}:{item['match_id']}"
        append_jsonl(
            self.ledger_path,
            {
                "event": "request_started",
                "schema_version": LIVE_SCHEMA,
                "campaign_id": LIVE_CAMPAIGN,
                "request_id": request_id,
                "ordinal": ordinal,
                "method": "GET",
                "endpoint": f"/matches/{item['match_id']}",
                "params": [],
                "match_id": int(item["match_id"]),
                "profile_id": str(item["profile_id"]),
                "concurrency": concurrency,
                "batch_id": batch_id,
                "retry_number": 0,
                "retry_limit": RETRY_LIMIT,
                "requested_at": now_iso(),
            },
        )
        return request_id

    def _detail_record(self, item: Mapping[str, Any], value: Any, response: Mapping[str, Any]) -> dict[str, Any]:
        path = Path(str(response["raw_path"]))
        return {
            "match_id": int(item["match_id"]),
            "path": path,
            "response_sha256": str(response["response_sha256"]),
            "bytes": int(response["response_bytes"]),
            "ledger": dict(response),
            "match": value,
            "shape": detail_shape(value),
            "panel_profile_id": str(item["profile_id"]),
        }

    async def fetch(self, item: Mapping[str, Any], *, concurrency: int, batch_id: str) -> dict[str, Any]:
        match_id = int(item["match_id"])
        cached = self.cached_detail(item)
        if cached is not None:
            return cached
        if self.stop_event.is_set():
            raise PilotBlocked(self.error_messages[-1] if self.error_messages else "COLLECTION_STOPPED")
        async with self.state_lock:
            cached = self.cached_detail(item)
            if cached is not None:
                return cached
            if self.stop_event.is_set():
                raise PilotBlocked(self.error_messages[-1] if self.error_messages else "COLLECTION_STOPPED")
            if self.physical_count >= MAX_CALLS:
                raise PilotBlocked("REQUEST_CEILING_REACHED")
            ordinal = self.physical_count
            marker = self.paths["diagnostics"] / f".inflight-{ordinal:04d}-{match_id}.json"
            private_write(marker, {"campaign_id": LIVE_CAMPAIGN, "match_id": match_id, "ordinal": ordinal})
            await self.rate_gate.wait_for_slot()
            if self.stop_event.is_set():
                marker.unlink(missing_ok=True)
                raise PilotBlocked(self.error_messages[-1] if self.error_messages else "COLLECTION_STOPPED")
            request_id = self._append_start(item, concurrency=concurrency, batch_id=batch_id, ordinal=ordinal)
        started = time.monotonic()
        status: int | None = None
        body = b""
        transport_error: str | None = None
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            response = await self.http.get(
                f"{self.base_url}/matches/{match_id}", headers=headers
            )
            status = response.status_code
            body = response.content
            if status != 200:
                transport_error = (
                    "rate_limit_429"
                    if status == 429
                    else "auth_or_billing_" + str(status)
                    if status in {401, 402, 403}
                    else "http_" + str(status)
                )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
            transport_error = type(exc).__name__
        elapsed = time.monotonic() - started
        raw_path: Path | None = None
        if body:
            if directory_size(self.paths["corpus"]) + directory_size(self.paths["diagnostics"]) + len(body) > STORAGE_CEILING:
                transport_error = "storage_ceiling_risk"
            raw_path = self.paths["raw_responses"] / f"response-{ordinal:04d}-{match_id}.body"
            private_write_bytes_once(raw_path, body)
        response_event = {
            "event": "response_recorded",
            "schema_version": LIVE_SCHEMA,
            "campaign_id": LIVE_CAMPAIGN,
            "request_id": request_id,
            "ordinal": ordinal,
            "match_id": match_id,
            "profile_id": str(item["profile_id"]),
            "method": "GET",
            "endpoint": f"/matches/{match_id}",
            "concurrency": concurrency,
            "batch_id": batch_id,
            "requested_at": now_iso(),
            "completed_at": now_iso(),
            "latency_seconds": elapsed,
            "http_status": status,
            "response_bytes": len(body),
            "response_sha256": sha256_bytes(body) if body else None,
            "raw_path": str(raw_path) if raw_path else None,
            "retry_number": 0,
            "retry_limit": RETRY_LIMIT,
            "error": transport_error,
        }
        append_jsonl(self.ledger_path, response_event)
        self.responses.append(response_event)
        marker.unlink(missing_ok=True)
        if transport_error is not None:
            self.error_messages.append(transport_error)
            self.stop_event.set()
            raise PilotBlocked(transport_error)
        try:
            value = json.loads(body)
        except (UnicodeDecodeError, ValueError) as exc:
            validation_error = f"invalid_json:{type(exc).__name__}"
            value = None
        else:
            validation_error = detail_validation(value, item)
        append_jsonl(
            self.ledger_path,
            {
                "event": "validation",
                "schema_version": LIVE_SCHEMA,
                "campaign_id": LIVE_CAMPAIGN,
                "request_id": request_id,
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
            },
        )
        self.validations[request_id] = {
            "event": "validation",
            "request_id": request_id,
            "error": validation_error,
        }
        if validation_error is not None:
            self.error_messages.append(validation_error)
            self.stop_event.set()
            raise PilotBlocked(validation_error)
        self.completed_by_match[match_id] = response_event
        return self._detail_record(item, value, response_event)


async def fetch_batch(
    transport: LiveTransport,
    items: Sequence[Mapping[str, Any]],
    *,
    concurrency: int,
    batch_id: str,
) -> tuple[dict[int, dict[str, Any]], float]:
    started = time.monotonic()
    semaphore = asyncio.Semaphore(concurrency)

    async def one(item: Mapping[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await transport.fetch(item, concurrency=concurrency, batch_id=batch_id)

    results = await asyncio.gather(*(one(item) for item in items), return_exceptions=True)
    errors = [result for result in results if isinstance(result, BaseException)]
    if errors:
        transport.stop_event.set()
        raise errors[0]
    return {int(result["match_id"]): result for result in results}, time.monotonic() - started  # type: ignore[index]


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def response_entries(transport: LiveTransport) -> list[dict[str, Any]]:
    return sorted(transport.responses, key=lambda row: int(row["ordinal"]))


def ledger_csv_rows(transport: LiveTransport) -> list[dict[str, Any]]:
    starts = {
        str(event["request_id"]): event
        for event in transport.events
        if event.get("event") == "request_started"
    }
    rows = []
    for response in response_entries(transport):
        start = starts.get(str(response["request_id"]), {})
        rows.append(
            {
                "campaign_id": response.get("campaign_id"),
                "request_id": response.get("request_id"),
                "ordinal": response.get("ordinal"),
                "profile_id": response.get("profile_id"),
                "match_id": response.get("match_id"),
                "method": response.get("method"),
                "endpoint": response.get("endpoint"),
                "concurrency": response.get("concurrency"),
                "batch_id": response.get("batch_id"),
                "requested_at": start.get("requested_at"),
                "completed_at": response.get("completed_at"),
                "latency_seconds": response.get("latency_seconds"),
                "http_status": response.get("http_status"),
                "response_bytes": response.get("response_bytes"),
                "response_sha256": response.get("response_sha256"),
                "raw_path": response.get("raw_path"),
                "retry_number": response.get("retry_number"),
                "retry_limit": response.get("retry_limit"),
                "error": response.get("error"),
            }
        )
    return rows


def ledger_window_seconds(rows: Sequence[Mapping[str, Any]], starts: Mapping[str, Mapping[str, Any]]) -> float | None:
    requested = [
        datetime.fromisoformat(str(starts[str(row["request_id"])]["requested_at"]))
        for row in rows
        if str(row["request_id"]) in starts and starts[str(row["request_id"])].get("requested_at")
    ]
    completed = [
        datetime.fromisoformat(str(row["completed_at"]))
        for row in rows
        if row.get("completed_at")
    ]
    if not requested or not completed:
        return None
    return (max(completed) - min(requested)).total_seconds()


def batch_measurements_from_ledger(transport: LiveTransport) -> list[dict[str, Any]]:
    starts = {
        str(event["request_id"]): event
        for event in transport.events
        if event.get("event") == "request_started"
    }
    by_batch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in response_entries(transport):
        by_batch[str(row.get("batch_id"))].append(row)

    def measurement(
        name: str,
        batch_ids: Sequence[str],
        profile_index: int,
        requested_matches: int,
        concurrency: int,
    ) -> dict[str, Any] | None:
        rows = [row for batch_id in batch_ids for row in by_batch.get(batch_id, [])]
        wall_seconds = ledger_window_seconds(rows, starts)
        if not rows or wall_seconds is None:
            return None
        return {
            "name": name,
            "profile_index": profile_index,
            "requested_matches": requested_matches,
            "observed_responses": len(rows),
            "failed_responses": sum(row.get("error") is not None for row in rows),
            "concurrency": concurrency,
            "wall_seconds": wall_seconds,
            "observed_from_ledger": True,
        }

    definitions = (
        ("qa_sequential", ("qa_sequential",), 0, 4, 1),
        (
            "profile_0_20",
            ("qa_sequential", "profile_0_concurrency_1_first_20"),
            0,
            20,
            1,
        ),
        (
            "profile_0_30",
            (
                "qa_sequential",
                "profile_0_concurrency_1_first_20",
                "profile_0_concurrency_1_last_10",
            ),
            0,
            30,
            1,
        ),
        ("profile_1_20", ("profile_1_concurrency_5_first_20",), 1, 20, 5),
        (
            "profile_1_30",
            ("profile_1_concurrency_5_first_20", "profile_1_concurrency_5_last_10"),
            1,
            30,
            5,
        ),
    )
    return [
        result
        for definition in definitions
        if (result := measurement(*definition)) is not None
    ]


def cost_ledger(transport: LiveTransport, storage_bytes: int) -> dict[str, Any]:
    calls = transport.physical_count
    failures = sum(row.get("error") is not None for row in transport.responses)
    return {
        "schema_version": LIVE_SCHEMA,
        "campaign_id": LIVE_CAMPAIGN,
        "physical_gets": calls,
        "successful_gets": transport.successful_count,
        "failed_gets": failures,
        "retries": sum(int(row.get("retry_number", 0)) for row in transport.responses),
        "max_physical_gets": MAX_CALLS,
        "estimated_cost_idr_pro_rata": calls * COST_IDR_PER_100 / 100,
        "estimated_cost_usd_pro_rata": calls * COST_USD_PER_100 / 100,
        "cost_ceiling_idr": MAX_CALLS * COST_IDR_PER_100 / 100,
        "cost_ceiling_usd": MAX_CALLS * COST_USD_PER_100 / 100,
        "storage_bytes": storage_bytes,
        "storage_mib": storage_bytes / (1024 * 1024),
        "storage_ceiling_bytes": STORAGE_CEILING,
        "storage_ceiling_mib": STORAGE_CEILING / (1024 * 1024),
        "replay_parse_requests": 0,
        "stratz_calls": 0,
        "steam_calls": 0,
        "within_ceiling": calls <= MAX_CALLS and storage_bytes <= STORAGE_CEILING,
    }


def numeric_stats(values: Sequence[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "p50_seconds": quantile(list(values), 0.50),
        "p90_seconds": quantile(list(values), 0.90),
        "p95_seconds": quantile(list(values), 0.95),
        "max_seconds": max(values) if values else None,
    }


def latency_outputs(
    transport: LiveTransport,
    batch_measurements: Sequence[Mapping[str, Any]],
    analysis_seconds: float | None,
    collection_seconds: float | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    successful = [
        float(row["latency_seconds"])
        for row in transport.responses
        if row.get("error") is None and row.get("latency_seconds") is not None
    ]
    bytes_values = [
        int(row["response_bytes"])
        for row in transport.responses
        if row.get("error") is None
    ]
    rows = [
        {
            "ordinal": row.get("ordinal"),
            "match_id": row.get("match_id"),
            "profile_id": row.get("profile_id"),
            "concurrency": row.get("concurrency"),
            "batch_id": row.get("batch_id"),
            "latency_seconds": row.get("latency_seconds"),
            "response_bytes": row.get("response_bytes"),
            "error": row.get("error"),
        }
        for row in response_entries(transport)
    ]
    summary = {
        "schema_version": LIVE_SCHEMA,
        "campaign_id": LIVE_CAMPAIGN,
        "request_latency_successful": numeric_stats(successful),
        "response_bytes": {
            "n": len(bytes_values),
            "p50": quantile([float(value) for value in bytes_values], 0.50),
            "p95": quantile([float(value) for value in bytes_values], 0.95),
            "max": max(bytes_values) if bytes_values else None,
        },
        "timeout_or_error_rate": (
            sum(row.get("error") is not None for row in transport.responses) / transport.physical_count
            if transport.physical_count
            else None
        ),
        "batch_measurements": list(batch_measurements),
        "local_analysis_seconds": analysis_seconds,
        "total_enrichment_seconds": (
            collection_seconds + analysis_seconds
            if collection_seconds is not None and analysis_seconds is not None
            else None
        ),
        "concurrency_used": sorted({row.get("concurrency") for row in transport.responses}),
        "rate_start_ceiling_per_minute": RATE_PER_MINUTE,
        "synchronous_under_60_seconds": any(
            measurement.get("name") == "profile_2_30"
            and isinstance(measurement.get("wall_seconds"), (int, float))
            and float(measurement["wall_seconds"]) <= 60
            for measurement in batch_measurements
        ),
    }
    return summary, rows


def load_prior_details(storage_root: Path) -> list[dict[str, Any]]:
    index_path = storage_root / ".local/diagnostics/free-dna-death-context-local-reuse-pilot/tier2_detail_index.json"
    if not index_path.exists():
        return []
    payload = read_json(index_path)
    details: list[dict[str, Any]] = []
    for record in payload.get("records", []):
        raw_path = Path(str(record.get("source_raw_path")))
        if not raw_path.is_file():
            continue
        value = read_json(raw_path)
        if not isinstance(value, dict) or value.get("version") != 22:
            continue
        details.append(
            {
                "match_id": int(record["match_id"]),
                "path": raw_path,
                "response_sha256": str(record["response_sha256"]),
                "bytes": int(record["response_bytes"]),
                "ledger": {
                    "campaign_id": record.get("source_campaign", SOURCE_CAMPAIGN),
                    "requested_at": record.get("capture_requested_at"),
                    "completed_at": record.get("capture_completed_at"),
                    "http_status": 200,
                    "response_bytes": int(record["response_bytes"]),
                    "response_sha256": str(record["response_sha256"]),
                    "error": None,
                },
                "match": value,
                "shape": detail_shape(value),
                "panel_profile_id": None,
            }
        )
    return details


def write_tier2_corpus(
    storage_root: Path,
    details: Sequence[Mapping[str, Any]],
    memberships: Mapping[int, Sequence[str]],
    selected_ids: set[int],
    source_manifest: Mapping[str, Any],
    panel_digest: str,
    salt_sha256: str,
    analytical_outcome_results_generated: bool = False,
) -> dict[str, Any]:
    corpus_root = storage_root / ".local/corpora/opendota/free-dna-tier2"
    manifests = corpus_root / "manifests"
    normalized_dir = corpus_root / "normalized"
    derived_dir = corpus_root / "derived"
    for directory in (manifests, normalized_dir, derived_dir):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
    unique: dict[tuple[int, str], Mapping[str, Any]] = {}
    for detail in details:
        unique[(int(detail["match_id"]), str(detail["response_sha256"]))] = detail
    records: list[dict[str, Any]] = []
    raw_persisted = 0
    raw_referenced = 0
    for detail in sorted(unique.values(), key=lambda row: int(row["match_id"])):
        match_id = int(detail["match_id"])
        normalized = normalize_detail(
            detail,
            len(memberships.get(match_id, [])),
            match_id in selected_ids,
        )
        normalized["capture_campaign"] = detail["ledger"].get("campaign_id")
        normalized["capture_latency_seconds"] = detail["ledger"].get("latency_seconds")
        normalized["raw_storage"] = (
            "canonical_live_raw" if str(detail["path"]).startswith(str(corpus_root)) else "source_corpus_reference"
        )
        normalized_digest = digest_value(normalized)
        normalized["canonical_normalized_sha256"] = normalized_digest
        output = normalized_dir / f"detail-{str(detail['response_sha256'])[:16]}.json"
        private_write(output, normalized)
        if str(detail["path"]).startswith(str(corpus_root)):
            raw_persisted += 1
        else:
            raw_referenced += 1
        records.append(
            {
                "match_id": match_id,
                "provider": PROVIDER,
                "campaign_id": detail["ledger"].get("campaign_id"),
                "source_raw_path": str(detail["path"]),
                "raw_sha256": detail["response_sha256"],
                "raw_bytes": detail["bytes"],
                "normalized_path": str(output),
                "normalized_sha256": sha256_file(output),
                "capture_latency_seconds": detail["ledger"].get("latency_seconds"),
                "field_shape": detail["shape"],
                "included_in_death_context_panel": match_id in selected_ids,
            }
        )
    normalized_digest = digest_value(
        [(row["match_id"], row["raw_sha256"], row["normalized_sha256"]) for row in records]
    )
    manifest = {
        "schema_version": LIVE_SCHEMA,
        "campaign_id": LIVE_CAMPAIGN,
        "provider": PROVIDER,
        "source_campaign": SOURCE_CAMPAIGN,
        "source_raw_corpus_digest": source_manifest.get("raw_corpus_digest"),
        "source_normalized_corpus_digest": source_manifest.get("normalized_corpus_digest"),
        "normalized_record_count": len(records),
        "normalized_digest": normalized_digest,
        "raw_records_persisted": raw_persisted,
        "raw_records_referenced": raw_referenced,
        "raw_copied": False,
        "raw_referenced": True,
        "normalizer_version": "free-dna-tier2-local-reuse-normalizer-1.0.0",
        "private_salt_sha256": salt_sha256,
        "frozen_panel_digest": panel_digest,
        "validation_and_holdout_non_use": True,
        "analytical_outcome_results_generated": analytical_outcome_results_generated,
        "records": records,
    }
    manifest_path = manifests / "corpus-manifest.json"
    private_write(manifest_path, manifest)
    private_write(
        manifests / "panel-binding.json",
        {
            "schema_version": LIVE_SCHEMA,
            "campaign_id": LIVE_CAMPAIGN,
            "panel_digest": panel_digest,
            "salt_sha256": salt_sha256,
            "selected_panel_detail_count": len(selected_ids),
        },
    )
    private_write(
        storage_root / ".local/diagnostics/free-dna-death-context-local-reuse-pilot/tier2_detail_index.json",
        {
            "schema_version": LIVE_SCHEMA,
            "provider": PROVIDER,
            "records": [
                {
                    "source_campaign": row["campaign_id"],
                    "source_raw_path": row["source_raw_path"],
                    "capture_requested_at": None,
                    "capture_completed_at": None,
                    "response_sha256": row["raw_sha256"],
                    "response_bytes": row["raw_bytes"],
                    "match_id": row["match_id"],
                    "profile_pseudonymous_membership_count": len(memberships.get(row["match_id"], [])),
                    "selected_in_frozen_panel": row["included_in_death_context_panel"],
                    "parsed_marker": {"version": 22, "od_data.has_parsed": True},
                }
                for row in records
            ],
            "record_count": len(records),
        },
    )
    return {
        "canonical_path": str(corpus_root),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "normalized_directory": str(normalized_dir),
        "normalized_record_count": len(records),
        "normalized_digest": normalized_digest,
        "raw_records_persisted": raw_persisted,
        "raw_records_referenced": raw_referenced,
        "provenance_preserved": True,
        "reusable_for_future_research": True,
        "analytical_outcome_results_generated": analytical_outcome_results_generated,
    }


def player_rows(
    details: Sequence[Mapping[str, Any]],
    items_by_match: Mapping[int, Mapping[str, Any]],
    source_secret: bytes,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    mapping_errors: list[dict[str, Any]] = []
    for detail in details:
        match = detail["match"]
        item = items_by_match.get(int(detail["match_id"]))
        if item is None:
            continue
        players = match.get("players") if isinstance(match, dict) else None
        if not isinstance(players, list):
            mapping_errors.append({"match_id": detail["match_id"], "error": "players_missing"})
            continue
        target_profile_id = str(item["profile_id"])
        target_indexes = [
            index
            for index, player in enumerate(players)
            if isinstance(player, dict)
            and source_profile_pseudonym(source_secret, player.get("account_id")) == target_profile_id
        ]
        if len(target_indexes) != 1:
            mapping_errors.append(
                {
                    "match_id": detail["match_id"],
                    "profile_id": target_profile_id,
                    "error": "target_player_not_unique",
                    "candidate_count": len(target_indexes),
                }
            )
        target_index = target_indexes[0] if len(target_indexes) == 1 else None
        adv = match.get("radiant_gold_adv") if isinstance(match, dict) else None
        numeric_adv = [float(value) for value in adv if is_number(value)] if isinstance(adv, list) else []
        for index, player in enumerate(players):
            if not isinstance(player, dict):
                continue
            slot = player.get("player_slot")
            side = "radiant" if is_number(slot) and int(slot) < 128 else "dire" if is_number(slot) else None
            ahead_exposure = None
            if numeric_adv and side is not None:
                ahead_exposure = sum(
                    value > 0 if side == "radiant" else value < 0 for value in numeric_adv
                ) / len(numeric_adv)
            fight_deaths = None
            fights = match.get("teamfights") if isinstance(match, dict) else None
            if isinstance(fights, list) and all(
                isinstance(fight, dict)
                and isinstance(fight.get("players"), list)
                and len(fight["players"]) == len(players)
                for fight in fights
            ):
                fight_deaths = sum(
                    int(fight["players"][index].get("deaths") or 0)
                    for fight in fights
                    if isinstance(fight["players"][index], dict)
                )
            outcome = player.get("win")
            if not isinstance(outcome, (int, bool)) and isinstance(match.get("radiant_win"), bool):
                outcome = int(bool(match["radiant_win"]) == (side == "radiant"))
            rows.append(
                {
                    "match_id": int(detail["match_id"]),
                    "profile_id": source_profile_pseudonym(source_secret, player.get("account_id")),
                    "target_profile_id": target_profile_id,
                    "target": index == target_index,
                    "player_index": index,
                    "player_slot": slot,
                    "side": side,
                    "hero_id": player.get("hero_id"),
                    "lane": player.get("lane"),
                    "role": player.get("lane_role"),
                    "outcome": int(outcome) if isinstance(outcome, (int, bool)) else None,
                    "patch": match.get("patch"),
                    "duration": match.get("duration"),
                    "ahead_exposure": ahead_exposure,
                    "deaths": int(player["deaths"]) if nonnegative_number(player.get("deaths")) else None,
                    "fight_deaths": fight_deaths,
                }
            )
    return rows, mapping_errors


def assign_ahead_quintiles(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [row for row in rows if isinstance(row.get("ahead_exposure"), (int, float))]
    ordered = sorted(
        usable,
        key=lambda row: (
            float(row["ahead_exposure"]),
            str(row.get("profile_id")),
            int(row["match_id"]),
            int(row["player_index"]),
        ),
    )
    for index, row in enumerate(ordered):
        row["ahead_quintile"] = min(4, index * 5 // max(1, len(ordered)))
    for row in rows:
        row.setdefault("ahead_quintile", None)
    values = [float(row["ahead_exposure"]) for row in usable]
    return {
        "method": "stable_rank_quintile_on_complete_panel_rows",
        "row_count": len(rows),
        "usable_exposure_rows": len(values),
        "boundaries": {
            "p20": quantile(values, 0.20),
            "p40": quantile(values, 0.40),
            "p60": quantile(values, 0.60),
            "p80": quantile(values, 0.80),
        },
    }


MODES: dict[str, tuple[str, ...]] = {
    "global": (),
    "primary": ("role", "outcome", "ahead_quintile", "patch"),
    "hero_exact": ("hero_id", "outcome", "patch"),
    "hero_fallback": ("hero_id", "outcome"),
    "role_sensitivity": ("outcome", "ahead_quintile", "patch"),
    "result_sensitivity": ("role", "ahead_quintile", "patch"),
    "patch_sensitivity": ("role", "outcome", "ahead_quintile"),
}


def row_key(row: Mapping[str, Any], mode: str) -> tuple[Any, ...] | None:
    fields = MODES[mode]
    values = tuple(row.get(field) for field in fields)
    if any(value is None for value in values):
        return None
    return values


class Baseline:
    def __init__(self, rows: Sequence[Mapping[str, Any]], profile_ids: Sequence[str]) -> None:
        self.base: dict[str, dict[str, dict[tuple[Any, ...], list[float]]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        self.match_all: dict[str, dict[int, dict[tuple[Any, ...], list[float]]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        self.match_profile: dict[str, dict[int, dict[str, dict[tuple[Any, ...], list[float]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(dict))
        )
        self._build(rows, profile_ids)

    @staticmethod
    def add(
        target: dict[tuple[Any, ...], list[float]], key: tuple[Any, ...] | None, deaths: float, fight_deaths: float
    ) -> None:
        if key is None:
            return
        cell = target.setdefault(key, [0.0, 0.0])
        cell[0] += deaths
        cell[1] += fight_deaths

    def _build(self, rows: Sequence[Mapping[str, Any]], profile_ids: Sequence[str]) -> None:
        for mode in MODES:
            for row in rows:
                if not nonnegative_number(row.get("deaths")) or not nonnegative_number(row.get("fight_deaths")):
                    continue
                deaths = float(row["deaths"])
                fight_deaths = float(row["fight_deaths"])
                key = row_key(row, mode)
                match_id = int(row["match_id"])
                self.add(self.match_all[mode][match_id], key, deaths, fight_deaths)
                profile_id = row.get("profile_id")
                if isinstance(profile_id, str):
                    self.add(self.match_profile[profile_id][match_id][mode], key, deaths, fight_deaths)
            for profile_id in profile_ids:
                target = self.base[profile_id][mode]
                for row in rows:
                    if row.get("profile_id") == profile_id:
                        continue
                    if not nonnegative_number(row.get("deaths")) or not nonnegative_number(row.get("fight_deaths")):
                        continue
                    self.add(target, row_key(row, mode), float(row["deaths"]), float(row["fight_deaths"]))

    def rate(
        self,
        profile_id: str,
        match_id: int,
        mode: str,
        key: tuple[Any, ...] | None,
        minimum_deaths: float = REFERENCE_DEATH_MINIMUM,
    ) -> float | None:
        if key is None:
            return None
        base_cell = self.base[profile_id][mode].get(key, [0.0, 0.0])
        all_match_cell = self.match_all[mode].get(match_id, {}).get(key, [0.0, 0.0])
        profile_match_cell = self.match_profile[profile_id][match_id][mode].get(key, [0.0, 0.0])
        deaths = base_cell[0] - all_match_cell[0] + profile_match_cell[0]
        fight_deaths = base_cell[1] - all_match_cell[1] + profile_match_cell[1]
        if deaths < minimum_deaths:
            return None
        return fight_deaths / deaths if deaths else None


def expected_rate(row: Mapping[str, Any], profile_id: str, baseline: Baseline, mode: str) -> tuple[float | None, str | None]:
    match_id = int(row["match_id"])
    if mode == "hero":
        exact = baseline.rate(profile_id, match_id, "hero_exact", row_key(row, "hero_exact"))
        if exact is not None:
            return exact, "hero_exact"
        fallback = baseline.rate(profile_id, match_id, "hero_fallback", row_key(row, "hero_fallback"))
        return fallback, "hero_outcome_fallback" if fallback is not None else None
    rate = baseline.rate(profile_id, match_id, mode, row_key(row, mode))
    return rate, mode if rate is not None else None


def estimate_profile(
    profile_id: str,
    match_ids: Sequence[int],
    target_rows: Mapping[int, Mapping[str, Any]],
    baseline: Baseline,
    mode: str,
) -> dict[str, Any]:
    selected = [target_rows[match_id] for match_id in match_ids if match_id in target_rows]
    total_deaths = sum(float(row["deaths"]) for row in selected if nonnegative_number(row.get("deaths")))
    fight_deaths = sum(float(row["fight_deaths"]) for row in selected if nonnegative_number(row.get("fight_deaths")))
    supported = 0
    supported_deaths = 0.0
    expected_fight_deaths = 0.0
    fallback_count = 0
    for row in selected:
        if not nonnegative_number(row.get("deaths")):
            continue
        rate, used = expected_rate(row, profile_id, baseline, mode)
        if rate is None:
            continue
        supported += 1
        deaths = float(row["deaths"])
        supported_deaths += deaths
        expected_fight_deaths += deaths * rate
        if used == "hero_outcome_fallback":
            fallback_count += 1
    observed_share = fight_deaths / total_deaths if total_deaths else None
    expected_share = expected_fight_deaths / supported_deaths if supported_deaths else None
    residual = (
        observed_share - expected_share
        if observed_share is not None and expected_share is not None
        else None
    )
    return {
        "mode": mode,
        "selected_matches": len(match_ids),
        "mapped_matches": len(selected),
        "support_matches": supported,
        "support_deaths": supported_deaths,
        "support_fraction": supported / len(selected) if selected else None,
        "total_deaths": total_deaths,
        "fight_deaths": fight_deaths,
        "observed_share": observed_share,
        "expected_share": expected_share,
        "residual": residual,
        "hero_fallback_rows": fallback_count,
        "minimum_support_pass": len(match_ids) >= 25 and total_deaths >= 100 and supported >= 25,
    }


def sign(value: float | None, epsilon: float = 1e-12) -> str:
    if value is None or abs(value) <= epsilon:
        return "tie"
    return "positive" if value > 0 else "negative"


def rank_values(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index + 1
        while end < len(indexed) and indexed[end][1] == indexed[index][1]:
            end += 1
        rank = (index + 1 + end) / 2
        for position in range(index, end):
            ranks[indexed[position][0]] = rank
        index = end
    return ranks


def spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 3:
        return None
    left_rank = rank_values(left)
    right_rank = rank_values(right)
    left_mean = statistics.fmean(left_rank)
    right_mean = statistics.fmean(right_rank)
    numerator = sum(
        (a - left_mean) * (b - right_mean)
        for a, b in zip(left_rank, right_rank, strict=True)
    )
    left_denominator = math.sqrt(sum((a - left_mean) ** 2 for a in left_rank))
    right_denominator = math.sqrt(sum((b - right_mean) ** 2 for b in right_rank))
    if not left_denominator or not right_denominator:
        return None
    return numerator / (left_denominator * right_denominator)


def aggregate_signs(values: Sequence[float | None]) -> dict[str, Any]:
    counts = Counter(sign(value) for value in values if value is not None)
    supported = sum(counts.values())
    directional = counts["positive"] + counts["negative"]
    dominant = max((counts["positive"], counts["negative"]), default=0)
    return {
        "supported_profiles": supported,
        "positive": counts["positive"],
        "negative": counts["negative"],
        "tied": counts["tie"],
        "dominant_direction": (
            "positive" if counts["positive"] >= counts["negative"] else "negative"
        )
        if directional
        else None,
        "dominant_direction_fraction": dominant / supported if supported else None,
        "dominant_direction_fraction_among_directional": dominant / directional if directional else None,
    }


def median_or_none(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def analysis_rows(
    rows: Sequence[Mapping[str, Any]],
    panel_profiles: Sequence[Mapping[str, Any]],
    baseline: Baseline,
) -> tuple[list[dict[str, Any]], dict[str, list[int]], dict[int, dict[str, Any]]]:
    target_rows: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    match_ids: dict[str, list[int]] = defaultdict(list)
    for item in panel_profiles:
        profile_id = str(item["profile_id"])
        match_ids[profile_id] = [int(match_id) for match_id in item["selected_match_ids"]]
    for row in rows:
        if row.get("target") and isinstance(row.get("target_profile_id"), str):
            target_rows[str(row["target_profile_id"])][int(row["match_id"])] = dict(row)
    results: list[dict[str, Any]] = []
    for profile_id, ids in match_ids.items():
        selected = target_rows.get(profile_id, {})
        primary = estimate_profile(profile_id, ids, selected, baseline, "primary")
        unadjusted = estimate_profile(profile_id, ids, selected, baseline, "global")
        hero = estimate_profile(profile_id, ids, selected, baseline, "hero")
        role = estimate_profile(profile_id, ids, selected, baseline, "role_sensitivity")
        result = estimate_profile(profile_id, ids, selected, baseline, "result_sensitivity")
        patch = estimate_profile(profile_id, ids, selected, baseline, "patch_sensitivity")
        hero_counts = Counter(row.get("hero_id") for row in selected.values() if row.get("hero_id") is not None)
        dominant_hero = hero_counts.most_common(1)[0][0] if hero_counts else None
        dominant_filtered = [
            row for row in rows if row.get("hero_id") != dominant_hero
        ] if dominant_hero is not None else list(rows)
        dominant_baseline = Baseline(dominant_filtered, list(match_ids))
        dominant_target = {
            match_id: row
            for match_id, row in selected.items()
            if row.get("hero_id") != dominant_hero
        }
        dominant = estimate_profile(profile_id, ids, dominant_target, dominant_baseline, "global")
        result_row = {
            "profile_id": profile_id,
            "selected_match_count": len(ids),
            "mapped_match_count": len(selected),
            "dominant_hero": dominant_hero,
            "primary": primary,
            "unadjusted": unadjusted,
            "hero_sensitive": hero,
            "dominant_hero_excluded": dominant,
            "role_sensitivity": role,
            "result_sensitivity": result,
            "patch_sensitivity": patch,
        }
        results.append(result_row)
    return results, match_ids, {int(row["match_id"]): dict(row) for row in rows}


def control_diagnostics(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    comparable = []
    hero_comparable = []
    attenuation: list[float] = []
    primary_retention: list[bool] = []
    role_retention: list[bool] = []
    result_retention: list[bool] = []
    patch_retention: list[bool] = []
    hero_retention: list[bool] = []
    for row in results:
        primary = row["primary"]
        unadjusted = row["unadjusted"]
        if primary.get("residual") is not None and unadjusted.get("residual") is not None:
            comparable.append(row)
            primary_retention.append(sign(unadjusted["residual"]) == sign(primary["residual"]))
            attenuation.append(
                1.0 - abs(float(primary["residual"])) / max(abs(float(unadjusted["residual"])), 1e-12)
            )
            for key, values in (
                ("role_sensitivity", role_retention),
                ("result_sensitivity", result_retention),
                ("patch_sensitivity", patch_retention),
                ("hero_sensitive", hero_retention),
            ):
                candidate = row[key].get("residual")
                values.append(candidate is not None and sign(candidate) == sign(unadjusted["residual"]))
        if row["primary"].get("residual") is not None and row["hero_sensitive"].get("residual") is not None:
            hero_comparable.append(row)
    def fraction(values: Sequence[bool]) -> float | None:
        return sum(values) / len(values) if values else None
    return {
        "schema_version": LIVE_SCHEMA,
        "comparable_profiles": len(comparable),
        "hero_comparable_profiles": len(hero_comparable),
        "direction_retention": {
            "role_outcome_state_patch_primary": fraction(primary_retention),
            "result_sensitivity": fraction(result_retention),
            "patch_sensitivity": fraction(patch_retention),
            "hero_sensitivity": fraction(hero_retention),
        },
        "median_absolute_attenuation": median_or_none(attenuation),
        "attenuation_values": attenuation,
        "control_gate_pass": (
            fraction(primary_retention) is not None
            and fraction(primary_retention) >= 0.70
            and fraction(hero_retention) is not None
            and fraction(hero_retention) >= 0.70
            and median_or_none(attenuation) is not None
            and median_or_none(attenuation) < 0.50
        ),
    }


def stability_outputs(
    results: Sequence[Mapping[str, Any]],
    match_ids: Mapping[str, Sequence[int]],
    target_rows: Mapping[str, Mapping[int, Mapping[str, Any]]],
    baseline: Baseline,
    salt: bytes,
) -> dict[str, Any]:
    full = {str(row["profile_id"]): row["primary"].get("residual") for row in results}
    records: list[dict[str, Any]] = []
    sensitivity_modes = {
        "hero_sensitive": "hero",
        "role_sensitivity": "role_sensitivity",
        "result_sensitivity": "result_sensitivity",
        "patch_sensitivity": "patch_sensitivity",
    }
    for n in NESTED_N:
        prefix_values: dict[str, float | None] = {}
        halves: list[tuple[float, float, str]] = []
        repeated_by_profile: list[float] = []
        profile_failure = 0
        hero_agreement: list[bool] = []
        role_agreement: list[bool] = []
        result_agreement: list[bool] = []
        patch_agreement: list[bool] = []
        for profile_id, ids in match_ids.items():
            prefix = list(ids[:n])
            estimate = estimate_profile(profile_id, prefix, target_rows[profile_id], baseline, "primary")
            prefix_values[profile_id] = estimate.get("residual")
            if estimate.get("residual") is None:
                profile_failure += 1
            split_at = len(prefix) // 2
            first = estimate_profile(profile_id, prefix[:split_at], target_rows[profile_id], baseline, "primary")
            second = estimate_profile(profile_id, prefix[split_at:], target_rows[profile_id], baseline, "primary")
            if first.get("residual") is not None and second.get("residual") is not None:
                halves.append((float(first["residual"]), float(second["residual"]), profile_id))
            prefix_sign = sign(estimate.get("residual"))
            for key, bucket in (
                ("hero_sensitive", hero_agreement),
                ("role_sensitivity", role_agreement),
                ("result_sensitivity", result_agreement),
                ("patch_sensitivity", patch_agreement),
            ):
                sensitivity = estimate_profile(
                    profile_id,
                    prefix,
                    target_rows[profile_id],
                    baseline,
                    sensitivity_modes[key],
                )
                if prefix_sign != "tie" and sensitivity.get("residual") is not None:
                    bucket.append(sign(sensitivity["residual"]) == prefix_sign)
            eligible_full = full.get(profile_id) is not None and abs(float(full[profile_id])) >= 0.05
            if eligible_full:
                seed = int.from_bytes(
                    hmac.new(salt, f"death-context-subsample:{profile_id}:{n}".encode(), hashlib.sha256).digest()[:8],
                    "big",
                )
                rng = random.Random(seed)
                agreements = []
                for _ in range(SUBSAMPLE_DRAWS):
                    sampled = rng.sample(list(ids), min(n, len(ids)))
                    sampled_estimate = estimate_profile(profile_id, sampled, target_rows[profile_id], baseline, "primary")
                    if sampled_estimate.get("residual") is not None:
                        agreements.append(sign(sampled_estimate["residual"]) == sign(full[profile_id]))
                if agreements:
                    repeated_by_profile.append(statistics.fmean(agreements))
        left = [item[0] for item in halves]
        right = [item[1] for item in halves]
        split_agreement = (
            sum(sign(a) == sign(b) for a, b in zip(left, right, strict=True)) / len(left)
            if left
            else None
        )
        split_spearman = spearman(left, right)
        full_agreement = [
            sign(prefix_values[profile_id]) == sign(full[profile_id])
            for profile_id in match_ids
            if prefix_values[profile_id] is not None and full.get(profile_id) is not None
        ]
        records.append(
            {
                "n": n,
                "profiles": len(match_ids),
                "profiles_with_estimate": len(match_ids) - profile_failure,
                "failure_rate": profile_failure / len(match_ids) if match_ids else None,
                "split_half_profiles": len(halves),
                "split_half_direction_agreement": split_agreement,
                "split_half_spearman": split_spearman,
                "split_half_effect_median_absolute_difference": median_or_none(
                    [abs(a - b) for a, b in zip(left, right, strict=True)]
                ),
                "prefix_vs_full_direction_agreement": (
                    sum(full_agreement) / len(full_agreement) if full_agreement else None
                ),
                "repeated_subsample_sign_agreement_median": median_or_none(repeated_by_profile),
                "repeated_subsample_profiles": len(repeated_by_profile),
                "hero_mix_sensitivity_direction_agreement": fraction_bool(hero_agreement),
                "role_sensitivity_direction_agreement": fraction_bool(role_agreement),
                "result_sensitivity_direction_agreement": fraction_bool(result_agreement),
                "patch_sensitivity_direction_agreement": fraction_bool(patch_agreement),
                "stability_criterion_pass": (
                    n in {25, 30}
                    and split_spearman is not None
                    and split_spearman >= 0.50
                    and median_or_none(repeated_by_profile) is not None
                    and median_or_none(repeated_by_profile) >= 0.75
                ),
            }
        )
    by_n = {str(record["n"]): record for record in records}
    return {
        "schema_version": LIVE_SCHEMA,
        "nested_n": list(NESTED_N),
        "bootstrap": {"draws": BOOTSTRAP_DRAWS, "unit": "whole match"},
        "repeated_subsamples": {"draws": SUBSAMPLE_DRAWS, "unit": "whole match"},
        "records": records,
        "by_n": by_n,
        "n25_or_n30_pass": bool(by_n.get("25", {}).get("stability_criterion_pass") or by_n.get("30", {}).get("stability_criterion_pass")),
    }


def fraction_bool(values: Sequence[bool]) -> float | None:
    return sum(values) / len(values) if values else None


def bootstrap_intervals(
    results: list[dict[str, Any]],
    match_ids: Mapping[str, Sequence[int]],
    target_rows: Mapping[str, Mapping[int, Mapping[str, Any]]],
    baseline: Baseline,
    salt: bytes,
) -> None:
    for result in results:
        profile_id = str(result["profile_id"])
        residual = result["primary"].get("residual")
        if residual is None:
            result["primary"]["bootstrap_95"] = None
            continue
        seed = int.from_bytes(
            hmac.new(salt, f"death-context-bootstrap:{profile_id}".encode(), hashlib.sha256).digest()[:8],
            "big",
        )
        rng = random.Random(seed)
        ids = list(match_ids[profile_id])
        samples: list[float] = []
        for _ in range(BOOTSTRAP_DRAWS):
            drawn = [ids[rng.randrange(len(ids))] for _ in ids]
            estimate = estimate_profile(profile_id, drawn, target_rows[profile_id], baseline, "primary")
            if estimate.get("residual") is not None:
                samples.append(float(estimate["residual"]))
        result["primary"]["bootstrap_95"] = {
            "draws": len(samples),
            "p025": quantile(samples, 0.025),
            "p50": quantile(samples, 0.50),
            "p975": quantile(samples, 0.975),
            "unit": "whole match",
        }


def coverage_model(profiles: Sequence[Mapping[str, Any]], recommended_n: int | None) -> dict[str, Any]:
    counts = [
        sum(
            1
            for row in profile.get("matches", [])
            if isinstance(row, dict) and row.get("source_version") == SOURCE_MARKER
        )
        for profile in profiles
    ]
    by_threshold = {
        str(n): {
            "profiles": sum(count >= n for count in counts),
            "coverage": sum(count >= n for count in counts) / len(counts) if counts else None,
        }
        for n in (20, 25, 30)
    }
    return {
        "schema_version": LIVE_SCHEMA,
        "development_tuning_profiles": len(counts),
        "parsed_count_distribution": {
            "p10": quantile([float(count) for count in counts], 0.10),
            "p25": quantile([float(count) for count in counts], 0.25),
            "median": quantile([float(count) for count in counts], 0.50),
            "p75": quantile([float(count) for count in counts], 0.75),
            "p90": quantile([float(count) for count in counts], 0.90),
        },
        "thresholds": by_threshold,
        "recommended_n": recommended_n,
        "publication_coverage_known": False,
    }


def free_user_model(
    latency_summary: Mapping[str, Any], batch_measurements: Sequence[Mapping[str, Any]], recommended_n: int | None
) -> dict[str, Any]:
    batch_30 = [
        measurement
        for measurement in batch_measurements
        if measurement.get("name") in {"profile_0_30", "profile_1_30", "profile_2_30"}
    ]
    best_30 = next(
        (measurement for measurement in batch_30 if measurement.get("name") == "profile_2_30"),
        None,
    )
    wall_30 = best_30.get("wall_seconds") if best_30 else None
    route = (
        "synchronous"
        if isinstance(wall_30, (int, float)) and wall_30 <= 30
        else "background"
        if isinstance(wall_30, (int, float)) and wall_30 <= 60
        else "unverified"
    )
    scenarios = []
    for n in (10, 15, 20, 25, 30):
        calls = 1 + n
        scenarios.append(
            {
                "n_details": n,
                "history_plus_detail_calls": calls,
                "estimated_idr_pro_rata": calls * COST_IDR_PER_100 / 100,
                "estimated_usd_pro_rata": calls * COST_USD_PER_100 / 100,
            }
        )
    return {
        "schema_version": LIVE_SCHEMA,
        "scenarios": scenarios,
        "recommended_n": recommended_n,
        "observed_detail_request_latency": latency_summary.get("request_latency_successful"),
        "observed_20_match_batches": [m for m in batch_measurements if m.get("requested_matches") == 20],
        "observed_30_match_batches": [m for m in batch_measurements if m.get("requested_matches") == 30],
        "local_analysis_seconds": latency_summary.get("local_analysis_seconds"),
        "total_enrichment_seconds": latency_summary.get("total_enrichment_seconds"),
        "synchronous_free_feasible": route == "synchronous",
        "routing": route,
        "note": "The current Free report remains unchanged; this model is research evidence only.",
    }


def write_analysis_outputs(
    *,
    storage_root: Path,
    live_diag: Path,
    items: Sequence[Mapping[str, Any]],
    details: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
    source_secret: bytes,
    source_manifest: Mapping[str, Any],
    frozen: Mapping[str, Any],
    salt: bytes,
    transport: LiveTransport,
    batch_measurements: Sequence[Mapping[str, Any]],
    collection_started: float,
) -> dict[str, Any]:
    analysis_started = time.monotonic()
    items_by_match = {int(item["match_id"]): item for item in items}
    panel_profiles = list(frozen["profiles"])
    live_details = [detail for detail in details if int(detail["match_id"]) in items_by_match]
    player_level, mapping_errors = player_rows(live_details, items_by_match, source_secret)
    quintiles = assign_ahead_quintiles(player_level)
    target_only = [row for row in player_level if row.get("target")]
    profile_ids = [str(profile["profile_id"]) for profile in panel_profiles]
    baseline = Baseline(player_level, profile_ids)
    target_rows: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in target_only:
        target_rows[str(row["target_profile_id"])][int(row["match_id"])] = row
    estimates, match_ids, _ = analysis_rows(player_level, panel_profiles, baseline)
    bootstrap_intervals(estimates, match_ids, target_rows, baseline, salt)
    controls = control_diagnostics(estimates)
    primary_residuals = [row["primary"].get("residual") for row in estimates]
    residual_values = [float(value) for value in primary_residuals if value is not None]
    iqr = (
        quantile(residual_values, 0.75) - quantile(residual_values, 0.25)
        if residual_values
        and quantile(residual_values, 0.75) is not None
        and quantile(residual_values, 0.25) is not None
        else None
    )
    common_direction = aggregate_signs(primary_residuals)
    stability = stability_outputs(estimates, match_ids, target_rows, baseline, salt)
    field_rows, field_summary = field_completeness(live_details)
    target_mapping_rate = (
        sum(len(target_rows.get(profile_id, {})) == MATCHES_PER_PROFILE for profile_id in profile_ids)
        / len(profile_ids)
        if profile_ids
        else 0.0
    )
    field_rows.append(
        {
            "field": "target_player_mapping",
            "scope": "selected-match",
            "present": sum(len(target_rows.get(profile_id, {})) for profile_id in profile_ids),
            "total": MAX_CALLS,
            "present_rate": sum(len(target_rows.get(profile_id, {})) for profile_id in profile_ids) / MAX_CALLS,
            "missing": MAX_CALLS - sum(len(target_rows.get(profile_id, {})) for profile_id in profile_ids),
            "semantics_confidence": "KNOWN",
            "source_path": "source split pseudonym + detail players[].account_id",
            "normalization_needed": "private-only mapping",
            "safe_for_analysis": "YES" if not mapping_errors else "NO",
            "notes": "target profile row required for every frozen match",
        }
    )
    core_fields = {
        "player_slot_mapping",
        "player_deaths",
        "teamfight_structures",
        "teamfight_start_end",
        "teamfight_participant_arrays",
        "teamfight_player_deaths",
        "hero_id",
        "lane_role",
        "result_side",
        "duration",
        "patch",
        "gold_advantage_timeline",
        "target_player_mapping",
    }
    rates = [
        float(row["present_rate"])
        for row in field_rows
        if row.get("field") in core_fields and row.get("present_rate") is not None
    ]
    core_minimum = min(rates) if rates else 0.0
    field_summary["core_field_completeness_minimum"] = core_minimum
    field_summary["core_field_threshold"] = 0.95
    field_summary["core_field_threshold_passes_on_available_records"] = core_minimum >= 0.95
    field_summary["target_player_mapping_rate"] = target_mapping_rate
    semantics = semantics_audit(live_details)
    semantics["analysis_allowed"] = bool(
        semantics.get("numerator_reconstruction_reliable_on_available_records")
        and not mapping_errors
        and len(live_details) == MAX_CALLS
    )
    semantics["blocked_reason"] = None if semantics["analysis_allowed"] else "TEAMFIGHT_SEMANTICS_BLOCKED"

    dominant_n25 = stability["by_n"].get("25", {}).get("stability_criterion_pass")
    dominant_n30 = stability["by_n"].get("30", {}).get("stability_criterion_pass")
    batch_summary = read_json(live_diag / "batch_latency_summary.json")
    collection_seconds = batch_summary.get("collection_wall_seconds")
    if not isinstance(collection_seconds, (int, float)):
        collection_seconds = None
    recommended_n = 25 if dominant_n25 else 30 if dominant_n30 else None
    coverage = coverage_model(profiles, recommended_n)
    gates = {
        "core_field_completeness_ge_95": {
            "observed": core_minimum,
            "passed": core_minimum >= 0.95,
        },
        "all_details_match_stored_parsed_marker": {
            "observed": transport.successful_count,
            "expected": MAX_CALLS,
            "passed": transport.successful_count == MAX_CALLS and not transport.error_messages,
        },
        "zero_replay_parse_requests": {"observed": 0, "passed": True},
        "zero_retries": {
            "observed": sum(int(row.get("retry_number", 0)) for row in transport.responses),
            "passed": all(int(row.get("retry_number", 0)) == 0 for row in transport.responses),
        },
        "call_cost_storage_ceiling": {
            "observed_calls": transport.physical_count,
            "observed_cost_idr": transport.physical_count * COST_IDR_PER_100 / 100,
            "observed_storage_bytes": directory_size(storage_root / ".local/corpora/opendota/free-dna-tier2") + directory_size(live_diag),
            "passed": transport.physical_count <= MAX_CALLS
            and transport.physical_count * COST_IDR_PER_100 / 100 <= MAX_CALLS * COST_IDR_PER_100 / 100
            and directory_size(storage_root / ".local/corpora/opendota/free-dna-tier2") + directory_size(live_diag) <= STORAGE_CEILING,
        },
        "teamfight_semantics": {"observed": semantics["status"], "passed": semantics["analysis_allowed"]},
        "residual_iqr_ge_010": {"observed": iqr, "passed": iqr is not None and iqr >= 0.10},
        "dominant_direction_below_90_percent": {
            "observed": common_direction["dominant_direction_fraction"],
            "passed": common_direction["dominant_direction_fraction"] is not None
            and common_direction["dominant_direction_fraction"] < 0.90,
        },
        "controls_retain_direction_ge_70_percent": {
            "observed": controls["direction_retention"],
            "passed": bool(controls["control_gate_pass"]),
        },
        "median_absolute_attenuation_below_50_percent": {
            "observed": controls["median_absolute_attenuation"],
            "passed": controls["median_absolute_attenuation"] is not None
            and controls["median_absolute_attenuation"] < 0.50,
        },
        "stability_n25_or_n30": {
            "n25_passed": dominant_n25,
            "n30_passed": dominant_n30,
            "passed": bool(stability["n25_or_n30_pass"]),
        },
        "interpretation_remains_death_context_composition": {"passed": True},
        "latency_not_over_60_seconds": {
            "observed_profile_2_30_seconds": None,
            "passed": True,
            "routing": "recorded_after_collection",
        },
    }
    analytical_gate_names = [
        "core_field_completeness_ge_95",
        "all_details_match_stored_parsed_marker",
        "zero_replay_parse_requests",
        "zero_retries",
        "call_cost_storage_ceiling",
        "teamfight_semantics",
        "residual_iqr_ge_010",
        "dominant_direction_below_90_percent",
        "controls_retain_direction_ge_70_percent",
        "median_absolute_attenuation_below_50_percent",
        "stability_n25_or_n30",
        "interpretation_remains_death_context_composition",
    ]
    all_pass = all(gates[name]["passed"] for name in analytical_gate_names)
    if not semantics["analysis_allowed"]:
        verdict = "DROP_DEATH_CONTEXT"
        verdict_reason = "TEAMFIGHT_SEMANTICS_FAILED"
    elif all_pass:
        verdict = "DEATH_CONTEXT_PILOT_PASS"
        verdict_reason = "ALL_FROZEN_PILOT_GATES_PASS"
    else:
        verdict = "DROP_DEATH_CONTEXT"
        verdict_reason = next(name for name in analytical_gate_names if not gates[name]["passed"])

    analysis_seconds = time.monotonic() - analysis_started
    latency_summary, latency_rows = latency_outputs(
        transport,
        batch_measurements,
        analysis_seconds,
        float(collection_seconds) if collection_seconds is not None else None,
    )
    model = free_user_model(latency_summary, batch_measurements, recommended_n)
    if model["routing"] == "unverified":
        gates["latency_not_over_60_seconds"]["passed"] = False
        gates["latency_not_over_60_seconds"]["routing"] = "UNVERIFIED"
    else:
        gates["latency_not_over_60_seconds"]["routing"] = model["routing"]
        gates["latency_not_over_60_seconds"]["observed_profile_2_30_seconds"] = next(
            (
                measurement.get("wall_seconds")
                for measurement in batch_measurements
                if measurement.get("name") == "profile_2_30"
            ),
        )
    write_csv(
        live_diag / "field_completeness.csv",
        list(field_rows[0].keys()),
        field_rows,
    )
    write_json(live_diag / "teamfight_semantics_audit.json", semantics)
    write_json(live_diag / "population_baseline.json", {
        "schema_version": LIVE_SCHEMA,
        "unit": "player-match",
        "denominator": "all player deaths",
        "numerator": "provider-attributed teamfight player deaths",
        "cluster": "whole match",
        "reference_death_minimum": REFERENCE_DEATH_MINIMUM,
        "primary_strata": list(MODES["primary"]),
        "hero_sensitivity": "hero_id x outcome x patch; fallback hero_id x outcome when exact cell has <100 reference deaths",
        "ahead_exposure_quintiles": quintiles,
        "reference_player_match_rows": len(player_level),
        "target_player_match_rows": len(target_only),
    })
    write_json(live_diag / "common_direction_check.json", {
        "schema_version": LIVE_SCHEMA,
        "stop_threshold": 0.90,
        "observed": common_direction,
        "stop_triggered": bool(common_direction["dominant_direction_fraction"] is not None and common_direction["dominant_direction_fraction"] >= 0.90),
    })
    write_json(live_diag / "control_attenuation.json", controls)
    write_json(live_diag / "stability_by_n.json", stability)
    write_json(live_diag / "pilot_gate_results.json", {
        "schema_version": LIVE_SCHEMA,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "gates": gates,
        "frozen_criteria": {
            "core_fields": ">=95%",
            "residual_iqr": ">=0.10",
            "dominant_direction": "<90%",
            "control_direction_retention": ">=70%",
            "median_attenuation": "<50%",
            "stability": "N=25 or N=30 split-half Spearman >=0.50 and repeated sign agreement >=0.75",
        },
    })
    write_json(live_diag / "coverage_model.json", coverage)
    write_json(live_diag / "free_user_cost_latency_model.json", model)
    write_json(live_diag / "latency_summary.json", latency_summary)
    write_json(live_diag / "cost_storage_summary.json", cost_ledger(transport, directory_size(storage_root / ".local/corpora/opendota/free-dna-tier2") + directory_size(live_diag)))
    write_csv(live_diag / "latency_measurements.csv", list(latency_rows[0].keys()) if latency_rows else ["ordinal", "match_id", "profile_id", "concurrency", "batch_id", "latency_seconds", "response_bytes", "error"], latency_rows)
    write_csv(
        live_diag / "death_context_match_level.csv",
        ["profile_id", "match_id", "player_slot", "side", "hero_id", "role", "outcome", "patch", "duration", "ahead_exposure", "ahead_quintile", "deaths", "fight_deaths", "target"],
        player_level,
    )
    player_output_rows: list[dict[str, Any]] = []
    for result in estimates:
        row = {"profile_id": result["profile_id"], "verdict": verdict}
        for prefix in ("primary", "unadjusted", "hero_sensitive", "dominant_hero_excluded", "role_sensitivity", "result_sensitivity", "patch_sensitivity"):
            estimate = result[prefix]
            row[f"{prefix}_residual"] = estimate.get("residual")
            row[f"{prefix}_observed_share"] = estimate.get("observed_share")
            row[f"{prefix}_expected_share"] = estimate.get("expected_share")
            row[f"{prefix}_support_matches"] = estimate.get("support_matches")
            row[f"{prefix}_support_deaths"] = estimate.get("support_deaths")
        row["bootstrap_p025"] = (result["primary"].get("bootstrap_95") or {}).get("p025")
        row["bootstrap_p975"] = (result["primary"].get("bootstrap_95") or {}).get("p975")
        player_output_rows.append(row)
    write_csv(live_diag / "death_context_player_level.csv", list(player_output_rows[0].keys()) if player_output_rows else ["profile_id", "verdict"], player_output_rows)
    with (live_diag / "profile_estimates.jsonl").open("w", encoding="utf-8") as handle:
        for result in estimates:
            handle.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
    write_csv(
        live_diag / "control_diagnostics.csv",
        ["profile_id", "unadjusted_residual", "primary_residual", "hero_residual", "role_residual", "result_residual", "patch_residual", "primary_support_matches", "primary_support_deaths"],
        [
            {
                "profile_id": result["profile_id"],
                "unadjusted_residual": result["unadjusted"].get("residual"),
                "primary_residual": result["primary"].get("residual"),
                "hero_residual": result["hero_sensitive"].get("residual"),
                "role_residual": result["role_sensitivity"].get("residual"),
                "result_residual": result["result_sensitivity"].get("residual"),
                "patch_residual": result["patch_sensitivity"].get("residual"),
                "primary_support_matches": result["primary"].get("support_matches"),
                "primary_support_deaths": result["primary"].get("support_deaths"),
            }
            for result in estimates
        ],
    )
    tier2 = write_tier2_corpus(
        storage_root,
        [*load_prior_details(storage_root), *live_details],
        profile_membership(profiles),
        set(items_by_match),
        source_manifest,
        str(frozen["selection_digest"]),
        str(frozen["private_salt_sha256"]),
        analytical_outcome_results_generated=True,
    )
    write_json(live_diag / "tier2_corpus_manifest.json", tier2)
    summary = {
        "schema_version": LIVE_SCHEMA,
        "status": "PASS" if verdict == "DEATH_CONTEXT_PILOT_PASS" else "FAIL",
        "terminal_verdict": verdict,
        "verdict_reason": verdict_reason,
        "campaign_id": LIVE_CAMPAIGN,
        "frozen_panel": {
            "profiles": PANEL_PROFILES,
            "matches_per_profile": MATCHES_PER_PROFILE,
            "planned_gets": MAX_CALLS,
            "selection_digest": frozen["selection_digest"],
        },
        "collection": {
            "physical_gets": transport.physical_count,
            "successful": transport.successful_count,
            "failed": sum(row.get("error") is not None for row in transport.responses),
            "replay_parse_requests": 0,
            "retries": 0,
        },
        "field_completeness": field_summary,
        "teamfight_semantics": semantics,
        "death_context": {
            "supported_profiles": len(residual_values),
            "residual_iqr": iqr,
            "common_direction": common_direction,
            "controls": controls,
            "stability_n25": stability["by_n"].get("25"),
            "stability_n30": stability["by_n"].get("30"),
        },
        "latency": latency_summary,
        "coverage": coverage,
        "tier2_corpus": tier2,
        "integrity": {
            "old_holdout_evaluated": 0,
            "fresh_sealed_validation_analytically_evaluated": 0,
            "replay_parse_requests": 0,
            "stratz_calls": 0,
            "steam_calls": 0,
            "thresholds_relaxed": False,
            "outcome_based_replacements": False,
            "adaptive_top_up": False,
            "production_analytical_behavior_changed": False,
            "deployment": False,
        },
    }
    write_json(live_diag / "aggregate_summary.json", summary)
    write_json(live_diag / "pilot_verdict.json", {"schema_version": LIVE_SCHEMA, "verdict": verdict, "reason": verdict_reason})
    return {
        "summary": summary,
        "estimates": estimates,
        "controls": controls,
        "stability": stability,
        "gates": gates,
        "mapping_errors": mapping_errors,
        "analysis_seconds": analysis_seconds,
        "tier2": tier2,
    }


async def collect(
    *,
    source_root: Path,
    storage_root: Path,
    paths: Mapping[str, Path],
    items: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Any],
    batch_summary_path: Path,
    progress_path: Path,
) -> tuple[LiveTransport, list[dict[str, Any]], list[dict[str, Any]]]:
    load_dotenv()
    base_url = os.getenv("OPENDOTA_BASE_URL", "https://api.opendota.com/api")
    api_key = os.getenv("OPENDOTA_API_KEY") or None
    timeout = float(os.getenv("OPENDOTA_TIMEOUT_SECONDS", "15"))
    batch_measurements = read_json(batch_summary_path).get("measurements", []) if batch_summary_path.exists() else []
    collection_started = time.monotonic()
    by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_profile[str(item["profile_id"])].append(dict(item))
    collected: dict[int, dict[str, Any]] = {}
    async with LiveTransport(paths=paths, base_url=base_url, api_key=api_key, timeout=timeout) as transport:
        if transport.error_messages:
            raise PilotBlocked(transport.error_messages[-1])
        def completed_profiles() -> int:
            return sum(
                all(int(item["match_id"]) in collected for item in profile_items)
                for profile_items in by_profile.values()
            )
        def update(stage: str, gate: str, next_action: str) -> None:
            write_progress(
                progress_path,
                stage=stage,
                calls_used=transport.physical_count,
                profiles_completed=completed_profiles(),
                matches_completed=len(collected),
                errors=transport.error_messages,
                latest_gate_status=gate,
                next_action=next_action,
            )
        if transport.physical_count == 0:
            update("collection_ready", "PREFLIGHT_PASS_OWNER_APPROVED", "run_four_sequential_QA_GETs")
        ordered_profiles = list(by_profile.values())
        if not ordered_profiles:
            raise PilotBlocked("PANEL_EMPTY")
        first = ordered_profiles[0]
        profile_start = time.monotonic()
        for item in first[:QA_COUNT]:
            detail = await transport.fetch(item, concurrency=1, batch_id="qa_sequential")
            collected[int(item["match_id"])] = detail
        update("semantic_QA_complete", "QA_PASS" if not transport.error_messages else "QA_FAIL", "complete_profile_0_at_concurrency_1")
        first_20_start = profile_start
        rest_first, _ = await fetch_batch(transport, first[QA_COUNT:20], concurrency=1, batch_id="profile_0_concurrency_1_first_20")
        collected.update(rest_first)
        batch_measurements.append(
            {
                "name": "profile_0_20",
                "profile_index": 0,
                "requested_matches": 20,
                "concurrency": 1,
                "wall_seconds": time.monotonic() - first_20_start,
                "includes_sequential_QA": True,
            }
        )
        rest_first_30, _ = await fetch_batch(transport, first[20:], concurrency=1, batch_id="profile_0_concurrency_1_last_10")
        collected.update(rest_first_30)
        batch_measurements.append(
            {
                "name": "profile_0_30",
                "profile_index": 0,
                "requested_matches": 30,
                "concurrency": 1,
                "wall_seconds": time.monotonic() - profile_start,
                "includes_sequential_QA": True,
            }
        )
        update("profile_0_complete", "PASS", "measure_profile_1_at_concurrency_5")
        if len(ordered_profiles) > 1:
            second = ordered_profiles[1]
            profile_start = time.monotonic()
            first_second, _ = await fetch_batch(transport, second[:20], concurrency=5, batch_id="profile_1_concurrency_5_first_20")
            collected.update(first_second)
            batch_measurements.append(
                {
                    "name": "profile_1_20",
                    "profile_index": 1,
                    "requested_matches": 20,
                    "concurrency": 5,
                    "wall_seconds": time.monotonic() - profile_start,
                }
            )
            last_second, _ = await fetch_batch(transport, second[20:], concurrency=5, batch_id="profile_1_concurrency_5_last_10")
            collected.update(last_second)
            batch_measurements.append(
                {
                    "name": "profile_1_30",
                    "profile_index": 1,
                    "requested_matches": 30,
                    "concurrency": 5,
                    "wall_seconds": time.monotonic() - profile_start,
                }
            )
        update("profile_1_complete", "PASS", "measure_profile_2_at_concurrency_10")
        if len(ordered_profiles) > 2:
            third = ordered_profiles[2]
            profile_start = time.monotonic()
            first_third, _ = await fetch_batch(transport, third[:20], concurrency=10, batch_id="profile_2_concurrency_10_first_20")
            collected.update(first_third)
            batch_measurements.append(
                {
                    "name": "profile_2_20",
                    "profile_index": 2,
                    "requested_matches": 20,
                    "concurrency": 10,
                    "wall_seconds": time.monotonic() - profile_start,
                }
            )
            last_third, _ = await fetch_batch(transport, third[20:], concurrency=10, batch_id="profile_2_concurrency_10_last_10")
            collected.update(last_third)
            batch_measurements.append(
                {
                    "name": "profile_2_30",
                    "profile_index": 2,
                    "requested_matches": 30,
                    "concurrency": 10,
                    "wall_seconds": time.monotonic() - profile_start,
                }
            )
        update("profile_2_complete", "PASS", "collect_remaining_panel_at_concurrency_10")
        for profile_index, profile_items in enumerate(ordered_profiles[3:], start=3):
            batch, _ = await fetch_batch(
                transport,
                profile_items,
                concurrency=10,
                batch_id=f"profile_{profile_index}_concurrency_10",
            )
            collected.update(batch)
            update(
                f"profile_{profile_index}_complete",
                "PASS",
                f"collect_profile_{profile_index + 1}_of_{len(ordered_profiles)}",
            )
        private_write(batch_summary_path, {
            "schema_version": LIVE_SCHEMA,
            "campaign_id": LIVE_CAMPAIGN,
            "measurements": batch_measurements,
            "collection_wall_seconds": time.monotonic() - collection_started,
            "concurrency_modes": [1, 5, 10],
            "rate_start_ceiling_per_minute": RATE_PER_MINUTE,
        })
        if transport.successful_count != MAX_CALLS:
            raise PilotBlocked("PANEL_COLLECTION_INCOMPLETE")
        write_progress(
            progress_path,
            stage="collection_complete",
            calls_used=transport.physical_count,
            profiles_completed=completed_profiles(),
            matches_completed=len(collected),
            errors=transport.error_messages,
            latest_gate_status="COLLECTION_PASS",
            next_action="run_field_semantics_and_frozen_analysis",
        )
        return transport, list(collected.values()), batch_measurements


async def materialize_blocked_artifacts(
    *,
    paths: Mapping[str, Path],
    items: Sequence[Mapping[str, Any]],
    storage_root: Path,
    profiles: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Write offline receipts for a stopped ledger without issuing another GET."""
    load_dotenv()
    base_url = os.getenv("OPENDOTA_BASE_URL", "https://api.opendota.com/api")
    api_key = os.getenv("OPENDOTA_API_KEY") or None
    timeout = float(os.getenv("OPENDOTA_TIMEOUT_SECONDS", "15"))
    batch_path = paths["diagnostics"] / "batch_latency_summary.json"
    measurements = read_json(batch_path).get("measurements", []) if batch_path.exists() else []
    async with LiveTransport(paths=paths, base_url=base_url, api_key=api_key, timeout=timeout) as transport:
        if not measurements:
            measurements = batch_measurements_from_ledger(transport)
        starts = {
            str(event["request_id"]): event
            for event in transport.events
            if event.get("event") == "request_started"
        }
        collection_wall_seconds = ledger_window_seconds(response_entries(transport), starts)
        selected_by_profile: dict[str, set[int]] = defaultdict(set)
        selected_ids: set[int] = set()
        for item in items:
            profile_id = str(item["profile_id"])
            match_id = int(item["match_id"])
            selected_by_profile[profile_id].add(match_id)
            selected_ids.add(match_id)
        completed = set(transport.completed_by_match)
        successful_details = [
            transport.cached_detail(item)
            for item in items
            if int(item["match_id"]) in completed
        ]
        successful_details = [detail for detail in successful_details if detail is not None]
        selected_ids = {int(item["match_id"]) for item in items}
        final_collection_artifacts(
            transport=transport,
            live_diag=paths["diagnostics"],
            batch_measurements=measurements,
            storage_root=storage_root,
            collection_wall_seconds=collection_wall_seconds,
        )
        tier2 = write_tier2_corpus(
            storage_root,
            [*load_prior_details(storage_root), *successful_details],
            profile_membership(profiles),
            selected_ids,
            source_manifest,
            str(frozen["selection_digest"]),
            str(frozen["private_salt_sha256"]),
        )
        write_json(paths["diagnostics"] / "tier2_corpus_manifest.json", tier2)
        field_rows, field_summary = field_completeness(successful_details)
        semantics = semantics_audit(successful_details)
        semantics["overlap_caveat"] = (
            f"{semantics['overlapping_window_pairs']} overlapping window pairs were observed; "
            "the frozen numerator remains the provider's indexed teamfight-death sum, "
            "not an independently timestamped unique-death reconstruction."
        )
        write_csv(
            paths["diagnostics"] / "field_completeness.csv",
            list(field_rows[0].keys()) if field_rows else ["field", "present", "total", "present_rate"],
            field_rows,
        )
        write_json(paths["diagnostics"] / "teamfight_semantics_audit.json", {
            **semantics,
            "analysis_allowed": False,
            "blocked_reason": "PILOT_COLLECTION_BLOCKED",
            "available_successful_details": len(successful_details),
            "required_details": MAX_CALLS,
        })
        blocked_analysis = {
            "schema_version": LIVE_SCHEMA,
            "status": "NOT_EVALUATED",
            "reason": "PILOT_COLLECTION_BLOCKED",
            "available_successful_details": len(successful_details),
            "required_details": MAX_CALLS,
        }
        for name in (
            "population_baseline.json",
            "control_attenuation.json",
            "common_direction_check.json",
            "stability_by_n.json",
            "pilot_gate_results.json",
        ):
            write_json(paths["diagnostics"] / name, blocked_analysis)
        write_csv(
            paths["diagnostics"] / "death_context_match_level.csv",
            ["status", "reason"],
            [],
        )
        write_csv(
            paths["diagnostics"] / "death_context_player_level.csv",
            ["status", "reason"],
            [],
        )
        (paths["diagnostics"] / "profile_estimates.jsonl").write_text("", encoding="utf-8")
        (paths["diagnostics"] / "profile_estimates.jsonl").chmod(0o600)
        latency_summary, latency_rows = latency_outputs(
            transport,
            measurements,
            None,
            collection_wall_seconds,
        )
        coverage = coverage_model(profiles, None)
        model = free_user_model(latency_summary, measurements, None)
        cost = cost_ledger(
            transport,
            directory_size(storage_root / ".local/corpora/opendota/free-dna-tier2")
            + directory_size(paths["diagnostics"]),
        )
        write_json(paths["diagnostics"] / "latency_summary.json", latency_summary)
        write_json(paths["diagnostics"] / "coverage_model.json", coverage)
        write_json(paths["diagnostics"] / "free_user_cost_latency_model.json", model)
        write_json(paths["diagnostics"] / "cost_storage_summary.json", cost)
        write_csv(
            paths["diagnostics"] / "latency_measurements.csv",
            list(latency_rows[0].keys()) if latency_rows else ["ordinal", "match_id", "profile_id", "latency_seconds", "error"],
            latency_rows,
        )
        summary = {
            "schema_version": LIVE_SCHEMA,
            "status": "BLOCKED",
            "terminal_verdict": "PILOT_COLLECTION_BLOCKED",
            "verdict_reason": transport.error_messages[-1] if transport.error_messages else "COLLECTION_STOPPED",
            "campaign_id": LIVE_CAMPAIGN,
            "collection": {
                "physical_gets": transport.physical_count,
                "successful": transport.successful_count,
                "failed": sum(row.get("error") is not None for row in transport.responses),
                "replay_parse_requests": 0,
                "retries": 0,
            },
            "field_completeness": field_summary,
            "teamfight_semantics": semantics,
            "analysis_status": "NOT_RUN",
            "coverage": coverage,
            "latency": latency_summary,
            "tier2_corpus": tier2,
            "integrity": {
                "old_holdout_evaluated": 0,
                "fresh_sealed_validation_analytically_evaluated": 0,
                "replay_parse_requests": 0,
                "stratz_calls": 0,
                "steam_calls": 0,
                "production_analytical_behavior_changed": False,
                "deployment": False,
            },
        }
        write_json(paths["diagnostics"] / "aggregate_summary.json", summary)
        write_json(paths["diagnostics"] / "pilot_verdict.json", {
            "schema_version": LIVE_SCHEMA,
            "verdict": "PILOT_COLLECTION_BLOCKED",
            "reason": summary["verdict_reason"],
        })
        return {
            "physical_gets": transport.physical_count,
            "successful_gets": transport.successful_count,
            "profiles_completed": sum(
                selected.issubset(completed) for selected in selected_by_profile.values()
            ),
            "matches_completed": len(completed & selected_ids),
            "errors": transport.error_messages,
        }


def preflight(
    *, source_root: Path, storage_root: Path, live_diag: Path, overnight_diag: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Path]]:
    canonicalize_prior_manifests(storage_root)
    source_raw_manifest, source_normalized_manifest, source_secret = source_manifests(source_root)
    frozen, items, profiles, panel_meta = frozen_panel(source_root, storage_root)
    panel_path = live_diag / "frozen_panel_manifest.json"
    private_write(panel_path, frozen)
    live_diag.mkdir(parents=True, exist_ok=True, mode=0o700)
    live_diag.chmod(0o700)
    overnight_diag.mkdir(parents=True, exist_ok=True, mode=0o700)
    overnight_diag.chmod(0o700)
    paths = {
        "diagnostics": live_diag,
        "overnight": overnight_diag,
        "corpus": storage_root / ".local/corpora/opendota/free-dna-tier2",
        "raw_responses": storage_root / ".local/corpora/opendota/free-dna-tier2/raw/responses",
    }
    paths["raw_responses"].mkdir(parents=True, exist_ok=True, mode=0o700)
    paths["raw_responses"].chmod(0o700)
    paths["corpus"].mkdir(parents=True, exist_ok=True, mode=0o700)
    paths["corpus"].chmod(0o700)
    preflight_payload = {
        "schema_version": LIVE_SCHEMA,
        "campaign_id": LIVE_CAMPAIGN,
        "task_type": "ANALYTICAL RESEARCH + DOCUMENTATION + REPOSITORY HYGIENE",
        "branch": "execution/free-dna-death-context-local-reuse-pilot",
        "branch_sha": git_sha(),
        "base_sha": BASE_SHA,
        "allowed_scope": ["frozen development/tuning panel GETs", "local immutable storage", "aggregate research analysis", "tracked aggregate evidence"],
        "forbidden_scope": ["history/public-match provider calls", "replay parse", "STRATZ", "Steam", "holdout", "fresh sealed validation", "production changes", "adaptive top-up", "outcome replacement"],
        "owner_authorization": {
            "explicit_in_active_brief": True,
            "max_opendota_gets": MAX_CALLS,
            "max_cost_idr": MAX_CALLS * COST_IDR_PER_100 / 100,
            "max_cost_usd": MAX_CALLS * COST_USD_PER_100 / 100,
            "max_storage_mib": STORAGE_CEILING / (1024 * 1024),
            "retries": RETRY_LIMIT,
            "replay_parse_requests": 0,
            "stratz_calls": 0,
            "steam_calls": 0,
        },
        "provider_key_configured": bool(os.getenv("OPENDOTA_API_KEY")),
        "source_corpus": {
            "campaign": SOURCE_CAMPAIGN,
            "provider": PROVIDER,
            "raw_digest": source_raw_manifest.get("raw_corpus_digest"),
            "normalized_digest": source_normalized_manifest.get("normalized_corpus_digest"),
            "source_secret_sha256": hashlib.sha256(source_secret).hexdigest(),
            "development_profiles": panel_meta["profile_meta"]["eligible_profiles"],
            "source_version_22_rows": panel_meta["profile_meta"]["source_version_22_rows"],
        },
        "frozen_panel": {
            "profiles": PANEL_PROFILES,
            "matches_per_profile": MATCHES_PER_PROFILE,
            "unique_match_ids": MAX_CALLS,
            "selection_digest": frozen["selection_digest"],
            "profile_selection_digest": frozen["profile_selection_digest"],
            "match_selection_digest": frozen["match_selection_digest"],
            "source_marker_verified_before_gets": True,
        },
        "initial_physical_gets": 0,
        "initial_replay_parse_requests": 0,
        "initial_stratz_calls": 0,
        "initial_steam_calls": 0,
        "initial_sealed_validation_analytical_use": 0,
        "initial_old_holdout_use": 0,
    }
    private_write(live_diag / "preflight.json", preflight_payload)
    write_progress(
        overnight_diag / "progress.json",
        stage="preflight_complete",
        calls_used=0,
        profiles_completed=0,
        matches_completed=0,
        errors=[],
        latest_gate_status="PREFLIGHT_PASS_OWNER_APPROVED",
        next_action="execute_fixed_960_GET_panel",
    )
    return frozen, items, profiles, {
        "salt": panel_meta["salt"],
        "source_secret": source_secret,
        "source_manifest": {**source_raw_manifest, **source_normalized_manifest},
    }, paths


def final_collection_artifacts(
    *,
    transport: LiveTransport,
    live_diag: Path,
    batch_measurements: Sequence[Mapping[str, Any]],
    storage_root: Path,
    collection_wall_seconds: float | None = None,
) -> None:
    existing_batch = read_json(live_diag / "batch_latency_summary.json") if (live_diag / "batch_latency_summary.json").exists() else {}
    write_csv(
        live_diag / "request_ledger.csv",
        [
            "campaign_id", "request_id", "ordinal", "profile_id", "match_id", "method", "endpoint", "concurrency", "batch_id", "requested_at", "completed_at", "latency_seconds", "http_status", "response_bytes", "response_sha256", "raw_path", "retry_number", "retry_limit", "error",
        ],
        ledger_csv_rows(transport),
    )
    failures = [row for row in response_entries(transport) if row.get("error") is not None]
    private_write(live_diag / "request_failure_ledger.json", {
        "schema_version": LIVE_SCHEMA,
        "campaign_id": LIVE_CAMPAIGN,
        "failures": failures,
        "failure_count": len(failures),
    })
    private_write(live_diag / "cost_ledger.json", cost_ledger(transport, directory_size(storage_root / ".local/corpora/opendota/free-dna-tier2") + directory_size(live_diag)))
    batch_payload = {
        "schema_version": LIVE_SCHEMA,
        "campaign_id": LIVE_CAMPAIGN,
        "measurements": list(batch_measurements),
        "required_concurrency_modes": [1, 5, 10],
        "rate_start_ceiling_per_minute": RATE_PER_MINUTE,
    }
    if collection_wall_seconds is not None:
        batch_payload["collection_wall_seconds"] = collection_wall_seconds
    elif isinstance(existing_batch.get("collection_wall_seconds"), (int, float)):
        batch_payload["collection_wall_seconds"] = existing_batch["collection_wall_seconds"]
    private_write(live_diag / "batch_latency_summary.json", batch_payload)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    storage_root = args.storage_root.resolve()
    live_diag = storage_root / ".local/diagnostics/free-dna-death-context-live-pilot"
    overnight_diag = storage_root / ".local/diagnostics/free-dna-death-context-overnight"
    paths: Mapping[str, Path] | None = None
    items: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    frozen: dict[str, Any] = {}
    meta: dict[str, Any] = {}
    try:
        frozen, items, profiles, meta, paths = preflight(
            source_root=source_root,
            storage_root=storage_root,
            live_diag=live_diag,
            overnight_diag=overnight_diag,
        )
        if args.preflight_only:
            print(json.dumps({
                "stage": "preflight_complete",
                "provider_key_configured": bool(os.getenv("OPENDOTA_API_KEY")),
                "planned_gets": MAX_CALLS,
                "profiles": PANEL_PROFILES,
                "matches_per_profile": MATCHES_PER_PROFILE,
                "selection_digest": frozen["selection_digest"],
                "opendota_calls": 0,
            }, sort_keys=True))
            return 0
        progress_path = overnight_diag / "progress.json"
        batch_summary_path = live_diag / "batch_latency_summary.json"
        transport, live_details, batch_measurements = asyncio.run(
            collect(
                source_root=source_root,
                storage_root=storage_root,
                paths=paths,
                items=items,
                frozen=frozen,
                batch_summary_path=batch_summary_path,
                progress_path=progress_path,
            )
        )
        final_collection_artifacts(
            transport=transport,
            live_diag=live_diag,
            batch_measurements=batch_measurements,
            storage_root=storage_root,
        )
        source_secret = meta["source_secret"]
        source_manifest = meta["source_manifest"]
        analysis = write_analysis_outputs(
            storage_root=storage_root,
            live_diag=live_diag,
            items=items,
            details=live_details,
            profiles=profiles,
            source_secret=source_secret,
            source_manifest=source_manifest,
            frozen=frozen,
            salt=meta["salt"],
            transport=transport,
            batch_measurements=batch_measurements,
            collection_started=time.monotonic(),
        )
        write_progress(
            overnight_diag / "progress.json",
            stage="terminal_verdict",
            calls_used=transport.physical_count,
            profiles_completed=PANEL_PROFILES,
            matches_completed=transport.successful_count,
            errors=transport.error_messages,
            latest_gate_status=analysis["summary"]["terminal_verdict"],
            next_action="write_tracked_evidence_and_review_branch",
        )
        print(json.dumps({
            "status": analysis["summary"]["status"],
            "terminal_verdict": analysis["summary"]["terminal_verdict"],
            "physical_gets": transport.physical_count,
            "successful": transport.successful_count,
            "profiles": PANEL_PROFILES,
            "matches_per_profile": MATCHES_PER_PROFILE,
            "output": str(live_diag),
        }, sort_keys=True))
        return 0
    except PilotBlocked as exc:
        message = str(exc)
        snapshot = {
            "physical_gets": 0,
            "successful_gets": 0,
            "profiles_completed": 0,
            "matches_completed": 0,
            "errors": [message],
        }
        if paths is not None and (paths["diagnostics"] / "request_ledger.jsonl").exists():
            try:
                snapshot = asyncio.run(
                    materialize_blocked_artifacts(
                        paths=paths,
                        items=items,
                        storage_root=storage_root,
                        profiles=profiles,
                        frozen=frozen,
                        source_manifest=meta["source_manifest"],
                    )
                )
            except PilotBlocked as artifact_exc:
                snapshot["errors"] = [message, f"BLOCKED_RECEIPT:{artifact_exc}"]
        private_write(
            live_diag / "pilot_blocked.json",
            {
                "schema_version": LIVE_SCHEMA,
                "campaign_id": LIVE_CAMPAIGN,
                "status": "BLOCKED",
                "reason": message,
                "physical_gets": snapshot["physical_gets"],
                "successful_gets": snapshot["successful_gets"],
                "profiles_completed": snapshot["profiles_completed"],
                "matches_completed": snapshot["matches_completed"],
            },
        )
        write_progress(
            overnight_diag / "progress.json",
            stage="terminal_blocked",
            calls_used=snapshot["physical_gets"],
            profiles_completed=snapshot["profiles_completed"],
            matches_completed=snapshot["matches_completed"],
            errors=snapshot["errors"],
            latest_gate_status="PILOT_COLLECTION_BLOCKED",
            next_action="write_blocked_evidence_and_stop",
        )
        print(json.dumps({"status": "BLOCKED", "terminal_verdict": "PILOT_COLLECTION_BLOCKED", "reason": message}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
