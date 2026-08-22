"""Normalize optional Valve Plus fixture input into a non-blocking shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import PARSER_VERSION, SCHEMA_VERSION


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_valve_plus_snapshot(
    root: str | Path,
    canonical_ids: set[int] | None = None,
) -> dict[str, Any]:
    snapshot_root = Path(root)
    try:
        metadata = _read(snapshot_root / "metadata.json")
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "schema_version": SCHEMA_VERSION,
            "source": "valve_plus",
            "status": "invalid_schema",
            "required": False,
            "reason": "metadata_missing_or_invalid",
            "heroes": [],
        }
    status = str(metadata.get("status", "unavailable"))
    base = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": str(metadata.get("snapshot_id", snapshot_root.name)),
        "source": "valve_plus",
        "status": status,
        "required": False,
        "reason": metadata.get("reason"),
        "fetched_at": metadata.get("fetched_at"),
        "source_url": metadata.get("source_url"),
        "parser_version": PARSER_VERSION,
        "heroes": [],
        "provenance": {
            "source": "Valve Dota Plus optional provider",
            "source_url": metadata.get("source_url"),
            "raw_sha256": metadata.get("raw_sha256"),
            "fetched_at": metadata.get("fetched_at"),
        },
    }
    if status != "available":
        return base
    try:
        payload = _read(snapshot_root / "payload.json")
    except (FileNotFoundError, json.JSONDecodeError):
        base["status"] = "invalid_schema"
        base["reason"] = "payload_missing_or_invalid"
        return base
    rows = payload.get("heroes") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        base["status"] = "invalid_schema"
        base["reason"] = "payload_must_contain_a_heroes_list"
        return base
    heroes: list[dict[str, Any]] = []
    unknown = False
    for row in rows:
        if not isinstance(row, dict):
            base["status"] = "invalid_schema"
            base["reason"] = "hero_row_is_not_an_object"
            return base
        raw_id = row.get("hero_id", row.get("id"))
        if raw_id is None:
            base["status"] = "invalid_schema"
            base["reason"] = "hero_row_has_no_integer_id"
            return base
        try:
            hero_id = int(str(raw_id))
        except (TypeError, ValueError):
            base["status"] = "invalid_schema"
            base["reason"] = "hero_row_has_no_integer_id"
            return base
        if canonical_ids is not None and hero_id not in canonical_ids:
            unknown = True
            continue
        heroes.append({"hero_id": hero_id, "data": row})
    base["heroes"] = sorted(heroes, key=lambda item: item["hero_id"])
    if unknown:
        base["status"] = "partial"
        base["reason"] = "payload_contains_unknown_canonical_heroes"
    return base
