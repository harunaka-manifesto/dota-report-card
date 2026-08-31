from __future__ import annotations

from app.player_analysis_v61.family_statistics import (
    _bootstrap_departure_p,
    _bootstrap_equivalence_p,
)


def test_bootstrap_departure_p_detects_tight_nonzero_point() -> None:
    samples = [0.2 + 0.001 * (index % 2) for index in range(40)]

    assert _bootstrap_departure_p(0.2, samples) < 0.05


def test_bootstrap_departure_p_zero_point_is_not_significant() -> None:
    samples = [0.001 * (index % 2) for index in range(40)]

    assert _bootstrap_departure_p(0.0, samples) == 1.0


def test_bootstrap_equivalence_p_detects_tight_point_inside_rope() -> None:
    samples = [0.01 + 0.001 * (index % 2) for index in range(40)]

    assert _bootstrap_equivalence_p(0.01, samples, 0.1) < 0.05


def test_bootstrap_equivalence_p_rejects_point_outside_rope() -> None:
    samples = [0.2 + 0.001 * (index % 2) for index in range(40)]

    assert _bootstrap_equivalence_p(0.2, samples, 0.1) >= 0.05
