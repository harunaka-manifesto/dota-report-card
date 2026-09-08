#!/usr/bin/env python3
"""Fetch the STRATZ item vocabulary once and persist it as static reference data.

The item vocabulary (item id → name, cost) is used by item-timing analysis to
distinguish consumables from real items. Fetch it once from the STRATZ GraphQL
API and commit the result as a static JSON file. The file serves as an
immutable reference for all downstream item classification.

This script makes exactly one HTTP POST to the GraphQL endpoint. The token is
never logged or stored; only the deterministic, sorted JSON output is kept.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
for candidate in (str(ROOT), str(API_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from app.stratz.queries import PROBE_ITEM_VOCABULARY  # noqa: E402

DEFAULT_ENDPOINT = "https://api.stratz.com/graphql"
DEFAULT_OUTPUT_PATH = API_ROOT / "app" / "stratz" / "item_vocabulary.json"
DEFAULT_TIMEOUT_SECONDS = 30.0


def load_stratz_token(dotenv_path: Path) -> str:
    """Read only the STRATZ token from an explicitly supplied dotenv file."""
    try:
        values = dotenv_values(dotenv_path, interpolate=False)
    except OSError as exc:
        raise RuntimeError("cannot read the supplied dotenv file") from exc
    token = values.get("STRATZ_API_TOKEN")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("STRATZ_API_TOKEN is missing from the supplied dotenv file")
    return token.strip()


def redact_text(value: str, secret: str | None) -> str:
    """Redact a token without exposing any token-derived diagnostic."""
    if secret:
        return value.replace(secret, "[REDACTED]")
    return value


async def fetch_item_vocabulary(
    token: str, *, endpoint: str, timeout_seconds: float
) -> Mapping[str, Any] | None:
    """Make exactly one HTTP POST to fetch the item vocabulary.

    Returns the parsed JSON payload or None if the request failed.
    """
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(
            endpoint,
            json={"query": PROBE_ITEM_VOCABULARY.document, "variables": {}},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "STRATZ_API_DOTA_REPORT_CARD_ITEM_VOCABULARY_FETCH",
            },
        )
    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP {response.status_code} from {endpoint}: {response.text[:200]}"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"invalid JSON in response: {exc}") from exc

    # Check for GraphQL errors.
    if isinstance(payload, Mapping):
        errors = payload.get("errors")
        if errors:
            error_text = str(errors)
            raise RuntimeError(f"GraphQL error: {redact_text(error_text, token)}")
    return payload


def process_items(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Extract and validate items from the response payload.

    The response shape is:
      {
        "data": {
          "constants": {
            "items": [
              {"id": int, "displayName": str, "shortName": str, "stat": {...} or null}
            ]
          }
        }
      }

    STRATZ returns "stat": null for some items (observed: ~15 of 575), so the
    cost lookup must tolerate a null. Extract only id, name (from displayName),
    short_name (from shortName), and cost (from nested stat). Sort by id.
    """
    if not isinstance(payload, Mapping):
        raise ValueError("payload is not a dict")
    constants = ((payload or {}).get("data") or {}).get("constants") or {}
    items_raw = constants.get("items") or []
    if not isinstance(items_raw, list):
        raise ValueError("items is not a list")

    items: list[dict[str, Any]] = []
    for raw in items_raw:
        if not isinstance(raw, Mapping):
            continue
        item_id = raw.get("id")
        name = raw.get("displayName")
        short_name = raw.get("shortName")
        cost = ((raw or {}).get("stat") or {}).get("cost")

        if item_id is None or name is None or short_name is None:
            continue

        items.append(
            {
                "id": item_id,
                "name": name,
                "short_name": short_name,
                "cost": cost,  # cost may be None
            }
        )

    # Sort by id for deterministic output.
    items.sort(key=lambda x: x["id"])
    return items


def build_output(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the final committed JSON structure."""
    items_with_cost = sum(1 for item in items if item.get("cost") is not None)
    return {
        "schema_version": "stratz-item-vocabulary-1.0.0",
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "operation_document_sha256": PROBE_ITEM_VOCABULARY.document_sha256,
        "item_count": len(items),
        "items_with_cost": items_with_cost,
        "items": items,
    }


async def main(args: argparse.Namespace) -> int:
    token = load_stratz_token(Path(args.dotenv))
    output_path = Path(args.out)

    # Check if output already exists and is non-empty, refuse to overwrite unless --force.
    if output_path.exists() and output_path.stat().st_size > 0 and not args.force:
        print(f"output file {output_path} already exists (use --force to overwrite)")
        return 1

    print(f"fetching item vocabulary from {args.endpoint}...", file=sys.stderr)
    start = time.monotonic()
    try:
        payload = await fetch_item_vocabulary(
            token, endpoint=args.endpoint, timeout_seconds=args.timeout
        )
    finally:
        # Never log or print the token.
        token = ""  # type: ignore

    elapsed = time.monotonic() - start
    print(f"fetched in {elapsed:.1f}s", file=sys.stderr)

    if payload is None:
        print("failed to fetch payload", file=sys.stderr)
        return 1

    items = process_items(payload)
    print(f"processed {len(items)} items", file=sys.stderr)

    output = build_output(items)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=False) + "\n")
    print(f"wrote {output_path}", file=sys.stderr)
    print(
        f"total: {output['item_count']} items, {output['items_with_cost']} with cost",
        file=sys.stderr,
    )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dotenv",
        default=".env",
        help="path to the dotenv holding STRATZ_API_TOKEN (default: .env)",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT_PATH),
        help="output JSON file path",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help="STRATZ GraphQL endpoint URL",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP request timeout in seconds",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing output file",
    )
    return parser


if __name__ == "__main__":
    import asyncio

    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(main(args)))
