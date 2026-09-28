from dataclasses import fields

import pytest
from app.tracker.context import (
    METRIC_CLASS,
    ContextInput,
    DraftPlayer,
    HeroLevel,
    MetricParameters,
    ParameterSet,
    evaluate,
)
from app.tracker.metrics import METRICS


def _draft() -> tuple[DraftPlayer, ...]:
    # The viewer is Radiant Carry in a 2v2 bottom lane. Teammate identity is irrelevant.
    return (
        DraftPlayer(1, 1, "SAFE_LANE", True), DraftPlayer(2, 2, "MID_LANE", True),
        DraftPlayer(3, 3, "OFF_LANE", True), DraftPlayer(4, 4, "SAFE_LANE", True),
        DraftPlayer(5, 5, "OFF_LANE", True), DraftPlayer(11, 1, "SAFE_LANE", False),
        DraftPlayer(12, 2, "MID_LANE", False), DraftPlayer(13, 3, "OFF_LANE", False),
        DraftPlayer(14, 4, "SAFE_LANE", False), DraftPlayer(15, 5, "OFF_LANE", False),
    )


def _parameters(*, validated: bool = True, coverage: float = 0.97, lane_model: bool = True) -> ParameterSet:
    metric = "carry.last_hits_at_10.v1"
    return ParameterSet(
        version="test-only-context-v1", validated=validated, opponent_coverage=coverage,
        cs_slope_regression_passed=lane_model,
        hero_levels={(1, 1, metric): HeroLevel(50, 500)},
        opponent_effects={(1, 13): 5.0, (1, 15): 5.0},
        role_slopes={"CARRY": 1.0, "MID": 1.0, "OFFLANE": 1.0},
        lane_thresholds={"CARRY": (-2.0, 2.0), "MID": (-2.0, 2.0), "OFFLANE": (-2.0, 2.0)},
        metrics={metric: MetricParameters(10.0, 0.35, 0.0, 0.0)},
    )


def _input(**changes: object) -> ContextInput:
    values: dict[str, object] = dict(
        metric_id="carry.last_hits_at_10.v1", role="CARRY", mode="STANDARD",
        hero_id=1, position=1, lane="SAFE_LANE", is_radiant=True, players=_draft(),
        comparison_value=120.0, baseline=100.0, prior_count=5,
        prior_hero_levels=(0.0, 10.0, 20.0),
    )
    values.update(changes)
    return ContextInput(**values)  # type: ignore[arg-type]


def test_window_relative_hero_adjustment_is_capped_and_lane_is_display_only() -> None:
    result = evaluate(_input(), _parameters())
    assert result.hero_level == 50.0
    assert result.lane_score == 10.0
    assert result.lane_context == "FAVOURABLE"
    assert result.delta_hero == 7.5
    # No lane or opponent term enters the expectation (context-adjustment-v3).
    assert result.adjusted_expectation == 107.5
    assert result.performance_state == "ABOVE"
    no_badge = evaluate(_input(), _parameters(lane_model=False))
    assert no_badge.lane_context == "UNAVAILABLE"
    assert no_badge.unavailable_reason == "LANE_MODEL_UNAVAILABLE"
    assert no_badge.adjusted_expectation == result.adjusted_expectation
    assert no_badge.performance_state == result.performance_state


def test_metric_matrix_and_higher_is_better_residual() -> None:
    assert set(METRIC_CLASS) == METRICS
    # The named metric rows in the active SSOT sum to 16 (8 B, 2 B*, 5 A, 1 E); classes C, C* and D are retired.
    assert not {"C", "C*", "D"} & set(METRIC_CLASS.values())
    assert sum(context_class == "B*" for context_class in METRIC_CLASS.values()) == 2
    assert sum(context_class == "B" for context_class in METRIC_CLASS.values()) == 8
    assert sum(context_class == "A" for context_class in METRIC_CLASS.values()) == 5
    assert sum(context_class == "E" for context_class in METRIC_CLASS.values()) == 1
    metric = "support.fight_presence.v1"
    params = _parameters()
    params = ParameterSet(**{
        **params.__dict__,
        "metrics": {metric: MetricParameters(10.0, 0.35, 0.0, 0.0)},
    })
    result = evaluate(_input(metric_id=metric, role="SUPPORT", comparison_value=105.0), params)
    assert result.adjusted_expectation == 100.0
    assert result.residual == 5.0
    assert result.performance_state == "ABOVE"
    for retired in ("carry.cs_10_to_20.v1", "carry.dead_time.v1", "mid.level_6_time.v1", "support.healing.v1"):
        with pytest.raises(ValueError, match="Unsupported context metric"):
            evaluate(_input(metric_id=retired), params)


def test_missing_or_unvalidated_artifact_fails_closed() -> None:
    for parameters in (None, _parameters(validated=False)):
        result = evaluate(_input(), parameters)
        assert result.delta_hero == 0
        assert result.lane_context == "UNAVAILABLE"
        assert result.performance_state == "NOT_READY"
        assert result.unavailable_reason == "PARAMETER_SET_UNAVAILABLE"


def test_turbo_floor_and_three_prior_gates_produce_no_adjustment() -> None:
    params = _parameters()
    assert evaluate(_input(mode="TURBO"), params).delta_hero == 0
    at_floor = evaluate(_input(baseline=0.0), params)
    assert at_floor.delta_hero == 0
    building = evaluate(_input(prior_count=4), params)
    assert building.delta_hero == 0
    assert building.performance_state == "NOT_READY"
    assert building.lane_context == "FAVOURABLE"
    too_few_terms = evaluate(_input(prior_hero_levels=(1.0, 2.0)), params)
    assert too_few_terms.delta_hero == 0


def test_metric_matrix_keeps_unadjusted_and_diagnostic_metrics_separate() -> None:
    params = _parameters()
    raw = _input()
    diagnostic = evaluate(_input(metric_id="offlane.objective_involvement.v1", role="OFFLANE"), params)
    unadjusted = evaluate(_input(metric_id="offlane.fight_presence.v1", role="OFFLANE"), params)
    assert diagnostic.context_class == "E" and diagnostic.performance_state == "NOT_READY"
    assert unadjusted.context_class == "A" and unadjusted.delta_hero == 0
    assert evaluate(raw, params).context_class == "B"


def test_paired_hero_term_uses_only_viewer_and_counterpart() -> None:
    metric = "mid.lane_net_worth_advantage_at_10.v1"
    params = _parameters()
    params = ParameterSet(**{
        **params.__dict__,
        "metrics": {metric: MetricParameters(10.0, 0.35, -100.0, 0.0)},
        "hero_levels": {(2, 2, metric): HeroLevel(30.0, 500), (12, 2, metric): HeroLevel(10.0, 500)},
        "opponent_effects": {(2, 12): 2.0},
        "role_slopes": {"MID": 1.0},
        "lane_thresholds": {"MID": (-2.0, 2.0)},
    })
    context = _input(metric_id=metric, role="MID", hero_id=2, position=2, lane="MID_LANE",
                     players=tuple(DraftPlayer(p.hero_id, p.position, p.lane, p.is_radiant) for p in _draft()))
    result = evaluate(context, params)
    assert result.hero_level == 20.0
    assert result.delta_hero == 7.5
    assert result.adjusted_expectation == 107.5
    # The paired hero term does not depend on the lane (badge) model.
    assert evaluate(context, ParameterSet(**{**params.__dict__, "cs_slope_regression_passed": False})).hero_level == 20.0
    changed_teammate = list(context.players)
    changed_teammate[3] = DraftPlayer(999, 4, "SAFE_LANE", True)
    assert evaluate(ContextInput(**{**context.__dict__, "players": tuple(changed_teammate)}), params).lane_score == result.lane_score
    changed_counterpart = list(context.players)
    changed_counterpart[6] = DraftPlayer(12, 2, "OFF_LANE", False)
    assert evaluate(ContextInput(**{**context.__dict__, "players": tuple(changed_counterpart)}), params).delta_hero == 0


def test_gold_metric_expectation_ignores_lane_score() -> None:
    metric = "offlane.net_worth_at_10.v1"
    params = _parameters()
    params = ParameterSet(**{
        **params.__dict__,
        "metrics": {metric: MetricParameters(1000.0, 0.35, 0.0, 0.0)},
        "opponent_effects": {(3, 11): 5.0, (3, 14): 5.0},
    })
    result = evaluate(_input(metric_id=metric, role="OFFLANE", hero_id=3, position=3,
                             lane="OFF_LANE", baseline=3000.0, comparison_value=4000.0,
                             prior_hero_levels=()), params)
    assert result.context_class == "B"
    assert result.lane_score == 10.0
    assert result.adjusted_expectation == 3000.0
    assert result.performance_state == "ABOVE"


@pytest.mark.parametrize("edit", [
    lambda rows: (rows[:9] + (DraftPlayer(15, None, "OFF_LANE", False),)),
    lambda rows: (rows[:9] + (DraftPlayer(15, 5, "ROAMING", False),)),
])
def test_lane_shape_or_enum_gaps_are_unavailable(edit) -> None:
    result = evaluate(_input(players=edit(_draft())), _parameters())
    assert result.lane_context == "UNAVAILABLE"
    assert result.adjusted_expectation == 107.5


def test_context_input_contains_only_allowlisted_pre_match_and_personal_history_fields() -> None:
    # Forbidden match outcomes, telemetry, provider scores, rank, and teammate behavior have no input slot.
    assert {field.name for field in fields(ContextInput)} == {
        "metric_id", "role", "mode", "hero_id", "position", "lane", "is_radiant", "players",
        "comparison_value", "baseline", "prior_count", "prior_hero_levels",
    }
    assert {field.name for field in fields(DraftPlayer)} == {"hero_id", "position", "lane", "is_radiant"}
