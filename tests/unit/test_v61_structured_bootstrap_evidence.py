from __future__ import annotations

import pytest
from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS
from app.player_analysis_v61.family_statistics import (
    _post_loss_branch_bootstrap_p_values,
    v61_production_family_branch_p_values,
)
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_CATALOG
from app.reports.dna_assembly_v61 import (
    _post_loss_bootstrap_metrics,
    _post_loss_response_statistic,
    _semantic_bootstrap_evidence,
)


def _session_statistics() -> list[dict[str, tuple[int, float]]]:
    return [
        {
            "win": (2, 0.0),
            "one_loss": (2, 0.2),
            "two_plus_losses": (2, 0.6),
        }
        for _ in range(8)
    ]


def test_weighted_post_loss_metrics_emit_ordered_scalars_and_ignore_finishing() -> None:
    metrics = _post_loss_bootstrap_metrics(_session_statistics(), [1] * 8)

    assert metrics["trend"] == pytest.approx(0.3)
    assert metrics["one_loss_departure"] == pytest.approx(0.2)
    assert metrics["two_loss_switch"] == pytest.approx(0.4)
    assert _post_loss_response_statistic(_session_statistics(), [1] * 8) == pytest.approx(0.3)


def test_semantic_evidence_has_aligned_post_loss_metrics_and_empty_branches() -> None:
    samples = [
        {
            "breadth": 2.0,
            "toolkit": 1.0,
            "involvement": 0.1,
            "death_exposure": 0.2,
            "transfer": 0.1,
            "transfer_components": {"outcome": 0.1, "activity": 0.1, "survival": 0.1},
            "post_loss_trend": 0.3,
            "post_loss_one_loss_departure": 0.2,
            "post_loss_two_loss_switch": 0.4,
            "consistency": 0.8,
        }
        for _ in range(3)
    ]
    evidence = _semantic_bootstrap_evidence(
        samples,
        post_loss_point={"trend": 0.3, "one_loss_departure": 0.2, "two_loss_switch": 0.4},
        post_loss_samples={
            "trend": [0.3] * 3,
            "one_loss_departure": [0.2] * 3,
            "two_loss_switch": [0.4] * 3,
        },
    )

    assert evidence["families"]["post_loss_response"] == [0.3] * 3
    assert evidence["post_loss_point"] == {
        "trend": 0.3,
        "one_loss_departure": 0.2,
        "two_loss_switch": 0.4,
    }
    assert all(not values for values in evidence["branches"]["transfer"].values())
    assert all(not values for values in evidence["branches"]["post_loss_response"].values())
    assert evidence["branches"]["pool_shape"]["hidden_center"] == [1.0] * 3


def test_missing_structured_post_loss_evidence_is_not_fabricated() -> None:
    evidence = _semantic_bootstrap_evidence([{"post_loss_response": 0.4}])

    assert "post_loss_point" not in evidence
    assert "post_loss_samples" not in evidence
    assert evidence["families"]["post_loss_response"] == []


def _production_evidence() -> tuple[dict[str, list[float]], dict[str, dict[str, list[float]]]]:
    families = {family: [0.2] * 4 for family in FINDING_FAMILY_KEYS}
    branches = {
        family: {
            definition.semantic_outcome_key: (
                [] if family in {"transfer", "post_loss_response"} else [0.2] * 4
            )
            for definition in SEMANTIC_OUTCOME_CATALOG
            if definition.rollout_status == "public_candidate" and definition.family_key == family
        }
        for family in FINDING_FAMILY_KEYS
    }
    return families, branches


def test_production_structured_post_loss_overrides_empty_branch_placeholders() -> None:
    families, branches = _production_evidence()
    point = {"trend": 0.2, "one_loss_departure": 0.2}
    samples = {"trend": [0.2] * 40, "one_loss_departure": [0.2] * 40}

    family, branch = v61_production_family_branch_p_values(
        semantic_calibration={"branch_procedure": "qualified-family-bh"},
        bootstrap_family_samples=families,
        bootstrap_branch_samples=branches,
        bootstrap_post_loss_point=point,
        bootstrap_post_loss_samples=samples,
    )

    assert family["post_loss_response"] < 0.05
    assert branch["post_loss_response"]["one_loss_runback"] < 0.05
    assert branch["post_loss_response"]["two_loss_switch"] == 1.0
    assert branch["post_loss_response"]["adjustment_without_recovery"] == 1.0
    semantic_draws = [
        {
            "post_loss_trend": 0.2,
            "post_loss_one_loss_departure": 0.2,
            "post_loss_two_loss_switch": None,
        }
        for _ in range(40)
    ]
    partial = _semantic_bootstrap_evidence(
        semantic_draws,
        post_loss_point=point,
        post_loss_samples=samples,
    )
    assert partial["post_loss_point"] == point
    assert "two_loss_switch" not in partial["post_loss_samples"]


def test_production_keeps_current_branch_keys_and_empty_placeholders_suppressed() -> None:
    families, branches = _production_evidence()
    family, branch = v61_production_family_branch_p_values(
        semantic_calibration={"branch_procedure": "qualified-family-bh"},
        bootstrap_family_samples=families,
        bootstrap_branch_samples=branches,
    )
    expected = {
        family_name: {
            definition.semantic_outcome_key
            for definition in SEMANTIC_OUTCOME_CATALOG
            if definition.rollout_status == "public_candidate"
            and definition.family_key == family_name
        }
        for family_name in FINDING_FAMILY_KEYS
    }

    assert {family_name: set(values) for family_name, values in branch.items()} == expected
    assert all(value == 1.0 for value in branch["transfer"].values())
    assert all(value == 1.0 for value in branch["post_loss_response"].values())
    assert family["post_loss_response"] == 1.0


def test_production_structured_transfer_branches_are_distinct() -> None:
    families, branches = _production_evidence()
    point = {"outcome": 0.2, "activity": 0.01, "survival": 0.01}
    samples = {
        component: [value + 0.001 * (index % 2) for index in range(40)]
        for component, value in point.items()
    }
    family, branch = v61_production_family_branch_p_values(
        semantic_calibration={"branch_procedure": "qualified-family-bh"},
        bootstrap_family_samples=families,
        bootstrap_branch_samples=branches,
        bootstrap_transfer_components=samples,
        transfer_point=point,
        transfer_ropes={"outcome": 0.08, "activity": 0.08, "survival": 0.35},
    )

    assert len(set(branch["transfer"].values())) > 1
    assert family["transfer"] <= 1.0
    assert _post_loss_branch_bootstrap_p_values(
        {"trend": 0.2}, {"trend": [0.2] * 40}
    )["result_invariant_response"] == 1.0
