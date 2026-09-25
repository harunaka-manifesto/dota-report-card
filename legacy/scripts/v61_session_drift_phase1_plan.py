#!/usr/bin/env python3
"""Build the offline V6.1 Session Drift Phase 1 execution plan."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

ANALYTICAL_BASE = "3323511da91329dc6c6af3e090e10e1be944ecef"
SOURCE_SHA = "7df38e6d234ae9c4ee425490bc40b8cc92685f85"
ARTIFACT_DIGEST = "8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0"
PROFILE_KEY_VERSION = "research-signed-prevalence-calibration-1.0.0"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _wilson(successes: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    spread = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total**2)) / denominator
    return center - spread, center + spread


def _beta_binomial_tail(n: int, minimum: int, alpha: float, beta: float) -> float:
    log_beta = math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)
    terms = [
        math.lgamma(n + 1)
        - math.lgamma(x + 1)
        - math.lgamma(n - x + 1)
        + math.lgamma(alpha + x)
        + math.lgamma(beta + n - x)
        - math.lgamma(alpha + beta + n)
        - log_beta
        for x in range(minimum, n + 1)
    ]
    peak = max(terms)
    return math.exp(peak) * sum(math.exp(value - peak) for value in terms)


def _minimum_trials(minimum: int, probability: float, alpha: float, beta: float) -> int:
    low = high = minimum
    while _beta_binomial_tail(high, minimum, alpha, beta) < probability:
        high *= 2
    while low < high:
        midpoint = (low + high) // 2
        if _beta_binomial_tail(midpoint, minimum, alpha, beta) >= probability:
            high = midpoint
        else:
            low = midpoint + 1
    return low


def _profile_key(profile_id: str) -> str:
    return hashlib.sha256(f"{PROFILE_KEY_VERSION}:{profile_id}".encode()).hexdigest()


def _bin_summary(
    rows: list[dict[str, Any]], descriptor: str, bands: list[tuple[str, float, float]]
) -> list[dict[str, Any]]:
    result = []
    for label, lower, upper in bands:
        selected = [row for row in rows if lower <= float(row[descriptor]) < upper]
        eligible = sum(bool(row["margin_eligible"]) for row in selected)
        interval = _wilson(eligible, len(selected)) if selected else (None, None)
        result.append(
            {
                "band": label,
                "profiles": len(selected),
                "margin_eligible": eligible,
                "support_rate": eligible / len(selected) if selected else None,
                "wilson_95": list(interval),
            }
        )
    return result


def _support_model(funnel: Path, corpus_path: Path, split_path: Path) -> dict[str, Any]:
    with funnel.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["margin_eligible"] = row["margin_eligible"] == "True"
        for name in (
            "total_matches",
            "total_sessions",
            "median_matches_per_session",
            "qualifying_session_coverage",
        ):
            row[name] = float(row[name])

    corpus, split = _read_json(corpus_path), _read_json(split_path)
    train = {str(value) for value in split["train_profile_ids"]}
    by_key = {row["profile_key"]: row for row in rows}
    for profile in corpus["profiles"]:
        profile_id = str(profile["profile_id"])
        if profile_id not in train:
            continue
        row = by_key[_profile_key(profile_id)]
        matches = profile["matches"]
        starts = [int(match["start_time"]) for match in matches]
        heroes = Counter(int(match["hero_id"]) for match in matches)
        row["activity_window_days"] = (max(starts) - min(starts)) / 86_400 if starts else 0
        row["dominant_hero_share"] = max(heroes.values()) / len(matches) if matches else 0

    if len(rows) != 791 or len(train) != 791 or any(
        "activity_window_days" not in row for row in rows
    ):
        raise ValueError("tuning corpus/funnel join mismatch")
    successes = sum(bool(row["margin_eligible"]) for row in rows)
    interval = _wilson(successes, len(rows))
    descriptors = {
        "match_depth": _bin_summary(
            rows,
            "total_matches",
            [("30-59", 30, 60), ("60-119", 60, 120), ("120-239", 120, 240), ("240+", 240, math.inf)],
        ),
        "session_count": _bin_summary(
            rows,
            "total_sessions",
            [("0-39", 0, 40), ("40-79", 40, 80), ("80-159", 80, 160), ("160+", 160, math.inf)],
        ),
        "median_session_length": _bin_summary(
            rows,
            "median_matches_per_session",
            [("1", 0, 2), ("2", 2, 3), ("3", 3, 4), ("4+", 4, math.inf)],
        ),
        "activity_window_days": _bin_summary(
            rows,
            "activity_window_days",
            [("<90", 0, 90), ("90-179", 90, 180), ("180-269", 180, 270), ("270+", 270, math.inf)],
        ),
        "dominant_hero_share": _bin_summary(
            rows,
            "dominant_hero_share",
            [("<10%", 0, 0.10), ("10-19%", 0.10, 0.20), ("20-29%", 0.20, 0.30), ("30%+", 0.30, math.inf)],
        ),
        "qualifying_session_coverage_diagnostic_only": _bin_summary(
            rows,
            "qualifying_session_coverage",
            [("<10%", 0, 0.10), ("10-24%", 0.10, 0.25), ("25-49%", 0.25, 0.50), ("50%+", 0.50, math.inf)],
        ),
    }
    return {
        "population": "frozen 791-profile tuning partition only",
        "profiles": len(rows),
        "margin_eligible": successes,
        "support_rate": successes / len(rows),
        "wilson_95": list(interval),
        "predictive_model": "Jeffreys Beta(62.5, 729.5) posterior with beta-binomial prediction",
        "descriptor_strata": descriptors,
        "interpretation": "descriptive diagnostics only; no descriptor may be used to enrich Phase-2 sampling",
    }


def _self_check() -> None:
    assert _wilson(62, 791)[0] < 62 / 791 < _wilson(62, 791)[1]
    assert _minimum_trials(38, 0.95, 62.5, 729.5) == 663
    assert _minimum_trials(38, 0.99, 62.5, 729.5) == 758
    assert _minimum_trials(769, 0.995, 379.5, 845.5) == 2848
    assert _minimum_trials(339, 0.995, 379.5, 845.5) == 1287


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--funnel", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--summary-scan", type=Path, required=True)
    parser.add_argument("--selection-evidence", type=Path, required=True)
    parser.add_argument("--candidate-source", type=Path, required=True)
    parser.add_argument("--raw-archive-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    _self_check()
    args.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output_dir.chmod(0o700)

    support = _support_model(args.funnel, args.corpus, args.split)
    scan = _read_json(args.summary_scan)
    selection = _read_json(args.selection_evidence)
    candidates = _read_json(args.candidate_source)
    raw_files = [path for path in args.raw_archive_dir.iterdir() if path.is_file()]
    raw_bytes = sum(path.stat().st_size for path in raw_files)
    if (
        support["profiles"] != 791
        or support["margin_eligible"] != 62
        or scan["eligible_count"] != 379
        or scan["candidate_count"] != 1224
        or selection["unused_eligible_reserve_count"] != 40
    ):
        raise ValueError("binding local counts changed")

    target_total, local_reserve = 1600, 40
    additional_total = target_total - 791
    external_tuning_eligible = additional_total - local_reserve
    fresh_validation_eligible = 339
    tuning_candidates = _minimum_trials(external_tuning_eligible, 0.995, 379.5, 845.5)
    validation_candidates = _minimum_trials(fresh_validation_eligible, 0.995, 379.5, 845.5)
    external_candidates = tuning_candidates + validation_candidates
    fixed_public_pages, fixed_seed_details = 12, 1200
    request_ceiling = fixed_public_pages + fixed_seed_details + external_candidates

    pools = [
        {
            "pool": "current canonical tuning partition",
            "profile_count": 791,
            "source_lineage": "replacement canonical corpus; frozen train split",
            "used_for_tuning": "YES",
            "used_for_calibration": "YES",
            "revealed": "YES (development)",
            "used_for_holdout": "NO",
            "safe_for_new_tuning_extension": "ALREADY INCLUDED",
            "why": "binding basis for the 62 Session margin observations",
        },
        {
            "pool": "unused eligible replacement-scan reserve",
            "profile_count": 40,
            "source_lineage": "precommitted 1,224-candidate scan; eligible but beyond first 339 selected holdout profiles",
            "used_for_tuning": "NO",
            "used_for_calibration": "NO",
            "revealed": "NO Session outputs",
            "used_for_holdout": "NO",
            "safe_for_new_tuning_extension": "YES",
            "why": "never assigned or evaluated; eligibility and raw histories already exist locally",
        },
        {
            "pool": "current fresh sealed replacement holdout",
            "profile_count": 339,
            "source_lineage": "first 339 eligible profiles in precommitted replacement order",
            "used_for_tuning": "NO",
            "used_for_calibration": "NO",
            "revealed": "NO",
            "used_for_holdout": "YES",
            "safe_for_new_tuning_extension": "NO",
            "why": "protected holdout assignment is irreversible",
        },
        {
            "pool": "historical revealed holdout",
            "profile_count": 339,
            "source_lineage": "prior validation population",
            "used_for_tuning": "NO",
            "used_for_calibration": "NO",
            "revealed": "YES",
            "used_for_holdout": "YES",
            "safe_for_new_tuning_extension": "NO",
            "why": "validation use and reveal permanently exclude tuning reuse",
        },
        {
            "pool": "replacement-scan ineligible candidates",
            "profile_count": 845,
            "source_lineage": "same fixed 365-day scan window",
            "used_for_tuning": "NO",
            "used_for_calibration": "NO",
            "revealed": "ELIGIBILITY ONLY",
            "used_for_holdout": "NO",
            "safe_for_new_tuning_extension": "NO",
            "why": "failed canonical eligibility in the fixed window; targeted completion/recollection would change selection",
        },
        {
            "pool": "previously screened reserve",
            "profile_count": 10,
            "source_lineage": "excluded before the 1,224-candidate replacement scan",
            "used_for_tuning": "NO",
            "used_for_calibration": "NO",
            "revealed": "YES (screened)",
            "used_for_holdout": "NO",
            "safe_for_new_tuning_extension": "NO",
            "why": "prior screening makes lineage unsuitable for a new extension",
        },
    ]
    _write_csv(args.output_dir / "existing_data_pool_audit.csv", pools)
    _write_json(args.output_dir / "session_support_model.json", support)

    sample_size = {
        "current_tuning_profiles": 791,
        "current_margin_observations": 62,
        "observed_support_rate": 62 / 791,
        "wilson_95": support["wilson_95"],
        "model": support["predictive_model"],
        "observations_still_required": 38,
        "naive_plugin_total_tuning_n": math.ceil(100 / (62 / 791)),
        "naive_plugin_additional_n": math.ceil(38 / (62 / 791)),
        "predictive_95_additional_n": 663,
        "predictive_95_total_n": 1454,
        "predictive_99_additional_n": 758,
        "predictive_99_total_n": 1549,
        "recommended_total_tuning_n": target_total,
        "recommended_additional_tuning_n": additional_total,
        "safe_local_reserve_n": local_reserve,
        "external_eligible_tuning_n": external_tuning_eligible,
        "recommended_probability_of_at_least_100": _beta_binomial_tail(809, 38, 62.5, 729.5),
        "buffer_rationale": "round the 99% predictive result up to 1,600; do not revise after Phase-2 inspection",
    }
    _write_json(args.output_dir / "sample_size_design.json", sample_size)

    sampling = {
        "target_population": "public-profile players observed in sampled OpenDota public matches; this excludes anonymous/private players and is not all Dota players",
        "known_bias": "original V6.1 frame overrepresents players with public histories and players appearing in sampled public matches",
        "fixed_discovery_frame": {
            "public_matches_pages": fixed_public_pages,
            "seed_matches_per_page": 100,
            "seed_match_details": fixed_seed_details,
            "pagination": "strictly descending less_than_match_id from the first page; no extra pages",
            "candidate_count_required_after_deduplication": external_candidates,
            "failure_if_short": "STOP; no adaptive page or account top-up",
        },
        "selection": "deduplicate positive public account IDs, exclude every historical/current candidate and profile, HMAC-rank, retain first 4,135",
        "eligibility_before_history_acquisition": "positive public account ID, not on any historical/current exclusion manifest; no match/session/effect eligibility",
        "allowed_stratification": "none",
        "forbidden_stratification": [
            "known long sessions",
            "known high session count",
            "Session support or effect",
            "Finding yield",
            "rank or MMR",
        ],
        "failed_requests": "record terminal failure, do not retry or replace",
        "private_or_unavailable": "terminal ineligible/failure under the assigned arm; do not replace",
    }
    _write_json(args.output_dir / "sampling_frame_spec.json", sampling)

    split = {
        "salt": "generate 32 random bytes before provider access; store mode 0600; publish only SHA-256 digest until one-shot validation completes",
        "ranking": "HMAC-SHA256(salt, 'v61-session-phase2:' + decimal account ID)",
        "assignment_timing": "after fixed candidate discovery/deduplication and before any player-history request or feature/effect inspection",
        "tuning_extension": {
            "candidate_accounts": tuning_candidates,
            "eligible_profiles_to_use": external_tuning_eligible,
            "plus_local_unused_eligible_reserve": local_reserve,
            "inspection": "full canonical processing allowed after assignment",
        },
        "fresh_sealed_validation": {
            "candidate_accounts": validation_candidates,
            "eligible_profiles_to_seal": fresh_validation_eligible,
            "inspection": "request status, bytes, response shape, and canonical eligibility only; no family features, effects, margins, p-values, or findings",
        },
        "eligible_selection": "within each arm, HMAC order; first required canonically eligible profiles only; extra eligible profiles remain unused reserve",
        "separate_calibration_split": "NONE; margin calibration remains tuning-only and validation remains one-shot",
        "joint_arm_assurance": ">=0.99 by union bound from two arm-wise >=0.995 beta-binomial assurances",
    }
    _write_json(args.output_dir / "split_design.json", split)

    candidate_summary = candidates["summary"]
    per_candidate_raw_bytes = raw_bytes / len(raw_files)
    expected_canonical_bytes = args.corpus.stat().st_size / 1130 * (external_tuning_eligible + fresh_validation_eligible)
    cost = {
        "new_candidate_accounts": {"value": external_candidates, "label": "KNOWN"},
        "new_eligible_tuning_profiles": {"value": external_tuning_eligible, "label": "KNOWN"},
        "fresh_sealed_eligible_profiles": {"value": fresh_validation_eligible, "label": "KNOWN"},
        "fixed_public_matches_requests": {"value": fixed_public_pages, "label": "KNOWN"},
        "fixed_seed_match_detail_requests": {"value": fixed_seed_details, "label": "KNOWN"},
        "fixed_summary_history_requests": {"value": external_candidates, "label": "KNOWN"},
        "expected_physical_requests": {"value": request_ceiling, "label": "ESTIMATED", "basis": "all fixed requests succeed; failures reduce downstream successful responses but are not retried"},
        "maximum_request_ceiling": {"value": request_ceiling, "label": "KNOWN"},
        "history_requests_per_candidate": {"value": 1, "label": "KNOWN"},
        "discovery_overhead_requests_per_candidate": {"value": (fixed_public_pages + fixed_seed_details) / external_candidates, "label": "ESTIMATED"},
        "historical_candidate_yield": {
            "unique_candidates": candidate_summary["unique_candidate_account_ids"],
            "seed_matches": candidate_summary["requested_seed_matches"],
            "label": "MEASURED",
        },
        "raw_archive_measurement": {"files": len(raw_files), "bytes": raw_bytes, "bytes_per_candidate": per_candidate_raw_bytes, "label": "MEASURED"},
        "estimated_new_raw_bytes": {"value": round(per_candidate_raw_bytes * external_candidates), "label": "ESTIMATED"},
        "estimated_canonical_bytes": {"value": round(expected_canonical_bytes), "label": "ESTIMATED"},
        "estimated_total_storage_bytes": {"value": round(per_candidate_raw_bytes * external_candidates + expected_canonical_bytes), "label": "ESTIMATED"},
        "elapsed_minutes_at_240_requests_per_minute": {"value": request_ceiling / 240, "label": "ASSUMED"},
        "elapsed_minutes_at_60_requests_per_minute": {"value": request_ceiling / 60, "label": "ASSUMED"},
        "rate_limit": "sequential requests paced at no more than 240 physical requests/minute; pilot verifies mechanics without changing counts",
        "retry_limit": 0,
        "partial_failure": "record and continue within fixed ceiling; fail the relevant count gate; never replace or top up",
        "currency_cost": {"value": None, "label": "UNKNOWN", "pilot_measurement": "record provider dashboard/request charge for the first 100 assigned histories"},
    }
    _write_json(args.output_dir / "collection_cost_model.json", cost)

    pilot = {
        "decision": "OPTION 2",
        "pilot_n": 100,
        "source": "first 100 HMAC-ranked tuning-arm candidates; included in the fixed 2,848, not additional",
        "may_inspect": ["request mechanics", "failure rate", "response shape", "request cost", "byte size", "runtime"],
        "must_not_inspect": ["Session support", "Session effect", "family output", "margin output", "rank/MMR"],
        "operational_pass": "100 requests attempted within the fixed arm, no schema-contract break, <=10 terminal transport/HTTP failures, observed bytes <=250 MiB total, and the full-collection cost projected from provider accounting fits the owner-approved ceiling",
        "operational_fail": "STOP before the remaining histories; preserve manifests; do not change sample size, frame, retry rule, or arm assignment",
        "continuation": "continue the already-fixed collection after operational checks and owner budget approval; sample counts cannot change",
    }
    _write_json(args.output_dir / "pilot_decision.json", pilot)

    processing = {
        "contract_status": "FROZEN_FROM_EXISTING_CANONICAL V6.1 RESEARCH CODE",
        "history_window": "one 365-day player-summary request, provider limit 10,000, retry limit 0",
        "match_eligibility": "required summary fields valid; lobby_type in {0,7}; game_mode in {1,22}; leaver_status in {0,1}; fixed window; deduplicate match_id and fail closed on conflicting duplicates",
        "abandon_handling": "leaver_status 2-5 excluded; missing/invalid leaver status fails closed",
        "minimum_profile_matches": 30,
        "sessionization": "90-minute start-time gap; 300-second clock tolerance; sessions-5.0.0",
        "completed_session": "exclude corrupt, left-censored first session without a pre-window anchor, and right-censored last session without a >90-minute post-window anchor",
        "early_late": "boundary-safe completed sessions with >=4 matches; sort by start_time, session_index, match_id; compare equal floor(n/2) early and late matches; omit middle match when odd",
        "session_effect": "late-half win rate minus early-half win rate",
        "support": ">=12 informative non-tie completed sessions, >=30 early/late opportunities, and qualifying-session coverage >=50%",
        "estimator": "theta = mean sign(non-zero session effects)",
        "p_value": "two-sided signed-prevalence randomization, 2,000 numpy default_rng draws; seed is first 8 SHA-256 bytes (big-endian) of 'research-signed-prevalence-calibration-1.0.0:<profile_key>:session_drift'; add-one p-value; one component",
        "margin": "linear-interpolated P90 at index (n-1)*0.90 across >=100 tuning profiles of absolute odd/even chronological-interleaved session-theta disagreement, divided by two",
        "stability": "odd and even direction each match full direction with >=6 informative sessions/half; leave-one-session-out direction agreement >=80%",
        "dominant_hero": "exclude most-used hero; require >=30 remaining eligible matches, retained structural support, and same non-zero direction",
        "failure_codes": [
            "history_request_failed",
            "profile_ineligible_fewer_than_30_matches",
            "fewer_than_12_boundary_safe_completed_sessions",
            "fewer_than_12_sessions_with_at_least_4_matches",
            "qualifying_session_coverage_below_50_percent",
            "fewer_than_12_informative_non_tie_sessions",
            "fewer_than_30_early_late_opportunities",
            "fewer_than_6_informative_odd_sessions",
            "fewer_than_6_informative_even_sessions",
            "non_finite_paired_margin",
            "dominant_hero_robustness_failed",
        ],
        "forbidden_changes": "no estimator, threshold, support, margin, stability, or family-question changes",
    }
    _write_json(args.output_dir / "processing_contract.json", processing)

    gates = {
        "gate_1": {"pass": "exact fixed frame and requests complete within ceiling with manifests/digests", "fail": "STOP; no extra pages, requests, replacements, or top-up"},
        "gate_2": {"pass": "for each fixed support-model binning (match depth, session count, median session length, activity window, dominant-hero share), natural-log Jensen-Shannon divergence (zero terms contribute zero) between original 791 and the 769 external eligible tuning profiles <=0.10 and every absolute bin-share difference <=0.15", "fail": "STOP for Sol/owner review; do not tune a corrective sample or alter the frame"},
        "gate_3": {"pass": "combined legitimate tuning Session margin observations >=100", "fail": "STOP; Session remains deferred; no adaptive collection"},
        "gate_4": {"pass": "finite practical margin derivable exactly under frozen method", "fail": "STOP; do not substitute margin method"},
        "gate_5": {"pass": "registered null/type-I, split-half, LOO, dominant-hero, and evidence-completeness checks all pass", "fail": "STOP; Session remains research-only"},
        "gate_6": {"pass": "fixed three-family BY q=.05 validation passes under preregistered dependence stress tests", "fail": "STOP; do not drop a family or switch procedure for yield"},
        "validation_gate": {"pass": "candidate frozen before one-shot sealed validation; validation contract passes", "fail": "release fails; no validation reuse or retuning"},
    }
    _write_json(args.output_dir / "phase2_gates.json", gates)

    multiplicity = {
        "family_universe": ["Transfer", "Post-Loss", "Session Drift"],
        "deferred": ["Presence & Exposure"],
        "q": 0.05,
        "fixed_m": 3,
        "simulation_repetitions_per_cell": 10000,
        "simulation_seed": 20260828,
        "release_procedure": "Benjamini-Yekutieli",
        "unsupported_family_p": 1.0,
        "bh": "diagnostic comparator only; cannot replace BY based on publication yield",
        "stress_scenarios": ["global null", "one moderate alternative", "subset nulls", "independent", "negative feasible dependence", "rho=.5", "rho=.9", "empirical tuning dependence"],
        "acceptance": "BY estimated FDR <=.055 and Wilson lower bound <=.05 in every registered null/dependence scenario",
        "yield_optimization": False,
    }
    _write_json(args.output_dir / "three_family_multiplicity_plan.json", multiplicity)

    validation = {
        "designed": True,
        "run": False,
        "eligible_profiles": fresh_validation_eligible,
        "candidate_arm_size": validation_candidates,
        "sealed_until": "source, manifests, family universe, estimators, null/p-value methods, margins, gates, BY q=.05, and semantic publication rules are frozen and hashed",
        "one_shot": "run once; every assigned eligible profile included in HMAC order through N=339; no exclusions based on outputs; no tuning after reveal",
        "predictive_replication": "before reveal, use tuning counts and Jeffreys beta-binomial prediction to freeze central 99.4444444% intervals (Bonferroni familywise 95% across 9 checks) for supported-profile, positive-direction supported, and analytically-qualified-before-product-cap counts for each of 3 families; all 9 validation counts must fall inside",
        "pass": "all 9 predictive counts are inside their frozen intervals, qualified rows have 100% semantic evidence completeness, and every integrity/checksum/method gate passes; no minimum Finding yield",
        "fail": "V6.1 three-family release fails; do not recycle validation profiles or adapt the candidate",
        "must_freeze": ["source SHA", "corpus/split manifest", "family universe", "estimators", "null methods", "p-value methods", "practical margins", "stability gates", "robustness gates", "multiplicity procedure", "q", "semantic publication rules"],
    }
    _write_json(args.output_dir / "fresh_validation_plan.json", validation)

    aggregate = {
        "status": "PARTIAL",
        "reason": "request budget and provider cost require owner approval; analytical policy is otherwise predeclared",
        "analytical_base_sha": ANALYTICAL_BASE,
        "analytical_source_sha": SOURCE_SHA,
        "frozen_artifact_digest": ARTIFACT_DIGEST,
        "corpus_sha256": hashlib.sha256(args.corpus.read_bytes()).hexdigest(),
        "split_sha256": hashlib.sha256(args.split.read_bytes()).hexdigest(),
        "can_local_data_alone_reach_target": False,
        "sample_size": sample_size,
        "external_candidate_accounts": external_candidates,
        "request_ceiling": request_ceiling,
        "owner_cost_approval_required": True,
        "phase2_policy_choices_remaining": 0,
        "external_provider_calls": 0,
        "old_holdout_profiles_evaluated": 0,
        "fresh_holdout_profiles_evaluated": 0,
        "production_analytical_changes": 0,
    }
    _write_json(args.output_dir / "aggregate_summary.json", aggregate)
    print(json.dumps(aggregate, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
