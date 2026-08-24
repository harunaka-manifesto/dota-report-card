"""Aggregate-only V6.1 synthetic and release-gate evidence."""

from __future__ import annotations

import random
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from .hierarchical import hierarchical_qualification
from .versions import default_versions_v61

SYNTHETIC_EVALUATION_VERSION = "v61-synthetic-evaluation-1.0.0"
RELEASE_EVALUATION_VERSION = "v61-release-evaluation-1.0.0"

# State A is a named contract, not an open-ended bag of booleans.  Keeping the
# manifest here prevents a caller from accidentally declaring implementation
# complete after checking only a convenient subset of the plan.
REQUIRED_STATE_A_CHECKS = frozenset(
    {
        "v60_compatibility",
        "versioned_fail_closed_artifacts",
        "canonical_one_request",
        "runtime_calibration_projection_parity",
        "reproducible_history_audit",
        "seven_elements_five_families",
        "researched_feature_registry",
        "breadth_and_fractional_toolkit_semantics",
        "repaired_estimators",
        "semantic_outcome_registry",
        "hierarchical_family_branch_fdr",
        "result_and_session_relationships",
        "experimental_offline_methodology",
        "experimental_publication_guard",
        "typed_identity_and_claim_contracts",
        "protected_deep_cohort_authorization",
        "api_web_interactions_and_fallbacks",
        "accessibility_privacy_resume_followup_analytics",
        "calibration_evaluation_builders",
        "release_flags_and_rollback",
        "documentation_and_ci",
        "figma_handoff_brief",
        "repository_verification",
        "user_changes_preserved",
    }
)

REQUIRED_STATE_D_CHECKS = frozenset(
    {
        "brief_exists",
        "implemented_contract_references",
        "unresolved_inputs_listed",
        "future_agent_definition_of_done",
    }
)


def run_synthetic_evaluation(*, seed: int = 61, replicates: int = 2_000) -> dict[str, Any]:
    rng = random.Random(seed)
    family_discoveries = 0
    branch_discoveries = 0
    interval_covered = 0
    for _ in range(replicates):
        family_p = {
            family: rng.random()
            for family in (
                "pool_shape",
                "transfer",
                "post_loss_response",
                "combat_expression",
                "session_drift",
            )
        }
        branch_p = {
            family: {f"{family}:branch:{index}": rng.random() for index in range(3)}
            for family in family_p
        }
        audit = hierarchical_qualification(family_p, branch_p)
        family_discoveries += any(bool(value["qualified"]) for value in audit.values())
        branch_qualified = False
        for value in audit.values():
            branches = value.get("branches")
            if isinstance(branches, Mapping):
                branch_qualified = branch_qualified or any(
                    isinstance(branch, Mapping) and bool(branch.get("qualified"))
                    for branch in branches.values()
                )
        branch_discoveries += branch_qualified
        # A deterministic known-truth normal approximation sanity check.
        truth = 0.40
        observations = [1 if rng.random() < truth else 0 for _ in range(400)]
        estimate = (sum(observations) + 2) / 404
        half = 1.96 * (estimate * (1 - estimate) / 405) ** 0.5
        interval_covered += estimate - half <= truth <= estimate + half
    return {
        "version": SYNTHETIC_EVALUATION_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "replicates": replicates,
        "interval_empirical_coverage": interval_covered / replicates,
        "family_global_null_discovery_rate": family_discoveries / replicates,
        "branch_global_null_discovery_rate": branch_discoveries / replicates,
        "known_truth": {"finishing_share": 0.40, "opportunities_per_replicate": 400},
        "versions": default_versions_v61(),
        "private_identifiers_present": False,
    }


def build_release_evaluation(
    *,
    implementation_checks: Mapping[str, bool],
    synthetic: Mapping[str, Any],
    automated_calibration: Mapping[str, Any] | None = None,
    human_reviews: Mapping[str, Any] | None = None,
    operator_authorized: bool = False,
    figma_handoff_checks: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    synthetic_passed = (
        0.93 <= float(synthetic.get("interval_empirical_coverage", 0.0)) <= 0.97
        and float(synthetic.get("family_global_null_discovery_rate", 1.0)) <= 0.05
        and float(synthetic.get("branch_global_null_discovery_rate", 1.0)) <= 0.05
    )
    implementation = dict(implementation_checks)
    missing_state_a = sorted(REQUIRED_STATE_A_CHECKS - implementation.keys())
    failed_state_a = sorted(
        key for key in REQUIRED_STATE_A_CHECKS if implementation.get(key) is not True
    )
    state_a = not missing_state_a and not failed_state_a and synthetic_passed
    calibration = dict(automated_calibration or {})
    state_b = state_a and calibration.get("sealed_holdout_passed") is True and calibration.get("frozen_artifacts") is True
    reviews = dict(human_reviews or {})
    state_c = state_b and all(
        reviews.get(key) is True
        for key in ("statistical", "dota_language", "copy", "accessibility", "product_comprehension")
    ) and operator_authorized
    figma = dict(figma_handoff_checks or {})
    missing_state_d = sorted(REQUIRED_STATE_D_CHECKS - figma.keys())
    failed_state_d = sorted(key for key in REQUIRED_STATE_D_CHECKS if figma.get(key) is not True)
    state_d = not missing_state_d and not failed_state_d
    return {
        "version": RELEASE_EVALUATION_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "states": {
            "implementation_complete": state_a,
            "automated_calibration_complete": state_b,
            "public_release_ready": state_c,
            "figma_documentation_handoff_ready": state_d,
        },
        "gates": {
            "implementation_checks": implementation,
            "implementation_missing": missing_state_a,
            "implementation_failed": failed_state_a,
            "synthetic_passed": synthetic_passed,
            "automated_calibration": calibration,
            "human_reviews": reviews,
            "operator_authorized": operator_authorized,
            "figma_handoff_checks": figma,
            "figma_handoff_missing": missing_state_d,
            "figma_handoff_failed": failed_state_d,
        },
        "public_flags_must_remain_off": not state_c,
    }


__all__ = [
    "RELEASE_EVALUATION_VERSION",
    "REQUIRED_STATE_A_CHECKS",
    "REQUIRED_STATE_D_CHECKS",
    "SYNTHETIC_EVALUATION_VERSION",
    "build_release_evaluation",
    "run_synthetic_evaluation",
]
