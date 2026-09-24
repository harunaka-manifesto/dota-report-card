"""Tracker V1 measurements from canonical facts; progression eligibility is separate."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Measurement:
    metric_id: str
    raw_value: int | float | None
    comparison_value: float | None
    numerator: int | float | None = None
    denominator: int | float | None = None
    reason: str | None = None


SUMMARY_METRICS = frozenset({
    "carry.hero_damage_share.v1", "carry.tower_damage_share.v1", "mid.tower_damage_share.v1",
    "offlane.fight_presence.v1", "support.fight_presence.v1", "support.healing.v1",
})
CHECKPOINT_METRICS = frozenset({
    "carry.last_hits_at_10.v1", "carry.cs_10_to_20.v1", "carry.net_worth_at_20.v1",
    "mid.lane_net_worth_advantage_at_10.v1", "mid.net_worth_at_20.v1",
    "offlane.lane_net_worth_advantage_at_10.v1", "offlane.net_worth_at_10.v1", "support.camps_stacked.v1",
})


EVENT_METRICS = frozenset({
    "carry.dead_time.v1", "mid.level_6_time.v1", "mid.early_fight_presence.v1",
    "offlane.objective_involvement.v1", "support.observer_wards_placed.v1", "support.vision_denial.v1",
})
METRICS = SUMMARY_METRICS | CHECKPOINT_METRICS | EVENT_METRICS
LOWER_IS_BETTER = frozenset({"carry.dead_time.v1", "mid.level_6_time.v1"})


def metric_ids(role: str) -> tuple[str, ...]:
    if role not in {"CARRY", "MID", "OFFLANE", "SUPPORT"}:
        raise ValueError("Invalid progression role")
    return tuple(sorted(metric for metric in METRICS if metric.startswith(role.lower() + ".")))


class MissingMetricEvidence(ValueError):
    pass


def _count(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise MissingMetricEvidence("MISSING_OR_MALFORMED_INPUT")
    return value


def _point(player: dict[str, Any], field: str, second: int, duration: int) -> int:
    if duration < second:
        raise MissingMetricEvidence("MATCH_ENDED_BEFORE_CHECKPOINT")
    checkpoints = player.get("checkpoints")
    series = checkpoints.get(field) if isinstance(checkpoints, dict) else None
    if not isinstance(series, dict) or str(second) not in series:
        raise MissingMetricEvidence("CHECKPOINT_UNAVAILABLE")
    if field in {"last_hits", "camps_stacked"}:
        try:
            entries = sorted((int(time), value) for time, value in series.items())
        except (TypeError, ValueError):
            raise MissingMetricEvidence("MALFORMED_TRAJECTORY") from None
        previous = 0
        for time, value in entries:
            if time < 0 or time > duration:
                continue
            current = _count(value)
            if current < previous:
                raise MissingMetricEvidence("NON_MONOTONIC_TRAJECTORY")
            previous = current
    return _count(series[str(second)])


def measure(metric_id: str, *, players: list[dict[str, Any]], player_slot: int, duration_seconds: int,
            replay_ready: bool, positions: dict[int, int | None] | None = None) -> Measurement:
    """Rows contain canonical `summary` and `checkpoints` from derived features.

    Caller selects the applicable role's metric IDs and handles eligibility,
    provenance and dependency quarantine. This function performs no provider I/O.
    Canonical events must be explicitly present and complete; unknown IDs are rejected.
    """
    if metric_id not in METRICS:
        raise ValueError("Unsupported metric calculator")
    try:
        if not isinstance(players, list) or len(players) != 10 or type(player_slot) is not int or player_slot not in range(10):
            raise MissingMetricEvidence("INVALID_ROSTER")
        roster = {}
        for row in players:
            if not isinstance(row, dict) or not isinstance(row.get("summary"), dict):
                raise MissingMetricEvidence("INVALID_ROSTER")
            summary = row["summary"]
            if not isinstance(summary.get("values"), dict):
                raise MissingMetricEvidence("MISSING_OR_MALFORMED_INPUT")
            slot = summary.get("player_slot")
            if type(slot) is not int or slot not in range(10) or slot in roster or summary.get("team") != ("RADIANT" if slot < 5 else "DIRE"):
                raise MissingMetricEvidence("INVALID_ROSTER")
            roster[slot] = row
        duration = _count(duration_seconds)
        player = roster[player_slot]
        team = [roster[i] for i in (range(5) if player_slot < 5 else range(5, 10))]
        values = player["summary"].get("values", {})
        raw: int | float
        numerator: int | float | None = None
        denominator: int | float | None = None
        if metric_id in SUMMARY_METRICS:
            if "damage_share" in metric_id:
                field = "hero_damage" if "hero_damage" in metric_id else "tower_damage"
                raw = numerator = _count(values.get(field))
                denominator = sum(_count(p["summary"].get("values", {}).get(field)) for p in team)
            elif "fight_presence" in metric_id:
                for p in roster.values():
                    _count(p["summary"]["values"].get("kills"))
                    _count(p["summary"]["values"].get("assists"))
                numerator = _count(values.get("kills")) + _count(values.get("assists"))
                denominator = sum(_count(p["summary"].get("values", {}).get("kills")) for p in team)
                if numerator > denominator:
                    raise MissingMetricEvidence("CREDIT_EXCEEDS_TEAM_KILLS")
                raw = numerator / denominator if denominator else 0
            else:
                raw = numerator = _count(values.get("hero_healing"))
                denominator = duration
            if denominator == 0:
                raise MissingMetricEvidence("ZERO_DENOMINATOR")
            comparison = numerator / denominator * (600 if metric_id == "support.healing.v1" else 1)
        elif metric_id in EVENT_METRICS:
            if not replay_ready:
                raise MissingMetricEvidence("REPLAY_UNAVAILABLE")
            raw, comparison, numerator, denominator = _events(metric_id, player, team, duration)
        else:
            if not replay_ready:
                raise MissingMetricEvidence("REPLAY_UNAVAILABLE")
            if "lane_net_worth_advantage" in metric_id:
                if positions is not None and not isinstance(positions, dict):
                    raise MissingMetricEvidence("OPPOSING_POSITION_NOT_UNIQUE")
                enemy_position = 2 if metric_id.startswith("mid.") else 1
                enemies = [i for i in (range(5, 10) if player_slot < 5 else range(5)) if positions is not None and type(positions.get(i)) is int and positions.get(i) == enemy_position]
                if len(enemies) != 1:
                    raise MissingMetricEvidence("OPPOSING_POSITION_NOT_UNIQUE")
                raw = _point(player, "net_worth", 600, duration) - _point(roster[enemies[0]], "net_worth", 600, duration)
            elif "cs_10_to_20" in metric_id:
                raw = _point(player, "last_hits", 1200, duration) - _point(player, "last_hits", 600, duration)
            else:
                field = "camps_stacked" if "camps_stacked" in metric_id else "last_hits" if "last_hits" in metric_id else "net_worth"
                second = 1200 if "at_20" in metric_id or field == "camps_stacked" else 600
                raw = _point(player, field, second, duration)
            comparison = float(raw)
        if not math.isfinite(raw) or not math.isfinite(comparison):
            raise MissingMetricEvidence("NON_FINITE_MEASUREMENT")
        return Measurement(metric_id, raw, comparison, numerator, denominator)
    except OverflowError:
        return Measurement(metric_id, None, None, reason="NON_FINITE_MEASUREMENT")
    except MissingMetricEvidence as exc:
        return Measurement(metric_id, None, None, reason=str(exc))


def _event_list(value: Any, duration: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(e, dict) or type(e.get("time")) is not int or e["time"] > duration for e in value):
        raise MissingMetricEvidence("MISSING_OR_MALFORMED_EVENTS")
    return value


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _events(metric: str, player: dict[str, Any], team: list[dict[str, Any]], duration: int) -> tuple[int | float, float, int | float | None, int | float | None]:
    events = player.get("events")
    if not isinstance(events, dict):
        raise MissingMetricEvidence("MISSING_OR_MALFORMED_EVENTS")
    if metric == "mid.level_6_time.v1":
        levels = events.get("level_up_times")
        if not isinstance(levels, list) or len(levels) < 6 or any(type(t) is not int or t > duration for t in levels) or any(a > b for a, b in zip(levels, levels[1:], strict=False)):
            raise MissingMetricEvidence("MISSING_OR_MALFORMED_LEVEL_TIMES")
        if levels[5] < 0:
            raise MissingMetricEvidence("MISSING_OR_MALFORMED_LEVEL_TIMES")
        return levels[5], float(levels[5]), None, None
    if metric == "carry.dead_time.v1":
        intervals = events.get("dead_intervals")
        if events.get("dead_intervals_complete") is not True or not isinstance(intervals, list) or len(intervals) != _count(player["summary"]["values"].get("deaths")):
            raise MissingMetricEvidence("INCOMPLETE_DEAD_INTERVALS")
        total, previous = 0, 0
        for interval in intervals:
            if not isinstance(interval, dict):
                raise MissingMetricEvidence("MALFORMED_DEAD_INTERVALS")
            start, end = _count(interval.get("start")), _count(interval.get("end"))
            if start < previous or end < start or end > duration:
                raise MissingMetricEvidence("MALFORMED_DEAD_INTERVALS")
            total += end - start
            previous = end
        if duration == 0:
            raise MissingMetricEvidence("ZERO_DENOMINATOR")
        return total, total / duration, total, duration
    if metric.startswith("support."):
        key = "wards" if metric == "support.observer_wards_placed.v1" else "ward_destructions"
        stream = _event_list(events.get(key), duration)
        if key == "wards" and any(not isinstance(e.get("type"), str) or e["type"] not in {"OBSERVER", "SENTRY"} for e in stream):
            raise MissingMetricEvidence("MALFORMED_WARD_TYPE")
        count = sum(e["type"] == "OBSERVER" for e in stream) if key == "wards" else len(stream)
        if duration == 0:
            raise MissingMetricEvidence("ZERO_DENOMINATOR")
        return count, count * 600 / duration, count, duration
    kills = _event_list(events.get("kills"), duration)
    assists = _event_list(events.get("assists"), duration)
    if metric == "mid.early_fight_presence.v1":
        # Event rows, not unique seconds: multiple valid kills can occur together.
        denominator = sum(sum(0 <= e["time"] <= 900 for e in _event_list(_mapping(p.get("events")).get("kills"), duration)) for p in team)
        numerator = sum(0 <= e["time"] <= 900 for e in kills + assists)
        if numerator > denominator:
            raise MissingMetricEvidence("CREDIT_EXCEEDS_TEAM_KILLS")
        if denominator == 0:
            raise MissingMetricEvidence("ZERO_DENOMINATOR")
        return numerator / denominator, numerator / denominator, numerator, denominator
    towers = _event_list(_mapping(player.get("match_events")).get("tower_deaths"), duration)
    if any(type(t.get("npc_id")) is not int or t["npc_id"] <= 0 or not isinstance(t.get("team"), str) or t["team"] not in {"RADIANT", "DIRE"} for t in towers):
        raise MissingMetricEvidence("MALFORMED_TOWER_EVENTS")
    enemy = {(t["time"], t["npc_id"]) for t in towers if t["team"] != player["summary"]["team"]}
    report = events.get("tower_damage")
    if not isinstance(report, list) or any(not isinstance(r, dict) or type(r.get("npc_id")) is not int or r["npc_id"] <= 0 for r in report):
        raise MissingMetricEvidence("MISSING_OR_MALFORMED_TOWER_DAMAGE")
    damaged = {r["npc_id"] for r in report if _count(r.get("damage")) > 0}
    credited = sum(npc in damaged or any(time - 60 <= e["time"] <= time for e in kills + assists) for time, npc in enemy)
    if not enemy:
        raise MissingMetricEvidence("ZERO_DENOMINATOR")
    return credited / len(enemy), credited / len(enemy), credited, len(enemy)
