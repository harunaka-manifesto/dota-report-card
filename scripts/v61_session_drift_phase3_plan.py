#!/usr/bin/env python3
"""Build the fixed, offline V6.1 Session Drift Phase-3 plan."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any

BASE_SHA = "c34f1a272005dda954af0932f7719a4cc230a23d"
SOURCE_SHA = "7df38e6d234ae9c4ee425490bc40b8cc92685f85"
ARTIFACT_DIGEST = "8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0"
TARGETS = (105, 110, 115, 120, 125)
SUPPORT_POSTERIOR = (35.5, 734.5)
ELIGIBILITY_POSTERIOR = (1609.5, 1239.5)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _wilson(successes: int, total: int) -> list[float]:
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    spread = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total**2)) / denominator
    return [center - spread, center + spread]


def _score_test(left: tuple[int, int], right: tuple[int, int]) -> dict[str, float]:
    left_successes, left_total = left
    right_successes, right_total = right
    pooled = (left_successes + right_successes) / (left_total + right_total)
    z = (left_successes / left_total - right_successes / right_total) / math.sqrt(
        pooled * (1 - pooled) * (1 / left_total + 1 / right_total)
    )
    return {"z": z, "two_sided_p": 2 * (1 - NormalDist().cdf(abs(z)))}


def _beta_binomial_tail(trials: int, minimum: int, alpha: float, beta: float) -> float:
    log_beta = math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)
    terms = [
        math.lgamma(trials + 1)
        - math.lgamma(value + 1)
        - math.lgamma(trials - value + 1)
        + math.lgamma(alpha + value)
        + math.lgamma(beta + trials - value)
        - math.lgamma(alpha + beta + trials)
        - log_beta
        for value in range(trials + 1)
    ]
    peak = max(terms)
    probabilities = [math.exp(value - peak) for value in terms]
    return sum(probabilities[minimum:]) / sum(probabilities)


def _binomial_tail(trials: int, minimum: int, probability: float) -> float:
    terms = [
        math.lgamma(trials + 1)
        - math.lgamma(value + 1)
        - math.lgamma(trials - value + 1)
        + value * math.log(probability)
        + (trials - value) * math.log1p(-probability)
        for value in range(minimum, trials + 1)
    ]
    peak = max(terms)
    return math.exp(peak) * sum(math.exp(value - peak) for value in terms)


def _minimum_trials(minimum: int, assurance: float, tail: Any) -> int:
    trials = minimum
    while tail(trials, minimum) < assurance:
        trials += 1
    return trials


def _option(
    *,
    name: str,
    target: int,
    eligible_profiles: int,
    candidate_accounts: int,
    public_pages: int,
) -> dict[str, Any]:
    details = public_pages * 100
    requests = public_pages + details + candidate_accounts
    support_probability = _beta_binomial_tail(eligible_profiles, target - 99, *SUPPORT_POSTERIOR)
    eligibility_probability = _beta_binomial_tail(
        candidate_accounts, eligible_profiles, *ELIGIBILITY_POSTERIOR
    )
    expected_final = 99 + eligible_profiles * SUPPORT_POSTERIOR[0] / sum(SUPPORT_POSTERIOR)
    return {
        "plan": name,
        "target_observations": target,
        "additional_eligible_profiles": eligible_profiles,
        "candidate_accounts": candidate_accounts,
        "public_match_pages": public_pages,
        "seed_match_details": details,
        "expected_physical_requests": requests,
        "hard_request_ceiling": requests,
        "expected_cost_idr_pro_rata": requests / 100 * 200,
        "whole_block_cost_idr": math.ceil(requests / 100) * 200,
        "support_target_probability_given_eligible_count": support_probability,
        "eligible_count_probability": eligibility_probability,
        "joint_gate_probability_lower_bound": support_probability + eligibility_probability - 1,
        "expected_final_session_observations": expected_final,
        "retries": 0,
        "replacements": 0,
        "adaptive_top_up": False,
    }


def _self_check() -> None:
    assert (
        _minimum_trials(11, 0.95, lambda n, k: _beta_binomial_tail(n, k, *SUPPORT_POSTERIOR)) == 400
    )
    assert (
        _minimum_trials(11, 0.99, lambda n, k: _beta_binomial_tail(n, k, *SUPPORT_POSTERIOR)) == 495
    )
    assert (
        _minimum_trials(407, 0.995, lambda n, k: _beta_binomial_tail(n, k, *ELIGIBILITY_POSTERIOR))
        == 792
    )
    assert _binomial_tail(400, 11, 35 / 769) > 0.97


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase2-diagnostics", type=Path, required=True)
    parser.add_argument("--phase2-corpus", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    _self_check()

    aggregate = _read(args.phase2_diagnostics / "aggregate_summary.json")
    support = _read(args.phase2_diagnostics / "old_vs_new_support_report.json")
    continuity = _read(args.phase2_diagnostics / "distribution_continuity_audit.json")
    cost = _read(args.phase2_diagnostics / "cost_ledger.json")
    normalized = _read(args.phase2_diagnostics / "normalized_corpus_manifest.json")
    validation = _read(args.phase2_corpus / "manifests" / "sealed-validation-status.json")
    reusable = _read(args.phase2_diagnostics / "reusable_corpus_manifest.json")

    if (
        aggregate["session_drift"]["combined_margin_observations"] != 99
        or support["by_arm"]["existing_tuning"]["session_margin_observations"] != 62
        or support["by_arm"]["external_tuning"]["session_margin_observations"] != 35
        or support["by_arm"]["local_reserve"]["session_margin_observations"] != 2
        or normalized["normalized_profile_count"] != 2848
        or normalized["eligible_profile_count"] != 1609
        or validation["eligible_status_count"] != 745
        or validation["analytically_evaluated"] != 0
        or not continuity["pass"]
    ):
        raise ValueError("binding Phase-2 evidence changed")

    old_rate = 62 / 791
    external_rate = 35 / 769
    extension_rate = 37 / 809
    pooled_rate = 99 / 1600
    rate_test = _score_test((62, 791), (35, 769))
    reconciliation = {
        "schema_version": "v61-session-drift-phase3-support-reconciliation-1.0.0",
        "original": {
            "margin_observations": 62,
            "eligible_profiles": 791,
            "rate": old_rate,
            "wilson_95": _wilson(62, 791),
        },
        "phase2_external": {
            "margin_observations": 35,
            "selected_eligible_profiles": 769,
            "rate": external_rate,
            "wilson_95": _wilson(35, 769),
        },
        "phase2_local_reserve": {
            "margin_observations": 2,
            "eligible_profiles": 40,
            "rate": 2 / 40,
            "wilson_95": _wilson(2, 40),
        },
        "phase2_extension_total": {
            "margin_observations": 37,
            "eligible_profiles": 809,
            "rate": extension_rate,
            "wilson_95": _wilson(37, 809),
        },
        "combined": {
            "margin_observations": 99,
            "eligible_profiles": 1600,
            "rate": pooled_rate,
            "wilson_95": _wilson(99, 1600),
        },
        "invalid_shorthand": "37/769 mixes the 35 external + 2 local-reserve numerator with the 769 external-only denominator",
        "old_vs_external_score_test": rate_test,
        "formal_distribution_continuity": "PASS",
        "interpretation": "Outcome definitions match, but collection campaigns are not exchangeable: the external rate is lower, the score-test difference is material, and Phase-2 had fewer 240+ match histories and fewer median-session-length 4+ profiles while remaining inside continuity limits.",
        "planning_consequence": "Forecast from the Phase-2 external campaign, retain campaign as a diagnostic indicator, and do not use the higher old or pooled rate to reduce collection.",
    }
    _write(args.output_dir / "phase2_support_reconciliation.json", reconciliation)

    models = []
    model_specs = [
        ("MODEL_1_POOLED_BINOMIAL", "binomial", pooled_rate, None),
        ("MODEL_2_NEW_WAVE_BINOMIAL", "binomial", external_rate, None),
        ("MODEL_3_POOLED_JEFFREYS_BETA_BINOMIAL", "beta_binomial", None, (99.5, 1501.5)),
        (
            "MODEL_4_CAMPAIGN_SPECIFIC_JEFFREYS_BETA_BINOMIAL",
            "beta_binomial",
            None,
            SUPPORT_POSTERIOR,
        ),
    ]
    for name, kind, probability, posterior in model_specs:
        tail = (
            (lambda n, k, p=probability: _binomial_tail(n, k, float(p)))
            if kind == "binomial"
            else (lambda n, k, ab=posterior: _beta_binomial_tail(n, k, *ab))
        )
        models.append(
            {
                "model": name,
                "kind": kind,
                "rate_or_posterior": probability
                if probability is not None
                else {
                    "alpha": posterior[0],
                    "beta": posterior[1],
                    "mean": posterior[0] / sum(posterior),
                },
                "additional_eligible_for_target_110_at_95": _minimum_trials(11, 0.95, tail),
                "additional_eligible_for_target_110_at_99": _minimum_trials(11, 0.99, tail),
                "planning_verdict": "SELECT" if name.startswith("MODEL_4") else "COMPARATOR_ONLY",
            }
        )
    _write(
        args.output_dir / "support_predictive_models.json",
        {
            "schema_version": "v61-session-drift-phase3-support-models-1.0.0",
            "models": models,
            "recommended_model": "MODEL_4_CAMPAIGN_SPECIFIC_JEFFREYS_BETA_BINOMIAL",
            "expected_session_margin_rate": SUPPORT_POSTERIOR[0] / sum(SUPPORT_POSTERIOR),
            "uncertainty_interval": {
                "type": "Wilson 95% on directly comparable external campaign",
                "value": _wilson(35, 769),
            },
            "why": "It carries rate uncertainty and forecasts from the only directly comparable external HMAC-selected tuning campaign; it does not borrow the demonstrably higher original rate.",
        },
    )

    comparisons = []
    for target in TARGETS:
        needed = target - 99
        row = {"target": target, "additional_observations_required": needed}
        for assurance in (0.95, 0.99):
            trials = _minimum_trials(
                needed,
                assurance,
                lambda n, k: _beta_binomial_tail(n, k, *SUPPORT_POSTERIOR),
            )
            row[f"eligible_profiles_at_{int(assurance * 100)}pct"] = trials
            row[f"achieved_probability_at_{int(assurance * 100)}pct"] = _beta_binomial_tail(
                trials, needed, *SUPPORT_POSTERIOR
            )
            row[f"expected_final_at_{int(assurance * 100)}pct"] = 99 + trials * SUPPORT_POSTERIOR[
                0
            ] / sum(SUPPORT_POSTERIOR)
        comparisons.append(row)
    _write(
        args.output_dir / "target_comparison.json",
        {
            "schema_version": "v61-session-drift-phase3-target-comparison-1.0.0",
            "starting_observations": 99,
            "model": "campaign-specific Jeffreys Beta(35.5,734.5) beta-binomial",
            "targets": comparisons,
            "recommended_target": 110,
            "minimum_eligible_at_95pct": 400,
            "fixed_eligible_buffer": 7,
            "recommended_phase3_eligible_profiles": 407,
            "recommended_expected_final": 99 + 407 * SUPPORT_POSTERIOR[0] / sum(SUPPORT_POSTERIOR),
            "recommended_support_probability": _beta_binomial_tail(407, 11, *SUPPORT_POSTERIOR),
        },
    )

    conversion = {
        "schema_version": "v61-session-drift-phase3-candidate-conversion-1.0.0",
        "whole_frame": {
            "candidate_accounts": 4135,
            "successfully_fetched_histories": 4134,
            "eligibility_status_determined": 4134,
            "canonically_eligible": 2354,
            "history_success_wilson_95": _wilson(4134, 4135),
            "eligibility_wilson_95": _wilson(2354, 4134),
        },
        "tuning_arm": {
            "candidate_accounts": 2848,
            "successfully_fetched_histories": 2848,
            "eligibility_status_determined": 2848,
            "canonically_eligible": 1609,
            "eligible_selected_for_phase2_tuning": 769,
            "eligible_unused_reserve": 840,
            "session_margin_observations_in_selected_profiles": 35,
            "eligibility_rate": 1609 / 2848,
            "eligibility_wilson_95": _wilson(1609, 2848),
            "selected_support_rate": external_rate,
            "selected_support_wilson_95": _wilson(35, 769),
        },
        "validation_arm_permitted_metadata": {
            "candidate_accounts": 1287,
            "successfully_fetched_histories": 1286,
            "eligibility_status_determined": 1286,
            "canonically_eligible": 745,
            "analytically_evaluated": 0,
            "eligibility_rate": 745 / 1287,
            "eligibility_wilson_95": _wilson(745, 1287),
        },
        "planning_model": {
            "posterior": "Beta(1609.5,1239.5)",
            "mean": ELIGIBILITY_POSTERIOR[0] / sum(ELIGIBILITY_POSTERIOR),
            "why": "tuning-arm only; lower than validation-arm eligibility and directly matches the future tuning-only arm",
        },
        "recommended_required_eligible_profiles": 407,
        "candidate_accounts_for_99_5pct_assurance": 792,
        "achieved_eligible_probability": _beta_binomial_tail(792, 407, *ELIGIBILITY_POSTERIOR),
    }
    _write(args.output_dir / "eligible_to_candidate_conversion.json", conversion)

    frame = {
        "schema_version": "v61-session-drift-phase3-frame-spec-1.0.0",
        "campaign_id": "v61-session-drift-phase3-2026-08-28",
        "target_population": "positive public-profile account IDs observed in sampled OpenDota public matches; same known public-history bias as Phase 2",
        "candidate_discovery": "continue strictly below the minimum Phase-2 seed match ID; exactly 4 descending /publicMatches pages of 100 unique seed matches and exactly 400 /matches detail attempts",
        "deduplication": "deduplicate positive account IDs across all 400 fixed seed details before exclusions",
        "prior_frame_exclusion": "exclude the complete private prior-candidate union before ranking",
        "ranking": "new 32-byte private salt; HMAC-SHA256(salt, 'v61-session-phase3:' + decimal_account_id), ascending digest then decimal ID",
        "fixed_candidate_count": 792,
        "split_behavior": "tuning extension only; process all 792 histories, select the first 407 canonically eligible profiles in HMAC order, retain later eligible profiles as unused reserve",
        "failure_handling": "record every fixed attempt; a short discovery frame or fewer than 407 eligible profiles fails without repair",
        "retry_limit": 0,
        "replacement_policy": "NONE",
        "optional_stopping": "Collect/process the entire fixed Phase 3 frame even if Session observation #100, #110, or the target is reached early. Do not stop because the target has been reached. Do not top up if the target is missed.",
        "forbidden_enrichment": [
            "session length",
            "completed-session count",
            "Session support",
            "Session effect",
            "Finding yield",
            "rank",
            "MMR",
        ],
    }
    _write(args.output_dir / "phase3_sampling_frame_spec.json", frame)
    _write(
        args.output_dir / "prior_candidate_exclusion_spec.json",
        {
            "schema_version": "v61-session-drift-phase3-exclusion-1.0.0",
            "exclude_counts": {
                "phase2_fixed_frame": 4135,
                "original_tuning": 791,
                "safe_local_reserves": 40,
                "old_revealed_holdout": 339,
                "fresh_replacement_holdout": 339,
                "phase2_fresh_validation_candidates": 1287,
            },
            "also_exclude": [
                "all 4,423 positive accounts discovered by the Phase-2 seed-detail corpus after reconstructing the private set",
                "all earlier research candidate pools and screened reserves",
                "both canceled/no-response Phase-2 assignments",
                "all prior seed match IDs",
            ],
            "construction": "rebuild the union from private historical manifests plus Phase-2 raw seed-detail capture; store IDs only in mode-0600 local artifacts; publish count and SHA-256 digest only",
            "raw_account_ids_in_tracked_outputs": False,
            "retry_old_failures": False,
        },
    )

    _write(
        args.output_dir / "validation_extension_decision.json",
        {
            "schema_version": "v61-session-drift-phase3-validation-decision-1.0.0",
            "existing_sealed_validation_candidate_count": 1287,
            "successfully_collected_count": 1286,
            "eligibility_status_count": 1286,
            "exact_eligible_count_legally_knowable": 745,
            "target_eligible_count": 339,
            "analytically_evaluated": 0,
            "sufficient_for_one_shot_validation": True,
            "phase3_validation_extension_needed": False,
            "decision": "A_COLLECT_TUNING_EXTENSION_ONLY",
        },
    )

    page_bytes = 302947 / 12
    detail_bytes = 24882110 / 1200
    history_bytes = (183640157 + 85436576) / 4134
    expected_raw = round(4 * page_bytes + 400 * detail_bytes + 792 * history_bytes)
    expected_storage_mib = 81
    cost_model = {
        "schema_version": "v61-session-drift-phase3-cost-1.0.0",
        "candidate_accounts": 792,
        "public_match_pages": 4,
        "seed_match_details": 400,
        "expected_physical_requests": 1196,
        "hard_request_ceiling": 1196,
        "expected_cost_idr_pro_rata": 2392,
        "whole_block_cost_idr": 2400,
        "hard_cost_ceiling_idr": 2400,
        "expected_raw_payload_bytes": expected_raw,
        "expected_retained_storage_mib": expected_storage_mib,
        "hard_storage_increment_mib": 100,
        "expected_elapsed_minutes_at_measured_phase2_rate": 1196 / (5346 / (4781.01703 / 60)),
        "measured_phase2_basis": {
            "physical_requests": cost["physical_request_count"],
            "retained_storage_mib": cost["cumulative_storage_mib"],
            "history_payload_bytes_per_attempt": history_bytes,
        },
        "owner_authorization_ceiling": "1,196 physical OpenDota calls, Rp2,400 under the supplied whole-block rate, and 100 MiB additional retained storage",
    }
    _write(args.output_dir / "phase3_cost_model.json", cost_model)

    _write(
        args.output_dir / "pooling_contract.json",
        {
            "schema_version": "v61-session-drift-phase3-pooling-contract-1.0.0",
            "calibration_lineage_version": "v61-session-drift-calibration-lineage-1.1.0",
            "estimator_version_unchanged": "research-signed-prevalence-calibration-1.0.0",
            "sessionization_version_unchanged": "sessions-5.0.0",
            "normalized_schema_required": "v61-calibration-corpus-2.1.0",
            "normalizer_required": "summary-normalization-2.0.0",
            "prior_profiles": {
                "original_tuning": 791,
                "safe_reserves": 40,
                "phase2_external": 769,
                "total": 1600,
            },
            "phase3_profiles": 407,
            "combined_profiles": 2007,
            "pooling_allowed": "YES only if every continuity/provenance/schema gate passes",
            "continuity_checks": "compare Phase-3 with both original 791 and Phase-2 external 769 on the five fixed bins; natural-log JS <=0.10 and every absolute bin-share difference <=0.15",
            "campaign_indicator": "retain source_arm/campaign_id for diagnostics",
            "weighting": "NONE",
            "selective_exclusions": "NONE beyond predeclared canonical eligibility and first-407 HMAC order",
        },
    )

    gates = {
        "schema_version": "v61-session-drift-phase3-gates-1.0.0",
        "ordered_gates": [
            {
                "gate": 1,
                "name": "operational_integrity",
                "pass": "fixed 4-page/400-detail/792-history frame completed within 1,196 requests, Rp2,400, and 100 MiB",
                "fail": "STOP; no retry, replacement, extra page, or top-up",
            },
            {
                "gate": 2,
                "name": "provenance",
                "pass": "private exclusion/frame/split/request/raw/normalized manifests and digests reconcile",
                "fail": "STOP",
            },
            {
                "gate": 3,
                "name": "distribution_continuity",
                "pass": "all predeclared old-vs-Phase3 and Phase2-vs-Phase3 bin checks pass",
                "fail": "STOP; no corrective sampling",
            },
            {
                "gate": 4,
                "name": "combined_session_evidence",
                "pass": "combined legitimate margin observations >=110",
                "fail": "classify exactly by the count bands below",
            },
            {
                "gate": 5,
                "name": "margin_derivation",
                "pass": "finite frozen P90/2 margin from the complete pooled tuning set",
                "fail": "STOP",
            },
            {
                "gate": 6,
                "name": "session_hardening",
                "pass": "frozen null/type-I, split-half, LOO, dominant-hero, and evidence-completeness gates pass",
                "fail": "STOP",
            },
            {
                "gate": 7,
                "name": "exact_m3_multiplicity",
                "pass": "fixed Transfer + Post-Loss + Session Drift BY q=.05 grid passes",
                "fail": "STOP; do not drop a family or select BH for yield",
            },
            {
                "gate": 8,
                "name": "candidate_freeze",
                "pass": "source, corpus, methods, margins, hardening, m=3 BY, semantic rules, and predictive intervals are hash-frozen before validation",
                "fail": "STOP; validation remains sealed",
            },
        ],
        "count_bands": {
            "below_100": "HARD_ANALYTICAL_FAILURE",
            "100_through_109": "FROZEN_MINIMUM_MET_BUT_PHASE3_EVIDENCE_TARGET_MISSED",
            "110_or_more": "PLANNED_EVIDENCE_TARGET_ACHIEVED",
        },
        "no_optional_stopping": frame["optional_stopping"],
    }
    _write(args.output_dir / "phase3_gates.json", gates)

    _write(
        args.output_dir / "three_family_multiplicity_execution_plan.json",
        {
            "schema_version": "v61-session-drift-phase3-m3-plan-1.0.0",
            "family_universe": ["Transfer", "Post-Loss", "Session Drift"],
            "deferred": ["Presence & Exposure"],
            "fixed_m": 3,
            "q": 0.05,
            "release_procedure": "Benjamini-Yekutieli",
            "diagnostic_comparator": "Benjamini-Hochberg",
            "repetitions_per_cell": 10000,
            "signed_prevalence_draws": 2000,
            "seed": 20260828,
            "truth_scenarios": [
                "complete_null",
                "mixed_truth_one_moderate_alternative",
                "subset_nulls",
            ],
            "dependence_scenarios": [
                "independent",
                "positive_rho_0.5",
                "positive_rho_0.9",
                "adverse_feasible_rho_minus_0.25",
                "empirical_tuning_dependence",
            ],
            "acceptance": "every registered BY null cell has estimated FDR <=0.055 and Wilson lower bound <=0.05",
            "procedure_selected_by_yield": False,
        },
    )

    _write(
        args.output_dir / "reusable_corpus_extension_plan.json",
        {
            "schema_version": "v61-session-drift-phase3-corpus-extension-1.0.0",
            "phase2_corpus_digest": reusable["raw_corpus_digest"],
            "phase2_normalized_digest": reusable["normalized_corpus_digest"],
            "phase2_split_digest": reusable["split_manifest_digest"],
            "new_sibling_path": ".local/corpora/opendota/v61-session-drift-phase3-extension/",
            "layers": [
                "raw provider capture",
                "normalized provider-specific projection",
                "cohort/split manifests",
                "derived analytical features",
            ],
            "append_rule": "never overwrite Phase-2 corpus files; create a new campaign sibling and a combined digest manifest that references both immutable campaigns",
            "provider": "OpenDota",
            "identity": "same salted SHA-256 pseudonym scheme; new private Phase-3 salt and v61-session-phase3 HMAC namespace",
            "campaign_indicator_required": True,
            "semantic_relabeling": False,
            "future_v7_stratz_reuse": "permitted only with provider layers separate and explicit field mapping",
        },
    )

    options = [
        _option(
            name="PLAN_A_MINIMUM_SMALL_WAVE",
            target=105,
            eligible_profiles=248,
            candidate_accounts=493,
            public_pages=3,
        ),
        _option(
            name="PLAN_B_RECOMMENDED_BALANCED_WAVE",
            target=110,
            eligible_profiles=407,
            candidate_accounts=792,
            public_pages=4,
        ),
        _option(
            name="PLAN_C_CONSERVATIVE_LARGER_WAVE",
            target=125,
            eligible_profiles=862,
            candidate_accounts=1641,
            public_pages=7,
        ),
    ]
    options[0].update(
        {
            "expected_retained_storage_mib": 55,
            "hard_storage_increment_mib": 75,
            "pros": ["lowest cost", "clears the frozen minimum with a small buffer"],
            "cons": [
                "only five observations above minimum",
                "greater chance of another near-edge result",
            ],
        }
    )
    options[1].update(
        {
            "expected_retained_storage_mib": 81,
            "hard_storage_increment_mib": 100,
            "pros": [
                "ten-observation target buffer",
                "expected final count remains inside the owner's 110-120 preference",
                "about 22% of Phase-2 request scale",
            ],
            "cons": ["more collection than Plan A"],
        }
    )
    options[2].update(
        {
            "expected_retained_storage_mib": 145,
            "hard_storage_increment_mib": 180,
            "pros": ["largest calibration buffer"],
            "cons": [
                "expected final count materially exceeds the preferred range",
                "diminishing returns and nearly twice Plan B cost",
            ],
        }
    )
    _write(
        args.output_dir / "owner_decision_options.json",
        {
            "schema_version": "v61-session-drift-phase3-owner-options-1.0.0",
            "options": options,
            "recommendation": "PLAN_B_RECOMMENDED_BALANCED_WAVE",
        },
    )

    summary = {
        "schema_version": "v61-session-drift-phase3-plan-aggregate-1.0.0",
        "status": "PASS",
        "base_sha": BASE_SHA,
        "analytical_source_sha": SOURCE_SHA,
        "frozen_artifact_digest": ARTIFACT_DIGEST,
        "recommended_target": 110,
        "current_margin_observations": 99,
        "additional_eligible_profiles": 407,
        "candidate_accounts": 792,
        "expected_final_observations": 99 + 407 * SUPPORT_POSTERIOR[0] / sum(SUPPORT_POSTERIOR),
        "support_target_probability": _beta_binomial_tail(407, 11, *SUPPORT_POSTERIOR),
        "eligibility_target_probability": _beta_binomial_tail(792, 407, *ELIGIBILITY_POSTERIOR),
        "joint_gate_probability_lower_bound": _beta_binomial_tail(407, 11, *SUPPORT_POSTERIOR)
        + _beta_binomial_tail(792, 407, *ELIGIBILITY_POSTERIOR)
        - 1,
        "physical_request_ceiling": 1196,
        "cost_ceiling_idr": 2400,
        "storage_increment_ceiling_mib": 100,
        "validation_extension": False,
        "provider_calls": 0,
        "old_revealed_holdout_evaluated": 0,
        "fresh_sealed_validation_analytically_evaluated": 0,
        "production_analytical_behavior_changed": False,
    }
    _write(args.output_dir / "aggregate_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
