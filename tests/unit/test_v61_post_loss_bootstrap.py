from __future__ import annotations

import pytest
from app.player_analysis_v61.family_statistics import (
    _ordered_post_loss_statistic,
    _post_loss_branch_bootstrap_p_values,
    _post_loss_family_bootstrap_p,
    _simes_p,
)


def test_ordered_post_loss_statistic_uses_all_three_states() -> None:
    states = {
        "win": (0.0, 1.0),
        "one_loss": (1.0, 2.0),
        "two_plus_losses": (2.0, 3.0),
    }

    assert _ordered_post_loss_statistic(states) == 1.0


def test_ordered_post_loss_statistic_two_states_is_exact_contrast() -> None:
    states = {"one_loss": (0.2, 8.0), "two_plus_losses": (0.7, 12.0)}

    assert _ordered_post_loss_statistic(states) == pytest.approx(0.5)


def test_flat_post_loss_trend_is_not_significant_and_win_streak_is_ignored() -> None:
    states = {
        "win": (0.0, 5.0),
        "one_loss": (0.0, 5.0),
        "two_plus_losses": (0.0, 5.0),
        "win_streak": ("bad", "evidence"),
    }
    point = {"one_loss_departure": 0.0, "two_loss_switch": 0.0, "trend": 0.0}
    samples = {key: [0.0] * 40 for key in point}

    assert _ordered_post_loss_statistic(states) == 0.0
    assert _post_loss_family_bootstrap_p(point, samples) == 1.0


def test_post_loss_branch_values_are_distinct_and_adjustment_is_one() -> None:
    point = {"one_loss_departure": 0.2, "two_loss_switch": 0.3, "trend": 0.25}
    samples = {
        "one_loss_departure": [0.2 + 0.001 * (index % 2) for index in range(40)],
        "two_loss_switch": [0.0] * 40,
        "trend": [0.25 + 0.001 * (index % 2) for index in range(40)],
    }

    values = _post_loss_branch_bootstrap_p_values(point, samples)

    assert len(set(values.values())) > 1
    assert values["adjustment_without_recovery"] == 1.0
    assert values["one_loss_runback"] < 0.05
    assert values["two_loss_switch"] >= 0.05


def test_post_loss_invariant_equivalence_can_qualify() -> None:
    point = {"one_loss_departure": 0.01, "two_loss_switch": 0.01, "trend": 0.0}
    samples = {key: [value + 0.001 * (index % 2) for index in range(40)] for key, value in point.items()}

    values = _post_loss_branch_bootstrap_p_values(point, samples)

    assert values["result_invariant_response"] < 0.05


def test_post_loss_invalid_evidence_fails_closed() -> None:
    assert _ordered_post_loss_statistic({"win": ("bad", 1), "one_loss": (0.1, 1)}) is None
    values = _post_loss_branch_bootstrap_p_values(
        {"one_loss_departure": 0.1, "two_loss_switch": 0.1, "trend": 0.1},
        {"one_loss_departure": ["bad"], "two_loss_switch": [0.1], "trend": [0.1]},
    )
    assert all(value == 1.0 for value in values.values())


def test_simes_rejects_boolean_inputs() -> None:
    assert _simes_p([True, 0.1]) == 1.0
