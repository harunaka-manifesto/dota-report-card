"""Fail-closed role metric contracts for the progression product.

The functions consume the normalized STRATZ row shape. They deliberately keep
scorecard measurement separate from progression eligibility: Turbo can have a
measured scorecard, but it never enters a role reference window.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import Any

MetricRow = Mapping[str, Any]

SUPPORT_HEALING = "support.healing.v1"
SUPPORT_FIGHT_PRESENCE = "support.fight_presence.v1"
SUPPORT_CAMPS_STACKED = "support.camps_stacked.v1"
SUPPORT_CONTROL = "support.control.v1"
MID_EARLY_FIGHT_PRESENCE = "mid.early_fight_presence.v1"
OFFLANE_OBJECTIVE_INVOLVEMENT = "offlane.objective_involvement.v1"

SUPPORTED_METRICS = frozenset(
    {
        SUPPORT_HEALING,
        SUPPORT_FIGHT_PRESENCE,
        SUPPORT_CAMPS_STACKED,
        MID_EARLY_FIGHT_PRESENCE,
        OFFLANE_OBJECTIVE_INVOLVEMENT,
    }
)

ALL_PICK_MODES = frozenset({"ALL_PICK", "ALL_PICK_RANKED", "ALL_PICK_UNRANKED"})
ALL_PICK_LOBBIES = frozenset({"RANKED", "UNRANKED"})
ROLE_BY_POSITION = {
    "POSITION_1": "carry",
    "POSITION_2": "mid",
    "POSITION_3": "offlane",
    "POSITION_4": "support",
    "POSITION_5": "support",
}
SUPPORT_ROLES = frozenset({"SUPPORT", "HARD_SUPPORT", "LIGHT_SUPPORT"})
REFERENCE_WINDOW_SIZE = 20
MINIMUM_MEASURED_REFERENCE_MATCHES = 5
EARLY_FIGHT_CUTOFF_SECONDS = 15 * 60
OBJECTIVE_PROXIMITY_WINDOW_SECONDS = 60


@dataclass(frozen=True, slots=True)
class MetricMeasurement:
    """One metric observation, including why it is unavailable when needed."""

    metric_key: str
    version: str
    role: str
    status: str
    raw_value: int | float | None
    normalized_value: float | None
    numerator: int | float | None = None
    denominator: int | float | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_key: str
    display_name: str
    role: str
    higher_is_better: bool
    supported: bool
    measure: Callable[[MetricRow], MetricMeasurement] | None = None
    unsupported_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProgressionComparison:
    """A current observation and its bounded own-role reference comparison."""

    measurement: MetricMeasurement
    status: str
    eligible_for_progression: bool
    baseline: float | None
    delta: float | None
    personal_best: bool | None
    reference_match_count: int
    measured_reference_count: int
    reason: str | None = None


def role_for_row(row: MetricRow) -> str | None:
    """Return the product role without inferring a missing lane position."""

    self_row = _mapping(row.get("self"))
    if self_row is None:
        return None
    position = self_row.get("position_native")
    if isinstance(position, str) and position in ROLE_BY_POSITION:
        return ROLE_BY_POSITION[position]
    native_role = self_row.get("role_native")
    if isinstance(native_role, str) and native_role in SUPPORT_ROLES:
        return "support"
    return None


def is_progression_eligible(row: MetricRow) -> bool:
    """Apply the product's narrow All Pick and finished-match gate."""

    duration = _integer(row.get("duration_seconds"), minimum=300)
    match_id = _integer(row.get("match_id"), minimum=1)
    started_at = _integer(row.get("started_at"), minimum=0)
    self_row = _mapping(row.get("self"))
    return bool(
        row.get("game_mode_native") in ALL_PICK_MODES
        and row.get("lobby_type_native") in ALL_PICK_LOBBIES
        and duration is not None
        and match_id is not None
        and started_at is not None
        and self_row is not None
        and self_row.get("leaver_status_native") == "NONE"
        and role_for_row(row) is not None
    )


def previous_role_matches(
    rows: Iterable[MetricRow], current_row: MetricRow, *, role: str, limit: int = REFERENCE_WINDOW_SIZE
) -> tuple[MetricRow, ...]:
    """Return the previous bounded eligible matches in one product role."""

    if limit <= 0:
        return ()
    current_match_id = _integer(current_row.get("match_id"), minimum=1)
    current_started_at = _integer(current_row.get("started_at"), minimum=0)
    if current_match_id is None or current_started_at is None:
        return ()
    candidates: list[MetricRow] = []
    for row in rows:
        if row is current_row:
            continue
        if not is_progression_eligible(row) or role_for_row(row) != role:
            continue
        match_id = _integer(row.get("match_id"), minimum=1)
        started_at = _integer(row.get("started_at"))
        if match_id is None or started_at is None:
            continue
        if match_id == current_match_id:
            continue
        if (started_at, match_id) >= (current_started_at, current_match_id):
            continue
        candidates.append(row)
    candidates.sort(
        key=lambda row: (_integer(row.get("started_at"), minimum=0) or 0, row["match_id"]),
        reverse=True,
    )
    return tuple(candidates[:limit])


def measure_metric(metric_key: str, row: MetricRow) -> MetricMeasurement:
    """Measure a registered metric, returning an explicit unsupported result."""

    try:
        spec = ROLE_METRIC_SPECS[metric_key]
    except KeyError as exc:
        raise KeyError(f"Unknown progression metric: {metric_key}") from exc
    if not spec.supported or spec.measure is None:
        return _unavailable(
            spec.metric_key,
            spec.role,
            spec.unsupported_reason or "unsupported_metric",
            status="unsupported",
        )
    return spec.measure(row)


def compare_progression(
    metric_key: str, current_row: MetricRow, rows: Iterable[MetricRow]
) -> ProgressionComparison:
    """Compare a current scorecard observation to up to 20 prior role matches."""

    spec = ROLE_METRIC_SPECS[metric_key]
    measurement = measure_metric(metric_key, current_row)
    if measurement.status != "measured":
        return ProgressionComparison(
            measurement=measurement,
            status=measurement.status,
            eligible_for_progression=False,
            baseline=None,
            delta=None,
            personal_best=None,
            reference_match_count=0,
            measured_reference_count=0,
            reason=measurement.reason,
        )
    if not is_progression_eligible(current_row):
        return ProgressionComparison(
            measurement=measurement,
            status="ineligible",
            eligible_for_progression=False,
            baseline=None,
            delta=None,
            personal_best=None,
            reference_match_count=0,
            measured_reference_count=0,
            reason="ineligible_progression_context",
        )
    if role_for_row(current_row) != spec.role:
        return ProgressionComparison(
            measurement=measurement,
            status="ineligible",
            eligible_for_progression=False,
            baseline=None,
            delta=None,
            personal_best=None,
            reference_match_count=0,
            measured_reference_count=0,
            reason="role_mismatch",
        )

    reference = previous_role_matches(rows, current_row, role=spec.role)
    measured = [measure_metric(metric_key, row) for row in reference]
    values: list[float] = []
    for item in measured:
        if item.status == "measured" and item.normalized_value is not None:
            values.append(item.normalized_value)
    if len(values) < MINIMUM_MEASURED_REFERENCE_MATCHES:
        return ProgressionComparison(
            measurement=measurement,
            status="insufficient_history",
            eligible_for_progression=True,
            baseline=None,
            delta=None,
            personal_best=None,
            reference_match_count=len(reference),
            measured_reference_count=len(values),
            reason="fewer_than_5_measured_reference_matches",
        )

    current_value = measurement.normalized_value
    assert current_value is not None
    baseline = fmean(values)
    delta = current_value - baseline
    best = current_value > max(values) if spec.higher_is_better else current_value < min(values)
    return ProgressionComparison(
        measurement=measurement,
        status="measured",
        eligible_for_progression=True,
        baseline=baseline,
        delta=delta,
        personal_best=best,
        reference_match_count=len(reference),
        measured_reference_count=len(values),
    )


def support_healing(row: MetricRow) -> MetricMeasurement:
    """Measure player ``heroHealing`` and normalize it per ten minutes."""

    if role_for_row(row) != "support":
        return _unavailable(SUPPORT_HEALING, "support", "role_mismatch")
    self_row = _mapping(row.get("self"))
    healing = _integer(self_row.get("hero_healing") if self_row else None, minimum=0)
    if healing is None:
        return _unavailable(SUPPORT_HEALING, "support", "missing_or_malformed_hero_healing")
    duration = _integer(row.get("duration_seconds"), minimum=1)
    if duration is None:
        return _unavailable(SUPPORT_HEALING, "support", "missing_or_malformed_duration_seconds")
    normalized = healing / (duration / 60) * 10
    return _measured(SUPPORT_HEALING, "support", healing, normalized, healing, duration)


def support_fight_presence(row: MetricRow) -> MetricMeasurement:
    """Measure K+A over credited kills on the player's five-person team."""

    if role_for_row(row) != "support":
        return _unavailable(SUPPORT_FIGHT_PRESENCE, "support", "role_mismatch")
    self_row = _mapping(row.get("self"))
    if self_row is None:
        return _unavailable(SUPPORT_FIGHT_PRESENCE, "support", "missing_self_row")
    players, reason = _scoreboard_players(row, require_kill_events=False)
    if players is None:
        return _unavailable(SUPPORT_FIGHT_PRESENCE, "support", reason or "malformed_all_players")
    player_slot = _integer(self_row.get("player_slot"), minimum=0)
    is_radiant = self_row.get("is_radiant")
    if player_slot is None or not isinstance(is_radiant, bool):
        return _unavailable(SUPPORT_FIGHT_PRESENCE, "support", "missing_or_malformed_player_identity")
    team = [player for player in players if player["is_radiant"] is is_radiant]
    player = next((item for item in team if item["player_slot"] == player_slot), None)
    if len(team) != 5 or player is None:
        return _unavailable(SUPPORT_FIGHT_PRESENCE, "support", "missing_all_player_row")
    team_kills = sum(item["kills"] for item in team)
    involvement = player["kills"] + player["assists"]
    if team_kills == 0:
        return _unavailable(
            SUPPORT_FIGHT_PRESENCE,
            "support",
            "zero_credited_team_kills",
            numerator=involvement,
            denominator=0,
        )
    if involvement > team_kills:
        return _unavailable(
            SUPPORT_FIGHT_PRESENCE,
            "support",
            "involvement_exceeds_credited_team_kills",
            numerator=involvement,
            denominator=team_kills,
        )
    value = involvement / team_kills
    return _measured(
        SUPPORT_FIGHT_PRESENCE,
        "support",
        value,
        value,
        involvement,
        team_kills,
    )


def support_camps_stacked(row: MetricRow) -> MetricMeasurement:
    """Measure the final value of the verified cumulative ``campStack`` series."""

    if role_for_row(row) != "support":
        return _unavailable(SUPPORT_CAMPS_STACKED, "support", "role_mismatch")
    self_row = _mapping(row.get("self"))
    trajectories = _mapping(self_row.get("trajectories") if self_row else None)
    series = trajectories.get("camp_stack") if trajectories else None
    series_values = _sequence(series)
    if series_values is None or len(series_values) == 0:
        return _unavailable(SUPPORT_CAMPS_STACKED, "support", "missing_or_empty_camp_stack")
    values: list[int] = []
    previous = 0
    for value in series_values:
        parsed = _integer(value, minimum=0)
        if parsed is None:
            return _unavailable(SUPPORT_CAMPS_STACKED, "support", "malformed_camp_stack")
        if parsed < previous:
            return _unavailable(SUPPORT_CAMPS_STACKED, "support", "non_monotonic_camp_stack")
        values.append(parsed)
        previous = parsed
    final_value = values[-1]
    return _measured(SUPPORT_CAMPS_STACKED, "support", final_value, float(final_value), final_value, None)


def mid_early_fight_presence(row: MetricRow) -> MetricMeasurement:
    """Measure credited kill participation from 0:00 through exactly 15:00."""

    if role_for_row(row) != "mid":
        return _unavailable(MID_EARLY_FIGHT_PRESENCE, "mid", "role_mismatch")
    self_row = _mapping(row.get("self"))
    if self_row is None:
        return _unavailable(MID_EARLY_FIGHT_PRESENCE, "mid", "missing_self_row")
    players, reason = _scoreboard_players(row, require_kill_events=True)
    if players is None:
        return _unavailable(MID_EARLY_FIGHT_PRESENCE, "mid", reason or "malformed_all_players")
    player_slot = _integer(self_row.get("player_slot"), minimum=0)
    is_radiant = self_row.get("is_radiant")
    if player_slot is None or not isinstance(is_radiant, bool):
        return _unavailable(MID_EARLY_FIGHT_PRESENCE, "mid", "missing_or_malformed_player_identity")
    team = [item for item in players if item["is_radiant"] is is_radiant]
    player = next((item for item in team if item["player_slot"] == player_slot), None)
    if len(team) != 5 or player is None:
        return _unavailable(MID_EARLY_FIGHT_PRESENCE, "mid", "missing_all_player_row")
    denominator = sum(
        _events_through(item["kill_events"], EARLY_FIGHT_CUTOFF_SECONDS) for item in team
    )
    own_kills = [
        time
        for time in player["kill_events"]
        if 0 <= time <= EARLY_FIGHT_CUTOFF_SECONDS
    ]
    event_map = _mapping(self_row.get("events"))
    own_assists = _timed_events(
        event_map.get("assist_events") if event_map else None,
        cutoff=EARLY_FIGHT_CUTOFF_SECONDS,
    )
    if own_assists is None:
        return _unavailable(MID_EARLY_FIGHT_PRESENCE, "mid", "missing_or_malformed_assist_events")
    numerator = _distinct_credit_count(own_kills, own_assists)
    if denominator == 0:
        return _unavailable(
            MID_EARLY_FIGHT_PRESENCE,
            "mid",
            "zero_credited_team_kills_through_15m",
            numerator=numerator,
            denominator=0,
        )
    if numerator > denominator:
        return _unavailable(
            MID_EARLY_FIGHT_PRESENCE,
            "mid",
            "involvement_exceeds_credited_team_kills",
            numerator=numerator,
            denominator=denominator,
        )
    value = numerator / denominator
    return _measured(MID_EARLY_FIGHT_PRESENCE, "mid", value, value, numerator, denominator)


def offlane_objective_involvement(
    row: MetricRow, *, proximity_window_seconds: int = OBJECTIVE_PROXIMITY_WINDOW_SECONDS
) -> MetricMeasurement:
    """Measure enemy-tower involvement with a versioned 60-second proximity rule."""

    if role_for_row(row) != "offlane":
        return _unavailable(OFFLANE_OBJECTIVE_INVOLVEMENT, "offlane", "role_mismatch")
    self_row = _mapping(row.get("self"))
    if self_row is None:
        return _unavailable(OFFLANE_OBJECTIVE_INVOLVEMENT, "offlane", "missing_self_row")
    is_radiant = self_row.get("is_radiant")
    if not isinstance(is_radiant, bool):
        return _unavailable(OFFLANE_OBJECTIVE_INVOLVEMENT, "offlane", "missing_or_malformed_player_side")
    towers, reason = _enemy_towers(row.get("tower_deaths"), is_radiant)
    if towers is None:
        return _unavailable(OFFLANE_OBJECTIVE_INVOLVEMENT, "offlane", reason or "malformed_tower_deaths")
    if not towers:
        return _unavailable(
            OFFLANE_OBJECTIVE_INVOLVEMENT,
            "offlane",
            "zero_enemy_towers_destroyed",
            numerator=0,
            denominator=0,
        )
    report = self_row.get("tower_damage_report")
    if report is None:
        return _unavailable(OFFLANE_OBJECTIVE_INVOLVEMENT, "offlane", "missing_tower_damage_report")
    damage_ids, reason = _tower_damage_ids(report)
    if damage_ids is None:
        return _unavailable(
            OFFLANE_OBJECTIVE_INVOLVEMENT,
            "offlane",
            reason or "malformed_tower_damage_report",
        )
    events = _mapping(self_row.get("events"))
    if events is None:
        return _unavailable(OFFLANE_OBJECTIVE_INVOLVEMENT, "offlane", "missing_proximity_events")
    proximity = _timed_events(events.get("kill_events"), cutoff=None)
    assists = _timed_events(events.get("assist_events"), cutoff=None)
    if proximity is None or assists is None:
        return _unavailable(
            OFFLANE_OBJECTIVE_INVOLVEMENT,
            "offlane",
            "missing_or_malformed_proximity_events",
        )
    involvement_times = proximity + assists
    if _integer(proximity_window_seconds, minimum=0) is None:
        return _unavailable(
            OFFLANE_OBJECTIVE_INVOLVEMENT,
            "offlane",
            "malformed_proximity_window_seconds",
        )
    attributed = sum(
        1
        for tower_time, npc_id in towers
        if npc_id in damage_ids
        or any(
            tower_time - proximity_window_seconds <= event_time <= tower_time
            for event_time in involvement_times
        )
    )
    value = attributed / len(towers)
    return _measured(
        OFFLANE_OBJECTIVE_INVOLVEMENT,
        "offlane",
        value,
        value,
        attributed,
        len(towers),
    )


def _scoreboard_players(
    row: MetricRow, *, require_kill_events: bool
) -> tuple[list[dict[str, Any]] | None, str | None]:
    raw_players = row.get("all_players")
    player_rows = _sequence(raw_players)
    if player_rows is None or len(player_rows) != 10:
        return None, "missing_or_malformed_all_players"
    players: list[dict[str, Any]] = []
    slots: set[int] = set()
    sides: list[bool] = []
    for raw in player_rows:
        player = _mapping(raw)
        if player is None:
            return None, "malformed_all_players"
        slot = _integer(player.get("player_slot"), minimum=0)
        is_radiant = player.get("is_radiant")
        kills = _integer(player.get("kills"), minimum=0)
        assists = _integer(player.get("assists"), minimum=0)
        if slot is None or not isinstance(is_radiant, bool) or kills is None or assists is None:
            return None, "malformed_all_players"
        if slot in slots:
            return None, "duplicate_all_player_slot"
        slots.add(slot)
        sides.append(is_radiant)
        parsed: dict[str, Any] = {
            "player_slot": slot,
            "is_radiant": is_radiant,
            "kills": kills,
            "assists": assists,
        }
        if require_kill_events:
            event_source = player.get("kill_events")
            if event_source is None:
                stats = _mapping(player.get("stats"))
                if stats is None or "kill_events" not in stats:
                    return None, "missing_team_kill_events"
                event_source = stats.get("kill_events")
            if event_source is None:
                return None, "missing_team_kill_events"
            event_times = _timed_events(event_source, cutoff=None)
            if event_times is None:
                return None, "malformed_team_kill_events"
            parsed["kill_events"] = event_times
        players.append(parsed)
    if sides.count(True) != 5 or sides.count(False) != 5:
        return None, "malformed_all_players"
    return players, None


def _enemy_towers(
    raw_towers: Any, player_is_radiant: bool
) -> tuple[list[tuple[int, int]] | None, str | None]:
    if _sequence(raw_towers) is None:
        return None, "missing_or_malformed_tower_deaths"
    towers: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for raw in raw_towers:
        tower = _mapping(raw)
        if tower is None:
            return None, "malformed_tower_deaths"
        time = _integer(tower.get("time"))
        is_radiant = tower.get("is_radiant")
        npc_id = _integer(tower.get("npc_id"), minimum=1)
        if time is None or not isinstance(is_radiant, bool) or npc_id is None:
            return None, "malformed_tower_deaths"
        if is_radiant == player_is_radiant:
            continue
        key = (time, npc_id)
        if key not in seen:
            seen.add(key)
            towers.append(key)
    return towers, None


def _tower_damage_ids(raw_report: Any) -> tuple[set[int] | None, str | None]:
    if _sequence(raw_report) is None:
        return None, "malformed_tower_damage_report"
    ids: set[int] = set()
    for raw in raw_report:
        report = _mapping(raw)
        if report is None:
            return None, "malformed_tower_damage_report"
        npc_id = _integer(report.get("npc_id"), minimum=1)
        damage = _integer(report.get("damage"), minimum=0)
        if npc_id is None or damage is None:
            return None, "malformed_tower_damage_report"
        if damage > 0:
            ids.add(npc_id)
    return ids, None


def _timed_events(raw: Any, *, cutoff: int | None) -> list[int] | None:
    if _sequence(raw) is None:
        return None
    times: list[int] = []
    for event in raw:
        mapping = _mapping(event)
        if mapping is None:
            return None
        time = _integer(mapping.get("time"))
        if time is None:
            return None
        if cutoff is None or 0 <= time <= cutoff:
            times.append(time)
    return times


def _events_through(events: list[int], cutoff: int) -> int:
    return sum(0 <= time <= cutoff for time in events)


def _distinct_credit_count(kill_events: list[int], assist_events: list[int]) -> int:
    """Count event rows; kill and assist event types are disjoint credits.

    The production selection carries timestamps only, so timestamps are not
    deduplicated: two kills can occur in the same second. STRATZ supplies the
    two event types as separate credits, and a player cannot be both killer and
    assister for one kill. A future event identity field can tighten this rule
    without silently changing this metric's version.
    """

    return len(kill_events) + len(assist_events)


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _sequence(value: Any) -> Sequence[Any] | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return None


def _integer(value: Any, *, minimum: int | None = None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if minimum is not None and value < minimum:
        return None
    return value


def _measured(
    metric_key: str,
    role: str,
    raw_value: int | float,
    normalized_value: float,
    numerator: int | float | None = None,
    denominator: int | float | None = None,
) -> MetricMeasurement:
    return MetricMeasurement(
        metric_key=metric_key,
        version="v1",
        role=role,
        status="measured",
        raw_value=raw_value,
        normalized_value=normalized_value,
        numerator=numerator,
        denominator=denominator,
    )


def _unavailable(
    metric_key: str,
    role: str,
    reason: str,
    *,
    numerator: int | float | None = None,
    denominator: int | float | None = None,
    status: str = "unavailable",
) -> MetricMeasurement:
    return MetricMeasurement(
        metric_key=metric_key,
        version="v1",
        role=role,
        status=status,
        raw_value=None,
        normalized_value=None,
        numerator=numerator,
        denominator=denominator,
        reason=reason,
    )


ROLE_METRIC_SPECS = {
    SUPPORT_HEALING: MetricSpec(SUPPORT_HEALING, "Healing", "support", True, True, support_healing),
    SUPPORT_FIGHT_PRESENCE: MetricSpec(
        SUPPORT_FIGHT_PRESENCE, "Fight Presence", "support", True, True, support_fight_presence
    ),
    SUPPORT_CAMPS_STACKED: MetricSpec(
        SUPPORT_CAMPS_STACKED, "Camps Stacked", "support", True, True, support_camps_stacked
    ),
    SUPPORT_CONTROL: MetricSpec(
        SUPPORT_CONTROL,
        "Control",
        "support",
        True,
        False,
        unsupported_reason="no direct player-attributed control-duration field; actionReport is counters only",
    ),
    MID_EARLY_FIGHT_PRESENCE: MetricSpec(
        MID_EARLY_FIGHT_PRESENCE,
        "Early Fight Presence",
        "mid",
        True,
        True,
        mid_early_fight_presence,
    ),
    OFFLANE_OBJECTIVE_INVOLVEMENT: MetricSpec(
        OFFLANE_OBJECTIVE_INVOLVEMENT,
        "Objective Involvement",
        "offlane",
        True,
        True,
        offlane_objective_involvement,
    ),
}


__all__ = [
    "ALL_PICK_LOBBIES",
    "ALL_PICK_MODES",
    "EARLY_FIGHT_CUTOFF_SECONDS",
    "MINIMUM_MEASURED_REFERENCE_MATCHES",
    "MetricMeasurement",
    "MetricSpec",
    "OBJECTIVE_PROXIMITY_WINDOW_SECONDS",
    "OFFLANE_OBJECTIVE_INVOLVEMENT",
    "MID_EARLY_FIGHT_PRESENCE",
    "ProgressionComparison",
    "REFERENCE_WINDOW_SIZE",
    "ROLE_METRIC_SPECS",
    "SUPPORTED_METRICS",
    "SUPPORT_CAMPS_STACKED",
    "SUPPORT_CONTROL",
    "SUPPORT_FIGHT_PRESENCE",
    "SUPPORT_HEALING",
    "compare_progression",
    "is_progression_eligible",
    "measure_metric",
    "mid_early_fight_presence",
    "offlane_objective_involvement",
    "previous_role_matches",
    "role_for_row",
    "support_camps_stacked",
    "support_fight_presence",
    "support_healing",
]
