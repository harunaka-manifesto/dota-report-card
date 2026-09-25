"""Section 5: the single improvement.

The tests that matter here are the honesty constraints. A recommendation is
the one thing in the report that tells the player to *do* something, so the
guards against circularity, against a missing denominator, and against a
population comparison dressed up as a personal gap are the load-bearing part.
"""

from __future__ import annotations

from typing import Any

import pytest
from report_card.player_analysis_v7.research import inference
from report_card.player_analysis_v7.research.recommendation import (
    ARM_LOSS,
    ARM_WIN,
    DOWNSTREAM_EXCLUSIONS,
    LANING_MINUTE,
    MIN_PER_ARM,
    MODAL_SIGN_SHARE_LIMIT,
    OUTCOME_CONTAMINATED_EXCLUSIONS,
    RECOMMENDATION_REGISTRY,
    ScoredRecommendation,
    build_personal_contrast_matrix,
    dimension_scale,
    eligible_dimensions,
    first_ward_time,
    gap_reliability,
    gap_supports_action,
    has_denominator,
    last_hits_at_ten,
    modal_sign_share,
    opportunities,
    outcome_arm,
    priority,
    recommendation_ctx,
    select,
    standardized_gap,
)

from legacy.tests.unit.test_v7_research_pass2_features import row


def match(match_id: int, *, won: bool, last_hits: list[int] | None = None) -> dict[str, Any]:
    series = last_hits if last_hits is not None else [3] * 31
    return row(
        match_id=match_id,
        self={
            "is_victory": won,
            "trajectories": {"last_hits_per_minute": series},
        },
    )


# --------------------------------------------------------------------------
# registry and eligibility
# --------------------------------------------------------------------------


def test_every_dimension_carries_a_verification() -> None:
    """The verification field is what separates this from advice."""

    for dimension in RECOMMENDATION_REGISTRY.values():
        assert dimension.verification.strip()
        assert dimension.recommendation.strip()
        assert dimension.upstream_rationale.strip()


def test_actionability_weights_lie_in_the_unit_interval() -> None:
    for dimension in RECOMMENDATION_REGISTRY.values():
        assert 0.0 <= dimension.actionability <= 1.0


def test_actionability_rejects_a_weight_outside_the_unit_interval() -> None:
    dimension = RECOMMENDATION_REGISTRY["last_hits_at_ten"]
    with pytest.raises(ValueError):
        type(dimension)(
            key="bad",
            fn=dimension.fn,
            actionability=1.5,
            upstream=True,
            outcome_contaminated=False,
            higher_is_worse=False,
            recommendation="x",
            verification="x",
            upstream_rationale="x",
        )


def test_eligible_dimensions_applies_both_exclusion_rules() -> None:
    eligible = eligible_dimensions()
    for key in OUTCOME_CONTAMINATED_EXCLUSIONS:
        assert key not in eligible
    for key in DOWNSTREAM_EXCLUSIONS:
        assert key not in eligible
    for key, dimension in RECOMMENDATION_REGISTRY.items():
        if dimension.upstream and not dimension.outcome_contaminated:
            assert key in eligible


def test_the_recorded_exclusions_match_the_registry_flags() -> None:
    """The exclusion table is documentation; the flags are what runs. They
    must not drift apart."""

    flagged = {
        key
        for key, dimension in RECOMMENDATION_REGISTRY.items()
        if dimension.outcome_contaminated
    }
    assert flagged == set(OUTCOME_CONTAMINATED_EXCLUSIONS)


def test_downstream_exclusions_are_not_in_the_registry_at_all() -> None:
    for key in DOWNSTREAM_EXCLUSIONS:
        assert key not in RECOMMENDATION_REGISTRY


# --------------------------------------------------------------------------
# the outcome-contamination screen
# --------------------------------------------------------------------------


def test_modal_sign_share_is_one_when_every_gap_runs_the_same_way() -> None:
    assert modal_sign_share([-1.0, -2.0, -0.5]) == pytest.approx(1.0)


def test_modal_sign_share_is_a_half_for_an_even_split() -> None:
    assert modal_sign_share([1.0, -1.0, 2.0, -2.0]) == pytest.approx(0.5)


def test_modal_sign_share_counts_zero_toward_neither_sign() -> None:
    assert modal_sign_share([1.0, -1.0, 0.0, 0.0]) == pytest.approx(0.25)


def test_the_screen_limit_is_below_one() -> None:
    """A limit of 1.0 would only catch a gap with no exceptions at all, which
    is a rule that never fires."""

    assert 0.5 < MODAL_SIGN_SHARE_LIMIT < 1.0


# --------------------------------------------------------------------------
# context and arms
# --------------------------------------------------------------------------


def test_outcome_arm_reads_the_players_own_result() -> None:
    assert outcome_arm(match(1, won=True)) == ARM_WIN
    assert outcome_arm(match(2, won=False)) == ARM_LOSS


def test_outcome_arm_is_none_without_a_result() -> None:
    assert outcome_arm(row(self={"is_victory": None})) is None


def test_context_excludes_duration_and_side() -> None:
    """Duration is downstream of the outcome -- a stomped loss is short -- so
    controlling for it would absorb the gap rather than a confounder."""

    factors = {name for name, _ in recommendation_ctx(match(1, won=True))}
    assert factors == {"mode", "patch", "hero", "position", "role", "lane"}


# --------------------------------------------------------------------------
# denominator
# --------------------------------------------------------------------------


def test_has_denominator_requires_both_arms() -> None:
    series = opportunities(
        [match(i, won=True) for i in range(MIN_PER_ARM * 2)],
        RECOMMENDATION_REGISTRY["last_hits_at_ten"],
    )
    assert series
    assert has_denominator(series) is False


def test_has_denominator_accepts_a_balanced_split() -> None:
    rows = [match(i, won=True) for i in range(MIN_PER_ARM)]
    rows += [match(100 + i, won=False) for i in range(MIN_PER_ARM)]
    series = opportunities(rows, RECOMMENDATION_REGISTRY["last_hits_at_ten"])
    assert has_denominator(series) is True


def test_has_denominator_rejects_one_short_on_either_side() -> None:
    rows = [match(i, won=True) for i in range(MIN_PER_ARM)]
    rows += [match(100 + i, won=False) for i in range(MIN_PER_ARM - 1)]
    series = opportunities(rows, RECOMMENDATION_REGISTRY["last_hits_at_ten"])
    assert has_denominator(series) is False


# --------------------------------------------------------------------------
# measurements
# --------------------------------------------------------------------------


def test_last_hits_at_ten_sums_increments_rather_than_indexing() -> None:
    """last_hits_per_minute is a per-minute increment, not a running total."""

    assert last_hits_at_ten(match(1, won=True, last_hits=[3] * 31)) == pytest.approx(
        3 * (LANING_MINUTE + 1)
    )


def test_last_hits_at_ten_refuses_a_hole_in_the_window() -> None:
    series: list[Any] = [3] * 31
    series[4] = None
    assert last_hits_at_ten(match(1, won=True, last_hits=series)) is None


def test_first_ward_time_takes_the_earliest_observer_ward() -> None:
    warded = row(
        self={"events": {"wards": [{"time": 300, "type": 0}, {"time": 120, "type": 0}]}}
    )
    assert first_ward_time(warded) == pytest.approx(120.0)


def test_first_ward_time_ignores_sentries() -> None:
    sentry_only = row(self={"events": {"wards": [{"time": 120, "type": 1}]}})
    assert first_ward_time(sentry_only) is None


# --------------------------------------------------------------------------
# the personal gap
# --------------------------------------------------------------------------


def _two_player_matrix() -> inference.FamilyMatrix:
    dimension = RECOMMENDATION_REGISTRY["last_hits_at_ten"]
    per_player = []
    for player, (win_lh, loss_lh) in enumerate(((6, 3), (4, 4))):
        # Interleaved, as a real history is: the blocked-means contrast needs
        # both arms inside a block, and 40 wins followed by 40 losses gives it
        # blocks that are entirely one arm.
        rows = []
        for i in range(40):
            rows.append(match(2 * i, won=True, last_hits=[win_lh] * 31))
            rows.append(match(2 * i + 1, won=False, last_hits=[loss_lh] * 31))
        per_player.append((f"player-{player}", opportunities(rows, dimension)))
    return build_personal_contrast_matrix(per_player)


def test_the_arm_is_not_projected_out() -> None:
    """``build_matrix(arm_family=True)`` encodes the arm as a context factor
    and removes the population-wide win/loss effect, which turns a personal
    gap into a population comparison -- forbidden by constraint 3."""

    matrix = _two_player_matrix()
    assert "__arm__" not in matrix.encoded.factors


def test_the_personal_gap_survives_a_population_wide_effect() -> None:
    """Both players could be given the same gap and the second player's zero
    gap must still read as zero, not as 'below average'."""

    matrix = _two_player_matrix()
    results = {r.pseudonym: r for r in inference.infer_all(matrix)}
    assert results["player-0"].delta < -1.0  # fewer last hits in losses
    assert results["player-1"].delta == pytest.approx(0.0, abs=1e-6)


def test_dimension_scale_is_the_pooled_spread() -> None:
    matrix = _two_player_matrix()
    assert dimension_scale(matrix) > 0.0


# --------------------------------------------------------------------------
# priority
# --------------------------------------------------------------------------


def test_standardized_gap_divides_by_the_scale() -> None:
    assert standardized_gap(2.0, 4.0) == pytest.approx(0.5)


def test_standardized_gap_is_zero_on_a_degenerate_scale() -> None:
    assert standardized_gap(2.0, 0.0) == 0.0
    assert standardized_gap(2.0, float("nan")) == 0.0


def test_gap_reliability_falls_as_the_gap_gets_noisier() -> None:
    clean = gap_reliability(0.1, 1.0, 1.0)
    noisy = gap_reliability(1.0, 1.0, 1.0)
    assert 0.0 < noisy < clean <= 1.0


def test_gap_reliability_accounts_for_dependence() -> None:
    """Constraint 1: a noisy gap cannot be promoted to advice, and serial
    dependence is part of the noise."""

    assert gap_reliability(0.5, 1.0, 4.0) < gap_reliability(0.5, 1.0, 1.0)


def test_priority_is_the_product_of_all_three_terms() -> None:
    assert priority(2.0, 0.5, 0.4) == pytest.approx(0.4)


def test_priority_of_an_unactionable_dimension_is_zero() -> None:
    assert priority(10.0, 1.0, 0.0) == 0.0


@pytest.mark.parametrize(
    ("key", "gap", "expected"),
    [
        ("first_ward_time", 1.0, True),
        ("first_ward_time", -1.0, False),
        ("last_hits_at_ten", -1.0, True),
        ("last_hits_at_ten", 1.0, False),
        ("first_ward_time", 0.0, False),
    ],
)
def test_gap_supports_only_the_registry_action_polarity(
    key: str, gap: float, expected: bool
) -> None:
    assert gap_supports_action(gap, RECOMMENDATION_REGISTRY[key]) is expected


def test_non_finite_gap_does_not_support_action() -> None:
    assert gap_supports_action(float("nan"), RECOMMENDATION_REGISTRY["first_ward_time"]) is False


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------


def _scored(key: str, priority_value: float, actionability: float = 0.5, sample: int = 100) -> ScoredRecommendation:
    return ScoredRecommendation(
        key=key,
        gap=1.0,
        standard_error=0.1,
        standardized_gap=1.0,
        reliability=1.0,
        actionability=actionability,
        priority=priority_value,
        direction="positive",
        wins=sample // 2,
        losses=sample // 2,
        recommendation="do the thing",
        verification="measure the thing",
    )


def test_exactly_one_recommendation_and_two_runners_up() -> None:
    scored = [_scored(f"d{i}", priority_value=1.0 - i / 10) for i in range(6)]
    top, runners = select(scored)
    assert top is not None and top.key == "d0"
    assert [r.key for r in runners] == ["d1", "d2"]


def test_selection_does_not_depend_on_input_order() -> None:
    scored = [_scored(f"d{i}", priority_value=1.0 - i / 10) for i in range(6)]
    forward = select(scored)
    backward = select(list(reversed(scored)))
    assert forward[0] == backward[0]
    assert [r.key for r in forward[1]] == [r.key for r in backward[1]]


def test_ties_break_toward_the_more_actionable_dimension() -> None:
    top, _ = select(
        [
            _scored("low", priority_value=0.5, actionability=0.2),
            _scored("high", priority_value=0.5, actionability=0.9),
        ]
    )
    assert top is not None and top.key == "high"


def test_ties_then_break_toward_the_larger_sample() -> None:
    top, _ = select(
        [
            _scored("small", priority_value=0.5, actionability=0.5, sample=40),
            _scored("large", priority_value=0.5, actionability=0.5, sample=400),
        ]
    )
    assert top is not None and top.key == "large"


def test_no_candidates_means_no_recommendation() -> None:
    top, runners = select([])
    assert top is None
    assert runners == []


def test_fewer_than_three_candidates_yields_fewer_runners_up() -> None:
    top, runners = select([_scored("only", priority_value=0.5)])
    assert top is not None
    assert runners == []
