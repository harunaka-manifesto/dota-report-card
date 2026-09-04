#!/usr/bin/env python3
"""Size the V7 pass-2 acquisition before committing days of collection to it.

Answers exactly three questions, with a hard ceiling on physical requests:

1. What is the largest match batch that ``GetDeepMatchBatch`` can carry without
   exceeding the endpoint's GraphQL complexity ceiling? Every downstream time
   and cost estimate is a function of this number, so guessing it is expensive.
2. Does ``stats.locationReport`` exist, what shape does it return, and what does
   it cost? It is the only route to a map-position answer that does not touch
   playback.
3. Can the item vocabulary be fetched, so an item-timing Finding can tell a
   consumable from a real item?

The command is separate from the production provider. It reads
``STRATZ_API_TOKEN`` from an explicitly supplied dotenv file, never logs or
stores it, writes redacted evidence under the ignored local corpus tree, and
refuses to exceed its physical-call budget.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
for candidate in (str(ROOT), str(API_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from app.stratz.queries import (  # noqa: E402
    GET_DEEP_MATCH_BATCH,
    GET_PLAYER_RANK_HISTORY,
    PROBE_ITEM_VOCABULARY,
    PROBE_LOCATION_REPORT,
    GraphQLOperation,
)

from scripts.stratz_v7_live_microprobe import (  # noqa: E402
    extract_complexity,
    graphql_error_text,
    is_complexity_failure,
    is_schema_failure,
    load_stratz_token,
    parse_retry_after,
    redact_text,
    safe_rate_headers,
    safe_response_headers,
)

DEFAULT_ENDPOINT = "https://api.stratz.com/graphql"
DEFAULT_OUTPUT_ROOT = ROOT / ".local" / "corpora" / "stratz" / "v7-pass2-probe"

#: Descending ladder. The probe stops at the first batch size that succeeds, so
#: a healthy endpoint costs far fewer calls than the budget allows.
BATCH_LADDER: tuple[int, ...] = (8, 6, 4, 3, 2, 1)

#: Hard ceiling. Raising it is a deliberate act, not a flag you forget.
MAX_PHYSICAL_CALLS = 12

DEFAULT_TIMEOUT_SECONDS = 45.0


class ProbeError(RuntimeError):
    """A probe could not complete and no further request should be made."""


class BudgetExceeded(ProbeError):
    pass


def summarise_deep_batch(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Aggregate-only description of a deep-batch response.

    Deliberately records counts and presence, never values: this summary is
    committed as evidence and must carry no account, match, or identity data.
    """

    player = ((payload or {}).get("data") or {}).get("player") or {}
    matches = player.get("matches") or []
    if not isinstance(matches, list):
        return {"matches": 0, "usable": False, "reason": "matches not a list"}

    trajectory_fields = (
        "networthPerMinute",
        "goldPerMinute",
        "experiencePerMinute",
        "lastHitsPerMinute",
        "deniesPerMinute",
        "heroDamagePerMinute",
        "heroDamageReceivedPerMinute",
        "towerDamagePerMinute",
        "healPerMinute",
        "campStack",
    )
    event_fields = ("killEvents", "deathEvents", "assistEvents", "itemPurchases", "wards", "runes")

    present: dict[str, int] = {name: 0 for name in trajectory_fields + event_fields}
    lengths: dict[str, list[int]] = {name: [] for name in trajectory_fields + event_fields}
    all_player_rows: list[int] = []
    own_rows = 0
    parsed = 0

    for match in matches:
        if not isinstance(match, Mapping):
            continue
        if match.get("parsedDateTime"):
            parsed += 1
        everyone = match.get("allPlayers") or []
        all_player_rows.append(len(everyone) if isinstance(everyone, list) else 0)
        own = match.get("players") or []
        if not isinstance(own, list) or not own:
            continue
        own_rows += 1
        stats = (own[0] or {}).get("stats") or {}
        for name in trajectory_fields + event_fields:
            value = stats.get(name)
            if isinstance(value, list):
                present[name] += 1
                lengths[name].append(len(value))

    return {
        "matches": len(matches),
        "parsed_matches": parsed,
        "own_player_rows": own_rows,
        "all_player_row_counts": sorted(set(all_player_rows)),
        "field_present_in_matches": present,
        "field_median_length": {
            name: (sorted(values)[len(values) // 2] if values else None)
            for name, values in lengths.items()
        },
        "usable": own_rows > 0 and present["deathEvents"] > 0,
    }


def summarise_location_report(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    player = ((payload or {}).get("data") or {}).get("player") or {}
    matches = player.get("matches") or []
    samples: list[dict[str, Any]] = []
    for match in matches if isinstance(matches, list) else []:
        own = (match or {}).get("players") or []
        if not own:
            continue
        report = (own[0] or {}).get("stats", {}).get("locationReport")
        if report is None:
            samples.append({"present": False})
            continue
        sample: dict[str, Any] = {"present": True, "python_type": type(report).__name__}
        if isinstance(report, list):
            sample["length"] = len(report)
            if report and isinstance(report[0], Mapping):
                sample["element_keys"] = sorted(report[0].keys())
            elif report:
                sample["element_type"] = type(report[0]).__name__
        elif isinstance(report, Mapping):
            sample["keys"] = sorted(report.keys())
        samples.append(sample)
    usable = any(s.get("present") for s in samples)
    return {"samples": samples, "usable": usable}


def summarise_item_vocabulary(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    constants = ((payload or {}).get("data") or {}).get("constants") or {}
    items = constants.get("items") or []
    if not isinstance(items, list) or not items:
        return {"items": 0, "usable": False}
    with_cost = sum(1 for item in items if (item or {}).get("stat", {}).get("cost") is not None)
    return {
        "items": len(items),
        "with_cost": with_cost,
        "element_keys": sorted(items[0].keys()) if isinstance(items[0], Mapping) else [],
        "usable": True,
    }


class Pass2Probe:
    def __init__(
        self,
        token: str,
        *,
        endpoint: str,
        output_dir: Path,
        timeout_seconds: float,
        max_calls: int,
    ) -> None:
        self._token = token
        self.endpoint = endpoint
        self.output_dir = output_dir
        self.timeout_seconds = timeout_seconds
        self.max_calls = max_calls
        self.calls = 0
        self.attempts: list[dict[str, Any]] = []
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Pass2Probe:
        self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        operation: GraphQLOperation,
        variables: Mapping[str, Any],
        *,
        label: str,
    ) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
        if self.calls >= self.max_calls:
            raise BudgetExceeded(
                f"physical-call budget of {self.max_calls} reached before {label}"
            )
        assert self._client is not None
        self.calls += 1
        started = time.monotonic()
        response = await self._client.post(
            self.endpoint,
            json={"query": operation.document, "variables": dict(variables)},
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "User-Agent": "STRATZ_API_DOTA_REPORT_CARD_V7_PASS2_PROBE",
            },
        )
        latency = time.monotonic() - started
        try:
            payload: Mapping[str, Any] | None = response.json()
        except ValueError:
            payload = None
        reason = graphql_error_text(payload, self._token)
        record = {
            "label": label,
            "operation": operation.name,
            "operation_version": operation.version,
            "operation_document_sha256": operation.document_sha256,
            "variable_keys": sorted(variables),
            "http_status": response.status_code,
            "response_bytes": len(response.content),
            "latency_seconds": round(latency, 3),
            "complexity": extract_complexity(payload, response.headers),
            "error": redact_text(reason, self._token) if reason else None,
            "complexity_failure": is_complexity_failure(payload, reason),
            "schema_failure": is_schema_failure(reason),
            "retry_after_seconds": parse_retry_after(response.headers.get("Retry-After")),
            "safe_headers": safe_response_headers(response.headers),
            "safe_rate_headers": safe_rate_headers(response.headers),
            "physical_ordinal": self.calls,
            "at_utc": datetime.now(UTC).isoformat(),
        }
        self.attempts.append(record)
        ok = response.status_code == 200 and not reason and payload is not None
        return (payload if ok else None), record

    async def find_batch_size(
        self, account_id: int, match_ids: Sequence[int]
    ) -> dict[str, Any]:
        ladder = [size for size in BATCH_LADDER if size <= len(match_ids)] or [len(match_ids)]
        rungs: list[dict[str, Any]] = []
        for size in ladder:
            payload, record = await self.request(
                GET_DEEP_MATCH_BATCH,
                {"steamAccountId": account_id, "matchIds": list(match_ids[:size])},
                label=f"deep-batch-{size}",
            )
            rung = {
                "batch_size": size,
                "http_status": record["http_status"],
                "complexity": record["complexity"],
                "complexity_failure": record["complexity_failure"],
                "schema_failure": record["schema_failure"],
                "error": record["error"],
                "response_bytes": record["response_bytes"],
                "latency_seconds": record["latency_seconds"],
            }
            if payload is not None:
                rung["summary"] = summarise_deep_batch(payload)
                rungs.append(rung)
                return {
                    "ladder": rungs,
                    "largest_successful_batch": size,
                    "bytes_per_match": round(record["response_bytes"] / size),
                }
            rungs.append(rung)
            if record["schema_failure"]:
                # A field the endpoint does not know will not start working at a
                # smaller batch size. Stop rather than burn the budget.
                break
        return {"ladder": rungs, "largest_successful_batch": None, "bytes_per_match": None}


def projected_cost(batch_size: int, accounts: int, matches_per_account: int) -> dict[str, Any]:
    calls_per_account = -(-matches_per_account // batch_size)
    total = calls_per_account * accounts
    return {
        "batch_size": batch_size,
        "accounts": accounts,
        "matches_per_account": matches_per_account,
        "calls_per_account": calls_per_account,
        "total_calls": total,
        "days_at_15000_per_day": round(total / 15_000, 2),
    }


async def run(args: argparse.Namespace) -> int:
    token = load_stratz_token(Path(args.dotenv))
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_root) / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "phase": "V7_PASS2_SIZING_PROBE",
        "schema_version": "stratz-v7-pass2-probe-1.0.0",
        "at_utc": datetime.now(UTC).isoformat(),
        "endpoint": args.endpoint,
        "max_physical_calls": args.max_calls,
        "operations": {
            op.name: {"version": op.version, "document_sha256": op.document_sha256}
            for op in (
                GET_DEEP_MATCH_BATCH,
                PROBE_LOCATION_REPORT,
                PROBE_ITEM_VOCABULARY,
                GET_PLAYER_RANK_HISTORY,
            )
        },
        "identities_included": False,
        "raw_bodies_retained": False,
    }

    async with Pass2Probe(
        token,
        endpoint=args.endpoint,
        output_dir=output_dir,
        timeout_seconds=args.timeout,
        max_calls=args.max_calls,
    ) as probe:
        try:
            report["batch_sizing"] = await probe.find_batch_size(
                args.steam_account_id, args.match_ids
            )

            payload, _ = await probe.request(
                PROBE_LOCATION_REPORT,
                {"steamAccountId": args.steam_account_id, "matchIds": list(args.match_ids[:2])},
                label="location-report",
            )
            report["location_report"] = summarise_location_report(payload)

            payload, _ = await probe.request(
                PROBE_ITEM_VOCABULARY, {}, label="item-vocabulary"
            )
            report["item_vocabulary"] = summarise_item_vocabulary(payload)

            if args.probe_rank:
                payload, _ = await probe.request(
                    GET_PLAYER_RANK_HISTORY,
                    {"steamAccountId": args.steam_account_id},
                    label="rank-history-display-only",
                )
                ranks = (((payload or {}).get("data") or {}).get("player") or {}).get("ranks")
                report["rank_history"] = {
                    "present": isinstance(ranks, list),
                    "entries": len(ranks) if isinstance(ranks, list) else 0,
                    "element_keys": sorted(ranks[0].keys())
                    if isinstance(ranks, list) and ranks and isinstance(ranks[0], Mapping)
                    else [],
                    "note": "DISPLAY ONLY. Must not reach a research table or feature.",
                }
        except BudgetExceeded as exc:
            report["stopped"] = str(exc)

        report["attempts"] = probe.attempts
        report["physical_calls"] = probe.calls

    batch = report.get("batch_sizing", {}).get("largest_successful_batch")
    if batch:
        report["projected_cost"] = [
            projected_cost(batch, accounts, 500) for accounts in (300, 600, 900)
        ]

    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"physical calls: {report['physical_calls']}")
    print(f"largest successful batch: {batch}")
    if batch:
        for row in report["projected_cost"]:
            print(
                f"  {row['accounts']:>3} accounts x {row['matches_per_account']} matches"
                f" -> {row['total_calls']:,} calls, {row['days_at_15000_per_day']} days"
            )
    print(f"locationReport usable: {report.get('location_report', {}).get('usable')}")
    print(f"item vocabulary usable: {report.get('item_vocabulary', {}).get('usable')}")
    print(f"report: {output_dir / 'report.json'}")
    return 0 if batch else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotenv", required=True, help="path to the dotenv holding STRATZ_API_TOKEN")
    parser.add_argument("--steam-account-id", type=int, required=True)
    parser.add_argument(
        "--match-ids",
        type=int,
        nargs="+",
        required=True,
        help="at least 8 parsed match ids belonging to that account",
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-calls", type=int, default=MAX_PHYSICAL_CALLS)
    parser.add_argument(
        "--probe-rank",
        action="store_true",
        help="also probe rank history (display-only; never an analytical input)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_calls > MAX_PHYSICAL_CALLS:
        raise SystemExit(
            f"--max-calls above the built-in ceiling of {MAX_PHYSICAL_CALLS} is refused"
        )
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
