"""Fail-closed STRATZ deep-match normalization for the V7 runtime."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.errors import StratzSchemaDrift
from app.stratz.field_policy import forbidden_fields_in

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_TRAJECTORIES = (
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
    "level",
    "tripsFountainPerMinute",
)
_EVENTS = {
    "kill_events": ("killEvents", ("time",)),
    "death_events": ("deathEvents", ("time",)),
    "assist_events": ("assistEvents", ("time",)),
    "item_purchases": ("itemPurchases", ("time", "itemId")),
    "wards": ("wards", ("time", "type", "positionX", "positionY")),
}
_BOOL_FIELDS = frozenset({"isRadiant"})


def _snake(value: str) -> str:
    return _CAMEL.sub("_", value).lower()


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StratzSchemaDrift(f"STRATZ schema drift at {path}")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise StratzSchemaDrift(f"STRATZ schema drift at {path}")
    return value


def _int(value: Any, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise StratzSchemaDrift(f"STRATZ schema drift at {path}")
    return value


def _bool(value: Any, path: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise StratzSchemaDrift(f"STRATZ schema drift at {path}")
    return value


def _str(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise StratzSchemaDrift(f"STRATZ schema drift at {path}")
    return value


def _series(value: Any, path: str) -> list[int | None] | None:
    if value is None:
        return None
    return [_int(item, f"{path}[{index}]") for index, item in enumerate(_sequence(value, path))]


def _events(value: Any, fields: Sequence[str], path: str) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_sequence(value, path)):
        event = _mapping(raw, f"{path}[{index}]")
        rows.append(
            {
                _snake(field): (
                    _bool(event.get(field), f"{path}[{index}].{field}")
                    if field in _BOOL_FIELDS
                    else _int(event.get(field), f"{path}[{index}].{field}")
                )
                for field in fields
            }
        )
    return rows


def _farm(stats: Mapping[str, Any], path: str) -> dict[str, Any] | None:
    raw = stats.get("farmDistributionReport")
    if raw is None:
        return None
    farm = _mapping(raw, f"{path}.farmDistributionReport")
    return {
        "creep_location": _events(
            farm.get("creepLocation"), ("id", "count", "gold", "xp"), f"{path}.creepLocation"
        ),
        "neutral_location": _events(
            farm.get("neutralLocation"), ("id", "count", "gold", "xp"), f"{path}.neutralLocation"
        ),
    }


def _all_players(value: Any, path: str) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_sequence(value, path)):
        player = _mapping(raw, f"{path}[{index}]")
        stats_raw = player.get("stats")
        stats = (
            _mapping(stats_raw, f"{path}[{index}].stats")
            if stats_raw is not None
            else None
        )
        rows.append(
            {
                "player_slot": _int(player.get("playerSlot"), f"{path}[{index}].playerSlot"),
                "is_radiant": _bool(player.get("isRadiant"), f"{path}[{index}].isRadiant"),
                "is_victory": _bool(player.get("isVictory"), f"{path}[{index}].isVictory"),
                "hero_id": _int(player.get("heroId"), f"{path}[{index}].heroId"),
                "position_native": _str(player.get("position"), f"{path}[{index}].position"),
                "role_native": _str(player.get("role"), f"{path}[{index}].role"),
                "lane_native": _str(player.get("lane"), f"{path}[{index}].lane"),
                "kills": _int(player.get("kills"), f"{path}[{index}].kills"),
                "deaths": _int(player.get("deaths"), f"{path}[{index}].deaths"),
                "assists": _int(player.get("assists"), f"{path}[{index}].assists"),
                "num_last_hits": _int(
                    player.get("numLastHits"), f"{path}[{index}].numLastHits"
                ),
                "num_denies": _int(player.get("numDenies"), f"{path}[{index}].numDenies"),
                "gold_per_minute": _int(
                    player.get("goldPerMinute"), f"{path}[{index}].goldPerMinute"
                ),
                "experience_per_minute": _int(
                    player.get("experiencePerMinute"), f"{path}[{index}].experiencePerMinute"
                ),
                "networth": _int(player.get("networth"), f"{path}[{index}].networth"),
                "hero_damage": _int(player.get("heroDamage"), f"{path}[{index}].heroDamage"),
                "tower_damage": _int(player.get("towerDamage"), f"{path}[{index}].towerDamage"),
                "hero_healing": _int(player.get("heroHealing"), f"{path}[{index}].heroHealing"),
                "kill_events": (
                    _events(
                        stats.get("killEvents"),
                        ("time",),
                        f"{path}[{index}].stats.killEvents",
                    )
                    if stats is not None
                    else None
                ),
            }
        )
    return rows


def normalize_deep_matches(
    data: Mapping[str, Any], *, requested_ids: Sequence[int]
) -> list[dict[str, Any]]:
    """Normalize the exact deep selection used by the reviewed Pass-2 collector."""

    forbidden = forbidden_fields_in(data)
    if forbidden:
        raise StratzSchemaDrift(f"forbidden analytical field(s) in deep response: {sorted(forbidden)!r}")
    player = _mapping(data.get("player"), "data.player")
    matches = _sequence(player.get("matches"), "data.player.matches")
    requested = set(requested_ids)
    rows: list[dict[str, Any]] = []
    returned: set[int] = set()
    for index, raw_match in enumerate(matches):
        path = f"data.player.matches[{index}]"
        match = _mapping(raw_match, path)
        match_id = _int(match.get("id"), f"{path}.id")
        if match_id is None or match_id not in requested or match_id in returned:
            raise StratzSchemaDrift("STRATZ returned an unrequested or duplicate deep match")
        returned.add(match_id)
        players = _sequence(match.get("players"), f"{path}.players")
        if len(players) != 1:
            raise StratzSchemaDrift(f"{path}: expected exactly one requested player")
        own = _mapping(players[0], f"{path}.players[0]")
        stats = _mapping(own.get("stats") or {}, f"{path}.players[0].stats")
        events = {
            target: _events(stats.get(source), fields, f"{path}.stats.{source}")
            for target, (source, fields) in _EVENTS.items()
        }
        rows.append(
            {
                "match_id": match_id,
                "did_radiant_win": _bool(match.get("didRadiantWin"), f"{path}.didRadiantWin"),
                "duration_seconds": _int(match.get("durationSeconds"), f"{path}.durationSeconds"),
                "started_at": _int(match.get("startDateTime"), f"{path}.startDateTime"),
                "ended_at": _int(match.get("endDateTime"), f"{path}.endDateTime"),
                "game_mode_native": _str(match.get("gameMode"), f"{path}.gameMode"),
                "lobby_type_native": _str(match.get("lobbyType"), f"{path}.lobbyType"),
                "game_version_id": _int(match.get("gameVersionId"), f"{path}.gameVersionId"),
                "radiant_kills": _series(match.get("radiantKills"), f"{path}.radiantKills"),
                "dire_kills": _series(match.get("direKills"), f"{path}.direKills"),
                "radiant_networth_leads": _series(
                    match.get("radiantNetworthLeads"), f"{path}.radiantNetworthLeads"
                ),
                "bottom_lane_outcome_native": _str(
                    match.get("bottomLaneOutcome"), f"{path}.bottomLaneOutcome"
                ),
                "mid_lane_outcome_native": _str(
                    match.get("midLaneOutcome"), f"{path}.midLaneOutcome"
                ),
                "top_lane_outcome_native": _str(
                    match.get("topLaneOutcome"), f"{path}.topLaneOutcome"
                ),
                "tower_deaths": _events(
                    match.get("towerDeaths"),
                    ("time", "isRadiant", "npcId", "attacker"),
                    f"{path}.towerDeaths",
                ),
                "all_players": _all_players(match.get("allPlayers"), f"{path}.allPlayers"),
                "self": {
                    "player_slot": _int(own.get("playerSlot"), f"{path}.p.playerSlot"),
                    "is_radiant": _bool(own.get("isRadiant"), f"{path}.p.isRadiant"),
                    "is_victory": _bool(own.get("isVictory"), f"{path}.p.isVictory"),
                    "hero_id": _int(own.get("heroId"), f"{path}.p.heroId"),
                    "position_native": _str(own.get("position"), f"{path}.p.position"),
                    "role_native": _str(own.get("role"), f"{path}.p.role"),
                    "lane_native": _str(own.get("lane"), f"{path}.p.lane"),
                    "leaver_status_native": _str(
                        own.get("leaverStatus"), f"{path}.p.leaverStatus"
                    ),
                    "kills": _int(own.get("kills"), f"{path}.p.kills"),
                    "assists": _int(own.get("assists"), f"{path}.p.assists"),
                    "hero_healing": _int(own.get("heroHealing"), f"{path}.p.heroHealing"),
                    "tower_damage": _int(own.get("towerDamage"), f"{path}.p.towerDamage"),
                    "trajectories": {
                        _snake(field): _series(stats.get(field), f"{path}.stats.{field}")
                        for field in _TRAJECTORIES
                    },
                    "events": events,
                    "tower_damage_report": _events(
                        stats.get("towerDamageReport"),
                        ("npcId", "damage"),
                        f"{path}.stats.towerDamageReport",
                    ),
                    "farm_distribution": _farm(stats, f"{path}.stats"),
                },
            }
        )
    return rows


__all__ = ["normalize_deep_matches"]
