from __future__ import annotations

from app.player_analysis_v61.family_statistics import (
    _simes_p,
    _transfer_branch_bootstrap_p_values,
    _transfer_family_bootstrap_p,
)

_ROPES = {"outcome": 0.08, "activity": 0.08, "survival": 0.35}


def _samples(point: dict[str, float], *, spread: float = 0.001) -> dict[str, list[float]]:
    return {
        component: [value + spread * (index % 2) for index in range(40)]
        for component, value in point.items()
    }


def test_transfer_branch_p_values_are_claim_aligned_and_localized_stays_unsupported() -> None:
    point = {"outcome": 0.2, "activity": 0.01, "survival": 0.01}
    values = _transfer_branch_bootstrap_p_values(point, _samples(point), _ROPES)

    assert values["results_stop_first"] < 0.05
    assert values["expression_stops_first"] >= 0.05
    assert values["localized_function_bottleneck"] == 1.0


def test_clean_transfer_can_qualify_without_no_transfer() -> None:
    point = {"outcome": 0.001, "activity": -0.001, "survival": 0.002}
    samples = {
        component: [value + (0.02 if index % 2 else -0.02) for index in range(40)]
        for component, value in point.items()
    }
    values = _transfer_branch_bootstrap_p_values(point, samples, _ROPES)

    assert values["clean_transfer"] < 0.05
    assert values["no_transfer"] >= 0.05


def test_no_transfer_can_qualify_when_clean_transfer_does_not() -> None:
    point = {"outcome": 0.2, "activity": -0.2, "survival": 0.4}
    values = _transfer_branch_bootstrap_p_values(point, _samples(point), _ROPES)

    assert values["no_transfer"] < 0.05
    assert values["clean_transfer"] >= 0.05


def test_transfer_family_omnibus_uses_all_seven_branch_values() -> None:
    values = {
        "clean_transfer": 0.01,
        "results_stop_first": 0.2,
        "expression_stops_first": 0.3,
        "involvement_boundary": 0.4,
        "exposure_boundary": 0.5,
        "localized_function_bottleneck": 1.0,
        "no_transfer": 0.6,
    }

    assert _transfer_family_bootstrap_p(values) == 0.07


def test_simes_is_valid_and_fails_closed() -> None:
    assert _simes_p([0.01, 0.2, 0.4]) == 0.03
    assert _simes_p([]) == 1.0
    assert _simes_p([0.1, "bad"]) == 1.0
    assert _simes_p([1.1]) == 1.0
