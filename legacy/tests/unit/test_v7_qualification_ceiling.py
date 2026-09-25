from __future__ import annotations

import math

import pytest

from scripts.v7_qualification_ceiling import (
    REPORTED_CRITICAL_VALUES,
    portfolio_share_at_least,
    qualified_share,
    required_per_candidate,
    required_ratio,
)


def test_no_heterogeneity_qualifies_only_the_nominal_false_positive_rate() -> None:
    # tau = 0 means every player is identical; a calibrated test must then
    # reject at exactly the nominal rate and nothing more.
    assert qualified_share(REPORTED_CRITICAL_VALUES["0.05"], 0.0) == pytest.approx(0.05, abs=1e-9)
    assert qualified_share(REPORTED_CRITICAL_VALUES["0.01"], 0.0) == pytest.approx(0.01, abs=1e-9)


def test_qualified_share_rises_with_signal_to_noise() -> None:
    critical = REPORTED_CRITICAL_VALUES["0.05"]
    shares = [qualified_share(critical, ratio) for ratio in (0.0, 1.0, 3.0, 10.0, 100.0)]
    assert shares == sorted(shares)
    assert shares[-1] > 0.95


def test_qualified_share_approaches_one_only_in_the_limit() -> None:
    assert qualified_share(REPORTED_CRITICAL_VALUES["0.01"], 1_000.0) < 1.0


def test_required_ratio_inverts_qualified_share() -> None:
    for level, critical in REPORTED_CRITICAL_VALUES.items():
        for target in (0.20, 0.50, 0.75, 0.90):
            ratio = required_ratio(critical, target)
            assert qualified_share(critical, ratio) == pytest.approx(target, abs=1e-9), level


def test_a_target_below_the_nominal_rate_needs_no_signal() -> None:
    assert required_ratio(REPORTED_CRITICAL_VALUES["0.05"], 0.05) == 0.0
    assert required_ratio(REPORTED_CRITICAL_VALUES["0.05"], 0.01) == 0.0


def test_stricter_levels_demand_more_signal_for_the_same_reach() -> None:
    strict = required_ratio(REPORTED_CRITICAL_VALUES["0.01"], 0.80)
    loose = required_ratio(REPORTED_CRITICAL_VALUES["0.05"], 0.80)
    assert strict > loose


@pytest.mark.parametrize("target", [0.0, 1.0, -0.1, 1.5])
def test_impossible_targets_fail_closed(target: float) -> None:
    with pytest.raises(ValueError):
        required_ratio(REPORTED_CRITICAL_VALUES["0.05"], target)


def test_portfolio_bound_matches_the_binomial_definition() -> None:
    # P(>=3 of 5) at p = 0.5 is (10 + 5 + 1) / 32.
    assert portfolio_share_at_least(0.5, 5, 3) == pytest.approx(16 / 32)
    assert portfolio_share_at_least(1.0, 5, 3) == pytest.approx(1.0)
    assert portfolio_share_at_least(0.0, 5, 3) == pytest.approx(0.0)
    assert portfolio_share_at_least(0.4, 5, 0) == pytest.approx(1.0)


def test_required_per_candidate_inverts_the_portfolio_bound() -> None:
    for target in (0.60, 0.80, 0.90):
        per_candidate = required_per_candidate(5, 3, target)
        assert portfolio_share_at_least(per_candidate, 5, 3) == pytest.approx(target, abs=1e-6)


def test_the_measured_contrast_families_are_far_below_the_portfolio_requirement() -> None:
    # The calibrated contrast families measured tau/SE between 1.0 and 3.4.
    # Reaching three-of-five for 80% of players needs roughly 6 at the 0.01
    # level. This test states the gap as a fact, so a later change that quietly
    # narrows it has to say so.
    needed = required_ratio(
        REPORTED_CRITICAL_VALUES["0.01"], required_per_candidate(5, 3, 0.80)
    )
    assert needed > 5.5
    best_measured_calibrated_ratio = 3.41
    assert best_measured_calibrated_ratio < needed
    # Standard error falls as 1/sqrt(n), so closing that gap by volume alone
    # would take more than a threefold increase in matches per player.
    assert (needed / best_measured_calibrated_ratio) ** 2 > 3.0


def test_reported_critical_values_are_the_usual_two_sided_normal_quantiles() -> None:
    assert REPORTED_CRITICAL_VALUES["0.05"] == pytest.approx(1.959964, abs=1e-5)
    assert REPORTED_CRITICAL_VALUES["0.01"] == pytest.approx(2.575829, abs=1e-5)
    assert math.isclose(
        qualified_share(REPORTED_CRITICAL_VALUES["0.05"], 0.0), 0.05, abs_tol=1e-9
    )
