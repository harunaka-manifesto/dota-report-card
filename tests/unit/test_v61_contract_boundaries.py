from __future__ import annotations

import re

import pytest
from app.analysis.service import _job_diagnostic_question
from app.core.config import Settings
from app.features.summary_models import SummaryMatchFeature
from app.ingestion.summary_history_contract import request_manifest
from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS
from app.player_analysis_v6.models import _freeze
from app.player_analysis_v61.copy import SEMANTIC_COPY_REGISTRY
from app.player_analysis_v61.family_statistics import (
    v61_branch_p_values,
    v61_production_family_branch_p_values,
)
from app.player_analysis_v61.hierarchical import hierarchical_qualification
from app.player_analysis_v61.identity import compose_identity_slots
from app.player_analysis_v61.semantic_outcomes import (
    SEMANTIC_OUTCOME_CATALOG,
    SEMANTIC_OUTCOME_REGISTRY,
)
from app.reports.dna_assembly_v6 import _plain_json
from app.reports.dna_assembly_v61 import (
    _post_loss_response_statistic,
    _protect_deep_handoffs,
    _semantic_bootstrap_evidence,
)
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
    assert len(expected) == 26
    assert all(0.0 <= value <= 1.0 for family in branches.values() for value in family.values())


def test_production_family_statistics_fail_closed_without_complete_evidence() -> None:
    with pytest.raises(ValueError, match="production family evidence"):
        v61_production_family_branch_p_values(
            semantic_calibration={"branch_procedure": "qualified-family-bh"},
            bootstrap_family_samples={},
            bootstrap_branch_samples={},
        )


def test_empty_production_semantic_evidence_abstains_without_crashing() -> None:
    branches = {
        family: {
            definition.semantic_outcome_key: []
            for definition in SEMANTIC_OUTCOME_CATALOG
            if definition.rollout_status == "public_candidate" and definition.family_key == family
        }
        for family in FINDING_FAMILY_KEYS
    }
    family, branch = v61_production_family_branch_p_values(
        semantic_calibration={"branch_procedure": "qualified-family-bh"},
        bootstrap_family_samples={family: [] for family in FINDING_FAMILY_KEYS},
        bootstrap_branch_samples=branches,
    )

    assert family == {key: 1.0 for key in FINDING_FAMILY_KEYS}
    assert all(value == 1.0 for values in branch.values() for value in values.values())
    evidence = _semantic_bootstrap_evidence([{}])
    assert all(not item["available"] for item in evidence["availability"].values())


def test_post_loss_bootstrap_never_uses_finishing_as_family_evidence() -> None:
    evidence = _semantic_bootstrap_evidence([{"finishing": 0.25}, {"finishing": 0.75}])

    assert evidence["families"]["post_loss_response"] == []
    assert evidence["availability"]["post_loss_response"] == {
        "available": False,
        "requested_iterations": 2,
        "usable_iterations": 0,
    }


def test_post_loss_bootstrap_statistic_uses_session_weighted_result_states() -> None:
    sessions = [
        {
            "win": (2, 0.0),
            "one_loss": (2, 0.1),
            "two_plus_losses": (0, None),
            "win_streak": (0, None),
        }
        for _ in range(8)
    ]

    assert _post_loss_response_statistic(sessions, [1] * 8) == pytest.approx(0.1)
    assert _post_loss_response_statistic(sessions, [1] * 7 + [0]) is None


def test_public_question_projection_deeply_converts_frozen_mappings() -> None:
    frozen = _freeze({"primary": {"params": {"hero_ids": [1, 2]}}})
    plain = _plain_json(frozen)

    assert type(plain["primary"]).__name__ == "dict"
    assert type(plain["primary"]["params"]).__name__ == "dict"
    assert plain["primary"]["params"]["hero_ids"] == [1, 2]


def test_copy_registry_matches_all_registered_outcomes() -> None:
    public_claims = {
        "hidden_center": "Your pool is wider than it first looks—but it has a center.",
        "names_wide_jobs_narrow": "Your hero names cover more ground than the jobs behind them.",
        "names_narrow_jobs_wide": "A compact hero set covers a wider mix of jobs.",
        "names_changed_jobs_held": "Your hero names moved more across the year than the jobs they covered.",
        "clean_transfer": "More of your observed expression travels when the hero changes.",
        "no_transfer": "Your game changed outside your usual heroes.",
        "results_stop_first": "The result changes before your expression does.",
        "expression_stops_first": "Your expression changes before the result does.",
        "involvement_boundary": "Involvement holds farther into the hero change.",
        "exposure_boundary": "Death exposure holds farther into the hero change.",
        "localized_function_bottleneck": "The supported gap sits in one mapped job context.",
        "one_loss_runback": "After one loss, your next choice stays closer to your prior path.",
        "two_loss_switch": "After two or more losses, your next choice changes differently.",
        "result_shaped_pool": "Your next choice moves differently after wins and losses.",
        "result_invariant_response": "Your next-choice movement stays about the same after wins and losses.",
        "adjustment_without_recovery": "Your next choice changes after the result, while the next result stays unresolved.",
        "involvement_holds_exposure_moves": "Involvement holds while death exposure moves.",
        "exposure_holds_involvement_moves": "Death exposure holds while involvement moves.",
        "same_expression_different_results": "Similar summary expression can arrive with different results.",
        "different_expression_same_results": "Similar results can arrive with different summary expression.",
        "localized_variance": "More of the expression variance sits in one supported context.",
        "opening_game_signature": "Game 1 has a different supported shape from later games.",
        "gradual_session_drift": "A covered part of your expression moves as the session continues.",
        "predeclared_breakpoint": "The first clear break appears at the registered session position.",
        "selection_only_drift": "Your pool changes across a session while summary expression stays compatible.",
        "bounded_stopping_response": "Completed session endings differ after the registered result state.",
    }
    public_keys = {
        definition.semantic_outcome_key
        for definition in SEMANTIC_OUTCOME_CATALOG
        if definition.rollout_status == "public_candidate"
    }
    shadow_keys = {
        definition.semantic_outcome_key
        for definition in SEMANTIC_OUTCOME_CATALOG
        if definition.rollout_status == "shadow_only"
    }

    assert len(SEMANTIC_COPY_REGISTRY) == len(SEMANTIC_OUTCOME_REGISTRY) == 29
    assert set(SEMANTIC_COPY_REGISTRY) == set(SEMANTIC_OUTCOME_REGISTRY)
    assert set(public_claims) == public_keys
    assert {key: SEMANTIC_COPY_REGISTRY[key].claim for key in public_keys} == public_claims
    assert shadow_keys == {"hero_lifecycle", "identity_eras", "behavioral_loop"}
    assert all(SEMANTIC_OUTCOME_REGISTRY[key].share_key is None for key in shadow_keys)
    assert all(
        SEMANTIC_COPY_REGISTRY[key].neutral_variant is None
        and SEMANTIC_COPY_REGISTRY[key].insufficient_variant is None
        and SEMANTIC_COPY_REGISTRY[key].mixed_variant is None
        for key in shadow_keys
    )


def test_copy_registry_has_no_registered_forbidden_public_token() -> None:
    for definition in SEMANTIC_OUTCOME_CATALOG:
        copy = SEMANTIC_COPY_REGISTRY[definition.semantic_outcome_key]
        public_text = " ".join(
            value
            for value in (
                copy.claim,
                copy.interpretation,
                copy.evidence_label,
                copy.neutral_variant,
                copy.insufficient_variant,
                copy.mixed_variant,
            )
            if value is not None
        ).casefold()
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
                    "deep_handoff": {"unanswered_alternatives": ["Unobserved match context"]}
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


def test_protected_cohort_persistence_rolls_back_the_public_report() -> None:
    repository = InMemoryRepository()

    def fail_persist(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("private persistence failed")

    repository.persist_protected_cohorts = fail_persist  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="private persistence failed"):
        repository.save_report_with_protected_cohorts(
            account_id=42,
            data_cutoff=100,
            model_version="free-dna-model-6.1.0",
            template_version="templates-6.1.0",
            report={"schema_version": "free-dna-report-6.1.0"},
            evidence=[],
            protected_cohorts={"cohort:v61:test": {"question": {}}},
        )

    assert repository.reports == {}
    assert repository._report_private == {}
