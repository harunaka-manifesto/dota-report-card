from __future__ import annotations

import re

import pytest
from app.analysis.service import _job_diagnostic_question
from app.core.config import Settings
from app.features.summary_models import SummaryMatchFeature
from app.ingestion.summary_history_contract import request_manifest
from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS
from app.player_analysis_v61.copy import SEMANTIC_COPY_REGISTRY
from app.player_analysis_v61.family_statistics import v61_branch_p_values
from app.player_analysis_v61.hierarchical import hierarchical_qualification
from app.player_analysis_v61.identity import compose_identity_slots
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_CATALOG
from app.reports.dna_assembly_v61 import _protect_deep_handoffs
from app.storage.repository import InMemoryRepository


def test_hierarchy_never_tests_branches_under_a_failed_family() -> None:
    family_p = {family: 1.0 for family in FINDING_FAMILY_KEYS}
    branch_p = {family: {f"{family}:branch": 0.0001} for family in FINDING_FAMILY_KEYS}

    result = hierarchical_qualification(family_p, branch_p)

    assert all(not family["qualified"] for family in result.values())
    assert all(
        branch["adjusted_q_value"] == 1.0 and not branch["qualified"]
        for family in result.values()
        for branch in family["branches"].values()
    )


def test_hierarchy_rejects_any_root_set_other_than_the_frozen_five() -> None:
    with pytest.raises(ValueError, match="exactly five family roots"):
        hierarchical_qualification({"pool_shape": 0.01}, {})


def test_every_public_branch_gets_a_predeclared_statistic() -> None:
    branches = v61_branch_p_values(
        portfolio_shape={},
        transfer={},
        result_response={},
        session_curve={},
        involvement={},
        death_exposure={},
    )
    expected = {
        definition.semantic_outcome_key
        for definition in SEMANTIC_OUTCOME_CATALOG
        if definition.rollout_status == "public_candidate"
    }

    assert {key for family in branches.values() for key in family} == expected
    assert len(expected) == 25
    assert all(0.0 <= value <= 1.0 for family in branches.values() for value in family.values())


def test_copy_registry_has_no_registered_forbidden_public_token() -> None:
    for definition in SEMANTIC_OUTCOME_CATALOG:
        copy = SEMANTIC_COPY_REGISTRY[definition.semantic_outcome_key]
        public_text = f"{copy.claim} {copy.interpretation} {copy.evidence_label}".casefold()
        for token in definition.forbidden_tokens:
            assert re.search(rf"\b{re.escape(token.casefold())}\b", public_text) is None


def test_identity_slots_require_stability_and_only_use_qualified_twists() -> None:
    shape = {"chronological_thirds": [{"match_count": 12}, {"match_count": 12}, {"match_count": 5}]}
    findings = [
        {
            "family": "transfer",
            "published": True,
            "confidence": "high",
            "semantic_outcome_key": "clean_transfer",
            "claim_contract": {"claim": "Transfer held in supported bands."},
            "evidence_refs": ["finding:transfer"],
        }
    ]
    slots = compose_identity_slots(
        {"headline": "A stable annual summary.", "confidence": "high", "evidence_refs": []},
        findings,
        {},
        shape,
    )

    assert slots["primary"]["kind"] == "PRIMARY"
    assert slots["twist"]["kind"] == "TWIST"
    assert all(slots["compatibility_checks"].values())

    findings[0]["published"] = False
    suppressed = compose_identity_slots(
        {"headline": "A stable annual summary.", "confidence": "high", "evidence_refs": []},
        findings,
        {},
        shape,
    )
    assert suppressed["twist"] is None


def test_request_manifest_contains_no_account_or_secret_material() -> None:
    manifest = request_manifest()
    encoded_parameters = repr(manifest["request_parameters"]).casefold()

    assert manifest["physical_request_count"] == 1
    assert manifest["rank_or_mmr_used"] is False
    assert "account_id" not in encoded_parameters
    assert "api_key" not in encoded_parameters
    assert "authorization" not in encoded_parameters


def test_all_v61_feature_flags_default_off() -> None:
    settings = Settings()

    assert settings.free_dna_v61_enabled is False
    assert settings.free_dna_v61_shadow_enabled is False
    assert settings.free_dna_v61_experimental_evolution_enabled is False
    assert settings.free_dna_v61_experimental_loops_enabled is False


def test_deep_handoff_moves_exact_cohorts_out_of_public_question() -> None:
    report = {
        "findings": [
            {
                "family": "post_loss_response",
                "published": True,
                "semantic_outcome_key": "one_loss_runback",
                "claim_contract": {
                    "deep_handoff": {
                        "unanswered_alternatives": ["Unobserved match context"]
                    }
                },
            }
        ],
        "diagnostic_questions": [
            {
                "id": "deep-v61-post-loss",
                "finding_family": "post_loss_response",
                "primary_hypothesis": {
                    "positive_definition": {
                        "name": "post_loss_transition",
                        "params": {"match_ids": [11, 13]},
                    },
                    "negative_definition": {
                        "name": "outside_match_id_set",
                        "params": {"match_ids": [11, 13]},
                    },
                    "control_definition": {
                        "name": "duration_bucket",
                        "params": {"bucket": "medium"},
                    },
                },
                "secondary_hypothesis": None,
            }
        ],
    }
    matches = [
        SummaryMatchFeature(
            match_id=match_id,
            start_time=1_700_000_000 + match_id,
            duration_seconds=2_100,
            hero_id=1,
            side="radiant",
            won=True,
            session_id=f"session-{match_id // 2}",
        )
        for match_id in (11, 12, 13)
    ]
    protected: dict[str, object] = {}

    _protect_deep_handoffs(
        report,
        matches,
        history_hash="history-hash",
        protected_cohorts_out=protected,
    )

    public_question = report["diagnostic_questions"][0]
    reference = public_question["protected_cohort_reference"]
    assert reference.startswith("cohort:v61:")
    assert "match_ids" not in repr(public_question)
    assert public_question["primary_hypothesis"]["positive_definition"]["params"] == {
        "cohort_reference": reference
    }
    stored = protected[reference]
    assert stored["primary"]["positive"]["match_ids"] == [11, 13]
    assert stored["primary"]["positive"]["session_ids"]


def test_protected_deep_cohort_requires_authorized_server_resolution() -> None:
    repository = InMemoryRepository()
    reference = "cohort:v61:0123456789abcdef01234567"
    report_id = repository.save_report(
        account_id=42,
        data_cutoff=100,
        model_version="free-dna-model-6.1.0",
        template_version="templates-6.1.0",
        report={
            "diagnostic_questions": [
                {
                    "id": "deep-v61-transfer",
                    "protected_cohort_reference": reference,
                }
            ]
        },
        evidence=[],
    )
    full_question = {
        "id": "deep-v61-transfer",
        "primary_hypothesis": {
            "positive_definition": {
                "name": "match_id_set",
                "params": {"match_ids": [91, 92]},
            }
        },
    }
    repository.persist_protected_cohorts(
        report_id,
        {reference: {"question": full_question}},
    )
    denied = repository.create_job(
        42,
        "42",
        "deep-diagnostics-2.1.0",
        "deep_scan",
        parent_report_id=report_id,
        diagnostic_question_id="deep-v61-transfer",
        entitlement_decision={"allowed": False},
    )
    allowed = repository.create_job(
        42,
        "42",
        "deep-diagnostics-2.1.0",
        "deep_scan",
        parent_report_id=report_id,
        diagnostic_question_id="deep-v61-transfer",
        entitlement_decision={"allowed": True},
    )

    with pytest.raises(RuntimeError, match="requires authorization"):
        _job_diagnostic_question(denied, repository)
    assert _job_diagnostic_question(allowed, repository) == full_question
    assert "match_ids" not in repr(repository.get_report(report_id))
