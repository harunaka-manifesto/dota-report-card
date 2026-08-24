#!/usr/bin/env python3
"""Collect private V6.1 histories through the canonical one-request contract."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.core.config import Settings  # noqa: E402
from app.ingestion.summary_history_contract import (  # noqa: E402
    SUMMARY_HISTORY_PROJECTION,
    SUMMARY_HISTORY_PROVIDER_LIMIT,
    SUMMARY_HISTORY_WINDOW_DAYS,
    normalize_canonical_summary_history,
    request_manifest,
)
from app.opendota.client import OpenDotaClient  # noqa: E402


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


def _publicly_safe_normalized_row(match: Any) -> dict[str, Any]:
    row = match.as_dict()
    row.pop("account_id", None)
    row.pop("match_id", None)
    return row


async def collect_profile(
    client: Any,
    account_id: int,
    *,
    salt: bytes,
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
    return {
        "profile_id": _pseudonym(account_id, salt),
        "history_audit": canonical.audit.as_dict(),
        "matches": [
            _publicly_safe_normalized_row(match)
            for match in canonical.normalization.matches
        ],
    }


async def collect_profiles(
    client: Any,
    account_ids: Sequence[int],
    *,
    salt: bytes,
) -> dict[str, Any]:
    profiles = []
    for account_id in account_ids:
        profiles.append(await collect_profile(client, account_id, salt=salt))
    return {
        "schema_version": "v61-calibration-corpus-1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "request_manifest": request_manifest(),
        "profile_count": len(profiles),
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
