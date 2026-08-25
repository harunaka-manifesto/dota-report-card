#!/usr/bin/env python3
"""Collect private V6.1 histories through the canonical one-request contract."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.core.config import Settings  # noqa: E402
from app.dna.sessions import infer_sessions  # noqa: E402
from app.ingestion.summary_history_contract import (  # noqa: E402
    SUMMARY_HISTORY_PROJECTION,
    SUMMARY_HISTORY_PROVIDER_LIMIT,
    SUMMARY_HISTORY_RETRY_LIMIT,
    SUMMARY_HISTORY_WINDOW_DAYS,
    normalize_canonical_summary_history,
    request_manifest,
)
from app.ingestion.summary_normalize import (  # noqa: E402
    filter_history_window,
    previous_year_window,
)
from app.opendota.client import OpenDotaClient  # noqa: E402
from app.player_analysis_v61.calibration_corpus import (  # noqa: E402
    CANONICAL_SESSION_POLICY,
    MINIMUM_USABLE_MATCHES,
)


def _pseudonym(account_id: int, salt: bytes) -> str:
    return hashlib.sha256(salt + str(account_id).encode("ascii")).hexdigest()


def _private_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        os.write(
            descriptor,
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    temporary.replace(path)


def _publicly_safe_normalized_row(
    match: Any,
    source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = source or {}
    return {
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
    }


async def collect_profile(
    client: Any,
    account_id: int,
    *,
    salt: bytes,
    window_start: int | None = None,
    window_end: int | None = None,
) -> dict[str, Any]:
    rows = await client.get_summary_history_once(
        account_id,
        days=SUMMARY_HISTORY_WINDOW_DAYS,
        project=SUMMARY_HISTORY_PROJECTION,
        provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
    )
    canonical = normalize_canonical_summary_history(
        rows,
        account_id,
        request_count=1,
        provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
    )
    eligible = canonical.normalization.eligible_matches
    if window_start is not None and window_end is not None:
        eligible = filter_history_window(
            eligible,
            window_start=window_start,
            window_end=window_end,
        )
    session_result = infer_sessions(
        eligible,
        CANONICAL_SESSION_POLICY,
        window_start=window_start,
        window_end=window_end,
    )
    source_rows = [row for row in rows if isinstance(row, Mapping)]
    exclusion_reasons = Counter(
        reason
        for record in canonical.normalization.exclusion_ledger
        for reason in record.get("reasons", [])
    )
    if window_start is not None and window_end is not None:
        exclusion_reasons["outside_window"] += sum(
            1
            for match in canonical.normalization.eligible_matches
            if match.started_at is None or not window_start <= match.started_at <= window_end
        )
    materialized = []
    for match in session_result.matches:
        source = source_rows[match.source_index] if match.source_index < len(source_rows) else None
        row = _publicly_safe_normalized_row(match, source)
        row.update(
            {
                "session_id": match.session_id,
                "session_index": match.session_index,
                "session_corrupt": match.session_corrupt,
            }
        )
        materialized.append(row)
    return {
        "profile_id": _pseudonym(account_id, salt),
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


async def collect_profiles(
    client: Any,
    account_ids: Sequence[int],
    *,
    salt: bytes,
) -> dict[str, Any]:
    window_end = int(datetime.now(UTC).timestamp())
    window_start, window_end = previous_year_window(
        window_end=window_end,
        days=SUMMARY_HISTORY_WINDOW_DAYS,
    )
    profiles = []
    for account_id in account_ids:
        profiles.append(
            await collect_profile(
                client,
                account_id,
                salt=salt,
                window_start=window_start,
                window_end=window_end,
            )
        )
    eligible_profiles = [profile for profile in profiles if profile["status"] == "eligible"]
    return {
        "schema_version": "v61-calibration-corpus-2.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "request_manifest": request_manifest(),
        "source": {
            "endpoint": "/players/{account_id}/matches",
            "request_count_per_profile": 1,
            "detail_requests": 0,
            "parse_requests": 0,
            "rank_or_mmr_used": False,
            "retry_limit": SUMMARY_HISTORY_RETRY_LIMIT,
        },
        "window": {
            "days": SUMMARY_HISTORY_WINDOW_DAYS,
            "start_time": window_start,
            "end_time": window_end,
        },
        "profile_count": len(profiles),
        "summary": {
            "profile_count": len(profiles),
            "eligible_profile_count": len(eligible_profiles),
            "eligible_match_count": sum(len(profile["matches"]) for profile in profiles),
        },
        "raw_identifiers_present": False,
        "profiles": profiles,
    }


def _candidate_ids(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("candidate_account_ids") if isinstance(payload, Mapping) else None
    if not isinstance(values, list):
        raise ValueError("candidate file needs candidate_account_ids")
    return sorted({value for value in values if isinstance(value, int) and value > 0})


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.acknowledge_network_collection:
        raise RuntimeError("network collection requires --acknowledge-network-collection")
    settings = Settings.from_env()
    if not settings.opendota_api_key:
        raise RuntimeError("OPENDOTA_API_KEY is not configured")
    salt = args.salt.read_bytes()
    if len(salt) < 32:
        raise ValueError("calibration salt must contain at least 32 bytes")
    async with OpenDotaClient(settings) as client:
        return await collect_profiles(
            client,
            _candidate_ids(args.candidates),
            salt=salt,
        )


def main() -> int:
    local = ROOT / ".local" / "calibration" / "v61"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--salt", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=local / "canonical-corpus.json")
    parser.add_argument("--acknowledge-network-collection", action="store_true")
    args = parser.parse_args()
    payload = asyncio.run(_run(args))
    _private_write(args.output, payload)
    print(json.dumps({"profile_count": payload["profile_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
