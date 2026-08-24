from app.player_analysis_v61.calibration_evaluation import (
    REQUIRED_STATE_A_CHECKS,
    build_release_evaluation,
    run_synthetic_evaluation,
)
from app.player_analysis_v61.experimental import (
    evaluate_experimental_candidates,
    run_stationary_experimental_simulations,
)


def test_v61_synthetic_evaluation_controls_registered_nulls() -> None:
    result = run_synthetic_evaluation(seed=61, replicates=2_000)

    assert 0.93 <= result["interval_empirical_coverage"] <= 0.97
    assert result["family_global_null_discovery_rate"] <= 0.05
    assert result["branch_global_null_discovery_rate"] <= 0.05
    assert result["private_identifiers_present"] is False


def test_release_evaluation_keeps_public_release_separate_from_state_a() -> None:
    synthetic = run_synthetic_evaluation(seed=61, replicates=2_000)
    result = build_release_evaluation(
        implementation_checks={key: True for key in REQUIRED_STATE_A_CHECKS},
        synthetic=synthetic,
    )

    assert result["states"]["implementation_complete"] is True
    assert result["states"]["automated_calibration_complete"] is False
    assert result["states"]["public_release_ready"] is False
    assert result["public_flags_must_remain_off"] is True


def test_release_evaluation_rejects_partial_or_failed_state_a_manifest() -> None:
    synthetic = run_synthetic_evaluation(seed=61, replicates=2_000)
    partial = build_release_evaluation(
        implementation_checks={"canonical_one_request": True},
        synthetic=synthetic,
    )
    failed_checks = {key: True for key in REQUIRED_STATE_A_CHECKS}
    failed_checks["protected_deep_cohort_authorization"] = False
    failed = build_release_evaluation(
        implementation_checks=failed_checks,
        synthetic=synthetic,
    )

    assert partial["states"]["implementation_complete"] is False
    assert "v60_compatibility" in partial["gates"]["implementation_missing"]
    assert failed["states"]["implementation_complete"] is False
    assert failed["gates"]["implementation_failed"] == [
        "protected_deep_cohort_authorization"
    ]


def test_figma_handoff_state_is_independent_and_fail_closed() -> None:
    synthetic = run_synthetic_evaluation(seed=61, replicates=10)
    result = build_release_evaluation(
        implementation_checks={},
        synthetic=synthetic,
        figma_handoff_checks={
            "brief_exists": True,
            "implemented_contract_references": True,
            "unresolved_inputs_listed": True,
            "future_agent_definition_of_done": True,
        },
    )

    assert result["states"]["implementation_complete"] is False
    assert result["states"]["figma_documentation_handoff_ready"] is True


def test_experimental_candidates_cannot_serialize_publicly() -> None:
    rows = [
        {
            "match_id": index,
            "start_time": 1_700_000_000 + index * 5_000,
            "hero_id": 1 + index % 4,
            "won": index % 2 == 0,
            "session_id": f"s{index // 2}",
        }
        for index in range(240)
    ]
    disabled = evaluate_experimental_candidates(
        rows, evolution_enabled=False, loops_enabled=False
    )
    enabled = evaluate_experimental_candidates(
        rows, evolution_enabled=True, loops_enabled=True
    )

    assert disabled["hero_lifecycle"]["status"] == "unavailable"
    assert enabled["hero_lifecycle"]["status"] == "experimental"
    assert enabled["public_serialization_allowed"] is False
    assert enabled["identity_eras"]["selection_corrected"] is False
    assert enabled["behavioral_loops"]["discovery_verification_complete"] is True
    assert enabled["promotion_requires_separate_decision"] is True


def test_stationary_experimental_simulation_records_false_positive_rates() -> None:
    result = run_stationary_experimental_simulations(seed=6105, replicates=50)

    assert result["false_era_rate"] <= 0.05
    assert result["false_loop_rate"] <= 0.05
