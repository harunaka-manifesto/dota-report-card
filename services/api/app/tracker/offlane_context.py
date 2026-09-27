"""Stored laning checkpoints and detected fights for an offlaner's match detail."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CONTRACT_VERSION = "offlane-context-v2"


def _unavailable_fights(reason: str) -> dict[str, Any]:
    return {"state": "UNAVAILABLE", "reason": reason, "segments": []}


def evaluate_fights(raw: Mapping[str, Any] | None, *, viewer: int, duration: int,
                    quarantined: list[str]) -> dict[str, Any]:
    """Use only a complete OpenDota fight array with canonical player ordering."""
    if raw is None or type(raw.get("version")) is not int or raw["version"] <= 0:
        return _unavailable_fights("FIGHTS_UNAVAILABLE")
    if ("duration_seconds" in quarantined or any(
        path.startswith("players.") and path.endswith((".hero_id", ".account_id", ".team"))
        for path in quarantined if isinstance(path, str)
    )):
        return _unavailable_fights("SOURCE_DISAGREEMENT")
    roster = raw.get("players")
    fights = raw.get("teamfights")
    slots = [0, 1, 2, 3, 4, 128, 129, 130, 131, 132]
    if (type(viewer) is not int or viewer not in range(10)
            or type(duration) is not int or duration < 0 or raw.get("duration") != duration
            or not isinstance(roster, list) or [p.get("player_slot") if isinstance(p, Mapping) else None
                                                     for p in roster] != slots
            or not isinstance(fights, list)):
        return _unavailable_fights("FIGHTS_INVALID")
    segments = []
    ally = range(0, 5) if viewer < 5 else range(5, 10)
    enemy = range(5, 10) if viewer < 5 else range(0, 5)
    for index, fight in enumerate(fights, 1):
        if not isinstance(fight, Mapping):
            return _unavailable_fights("FIGHTS_INVALID")
        start, end, players = fight.get("start"), fight.get("end"), fight.get("players")
        if (type(start) is not int or type(end) is not int or not 0 <= start < end <= duration
                or not isinstance(players, list) or len(players) != 10):
            return _unavailable_fights("FIGHTS_INVALID")
        if any(not isinstance(player, Mapping)
               or type(player.get("damage")) is not int or player["damage"] < 0
               or type(player.get("deaths")) is not int or player["deaths"] < 0
               or not isinstance(player.get("killed"), Mapping)
               or any(not isinstance(hero, str) or type(count) is not int or count < 0
                      for hero, count in player["killed"].items())
               for player in players):
            return _unavailable_fights("FIGHTS_INVALID")
        own_damage = players[viewer]["damage"]
        allied_damage = sum(players[slot]["damage"] for slot in ally)
        ally_deaths = sum(players[slot]["deaths"] for slot in ally)
        enemy_deaths = sum(players[slot]["deaths"] for slot in enemy)
        segments.append({
            "segment_index": index, "start_seconds": start, "end_seconds": end,
            "offlaner_damage": own_damage, "allied_damage_total": allied_damage,
            "damage_share": own_damage / allied_damage if allied_damage else None,
            "damage_participated": own_damage > 0,
            "offlaner_kills": sum(count for hero, count in players[viewer]["killed"].items()
                                   if hero.startswith("npc_dota_hero_")),
            "offlaner_deaths": players[viewer]["deaths"],
            "allied_hero_deaths": ally_deaths, "enemy_hero_deaths": enemy_deaths,
            "death_trade": "FAVORABLE" if ally_deaths < enemy_deaths else
                           "UNFAVORABLE" if ally_deaths > enemy_deaths else "EVEN",
        })
    return {"state": "AVAILABLE", "reason": None, "segments": segments}


def _panel(features: list[dict[str, Any]], viewer: int, carry: int, field: str,
           duration: int, quarantined: set[str]) -> dict[str, Any]:
    own_checkpoints = features[viewer].get("checkpoints")
    enemy_checkpoints = features[carry].get("checkpoints")
    own = own_checkpoints.get(field) if isinstance(own_checkpoints, dict) else None
    opponent = enemy_checkpoints.get(field) if isinstance(enemy_checkpoints, dict) else None
    if not isinstance(own, dict) or not isinstance(opponent, dict):
        return {"state": "UNAVAILABLE", "reason": "TRAJECTORY_UNAVAILABLE", "points": []}
    points = []
    for second in range(0, min(duration, 600) + 1, 60):
        key = str(second)
        if any(f"players.{slot}.series.{field}.{key}" in quarantined for slot in (viewer, carry)):
            continue
        you, enemy = own.get(key), opponent.get(key)
        if type(you) is not int or type(enemy) is not int or you < 0 or enemy < 0:
            continue
        if field == "xp_earned" and second == 0 and (you != 0 or enemy != 0):
            return {"state": "UNAVAILABLE", "reason": "TRAJECTORY_UNAVAILABLE", "points": []}
        points.append({"time_seconds": second, "you": you, "enemy_carry": enemy,
                       "difference": you - enemy})
    return {"state": "AVAILABLE" if points else "UNAVAILABLE",
            "reason": None if points else "TRAJECTORY_UNAVAILABLE", "points": points}


def evaluate(features: list[dict[str, Any]], *, viewer: int,
             positions: dict[int, int | None], duration: int,
             quarantined: list[str], fights: dict[str, Any] | None = None) -> dict[str, Any]:
    """Require a unique enemy Position 1; preserve partial real minute samples."""
    enemy_slots = range(5, 10) if viewer < 5 else range(5)
    carries = [slot for slot in enemy_slots if positions.get(slot) == 1]
    carry = carries[0] if len(carries) == 1 else None
    hero = features[carry]["summary"].get("hero_id") if carry is not None else None
    if (carry is None or type(hero) is not int or hero <= 0
            or "duration_seconds" in quarantined
            or f"players.{carry}.hero_id" in quarantined):
        reason = "CARRY_UNCLEAR" if carry is None or type(hero) is not int or hero <= 0 else "SOURCE_DISAGREEMENT"
        empty = {"state": "UNAVAILABLE", "reason": reason, "points": []}
        return {"contract_version": CONTRACT_VERSION, "enemy_carry_hero_id": None,
                "net_worth": empty, "xp": empty.copy(),
                "fights": fights if fights is not None else _unavailable_fights("FIGHTS_UNAVAILABLE")}
    conflicts = set(quarantined)
    return {"contract_version": CONTRACT_VERSION, "enemy_carry_hero_id": hero,
            "net_worth": _panel(features, viewer, carry, "net_worth", duration, conflicts),
            "xp": _panel(features, viewer, carry, "xp_earned", duration, conflicts),
            "fights": fights if fights is not None else _unavailable_fights("FIGHTS_UNAVAILABLE")}
