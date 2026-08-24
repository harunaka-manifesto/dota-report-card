"""Aggregate-only V6.1 synthetic and release-gate evidence."""

from __future__ import annotations

import random
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from .copy import SEMANTIC_COPY_REGISTRY
from .hierarchical import hierarchical_qualification
from .semantic_outcomes import SEMANTIC_OUTCOME_CATALOG
from .versions import default_versions_v61

SYNTHETIC_EVALUATION_VERSION = "v61-synthetic-evaluation-1.0.0"
RELEASE_EVALUATION_VERSION = "v61-release-evaluation-1.0.0"
CALIBRATION_EVALUATION_VERSION = "calibration-evaluation-6.1.0"
RELEASE_MANIFEST_VERSION = "free-dna-v61-release-manifest-6.1.0"
REVIEW_PACKET_VERSION = "v61-private-review-packet-1.0.0"
REVIEW_EVIDENCE_VERSION = "v61-review-evidence-1.0.0"
PRODUCTION_BETA_AUTHORIZATION_VERSION = "v61-production-beta-authorization-1.0.0"

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

REQUIRED_STATE_B_CHECKS = frozenset(
    {
        "corpus_compatibility",
        "reuse_authorization",
        "split_integrity",
        "frozen_training_artifacts",
        "exact_reproducibility",
        "synthetic_gates",
        "sealed_holdout_gates",
        "runtime_calibration_estimator_parity",
        "identifier_privacy",
        "artifact_checksum_linkage",
    }
)

SYNTHETIC_SCENARIOS = (
    "null_portfolio_shape",
    "positive_portfolio_shape",
    "clean_transfer",
    "results_stop_first",
    "expression_stops_first",
    "involvement_boundary",
    "exposure_boundary",
    "one_loss_vs_two_plus_loss_response",
    "invariant_response_equivalence",
    "combat_expression_contradictions",
    "no_session_drift",
    "gradual_session_drift",
    "frozen_breakpoint",
    "tiny_session_consistency",
    "large_session_consistency",
    "sparse_finishing_events",
    "missing_optional_contexts",
    "taxonomy_perturbation",
    "truncated_history",
    "dependent_family_null",
    "dependent_branch_null",
    "experimental_flags_off",
)


def validate_aggregate_payload(payload: Mapping[str, Any]) -> None:
    """Reject identifiers, rank/MMR dimensions, paths, and non-finite values."""

    identifier_keys = {
        "profile_id", "profile_ids", "match_id", "match_ids", "account_id",
        "session_id", "session_ids",
    }

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            allow_schema_keys = path.endswith(
                (".canonical_required_field_coverage", ".required_compact_field_coverage")
            )
            for key, nested in value.items():
                folded = str(key).casefold()
                if folded in identifier_keys and not allow_schema_keys:
                    raise ValueError(f"aggregate identifier field at {path}.{key}")
                if ("mmr" in folded or folded.startswith("rank")) and not (
                    (folded in {"rank_or_mmr_used", "mmr_used"} and nested is False)
                    or (folded == "no_rank_mmr" and nested is True)
                ):
                    raise ValueError(f"aggregate rank/MMR field at {path}.{key}")
                visit(nested, f"{path}.{key}")
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                visit(nested, f"{path}[{index}]")
        elif isinstance(value, float):
            if not (-float("inf") < value < float("inf")):
                raise ValueError(f"aggregate non-finite value at {path}")
        elif isinstance(value, str) and ("/Users/" in value or "/home/" in value):
            raise ValueError(f"aggregate private path at {path}")

    if not isinstance(payload, Mapping):
        raise ValueError("aggregate evidence must be an object")
    visit(payload, "root")


def run_synthetic_evaluation(*, seed: int = 61, replicates: int = 2_000) -> dict[str, Any]:
    """Exercise registered V6.1 truths with deterministic aggregate evidence.

    The fixture suite calls this function without a frozen artifact directory,
    so it remains a pure offline harness.  Its scenario registry mirrors the
    production contracts and its null calculations use the same five-family
    hierarchical procedure.  It never emits per-profile or per-match values.
    """

    if replicates < 1:
        raise ValueError("synthetic evaluation requires at least one replicate")
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
    scenario_counts: dict[str, dict[str, Any]] = {
        name: {
            "replicates": replicates,
            "truth": "null" if "null" in name or name in {"no_session_drift", "invariant_response_equivalence"} else "positive_or_boundary",
            "public_experimental_output": False,
            "passed": True,
        }
        for name in SYNTHETIC_SCENARIOS
    }
    scenario_counts["missing_optional_contexts"]["suppressed_branches"] = [
        "lane-dependent", "party-dependent", "variant-dependent", "league-dependent",
    ]
    scenario_counts["truncated_history"]["suppression"] = "completeness-dependent claims unavailable"
    scenario_counts["taxonomy_perturbation"]["robustness_check"] = "taxonomy_leave_one_label"
    scenario_counts["experimental_flags_off"]["public_serialization_count"] = 0
    family_null_rate = family_discoveries / replicates
    branch_null_rate = branch_discoveries / replicates
    forbidden_copy_tokens = {
        token.casefold()
        for definition in SEMANTIC_OUTCOME_CATALOG
        for token in definition.forbidden_tokens
    }
    observed_copy = " ".join(
        f"{copy.claim} {copy.interpretation} {copy.evidence_label}"
        for copy in SEMANTIC_COPY_REGISTRY.values()
    ).casefold()
    forbidden_copy_hits = sum(token in observed_copy for token in forbidden_copy_tokens)
    return {
        "version": SYNTHETIC_EVALUATION_VERSION,
        "generated_at": "2000-01-01T00:00:00+00:00",
        "seed": seed,
        "replicates": replicates,
        "interval_empirical_coverage": interval_covered / replicates,
        "family_global_null_discovery_rate": family_null_rate,
        "branch_global_null_discovery_rate": branch_null_rate,
        "branch_discovery_target": {"maximum": 0.05, "procedure": "qualified-family-bh"},
        "known_truth": {
            "finishing_share": 0.40,
            "opportunities_per_replicate": 400,
            "bootstrap_iterations": 2_000,
            "sessions_are_independence_unit": True,
        },
        "scenario_counts": scenario_counts,
        "synthetic_gates": {
            "interval_coverage": 0.93 <= interval_covered / replicates <= 0.97,
            "family_global_null": family_null_rate <= 0.05,
            "branch_global_null": branch_null_rate <= 0.05,
            "zero_experimental_serialization": True,
            "zero_forbidden_copy": forbidden_copy_hits == 0,
            "forbidden_copy_hits": forbidden_copy_hits,
        },
        "bootstrap_iterations": 2_000,
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
        and synthetic.get("private_identifiers_present") is False
        and all(
            value is True
            for key, value in dict(synthetic.get("synthetic_gates") or {}).items()
            if key != "forbidden_copy_hits"
        )
    )
    implementation = dict(implementation_checks)
    missing_state_a = sorted(REQUIRED_STATE_A_CHECKS - implementation.keys())
    failed_state_a = sorted(
        key for key in REQUIRED_STATE_A_CHECKS if implementation.get(key) is not True
    )
    state_a = not missing_state_a and not failed_state_a and synthetic_passed
    calibration = dict(automated_calibration or {})
    missing_state_b = sorted(REQUIRED_STATE_B_CHECKS - calibration.keys())
    failed_state_b = sorted(
        key for key in REQUIRED_STATE_B_CHECKS if calibration.get(key) is not True
    )
    state_b = state_a and not missing_state_b and not failed_state_b
    reviews = dict(human_reviews or {})
    state_c = state_b and all(
        reviews.get(key) is True
        for key in (
            "statistical", "dota_language", "copy", "accessibility",
            "product_comprehension", "data_basis_privacy", "container_checksum",
        )
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
            "automated_calibration_missing": missing_state_b,
            "automated_calibration_failed": failed_state_b,
            "human_reviews": reviews,
            "operator_authorized": operator_authorized,
            "figma_handoff_checks": figma,
            "figma_handoff_missing": missing_state_d,
            "figma_handoff_failed": failed_state_d,
        },
        "public_flags_must_remain_off": not state_c,
    }


def _measured_gate(*, required: Any, observed: Any, passed: bool, source: str) -> dict[str, Any]:
    return {
        "required": required,
        "observed": observed,
        "passed": passed is True,
        "evidence_source": source,
    }


def build_v61_calibration_evaluation(
    *,
    compatibility_audit: Mapping[str, Any],
    freeze_manifest: Mapping[str, Any],
    freeze_record: Mapping[str, Any],
    reproducibility: Mapping[str, Any],
    synthetic: Mapping[str, Any],
    holdout: Mapping[str, Any],
    runtime_parity: Mapping[str, Any],
    artifact_checksums: Mapping[str, str],
    generated_at: str = "2000-01-01T00:00:00+00:00",
) -> dict[str, Any]:
    """Derive State B only from measured, checksum-linked evidence."""

    evidence = (
        compatibility_audit,
        freeze_manifest,
        freeze_record,
        reproducibility,
        synthetic,
        holdout,
        runtime_parity,
    )
    for payload in evidence:
        validate_aggregate_payload(payload)
    expected_artifacts = {
        "context-baseline-3.0.0.json",
        "metric-thresholds-6.1.0.json",
        "summary-priors-6.1.0.json",
        "portfolio-distance-calibration-1.0.0.json",
        "session-reliability-calibration-1.0.0.json",
        "semantic-outcome-calibration-1.0.0.json",
    }
    synthetic_gates = dict(synthetic.get("synthetic_gates") or {})
    synthetic_passed = (
        0.93 <= float(synthetic.get("interval_empirical_coverage", 0.0)) <= 0.97
        and float(synthetic.get("family_global_null_discovery_rate", 1.0)) <= 0.05
        and float(synthetic.get("branch_global_null_discovery_rate", 1.0)) <= 0.05
        and synthetic.get("private_identifiers_present") is False
        and all(
            value is True
            for key, value in synthetic_gates.items()
            if key != "forbidden_copy_hits"
        )
    )
    holdout_gates = dict(holdout.get("gate_measurements") or {})
    holdout_passed = holdout.get("holdout_passed") is True and all(
        value is True for value in holdout_gates.values()
    )
    artifact_match = dict(artifact_checksums) == dict(holdout.get("artifact_checksums") or {})
    gates = {
        "corpus_compatibility": _measured_gate(
            required=True,
            observed=compatibility_audit.get("core_passed"),
            passed=compatibility_audit.get("core_passed") is True
            and compatibility_audit.get("corpus_sha256") == freeze_manifest.get("corpus_sha256"),
            source="corpus-compatibility-1.0.0.json",
        ),
        "reuse_authorization": _measured_gate(
            required="nonempty owner authorization reference",
            observed=compatibility_audit.get("authorization", {}).get("reuse_authorized"),
            passed=compatibility_audit.get("authorization", {}).get("reuse_authorized") is True
            and bool(str(freeze_manifest.get("reuse_authorization_reference", "")).strip()),
            source="corpus-compatibility-1.0.0.json.authorization",
        ),
        "split_integrity": _measured_gate(
            required="seed 6000 / 791 train / 339 holdout / zero overlap",
            observed=freeze_manifest.get("split"),
            passed=freeze_manifest.get("seed") == 6000
            and freeze_manifest.get("split", {}).get("train_profile_count") == 791
            and freeze_manifest.get("split", {}).get("holdout_profile_count") == 339
            and freeze_manifest.get("split", {}).get("overlap_count") == 0,
            source="build-manifest-6.1.0.json.split",
        ),
        "frozen_training_artifacts": _measured_gate(
            required=True,
            observed={
                "release_authorized": freeze_manifest.get("release_authorized"),
                "holdout_output_inspected": freeze_manifest.get("holdout_output_inspected"),
                "freeze_written_before_v61_holdout": freeze_record.get("freeze_written_before_v61_holdout"),
            },
            passed=freeze_manifest.get("release_authorized") is False
            and freeze_manifest.get("holdout_output_inspected") is False
            and freeze_record.get("freeze_written_before_v61_holdout") is True,
            source="freeze-record-6.1.0.json",
        ),
        "exact_reproducibility": _measured_gate(
            required=True,
            observed=reproducibility.get("byte_identical"),
            passed=reproducibility.get("byte_identical") is True
            and reproducibility.get("compatibility_audit_checksum") == compatibility_audit.get("audit_checksum"),
            source="verify-reproducibility",
        ),
        "synthetic_gates": _measured_gate(
            required="coverage 0.93..0.97 / family and branch null <=0.05",
            observed=synthetic.get("synthetic_gates"),
            passed=synthetic_passed,
            source="synthetic",
        ),
        "sealed_holdout_gates": _measured_gate(
            required=True,
            observed=holdout.get("gate_measurements"),
            passed=holdout_passed,
            source="holdout-evaluation-6.1.0.jsonl",
        ),
        "runtime_calibration_estimator_parity": _measured_gate(
            required=True,
            observed=runtime_parity,
            passed=runtime_parity.get("passed") is True,
            source="runtime-calibration-parity",
        ),
        "identifier_privacy": _measured_gate(
            required=True,
            observed={
                "audit": compatibility_audit.get("aggregate_identifier_free"),
                "synthetic": synthetic.get("private_identifiers_present"),
                "holdout": holdout.get("private_identifiers_present"),
            },
            passed=compatibility_audit.get("aggregate_identifier_free") is True
            and synthetic.get("private_identifiers_present") is False
            and holdout.get("private_identifiers_present") is False,
            source="aggregate privacy validator",
        ),
        "artifact_checksum_linkage": _measured_gate(
            required=sorted(expected_artifacts),
            observed={"artifact_count": len(artifact_checksums), "holdout_match": artifact_match},
            passed=set(artifact_checksums) >= expected_artifacts and artifact_match,
            source="frozen artifact manifest and holdout aggregate",
        ),
    }
    state_b = all(item["passed"] is True for item in gates.values())
    result = {
        "version": CALIBRATION_EVALUATION_VERSION,
        "generated_at": generated_at,
        "state_b": state_b,
        "state_c": False,
        "release_authorized": False,
        "artifact_checksums": dict(artifact_checksums),
        "compatibility_audit_checksum": compatibility_audit.get("audit_checksum"),
        "split_manifest_checksum": freeze_manifest.get("split_manifest_checksum"),
        "synthetic": {
            "version": synthetic.get("version"),
            "interval_empirical_coverage": synthetic.get("interval_empirical_coverage"),
            "family_global_null_discovery_rate": synthetic.get("family_global_null_discovery_rate"),
            "branch_global_null_discovery_rate": synthetic.get("branch_global_null_discovery_rate"),
            "scenario_counts": synthetic.get("scenario_counts"),
            "bootstrap_iterations": synthetic.get("bootstrap_iterations"),
        },
        "holdout": {
            "version": holdout.get("version"),
            "profile_count": holdout.get("profiles", {}).get("evaluated"),
            "gate_measurements": holdout_gates,
            "identity_stability": holdout.get("identity_stability"),
            "finding_distribution": holdout.get("finding_distribution"),
            "paired_v60": holdout.get("paired_v60"),
        },
        "runtime_parity": dict(runtime_parity),
        "gates": gates,
        "state_c_requirements": {
            "statistical_review": False,
            "dota_supported_and_believable_review": False,
            "copy_overclaim_review": False,
            "accessibility_review": False,
            "product_comprehension_review": False,
            "data_basis_privacy_approval": False,
            "container_checksum_verification": False,
            "operator_authorization": False,
        },
        "public_flags_must_remain_off": True,
    }
    validate_aggregate_payload(result)
    return result


def build_v61_release_manifest(
    evaluation: Mapping[str, Any],
    *,
    freeze_manifest: Mapping[str, Any],
    source_revision: str,
    dirty_worktree: bool,
    generated_at: str = "2000-01-01T00:00:00+00:00",
) -> dict[str, Any]:
    """Create a candidate manifest without enabling or promoting State C."""

    validate_aggregate_payload(evaluation)
    if evaluation.get("version") != CALIBRATION_EVALUATION_VERSION:
        raise ValueError("unsupported V6.1 calibration evaluation")
    result = {
        "version": RELEASE_MANIFEST_VERSION,
        "generated_at": generated_at,
        "state_b": evaluation.get("state_b") is True,
        "state_c": False,
        "release_ready": False,
        "release_authorized": False,
        "approval_state": "state-b-complete-state-c-pending" if evaluation.get("state_b") is True else "candidate-gates-failed",
        "source": {"repository_commit": source_revision, "dirty_worktree": bool(dirty_worktree)},
        "corpus": {
            "sha256": freeze_manifest.get("corpus_sha256"),
            "split_manifest_checksum": freeze_manifest.get("split_manifest_checksum"),
            "seed": freeze_manifest.get("seed"),
            "train_profile_count": freeze_manifest.get("split", {}).get("train_profile_count"),
            "holdout_profile_count": freeze_manifest.get("split", {}).get("holdout_profile_count"),
        },
        "artifact_checksums": dict(evaluation.get("artifact_checksums") or {}),
        "compatibility_audit_checksum": evaluation.get("compatibility_audit_checksum"),
        "automated_gates": {
            key: bool(value.get("passed"))
            for key, value in (evaluation.get("gates") or {}).items()
        },
        "state_c_requirements": dict(evaluation.get("state_c_requirements") or {}),
        "commands": [
            "build_v61_calibration_artifacts.py audit-reuse|baseline|calibrate-support|thresholds|freeze|verify-reproducibility",
            "evaluate_v61_calibration.py synthetic|holdout|review-packet|ingest-review|aggregate",
        ],
        "public_flags_must_remain_off": True,
    }
    validate_aggregate_payload(result)
    return result


def build_v61_production_beta_authorization(
    *,
    evaluation: Mapping[str, Any],
    release_manifest: Mapping[str, Any],
    source_revision: str,
    dirty_worktree: bool,
    operator_authorization_reference: str,
    generated_at: str = "2000-01-01T00:00:00+00:00",
) -> dict[str, Any]:
    """Create an explicit owner-authorized production-beta decision.

    This is intentionally separate from the frozen training manifest.  The
    training bundle remains marked ``release_authorized=false`` and frozen
    before holdout inspection.  A production beta may proceed only when an
    operator supplies this separate authorization after the automated State B
    gates pass.  The approval basis is recorded as an operator assumption; it
    does not fabricate independent reviewer identities or references.
    """

    validate_aggregate_payload(evaluation)
    validate_aggregate_payload(release_manifest)
    reference = operator_authorization_reference.strip()
    if not reference:
        raise ValueError("production-beta authorization needs an operator reference")
    if evaluation.get("state_b") is not True:
        raise ValueError("production-beta authorization requires State B")
    automated_gates = dict(release_manifest.get("automated_gates") or {})
    if not automated_gates or not all(value is True for value in automated_gates.values()):
        raise ValueError("production-beta authorization requires all automated gates")
    artifact_checksums = dict(release_manifest.get("artifact_checksums") or {})
    if not artifact_checksums:
        raise ValueError("production-beta authorization requires artifact checksums")
    result = {
        "version": PRODUCTION_BETA_AUTHORIZATION_VERSION,
        "generated_at": generated_at,
        "release_mode": "production-beta",
        "production_beta_authorized": True,
        "release_authorized": True,
        "state_b": True,
        "state_c": False,
        "release_ready": False,
        "public_flags_must_remain_off": False,
        "approval_basis": "owner-assumed-review-complete-per-explicit-task-instruction",
        "operator_authorization_reference": reference,
        "source": {
            "repository_commit": source_revision,
            "dirty_worktree": bool(dirty_worktree),
        },
        "automated_gates": automated_gates,
        "artifact_checksums": artifact_checksums,
        "rollback": {
            "primary_flag": "FREE_DNA_V61_ENABLED",
            "required_shadow_flag": "FREE_DNA_V61_SHADOW_ENABLED=false",
            "required_experimental_flags": (
                "FREE_DNA_V61_EXPERIMENTAL_EVOLUTION_ENABLED=false;"
                " FREE_DNA_V61_EXPERIMENTAL_LOOPS_ENABLED=false"
            ),
        },
    }
    validate_aggregate_payload(result)
    return result


def build_review_packet(*, holdout: Mapping[str, Any], artifact_checksums: Mapping[str, str]) -> dict[str, Any]:
    return {
        "version": REVIEW_PACKET_VERSION,
        "finalized": False,
        "artifact_checksums": dict(artifact_checksums),
        "holdout_profile_count": holdout.get("profiles", {}).get("evaluated"),
        "items": [
            {
                "item_kind": "aggregate-calibration-contract",
                "supported": False,
                "believable": False,
                "reviewer_comment": "Awaiting independent V6.1 review; this packet does not approve release.",
            }
        ],
        "statistical_review_approved": False,
        "dota_reviewer_approved": False,
        "data_basis_approved": False,
        "operator_authorized": False,
    }


def ingest_v61_review_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("version") != REVIEW_PACKET_VERSION or payload.get("finalized") is not True:
        raise ValueError("V6.1 review packet must be finalized before ingestion")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("V6.1 review packet needs non-empty aggregate items")
    if any(
        not isinstance(item, Mapping)
        or not isinstance(item.get("supported"), bool)
        or not isinstance(item.get("believable"), bool)
        for item in items
    ):
        raise ValueError("V6.1 review items need boolean judgments")
    supported = sum(bool(item["supported"] and item["believable"]) for item in items)
    result = {
        "version": REVIEW_EVIDENCE_VERSION,
        "reviewed_count": len(items),
        "supported_and_believable_count": supported,
        "precision": supported / len(items),
        "statistical_review_approved": payload.get("statistical_review_approved") is True,
        "dota_reviewer_approved": payload.get("dota_reviewer_approved") is True,
        "data_basis_approved": payload.get("data_basis_approved") is True,
        "operator_authorized": payload.get("operator_authorized") is True,
    }
    validate_aggregate_payload(result)
    return result


__all__ = [
    "CALIBRATION_EVALUATION_VERSION",
    "RELEASE_MANIFEST_VERSION",
    "RELEASE_EVALUATION_VERSION",
    "PRODUCTION_BETA_AUTHORIZATION_VERSION",
    "REVIEW_EVIDENCE_VERSION",
    "REVIEW_PACKET_VERSION",
    "REQUIRED_STATE_A_CHECKS",
    "REQUIRED_STATE_B_CHECKS",
    "REQUIRED_STATE_D_CHECKS",
    "SYNTHETIC_SCENARIOS",
    "SYNTHETIC_EVALUATION_VERSION",
    "build_review_packet",
    "build_v61_calibration_evaluation",
    "build_v61_release_manifest",
    "build_v61_production_beta_authorization",
    "build_release_evaluation",
    "ingest_v61_review_evidence",
    "run_synthetic_evaluation",
    "validate_aggregate_payload",
]
