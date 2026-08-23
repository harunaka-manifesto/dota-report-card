from __future__ import annotations

import copy

import pytest
from app.player_analysis_v6.calibration_evaluation import (
    CalibrationEvaluationError,
    atomic_json,
    build_evaluation_artifact,
    ingest_review_evidence,
    promote_release,
    validate_aggregate_payload,
)


def _synthetic(*, coverage: float = 0.95, fdr: float = 0.04) -> dict:
    return {
        "version": "v6-synthetic-evaluation-1.0.0",
        "seed": 6000,
        "bootstrap_iterations": 2000,
        "artifact_checksums": {"baseline_sha256": "a", "threshold_sha256": "b"},
        "scenario_counts": {"null_no_effect": 20},
        "interval_empirical_coverage": {"observed": coverage, "covered": 95, "total": 100},
        "family_fdr": {"observed": fdr, "null_replicates": 100},
    }


def _holdout(*, nonblank: float = 0.85, agreement: float | None = 0.82) -> dict:
    return {
        "version": "v6-holdout-evaluation-1.0.0",
        "artifact_checksums": {"baseline_sha256": "a", "threshold_sha256": "b"},
        "corpus": {"profile_count": 1130, "train_profile_count": 791, "holdout_profile_count": 339, "mmr_used": False},
        "nonblank_identity": {"observed": nonblank, "eligible_profiles": 339},
        "split_half_agreement": {"observed": agreement, "comparable_zones": 100},
        "copy_safety": {"violations": 0, "strings_scanned": 10_000},
        "free_cost": {"violations": 0, "reports_checked": 339},
        "abstention": {},
        "per_metric_coverage": {},
        "baseline_fallback": {},
    }


def _review() -> dict:
    return {
        "version": "v6-review-evidence-1.0.0",
        "dota_reviewer": {"precision": 0.95, "reviewed_count": 40, "approved": True},
        "statistical_review": {"approved": True},
        "data_basis": {"approved": True},
    }


def test_evaluation_readiness_is_derived_from_all_gates() -> None:
    pending = build_evaluation_artifact(_synthetic(), _holdout())
    assert pending["status"] == "external-review-required"
    assert pending["release_ready"] is False

    ready = build_evaluation_artifact(_synthetic(), _holdout(), _review())
    assert ready["status"] == "release-ready"
    assert ready["release_ready"] is True
    assert all(item["passed"] for item in ready["gates"].values())


def test_failed_or_missing_automated_measurement_fails_closed() -> None:
    failed = build_evaluation_artifact(_synthetic(coverage=0.90), _holdout(agreement=None), _review())
    assert failed["status"] == "automated-gates-failed"
    assert failed["gates"]["interval_empirical_coverage"]["passed"] is False
    assert failed["gates"]["split_half_agreement"]["passed"] is False


def test_smoke_evidence_cannot_be_aggregated_for_release() -> None:
    synthetic = _synthetic()
    synthetic["smoke"] = True
    with pytest.raises(CalibrationEvaluationError, match="smoke evidence"):
        build_evaluation_artifact(synthetic, _holdout(), _review())


def test_evidence_checksums_must_match() -> None:
    holdout = _holdout()
    holdout["artifact_checksums"]["threshold_sha256"] = "different"
    with pytest.raises(CalibrationEvaluationError, match="checksums"):
        build_evaluation_artifact(_synthetic(), holdout)


def test_review_ingestion_computes_precision_and_never_self_approves() -> None:
    payload = {
        "version": "v6-review-evidence-1.0.0",
        "judgments": [
            {"supported": True, "believable": True},
            {"supported": True, "believable": False},
        ],
        "dota_reviewer_approved": True,
        "statistical_review_approved": False,
        "data_basis_approved": True,
    }
    result = ingest_review_evidence(payload)
    assert result["dota_reviewer"]["precision"] == 0.5
    assert result["dota_reviewer"]["approved"] is False
    assert result["statistical_review"]["approved"] is False


def test_completed_private_review_packet_can_be_ingested_directly() -> None:
    payload = {
        "version": "v6-private-review-packet-1.0.0",
        "items": [
            {"review_item_id": "review-0001", "supported": True, "believable": True},
            {"review_item_id": "review-0002", "supported": True, "believable": True},
        ],
        "dota_reviewer_approved": True,
        "dota_reviewer_reference": "external-review-record",
        "statistical_review_approved": True,
        "statistical_reviewer_reference": "statistics-review-record",
        "data_basis_approved": True,
        "data_basis_approver_reference": "data-basis-record",
    }
    result = ingest_review_evidence(payload)
    assert result["dota_reviewer"]["precision"] == 1.0
    assert result["dota_reviewer"]["approved"] is True
    assert result["statistical_review"]["approved"] is True
    assert result["data_basis"]["approved"] is True


@pytest.mark.parametrize("field", ["profile_id", "match_ids", "mmr", "rank_tier"])
def test_aggregate_artifacts_reject_private_or_rank_dimensions(field: str) -> None:
    payload = copy.deepcopy(_synthetic())
    payload[field] = "forbidden"
    with pytest.raises(CalibrationEvaluationError):
        validate_aggregate_payload(payload)


def test_promotion_refuses_external_review_pending_candidate(tmp_path) -> None:
    evaluation = build_evaluation_artifact(_synthetic(), _holdout())
    manifest = {
        "version": "free-dna-v6-release-manifest-6.0.0",
        "release_ready": False,
        "mmr_used": False,
        "automated_gates": {"external_review": False},
    }
    atomic_json(tmp_path / "calibration-evaluation-6.0.0.json", evaluation)
    atomic_json(tmp_path / "release-manifest-6.0.0.json", manifest)
    with pytest.raises(CalibrationEvaluationError, match="automated and human gate"):
        promote_release(tmp_path, tmp_path / "promoted")
