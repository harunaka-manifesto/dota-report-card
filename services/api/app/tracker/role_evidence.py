"""Replay-only lane/ward observations; vendor position labels never enter roles."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.tracker.normalization import Provider, replay_available

ROLE_EVIDENCE_VERSION = "role-evidence-1"


def replay_role_inputs(raw: Mapping[str, Any], provider: Provider, summary: dict[str, Any]) -> list[dict[str, Any]]:
    available = replay_available(raw, provider)
    source = {p["player_slot" if provider == "opendota" else "playerSlot"]: p for p in raw["players"]}
    result = []
    for player in summary["players"]:
        slot = player["player_slot"]
        entry = source[slot if slot < 5 else slot + 123]
        lane = wards = None
        paths: dict[str, Any] = {}
        if available and provider == "opendota":
            value = entry.get("lane_role")
            if type(value) is int and entry.get("is_roaming") is not True:
                lane = {1: "SAFE", 2: "MID", 3: "OFF"}.get(value)
            observer, sentry = entry.get("obs_placed"), entry.get("sen_placed")
            if all(type(v) is int and v >= 0 for v in (observer, sentry)):
                wards = observer + sentry
            paths = {"lane": "players[].lane_role", "wards_placed": "players[].obs_placed + players[].sen_placed"}
        elif available:
            stats = entry.get("stats")
            events = stats.get("wards") if isinstance(stats, Mapping) else None
            # The retained STRATZ operation has no lane/early-position evidence.
            # An explicit complete empty event list is zero; absent/null is not.
            if isinstance(events, list) and all(isinstance(e, Mapping) and type(e.get("time")) is int
                    and e["time"] <= summary["duration_seconds"] and type(e.get("type")) is int and e["type"] in {0, 1} for e in events):
                wards = len(events)
            paths = {"lane": None, "wards_placed": "players[].stats.wards"}
        result.append({**player, "lane": lane, "wards_placed": wards, "role_source_paths": paths})
    return result
