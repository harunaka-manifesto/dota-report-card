"""Factual Carry economy, hero-damage and event timelines for Match Detail."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .item_references import normalize_key_item_purchases

CONTRACT_VERSION = "carry-context-v1"


def _empty(reason: str) -> dict[str, Any]:
    return {"state": "UNAVAILABLE", "reason": reason, "points": []}


def _series(features: list[dict[str, Any]], viewer: int, enemy: int, field: str,
            duration: int, quarantined: set[str]) -> dict[str, Any]:
    own_checkpoints = features[viewer].get("checkpoints")
    other_checkpoints = features[enemy].get("checkpoints")
    own = own_checkpoints.get(field) if isinstance(own_checkpoints, Mapping) else None
    other = other_checkpoints.get(field) if isinstance(other_checkpoints, Mapping) else None
    if not isinstance(own, dict) or not isinstance(other, dict):
        return _empty("TRAJECTORY_UNAVAILABLE")
    points = []
    for second in range(0, duration + 1, 60):
        key = str(second)
        if any(f"players.{slot}.series.{field}.{key}" in quarantined for slot in (viewer, enemy)):
            continue
        you, them = own.get(key), other.get(key)
        if type(you) is int and type(them) is int and you >= 0 and them >= 0:
            points.append({"time_seconds": second, "you": you, "enemy_carry": them,
                           "difference": you - them})
    if field == "hero_damage_earned" and points and points[0]["time_seconds"] == 0:
        if points[0]["you"] != 0 or points[0]["enemy_carry"] != 0:
            return _empty("TRAJECTORY_UNAVAILABLE")
    return {"state": "AVAILABLE" if points else "UNAVAILABLE",
            "reason": None if points else "TRAJECTORY_UNAVAILABLE", "points": points}


def _kills(features: list[dict[str, Any]], slot: int, duration: int,
           conflicts: set[str]) -> dict[str, Any]:
    if f"players.{slot}.values.kills" in conflicts:
        return {"state": "UNAVAILABLE", "reason": "SOURCE_DISAGREEMENT", "events": []}
    events = features[slot].get("events")
    rows = events.get("kills") if isinstance(events, Mapping) else None
    if not isinstance(rows, list) or any(
        not isinstance(row, Mapping) or type(row.get("time")) is not int
        or row["time"] > duration for row in rows
    ):
        return {"state": "UNAVAILABLE", "reason": "KILLS_UNAVAILABLE", "events": []}
    return {"state": "AVAILABLE", "reason": None,
            "events": [{"time_seconds": row["time"]} for row in sorted(rows, key=lambda r: r["time"])
                       if row["time"] >= 0]}


def _enemy_items(raw: Mapping[str, Any] | None, provider: str | None, slot: int,
                 duration: int) -> dict[str, Any]:
    players = raw.get("players") if isinstance(raw, Mapping) else None
    native_slot = slot if slot < 5 else slot + 123
    matches = [row for row in players if isinstance(row, Mapping)
               and row.get("player_slot" if provider == "opendota" else "playerSlot") == native_slot] \
        if isinstance(players, list) and provider in {"opendota", "stratz"} else []
    if len(matches) != 1:
        return {"state": "UNAVAILABLE", "reason": "ITEMS_UNAVAILABLE", "items": []}
    assert isinstance(provider, str)
    player = matches[0]
    rows = player.get("purchase_log") if provider == "opendota" else (
        player.get("stats", {}).get("itemPurchases")
        if isinstance(player.get("stats"), Mapping) else None
    )
    items = normalize_key_item_purchases(rows, provider, duration)
    if items is None:
        return {"state": "UNAVAILABLE", "reason": "ITEMS_UNAVAILABLE", "items": []}
    return {"state": "AVAILABLE", "reason": None, "items": items}


def evaluate(features: list[dict[str, Any]], *, viewer: int,
             positions: dict[int, int | None], duration: int,
             quarantined: list[str], raw: Mapping[str, Any] | None = None,
             provider: str | None = None) -> dict[str, Any]:
    enemy_slots = range(5, 10) if viewer < 5 else range(5)
    carries = [slot for slot in enemy_slots if positions.get(slot) == 1]
    enemy = carries[0] if len(carries) == 1 else None
    hero = features[enemy]["summary"].get("hero_id") if enemy is not None else None
    conflicts = set(quarantined)
    if (enemy is None or type(hero) is not int or hero <= 0
            or "duration_seconds" in conflicts or f"players.{enemy}.hero_id" in conflicts):
        reason = "CARRY_UNCLEAR" if enemy is None or type(hero) is not int or hero <= 0 else "SOURCE_DISAGREEMENT"
        return {"contract_version": CONTRACT_VERSION, "enemy_carry_hero_id": None,
                "net_worth": _empty(reason), "hero_damage": _empty(reason),
                "enemy_key_items": {"state": "UNAVAILABLE", "reason": reason, "items": []},
                "you_kills": {"state": "UNAVAILABLE", "reason": reason, "events": []},
                "enemy_carry_kills": {"state": "UNAVAILABLE", "reason": reason, "events": []}}
    return {"contract_version": CONTRACT_VERSION, "enemy_carry_hero_id": hero,
            "net_worth": _series(features, viewer, enemy, "net_worth", duration, conflicts),
            "hero_damage": _series(features, viewer, enemy, "hero_damage_earned", duration, conflicts),
            "enemy_key_items": _enemy_items(raw, provider, enemy, duration),
            "you_kills": _kills(features, viewer, duration, conflicts),
            "enemy_carry_kills": _kills(features, enemy, duration, conflicts)}
