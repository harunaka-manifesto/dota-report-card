from __future__ import annotations

import pytest
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

