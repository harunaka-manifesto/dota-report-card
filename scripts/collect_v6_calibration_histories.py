#!/usr/bin/env python3
"""Fetch, normalize, and checkpoint v6 calibration candidate histories."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.core.config import (  # noqa: E402
    DEFAULT_SESSION_GAP_MINUTES,
    FREE_HISTORY_WINDOW_DAYS,
    Settings,
)
from app.dna.sessions import SessionPolicy, infer_sessions  # noqa: E402
from app.ingestion.summary_normalize import (  # noqa: E402
    filter_history_window,
    normalize_summary_rows,
    previous_year_window,
)
from app.opendota.client import OpenDotaClient  # noqa: E402
from app.player_analysis_v6.context_adjustment import match_context  # noqa: E402
from app.player_analysis_v6.hero_portfolio import load_v6_hero_taxonomy  # noqa: E402
from app.player_analysis_v6.metrics import (  # noqa: E402
    death_exposure_per_ten_minutes,
    finishing_share,
    involvement_per_minute,
)

HISTORY_PROJECTION_VERSION = "summary-projection-2.0.0"
HISTORY_PAGINATION_VERSION = "annual-pagination-1.0.0"
HISTORY_PROJECTIONS = (
    "match_id",
    "player_slot",
    "radiant_win",
    "duration",
    "game_mode",
    "lobby_type",
    "hero_id",
    "start_time",
    "version",
    "kills",
    "deaths",
    "assists",
    "leaver_status",
    "party_size",
    "hero_variant",
    "leagueid",
    "cluster",
    "lane",
    "lane_role",
    "is_roaming",
)


@dataclass(frozen=True, slots=True)
class ReferenceData:
    cluster_regions: Mapping[int, int]
    patches: tuple[tuple[int, str], ...]
    taxonomy_by_hero: Mapping[int, Any]


class RequestPacer:
    """Smoothly space request starts across concurrent workers."""

    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute < 1:
            raise ValueError("requests_per_minute must be positive")
        self.interval = 60.0 / requests_per_minute
        self._next_request = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_request - now)
            if delay:
                await asyncio.sleep(delay)
            self._next_request = max(now, self._next_request) + self.interval


def _private_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def load_candidate_ids(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("candidate_account_ids") if isinstance(payload, dict) else None
    if not isinstance(values, list):
        raise ValueError(f"candidate artifact has no account ID list: {path}")
    return sorted({value for value in values if isinstance(value, int) and value > 0})


def load_or_create_salt(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        value = path.read_bytes()
        if len(value) < 32:
            raise ValueError(f"calibration salt is invalid: {path}")
        return value
    value = secrets.token_bytes(32)
    path.write_bytes(value)
    os.chmod(path, 0o600)
    return value


def pseudonym(account_id: int, salt: bytes) -> str:
    return hashlib.sha256(salt + str(account_id).encode("ascii")).hexdigest()


def _timestamp(value: Any) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def build_reference_data(
    cluster_payload: Any,
    patch_payload: Any,
    taxonomy_by_hero: Mapping[int, Any] | None = None,
) -> ReferenceData:
    clusters = {
        int(cluster): int(region)
        for cluster, region in (cluster_payload.items() if isinstance(cluster_payload, dict) else ())
        if str(cluster).isdigit() and isinstance(region, int)
    }
    patches = sorted(
        (
            timestamp,
            str(row["name"]),
        )
        for row in (patch_payload if isinstance(patch_payload, list) else ())
        if isinstance(row, dict)
        and row.get("name")
        and (timestamp := _timestamp(row.get("date"))) is not None
    )
    return ReferenceData(clusters, tuple(patches), taxonomy_by_hero or load_v6_hero_taxonomy())


def _patch_for(start_time: Any, patches: Sequence[tuple[int, str]]) -> str | None:
    if not isinstance(start_time, int):
        return None
    result = None
    for timestamp, name in patches:
        if timestamp > start_time:
            break
        result = name
    return result


def enrich_history(rows: Sequence[dict[str, Any]], references: ReferenceData) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        cluster = row.get("cluster")
        if row.get("region") is None and isinstance(cluster, int):
            row["region"] = references.cluster_regions.get(cluster)
        if not row.get("patch"):
            row["patch"] = _patch_for(row.get("start_time"), references.patches)
        enriched.append(row)
    return enriched


def _calibration_row(match: Any, profile_id: str, references: ReferenceData) -> dict[str, Any]:
    context = match_context(match, taxonomy_by_hero=references.taxonomy_by_hero)
    return {
        "profile_id": profile_id,
        "match_id": match.match_id,
        "start_time": match.started_at,
        "duration_seconds": match.duration_seconds,
        "won": match.won,
        "kills": match.kills,
        "deaths": match.deaths,
        "assists": match.assists,
        "hero_id": match.hero_id,
        "hero_function": context.hero_function,
        "patch": match.patch,
        "lane_context": context.lane_context,
        "region": match.region,
        "game_mode": match.game_mode,
        "lobby_type": match.lobby_type,
        "session_id": match.session_id,
        "session_index": match.session_index,
        "session_corrupt": match.session_corrupt,
        "source_version": match.source_version,
        "metrics": {
            "outcome": 1.0 if match.won else 0.0,
            "involvement_per_minute": involvement_per_minute(
                match.kills, match.assists, match.duration_seconds
            ),
            "finishing_share": finishing_share(match.kills, match.assists),
            "death_exposure_per_ten": death_exposure_per_ten_minutes(
                match.deaths, match.duration_seconds
            ),
        },
    }


def compact_calibration_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project older checkpoints onto the current calibration-only row schema."""

    keys = (
        "profile_id",
        "match_id",
        "start_time",
        "duration_seconds",
        "won",
        "kills",
        "deaths",
        "assists",
        "hero_id",
        "hero_function",
        "patch",
        "lane_context",
        "region",
        "game_mode",
        "lobby_type",
        "session_id",
        "session_index",
        "session_corrupt",
        "source_version",
        "metrics",
    )
    return {key: row.get(key) for key in keys}


async def process_candidate(
    client: Any,
    account_id: int,
    *,
    salt: bytes,
    references: ReferenceData,
    pacer: RequestPacer,
    window_start: int,
    window_end: int,
) -> dict[str, Any]:
    profile_id = pseudonym(account_id, salt)
    try:
        await pacer.wait()
        history = await client.get_matches(
            account_id,
            limit=None,
            days=FREE_HISTORY_WINDOW_DAYS,
            project=HISTORY_PROJECTIONS,
        )
        normalized = normalize_summary_rows(enrich_history(history, references), account_id)
        eligible = filter_history_window(
            normalized.eligible_matches,
            window_start=window_start,
            window_end=window_end,
        )
        session_result = infer_sessions(
            eligible,
            SessionPolicy(gap_minutes=DEFAULT_SESSION_GAP_MINUTES),
            window_start=window_start,
            window_end=window_end,
        )
        exclusion_reasons = Counter(
            reason
            for row in normalized.exclusion_ledger
            for reason in row.get("reasons", [])
        )
        is_eligible = len(eligible) >= 30
        return {
            "account_id": account_id,
            "profile_id": profile_id,
            "history_projection_version": HISTORY_PROJECTION_VERSION,
            "history_pagination_version": HISTORY_PAGINATION_VERSION,
            "status": "eligible" if is_eligible else "ineligible",
            "source_match_count": len(history),
            "normalized_match_count": len(normalized.matches),
            "eligible_match_count": len(eligible),
            "session_count": len(session_result.sessions),
            "completed_session_count": len(session_result.completed_sessions),
            "exclusion_reasons": dict(sorted(exclusion_reasons.items())),
            "matches": (
                [
                    _calibration_row(match, profile_id, references)
                    for match in session_result.matches
                ]
                if is_eligible
                else []
            ),
        }
    except Exception as exc:
        return {
            "account_id": account_id,
            "profile_id": profile_id,
            "history_projection_version": HISTORY_PROJECTION_VERSION,
            "history_pagination_version": HISTORY_PAGINATION_VERSION,
            "status": "error",
            "error_type": type(exc).__name__,
            "matches": [],
        }


def load_checkpoints(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[int, dict[str, Any]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                break
            raise
        account_id = record.get("account_id") if isinstance(record, dict) else None
        if isinstance(account_id, int) and account_id > 0:
            rows[account_id] = record
    return rows


def append_checkpoint(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, (json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def rewrite_checkpoints(path: Path, checkpoints: Mapping[int, Mapping[str, Any]]) -> None:
    """Remove superseded attempts and compact retained eligible match rows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        for account_id in sorted(checkpoints):
            record = dict(checkpoints[account_id])
            record["matches"] = [
                compact_calibration_row(row) for row in record.get("matches", [])
            ]
            os.write(descriptor, (json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.replace(path)


def materialize_corpus(
    path: Path,
    checkpoints: Mapping[int, Mapping[str, Any]],
    *,
    window_start: int,
    window_end: int,
    candidate_count: int,
    target_eligible: int,
) -> dict[str, Any]:
    eligible_profiles = [
        record for record in checkpoints.values() if record.get("status") == "eligible"
    ]
    matches = [
        compact_calibration_row(row)
        for record in eligible_profiles
        for row in record.get("matches", [])
    ]
    summary = {
        "candidate_count": candidate_count,
        "processed_profile_count": sum(record.get("status") != "error" for record in checkpoints.values()),
        "eligible_profile_count": len(eligible_profiles),
        "ineligible_profile_count": sum(record.get("status") == "ineligible" for record in checkpoints.values()),
        "error_profile_count": sum(record.get("status") == "error" for record in checkpoints.values()),
        "eligible_match_count": len(matches),
        "target_eligible_profiles": target_eligible,
        "target_met": len(eligible_profiles) >= target_eligible,
    }
    payload = {
        "schema_version": "v6-calibration-corpus-1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "window": {"start_time": window_start, "end_time": window_end, "days": 365},
        "source": {
            "provider": "OpenDota",
            "endpoint": "/players/{account_id}/matches",
            "projections": list(HISTORY_PROJECTIONS),
            "rank_or_mmr_used": False,
        },
        "summary": summary,
        "profiles": [
            {key: value for key, value in record.items() if key not in {"account_id", "matches"}}
            for record in eligible_profiles
        ],
        "matches": matches,
    }
    _private_write(path, payload)
    return payload


async def collect_histories(
    client: Any,
    candidate_ids: Sequence[int],
    *,
    checkpoint_path: Path,
    output_path: Path,
    salt: bytes,
    references: ReferenceData,
    requests_per_minute: int,
    concurrency: int,
    progress_batch_size: int,
    target_eligible: int,
    window_end: int | None = None,
) -> dict[str, Any]:
    window_start, fixed_window_end = previous_year_window(
        window_end=window_end,
        days=FREE_HISTORY_WINDOW_DAYS,
    )
    checkpoints = load_checkpoints(checkpoint_path)
    mandatory_refresh = [
        account_id
        for account_id in candidate_ids
        if checkpoints.get(account_id, {}).get("status") not in {None, "error"}
        and (
            checkpoints.get(account_id, {}).get("history_projection_version")
            != HISTORY_PROJECTION_VERSION
            or (
                checkpoints.get(account_id, {}).get("source_match_count", 0) >= 200
                and checkpoints.get(account_id, {}).get("history_pagination_version")
                != HISTORY_PAGINATION_VERSION
            )
        )
    ]
    optional_pending = [
        account_id
        for account_id in candidate_ids
        if checkpoints.get(account_id, {}).get("status") in {None, "error"}
    ]
    pending = mandatory_refresh + optional_pending
    mandatory_refresh_count = len(mandatory_refresh)
    pacer = RequestPacer(requests_per_minute)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def run_one(account_id: int) -> dict[str, Any]:
        async with semaphore:
            return await process_candidate(
                client,
                account_id,
                salt=salt,
                references=references,
                pacer=pacer,
                window_start=window_start,
                window_end=fixed_window_end,
            )

    completed = 0
    for start in range(0, len(pending), progress_batch_size):
        eligible_count = sum(
            item.get("status") == "eligible" for item in checkpoints.values()
        )
        if eligible_count >= target_eligible and start >= mandatory_refresh_count:
            break
        batch = pending[start : start + progress_batch_size]
        records = await asyncio.gather(*(run_one(account_id) for account_id in batch))
        for record in records:
            append_checkpoint(checkpoint_path, record)
            checkpoints[int(record["account_id"])] = record
        completed += len(records)
        eligible_count = sum(
            item.get("status") == "eligible" for item in checkpoints.values()
        )
        print(
            f"processed {completed}/{len(pending)} pending profiles; "
            f"{eligible_count}/{target_eligible} eligible",
            file=sys.stderr,
            flush=True,
        )

    payload = materialize_corpus(
        output_path,
        checkpoints,
        window_start=window_start,
        window_end=fixed_window_end,
        candidate_count=len(candidate_ids),
        target_eligible=target_eligible,
    )
    rewrite_checkpoints(checkpoint_path, checkpoints)
    return payload


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    settings = replace(Settings.from_env(), free_history_limit=None, history_limit=None)
    if not settings.opendota_api_key:
        raise RuntimeError("OPENDOTA_API_KEY is not configured")
    candidate_ids = load_candidate_ids(args.candidates)
    salt = load_or_create_salt(args.salt)
    async with OpenDotaClient(settings) as client:
        cluster_payload, patch_payload = await asyncio.gather(
            client.get_constants("cluster"),
            client.get_constants("patch"),
        )
        references = build_reference_data(cluster_payload, patch_payload)
        return await collect_histories(
            client,
            candidate_ids,
            checkpoint_path=args.checkpoint,
            output_path=args.output,
            salt=salt,
            references=references,
            requests_per_minute=args.requests_per_minute,
            concurrency=args.concurrency,
            progress_batch_size=args.progress_batch_size,
            target_eligible=args.target_eligible,
        )


def main() -> None:
    local = ROOT / ".local" / "calibration"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidates",
        type=Path,
        default=local / "v6-public-match-candidates.json",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=local / "v6-profile-history-checkpoints.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=local / "v6-eligible-corpus.json",
    )
    parser.add_argument("--salt", type=Path, default=local / "v6-corpus-salt.bin")
    parser.add_argument("--target-eligible", type=int, default=1_000)
    parser.add_argument("--requests-per-minute", type=int, default=240)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--progress-batch-size", type=int, default=20)
    args = parser.parse_args()
    payload = asyncio.run(_run(args))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
