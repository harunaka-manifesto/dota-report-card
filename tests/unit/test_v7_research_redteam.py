"""Unit tests for the independent red-team checks."""

from __future__ import annotations

import math

import pytest
from report_card.player_analysis_v7.research.redteam import (
    bonferroni_level,
    disattenuated_agreement,
    expected_qualified_share,
    marginal_variance_ratio,
    qualified_share_at_ratio,
)

from scripts.v7_qualification_ceiling import qualified_share


def test_the_closed_form_agrees_with_the_ceiling_scripts_own_implementation() -> None:
    # The red-team check must not be a second, subtly different formula, or a
    # disagreement would say nothing about the claim under audit.
    for ratio in (0.0, 0.78, 3.08, 9.69):
        for critical in (1.959963984540054, 2.5758293035489004):
            assert qualified_share_at_ratio(critical, ratio) == pytest.approx(
                qualified_share(critical, ratio), abs=1e-12
            )


def test_qualified_share_rejects_impossible_arguments() -> None:
    with pytest.raises(ValueError):
        qualified_share_at_ratio(0.0, 1.0)
    with pytest.raises(ValueError):
        qualified_share_at_ratio(1.96, -0.1)


def test_perfect_reliability_leaves_agreement_untouched() -> None:
    assert disattenuated_agreement(0.495, 1.0, 1.0) == pytest.approx(0.495)


def test_a_noisier_family_is_corrected_upwards() -> None:
    # duration_tempo reproduces itself within a mode at ~0.98/0.90; the
    # contrast families at ~0.65. Equal raw agreement therefore means the
    # contrast family is measuring the more mode-portable trait.
    level = disattenuated_agreement(0.495, 0.981, 0.901)
    contrast = disattenuated_agreement(0.482, 0.650, 0.658)
    assert level == pytest.approx(0.526, abs=5e-3)
    assert contrast == pytest.approx(0.738, abs=5e-3)
    assert contrast > level


def test_disattenuation_is_undefined_rather_than_infinite_at_zero_reliability() -> None:
    assert math.isnan(disattenuated_agreement(0.4, 0.0, 0.5))
    assert math.isnan(disattenuated_agreement(0.4, 0.5, -0.1))


def test_homogeneous_standard_errors_reproduce_the_median_evaluation() -> None:
    critical = 2.5758293035489004
    errors = [0.02] * 50
    assert expected_qualified_share(critical, 0.1, errors) == pytest.approx(
        qualified_share_at_ratio(critical, 0.1 / 0.02)
    )


def test_spread_standard_errors_move_the_share_away_from_the_median_player() -> None:
    critical = 2.5758293035489004
    spread = [0.005, 0.01, 0.02, 0.08, 0.40]
    at_median = qualified_share_at_ratio(critical, 0.1 / 0.02)
    averaged = expected_qualified_share(critical, 0.1, spread)
    assert averaged != pytest.approx(at_median, abs=1e-3)
    assert 0.0 < averaged < 1.0


def test_expected_share_ignores_unusable_standard_errors() -> None:
    critical = 1.959963984540054
    assert expected_qualified_share(critical, 0.1, [float("nan"), 0.0, -1.0, 0.02]) == (
        pytest.approx(qualified_share_at_ratio(critical, 5.0))
    )
    assert math.isnan(expected_qualified_share(critical, 0.1, [float("nan")]))


def test_variance_decomposition_is_one_when_the_model_generated_the_data() -> None:
    # Deviations of exactly +/- sqrt(tau^2 + se^2) have that variance by
    # construction, up to the sample-variance (n-1) denominator the check uses.
    tau, se = 0.1, 0.03
    spread = math.sqrt(tau * tau + se * se)
    deltas = [spread, -spread] * 40
    ratio = marginal_variance_ratio(deltas, 0.0, tau, [se] * 80)
    assert ratio == pytest.approx(80.0 / 79.0, rel=1e-9)


def test_variance_decomposition_flags_an_overstated_tau() -> None:
    # Same realised spread, a tau twice as large: the model now predicts far
    # more spread than the estimates show.
    deltas = [0.05, -0.05] * 40
    assert marginal_variance_ratio(deltas, 0.0, 0.4, [0.03] * 80) < 0.25


def test_variance_decomposition_needs_data() -> None:
    assert math.isnan(marginal_variance_ratio([0.1], 0.0, 0.1, [0.02]))
    assert math.isnan(marginal_variance_ratio([0.1, 0.2], 0.0, 0.1, []))


def test_bonferroni_divides_by_the_number_of_families() -> None:
    assert bonferroni_level(0.01, 12) == pytest.approx(0.01 / 12)
    assert bonferroni_level(0.05, 1) == pytest.approx(0.05)
    with pytest.raises(ValueError):
        bonferroni_level(0.0, 12)
    with pytest.raises(ValueError):
        bonferroni_level(0.01, 0)
