"""Exact replay checkpoints; source arrays are not interchangeable by name.

Raw snapshot IDs belong on the persisted feature record. The projection carries
field paths and translation version so each point can be traced to that input.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .normalization import (
    InvalidEvidence,
    Provider,
    _optional_int,
    opendota_summary,
    replay_available,
    stratz_summary,
)

REPLAY_VERSION = "replay-checkpoints-1"


def _points(times: Any, values: Any, duration: int) -> dict[str, int | None] | None:
    if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
        return None
    if any(type(t) is not int for t in times) or any(a >= b for a, b in zip(times, times[1:], strict=False)):
        return None
    return {str(t): _optional_int(v) for t, v in zip(times, values, strict=True) if 0 <= t <= duration}


def replay_checkpoints(raw: Mapping[str, Any], provider: Provider) -> dict[str, Any]:
    """Translate only established series semantics, without interpolation.

    Missing replay produces absent series, never summary-derived substitutes.
    A missing delta invalidates every later cumulative last-hit point.
    """
    if provider not in {"opendota", "stratz"}:
        raise InvalidEvidence("Unsupported provider")
    summary = opendota_summary(raw) if provider == "opendota" else stratz_summary(raw)
    duration = summary["duration_seconds"]
    available = replay_available(raw, provider)
    players = []
    for row in raw["players"]:
        native_slot = row["player_slot" if provider == "opendota" else "playerSlot"]
        slot = native_slot if native_slot < 128 else native_slot - 123
        series: dict[str, Any] = {}
        paths = {}
        for field, od, sz in (
            ("net_worth", "networth_t", "networthPerMinute"),
            ("last_hits", "lh_t", "lastHitsPerMinute"),
            ("camps_stacked", "camps_stacked_t", "campStack"),
        ):
            paths[field] = f"players.{native_slot}.{od if provider == 'opendota' else 'stats.' + sz}"
            series[field] = None
            if not available:
                continue
            if provider == "opendota":
                series[field] = _points(row.get("times"), row.get(od), duration)
                continue
            stats = row.get("stats")
            values = stats.get(sz) if isinstance(stats, Mapping) else None
            if not isinstance(values, list):
                continue
            if field == "last_hits":
                total: int | None = 0
                cumulative = []
                for delta in values:
                    valid = _optional_int(delta)
                    total = total + valid if total is not None and valid is not None else None
                    cumulative.append(total)
                values = cumulative
            # Net worth index t is t:00. Stacks are cumulative at minute t+1;
            # last hits are deltas over [t:00, (t+1):00), per the normative annex.
            offset = 0 if field == "net_worth" else 1
            series[field] = _points([(i + offset) * 60 for i in range(len(values))], values, duration)
        players.append({"player_slot": slot, "series": series, "source_paths": paths})
    return {
        "version": REPLAY_VERSION, "match_id": summary["match_id"],
        "duration_seconds": duration, "players": sorted(players, key=lambda p: p["player_slot"]),
    }


def quarantine_checkpoint_conflicts(primary: Mapping[str, Any], secondary: Mapping[str, Any]) -> dict[str, Any]:
    """Return primary points with exact known disagreements withheld.

    Secondary evidence never fills primary gaps. Inputs remain immutable. A
    caller persists these conflicts beside both source snapshot references.
    """
    if primary.get("match_id") != secondary.get("match_id") or primary.get("version") != secondary.get("version") or primary.get("duration_seconds") != secondary.get("duration_seconds"):
        raise InvalidEvidence("Cannot reconcile different matches, durations or translations")
    for source in (primary, secondary):
        roster = source.get("players")
        if not isinstance(roster, list) or len(roster) != 10 or any(
            not isinstance(p, Mapping) or type(p.get("player_slot")) is not int for p in roster
        ) or {p["player_slot"] for p in roster} != set(range(10)):
            raise InvalidEvidence("Checkpoint comparison requires a canonical roster")
    by_slot = {p["player_slot"]: p for p in secondary["players"]}
    conflicts = []
    players = []
    for player in primary["players"]:
        series = {}
        other = by_slot[player["player_slot"]]
        for name, points in player["series"].items():
            series[name] = None if points is None else dict(points)
            other_points = other["series"].get(name)
            if points is None or other_points is None:
                continue
            for time, value in points.items():
                alternate = other_points.get(time)
                if value is not None and alternate is not None and value != alternate:
                    quarantined = series[name]
                    assert quarantined is not None
                    quarantined[time] = None
                    conflicts.append(f"players.{player['player_slot']}.series.{name}.{time}")
        players.append({**player, "series": series})
    return {**primary, "players": players, "conflicts": sorted(conflicts)}
