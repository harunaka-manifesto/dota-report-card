"""Replay event translation. Missing streams stay absent; raw evidence is immutable."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .normalization import Provider, opendota_summary, replay_available, stratz_summary

EVENT_VERSION = "replay-events-1"


def _stream(value: Any, duration: int) -> list[dict[str, Any]] | None:
    if not isinstance(value, list) or any(
        not isinstance(row, dict) or type(row.get("time")) is not int or row["time"] > duration
        for row in value
    ):
        return None
    return value


def replay_events(raw: Mapping[str, Any], provider: Provider) -> dict[str, Any]:
    summary = opendota_summary(raw) if provider == "opendota" else stratz_summary(raw)
    duration = summary["duration_seconds"]
    available = replay_available(raw, provider)
    players = []
    towers = None
    if available and provider == "stratz":
        native = _stream(raw.get("towerDeaths"), duration)
        if native is not None and all(type(e.get("isRadiant")) is bool and type(e.get("npcId")) is int and e["npcId"] > 0 for e in native):
            towers = [{"time": e["time"], "npc_id": e["npcId"], "team": "RADIANT" if e["isRadiant"] else "DIRE"} for e in native]
    for row in raw["players"]:
        native_slot = row["player_slot" if provider == "opendota" else "playerSlot"]
        slot = native_slot if native_slot < 128 else native_slot - 123
        events: dict[str, Any] = {}
        paths: dict[str, str] = {}
        if available:
            stats = row if provider == "opendota" else row.get("stats")
            stats = stats if isinstance(stats, dict) else {}
            prefix = f"players.{native_slot}." + ("" if provider == "opendota" else "stats.")
            for key, native_key in (("kills", "kills_log" if provider == "opendota" else "killEvents"), ("assists", "assists_log" if provider == "opendota" else "assistEvents"), ("ward_destructions", "wardDestruction")):
                # OpenDota's ward removal logs do not identify the credited destroyer.
                if provider == "opendota" and key != "kills":
                    continue
                stream = _stream(stats.get(native_key), duration)
                events[key] = None if stream is None else [{"time": e["time"]} for e in stream]
                paths[key] = prefix + native_key
            death_key, dead_key = ("deaths_log", "time_dead") if provider == "opendota" else ("deathEvents", "timeDead")
            deaths = _stream(stats.get(death_key), duration)
            complete = deaths is not None and type(row.get("deaths")) is int and len(deaths) == row["deaths"] and all(type(e.get(dead_key)) is int and e[dead_key] >= 0 for e in deaths)
            events["dead_intervals_complete"] = complete
            events["dead_intervals"] = [{"start": e["time"], "end": e["time"] + e[dead_key]} for e in deaths] if complete and deaths is not None else None
            paths["dead_intervals"] = prefix + death_key
            if provider == "stratz":
                levels = stats.get("level")
                events["level_up_times"] = list(levels) if isinstance(levels, list) else None
                paths["level_up_times"] = prefix + "level"
                wards = _stream(stats.get("wards"), duration)
                events["wards"] = [{"time": e["time"], "type": "OBSERVER" if e["type"] == 0 else "SENTRY"} for e in wards] if wards is not None and all(type(e.get("type")) is int and e["type"] in (0, 1) for e in wards) else None
                paths["wards"] = prefix + "wards"
                report = stats.get("towerDamageReport")
                events["tower_damage"] = [{"npc_id": e.get("npcId"), "damage": e.get("damage")} for e in report] if isinstance(report, list) and all(isinstance(e, dict) for e in report) else None
                paths["tower_damage"] = prefix + "towerDamageReport"
            else:
                observers, sentries = _stream(row.get("obs_log"), duration), _stream(row.get("sen_log"), duration)
                events["wards"] = None if observers is None or sentries is None else [{"time": e["time"], "type": kind} for stream, kind in ((observers, "OBSERVER"), (sentries, "SENTRY")) for e in stream]
                paths["wards"] = prefix + "{obs_log,sen_log}"
        players.append({"player_slot": slot, "events": events, "match_events": {"tower_deaths": towers}, "source_paths": paths})
    return {"version": EVENT_VERSION, "players": sorted(players, key=lambda p: p["player_slot"]), "source_paths": {"tower_deaths": "towerDeaths"} if provider == "stratz" else {}}
