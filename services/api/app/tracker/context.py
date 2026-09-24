"""Pure V1 context adjustment from a versioned, validated population parameter set."""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from statistics import median

from .metrics import LOWER_IS_BETTER, METRICS

ContextClass = str
LaneContext = str
PerformanceState = str

METRIC_CLASS: dict[str, ContextClass] = {
    "carry.last_hits_at_10.v1": "C",
    "carry.cs_10_to_20.v1": "B",
    "carry.net_worth_at_20.v1": "B",
    "carry.dead_time.v1": "D",
    "carry.hero_damage_share.v1": "B",
    "carry.tower_damage_share.v1": "B",
    "mid.lane_net_worth_advantage_at_10.v1": "C*",
    "mid.level_6_time.v1": "C",
    "mid.early_fight_presence.v1": "B",
    "mid.net_worth_at_20.v1": "B",
    "mid.tower_damage_share.v1": "B",
    "offlane.lane_net_worth_advantage_at_10.v1": "C*",
    "offlane.net_worth_at_10.v1": "C",
    "offlane.fight_presence.v1": "A",
    "offlane.objective_involvement.v1": "E",
    "support.fight_presence.v1": "A",
    "support.observer_wards_placed.v1": "A",
    "support.vision_denial.v1": "A",
    "support.camps_stacked.v1": "A",
    "support.healing.v1": "B",
}


@dataclass(frozen=True)
class DraftPlayer:
    hero_id: int | None
    position: int | None
    lane: str | None
    is_radiant: bool


@dataclass(frozen=True)
class HeroLevel:
    value: float
    match_count: int


@dataclass(frozen=True)
class MetricParameters:
    sigma_pop: float
    tau: float
    floor: float
    floor_tolerance: float


@dataclass(frozen=True)
class ParameterSet:
    version: str
    validated: bool
    opponent_coverage: float
    cs_slope_regression_passed: bool
    hero_levels: Mapping[tuple[int, int, str], HeroLevel]
    opponent_effects: Mapping[tuple[int, int], float]
    role_slopes: Mapping[str, float]
    lane_thresholds: Mapping[str, tuple[float, float]]
    metrics: Mapping[str, MetricParameters]


@dataclass(frozen=True)
class ContextInput:
    metric_id: str
    role: str
    mode: str
    hero_id: int | None
    position: int | None
    lane: str | None
    is_radiant: bool | None
    players: tuple[DraftPlayer, ...]
    comparison_value: float | None
    baseline: float | None
    prior_count: int
    prior_hero_levels: tuple[float | None, ...] = ()
    prior_lane_scores: tuple[float | None, ...] = ()


@dataclass(frozen=True)
class ContextResult:
    context_class: ContextClass
    hero_level: float | None
    lane_score: float | None
    delta_hero: float
    delta_lane: float
    adjusted_expectation: float | None
    residual: float | None
    performance_state: PerformanceState
    lane_context: LaneContext
    unavailable_reason: str | None


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _artifact_ready(parameters: ParameterSet | None, metric_id: str) -> bool:
    return bool(
        parameters
        and isinstance(parameters.version, str)
        and parameters.version.strip()
        and parameters.validated
        and _finite(parameters.opponent_coverage)
        and parameters.opponent_coverage >= 0.97
        and parameters.cs_slope_regression_passed
        and metric_id in parameters.metrics
        and all(_finite(v) for v in parameters.role_slopes.values())
        and all(_finite(v) for v in parameters.opponent_effects.values())
    )


def _physical_lane(lane: str | None, radiant: bool) -> str | None:
    if lane == "MID_LANE":
        return "MID"
    if lane == "SAFE_LANE":
        return "BOT" if radiant else "TOP"
    if lane == "OFF_LANE":
        return "TOP" if radiant else "BOT"
    return None


def _lane_score(context: ContextInput, parameters: ParameterSet) -> tuple[float | None, str | None]:
    if context.mode != "STANDARD" or context.role not in {"CARRY", "MID", "OFFLANE"}:
        return None, "OUT_OF_SCOPE"
    if (context.hero_id is None or context.position != {"CARRY": 1, "MID": 2, "OFFLANE": 3}[context.role]
            or context.lane not in {"SAFE_LANE", "MID_LANE", "OFF_LANE"}
            or type(context.is_radiant) is not bool or len(context.players) != 10):
        return None, "INVALID_DRAFT"
    if context.hero_id <= 0:
        return None, "INVALID_DRAFT"
    lanes: list[tuple[DraftPlayer, str]] = []
    for player in context.players:
        if (player.hero_id is None or player.position not in range(1, 6)
                or player.lane not in {"SAFE_LANE", "MID_LANE", "OFF_LANE"}
                or type(player.is_radiant) is not bool):
            return None, "INVALID_DRAFT"
        if player.hero_id <= 0:
            return None, "INVALID_DRAFT"
        physical = _physical_lane(player.lane, player.is_radiant)
        if physical is None:
            return None, "INVALID_DRAFT"
        lanes.append((player, physical))
    for radiant in (True, False):
        if {player.position for player, _ in lanes if player.is_radiant == radiant} != {1, 2, 3, 4, 5}:
            return None, "INVALID_DRAFT"
    if not any(
        player.hero_id == context.hero_id and player.position == context.position
        and player.lane == context.lane and player.is_radiant == context.is_radiant
        for player, _ in lanes
    ):
        return None, "INVALID_DRAFT"
    own_lane = _physical_lane(context.lane, context.is_radiant)
    if context.position is None:
        return None, "INVALID_DRAFT"
    own_count = sum(1 for player, lane in lanes if player.is_radiant == context.is_radiant and lane == own_lane)
    opps = [player for player, lane in lanes if player.is_radiant != context.is_radiant and lane == own_lane]
    if own_count not in (1, 2) or len(opps) != own_count:
        return None, "ASYMMETRIC_OR_UNRESOLVED_LANE"
    effects = []
    for opponent in opps:
        if opponent.hero_id is None:
            return None, "INVALID_DRAFT"
        effect = parameters.opponent_effects.get((context.position, opponent.hero_id))
        if effect is None or not _finite(effect):
            return None, "OPPONENT_PARAMETER_MISSING"
        effects.append(float(effect))
    slope = parameters.role_slopes.get(context.role)
    if slope is None or not _finite(slope):
        return None, "ROLE_SLOPE_MISSING"
    return float(slope) * sum(effects), None


def evaluate(context: ContextInput, parameters: ParameterSet | None) -> ContextResult:
    """Evaluate expectation and draft-only lane context; no provider or runtime model calls."""
    if context.metric_id not in METRICS or context.metric_id not in METRIC_CLASS:
        raise ValueError("Unsupported context metric")
    cls = METRIC_CLASS[context.metric_id]
    if context.mode not in {"STANDARD", "TURBO"} or context.role not in {"CARRY", "MID", "OFFLANE", "SUPPORT"}:
        raise ValueError("Invalid context identity")
    if not context.metric_id.startswith(context.role.lower() + "."):
        raise ValueError("Metric does not belong to progression role")
    if context.prior_count < 0 or context.prior_count > 20:
        raise ValueError("Baseline prior count must be between 0 and 20")
    if len(context.prior_hero_levels) > 20 or len(context.prior_lane_scores) > 20:
        raise ValueError("Context terms must come from the 20-match baseline window")
    if context.comparison_value is not None and not _finite(context.comparison_value):
        raise ValueError("Comparison value must be finite")
    if context.baseline is not None and not _finite(context.baseline):
        raise ValueError("Baseline must be finite")

    empty = ContextResult(cls, None, None, 0.0, 0.0, None, None, "NOT_READY", "UNAVAILABLE", None)
    if not _artifact_ready(parameters, context.metric_id):
        return ContextResult(**{**empty.__dict__, "unavailable_reason": "PARAMETER_SET_UNAVAILABLE"})
    assert parameters is not None
    metric = parameters.metrics[context.metric_id]
    if not (_finite(metric.sigma_pop) and metric.sigma_pop > 0 and _finite(metric.tau) and metric.tau > 0
            and _finite(metric.floor) and _finite(metric.floor_tolerance) and metric.floor_tolerance >= 0):
        return ContextResult(**{**empty.__dict__, "unavailable_reason": "METRIC_PARAMETERS_UNAVAILABLE"})

    hero_level: float | None = None
    lane_score: float | None = None
    delta_h = delta_e = 0.0
    lane_context: LaneContext = "UNAVAILABLE"
    lane_reason: str | None = None
    if context.mode == "STANDARD":
        lane_score, lane_reason = _lane_score(context, parameters)
        if lane_score is not None:
            thresholds = parameters.lane_thresholds.get(context.role)
            if thresholds is None:
                lane_reason = "LANE_THRESHOLDS_UNAVAILABLE"
            else:
                difficult, favourable = thresholds
                if _finite(difficult) and _finite(favourable) and difficult < favourable:
                    lane_context = "DIFFICULT" if lane_score <= difficult else "FAVOURABLE" if lane_score >= favourable else "TYPICAL"
                else:
                    lane_reason = "LANE_THRESHOLDS_UNAVAILABLE"

    if (cls in {"B", "C", "C*"} and context.mode == "STANDARD"
            and context.baseline is not None and context.prior_count >= 5):
        if context.baseline > metric.floor + metric.floor_tolerance:
            if cls == "C*":
                own_lane = _physical_lane(context.lane, bool(context.is_radiant))
                counterpart_position = 2 if context.role == "MID" else 1
                counterparts = [player for player in context.players
                                if player.is_radiant != context.is_radiant
                                and player.position == counterpart_position
                                and own_lane is not None and lane_score is not None
                                and _physical_lane(player.lane, player.is_radiant) == own_lane]
                viewer = parameters.hero_levels.get((int(context.hero_id or 0), int(context.position or 0), context.metric_id))
                paired = (parameters.hero_levels.get((int(counterparts[0].hero_id or 0), counterpart_position, context.metric_id))
                          if len(counterparts) == 1 else None)
                if (viewer and paired and _finite(viewer.value) and _finite(paired.value)
                        and type(viewer.match_count) is int and type(paired.match_count) is int
                        and viewer.match_count >= 300 and paired.match_count >= 300):
                    hero_level = viewer.value - paired.value
            else:
                own = parameters.hero_levels.get((int(context.hero_id or 0), int(context.position or 0), context.metric_id))
                if (own and _finite(own.value) and type(own.match_count) is int
                        and own.match_count >= 300):
                    hero_level = own.value
            if hero_level is not None and len([x for x in context.prior_hero_levels if x is not None and _finite(x)]) >= 3:
                prior_h = [float(x) for x in context.prior_hero_levels if x is not None and _finite(x)]
                delta_h = max(-0.75 * metric.sigma_pop, min(0.75 * metric.sigma_pop, hero_level - median(prior_h)))
            if cls in {"C", "C*"} and lane_score is not None and len([x for x in context.prior_lane_scores if x is not None and _finite(x)]) >= 3:
                prior_e = [float(x) for x in context.prior_lane_scores if x is not None and _finite(x)]
                delta_e = max(-0.6 * metric.sigma_pop, min(0.6 * metric.sigma_pop, lane_score - median(prior_e)))

    expectation = context.baseline
    residual = None
    state: PerformanceState = "NOT_READY"
    reason = lane_reason
    if context.baseline is not None and context.prior_count >= 5:
        expectation = context.baseline + delta_h + delta_e
        if context.comparison_value is not None and cls != "E":
            residual = (expectation - context.comparison_value if context.metric_id in LOWER_IS_BETTER
                        else context.comparison_value - expectation)
            threshold = metric.tau * metric.sigma_pop
            state = "ABOVE" if residual >= threshold else "BELOW" if residual <= -threshold else "IN_LINE"
    elif context.baseline is None:
        reason = reason or "BASELINE_UNAVAILABLE"
    return ContextResult(cls, hero_level, lane_score, delta_h, delta_e, expectation, residual, state, lane_context, reason)
