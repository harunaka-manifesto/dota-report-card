"""Stored, source-neutral lane checkpoints for an offlaner's match detail."""
from __future__ import annotations

from typing import Any

CONTRACT_VERSION = "offlane-context-v1"


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
             quarantined: list[str]) -> dict[str, Any]:
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
                "net_worth": empty, "xp": empty.copy()}
    conflicts = set(quarantined)
    return {"contract_version": CONTRACT_VERSION, "enemy_carry_hero_id": hero,
            "net_worth": _panel(features, viewer, carry, "net_worth", duration, conflicts),
            "xp": _panel(features, viewer, carry, "xp_earned", duration, conflicts)}
