#!/usr/bin/env python3
"""Collect candidate account IDs from randomly sampled OpenDota public matches."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.cohorts.collector import CollectorPolicy, PublicMatchCollector  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.opendota.client import OpenDotaClient  # noqa: E402

Progress = Callable[[str], None]


async def collect_candidates(
    client: Any,
    *,
    match_count: int,
    requests_per_minute: int,
    less_than_match_id: int | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Return a deterministic artifact shape from live public-match details."""

    if match_count < 1 or match_count > 100:
        raise ValueError("match_count must be between 1 and 100")
    if requests_per_minute < 1:
        raise ValueError("requests_per_minute must be positive")

    collector = PublicMatchCollector(
        client,
        CollectorPolicy(
            batch_size=match_count,
            max_requests_per_minute=requests_per_minute,
            minimum_rank=None,
            maximum_rank=None,
        ),
    )
    public_rows = await collector.collect_page(less_than_match_id=less_than_match_id)
    seed_match_ids = list(
        dict.fromkeys(
            match_id
            for row in public_rows
            if isinstance(row, dict)
            and isinstance((match_id := row.get("match_id")), int)
            and match_id > 0
        )
    )[:match_count]
    if len(seed_match_ids) != match_count:
        raise RuntimeError(
            f"OpenDota returned {len(seed_match_ids)} unique match IDs; expected {match_count}"
        )

    candidate_ids: set[int] = set()
    seed_matches: list[dict[str, Any]] = []
    identified_slots = 0
    anonymous_slots = 0
    failed_matches: list[dict[str, Any]] = []
    delay_seconds = 60.0 / requests_per_minute

    for index, match_id in enumerate(seed_match_ids, start=1):
        if index > 1:
            await asyncio.sleep(delay_seconds)
        try:
            match = await client.get_match(match_id)
        except Exception as exc:  # keep partial collection resumable and auditable
            failed_matches.append(
                {"match_id": match_id, "error_type": type(exc).__name__}
            )
            continue

        players = match.get("players") if isinstance(match, dict) else None
        players = players if isinstance(players, list) else []
        match_public_ids: set[int] = set()
        match_anonymous = 0
        for player in players:
            account_id = player.get("account_id") if isinstance(player, dict) else None
            if isinstance(account_id, int) and account_id > 0:
                identified_slots += 1
                match_public_ids.add(account_id)
                candidate_ids.add(account_id)
            else:
                anonymous_slots += 1
                match_anonymous += 1

        seed_matches.append(
            {
                "match_id": match_id,
                "start_time": match.get("start_time"),
                "cluster": match.get("cluster"),
                "region": match.get("region"),
                "lobby_type": match.get("lobby_type"),
                "game_mode": match.get("game_mode"),
                "player_slots": len(players),
                "public_account_ids": len(match_public_ids),
                "anonymous_player_slots": match_anonymous,
            }
        )
        if progress is not None and (index % 10 == 0 or index == match_count):
            progress(
                f"expanded {index}/{match_count} matches; "
                f"{len(candidate_ids)} unique public account IDs"
            )

    return {
        "schema_version": "v6-calibration-candidates-1.0.0",
        "collected_at": datetime.now(UTC).isoformat(),
        "source": {
            "provider": "OpenDota",
            "seed_endpoint": "/publicMatches",
            "detail_endpoint": "/matches/{match_id}",
            "rank_filters_used": False,
            "authenticated": True,
            "less_than_match_id": less_than_match_id,
        },
        "summary": {
            "requested_seed_matches": match_count,
            "collected_seed_matches": len(seed_matches),
            "failed_seed_matches": len(failed_matches),
            "identified_player_slots": identified_slots,
            "anonymous_player_slots": anonymous_slots,
            "duplicate_identified_slots": identified_slots - len(candidate_ids),
            "unique_candidate_account_ids": len(candidate_ids),
        },
        "candidate_account_ids": sorted(candidate_ids),
        "seed_matches": seed_matches,
        "failures": failed_matches,
    }


def load_private_artifact(path: Path) -> dict[str, Any]:
    """Load and minimally validate a resumable candidate artifact."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("candidate_account_ids"), list):
        raise ValueError(f"invalid candidate artifact: {path}")
    if not isinstance(payload.get("seed_matches"), list):
        raise ValueError(f"candidate artifact has no seed matches: {path}")
    return payload


def merge_candidate_artifacts(
    existing: Mapping[str, Any] | None,
    batch: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge one non-overlapping page and recompute auditable aggregate counts."""

    existing = existing or {}
    candidates = {
        account_id
        for artifact in (existing, batch)
        for account_id in artifact.get("candidate_account_ids", [])
        if isinstance(account_id, int) and account_id > 0
    }
    seed_by_id: dict[int, dict[str, Any]] = {}
    for artifact in (existing, batch):
        for row in artifact.get("seed_matches", []):
            if isinstance(row, dict) and isinstance(row.get("match_id"), int):
                seed_by_id[row["match_id"]] = row
    failure_by_id: dict[int, dict[str, Any]] = {}
    for artifact in (existing, batch):
        for row in artifact.get("failures", []):
            if isinstance(row, dict) and isinstance(row.get("match_id"), int):
                failure_by_id[row["match_id"]] = row
    for match_id in seed_by_id:
        failure_by_id.pop(match_id, None)

    seed_matches = list(seed_by_id.values())
    failures = list(failure_by_id.values())
    identified_slots = sum(
        int(row.get("public_account_ids", 0)) for row in seed_matches
    )
    anonymous_slots = sum(
        int(row.get("anonymous_player_slots", 0)) for row in seed_matches
    )
    prior_candidates = {
        value
        for value in existing.get("candidate_account_ids", [])
        if isinstance(value, int) and value > 0
    }
    batches = list(existing.get("batches", []))
    batches.append(
        {
            "collected_at": batch.get("collected_at"),
            "less_than_match_id": batch.get("source", {}).get("less_than_match_id"),
            "seed_matches": len(batch.get("seed_matches", [])),
            "failed_seed_matches": len(batch.get("failures", [])),
            "candidates_added": len(candidates - prior_candidates),
            "candidate_total": len(candidates),
        }
    )
    return {
        "schema_version": "v6-calibration-candidates-1.0.0",
        "collected_at": batch.get("collected_at"),
        "source": {
            "provider": "OpenDota",
            "seed_endpoint": "/publicMatches",
            "detail_endpoint": "/matches/{match_id}",
            "rank_filters_used": False,
            "authenticated": True,
            "pagination": "less_than_match_id",
        },
        "summary": {
            "requested_seed_matches": len(seed_matches) + len(failures),
            "collected_seed_matches": len(seed_matches),
            "failed_seed_matches": len(failures),
            "identified_player_slots": identified_slots,
            "anonymous_player_slots": anonymous_slots,
            "duplicate_identified_slots": identified_slots - len(candidates),
            "unique_candidate_account_ids": len(candidates),
        },
        "candidate_account_ids": sorted(candidates),
        "seed_matches": seed_matches,
        "failures": failures,
        "batches": batches,
    }


async def collect_until_target(
    client: Any,
    *,
    target_candidates: int,
    batch_size: int,
    requests_per_minute: int,
    existing: Mapping[str, Any] | None = None,
    checkpoint: Callable[[dict[str, Any]], None] | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Page backward in fixed-size batches until the unique-ID target is met."""

    if target_candidates < 1:
        raise ValueError("target_candidates must be positive")
    if batch_size < 1 or batch_size > 100:
        raise ValueError("batch_size must be between 1 and 100")

    artifact = dict(existing) if existing else None
    batch_number = 0
    while len((artifact or {}).get("candidate_account_ids", [])) < target_candidates:
        prior_match_ids: set[int] = set()
        for row in (*((artifact or {}).get("seed_matches", [])), *((artifact or {}).get("failures", []))):
            match_id = row.get("match_id") if isinstance(row, dict) else None
            if isinstance(match_id, int):
                prior_match_ids.add(match_id)
        cursor = min(prior_match_ids) if prior_match_ids else None
        batch = await collect_candidates(
            client,
            match_count=batch_size,
            requests_per_minute=requests_per_minute,
            less_than_match_id=cursor,
        )
        new_match_ids: set[int] = set()
        for row in batch.get("seed_matches", []) + batch.get("failures", []):
            match_id = row.get("match_id") if isinstance(row, dict) else None
            if isinstance(match_id, int):
                new_match_ids.add(match_id)
        if not new_match_ids or new_match_ids.issubset(prior_match_ids):
            raise RuntimeError("OpenDota pagination did not produce a new match page")

        artifact = merge_candidate_artifacts(artifact, batch)
        batch_number += 1
        if checkpoint is not None:
            checkpoint(artifact)
        if progress is not None:
            progress(
                f"batch {batch_number}: {artifact['summary']['collected_seed_matches']} matches; "
                f"{artifact['summary']['unique_candidate_account_ids']}/{target_candidates} candidates"
            )
    if artifact is None:  # pragma: no cover - positive target always enters the loop
        raise RuntimeError("candidate collection produced no artifact")
    return artifact


def write_private_artifact(path: Path, artifact: dict[str, Any]) -> None:
    """Write account IDs locally with owner-only permissions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings.from_env()
    if not settings.opendota_api_key:
        raise RuntimeError("OPENDOTA_API_KEY is not configured")
    def progress(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    async with OpenDotaClient(settings) as client:
        if args.target_candidates is not None:
            existing = (
                load_private_artifact(args.output)
                if args.resume and args.output.exists()
                else None
            )
            return await collect_until_target(
                client,
                target_candidates=args.target_candidates,
                batch_size=args.batch_size,
                requests_per_minute=args.requests_per_minute,
                existing=existing,
                checkpoint=lambda artifact: write_private_artifact(args.output, artifact),
                progress=progress,
            )
        return await collect_candidates(
            client,
            match_count=args.matches,
            requests_per_minute=args.requests_per_minute,
            progress=progress,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matches", type=int, default=50, help="public seed matches (1-100)")
    parser.add_argument(
        "--target-candidates",
        type=int,
        help="resume in batches until at least this many unique account IDs exist",
    )
    parser.add_argument("--batch-size", type=int, default=20, help="matches per target-mode batch")
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="resume an existing output artifact in target mode",
    )
    parser.add_argument(
        "--requests-per-minute",
        type=int,
        default=120,
        help="paced match-detail request rate",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".local" / "calibration" / "v6-public-match-candidates.json",
        help="git-ignored raw candidate artifact",
    )
    args = parser.parse_args()
    artifact = asyncio.run(_run(args))
    write_private_artifact(args.output, artifact)
    print(json.dumps(artifact["summary"], indent=2, sort_keys=True))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
