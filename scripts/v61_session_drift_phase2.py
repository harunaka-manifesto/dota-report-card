#!/usr/bin/env python3
"""Execute the frozen V6.1 Session Drift Phase-2 research campaign.

The runner is deliberately separate from production collection and analysis.
It keeps raw provider responses, canonical projections, split manifests, and
derived evidence in the private ``.local`` tree; only aggregate evidence is
written to the repository.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import hashlib
import hmac
import json
import math
import os
import secrets
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any

import httpx
import numpy as np
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.core.config import Settings  # noqa: E402
from app.dna.sessions import infer_sessions  # noqa: E402
from app.ingestion.summary_history_contract import (  # noqa: E402
    REQUIRED_FIELDS,
    SUMMARY_HISTORY_NORMALIZATION_VERSION,
    SUMMARY_HISTORY_PROJECTION,
    SUMMARY_HISTORY_PROVIDER_LIMIT,
    SUMMARY_HISTORY_PROVIDER_VERSION,
    SUMMARY_HISTORY_RETRY_LIMIT,
    SUMMARY_HISTORY_WINDOW_DAYS,
    normalize_canonical_summary_history,
    request_manifest,
    sha256_payload,
)
from app.ingestion.summary_normalize import (  # noqa: E402
    filter_history_window,
    previous_year_window,
)
from app.player_analysis_v61.artifacts import load_v61_artifact_bundle  # noqa: E402
from app.player_analysis_v61.calibration_corpus import (  # noqa: E402
    CANONICAL_SCHEMA_VERSION,
    CANONICAL_SESSION_POLICY,
    CANONICAL_WINDOW_SECONDS,
    MINIMUM_USABLE_MATCHES,
    canonical_history,
    canonical_rows,
    validate_canonical_corpus,
)
from app.player_analysis_v61.corpus_reuse import sha256_file  # noqa: E402
from app.player_analysis_v61.legacy_adapter import current_taxonomy_mapping  # noqa: E402
from v61_four_family_inference_design import (  # noqa: E402
    _family_p,
    _simulate_type1,
    _wilson,
)
from v61_four_family_tuning_calibration import (  # noqa: E402
    COMPONENTS,
    HALF_MIN_SESSIONS,
    LOO_AGREEMENT,
    MIN_MARGIN_PROFILES,
    MULTIPLICITY_MAX_FDR,
    TARGET_Q,
    _adjust,
    _infer_family,
    _loo_agreement,
    _measure_profile,
    _profile_key,
    _quantile,
    _session_partitions,
    _theta,
)
from v61_four_family_tuning_calibration import VERSION as INFERENCE_VERSION  # noqa: E402

CAMPAIGN_ID = "v61-session-drift-phase2-2026-08-28"
CORPUS_DIRNAME = "v61-session-drift-expansion"
DIAGNOSTIC_DIRNAME = "v61-session-drift-data-expansion"
FAMILIES = ("transfer", "post_loss_response", "session_drift")
FAMILY_LABELS = {
    "transfer": "Transfer",
    "post_loss_response": "Post-Loss",
    "session_drift": "Session Drift",
}
PHASE1_SHA = "43d8183f4b9be4bbf9cf096abf8b528598ce83e4"
ANALYTICAL_SOURCE_SHA = "7df38e6d234ae9c4ee425490bc40b8cc92685f85"
FROZEN_ARTIFACT_DIGEST = "8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0"
MAX_REQUESTS = 5_347
MAX_STORAGE_BYTES = 600 * 1024 * 1024
OWNER_COST_PER_100_CALLS_IDR = 200.0
OWNER_COST_PER_100_CALLS_USD = 0.01
PUBLIC_PAGES = 12
SEEDS_PER_PAGE = 100
DETAIL_REQUESTS = 1_200
FRAME_SIZE = 4_135
TUNING_CANDIDATES = 2_848
VALIDATION_CANDIDATES = 1_287
EXTERNAL_TUNING_TARGET = 769
VALIDATION_TARGET = 339
LOCAL_RESERVE = 40
TARGET_TUNING = 1_600
PILOT_SIZE = 100
PILOT_BYTES = 250 * 1024 * 1024
MULTIPLICITY_REPETITIONS = 10_000
MULTIPLICITY_DRAWS = 2_000
MULTIPLICITY_SEED = 20260828
P_VALUE_SEED_NAMESPACE = "research-signed-prevalence-calibration-1.0.0"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _private_write(path: Path, value: Any, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    try:
        payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
        view = memoryview(payload)
        while view:
            view = view[os.write(descriptor, view) :]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.chmod(mode)
    temporary.replace(path)
    path.chmod(mode)


def _private_write_once(path: Path, value: bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
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
    path.chmod(mode)


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o600)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_normalized_envelope(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = _read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"normalized profile is not an object: {path}")
    return value


def _write_gzip_json(path: Path, value: Any, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    compressed = gzip.compress(payload, compresslevel=9, mtime=0)
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    try:
        view = memoryview(compressed)
        while view:
            view = view[os.write(descriptor, view) :]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.chmod(mode)
    temporary.replace(path)
    path.chmod(mode)


def _compact_normalized_profiles(paths: Mapping[str, Path]) -> int:
    compacted = 0
    for source in sorted(paths["normalized_tuning"].glob("*.json")):
        target = source.with_suffix(".json.gz")
        envelope = _read_normalized_envelope(source)
        if target.exists():
            if _read_normalized_envelope(target) != envelope:
                raise RuntimeError(f"normalized profile collision: {target}")
        else:
            _write_gzip_json(target, envelope)
            if _read_normalized_envelope(target) != envelope:
                raise RuntimeError(f"normalized profile compression check failed: {target}")
        source.unlink()
        compacted += 1
    return compacted


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        path.chmod(0o600)
        return
    fields = list(rows[0])
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def _profile_pseudonym(account_id: int, salt: bytes) -> str:
    """Reuse the collector's canonical salted profile-id construction."""

    return hashlib.sha256(salt + str(account_id).encode("ascii")).hexdigest()


def _rank_digest(account_id: int, salt: bytes) -> str:
    return hmac.new(
        salt,
        f"v61-session-phase2:{int(account_id)}".encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _paths(local_root: Path) -> dict[str, Path]:
    corpus = local_root / "corpora" / "opendota" / CORPUS_DIRNAME
    diagnostics = local_root / "diagnostics" / DIAGNOSTIC_DIRNAME
    return {
        "local": local_root,
        "corpus": corpus,
        "raw": corpus / "raw",
        "raw_responses": corpus / "raw" / "responses",
        "normalized": corpus / "normalized",
        "normalized_tuning": corpus / "normalized" / "tuning",
        "manifests": corpus / "manifests",
        "derived": corpus / "derived",
        "diagnostics": diagnostics,
    }


def _prepare_dirs(paths: Mapping[str, Path]) -> None:
    for key in ("raw", "raw_responses", "normalized", "normalized_tuning", "manifests", "derived", "diagnostics"):
        paths[key].mkdir(parents=True, exist_ok=True, mode=0o700)
        paths[key].chmod(0o700)


def _storage_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _is_interrupted_entry(entry: Mapping[str, Any]) -> bool:
    return entry.get("error") == "interrupted_physical_request"


def _physical_entries(entries: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [entry for entry in entries if not _is_interrupted_entry(entry)]


def _physical_request_count(entries: Sequence[Mapping[str, Any]]) -> int:
    return len(_physical_entries(entries))


def _load_salt(paths: Mapping[str, Path], *, create: bool) -> bytes:
    path = paths["manifests"] / "private-split-secret.bin"
    if path.exists():
        value = path.read_bytes()
        if len(value) != 32:
            raise RuntimeError("IDENTITY_LINKAGE_DESIGN_REQUIRED: private split secret is not 32 bytes")
        return value
    if not create:
        raise RuntimeError("private split secret is missing; run --phase prepare first")
    value = secrets.token_bytes(32)
    _private_write_once(path, value)
    _private_write(
        paths["manifests"] / "private-split-secret.json",
        {
            "campaign_id": CAMPAIGN_ID,
            "algorithm": "HMAC-SHA256",
            "rank_namespace": "v61-session-phase2:",
            "pseudonymization": "sha256(salt||decimal_account_id)",
            "secret_bytes": len(value),
            "secret_sha256": hashlib.sha256(value).hexdigest(),
            "raw_secret_path": str(path),
        },
    )
    return value


def _candidate_values(value: Any, *, key: str = "") -> set[int]:
    found: set[int] = set()
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            folded = str(child_key).casefold()
            if folded in {"candidate_account_ids", "account_ids"} and isinstance(child, list):
                found.update(int(item) for item in child if isinstance(item, int) and item > 0)
            elif folded == "account_id" and isinstance(child, int) and child > 0:
                found.add(int(child))
            else:
                found.update(_candidate_values(child, key=folded))
    elif isinstance(value, list) and key in {"candidate_account_ids", "account_ids"}:
        found.update(int(item) for item in value if isinstance(item, int) and item > 0)
    return found


def _known_account_ids(local_root: Path) -> tuple[set[int], list[str]]:
    calibration = local_root / "calibration"
    paths = [
        calibration / "v6-public-match-candidates.json",
        calibration / "v61" / "candidates.json",
        calibration / "v61" / "replacement-candidates-precommitted-2026-08-25.json",
        calibration / "v61" / "replacement-candidates-selected.json",
        calibration / "v61" / "replacement-candidates-batch-01.json",
    ]
    paths.extend((calibration / "v61" / "manifest-history").glob("*candidate*.json"))
    found: set[int] = set()
    used: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        values = _candidate_values(_read_json(path))
        found.update(values)
        used.append(str(path))
    if not found:
        raise RuntimeError("IDENTITY_LINKAGE_DESIGN_REQUIRED: no existing candidate lineage found")
    return found, used


def _canonical_profile_payload(
    profiles: Sequence[Mapping[str, Any]],
    *,
    source: Mapping[str, Any],
    request: Mapping[str, Any],
    window_policy: Mapping[str, Any],
) -> dict[str, Any]:
    profiles = [dict(profile) for profile in profiles]
    return {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "generated_at": _now(),
        "request_manifest": dict(request),
        "source": dict(source),
        "window_policy": dict(window_policy),
        "profile_count": len(profiles),
        "summary": {
            "profile_count": len(profiles),
            "eligible_profile_count": sum(profile.get("status") == "eligible" for profile in profiles),
            "eligible_match_count": sum(len(profile.get("matches", [])) for profile in profiles),
        },
        "raw_identifiers_present": False,
        "profiles": profiles,
    }


def _validate_selected_local_data(local_root: Path) -> dict[str, Any]:
    base = local_root / "calibration" / "v61"
    corpus_path = base / "replacement-canonical-corpus.json"
    split_path = base / "manifests" / "replacement-split-2026-08-25.json"
    scan_path = base / "replacement-summary-scan.json"
    evidence_path = base / "replacement-selection-evidence.json"
    if not all(path.is_file() for path in (corpus_path, split_path, scan_path, evidence_path)):
        raise RuntimeError("required Phase-1 local lineage is incomplete")
    corpus_payload = _read_json(corpus_path)
    split = _read_json(split_path)
    train_ids = {str(item) for item in split["train_profile_ids"]}
    holdout_ids = {str(item) for item in split["holdout_profile_ids"]}
    if len(train_ids) != 791 or len(holdout_ids) != 339 or train_ids & holdout_ids:
        raise RuntimeError("frozen 791/339 split integrity mismatch")
    by_id = {str(profile["profile_id"]): profile for profile in corpus_payload["profiles"]}
    train_profiles = [by_id[profile_id] for profile_id in sorted(train_ids)]
    old_payload = dict(corpus_payload)
    old_payload["profiles"] = train_profiles
    old_payload["profile_count"] = len(train_profiles)
    old_payload["summary"] = {
        "profile_count": len(train_profiles),
        "eligible_profile_count": len(train_profiles),
        "eligible_match_count": sum(len(profile["matches"]) for profile in train_profiles),
    }
    old_corpus = validate_canonical_corpus(old_payload, checksum=_digest(old_payload))
    scan = _read_json(scan_path)
    selection = _read_json(evidence_path)
    eligible = [
        (index, status)
        for index, status in enumerate(scan["candidate_statuses"])
        if status.get("eligibility") == "eligible"
    ]
    reserve_statuses = eligible[339:]
    if len(reserve_statuses) != LOCAL_RESERVE or selection.get("unused_eligible_reserve_count") != LOCAL_RESERVE:
        raise RuntimeError("Phase-1 safe reserve count changed")
    scan_profiles = {str(profile["profile_id"]): profile for profile in scan["profiles"]}
    scan_window = scan["window"]
    reserve_profiles = []
    for _candidate_index, status in reserve_statuses:
        profile = dict(scan_profiles[status["profile_id"]])
        profile["collection_window"] = dict(scan_window)
        reserve_profiles.append(profile)
    reserve_payload = _canonical_profile_payload(
        reserve_profiles,
        source=corpus_payload["source"],
        request=corpus_payload["request_manifest"],
        window_policy=corpus_payload["window_policy"],
    )
    reserve_corpus = validate_canonical_corpus(reserve_payload, checksum=_digest(reserve_payload))
    if len(reserve_corpus.usable_profile_ids) != LOCAL_RESERVE:
        raise RuntimeError("safe local reserve is not fully eligible")
    return {
        "base": base,
        "old_payload": old_payload,
        "old_corpus": old_corpus,
        "reserve_payload": reserve_payload,
        "reserve_corpus": reserve_corpus,
        "split": split,
        "scan": scan,
        "selection": selection,
        "source_sha256": sha256_file(corpus_path),
    }


def _preflight(paths: Mapping[str, Path], local_root: Path, salt: bytes) -> dict[str, Any]:
    local = _validate_selected_local_data(local_root)
    artifact_dir = ROOT / "infra" / "runtime-artifacts" / "free_dna_v61" / "6.1.0"
    manifest = _read_json(artifact_dir / "build-manifest-6.1.0.json")
    if manifest["source"]["repository_commit"] != ANALYTICAL_SOURCE_SHA or manifest["source"]["dirty_worktree"] is not False:
        raise RuntimeError("frozen analytical artifact source binding mismatch")
    load_v61_artifact_bundle(
        artifact_dir,
        expected_source_revision=ANALYTICAL_SOURCE_SHA,
        expected_dirty_worktree=False,
    )
    window_path = paths["manifests"] / "collection-window.json"
    if window_path.exists():
        window = _read_json(window_path)
    else:
        window_end = int(datetime.now(UTC).timestamp())
        window_start, window_end = previous_year_window(
            window_end=window_end, days=SUMMARY_HISTORY_WINDOW_DAYS
        )
        window = {
            "days": SUMMARY_HISTORY_WINDOW_DAYS,
            "start_time": window_start,
            "end_time": window_end,
        }
        _private_write(window_path, window)
    if int(window["end_time"]) - int(window["start_time"]) != CANONICAL_WINDOW_SECONDS:
        raise RuntimeError("collection window is not exactly 365 days")
    _private_write(
        paths["diagnostics"] / "existing_data_pool_audit.json",
        {
            "campaign_id": CAMPAIGN_ID,
            "historical_tuning_profiles": 791,
            "existing_margin_observations": 62,
            "safe_local_reserve_profiles": 40,
            "fresh_replacement_holdout_profiles": 339,
            "historical_revealed_holdout_profiles": 339,
            "replacement_scan_ineligible_profiles": 845,
            "previously_screened_reserve_profiles": 10,
            "old_holdout_loaded_for_analysis": False,
            "reserve_lineage": str(local["selection"].get("schema_version")),
            "replacement_scan_sha256": local["selection"].get("replacement_scan_sha256"),
            "source_corpus_sha256": local["source_sha256"],
        },
    )
    _private_write(
        paths["diagnostics"] / "private_split_secret.json",
        {
            "campaign_id": CAMPAIGN_ID,
            "algorithm": "HMAC-SHA256(salt, v61-session-phase2:decimal_account_id)",
            "secret_bytes": len(salt),
            "secret_sha256": hashlib.sha256(salt).hexdigest(),
            "secret_path": str(paths["manifests"] / "private-split-secret.bin"),
        },
    )
    preflight = {
        "campaign_id": CAMPAIGN_ID,
        "phase1_sha": PHASE1_SHA,
        "analytical_source_sha": ANALYTICAL_SOURCE_SHA,
        "frozen_artifact_digest": FROZEN_ARTIFACT_DIGEST,
        "execution_code_sha": _git_sha(),
        "owner_ceilings": {
            "physical_requests": MAX_REQUESTS,
            "storage_bytes": MAX_STORAGE_BYTES,
            "storage_mib": 600,
            "expected_cost_idr": 12_000,
        },
        "fixed_frame": {
            "public_pages": PUBLIC_PAGES,
            "seed_details": DETAIL_REQUESTS,
            "candidate_accounts": FRAME_SIZE,
            "tuning_candidates": TUNING_CANDIDATES,
            "validation_candidates": VALIDATION_CANDIDATES,
        },
        "owner_cost_assumption": {
            "label": "OWNER-SUPPLIED COST ASSUMPTION",
            "idr_per_100_calls": OWNER_COST_PER_100_CALLS_IDR,
            "usd_per_100_calls": OWNER_COST_PER_100_CALLS_USD,
        },
        "window": window,
        "known_exclusion_account_count": len(_known_account_ids(local_root)[0]),
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "old_holdout_analytical_outputs_loaded": False,
        "fresh_validation_analytical_outputs_allowed": False,
    }
    _private_write(paths["diagnostics"] / "execution_preflight.json", preflight)
    return {"local": local, "preflight": preflight, "artifact_dir": artifact_dir, "salt": salt}


class FixedTransport:
    """Sequential, retry-free OpenDota transport with immutable response capture."""

    def __init__(
        self,
        settings: Settings,
        paths: Mapping[str, Path],
        *,
        pace_seconds: float,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.pace_seconds = max(0.0, pace_seconds)
        self.ledger_path = paths["diagnostics"] / "request_ledger.jsonl"
        self.ledger = _read_jsonl(self.ledger_path)
        self.last_started = 0.0
        inflight = list(paths["raw"].glob(".inflight-*.json"))
        if inflight:
            raise RuntimeError("an interrupted physical request is indeterminate; preserve and inspect campaign")
        timeout = httpx.Timeout(settings.opendota_timeout_seconds)
        self.http = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> FixedTransport:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.http.aclose()

    def _ordinal(self) -> int:
        return len(self.ledger)

    def _projected_cost(self, requests: int = MAX_REQUESTS) -> float:
        return requests / 100.0 * OWNER_COST_PER_100_CALLS_IDR

    async def request(
        self,
        endpoint: str,
        *,
        params: Sequence[tuple[str, Any]] | None,
        area: str,
        profile_id: str | None = None,
        expected_shape: str,
    ) -> tuple[Any | None, dict[str, Any]]:
        if _physical_request_count(self.ledger) >= MAX_REQUESTS:
            raise RuntimeError("physical request ceiling reached")
        ordinal = self._ordinal()
        request_identity = {
            "method": "GET",
            "endpoint": endpoint,
            "params": [[str(key), str(value)] for key, value in (params or ())],
            "expected_shape": expected_shape,
        }
        marker = self.paths["raw"] / f".inflight-{ordinal:05d}.json"
        _private_write_once(
            marker,
            json.dumps(
                {"campaign_id": CAMPAIGN_ID, "ordinal": ordinal, "request": request_identity},
                sort_keys=True,
            ).encode(),
        )
        if self.last_started:
            delay = self.pace_seconds - (time.monotonic() - self.last_started)
            if delay > 0:
                await asyncio.sleep(delay)
        self.last_started = time.monotonic()
        started_at = _now()
        status: int | None = None
        body = b""
        parsed: Any | None = None
        error: str | None = None
        try:
            url = f"{self.settings.opendota_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            response = await self.http.get(url, params=params, headers=self._headers())
            status = response.status_code
            body = response.content
            if status < 200 or status >= 300:
                error = f"http_{status}"
            else:
                try:
                    parsed = response.json()
                except ValueError:
                    error = "invalid_json"
                if error is None:
                    error = _raw_shape_error(parsed, expected_shape)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
            error = type(exc).__name__
        finished_at = _now()
        raw_path: str | None = None
        if body:
            raw_path = str(self.paths["raw_responses"] / f"response-{ordinal:05d}.body")
            _private_write_once(self.paths["raw_responses"] / f"response-{ordinal:05d}.body", body)
        entry = {
            "campaign_id": CAMPAIGN_ID,
            "area": area,
            "profile_id": profile_id,
            "ordinal": ordinal,
            "request": request_identity,
            "requested_at": started_at,
            "completed_at": finished_at,
            "http_status": status,
            "response_bytes": len(body),
            "response_sha256": hashlib.sha256(body).hexdigest() if body else None,
            "raw_artifact_path": raw_path,
            "retry_number": 0,
            "retry_limit": 0,
            "error": error,
            "projected_full_campaign_cost_idr": self._projected_cost(),
        }
        _append_jsonl(self.ledger_path, entry)
        self.ledger.append(entry)
        marker.unlink(missing_ok=True)
        if len(self.ledger) % 500 == 0:
            _private_write(
                self.paths["diagnostics"] / "cost_ledger.json",
                _cost_ledger(self.ledger, _storage_bytes(self.paths["corpus"])),
            )
        return parsed, entry

    def _headers(self) -> dict[str, str]:
        return (
            {"Authorization": f"Bearer {self.settings.opendota_api_key}"}
            if self.settings.opendota_api_key
            else {}
        )


def _cost_ledger(entries: Sequence[Mapping[str, Any]], storage_bytes: int) -> dict[str, Any]:
    physical_entries = _physical_entries(entries)
    physical = len(physical_entries)
    successful = sum(entry.get("error") is None for entry in physical_entries)
    failed = physical - successful
    payload_bytes = sum(int(entry.get("response_bytes") or 0) for entry in physical_entries)
    estimated_pro_rata = physical / 100 * OWNER_COST_PER_100_CALLS_IDR
    estimated_block = math.ceil(physical / 100) * OWNER_COST_PER_100_CALLS_IDR
    return {
        "campaign_id": CAMPAIGN_ID,
        "physical_request_count": physical,
        "successful_requests": successful,
        "failed_requests": failed,
        "retries": sum(int(entry.get("retry_number", 0)) for entry in physical_entries),
        "interrupted_request_markers": sum(_is_interrupted_entry(entry) for entry in entries),
        "estimated_billable_100_call_units": math.ceil(physical / 100),
        "estimated_cost_idr_pro_rata": estimated_pro_rata,
        "estimated_cost_idr_whole_100_call_blocks": estimated_block,
        "estimated_cost_usd_whole_100_call_blocks": math.ceil(physical / 100) * OWNER_COST_PER_100_CALLS_USD,
        "cost_rate_label": "OWNER-SUPPLIED COST ASSUMPTION",
        "cost_rate_idr_per_100_calls": OWNER_COST_PER_100_CALLS_IDR,
        "cost_rate_usd_per_100_calls": OWNER_COST_PER_100_CALLS_USD,
        "payload_bytes": payload_bytes,
        "cumulative_storage_bytes": storage_bytes,
        "cumulative_storage_mib": storage_bytes / (1024 * 1024),
        "request_ceiling": MAX_REQUESTS,
        "storage_ceiling_bytes": MAX_STORAGE_BYTES,
        "cost_ceiling_idr": 12_000,
        "within_ceiling": physical <= MAX_REQUESTS and storage_bytes <= MAX_STORAGE_BYTES and estimated_block <= 12_000,
    }


def _frame_exclusion_digest(known: set[int]) -> str:
    return hashlib.sha256("\n".join(str(value) for value in sorted(known)).encode()).hexdigest()


async def _discover_frame(
    transport: FixedTransport,
    *,
    salt: bytes,
    known: set[int],
    paths: Mapping[str, Path],
) -> list[dict[str, Any]]:
    frame_path = paths["manifests"] / "fixed-frame-manifest.json"
    if frame_path.exists():
        payload = _read_json(frame_path)
        return list(payload["ranked_frame"])
    seed_ids: list[int] = []
    page_rows: list[dict[str, Any]] = []
    cursor: int | None = None
    for page_index in range(PUBLIC_PAGES):
        params = [("less_than_match_id", cursor)] if cursor is not None else []
        value, entry = await transport.request(
            "/publicMatches",
            params=params,
            area="public_match_page",
            expected_shape="array",
        )
        if not isinstance(value, list):
            raise RuntimeError("PROVIDER_SCHEMA_DRIFT: /publicMatches did not return an array")
        unique: list[int] = []
        seen: set[int] = set()
        for row in value:
            if isinstance(row, Mapping) and isinstance(row.get("match_id"), int) and row["match_id"] > 0:
                match_id = int(row["match_id"])
                if match_id not in seen:
                    seen.add(match_id)
                    unique.append(match_id)
        if len(unique) < SEEDS_PER_PAGE:
            raise RuntimeError("fixed discovery page returned fewer than 100 unique positive seeds")
        unique = unique[:SEEDS_PER_PAGE]
        seed_ids.extend(unique)
        cursor = min(seed_ids)
        page_rows.append(
            {
                "page": page_index,
                "cursor": params[0][1] if params else None,
                "seed_count": len(unique),
                "request_ordinal": entry["ordinal"],
            }
        )
    public_accounts: set[int] = set()
    details: list[dict[str, Any]] = []
    for detail_index, match_id in enumerate(seed_ids):
        value, entry = await transport.request(
            f"/matches/{match_id}",
            params=[],
            area="seed_match_detail",
            expected_shape="object",
        )
        found: set[int] = set()
        if isinstance(value, Mapping) and isinstance(value.get("players"), list):
            for player in value["players"]:
                if isinstance(player, Mapping) and isinstance(player.get("account_id"), int) and player["account_id"] > 0:
                    found.add(int(player["account_id"]))
        public_accounts.update(found)
        details.append(
            {
                "detail_index": detail_index,
                "match_id": match_id,
                "request_ordinal": entry["ordinal"],
                "positive_accounts": len(found),
                "error": entry.get("error"),
            }
        )
    candidates = sorted(public_accounts - known)
    ranked = sorted(
        ({"account_id": account_id, "rank_digest": _rank_digest(account_id, salt)} for account_id in candidates),
        key=lambda row: (row["rank_digest"], row["account_id"]),
    )
    if len(ranked) < FRAME_SIZE:
        raise RuntimeError(f"fixed frame shortfall: {len(ranked)} < {FRAME_SIZE}")
    ranked = ranked[:FRAME_SIZE]
    assignments = []
    for position, row in enumerate(ranked):
        arm = "tuning" if position < TUNING_CANDIDATES else "fresh_sealed_validation"
        assignments.append(
            {
                "position": position,
                "account_id": row["account_id"],
                "rank_digest": row["rank_digest"],
                "profile_id": _profile_pseudonym(row["account_id"], salt),
                "arm": arm,
            }
        )
    payload = {
        "schema_version": "v61-session-drift-fixed-frame-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "selection": "12 descending /publicMatches pages x 100 + 1,200 /matches details; exclude; HMAC-rank; first 4,135",
        "public_pages": page_rows,
        "seed_match_count": len(seed_ids),
        "detail_request_count": len(details),
        "positive_public_account_count": len(public_accounts),
        "known_exclusion_count": len(known),
        "known_exclusion_digest": _frame_exclusion_digest(known),
        "rank_namespace": "v61-session-phase2:",
        "ranked_frame": assignments,
        "detail_digest": _digest(details),
        "adaptive_top_up": False,
        "long_session_enrichment": False,
    }
    _private_write(frame_path, payload)
    return assignments


def _source_metadata() -> dict[str, Any]:
    return {
        "endpoint": "/players/{account_id}/matches",
        "request_count_per_profile": 1,
        "detail_requests": 0,
        "parse_requests": 0,
        "rank_or_mmr_used": False,
        "retry_limit": SUMMARY_HISTORY_RETRY_LIMIT,
        "provider": "OpenDota",
        "provider_version": SUMMARY_HISTORY_PROVIDER_VERSION,
    }


def _materialize_profile(
    rows: Sequence[Mapping[str, Any]],
    *,
    account_id: int,
    profile_id: str,
    window: Mapping[str, Any],
) -> dict[str, Any]:
    canonical = normalize_canonical_summary_history(
        rows,
        account_id,
        request_count=1,
        provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
    )
    eligible = filter_history_window(
        canonical.normalization.eligible_matches,
        window_start=int(window["start_time"]),
        window_end=int(window["end_time"]),
    )
    session_result = infer_sessions(
        eligible,
        CANONICAL_SESSION_POLICY,
        window_start=int(window["start_time"]),
        window_end=int(window["end_time"]),
    )
    source_rows = [row for row in rows if isinstance(row, Mapping)]
    exclusion_reasons = Counter(
        reason
        for record in canonical.normalization.exclusion_ledger
        for reason in record.get("reasons", [])
    )
    exclusion_reasons["outside_window"] += sum(
        1
        for match in canonical.normalization.eligible_matches
        if match.started_at is None
        or not int(window["start_time"]) <= match.started_at <= int(window["end_time"])
    )
    materialized: list[dict[str, Any]] = []
    for match in session_result.matches:
        source = source_rows[match.source_index] if match.source_index < len(source_rows) else {}
        materialized.append(
            {
                "match_id": match.match_id,
                "start_time": match.started_at,
                "duration_seconds": match.duration_seconds,
                "won": match.won,
                "hero_id": match.hero_id,
                "kills": match.kills,
                "deaths": match.deaths,
                "assists": match.assists,
                "leaver_status": match.leaver_status,
                "game_mode": match.game_mode,
                "lobby_type": match.lobby_type,
                "player_slot": source.get("player_slot"),
                "radiant_win": source.get("radiant_win"),
                "hero_variant": match.hero_variant,
                "party_size": match.party_size,
                "lane": match.lane,
                "lane_role": match.lane_role,
                "is_roaming": match.is_roaming,
                "source_version": match.source_version,
                "session_id": match.session_id,
                "session_index": match.session_index,
                "session_corrupt": match.session_corrupt,
            }
        )
    return {
        "profile_id": profile_id,
        "collection_window": dict(window),
        "status": "eligible" if len(materialized) >= MINIMUM_USABLE_MATCHES else "ineligible",
        "eligible_match_count": len(materialized),
        "session_count": len(session_result.sessions),
        "completed_session_count": len(session_result.completed_sessions),
        "history_audit": canonical.audit.as_dict(),
        "eligibility_audit": {
            "excluded_match_count": max(0, canonical.audit.raw_count - len(materialized)),
            "exclusion_reasons": dict(sorted(exclusion_reasons.items())),
            "duplicate_conflict_count": len(canonical.normalization.duplicate_conflicts),
            "minimum_usable_matches": MINIMUM_USABLE_MATCHES,
        },
        "matches": materialized,
    }


def _validation_eligibility(rows: Sequence[Mapping[str, Any]], account_id: int, window: Mapping[str, Any]) -> dict[str, Any]:
    canonical = normalize_canonical_summary_history(
        rows,
        account_id,
        request_count=1,
        provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
    )
    eligible = filter_history_window(
        canonical.normalization.eligible_matches,
        window_start=int(window["start_time"]),
        window_end=int(window["end_time"]),
    )
    return {
        "status": "eligible" if len(eligible) >= MINIMUM_USABLE_MATCHES else "ineligible",
        "eligible_match_count": len(eligible),
        "raw_count": canonical.audit.raw_count,
        "normalized_count": canonical.audit.normalized_count,
        "normalization_version": canonical.audit.normalization_version,
    }


def _raw_shape_error(value: Any, expected_shape: str) -> str | None:
    if expected_shape == "array" and not isinstance(value, list):
        return "schema_contract_break"
    if expected_shape == "object" and not isinstance(value, Mapping):
        return "schema_contract_break"
    if expected_shape == "history":
        if not isinstance(value, list):
            return "schema_contract_break"
        for row in value:
            if not isinstance(row, Mapping):
                return "schema_contract_break"
            if any(field not in row for field in REQUIRED_FIELDS):
                return "schema_contract_break"
    return None


def _pilot_decision(entries: Sequence[Mapping[str, Any]], paths: Mapping[str, Path]) -> dict[str, Any]:
    pilot = [entry for entry in entries if entry.get("area") == "tuning_history"][:PILOT_SIZE]
    schema_breaks = sum(entry.get("error") == "schema_contract_break" for entry in pilot)
    failures = sum(entry.get("error") not in (None, "schema_contract_break") for entry in pilot)
    observed_bytes = sum(int(entry.get("response_bytes") or 0) for entry in pilot)
    average_bytes = observed_bytes / len(pilot) if pilot else 0.0
    remaining_history_requests = (TUNING_CANDIDATES + VALIDATION_CANDIDATES) - len(pilot)
    storage_bytes = _storage_bytes(paths["corpus"])
    normalized_bytes = _storage_bytes(paths["normalized_tuning"])
    normalized_ratio = normalized_bytes / observed_bytes if observed_bytes else 0.0
    projected_storage = storage_bytes + average_bytes * remaining_history_requests * (1 + normalized_ratio)
    projected_requests = PUBLIC_PAGES + DETAIL_REQUESTS + FRAME_SIZE
    projected_cost = math.ceil(projected_requests / 100) * OWNER_COST_PER_100_CALLS_IDR
    checks = {
        "exactly_100_tuning_requests": len(pilot) == PILOT_SIZE,
        "schema_contract_breaks_zero": schema_breaks == 0,
        "transport_or_http_failures_at_most_10": failures <= 10,
        "observed_bytes_at_most_250_mib": observed_bytes <= PILOT_BYTES,
        "projected_physical_requests_within_ceiling": projected_requests <= MAX_REQUESTS,
        "projected_storage_within_ceiling": projected_storage <= MAX_STORAGE_BYTES,
        "projected_cost_within_ceiling": projected_cost <= 12_000,
    }
    return {
        "campaign_id": CAMPAIGN_ID,
        "pilot_size": len(pilot),
        "schema_contract_breaks": schema_breaks,
        "transport_or_http_failures": failures,
        "observed_response_bytes": observed_bytes,
        "observed_response_mib": observed_bytes / (1024 * 1024),
        "observed_normalized_bytes": normalized_bytes,
        "normalized_to_response_ratio": normalized_ratio,
        "projected_storage_bytes": int(projected_storage),
        "projected_storage_mib": projected_storage / (1024 * 1024),
        "projected_physical_requests": projected_requests,
        "projected_cost_idr_whole_100_call_blocks": projected_cost,
        "cost_assumption": "OWNER-SUPPLIED COST ASSUMPTION",
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "STOP",
        "analytical_inspection_performed": False,
    }


def _recover_interrupted_requests(paths: Mapping[str, Path]) -> int:
    markers = sorted(paths["raw"].glob(".inflight-*.json"))
    if not markers:
        return 0
    frame_path = paths["manifests"] / "fixed-frame-manifest.json"
    if not frame_path.is_file():
        raise RuntimeError("interrupted discovery request is indeterminate; preserve and inspect campaign")
    frame = _read_json(frame_path).get("ranked_frame", [])
    by_account = {int(row["account_id"]): row for row in frame}
    ledger_path = paths["diagnostics"] / "request_ledger.jsonl"
    ledger = _read_jsonl(ledger_path)
    recovered = 0
    for marker in markers:
        payload = _read_json(marker)
        if payload.get("campaign_id") != CAMPAIGN_ID:
            raise RuntimeError(f"unknown campaign in interrupted marker: {marker}")
        ordinal = int(payload["ordinal"])
        if ordinal != len(ledger):
            raise RuntimeError(f"request ledger/marker ordinal mismatch: {marker}")
        request = payload["request"]
        endpoint = str(request.get("endpoint", ""))
        prefix, suffix = "/players/", "/matches"
        if not (endpoint.startswith(prefix) and endpoint.endswith(suffix)):
            raise RuntimeError("interrupted discovery request is indeterminate; preserve and inspect campaign")
        account_id = int(endpoint[len(prefix) : -len(suffix)])
        assignment = by_account.get(account_id)
        if assignment is None:
            raise RuntimeError("interrupted request is not in the fixed candidate frame")
        raw_path = paths["raw_responses"] / f"response-{ordinal:05d}.body"
        body = raw_path.read_bytes() if raw_path.is_file() else b""
        entry = {
            "campaign_id": CAMPAIGN_ID,
            "area": "tuning_history" if assignment["arm"] == "tuning" else "sealed_validation_history",
            "profile_id": assignment["profile_id"],
            "ordinal": ordinal,
            "request": request,
            "requested_at": _now(),
            "completed_at": _now(),
            "http_status": None,
            "response_bytes": len(body),
            "response_sha256": hashlib.sha256(body).hexdigest() if body else None,
            "raw_artifact_path": str(raw_path) if body else None,
            "retry_number": 0,
            "retry_limit": 0,
            "error": "interrupted_physical_request",
            "counted_as_physical_request": False,
            "projected_full_campaign_cost_idr": MAX_REQUESTS / 100 * OWNER_COST_PER_100_CALLS_IDR,
        }
        _append_jsonl(ledger_path, entry)
        ledger.append(entry)
        marker.unlink()
        recovered += 1
    return recovered


def _checkpoint(paths: Mapping[str, Path], entries: Sequence[Mapping[str, Any]], *, phase: str) -> None:
    storage = _storage_bytes(paths["corpus"])
    _private_write(
        paths["diagnostics"] / "collection_checkpoint.json",
        {
            "campaign_id": CAMPAIGN_ID,
            "phase": phase,
            "physical_requests": _physical_request_count(entries),
            "successful_requests": sum(entry.get("error") is None for entry in _physical_entries(entries)),
            "failed_requests": sum(entry.get("error") is not None for entry in _physical_entries(entries)),
            "storage_bytes": storage,
            "storage_mib": storage / (1024 * 1024),
            "within_ceiling": _physical_request_count(entries) <= MAX_REQUESTS and storage <= MAX_STORAGE_BYTES,
            "updated_at": _now(),
        },
    )


def _save_normalized_profile(
    paths: Mapping[str, Path],
    profile: Mapping[str, Any],
    *,
    raw_entry: Mapping[str, Any],
) -> Path:
    profile_id = str(profile["profile_id"])
    path = paths["normalized_tuning"] / f"{profile_id}.json.gz"
    envelope = {
        "schema_version": "v61-opendota-normalized-profile-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "provider": "OpenDota",
        "normalizer_version": SUMMARY_HISTORY_NORMALIZATION_VERSION,
        "canonical_schema_version": CANONICAL_SCHEMA_VERSION,
        "raw_response_sha256": raw_entry.get("response_sha256"),
        "raw_response_path": raw_entry.get("raw_artifact_path"),
        "profile": dict(profile),
    }
    _write_gzip_json(path, envelope)
    return path


def _split_manifest(paths: Mapping[str, Path], frame: Sequence[Mapping[str, Any]], salt: bytes) -> dict[str, Any]:
    assignments = [dict(row) for row in frame]
    payload = {
        "schema_version": "v61-session-drift-split-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "algorithm": "HMAC-SHA256(salt, v61-session-phase2:decimal_account_id), ascending digest then decimal id",
        "candidate_frame_size": len(assignments),
        "tuning_arm_size": sum(row["arm"] == "tuning" for row in assignments),
        "validation_arm_size": sum(row["arm"] == "fresh_sealed_validation" for row in assignments),
        "tuning_target_eligible": EXTERNAL_TUNING_TARGET,
        "validation_target_eligible": VALIDATION_TARGET,
        "salt_sha256": hashlib.sha256(salt).hexdigest(),
        "assignments": assignments,
        "raw_identifiers_present": True,
    }
    _private_write(paths["manifests"] / "split-manifest.json", payload)
    return payload


async def _collect(
    paths: Mapping[str, Path],
    local_root: Path,
    *,
    env_file: Path,
    pace_seconds: float,
    acknowledge: bool,
) -> int:
    if not acknowledge:
        raise RuntimeError("network collection requires --acknowledge-owner-approval")
    if not env_file.is_file():
        raise RuntimeError(f"OpenDota environment file is missing: {env_file}")
    load_dotenv(env_file, override=False)
    settings = Settings.from_env()
    if settings.opendota_source != "live" or not settings.opendota_api_key:
        raise RuntimeError("OPENDOTA_SOURCE=live and OPENDOTA_API_KEY are required")
    salt = _load_salt(paths, create=False)
    _preflight(paths, local_root, salt)
    _compact_normalized_profiles(paths)
    _recover_interrupted_requests(paths)
    known, known_paths = _known_account_ids(local_root)
    _private_write(
        paths["manifests"] / "known-exclusion-lineage.json",
        {
            "campaign_id": CAMPAIGN_ID,
            "file_count": len(known_paths),
            "files": known_paths,
            "account_count": len(known),
            "account_set_sha256": _frame_exclusion_digest(known),
        },
    )
    async with FixedTransport(settings, paths, pace_seconds=pace_seconds) as transport:
        frame = await _discover_frame(transport, salt=salt, known=known, paths=paths)
        split = _split_manifest(paths, frame, salt)
        _checkpoint(paths, transport.ledger, phase="discovery_and_split")
        if len(frame) != FRAME_SIZE or split["tuning_arm_size"] != TUNING_CANDIDATES or split["validation_arm_size"] != VALIDATION_CANDIDATES:
            raise RuntimeError("split integrity mismatch")

        window = _read_json(paths["manifests"] / "collection-window.json")
        failure_path = paths["diagnostics"] / "normalization_failure_ledger.json"
        normalization_failures: list[dict[str, Any]] = (
            list(_read_json(failure_path)) if failure_path.is_file() else []
        )
        validation_rows: list[dict[str, Any]] = []
        history_entries = [
            entry
            for entry in transport.ledger
            if entry.get("area") in {
                "tuning_history",
                "sealed_validation_history",
                "fresh_sealed_validation_history",
            }
        ]
        completed_history = {
            str(entry["profile_id"])
            for entry in history_entries
            if entry.get("profile_id") is not None
        }
        tuning_attempts = sum(entry.get("area") == "tuning_history" for entry in transport.ledger)
        pilot_path = paths["diagnostics"] / "pilot_decision.json"
        pilot_checked = tuning_attempts >= PILOT_SIZE and pilot_path.is_file()
        if tuning_attempts >= PILOT_SIZE and not pilot_checked:
            pilot = _pilot_decision(transport.ledger, paths)
            _private_write(pilot_path, pilot)
            pilot_checked = True
            if pilot["status"] != "PASS":
                _private_write(paths["diagnostics"] / "request_failure_ledger.json", [entry for entry in transport.ledger if entry.get("error")])
                _private_write(paths["diagnostics"] / "cost_ledger.json", _cost_ledger(transport.ledger, _storage_bytes(paths["corpus"])))
                return 2
        for assignment in frame[:TUNING_CANDIDATES]:
            if assignment["profile_id"] in completed_history:
                continue
            tuning_attempts += 1
            value, entry = await transport.request(
                f"/players/{assignment['account_id']}/matches",
                params=[
                    ("date", SUMMARY_HISTORY_WINDOW_DAYS),
                    ("limit", SUMMARY_HISTORY_PROVIDER_LIMIT),
                    *[("project", field) for field in SUMMARY_HISTORY_PROJECTION],
                ],
                area="tuning_history",
                profile_id=assignment["profile_id"],
                expected_shape="history",
            )
            shape_error = _raw_shape_error(value, "history") if entry.get("error") is None else None
            if shape_error:
                entry["error"] = shape_error
                normalization_failures.append(
                    {
                        "profile_id": assignment["profile_id"],
                        "request_ordinal": entry["ordinal"],
                        "failure_code": shape_error,
                    }
                )
            if tuning_attempts == PILOT_SIZE:
                pilot = _pilot_decision(transport.ledger, paths)
                _private_write(paths["diagnostics"] / "pilot_decision.json", pilot)
                pilot_checked = True
                if pilot["status"] != "PASS":
                    _private_write(paths["diagnostics"] / "normalization_failure_ledger.json", normalization_failures)
                    _private_write(paths["diagnostics"] / "request_failure_ledger.json", [entry for entry in transport.ledger if entry.get("error")])
                    _private_write(paths["diagnostics"] / "cost_ledger.json", _cost_ledger(transport.ledger, _storage_bytes(paths["corpus"])))
                    return 2
            if entry.get("error") is None and shape_error is None:
                try:
                    profile = _materialize_profile(
                        value or [],
                        account_id=int(assignment["account_id"]),
                        profile_id=str(assignment["profile_id"]),
                        window=window,
                    )
                    _save_normalized_profile(paths, profile, raw_entry=entry)
                    completed_history.add(assignment["profile_id"])
                except Exception as exc:
                    normalization_failures.append(
                        {
                            "profile_id": assignment["profile_id"],
                            "request_ordinal": entry["ordinal"],
                            "failure_code": "normalization_failed",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
            if _storage_bytes(paths["corpus"]) > MAX_STORAGE_BYTES:
                raise RuntimeError("STORAGE_CEILING_EXCEEDED")
            if len(transport.ledger) % 500 == 0:
                _checkpoint(paths, transport.ledger, phase="tuning_history")
        if not pilot_checked:
            raise RuntimeError("pilot was not completed")

        existing_validation_status = {}
        status_path = paths["manifests"] / "sealed-validation-status.json"
        if not status_path.is_file():
            status_path = paths["manifests"] / "sealed-validation-status.partial.json"
        if status_path.is_file():
            existing_validation_status = {
                str(row["profile_id"]): row
                for row in _read_json(status_path).get("profiles", [])
                if isinstance(row, Mapping) and row.get("profile_id") is not None
            }
        for assignment in frame[TUNING_CANDIDATES:]:
            profile_id = str(assignment["profile_id"])
            if profile_id in existing_validation_status:
                validation_rows.append(existing_validation_status[profile_id])
                continue
            if profile_id in completed_history:
                entry = next(
                    item
                    for item in reversed(transport.ledger)
                    if item.get("profile_id") == profile_id
                )
                status = {
                    "profile_id": profile_id,
                    "position": assignment["position"],
                    "arm": "fresh_sealed_validation",
                    "request_ordinal": entry["ordinal"],
                    "request_error": entry.get("error"),
                    "analytical_evaluation": False,
                }
                if entry.get("error") is None:
                    raw_path = Path(str(entry["raw_artifact_path"]))
                    body = raw_path.read_bytes()
                    if hashlib.sha256(body).hexdigest() != entry.get("response_sha256"):
                        raise RuntimeError(f"raw response digest mismatch: {raw_path}")
                    value = json.loads(body)
                    shape_error = _raw_shape_error(value, "history")
                    if shape_error:
                        status["request_error"] = shape_error
                    else:
                        status["eligibility"] = _validation_eligibility(
                            value, int(assignment["account_id"]), window
                        )
                validation_rows.append(status)
                continue
            value, entry = await transport.request(
                f"/players/{assignment['account_id']}/matches",
                params=[
                    ("date", SUMMARY_HISTORY_WINDOW_DAYS),
                    ("limit", SUMMARY_HISTORY_PROVIDER_LIMIT),
                    *[("project", field) for field in SUMMARY_HISTORY_PROJECTION],
                ],
                area="sealed_validation_history",
                profile_id=assignment["profile_id"],
                expected_shape="history",
            )
            shape_error = _raw_shape_error(value, "history") if entry.get("error") is None else None
            if shape_error:
                entry["error"] = shape_error
                normalization_failures.append(
                    {
                        "profile_id": assignment["profile_id"],
                        "request_ordinal": entry["ordinal"],
                        "failure_code": shape_error,
                        "arm": "fresh_sealed_validation",
                    }
                )
            status = {
                "profile_id": assignment["profile_id"],
                "position": assignment["position"],
                "arm": "fresh_sealed_validation",
                "request_ordinal": entry["ordinal"],
                "request_error": entry.get("error"),
                "analytical_evaluation": False,
            }
            if entry.get("error") is None and shape_error is None:
                try:
                    status["eligibility"] = _validation_eligibility(
                        value or [], int(assignment["account_id"]), window
                    )
                except Exception as exc:
                    status["eligibility"] = {
                        "status": "normalization_failed",
                        "failure_code": "normalization_failed",
                        "error_type": type(exc).__name__,
                    }
                    normalization_failures.append(
                        {
                            "profile_id": assignment["profile_id"],
                            "request_ordinal": entry["ordinal"],
                            "failure_code": "normalization_failed",
                            "arm": "fresh_sealed_validation",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
            validation_rows.append(status)
            completed_history.add(profile_id)
            _private_write(paths["manifests"] / "sealed-validation-status.partial.json", {
                "schema_version": "v61-sealed-validation-status-1.0.0",
                "campaign_id": CAMPAIGN_ID,
                "target_eligible_profiles": VALIDATION_TARGET,
                "candidate_count": VALIDATION_CANDIDATES,
                "assigned_status_count": len(validation_rows),
                "eligible_status_count": sum(row.get("eligibility", {}).get("status") == "eligible" for row in validation_rows),
                "profiles": validation_rows,
                "analytically_evaluated": 0,
                "sealed": True,
            })
            if _storage_bytes(paths["corpus"]) > MAX_STORAGE_BYTES:
                raise RuntimeError("STORAGE_CEILING_EXCEEDED")
            if len(transport.ledger) % 500 == 0:
                _checkpoint(paths, transport.ledger, phase="sealed_validation_history")

        _private_write(paths["manifests"] / "sealed-validation-status.json", {
            "schema_version": "v61-sealed-validation-status-1.0.0",
            "campaign_id": CAMPAIGN_ID,
            "target_eligible_profiles": VALIDATION_TARGET,
            "candidate_count": VALIDATION_CANDIDATES,
            "assigned_status_count": len(validation_rows),
            "eligible_status_count": sum(row.get("eligibility", {}).get("status") == "eligible" for row in validation_rows),
            "profiles": validation_rows,
            "analytically_evaluated": 0,
            "sealed": True,
        })
        (paths["manifests"] / "sealed-validation-status.partial.json").unlink(missing_ok=True)
        _private_write(paths["diagnostics"] / "normalization_failure_ledger.json", normalization_failures)
        _private_write(paths["diagnostics"] / "request_failure_ledger.json", [entry for entry in transport.ledger if entry.get("error")])
        _private_write(paths["diagnostics"] / "cost_ledger.json", _cost_ledger(transport.ledger, _storage_bytes(paths["corpus"])))
        _checkpoint(paths, transport.ledger, phase="complete_collection")
        if _physical_request_count(transport.ledger) > MAX_REQUESTS:
            raise RuntimeError("physical request ceiling exceeded")
    return 0


def _completion_map(profile: Mapping[str, Any]) -> dict[str, bool]:
    rows = list(profile.get("matches", []))
    by_session: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_session[str(row["session_id"])].append(row)
    ordered = sorted(by_session, key=lambda sid: min(int(row["start_time"]) for row in by_session[sid]))
    noncorrupt = [
        sid for sid in ordered if not any(bool(row.get("session_corrupt")) for row in by_session[sid])
    ]
    completed_count = int(profile.get("completed_session_count", 0))
    completed = set(noncorrupt[:completed_count])
    return {
        sid: sid in completed and not any(bool(row.get("session_corrupt")) for row in by_session[sid])
        for sid in ordered
    }


def _profile_records(local: Mapping[str, Any], paths: Mapping[str, Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    old_corpus = local["old_corpus"]
    old_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in canonical_rows(old_corpus):
        old_rows[str(row["profile_id"])].append(dict(row))
    for profile_id in old_corpus.profile_ids:
        profile = old_corpus.profile_summaries[profile_id]
        records.append(
            {
                "profile_id": profile_id,
                "source_arm": "existing_tuning",
                "profile": dict(profile),
                "rows": old_rows[profile_id],
                "completed": dict(old_corpus.completion_for_profile(profile_id)),
            }
        )
    reserve_corpus = local["reserve_corpus"]
    reserve_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in canonical_rows(reserve_corpus):
        reserve_rows[str(row["profile_id"])].append(dict(row))
    for profile_id in reserve_corpus.profile_ids:
        profile = reserve_corpus.profile_summaries[profile_id]
        records.append(
            {
                "profile_id": profile_id,
                "source_arm": "local_reserve",
                "profile": dict(profile),
                "rows": reserve_rows[profile_id],
                "completed": dict(reserve_corpus.completion_for_profile(profile_id)),
            }
        )
    split_payload = _read_json(paths["manifests"] / "split-manifest.json") if (paths["manifests"] / "split-manifest.json").exists() else {"assignments": []}
    selected_external = 0
    for assignment in sorted(
        (row for row in split_payload.get("assignments", []) if row.get("arm") == "tuning"),
        key=lambda row: int(row["position"]),
    ):
        candidates = [
            paths["normalized_tuning"] / f"{assignment['profile_id']}.json.gz",
            paths["normalized_tuning"] / f"{assignment['profile_id']}.json",
        ]
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            continue
        envelope = _read_normalized_envelope(path)
        profile = envelope.get("profile")
        if not isinstance(profile, Mapping):
            continue
        if profile.get("status") != "eligible":
            continue
        selected_external += 1
        profile_id = str(profile["profile_id"])
        records.append(
            {
                "profile_id": profile_id,
                "source_arm": "external_tuning",
                "profile": dict(profile),
                "rows": [dict(row) for row in profile.get("matches", [])],
                "completed": _completion_map(profile),
                "normalized_path": str(path),
                "normalized_sha256": sha256_file(path),
            }
        )
        if selected_external >= EXTERNAL_TUNING_TARGET:
            break
    if len({record["profile_id"] for record in records}) != len(records):
        raise RuntimeError("combined tuning corpus has duplicate pseudonymous profiles")
    return records


def _descriptor(profile: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(profile.get("matches", []))
    starts = [int(row["start_time"]) for row in rows]
    heroes = Counter(int(row["hero_id"]) for row in rows)
    session_lengths = Counter(str(row["session_id"]) for row in rows)
    modes = Counter(str(row["game_mode"]) for row in rows)
    return {
        "total_matches": len(rows),
        "total_sessions": len(session_lengths),
        "median_session_length": statistics.median(session_lengths.values()) if session_lengths else 0,
        "activity_window_days": (max(starts) - min(starts)) / 86_400 if starts else 0.0,
        "dominant_hero_share": max(heroes.values()) / len(rows) if rows else 0.0,
        "qualifying_session_coverage": 0.0,
        "game_mode_composition": {key: value / len(rows) for key, value in modes.items()} if rows else {},
    }


def _fixed_bins() -> dict[str, list[tuple[str, float, float]]]:
    return {
        "match_depth": [("30-59", 30, 60), ("60-119", 60, 120), ("120-239", 120, 240), ("240+", 240, math.inf)],
        "session_count": [("0-39", 0, 40), ("40-79", 40, 80), ("80-159", 80, 160), ("160+", 160, math.inf)],
        "median_session_length": [("1", 0, 2), ("2", 2, 3), ("3", 3, 4), ("4+", 4, math.inf)],
        "activity_window_days": [("<90", 0, 90), ("90-179", 90, 180), ("180-269", 180, 270), ("270+", 270, math.inf)],
        "dominant_hero_share": [("<10%", 0, 0.10), ("10-19%", 0.10, 0.20), ("20-29%", 0.20, 0.30), ("30%+", 0.30, math.inf)],
    }


def _natural_js(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right:
        return 0.0
    total_left, total_right = sum(left), sum(right)
    p = [value / total_left for value in left]
    q = [value / total_right for value in right]
    midpoint = [(a + b) / 2 for a, b in zip(p, q, strict=True)]
    return 0.5 * sum(a * math.log(a / m) for a, m in zip(p, midpoint, strict=True) if a and m) + 0.5 * sum(
        b * math.log(b / m) for b, m in zip(q, midpoint, strict=True) if b and m
    )


def _distribution_audit(old: Sequence[Mapping[str, Any]], new: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    old_descriptors = [_descriptor(profile) for profile in old]
    new_descriptors = [_descriptor(profile) for profile in new]
    output: dict[str, Any] = {
        "population": {"old_profiles": len(old), "new_external_profiles": len(new)},
        "fixed_bins": {},
        "additional_descriptors": {},
        "thresholds": {"natural_log_js_max": 0.10, "absolute_bin_share_difference_max": 0.15},
    }
    for descriptor, bands in _fixed_bins().items():
        key = {
            "match_depth": "total_matches",
            "session_count": "total_sessions",
            "median_session_length": "median_session_length",
            "activity_window_days": "activity_window_days",
            "dominant_hero_share": "dominant_hero_share",
        }[descriptor]
        old_counts = [sum(lower <= float(row[key]) < upper for row in old_descriptors) for _label, lower, upper in bands]
        new_counts = [sum(lower <= float(row[key]) < upper for row in new_descriptors) for _label, lower, upper in bands]
        old_shares = [value / len(old) if old else 0.0 for value in old_counts]
        new_shares = [value / len(new) if new else 0.0 for value in new_counts]
        differences = [abs(a - b) for a, b in zip(old_shares, new_shares, strict=True)]
        output["fixed_bins"][descriptor] = {
            "bands": [label for label, _lower, _upper in bands],
            "old_counts": old_counts,
            "new_counts": new_counts,
            "old_shares": old_shares,
            "new_shares": new_shares,
            "absolute_share_differences": differences,
            "natural_log_js": _natural_js(old_counts, new_counts),
            "pass": _natural_js(old_counts, new_counts) <= 0.10 and max(differences, default=0.0) <= 0.15,
        }
    old_modes = Counter()
    new_modes = Counter()
    for descriptor in old_descriptors:
        old_modes.update(descriptor["game_mode_composition"])
    for descriptor in new_descriptors:
        new_modes.update(descriptor["game_mode_composition"])
    output["additional_descriptors"] = {
        "game_mode_composition": {
            "old": dict(old_modes),
            "new": dict(new_modes),
            "gate": "diagnostic_only",
        },
        "qualifying_session_coverage": {"gate": "diagnostic_only"},
    }
    output["pass"] = bool(output["fixed_bins"]) and all(
        item["pass"] for item in output["fixed_bins"].values()
    ) and len(old) == 791 and len(new) == EXTERNAL_TUNING_TARGET
    return output


def _session_gap_sensitivity(profile: Mapping[str, Any]) -> dict[str, int]:
    rows = list(profile.get("matches", []))
    if not rows:
        return {"60": 0, "90": 0, "120": 0}
    window = profile["collection_window"]
    history = canonical_history(
        rows,
        account_id=1,
        window_start=int(window["start_time"]),
        window_end=int(window["end_time"]),
    )
    return {
        str(gap): sum(
            group.match_count >= 4
            for group in infer_sessions(
                history.normalization.eligible_matches,
                CANONICAL_SESSION_POLICY.__class__(gap_minutes=gap),
                window_start=int(window["start_time"]),
                window_end=int(window["end_time"]),
            ).sessions
        )
        for gap in (60, 90, 120)
    }


def _analyze_profiles(
    paths: Mapping[str, Path],
    local: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    records = _profile_records(local, paths)
    artifact_dir = ROOT / "infra" / "runtime-artifacts" / "free_dna_v61" / "6.1.0"
    bundle = load_v61_artifact_bundle(
        artifact_dir,
        expected_source_revision=ANALYTICAL_SOURCE_SHA,
        expected_dirty_worktree=False,
    )
    resolver = bundle.baseline.resolver()
    taxonomy = current_taxonomy_mapping()
    internal: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        profile = record["profile"]
        rows = list(record["rows"])
        key = _profile_key(str(record["profile_id"]))
        try:
            measured = _measure_profile(
                rows,
                dict(record["completed"]),
                resolver,
                taxonomy,
                dict(bundle.distance_calibration),
            )
        except Exception as exc:
            failures.append(
                {
                    "profile_key": key,
                    "source_arm": record["source_arm"],
                    "failure_code": "analysis_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        dominant = Counter(int(row["hero_id"]) for row in rows).most_common(1)[0]
        reduced_rows = [row for row in rows if int(row["hero_id"]) != dominant[0]]
        reduced = None
        if len(reduced_rows) >= MINIMUM_USABLE_MATCHES:
            try:
                reduced = _measure_profile(
                    reduced_rows,
                    dict(record["completed"]),
                    resolver,
                    taxonomy,
                    dict(bundle.distance_calibration),
                )
            except Exception as exc:
                failures.append(
                    {
                        "profile_key": key,
                        "source_arm": record["source_arm"],
                        "failure_code": "dominant_hero_analysis_failed",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
        odd, even = _session_partitions(rows)
        family_rows: dict[str, dict[str, Any]] = {}
        for family in FAMILIES:
            inference = _infer_family(
                family,
                measured[family],
                seed=int.from_bytes(
                    hashlib.sha256(
                        f"{P_VALUE_SEED_NAMESPACE}:{key}:{family}".encode()
                    ).digest()[:8],
                    "big",
                ),
            )
            noise: list[float] = []
            for component in COMPONENTS[family]:
                effects = measured[family][component]["effects"]
                odd_theta, odd_n = _theta(effects, odd)
                even_theta, even_n = _theta(effects, even)
                if inference["supported"][component] and odd_n >= HALF_MIN_SESSIONS and even_n >= HALF_MIN_SESSIONS:
                    noise.append(abs(odd_theta - even_theta))
            selected = inference["selected_component"]
            selected_effects = measured[family][selected]["effects"] if selected else {}
            theta = inference["theta"].get(selected, 0.0) if selected else 0.0
            direction = math.copysign(1.0, theta) if theta else 0.0
            odd_theta, odd_n = _theta(selected_effects, odd)
            even_theta, even_n = _theta(selected_effects, even)
            split_pass = bool(
                direction
                and odd_n >= HALF_MIN_SESSIONS
                and even_n >= HALF_MIN_SESSIONS
                and odd_theta
                and even_theta
                and math.copysign(1.0, odd_theta) == direction
                and math.copysign(1.0, even_theta) == direction
            )
            robust_theta = 0.0
            robust_supported = False
            if selected and reduced is not None:
                robust_inference = _infer_family(
                    family,
                    reduced[family],
                    seed=int.from_bytes(
                        hashlib.sha256(
                            f"{P_VALUE_SEED_NAMESPACE}:{key}:dominant-excluded:{family}".encode()
                        ).digest()[:8],
                        "big",
                    ),
                )
                robust_theta = robust_inference["theta"].get(selected, 0.0)
                robust_supported = bool(robust_inference["supported"].get(selected, False))
            robust_pass = bool(
                direction and robust_supported and robust_theta and math.copysign(1.0, robust_theta) == direction
            )
            family_rows[family] = {
                "inference": inference,
                "noise": max(noise) if noise else None,
                "split_pass": split_pass,
                "loo_agreement": _loo_agreement(selected_effects, direction),
                "robust_pass": robust_pass,
                "robust_theta": robust_theta,
                "dominant_hero_share": dominant[1] / len(rows) if rows else 0.0,
                "evidence_complete": bool(selected),
                "component_coverage": {
                    component: measured[family][component]["coverage"]
                    for component in COMPONENTS[family]
                },
            }
        derived = {
            "schema_version": "v61-session-drift-derived-profile-1.0.0",
            "campaign_id": CAMPAIGN_ID,
            "provider": "OpenDota",
            "profile_key": key,
            "source_arm": record["source_arm"],
            "input_normalized_digest": record.get("normalized_sha256") or _digest(profile),
            "estimator_version": INFERENCE_VERSION,
            "sessionization_version": CANONICAL_SESSION_POLICY.version,
            "derived_at": _now(),
            "families": family_rows,
        }
        _private_write(paths["derived"] / f"profile-{key}.json", derived)
        internal.append(
            {
                "profile_key": key,
                "source_arm": record["source_arm"],
                "profile": profile,
                "rows": rows,
                "completed": record["completed"],
                "families": family_rows,
                "session_gap_sensitivity": _session_gap_sensitivity(profile),
            }
        )
        if (index + 1) % 100 == 0:
            print(json.dumps({"phase": "analysis", "profiles": index + 1}, sort_keys=True), flush=True)
    if failures:
        _private_write(paths["diagnostics"] / "analysis_failure_ledger.json", failures)
    else:
        _private_write(paths["diagnostics"] / "analysis_failure_ledger.json", [])
    return internal, failures, {"artifact_checksums": dict(bundle.checksums), "source_sha": ANALYTICAL_SOURCE_SHA}


def _apply_family_qualification(internal: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    margins: dict[str, float | None] = {}
    margin_rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        noise = [
            float(row["families"][family]["noise"])
            for row in internal
            if row["families"][family]["noise"] is not None
        ]
        p90 = _quantile(noise, 0.90)
        margins[family] = p90 / 2 if len(noise) >= MIN_MARGIN_PROFILES and p90 is not None else None
        margin_rows.append(
            {
                "family": family,
                "observations": len(noise),
                "noise_p50": _quantile(noise, 0.50),
                "noise_p90": p90,
                "practical_theta_margin": margins[family],
                "status": "CALIBRATED" if margins[family] is not None else "INSUFFICIENT_EVIDENCE",
                "rule": "P90_MAX_COMPONENT_ODD_EVEN_DISAGREEMENT_DIVIDED_BY_TWO",
                "yield_used": False,
            }
        )
    result: list[dict[str, Any]] = []
    for profile in internal:
        p_values = [float(profile["families"][family]["inference"]["family_p"]) for family in FAMILIES]
        bh = _adjust(p_values, by=False)
        by = _adjust(p_values, by=True)
        for index, family in enumerate(FAMILIES):
            data = profile["families"][family]
            inference = data["inference"]
            selected = inference["selected_component"]
            theta = inference["theta"].get(selected, 0.0) if selected else 0.0
            practical = margins[family] is not None and abs(theta) >= float(margins[family])
            stable = bool(data["split_pass"]) and float(data["loo_agreement"]) >= LOO_AGREEMENT
            qualified = bool(
                by[index] <= TARGET_Q
                and practical
                and stable
                and data["robust_pass"]
                and data["evidence_complete"]
            )
            result.append(
                {
                    "profile_key": profile["profile_key"],
                    "source_arm": profile["source_arm"],
                    "family": family,
                    "supported": any(inference["supported"].values()),
                    "selected_component": selected,
                    "family_p": p_values[index],
                    "bh_q_diagnostic": bh[index],
                    "by_q": by[index],
                    "theta": theta,
                    "practical_margin": margins[family],
                    "selected_coverage": data["component_coverage"].get(selected, 0.0) if selected else 0.0,
                    "practical_pass": practical,
                    "split_half_pass": data["split_pass"],
                    "loo_agreement": data["loo_agreement"],
                    "loo_pass": float(data["loo_agreement"]) >= LOO_AGREEMENT,
                    "dominant_hero_share": data["dominant_hero_share"],
                    "dominant_hero_robustness_pass": data["robust_pass"],
                    "candidate_qualified": qualified,
                    "component_p": inference["component_p"],
                    "component_theta": inference["theta"],
                    "component_sessions": inference["informative_sessions"],
                }
            )
    result.sort(key=lambda row: (row["profile_key"], FAMILIES.index(row["family"])))
    return result, margin_rows


def _support_report(internal: Sequence[Mapping[str, Any]], family_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {"by_arm": {}, "families": {}}
    for arm in ("existing_tuning", "local_reserve", "external_tuning"):
        profiles = [row for row in internal if row["source_arm"] == arm]
        session = [row["families"]["session_drift"] for row in profiles]
        output["by_arm"][arm] = {
            "profiles": len(profiles),
            "session_supported": sum(bool(row["inference"]["supported"].get("late_minus_early_result")) for row in session),
            "session_margin_observations": sum(row["noise"] is not None for row in session),
            "session_split_pass": sum(bool(row["split_pass"]) for row in session),
            "session_loo_pass": sum(float(row["loo_agreement"]) >= LOO_AGREEMENT for row in session),
            "session_dominant_hero_pass": sum(bool(row["robust_pass"]) for row in session),
        }
    for family in FAMILIES:
        rows = [row for row in family_rows if row["family"] == family]
        supported = [row for row in rows if row["supported"]]
        directions = Counter("positive" if row["theta"] > 0 else "negative" if row["theta"] < 0 else "zero" for row in supported)
        output["families"][family] = {
            "profiles": len(rows),
            "supported": len(supported),
            "raw_p_at_0_05": sum(row["family_p"] <= TARGET_Q for row in rows),
            "bh_q_at_0_05": sum(row["bh_q_diagnostic"] <= TARGET_Q for row in rows),
            "by_q_at_0_05": sum(row["by_q"] <= TARGET_Q for row in rows),
            "candidate_qualified_before_product_cap": sum(row["candidate_qualified"] for row in rows),
            "positive_direction": directions.get("positive", 0),
            "negative_direction": directions.get("negative", 0),
            "zero_direction": directions.get("zero", 0),
            "publication_yield_optimized": False,
        }
    return output


def _empirical_correlation(family_rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    by_profile: dict[str, dict[str, float]] = defaultdict(dict)
    for row in family_rows:
        value = float(row["family_p"])
        if math.isfinite(value):
            by_profile[str(row["profile_key"])][str(row["family"])] = min(max(value, 0.0), 1.0)
    matrix = [
        [values[family] for family in FAMILIES]
        for values in by_profile.values()
        if all(family in values for family in FAMILIES)
    ]
    if len(matrix) < 3:
        return np.eye(len(FAMILIES))
    ranked: list[list[float]] = []
    normal = NormalDist()
    for column in zip(*matrix, strict=True):
        ordered = sorted(enumerate(column), key=lambda item: (item[1], item[0]))
        ranks = [0.0] * len(column)
        start = 0
        while start < len(ordered):
            end = start + 1
            while end < len(ordered) and ordered[end][1] == ordered[start][1]:
                end += 1
            midpoint = (start + 1 + end) / 2
            for offset in range(start, end):
                ranks[ordered[offset][0]] = midpoint
            start = end
        ranked.append([normal.inv_cdf((rank - 0.5) / len(column)) for rank in ranks])
    correlation = np.corrcoef(np.asarray(ranked), rowvar=True)
    correlation = np.asarray(correlation, dtype=float)
    correlation = (correlation + correlation.T) / 2
    values, vectors = np.linalg.eigh(correlation)
    values = np.maximum(values, 1e-8)
    correlation = vectors @ np.diag(values) @ vectors.T
    diagonal = np.sqrt(np.diag(correlation))
    correlation = correlation / diagonal[:, None] / diagonal[None, :]
    np.fill_diagonal(correlation, 1.0)
    return correlation


def _p_matrix_batch(
    rng: np.random.Generator,
    *,
    count: int,
    scenario: str,
    covariance: np.ndarray,
    empirical: bool,
    empirical_correlation: np.ndarray | None = None,
) -> tuple[np.ndarray, list[set[int]]]:
    sessions = 36
    if empirical:
        latent = rng.multivariate_normal(
            np.zeros(len(FAMILIES)),
            empirical_correlation if empirical_correlation is not None else np.eye(len(FAMILIES)),
            size=count,
        )
        normal = NormalDist()
        p_matrix = np.asarray([[normal.cdf(float(value)) for value in row] for row in latent])
    else:
        latent = rng.multivariate_normal(np.zeros(len(FAMILIES)), covariance, size=(count, sessions))
        p_matrix = np.ones((count, len(FAMILIES)))
        null_masks: list[set[int]] = []
        for dataset in range(count):
            if scenario == "global_null":
                null_masks.append(set(range(len(FAMILIES))))
            elif scenario == "one_moderate_alternative":
                null_masks.append({1, 2})
            else:
                null_masks.append({dataset % len(FAMILIES)})
        for family_index, family in enumerate(FAMILIES):
            names = COMPONENTS[family]
            values = rng.choice((-1.0, 1.0), size=(count, sessions, len(names)))
            null = np.asarray([family_index in mask for mask in null_masks])
            latent_sign = np.where(latent[:, :, family_index] >= 0, 1.0, -1.0)
            alternative_sign = np.where(
                rng.random((count, sessions)) < 0.65, 1.0, -1.0
            )
            values[:, :, 0] = np.where(null[:, None], latent_sign, alternative_sign)
            opportunities = np.full((count, len(names)), 90)
            p_matrix[:, family_index] = _family_p(
                values, opportunities, draws=MULTIPLICITY_DRAWS, rng=rng
            )[0]
        return p_matrix, null_masks
    null_masks = [
        set(range(len(FAMILIES))) if scenario == "global_null" else {1, 2}
        for _ in range(count)
    ]
    if scenario == "one_moderate_alternative":
        p_matrix[:, 0] = np.minimum(p_matrix[:, 0], rng.beta(1.0, 5.0, size=count))
    return p_matrix, null_masks


def _multiplicity_validation(
    family_rows: Sequence[Mapping[str, Any]], *, repetitions: int = MULTIPLICITY_REPETITIONS
) -> dict[str, Any]:
    if repetitions < MULTIPLICITY_REPETITIONS:
        raise ValueError("m=3 multiplicity validation requires 10,000 datasets per cell")
    rng = np.random.default_rng(MULTIPLICITY_SEED)
    correlations = {
        "independent": np.eye(len(FAMILIES)),
        "feasible_negative": np.full((len(FAMILIES), len(FAMILIES)), -0.25),
        "rho_0.5": np.full((len(FAMILIES), len(FAMILIES)), 0.50),
        "rho_0.9": np.full((len(FAMILIES), len(FAMILIES)), 0.90),
    }
    for matrix in correlations.values():
        np.fill_diagonal(matrix, 1.0)
    empirical = _empirical_correlation(family_rows)
    rows: list[dict[str, Any]] = []
    cells = [(name, covariance, False) for name, covariance in correlations.items()]
    cells.extend(
        [
            ("empirical_tuning_dependence", empirical, True),
        ]
    )
    for dependence, covariance, is_empirical in cells:
        scenarios = ("global_null", "one_moderate_alternative", "subset_nulls")
        for scenario in scenarios:
            false_discovery_proportions: dict[str, list[float]] = {"BH": [], "BY": []}
            false_discovery_events: dict[str, int] = {"BH": 0, "BY": 0}
            for start in range(0, repetitions, 200):
                count = min(200, repetitions - start)
                p_matrix, null_masks = _p_matrix_batch(
                    rng,
                    count=count,
                    scenario=scenario,
                    covariance=covariance,
                    empirical=is_empirical,
                    empirical_correlation=empirical if is_empirical else None,
                )
                for dataset in range(count):
                    for procedure, by in (("BH", False), ("BY", True)):
                        adjusted = _adjust(p_matrix[dataset].tolist(), by=by)
                        rejected = {
                            index for index, value in enumerate(adjusted) if value <= TARGET_Q
                        }
                        false = len(rejected & null_masks[dataset])
                        false_discovery_proportions[procedure].append(false / max(1, len(rejected)))
                        false_discovery_events[procedure] += bool(false)
            for procedure in ("BH", "BY"):
                fdr = float(np.mean(false_discovery_proportions[procedure]))
                event_rate = false_discovery_events[procedure] / repetitions
                lower, upper = _wilson(false_discovery_events[procedure], repetitions)
                null_family_count = {
                    "global_null": len(FAMILIES),
                    "one_moderate_alternative": 2,
                    "subset_nulls": 1,
                }[scenario]
                rows.append(
                    {
                        "dependence": dependence,
                        "scenario": scenario,
                        "procedure": procedure,
                        "repetitions": repetitions,
                        "null_draws_per_dataset": MULTIPLICITY_DRAWS,
                        "null_family_count": null_family_count,
                        "estimated_fdr": fdr,
                        "false_discovery_event_rate": event_rate,
                        "wilson_lower_bound": lower,
                        "wilson_upper_bound": upper,
                        "acceptance_fdr_max": MULTIPLICITY_MAX_FDR,
                        "acceptance_wilson_lower_max": TARGET_Q,
                        "verdict": "PASS" if fdr <= MULTIPLICITY_MAX_FDR and lower <= TARGET_Q else "FAIL",
                        "p_generation": "signed_prevalence_2000_draw" if not is_empirical else "empirical_tuning_gaussian_copula_stress",
                    }
                )
    by_rows = [row for row in rows if row["procedure"] == "BY" and row["null_family_count"] > 0]
    return {
        "schema_version": "v61-session-drift-m3-multiplicity-1.0.0",
        "family_universe": [FAMILY_LABELS[family] for family in FAMILIES],
        "fixed_m": 3,
        "q": TARGET_Q,
        "release_procedure": "Benjamini-Yekutieli",
        "bh_status": "diagnostic comparator only",
        "seed": MULTIPLICITY_SEED,
        "repetitions_per_cell": repetitions,
        "null_draws_per_dataset": MULTIPLICITY_DRAWS,
        "registered_scenarios": [
            "global null",
            "one moderate alternative",
            "subset nulls",
            "independent",
            "feasible negative dependence",
            "rho=.5",
            "rho=.9",
            "empirical tuning dependence",
        ],
        "empirical_rank_gaussian_correlation": empirical.tolist(),
        "rows": rows,
        "by_acceptance": all(row["verdict"] == "PASS" for row in by_rows),
        "yield_optimization": False,
    }


def _beta_binomial_interval(n: int, successes: int, total: int) -> tuple[int, int]:
    alpha = successes + 0.5
    beta = total - successes + 0.5
    log_beta = math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)
    terms = []
    for value in range(n + 1):
        terms.append(
            math.lgamma(n + 1)
            - math.lgamma(value + 1)
            - math.lgamma(n - value + 1)
            + math.lgamma(alpha + value)
            + math.lgamma(beta + n - value)
            - math.lgamma(alpha + beta + n)
            - log_beta
        )
    peak = max(terms)
    probabilities = [math.exp(value - peak) for value in terms]
    normalizer = sum(probabilities)
    probabilities = [value / normalizer for value in probabilities]
    tail = (1 - 0.994444444) / 2
    cumulative = 0.0
    lower = 0
    for value, probability in enumerate(probabilities):
        cumulative += probability
        if cumulative >= tail:
            lower = value
            break
    cumulative = 0.0
    upper = n
    for value, probability in enumerate(probabilities):
        cumulative += probability
        if cumulative >= 1 - tail:
            upper = value
            break
    return lower, upper


def _predictive_intervals(family_rows: Sequence[Mapping[str, Any]], tuning_count: int) -> dict[str, Any]:
    output: dict[str, Any] = {
        "schema_version": "v61-session-drift-predictive-intervals-1.0.0",
        "validation_profiles": VALIDATION_TARGET,
        "central_probability": 0.994444444,
        "bonferroni_checks": 9,
        "families": {},
    }
    for family in FAMILIES:
        rows = [row for row in family_rows if row["family"] == family]
        supported = sum(bool(row["supported"]) for row in rows)
        positive = sum(bool(row["supported"]) and row["theta"] > 0 for row in rows)
        qualified = sum(bool(row["candidate_qualified"]) for row in rows)
        output["families"][family] = {
            "supported_profile_count": {"observed": supported, "interval": list(_beta_binomial_interval(VALIDATION_TARGET, supported, tuning_count))},
            "positive_direction_supported_count": {"observed": positive, "interval": list(_beta_binomial_interval(VALIDATION_TARGET, positive, tuning_count))},
            "qualified_before_product_cap_count": {"observed": qualified, "interval": list(_beta_binomial_interval(VALIDATION_TARGET, qualified, tuning_count))},
        }
    return output


def _session_hardening(
    internal: Sequence[Mapping[str, Any]],
    family_rows: Sequence[Mapping[str, Any]],
    failures: Sequence[Mapping[str, Any]],
    *,
    run_type1: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    session = [row for row in family_rows if row["family"] == "session_drift"]
    supported = [row for row in session if row["supported"]]
    noise = [float(row["families"]["session_drift"]["noise"]) for row in internal if row["families"]["session_drift"]["noise"] is not None]
    sensitivity = Counter()
    for profile in internal:
        sensitivity.update(profile["session_gap_sensitivity"])
    type1_summary: list[dict[str, Any]] = []
    if run_type1:
        _detail, type1_summary = _simulate_type1(
            repetitions=1_000,
            draws=MULTIPLICITY_DRAWS,
            seed=MULTIPLICITY_SEED,
            batch_size=100,
        )
        type1_summary = [row for row in type1_summary if row["family"] in FAMILIES]
    type1_pass = run_type1 and all(row["verdict"] == "PASS" for row in type1_summary)
    row = {
        "schema_version": "v61-session-drift-hardening-1.0.0",
        "supported_profiles": len(supported),
        "margin_observations": len(noise),
        "split_half_pass": sum(bool(item["split_half_pass"]) for item in supported),
        "loo_pass": sum(bool(item["loo_pass"]) for item in session if item["supported"]),
        "dominant_hero_robustness_pass": sum(bool(item["dominant_hero_robustness_pass"]) for item in supported),
        "evidence_complete": all(bool(item["selected_component"]) for item in session),
        "failure_count": len(failures),
        "failure_rate": len(failures) / max(1, len(internal)),
        "margin_sensitivity": {
            "p90": _quantile(noise, 0.90),
            "p90_excluding_max": _quantile(sorted(noise)[:-1], 0.90) if len(noise) > 1 else None,
        },
        "session_count_sensitivity": dict(sorted(sensitivity.items())),
        "type1": {
            "run": run_type1,
            "pass": type1_pass,
            "scenarios": type1_summary,
        },
        "pass": bool(run_type1 and type1_pass and not failures),
    }
    return row, type1_summary


def _data_dictionary() -> dict[str, Any]:
    rows = [
        ("profile_id", "campaign salted pseudonym", "none", "stable research profile key", "identifier", "never missing", "cohort identity", "not semantically comparable", "NO"),
        ("collection_window", "campaign metadata", "none", "inclusive 365-day window", "unix seconds", "required", "window boundary", "not provider data", "NO"),
        ("status", "frozen eligibility rule", "none", "canonical profile eligibility", "label", "required", "profile inclusion", "not a provider measurement", "NO"),
        ("eligible_match_count", "frozen eligibility rule", "none", "matches after normalization/window filtering", "matches", "zero allowed for ineligible profiles", "minimum 30 gate", "not a provider count guarantee", "NEEDS MAPPING"),
        ("session_count", "frozen sessionizer", "derived", "inferred chronological sessions", "sessions", "zero allowed", "session support", "not an OpenDota field", "NEEDS MAPPING"),
        ("completed_session_count", "frozen sessionizer", "derived", "boundary-safe completed sessions", "sessions", "zero allowed", "Session Drift support", "censoring depends on collection window", "NEEDS MAPPING"),
        ("match_id", "OpenDota summary", "match_id", "provider match identifier", "integer", "invalid rows excluded", "deduplication", "provider identifier; local corpus only", "NEEDS MAPPING"),
        ("start_time", "OpenDota summary", "start_time", "match start timestamp", "unix seconds", "missing/invalid excluded", "window/session chronology", "provider clock and boundary semantics", "NEEDS MAPPING"),
        ("duration_seconds", "OpenDota summary", "duration", "match duration", "seconds", "missing or <300 excluded", "eligibility/session end", "summary duration may differ from replay detail", "NEEDS MAPPING"),
        ("won", "OpenDota summary", "player_slot + radiant_win", "target player's result", "boolean", "missing side/outcome excluded", "all result families", "derived from side and game outcome", "NEEDS MAPPING"),
        ("hero_id", "OpenDota summary", "hero_id", "hero selected in match", "integer", "missing/non-positive excluded", "portfolio/family features", "provider hero catalog mapping required", "NEEDS MAPPING"),
        ("kills", "OpenDota summary", "kills", "target player kills", "count", "missing/negative excluded", "activity/features", "summary statistic", "NEEDS MAPPING"),
        ("deaths", "OpenDota summary", "deaths", "target player deaths", "count", "missing/negative excluded", "survival/features", "summary statistic", "NEEDS MAPPING"),
        ("assists", "OpenDota summary", "assists", "target player assists", "count", "missing/negative excluded", "activity/features", "summary statistic", "NEEDS MAPPING"),
        ("leaver_status", "OpenDota summary", "leaver_status", "provider abandon status", "enum", "only 0/1 retained; 2-5 excluded", "eligibility", "provider-specific status meanings", "NEEDS MAPPING"),
        ("game_mode", "OpenDota summary", "game_mode", "match mode", "enum", "only 1/22 retained", "eligibility", "provider enum mapping required", "NEEDS MAPPING"),
        ("lobby_type", "OpenDota summary", "lobby_type", "lobby category", "enum", "only 0/7 retained", "eligibility", "provider enum mapping required", "NEEDS MAPPING"),
        ("player_slot", "OpenDota summary", "player_slot", "target side slot", "integer", "missing excludes result", "outcome derivation", "side mapping is provider-specific", "NEEDS MAPPING"),
        ("radiant_win", "OpenDota summary", "radiant_win", "match-side result", "boolean", "missing excludes result", "outcome derivation", "side outcome must be aligned", "NEEDS MAPPING"),
        ("hero_variant", "OpenDota summary", "hero_variant", "provider hero variant", "integer", "nullable", "optional", "provider-specific and sparse", "NEEDS MAPPING"),
        ("party_size", "OpenDota summary", "party_size", "provider party size", "count", "nullable", "optional", "provider availability is sparse", "NEEDS MAPPING"),
        ("lane", "OpenDota summary", "lane", "provider lane enum", "enum", "nullable", "optional", "not a universal role label", "NEEDS MAPPING"),
        ("lane_role", "OpenDota summary", "lane_role", "provider lane-role enum", "enum", "nullable", "optional", "not equivalent to position", "NEEDS MAPPING"),
        ("is_roaming", "OpenDota summary", "is_roaming", "provider roaming flag", "boolean", "nullable", "optional", "provider-specific and sparse", "NEEDS MAPPING"),
        ("source_version", "OpenDota summary", "version", "provider source version", "label", "nullable", "audit", "provider version semantics", "NEEDS MAPPING"),
        ("session_id", "frozen sessionizer", "derived", "deterministic inferred session id", "label", "required for eligible rows", "session clustering", "not a provider session identifier", "NEEDS MAPPING"),
        ("session_index", "frozen sessionizer", "derived", "chronological match position in session", "integer", "required for eligible rows", "early/late split", "not a provider field", "NEEDS MAPPING"),
        ("session_corrupt", "frozen sessionizer", "derived", "clock-overlap corruption flag", "boolean", "required for eligible rows", "completed-session exclusion", "not a provider field", "NEEDS MAPPING"),
    ]
    fields = []
    for field, provider, raw_path, meaning, unit, missingness, relevance, caveat, comparable in rows:
        fields.append(
            {
                "field": field,
                "provider_source": provider,
                "raw_path": raw_path,
                "normalized_meaning": meaning,
                "unit": unit,
                "missingness_rule": missingness,
                "eligibility_relevance": relevance,
                "known_semantic_caveat": caveat,
                "normalizer_version": SUMMARY_HISTORY_NORMALIZATION_VERSION if provider == "OpenDota summary" else CANONICAL_SESSION_POLICY.version if "session" in field else "campaign-metadata-1.0.0",
                "safe_for_cross_provider_comparison": comparable,
            }
        )
    return {
        "schema_version": "v61-opendota-data-dictionary-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "provider": "OpenDota",
        "fields": fields,
        "cross_provider_rule": "No OpenDota field is re-attributed to STRATZ; every future join needs an explicit mapping.",
    }


def _write_collection_artifacts(paths: Mapping[str, Path], *, status: str) -> dict[str, Any]:
    ledger = _read_jsonl(paths["diagnostics"] / "request_ledger.jsonl")
    raw_files = [
        {
            "ordinal": entry["ordinal"],
            "path": entry.get("raw_artifact_path"),
            "sha256": entry.get("response_sha256"),
            "bytes": int(entry.get("response_bytes") or 0),
            "http_status": entry.get("http_status"),
        }
        for entry in ledger
        if entry.get("raw_artifact_path")
    ]
    normalized_files = []
    normalized_paths = sorted(paths["normalized_tuning"].glob("*.json.gz"))
    normalized_paths.extend(sorted(paths["normalized_tuning"].glob("*.json")))
    for path in normalized_paths:
        envelope = _read_normalized_envelope(path)
        profile = envelope.get("profile", {})
        normalized_files.append(
            {
                "profile_id": profile.get("profile_id"),
                "status": profile.get("status"),
                "path": str(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "encoding": "gzip-json" if path.suffix == ".gz" else "json",
            }
        )
    raw_manifest = {
        "schema_version": "v61-opendota-raw-corpus-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "provider": "OpenDota",
        "raw_response_count": len(raw_files),
        "raw_bytes": sum(row["bytes"] for row in raw_files),
        "responses": raw_files,
        "raw_corpus_digest": _digest(raw_files),
        "immutable_after_capture": True,
    }
    normalized_manifest = {
        "schema_version": "v61-opendota-normalized-corpus-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "provider": "OpenDota",
        "normalizer_version": SUMMARY_HISTORY_NORMALIZATION_VERSION,
        "canonical_schema_version": CANONICAL_SCHEMA_VERSION,
        "normalized_profile_count": len(normalized_files),
        "eligible_profile_count": sum(row["status"] == "eligible" for row in normalized_files),
        "profiles": normalized_files,
        "normalized_corpus_digest": _digest([(row["profile_id"], row["sha256"]) for row in normalized_files]),
        "sealed_validation_normalized_files": 0,
        "normalized_encoding": "gzip-json",
    }
    split_path = paths["manifests"] / "split-manifest.json"
    frame_path = paths["manifests"] / "fixed-frame-manifest.json"
    split_payload = _read_json(split_path) if split_path.exists() else {}
    frame_payload = _read_json(frame_path) if frame_path.exists() else {}
    split_digest = sha256_file(split_path) if split_path.exists() else None
    request_digest = sha256_payload(request_manifest())
    costs = _cost_ledger(ledger, _storage_bytes(paths["corpus"]) + _storage_bytes(paths["diagnostics"]))
    collection = {
        "schema_version": "v61-session-drift-collection-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "provider": "OpenDota",
        "status": status,
        "fixed_frame_size": len(frame_payload.get("ranked_frame", [])),
        "tuning_arm_size": split_payload.get("tuning_arm_size", 0),
        "validation_arm_size": split_payload.get("validation_arm_size", 0),
        "fixed_public_page_requests": PUBLIC_PAGES,
        "fixed_detail_requests": DETAIL_REQUESTS,
        "physical_request_count": _physical_request_count(ledger),
        "raw_response_count": len(raw_files),
        "normalized_profile_count": len(normalized_files),
        "validation_analytically_evaluated": 0,
        "adaptive_top_up": False,
        "long_session_enrichment": False,
        "old_holdout_used": False,
        "fresh_validation_status_path": str(paths["manifests"] / "sealed-validation-status.json"),
        "request_manifest_digest": request_digest,
        "split_manifest_digest": split_digest,
        "updated_at": _now(),
    }
    _private_write(paths["corpus"] / "raw" / "raw-corpus-manifest.json", raw_manifest)
    _private_write(paths["corpus"] / "normalized" / "normalized-corpus-manifest.json", normalized_manifest)
    _private_write(paths["diagnostics"] / "raw_corpus_manifest.json", raw_manifest)
    _private_write(paths["diagnostics"] / "normalized_corpus_manifest.json", normalized_manifest)
    _private_write(paths["diagnostics"] / "collection_manifest.json", collection)
    _private_write(paths["diagnostics"] / "cost_ledger.json", costs)
    _private_write(paths["diagnostics"] / "data_dictionary.json", _data_dictionary())
    _private_write(
        paths["diagnostics"] / "fixed_frame_manifest.json",
        {
            "schema_version": frame_payload.get("schema_version"),
            "campaign_id": CAMPAIGN_ID,
            "seed_match_count": frame_payload.get("seed_match_count", 0),
            "detail_request_count": frame_payload.get("detail_request_count", 0),
            "positive_public_account_count": frame_payload.get("positive_public_account_count", 0),
            "known_exclusion_count": frame_payload.get("known_exclusion_count", 0),
            "retained_frame_size": len(frame_payload.get("ranked_frame", [])),
            "adaptive_top_up": False,
        },
    )
    _private_write(
        paths["diagnostics"] / "split_manifest.json",
        {
            "schema_version": split_payload.get("schema_version"),
            "campaign_id": CAMPAIGN_ID,
            "candidate_frame_size": split_payload.get("candidate_frame_size", 0),
            "tuning_arm_size": split_payload.get("tuning_arm_size", 0),
            "validation_arm_size": split_payload.get("validation_arm_size", 0),
            "tuning_target_eligible": EXTERNAL_TUNING_TARGET,
            "validation_target_eligible": VALIDATION_TARGET,
            "salt_sha256": split_payload.get("salt_sha256"),
            "split_manifest_digest": split_digest,
        },
    )
    _private_write(paths["diagnostics"] / "reusable_corpus_manifest.json", {
        "campaign_id": CAMPAIGN_ID,
        "provider": "OpenDota",
        "collection_date_range": [
            min((entry["requested_at"] for entry in ledger), default=None),
            max((entry["completed_at"] for entry in ledger), default=None),
        ],
        "candidate_frame_version": frame_payload.get("schema_version"),
        "raw_capture_version": raw_manifest["schema_version"],
        "normalized_schema_version": CANONICAL_SCHEMA_VERSION,
        "normalizer_version": SUMMARY_HISTORY_NORMALIZATION_VERSION,
        "eligibility_version": "v61-summary-eligibility-2.0.0",
        "sessionization_version": CANONICAL_SESSION_POLICY.version,
        "split_manifest_version": split_payload.get("schema_version"),
        "pseudonymization_version": "sha256(salt||decimal_account_id)-1.0.0; HMAC-SHA256 ranking",
        "raw_response_count": len(raw_files),
        "raw_bytes": raw_manifest["raw_bytes"],
        "normalized_profile_count": len(normalized_files),
        "tuning_profile_count": normalized_manifest["eligible_profile_count"],
        "sealed_validation_profile_count": VALIDATION_TARGET if (paths["manifests"] / "sealed-validation-status.json").exists() else 0,
        "request_manifest_digest": request_digest,
        "raw_corpus_digest": raw_manifest["raw_corpus_digest"],
        "normalized_corpus_digest": normalized_manifest["normalized_corpus_digest"],
        "split_manifest_digest": split_digest,
        "allowed_future_uses": ["reproducibility", "bug investigation", "new offline descriptive feature research", "future calibration research", "V7 cross-provider comparison", "V7 OpenDota+STRATZ feature research", "provider disagreement studies"],
        "forbidden_future_uses": ["relabeling OpenDota data as STRATZ", "using V6.1 fresh validation as V7 holdout", "unsealing validation for tuning", "changing historical provenance"],
    })
    return {"raw": raw_manifest, "normalized": normalized_manifest, "collection": collection, "cost": costs}


def _write_analysis_artifacts(
    paths: Mapping[str, Path],
    *,
    internal: Sequence[Mapping[str, Any]],
    family_rows: Sequence[Mapping[str, Any]],
    margin_rows: Sequence[Mapping[str, Any]],
    support: Mapping[str, Any],
    distribution: Mapping[str, Any],
    hardening: Mapping[str, Any],
    multiplicity: Mapping[str, Any],
    predictive: Mapping[str, Any],
    aggregate: Mapping[str, Any],
) -> None:
    _private_write(paths["diagnostics"] / "profile_family_results.json", list(family_rows))
    _private_write(paths["diagnostics"] / "old_vs_new_support_report.json", support)
    _private_write(paths["diagnostics"] / "distribution_continuity_audit.json", distribution)
    _private_write(paths["diagnostics"] / "session_margin_calibration.json", {
        "schema_version": "v61-session-drift-margin-calibration-1.0.0",
        "existing_margin_observations": 62,
        "new_local_reserve_observations": support["by_arm"].get("local_reserve", {}).get("session_margin_observations", 0),
        "new_external_observations": support["by_arm"].get("external_tuning", {}).get("session_margin_observations", 0),
        "combined_margin_observations": aggregate["session_drift"]["combined_margin_observations"],
        "families": list(margin_rows),
        "session_rule": "linearly interpolated P90 at (n-1)*.90 divided by two",
        "yield_used": False,
    })
    _private_write(paths["diagnostics"] / "session_hardening.json", hardening)
    _private_write(paths["diagnostics"] / "m3_multiplicity.json", multiplicity)
    _private_write(paths["diagnostics"] / "tuning_only_product_diagnostic.json", aggregate["tuning_only_diagnostic"])
    _private_write(paths["diagnostics"] / "predictive_intervals.json", predictive)
    _private_write(paths["diagnostics"] / "aggregate_summary.json", aggregate)


def _evidence_markdown(
    aggregate: Mapping[str, Any],
    *,
    collection: Mapping[str, Any],
    corpus: Mapping[str, Any],
    diagnostics_path: Path,
) -> str:
    session = aggregate["session_drift"]
    cost = aggregate["cost"]
    tuning = aggregate["tuning"]
    multiplicity = aggregate["multiplicity"]
    diagnostic = aggregate["tuning_only_diagnostic"]
    status = aggregate["status"]
    return f"""# V6.1 Session Drift Phase 2 Execution

## Status
{status}

This is a research-only execution record. OpenDota-derived data remains
provider-specific, validation remains sealed, and no production analytical
behavior was changed.

## Collection
- fixed candidate frame: {collection.get('fixed_frame_size', 0)} (target {FRAME_SIZE})
- physical OpenDota requests: {collection.get('physical_request_count', 0)}
- request ceiling: {MAX_REQUESTS}
- estimated/API-recorded cost: {cost.get('estimated_cost_idr_whole_100_call_blocks', 0):.0f} IDR under owner-supplied assumption
- owner cost ceiling: 12,000 IDR
- retained storage: {cost.get('cumulative_storage_mib', 0):.2f} MiB
- storage ceiling: 600 MiB
- adaptive top-ups: NO

## Reusable corpus
- raw/provider layer: `{CORPUS_DIRNAME}/raw/`, immutable OpenDota response bodies with request ledger, status, bytes, and SHA-256
- normalized layer: `{CORPUS_DIRNAME}/normalized/`, frozen summary-history normalizer `{SUMMARY_HISTORY_NORMALIZATION_VERSION}` and canonical schema `{CANONICAL_SCHEMA_VERSION}`
- manifest/digest: raw `{corpus.get('raw_corpus_digest')}`, normalized `{corpus.get('normalized_corpus_digest')}`, split `{corpus.get('split_manifest_digest')}`
- pseudonymous identity: existing salted SHA-256 profile IDs plus private HMAC ranking; secret digest only
- V7/STRATZ reuse readiness: READY FOR FUTURE PROTOCOL, provider-specific layers remain separate
- important limitations: summary-only OpenDota data, sparse provider fields, no semantic equivalence with STRATZ, no validation reuse

## Tuning
- existing tuning profiles: {tuning.get('existing', 0)}
- safe local reserves used: {tuning.get('local_reserve', 0)}
- new external eligible tuning profiles: {tuning.get('external', 0)}
- final tuning profiles: {tuning.get('final', 0)}

## Session Drift
- existing margin observations: {session.get('existing_margin_observations', 0)}
- new margin observations: {session.get('new_margin_observations', 0)}
- combined margin observations: {session.get('combined_margin_observations', 0)}
- practical margin: {session.get('practical_margin')}
- hardening: {session.get('hardening_status')}
- verdict: {session.get('verdict')}

## Three-family candidate
1. Transfer
2. Post-Loss
3. Session Drift

Presence & Exposure: DEFERRED

## Multiplicity
- procedure: Benjamini-Yekutieli
- q: 0.05
- stress result: {multiplicity.get('status', 'NOT_RUN')} (fixed m=3; BH diagnostic only)

## Tuning-only diagnostic
- 0 Findings: {diagnostic.get('counts', {}).get('0', 0)}
- 1 Finding: {diagnostic.get('counts', {}).get('1', 0)}
- 2 Findings: {diagnostic.get('counts', {}).get('2', 0)}
- 3 Findings: {diagnostic.get('counts', {}).get('3', 0)}
- NOT USED FOR TUNING DECISIONS: YES

## Fresh sealed validation
- target eligible profiles: {VALIDATION_TARGET}
- collected/assigned: {aggregate.get('validation', {}).get('assigned', 0)}
- analytically evaluated: 0
- status: SEALED

## Cost
- physical requests: {cost.get('physical_request_count', 0)}
- owner-supplied rate: Rp200 / 100 calls; $0.01 / 100 calls
- estimated IDR: {cost.get('estimated_cost_idr_whole_100_call_blocks', 0):.0f}
- hard ceiling: 12,000
- exceeded: {'NO' if cost.get('within_ceiling') else 'YES'}

## Next status
{aggregate.get('next_status')}

## Integration
- branch head at analysis: {aggregate.get('branch_head_at_analysis')}
- latest main: {aggregate.get('latest_main')}
- integration performed: NO
- recommended method: review this execution commit, then integrate tracked research code/evidence after owner approval; preserve local corpus outside main

## Branch / worktree disposition
- execution branch: execution/v61-session-drift-phase2
- base SHA: {PHASE1_SHA}
- final SHA: pending execution commit
- temporary worktree removed: pending final verification
- merged to main: NO
- should merge now: WAIT
- dependencies that must land first: NONE
- recommended integration order: 1. owner review; 2. merge tracked execution code/evidence if approved; 3. preserve local corpus and run a separately authorized validation/integration task
- raw/local corpus committed to main: NO

## Files / artifacts
- tracked runner: `scripts/v61_session_drift_phase2.py`
- tracked evidence: `docs/evidence/free-dna-v6.1-session-drift-phase2-execution-2026-08-28.md`
- local diagnostics: `{diagnostics_path}`
- local reusable corpus: `.local/corpora/opendota/{CORPUS_DIRNAME}/`

## Integrity
- old revealed holdout used = NO
- fresh sealed validation evaluated = NO
- thresholds lowered = NO
- Session minimum lowered = NO
- long-session enrichment = NO
- adaptive top-up = NO
- raw provider provenance preserved = YES
- OpenDota data re-attributed to STRATZ = NO
- production analytical behavior changed = NO
- deployment = NO
"""


def _analyze(paths: Mapping[str, Path], local_root: Path, *, multiplicity_repetitions: int) -> dict[str, Any]:
    local = _validate_selected_local_data(local_root)
    collection_info = _write_collection_artifacts(paths, status="COLLECTED")
    internal, failures, artifact_info = _analyze_profiles(paths, local)
    old = [row for row in internal if row["source_arm"] == "existing_tuning"]
    external = [row for row in internal if row["source_arm"] == "external_tuning"]
    family_rows, margin_rows = _apply_family_qualification(internal)
    support = _support_report(internal, family_rows)
    distribution = _distribution_audit(
        [row["profile"] for row in old], [row["profile"] for row in external]
    )
    session_margin_rows = [row for row in margin_rows if row["family"] == "session_drift"]
    session_margin = session_margin_rows[0] if session_margin_rows else {}
    session_arm = support["by_arm"]
    existing_observations = int(session_arm.get("existing_tuning", {}).get("session_margin_observations", 0))
    local_observations = int(session_arm.get("local_reserve", {}).get("session_margin_observations", 0))
    external_observations = int(session_arm.get("external_tuning", {}).get("session_margin_observations", 0))
    combined_observations = existing_observations + local_observations + external_observations
    collection = collection_info["collection"]
    cost = collection_info["cost"]
    fixed_collection_ok = bool(
        collection.get("fixed_frame_size") == FRAME_SIZE
        and collection.get("physical_request_count") <= MAX_REQUESTS
        and collection.get("tuning_arm_size") == TUNING_CANDIDATES
        and collection.get("validation_arm_size") == VALIDATION_CANDIDATES
    )
    external_target_ok = len(external) == EXTERNAL_TUNING_TARGET
    distribution_ready = bool(distribution.get("pass"))
    margin_ready = combined_observations >= MIN_MARGIN_PROFILES and session_margin.get("practical_theta_margin") is not None
    hardening, _type1_rows = _session_hardening(
        internal,
        family_rows,
        failures,
        run_type1=bool(margin_ready and distribution_ready),
    )
    hardening_ready = bool(hardening.get("pass"))
    m3_ready = bool(fixed_collection_ok and external_target_ok and distribution_ready and margin_ready and hardening_ready)
    if m3_ready:
        multiplicity = _multiplicity_validation(family_rows, repetitions=multiplicity_repetitions)
    else:
        multiplicity = {
            "schema_version": "v61-session-drift-m3-multiplicity-1.0.0",
            "status": "NOT_RUN_SESSION_NOT_IMPLEMENTATION_READY",
            "fixed_m": 3,
            "q": TARGET_Q,
            "release_procedure": "Benjamini-Yekutieli",
            "bh_status": "diagnostic comparator only",
            "rows": [],
            "by_acceptance": False,
        }
    m3_pass = bool(multiplicity.get("by_acceptance"))
    rules_frozen = bool(m3_ready and m3_pass and not failures)
    diagnostic_counts = Counter()
    diagnostic_family = {}
    if rules_frozen:
        by_profile: dict[str, int] = Counter()
        for row in family_rows:
            if row["candidate_qualified"]:
                by_profile[str(row["profile_key"])] += 1
        diagnostic_counts.update(by_profile.values())
        diagnostic_family = {
            FAMILY_LABELS[family]: sum(row["candidate_qualified"] for row in family_rows if row["family"] == family)
            for family in FAMILIES
        }
        tuning_diagnostic = {
            "status": "RUN",
            "not_used_for_tuning_decisions": True,
            "counts": {str(index): int(diagnostic_counts.get(index, 0)) for index in range(4)},
            "family_qualification_counts": diagnostic_family,
            "profiles": len(internal),
        }
    else:
        tuning_diagnostic = {
            "status": "NOT_RUN_RULES_NOT_FROZEN",
            "not_used_for_tuning_decisions": True,
            "counts": {str(index): 0 for index in range(4)},
            "family_qualification_counts": {},
            "profiles": len(internal),
        }
    predictive = _predictive_intervals(family_rows, len(internal)) if internal else {
        "validation_profiles": VALIDATION_TARGET,
        "families": {},
    }
    validation_status_path = paths["manifests"] / "sealed-validation-status.json"
    validation_status = _read_json(validation_status_path) if validation_status_path.exists() else {}
    validation_result = {
        "schema_version": "v61-fresh-sealed-validation-result-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "target_eligible_profiles": VALIDATION_TARGET,
        "candidate_count": VALIDATION_CANDIDATES,
        "collected_or_assigned": validation_status.get("assigned_status_count", 0),
        "eligible_status_count": validation_status.get("eligible_status_count", 0),
        "analytically_evaluated": 0,
        "status": "SEALED",
        "predictive_intervals_path": str(paths["diagnostics"] / "predictive_intervals.json"),
    }
    _private_write(paths["diagnostics"] / "fresh_validation_result.json", validation_result)
    fixed_gate = fixed_collection_ok and external_target_ok and cost.get("within_ceiling", False)
    if combined_observations < 100:
        session_verdict = "SESSION_DRIFT_REMAINS_DATA_LIMITED"
    elif not distribution_ready:
        session_verdict = "DISTRIBUTION_CONTINUITY_FAILED"
    elif session_margin.get("practical_theta_margin") is None:
        session_verdict = "NON_FINITE_MARGIN"
    elif not hardening_ready:
        session_verdict = "SESSION_HARDENING_FAILED"
    else:
        session_verdict = "CALIBRATED_WITH_LIMITATIONS"
    next_status = (
        "READY_FOR_IMPLEMENTATION"
        if rules_frozen
        else "SESSION_REMAINS_BLOCKED"
        if session_verdict != "CALIBRATED_WITH_LIMITATIONS"
        else "OWNER_ACTION_REQUIRED"
    )
    aggregate = {
        "schema_version": "v61-session-drift-phase2-aggregate-1.0.0",
        "campaign_id": CAMPAIGN_ID,
        "status": "PASS" if rules_frozen and fixed_gate else "PARTIAL",
        "next_status": next_status,
        "phase1_sha": PHASE1_SHA,
        "analytical_source_sha": ANALYTICAL_SOURCE_SHA,
        "frozen_artifact_digest": FROZEN_ARTIFACT_DIGEST,
        "branch_head_at_analysis": _git_sha(),
        "latest_main": _latest_main_sha(),
        "collection": collection,
        "cost": cost,
        "tuning": {
            "existing": len(old),
            "local_reserve": len([row for row in internal if row["source_arm"] == "local_reserve"]),
            "external": len(external),
            "final": len(internal),
            "target": TARGET_TUNING,
        },
        "session_drift": {
            "existing_margin_observations": existing_observations,
            "new_local_reserve_observations": local_observations,
            "new_external_observations": external_observations,
            "new_margin_observations": local_observations + external_observations,
            "combined_margin_observations": combined_observations,
            "practical_margin": session_margin.get("practical_theta_margin"),
            "hardening_status": "PASS" if hardening_ready else "FAIL",
            "verdict": session_verdict,
        },
        "distribution_continuity": distribution,
        "multiplicity": {
            "status": "PASS" if m3_pass else multiplicity.get("status", "FAIL"),
            "fixed_m": 3,
            "procedure": "Benjamini-Yekutieli",
            "q": TARGET_Q,
            "by_acceptance": m3_pass,
        },
        "tuning_only_diagnostic": tuning_diagnostic,
        "validation": {
            "target": VALIDATION_TARGET,
            "assigned": validation_result["collected_or_assigned"],
            "analytically_evaluated": 0,
            "status": "SEALED",
        },
        "hardening": hardening,
        "artifact_checksums": artifact_info["artifact_checksums"],
        "analysis_failures": len(failures),
        "gates": {
            "fixed_collection": fixed_gate,
            "distribution_continuity": distribution_ready,
            "session_margin": margin_ready,
            "session_hardening": hardening_ready,
            "m3_by": m3_pass,
            "transfer_post_loss_contracts_unchanged": True,
            "fresh_validation_evaluated": False,
        },
        "production_changes": 0,
    }
    if rules_frozen:
        candidate_rows = [row for row in family_rows if row["candidate_qualified"]]
        _private_write(paths["manifests"] / "candidate-freeze.json", {
            "schema_version": "v61-three-family-candidate-freeze-1.0.0",
            "campaign_id": CAMPAIGN_ID,
            "status": "FROZEN_FOR_FUTURE_VALIDATION",
            "family_universe": [FAMILY_LABELS[family] for family in FAMILIES],
            "candidate_result_count": len(candidate_rows),
            "candidate_result_digest": _digest(candidate_rows),
            "validation_analytically_evaluated": 0,
            "sealed_validation_status_path": str(validation_status_path),
        })
    else:
        _private_write(paths["manifests"] / "candidate-freeze.json", {
            "schema_version": "v61-three-family-candidate-freeze-1.0.0",
            "campaign_id": CAMPAIGN_ID,
            "status": "NOT_FROZEN_BLOCKED",
            "family_universe": [FAMILY_LABELS[family] for family in FAMILIES],
            "validation_analytically_evaluated": 0,
        })
    _write_analysis_artifacts(
        paths,
        internal=internal,
        family_rows=family_rows,
        margin_rows=margin_rows,
        support=support,
        distribution=distribution,
        hardening=hardening,
        multiplicity=multiplicity,
        predictive=predictive,
        aggregate=aggregate,
    )
    collection_info = _write_collection_artifacts(paths, status="ANALYZED")
    aggregate["cost"] = collection_info["cost"]
    _private_write(paths["diagnostics"] / "aggregate_summary.json", aggregate)
    evidence_path = ROOT / "docs" / "evidence" / "free-dna-v6.1-session-drift-phase2-execution-2026-08-28.md"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        _evidence_markdown(
            aggregate,
            collection=collection_info["collection"],
            corpus={**collection_info["raw"], **collection_info["normalized"], "split_manifest_digest": collection_info["collection"].get("split_manifest_digest")},
            diagnostics_path=paths["diagnostics"],
        ),
        encoding="utf-8",
    )
    return aggregate


def _latest_main_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        return "UNKNOWN"


def _self_check() -> None:
    salt = bytes(range(32))
    assert _rank_digest(42, salt) == _rank_digest(42, salt)
    assert _rank_digest(42, salt) != _rank_digest(43, salt)
    assert _natural_js([10, 0], [10, 0]) == 0.0
    assert _adjust([0.01, 0.02, 0.5], by=True)[0] >= _adjust([0.01, 0.02, 0.5], by=False)[0]
    assert _raw_shape_error([], "history") is None
    assert _raw_shape_error({}, "history") == "schema_contract_break"
    assert _beta_binomial_interval(10, 5, 100)[0] <= _beta_binomial_interval(10, 5, 100)[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--phase", choices=("prepare", "collect", "analyze", "all"), default="all")
    parser.add_argument("--pace-seconds", type=float, default=0.25)
    parser.add_argument("--multiplicity-repetitions", type=int, default=MULTIPLICITY_REPETITIONS)
    parser.add_argument("--acknowledge-owner-approval", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        _self_check()
        print(json.dumps({"self_check": "PASS"}, sort_keys=True))
        return 0
    if args.multiplicity_repetitions < MULTIPLICITY_REPETITIONS:
        raise SystemExit("multiplicity validation requires at least 10,000 datasets per cell")
    paths = _paths(args.local_root)
    _prepare_dirs(paths)
    salt = _load_salt(paths, create=args.phase in {"prepare", "all"})
    if args.phase in {"prepare", "all"}:
        _preflight(paths, args.local_root, salt)
        if args.phase == "prepare":
            print(json.dumps({"phase": "prepare", "status": "PASS", "campaign_id": CAMPAIGN_ID}, sort_keys=True))
            return 0
    if args.phase in {"collect", "all"}:
        result = asyncio.run(
            _collect(
                paths,
                args.local_root,
                env_file=args.env_file,
                pace_seconds=args.pace_seconds,
                acknowledge=args.acknowledge_owner_approval,
            )
        )
        if result:
            print(json.dumps({"phase": "collect", "status": "STOP", "campaign_id": CAMPAIGN_ID}, sort_keys=True))
            return result
    if args.phase in {"analyze", "all"}:
        aggregate = _analyze(paths, args.local_root, multiplicity_repetitions=args.multiplicity_repetitions)
        print(json.dumps({"phase": "analyze", "status": aggregate["status"], "next_status": aggregate["next_status"]}, sort_keys=True))
        return 0 if aggregate["status"] == "PASS" else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
