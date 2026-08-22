"""Normalize OpenDota aggregate endpoints into the empirical schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import PARSER_VERSION, SCHEMA_VERSION
from ..errors import SourceSchemaError
from ..schemas import HeroIdentity

ENDPOINT_FILES = {
    "durations": "durations.json",
    "itemPopularity": "itemPopularity.json",
    "matchups": "matchups.json",
}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise SourceSchemaError(f"Unable to read OpenDota snapshot file: {path}") from exc


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise SourceSchemaError(f"OpenDota field {field} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SourceSchemaError(f"OpenDota field {field} must be an integer") from exc
    if isinstance(value, float) and value != parsed:
        raise SourceSchemaError(f"OpenDota field {field} must be an integer")
    return parsed


def _rate(wins: int, matches: int) -> float | None:
    return round(wins / matches, 6) if matches > 0 else None


def _bracket_performance(row: dict[str, Any], hero_id: int) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    ranks = sorted(
        key[:-5]
        for key in row
        if key.endswith("_pick") and key[:-5].isdigit()
    )
    for rank in ranks:
        picks = _integer(row[rank + "_pick"], f"{hero_id}.{rank}_pick")
        win_key = rank + "_win"
        if win_key not in row:
            raise SourceSchemaError(f"OpenDota heroStats is missing {win_key} for hero {hero_id}")
        wins = _integer(row[win_key], f"{hero_id}.{win_key}")
        values.append(
            {
                "bracket": f"rank_tier_{rank}",
                "population": "public_aggregate",
                "picks": picks,
                "wins": wins,
                "win_rate": _rate(wins, picks),
            }
        )

    for label, population, pick_key, win_key in (
        ("public", "public_aggregate", "pub_pick", "pub_win"),
        ("professional", "professional", "pro_pick", "pro_win"),
    ):
        if pick_key not in row and win_key not in row:
            continue
        if pick_key not in row or win_key not in row:
            raise SourceSchemaError(
                f"OpenDota heroStats is missing one of {pick_key}/{win_key} for hero {hero_id}"
            )
        picks = _integer(row[pick_key], f"{hero_id}.{pick_key}")
        wins = _integer(row[win_key], f"{hero_id}.{win_key}")
        values.append(
            {
                "bracket": label,
                "population": population,
                "picks": picks,
                "wins": wins,
                "win_rate": _rate(wins, picks),
            }
        )
    return values


def _duration_profile(payload: Any, hero_id: int) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise SourceSchemaError(f"OpenDota durations for hero {hero_id} must be a list")
    result: list[dict[str, Any]] = []
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise SourceSchemaError(f"OpenDota durations row {index} for hero {hero_id} is invalid")
        try:
            duration_bin = _integer(row["duration_bin"], f"{hero_id}.duration_bin")
            games = _integer(row["games_played"], f"{hero_id}.games_played")
            wins = _integer(row["wins"], f"{hero_id}.wins")
        except KeyError as exc:
            raise SourceSchemaError(
                f"OpenDota durations row {index} for hero {hero_id} is missing {exc.args[0]}"
            ) from exc
        result.append(
            {
                "duration_bin_seconds": duration_bin,
                "games": games,
                "wins": wins,
                "win_rate": _rate(wins, games),
            }
        )
    return sorted(result, key=lambda item: item["duration_bin_seconds"])


def _item_profile(payload: Any, hero_id: int) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise SourceSchemaError(f"OpenDota itemPopularity for hero {hero_id} must be an object")
    result: list[dict[str, Any]] = []
    for raw_phase, items in sorted(payload.items()):
        if not isinstance(items, dict):
            raise SourceSchemaError(
                f"OpenDota itemPopularity phase {raw_phase} for hero {hero_id} is invalid"
            )
        phase = raw_phase.removesuffix("_game")
        total = 0
        rows: list[tuple[int, int]] = []
        for raw_item_id, raw_count in items.items():
            item_id = _integer(raw_item_id, f"{hero_id}.{raw_phase}.item_id")
            count = _integer(raw_count, f"{hero_id}.{raw_phase}.{raw_item_id}")
            rows.append((item_id, count))
            total += count
        for item_id, count in sorted(rows):
            result.append(
                {
                    "phase": phase,
                    "item_id": item_id,
                    "count": count,
                    "share": round(count / total, 6) if total > 0 else None,
                }
            )
    return result


def _matchup_profile(payload: Any, hero_id: int) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise SourceSchemaError(f"OpenDota matchups for hero {hero_id} must be a list")
    result: list[dict[str, Any]] = []
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise SourceSchemaError(f"OpenDota matchup row {index} for hero {hero_id} is invalid")
        try:
            opponent = _integer(row["hero_id"], f"{hero_id}.matchup.hero_id")
            games = _integer(row["games_played"], f"{hero_id}.matchup.games_played")
            wins = _integer(row["wins"], f"{hero_id}.matchup.wins")
        except KeyError as exc:
            raise SourceSchemaError(
                f"OpenDota matchup row {index} for hero {hero_id} is missing {exc.args[0]}"
            ) from exc
        result.append(
            {
                "opponent_hero_id": opponent,
                "games": games,
                "wins": wins,
                "win_rate": _rate(wins, games),
                "evidence_population": "opendota_aggregate",
                "population_note": (
                    "The OpenDota response does not identify a narrower population; "
                    "do not label this as general-player or professional-only data."
                ),
            }
        )
    return result


def _endpoint_meta(metadata: dict[str, Any], hero_id: int, endpoint: str) -> dict[str, Any]:
    return dict(metadata.get("hero_sources", {}).get(str(hero_id), {}).get(endpoint, {}))


def _normalized_row(
    row: dict[str, Any],
    *,
    snapshot_root: Path,
    metadata: dict[str, Any],
    identity: HeroIdentity | None,
) -> dict[str, Any]:
    hero_id = _integer(row.get("id"), "heroStats.id")
    endpoint_payloads = {
        endpoint: _read_json(snapshot_root / "heroes" / str(hero_id) / filename)
        for endpoint, filename in ENDPOINT_FILES.items()
    }
    bracket_performance = _bracket_performance(row, hero_id)
    duration_profile = _duration_profile(endpoint_payloads["durations"], hero_id)
    item_profile = _item_profile(endpoint_payloads["itemPopularity"], hero_id)
    matchup_profile = _matchup_profile(endpoint_payloads["matchups"], hero_id)
    observed = any(item.get("picks", 0) > 0 for item in bracket_performance)
    observed = observed or any(item.get("games", 0) > 0 for item in duration_profile)
    observed = observed or any(item.get("count", 0) > 0 for item in item_profile)
    observed = observed or any(item.get("games", 0) > 0 for item in matchup_profile)
    return {
        "hero_id": hero_id,
        "identity_name": identity.display_name if identity else row.get("localized_name"),
        "bracket_performance": bracket_performance,
        "duration_profile": duration_profile,
        "item_profile": item_profile,
        "matchup_profile": matchup_profile,
        "optional_valve_plus": {},
        "status": "observed" if observed else "unknown",
        "provenance": {
            "source": "OpenDota public aggregate endpoints",
            "fetched_at": metadata.get("fetched_at"),
            "parser_version": PARSER_VERSION,
            "endpoint_sources": {
                "heroStats": {
                    "source_url": metadata.get("source_urls", {}).get("heroStats"),
                    "raw_sha256": metadata.get("raw_sha256", {}).get("heroStats"),
                },
                **{
                    endpoint: {
                        "source_url": _endpoint_meta(metadata, hero_id, endpoint).get("source_url"),
                        "raw_sha256": _endpoint_meta(metadata, hero_id, endpoint).get("raw_sha256"),
                    }
                    for endpoint in ENDPOINT_FILES
                },
            },
            "field_sources": {
                "bracket_performance": "opendota.heroStats",
                "duration_profile": "opendota.heroes/{hero_id}/durations",
                "item_profile": "opendota.heroes/{hero_id}/itemPopularity",
                "matchup_profile": "opendota.heroes/{hero_id}/matchups",
            },
            "population_notes": {
                "bracket_performance": "Rank-tier/public aggregate fields are retained with their source labels.",
                "matchup_profile": "OpenDota matchup payload does not expose a narrower population label.",
            },
        },
    }


def normalize_opendota_snapshot(
    root: str | Path,
    identities: list[HeroIdentity] | None = None,
) -> dict[str, Any]:
    snapshot_root = Path(root)
    metadata = _read_json(snapshot_root / "metadata.json")
    payload = _read_json(snapshot_root / "heroStats.json")
    if not isinstance(payload, list) or not payload:
        raise SourceSchemaError("OpenDota heroStats snapshot must contain a non-empty list")
    identity_by_id = {identity.hero_id: identity for identity in identities or []}
    selected_raw = metadata.get("hero_ids")
    selected_ids = (
        {int(hero_id) for hero_id in selected_raw}
        if isinstance(selected_raw, list) and selected_raw
        else None
    )
    seen: set[int] = set()
    heroes: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict) or row.get("id") is None:
            raise SourceSchemaError("OpenDota heroStats snapshot contains an incomplete row")
        hero_id = _integer(row["id"], "heroStats.id")
        if selected_ids is not None and hero_id not in selected_ids:
            continue
        if hero_id in seen:
            raise SourceSchemaError(f"OpenDota heroStats snapshot duplicates hero {hero_id}")
        seen.add(hero_id)
        heroes.append(
            _normalized_row(
                row,
                snapshot_root=snapshot_root,
                metadata=metadata,
                identity=identity_by_id.get(hero_id),
            )
        )
    if selected_ids is not None and seen != selected_ids:
        missing = sorted(selected_ids - seen)
        raise SourceSchemaError(f"OpenDota snapshot is missing selected hero ids: {missing}")
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": str(metadata.get("snapshot_id", snapshot_root.name)),
        "source": "opendota",
        "status": str(metadata.get("status", "available")),
        "required": True,
        "fetched_at": metadata.get("fetched_at"),
        "source_url": metadata.get("source_urls", {}).get("heroStats"),
        "parser_version": PARSER_VERSION,
        "endpoint_semantics": metadata.get("endpoint_semantics", {}),
        "heroes": sorted(heroes, key=lambda item: item["hero_id"]),
        "provenance": {
            "source": "OpenDota public aggregate endpoints",
            "raw_snapshot": str(snapshot_root),
            "fetched_at": metadata.get("fetched_at"),
            "source_urls": metadata.get("source_urls", {}),
            "raw_sha256": metadata.get("raw_sha256", {}),
        },
    }
