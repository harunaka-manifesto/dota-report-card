"""Stored 0–10 minute net-worth comparison for a Mid player's match detail."""
from __future__ import annotations

from typing import Any

from .offlane_context import lane_panel

CONTRACT_VERSION = "mid-context-v1"


def evaluate(features: list[dict[str, Any]], *, viewer: int,
             positions: dict[int, int | None], duration: int,
             quarantined: list[str]) -> dict[str, Any]:
    enemies = range(5, 10) if viewer < 5 else range(5)
    mids = [slot for slot in enemies if positions.get(slot) == 2]
    opponent = mids[0] if len(mids) == 1 else None
    hero = features[opponent]["summary"].get("hero_id") if opponent is not None else None
    conflicts = set(quarantined)
    if (opponent is None or type(hero) is not int or hero <= 0
            or "duration_seconds" in conflicts or f"players.{opponent}.hero_id" in conflicts):
        reason = "MID_UNCLEAR" if opponent is None or type(hero) is not int or hero <= 0 else "SOURCE_DISAGREEMENT"
        return {"contract_version": CONTRACT_VERSION, "enemy_mid_hero_id": None,
                "net_worth": {"state": "UNAVAILABLE", "reason": reason, "points": []}}
    return {"contract_version": CONTRACT_VERSION, "enemy_mid_hero_id": hero,
            "net_worth": lane_panel(features, viewer, opponent, "net_worth", duration,
                                    conflicts, "enemy_mid")}
