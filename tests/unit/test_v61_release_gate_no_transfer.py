from __future__ import annotations

from app.player_analysis_v61.copy import SEMANTIC_COPY_REGISTRY
from app.player_analysis_v61.family_statistics import (
    _transfer_branch_bootstrap_p_values,
    _transfer_family_bootstrap_p,
)
from app.player_analysis_v61.hierarchical import hierarchical_qualification
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_CATALOG


def test_reference_no_transfer_reaches_public_hierarchy_with_tight_bootstrap() -> None:
    point = {"outcome": 0.167, "activity": -0.081, "survival": 0.315}
    ropes = {"outcome": 0.08, "activity": 0.08, "survival": 0.35}
    samples = {
        component: [value + 0.0001 * (index % 2) for index in range(2_000)]
        for component, value in point.items()
    }
    transfer_branches = _transfer_branch_bootstrap_p_values(point, samples, ropes)
    transfer_family = _transfer_family_bootstrap_p(transfer_branches)

    family_p = {
        "pool_shape": 1.0,
        "transfer": transfer_family,
        "post_loss_response": 1.0,
        "combat_expression": 1.0,
        "session_drift": 1.0,
    }
    branch_p = {
        family: {
            definition.semantic_outcome_key: 1.0
            for definition in SEMANTIC_OUTCOME_CATALOG
            if definition.rollout_status == "public_candidate" and definition.family_key == family
        }
        for family in family_p
    }
    branch_p["transfer"] = transfer_branches

    qualified = hierarchical_qualification(family_p, branch_p, q=0.05)

    assert set(qualified) == {
        "pool_shape",
        "transfer",
        "post_loss_response",
        "combat_expression",
        "session_drift",
    }
    assert qualified["transfer"]["qualified"] is True
    assert qualified["transfer"]["branches"]["no_transfer"]["qualified"] is True
    assert qualified["transfer"]["branches"]["no_transfer"]["raw_p_value"] < 0.05
    assert qualified["transfer"]["adjusted_q_value"] <= 0.05
    assert transfer_branches["no_transfer"] < transfer_branches["clean_transfer"]
    assert SEMANTIC_COPY_REGISTRY["no_transfer"].claim == (
        "Your game changed outside your usual heroes."
    )
