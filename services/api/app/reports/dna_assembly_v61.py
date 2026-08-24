"""Additive public projection for the Free DNA V6.1 generation path."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from app.analysis.budget import DataCostLedger
from app.hypotheses.models import MatchPredicate
from app.ingestion.summary_history_contract import CanonicalSummaryHistory, request_manifest
from app.player_analysis_v61.copy import SEMANTIC_COPY_REGISTRY
from app.player_analysis_v61.estimators import (
    continuous_transfer,
    duration_context_involvement,
    information_weighted_consistency,
    overdispersed_death_exposure,
    stabilized_finishing,
)
from app.player_analysis_v61.family_statistics import v61_branch_p_values, v61_family_p_values
from app.player_analysis_v61.hierarchical import hierarchical_qualification
from app.player_analysis_v61.identity import compose_identity_slots
from app.player_analysis_v61.portfolio_shape import build_portfolio_shape
from app.player_analysis_v61.relationships import result_response_summary, session_position_curve
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_REGISTRY
from app.player_analysis_v61.versions import REPORT_VERSION, default_versions_v61
from app.reports.dna_assembly_v6 import assemble_free_dna_report_v6

REPORT_SCHEMA_VERSION_V61 = REPORT_VERSION


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, frozenset)):
        return [_plain(item) for item in value]
    return value


def _semantic_key(
    family: str,
    finding: Mapping[str, Any],
    portfolio_shape: Mapping[str, Any],
    transfer: Mapping[str, Any],
    result_response: Mapping[str, Any],
    involvement: Mapping[str, Any],
    death_exposure: Mapping[str, Any],
) -> str:
    if family == "pool_shape":
        hero_jsd = float(portfolio_shape.get("hero_jsd_first_to_last", 0.0))
        job_jsd = float(portfolio_shape.get("job_jsd_first_to_last", 0.0))
        top = portfolio_shape.get("top_shares", {})
        if hero_jsd >= 0.10 and job_jsd <= 0.05:
            return "names_changed_jobs_held"
        if float(top.get("top_1", 0.0)) >= 0.25:
            return "hidden_center"
        hero_count = float(portfolio_shape.get("shannon_effective_heroes", 0.0))
        job_count = float(portfolio_shape.get("shannon_effective_jobs", 0.0))
        return "names_wide_jobs_narrow" if hero_count > job_count else "names_narrow_jobs_wide"
    if family == "transfer":
        key = str(transfer.get("semantic_subtype", "clean_transfer"))
        return key if key in SEMANTIC_OUTCOME_REGISTRY else "clean_transfer"
    if family == "post_loss_response":
        states = result_response.get("states", {})
        one_loss = states.get("one_loss", {})
        two_loss = states.get("two_plus_losses", {})
        if two_loss.get("available") and one_loss.get("available"):
            first = one_loss.get("mean_distance_movement")
            second = two_loss.get("mean_distance_movement")
            if first is not None and second is not None and abs(float(second) - float(first)) >= 0.10:
                return "two_loss_switch"
        if finding.get("direction") in {"neutral", "unknown"}:
            return "result_invariant_response"
        return "one_loss_runback"
    if family == "combat_expression":
        involvement_value = involvement.get("estimate")
        exposure_value = death_exposure.get("estimate")
        involvement_holds = (
            involvement_value is not None and abs(float(involvement_value)) <= 0.08
        )
        exposure_holds = exposure_value is not None and abs(float(exposure_value)) <= 0.35
        if involvement_holds and not exposure_holds:
            return "involvement_holds_exposure_moves"
        if exposure_holds and not involvement_holds:
            return "exposure_holds_involvement_moves"
        if involvement_holds and exposure_holds:
            return "same_expression_different_results"
        return "localized_variance"
    direction = str(finding.get("direction", "unknown"))
    return {
        "rise": "gradual_session_drift",
        "positive": "gradual_session_drift",
        "fade": "predeclared_breakpoint",
        "negative": "predeclared_breakpoint",
        "neutral": "selection_only_drift",
    }.get(direction, "opening_game_signature")


def _protected_cohort_reference(family: str, history_hash: str) -> str:
    digest = hashlib.sha256(f"{history_hash}:{family}".encode()).hexdigest()
    return f"cohort:v61:{digest[:24]}"


def _value(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, Mapping) else getattr(item, key, None)


def _cohort_groups(hypothesis: Mapping[str, Any], matches: Sequence[Any]) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for role in ("positive", "negative", "control"):
        raw = hypothesis.get(f"{role}_definition")
        if not isinstance(raw, Mapping):
            continue
        params = raw.get("params")
        if not isinstance(params, Mapping):
            params = {}
        predicate = MatchPredicate(str(raw.get("name") or ""), dict(params))
        selected = [match for match in matches if predicate.matches(match)]
        groups[role] = {
            "definition": deepcopy(dict(raw)),
            "match_ids": sorted(
                {
                    int(match_id)
                    for match in selected
                    if (match_id := _value(match, "match_id")) is not None
                }
            ),
            "session_ids": sorted(
                {
                    str(session_id)
                    for match in selected
                    if (session_id := _value(match, "session_id")) not in (None, "")
                }
            ),
        }
    return groups


def _redact_match_ids(value: Any, cohort_reference: str) -> Any:
    if isinstance(value, Mapping):
        redacted = {
            str(key): _redact_match_ids(item, cohort_reference)
            for key, item in value.items()
            if str(key) != "match_ids"
        }
        if "match_ids" in value:
            redacted["cohort_reference"] = cohort_reference
        return redacted
    if isinstance(value, list):
        return [_redact_match_ids(item, cohort_reference) for item in value]
    return value


def _protect_deep_handoffs(
    report: dict[str, Any],
    matches: Sequence[Any],
    *,
    history_hash: str,
    protected_cohorts_out: dict[str, Any] | None,
) -> None:
    """Move exact Deep cohorts out of the immutable public snapshot."""

    findings = {
        str(item["family"]): item
        for item in report["findings"]
        if item.get("published") and item.get("claim_contract")
    }
    for question in report["diagnostic_questions"]:
        family = str(question["finding_family"])
        finding = findings.get(family)
        if finding is None:
            continue
        reference = _protected_cohort_reference(family, history_hash)
        full_question = deepcopy(question)
        record = {
            "version": "protected-deep-cohort-1.0.0",
            "cohort_reference": reference,
            "family": family,
            "semantic_outcome_key": finding.get("semantic_outcome_key"),
            "history_hash": history_hash,
            "question": full_question,
            "primary": _cohort_groups(
                full_question.get("primary_hypothesis") or {}, matches
            ),
            "secondary": _cohort_groups(
                full_question.get("secondary_hypothesis") or {}, matches
            ),
            "unanswered_alternatives": list(
                finding["claim_contract"]["deep_handoff"]["unanswered_alternatives"]
            ),
        }
        if protected_cohorts_out is not None:
            protected_cohorts_out[reference] = record
        public_question = _redact_match_ids(question, reference)
        public_question["protected_cohort_reference"] = reference
        question.clear()
        question.update(public_question)


def _set_page_observed(page: dict[str, Any], observed: Mapping[str, Any]) -> None:
    page["observed"] = _plain(observed)
    page["content"] = dict(page.get("content") or {})
    page["content"]["observed"] = _plain(observed)


def _refresh_public_surfaces(report: dict[str, Any]) -> None:
    """Remove inherited V6 branches that did not pass the V6.1 hierarchy."""

    published = [finding for finding in report["findings"] if finding.get("published")]
    allowed_families = {str(finding["family"]) for finding in published}
    report["diagnostic_questions"] = [
        question
        for question in report["diagnostic_questions"]
        if question.get("finding_family") in allowed_families
    ][:3]
    report["share_candidates"] = [
        candidate
        for candidate in report["share_candidates"]
        if not str(candidate.get("id", "")).startswith("finding:")
        or str(candidate.get("id", "")).split(":", 1)[-1] in allowed_families
    ][:3]
    pages = {str(page.get("id")): page for page in report["pages"]}
    identity_page = pages.get("identity-reveal")
    if identity_page is not None:
        _set_page_observed(
            identity_page,
            {"elements": report["elements"], "identity": report["identity_summary"]["slots"]},
        )
    combat = next(
        (finding for finding in published if finding["family"] == "combat_expression"),
        None,
    )
    combat_page = pages.get("combat-expression")
    if combat_page is not None:
        combat_page["available"] = combat is not None
        _set_page_observed(combat_page, {"finding": combat})
    for page_id, finding in (
        ("strongest-finding", published[0] if published else None),
        ("secondary-finding", published[1] if len(published) > 1 else None),
    ):
        page = pages.get(page_id)
        if page is not None:
            page["available"] = finding is not None
            if finding is None:
                page["body"] = "No additional family cleared the registered evidence gates."
            _set_page_observed(page, {"finding": finding})
    recommendation_page = pages.get("recommendation")
    if recommendation_page is not None:
        recommendations = [
            finding["claim_contract"]["recommendation"]
            for finding in published
            if finding.get("claim_contract", {}).get("recommendation") is not None
        ]
        recommendation_page["available"] = bool(recommendations)
        _set_page_observed(recommendation_page, {"recommendations": recommendations})
    deep_page = pages.get("deep-diagnostic")
    if deep_page is not None:
        deep_page["available"] = bool(report["diagnostic_questions"])
        _set_page_observed(
            deep_page,
            {"diagnostic_questions": report["diagnostic_questions"]},
        )


def _patch_element(
    element: dict[str, Any],
    *,
    involvement: Mapping[str, Any],
    finishing: Mapping[str, Any],
    death_exposure: Mapping[str, Any],
    transfer: Mapping[str, Any],
    consistency: Mapping[str, Any],
) -> None:
    key = element.get("key")
    overlay = {
        "involvement": involvement,
        "finishing": finishing,
        "death_exposure": death_exposure,
        "transfer": transfer,
        "consistency": consistency,
    }.get(str(key))
    if overlay is not None:
        element["estimate"] = overlay.get("estimate")
        element["status"] = overlay.get("status", element.get("status"))
        element["limitations"] = list(overlay.get("limitations", []))
        element["interval"] = (
            {
                "lower": overlay["interval"][0],
                "upper": overlay["interval"][1],
                "level": 0.95,
            }
            if overlay.get("interval")
            else None
        )
        element["evidence_refs"] = list(
            dict.fromkeys([*element.get("evidence_refs", []), f"supporting:{key}:v61"])
        )
        element["sample_size"] = int(overlay.get("matches", element.get("sample_size", 0)))
        element["independent_session_count"] = int(
            overlay.get("sessions", overlay.get("session_count", element.get("independent_session_count", 0)))
        )
        element["coverage"] = float(overlay.get("coverage", element.get("coverage", 0.0)))
    element["estimator_version"] = {
        "breadth": "breadth-shannon-plus-shape-1.0.0",
        "toolkit": "toolkit-fractional-taxonomy-1.0.0",
        "involvement": "involvement-duration-context-2.0.0",
        "finishing": "finishing-beta-binomial-1.0.0",
        "death_exposure": "death-exposure-overdispersed-2.0.0",
        "transfer": "portfolio-distance-frontier-1.0.0",
        "consistency": "consistency-information-weighted-1.0.0",
    }[str(key)]
    if key == "finishing":
        element["unit"] = "posterior kill share"
        element["sample_size"] = int(finishing.get("events", 0))
        element["independent_session_count"] = int(finishing.get("sessions", 0))
        element["zone"] = None
        element["direction"] = None


def assemble_free_dna_report_v61(
    *,
    account_id: int,
    profile: dict[str, Any],
    matches: Sequence[Any],
    canonical_history: CanonicalSummaryHistory,
    processed_matches: int,
    eligible_matches: int,
    model_version: str,
    template_version: str,
    cost_ledger: DataCostLedger | None,
    analysis_version_fingerprint: str,
    baseline_resolver: Any,
    thresholds: Mapping[str, Any],
    taxonomy_by_hero: Mapping[Any, Any] | None,
    completed_sessions: Mapping[str, bool],
    artifact_checksums: Mapping[str, str],
    shadow_enabled: bool = False,
    experimental_evolution_enabled: bool = False,
    experimental_loops_enabled: bool = False,
    protected_cohorts_out: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = assemble_free_dna_report_v6(
        account_id=account_id,
        profile=profile,
        analysis=tuple(matches),
        processed_matches=processed_matches,
        eligible_matches=eligible_matches,
        raw_payload_hash=canonical_history.audit.raw_payload_sha256,
        history_limit=None,
        model_version=model_version,
        template_version=template_version,
        cost_ledger=cost_ledger,
        analysis_version_fingerprint=analysis_version_fingerprint,
        baseline_resolver=baseline_resolver,
        thresholds=thresholds,
        taxonomy_by_hero=taxonomy_by_hero,
        completed_sessions=completed_sessions,
    )
    portfolio_shape = build_portfolio_shape(matches, taxonomy_by_hero)
    involvement = duration_context_involvement(
        matches,
        baseline_resolver=baseline_resolver,
        taxonomy_by_hero=taxonomy_by_hero,
    )
    finishing = stabilized_finishing(matches)
    death_exposure = overdispersed_death_exposure(
        matches,
        baseline_resolver=baseline_resolver,
        taxonomy_by_hero=taxonomy_by_hero,
    )
    transfer = continuous_transfer(
        matches,
        baseline_resolver=baseline_resolver,
        taxonomy_by_hero=taxonomy_by_hero,
    )
    consistency = information_weighted_consistency(
        matches,
        baseline_resolver=baseline_resolver,
        taxonomy_by_hero=taxonomy_by_hero,
    )
    result_response = result_response_summary(matches, taxonomy_by_hero)
    session_curve = session_position_curve(matches, completed_sessions=completed_sessions)

    report["schema_version"] = REPORT_VERSION
    versions = default_versions_v61()
    report["versions"] = {
        "elements": versions["elements"],
        "findings": versions["findings"],
        "supporting_signals": versions["supporting_signals"],
        "semantic_outcomes": versions["semantic_outcomes"],
        "expression": versions["expression"],
        "statistics": versions["statistics"],
        "context_baseline": versions["context_baseline"],
        "thresholds": versions["thresholds"],
        "claims": versions["claims"],
        "story": versions["story"],
        "copy": versions["copy"],
        "recommendations": versions["recommendations"],
        "deep_diagnostics": versions["deep_diagnostics"],
        "share_renderer": versions["share_renderer"],
        "interactions": versions["interactions"],
        "summary_history": versions["summary_history"],
        "model": model_version,
        "template": template_version,
        "analysis_version_fingerprint": analysis_version_fingerprint,
    }
    report["story"]["version"] = versions["story"]
    for question in report["diagnostic_questions"]:
        question["version"] = versions["deep_diagnostics"]
        if isinstance(question.get("question_spec"), dict):
            question["question_spec"]["version"] = versions["deep_diagnostics"]
    for element in report["elements"]:
        _patch_element(
            element,
            involvement=involvement,
            finishing=finishing,
            death_exposure=death_exposure,
            transfer=transfer,
            consistency=consistency,
        )
    family_p = v61_family_p_values(
        portfolio_shape=portfolio_shape,
        transfer=transfer,
        result_response=result_response,
        session_curve=session_curve,
        involvement=involvement,
        death_exposure=death_exposure,
    )
    selected_keys = {
        finding["family"]: _semantic_key(
            finding["family"],
            finding,
            portfolio_shape,
            transfer,
            result_response,
            involvement,
            death_exposure,
        )
        for finding in report["findings"]
    }
    branch_p = v61_branch_p_values(
        portfolio_shape=portfolio_shape,
        transfer=transfer,
        result_response=result_response,
        session_curve=session_curve,
        involvement=involvement,
        death_exposure=death_exposure,
    )
    selection_audit = hierarchical_qualification(family_p, branch_p)
    published_count = 0
    for finding in report["findings"]:
        family = finding["family"]
        semantic_key = selected_keys[family]
        definition = SEMANTIC_OUTCOME_REGISTRY[semantic_key]
        branch_values = selection_audit[family].get("branches")
        branch = (
            branch_values.get(semantic_key, {})
            if isinstance(branch_values, Mapping)
            else {}
        )
        eligible = bool(finding.get("published")) and bool(branch.get("qualified"))
        eligible = eligible and definition.rollout_status == "public_candidate" and published_count < 3
        if family == "pool_shape" and canonical_history.audit.completeness != "complete":
            eligible = False
            selection_audit[family]["suppression_reason"] = "history_not_complete"
        finding["published"] = eligible
        published_count += int(eligible)
        finding["semantic_outcome_key"] = semantic_key
        finding["hypothesis_branch"] = definition.hypothesis_branch
        finding["estimator_version"] = f"semantic:{semantic_key}:1.0.0"
        finding["branch_adjusted_q_value"] = branch.get("adjusted_q_value", 1.0)
        finding["raw_p_value"] = family_p[family]
        finding["adjusted_q_value"] = selection_audit[family]["adjusted_q_value"]
        finding["interaction"] = {
            "kind": definition.interaction_key,
            "enabled": eligible and definition.interaction_key is not None,
            "fallback": "text_evidence",
        }
        copy = SEMANTIC_COPY_REGISTRY[semantic_key]
        finding["claim"] = copy.claim
        finding["interpretation"] = copy.interpretation
        finding["evidence_text"] = copy.evidence_label
        contract = dict(finding.get("claim_contract") or {})
        contract.update(
            {
                "claim": copy.claim,
                "evidence": copy.evidence_label,
                "interpretation": copy.interpretation,
                "alternatives": list(definition.alternatives),
                "verification": (
                    {
                        "eligibility_games": 5,
                        "primary_metric": definition.verification_metric_keys[0],
                        "guardrail_metric": definition.verification_metric_keys[1],
                        "causal": False,
                        "abstention": "too early to tell",
                    }
                    if definition.verification_metric_keys
                    else None
                ),
                "interaction": definition.interaction_key,
                "deep_handoff": {
                    "cohort_reference": _protected_cohort_reference(
                        family, canonical_history.audit.normalized_payload_sha256
                    ),
                    "unanswered_alternatives": list(definition.alternatives),
                },
                "copy_version": versions["copy"],
            }
        )
        finding["claim_contract"] = contract
        if not eligible:
            finding["semantic_outcome_key"] = None
            finding["hypothesis_branch"] = None
            finding["outcome_key"] = None
            finding["signal_keys"] = []
            finding["supported_claims"] = []
            finding["claim"] = None
            finding["interpretation"] = None
            finding["evidence_text"] = None
            finding["interaction"] = {
                "kind": None,
                "enabled": False,
                "fallback": "family_not_published",
            }
            finding["claim_contract"] = None
    report["quality"]["published_findings"] = published_count
    if canonical_history.audit.completeness != "complete":
        report["quality"]["warnings"] = list(
            dict.fromkeys(
                [
                    *report["quality"].get("warnings", []),
                    "Annual and longitudinal pool-shape claims require complete history.",
                ]
            )
        )
    report["identity_summary"]["slots"] = compose_identity_slots(
        report["identity_summary"], report["findings"], report["hero_portfolio"], portfolio_shape
    )
    _refresh_public_surfaces(report)
    _protect_deep_handoffs(
        report,
        matches,
        history_hash=canonical_history.audit.normalized_payload_sha256,
        protected_cohorts_out=protected_cohorts_out,
    )
    report["supporting_evidence"] = {
        "portfolio_shape": portfolio_shape,
        "involvement": involvement,
        "finishing": finishing,
        "death_exposure": death_exposure,
        "transfer_frontier": transfer,
        "consistency": consistency,
        "result_response": result_response,
        "session_curve": session_curve,
    }
    for family_audit in selection_audit.values():
        family_audit["calibration_status"] = "fixture_synthetic_only"
    report["selection_audit"] = selection_audit
    report["reproducibility"].update(
        {
            "history_contract": canonical_history.audit.as_dict(),
            "request_manifest": request_manifest(),
            "artifact_checksums": dict(artifact_checksums),
            "baseline_artifact": versions["context_baseline"],
            "threshold_artifact": versions["thresholds"],
        }
    )
    report["methodology"] = {
        "free_summary_only": True,
        "population_window_days": 365,
        "weighting": "estimator_specific",
        "sessions_are_independence_unit": True,
        "bootstrap_iterations": 2_000,
        "family_roots": 5,
        "public_elements": 7,
        "hierarchical_error_control": True,
        "calibration_status": "fixture_synthetic_only",
        "rank_or_mmr_used": False,
        "shadow_enabled": shadow_enabled,
        "experimental_evolution_enabled": experimental_evolution_enabled,
        "experimental_loops_enabled": experimental_loops_enabled,
        "notes": [
            "Supporting signals are evidence, not additional public score cards.",
            "Optional context is used only when its canonical coverage gate passes.",
        ],
    }
    # Fingerprint the exact version/artifact/contract bytes used for this report.
    report["versions"]["analysis_version_fingerprint"] = hashlib.sha256(
        json.dumps(
            {
                "versions": report["versions"],
                "artifacts": artifact_checksums,
                "history": canonical_history.audit.normalized_payload_sha256,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return _plain(report)


__all__ = ["REPORT_SCHEMA_VERSION_V61", "assemble_free_dna_report_v61"]
