#!/usr/bin/env python3
"""Validate research-only signed-prevalence inference for four V6.1 families."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from v61_findings_statistical_hardening import _offline_guard, _wilson, _write_csv, _write_json

TARGET_ALPHA = 0.05
MAX_ACCEPTABLE_ALPHA = 0.065
MIN_SESSIONS = 12
EFFECTS = (0.05, 0.15, 0.30, 0.50)
COMMON_SCENARIOS = (
    "exact_zero_effect",
    "gaussian_null",
    "skewed_magnitude_null",
    "heavy_tailed_null",
    "unequal_session_sizes",
    "low_sessions_floor",
    "high_sessions",
    "low_opportunity_floor",
    "high_opportunity",
    "strong_component_correlation",
    "heteroskedastic_sessions",
    "dominant_session",
    "missing_component_support",
    "below_support_fail_closed",
)
FAMILY_SCENARIOS = {
    "transfer": ("session_sign_reversal", "band_imbalance_null"),
    "post_loss_response": (
        "unequal_state_frequency_null",
        "overlapping_transition_dependence_null",
    ),
    "presence_exposure_link": (
        "between_session_confounding_only",
        "nonlinear_symmetric_null",
        "single_session_relationship_null",
    ),
    "session_drift": (
        "session_length_selection_null",
        "session_sign_reversal",
        "single_session_change_null",
        "left_censored_sessions_excluded",
    ),
}
FAMILY_LABELS = {
    "transfer": "Transfer",
    "post_loss_response": "Post-Loss Response",
    "presence_exposure_link": "Presence & Exposure",
    "session_drift": "Session Drift",
}
COMPONENTS = {
    "transfer": ("outcome", "activity", "survival"),
    "post_loss_response": ("one_loss_vs_win", "two_plus_losses_vs_win", "win_streak_vs_win"),
    "presence_exposure_link": ("within_session_involvement_exposure_slope",),
    "session_drift": ("late_minus_early_result",),
}


def _contracts() -> dict[str, Any]:
    shared = {
        "candidate_lineage": "research-signed-prevalence-1.0.0",
        "null_draws": 2_000,
        "alpha": TARGET_ALPHA,
        "independent_unit": "session",
        "effect_estimand": "theta = P(session effect > 0) - P(session effect < 0)",
        "null_hypothesis": "H0: theta = 0 for every predeclared supported component",
        "test": "two-sided Monte Carlo sign randomization with add-one p-value",
        "ties": "zero session effects are reported and excluded from the sign denominator",
        "invalid_draw_behavior": "unsupported components receive p=1; a family with no supported component abstains",
        "practical_margin": "DEFERRED_REQUIRES_NEW_ESTIMAND_CALIBRATION",
    }
    return {
        "pool_shape": {
            "status": "DEMOTED_TO_ELEMENTS",
            "family_test": None,
            "reason": "Breadth and Toolkit own the supported descriptive constructs",
        },
        "transfer": {
            **shared,
            "display_name": FAMILY_LABELS["transfer"],
            "player_question": "What survives when the hero changes?",
            "raw_unit": "eligible match in a fixed cross-fitted core or reliable-stretch band",
            "session_effect": "reliable-stretch session mean minus core session mean",
            "components": list(COMPONENTS["transfer"]),
            "support": {
                "informative_paired_sessions_per_component": 12,
                "component_complete_matches_per_band": 30,
                "context_coverage": 0.80,
                "band_assignment": "fixed before inference",
            },
            "internal_multiplicity": "Bonferroni over all 3 fixed components; unsupported component p=1",
            "claim_boundary": "stable signed prevalence of a covered component change, not hero-choice causality",
        },
        "post_loss_response": {
            **shared,
            "display_name": FAMILY_LABELS["post_loss_response"],
            "player_question": "How does the next same-session hero choice move after supported result states?",
            "raw_unit": "chronological adjacent same-session transition",
            "states": ["win", "one_loss", "two_plus_losses", "win_streak"],
            "reference_state": "win",
            "session_effect": "target-state session mean movement minus win-state session mean movement",
            "components": list(COMPONENTS["post_loss_response"]),
            "support": {
                "informative_paired_sessions_per_contrast": 12,
                "transitions_across_compared_states": 30,
                "context_coverage": 0.80,
                "cross_session_transitions": "forbidden",
            },
            "internal_multiplicity": "Bonferroni over all 3 fixed contrasts; unsupported contrast p=1",
            "claim_boundary": "same-session result-state association, not psychology or causality",
        },
        "presence_exposure_link": {
            **shared,
            "display_name": FAMILY_LABELS["presence_exposure_link"],
            "player_question": "When your scoreboard involvement rises, what happens to your death exposure?",
            "raw_unit": "paired context-adjusted per-match involvement and death-exposure rates",
            "session_effect": "sign of the within-session centered least-squares slope",
            "components": list(COMPONENTS["presence_exposure_link"]),
            "support": {
                "qualifying_sessions": 12,
                "paired_matches": 30,
                "paired_matches_per_session": 3,
                "context_coverage": 0.80,
                "within_session_involvement_variation": "required",
            },
            "internal_multiplicity": "one predeclared relationship",
            "claim_boundary": "bounded within-session summary-rate association, not aggression, positioning, or causality",
        },
        "session_drift": {
            **shared,
            "display_name": FAMILY_LABELS["session_drift"],
            "player_question": "Within completed sessions, what changes from early to late?",
            "raw_unit": "eligible match in a boundary-safe completed session",
            "session_effect": "late-half win rate minus early-half win rate; middle match omitted when odd",
            "components": list(COMPONENTS["session_drift"]),
            "support": {
                "informative_completed_sessions": 12,
                "matches_per_session": 4,
                "qualifying_session_coverage": 0.50,
                "left_censored": "excluded",
                "right_censored_or_corrupt": "excluded",
            },
            "internal_multiplicity": "one predeclared result component",
            "claim_boundary": "repeated early-to-late result direction, not fatigue or causality",
        },
    }


def _candidate_methods() -> dict[str, Any]:
    return {
        "selected": {
            "method": "session_signed_prevalence_randomization",
            "reason": "tests the predeclared repeated-direction estimand without magnitude, tail, or cluster-size assumptions",
            "multi_component_family_rule": "fixed Bonferroni union bound; valid under arbitrary component dependence",
        },
        "rejected": [
            {
                "method": "scalar_centered_cluster_bootstrap",
                "reason": "previous known-truth simulations were anti-conservative and did not impose the joint null",
            },
            {
                "method": "pooled_match_permutation",
                "reason": "matches are not exchangeable across sessions, bands, or result states",
            },
            {
                "method": "mean_session_effect_t_test",
                "reason": "changes the estimand and remains sensitive to dominant and heavy-tailed session magnitudes",
            },
        ],
        "known_limitations": [
            "magnitude is descriptive until new practical margins are calibrated",
            "the null is sign balance, not zero mean",
            "session independence and structural eligibility remain required",
            "current V6 context cannot remove unobserved hero, role, draft, opponent, or match-state confounding",
        ],
    }


def _scenario_values(
    family: str, scenario: str, count: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    components = len(COMPONENTS[family])
    sessions = 24
    opportunities = np.full((count, components), 60)
    if scenario == "low_sessions_floor":
        sessions = MIN_SESSIONS
    elif scenario == "high_sessions":
        sessions = 60
    elif scenario == "low_opportunity_floor":
        opportunities.fill(30)
    elif scenario == "high_opportunity":
        opportunities.fill(240)
    elif scenario == "below_support_fail_closed":
        sessions = MIN_SESSIONS - 1
        opportunities.fill(29)

    signs = rng.choice((-1.0, 1.0), size=(count, sessions, components))
    magnitudes = np.abs(rng.normal(1.0, 0.25, size=signs.shape))
    if scenario == "exact_zero_effect":
        return np.zeros_like(signs), opportunities
    if scenario == "gaussian_null":
        return rng.normal(0.0, 1.0, size=signs.shape), opportunities
    if scenario == "skewed_magnitude_null":
        magnitudes = rng.lognormal(0.0, 1.0, size=signs.shape)
    elif scenario == "heavy_tailed_null":
        magnitudes = np.abs(rng.standard_t(2.5, size=signs.shape))
    elif scenario == "unequal_session_sizes":
        magnitudes *= np.geomspace(0.1, 8.0, sessions)[None, :, None]
    elif scenario == "strong_component_correlation" and components > 1:
        signs = np.repeat(signs[:, :, :1], components, axis=2)
    elif scenario == "heteroskedastic_sessions":
        magnitudes *= np.linspace(0.15, 3.0, sessions)[None, :, None]
    elif scenario == "dominant_session":
        magnitudes[:, 0, :] *= 100.0
    elif scenario == "missing_component_support":
        signs[:, 11:, -1] = np.nan
        opportunities[:, -1] = 20
    elif scenario in {"session_sign_reversal", "sign_reversal_by_session"}:
        signs[:] = 1.0
        signs[:, sessions // 2 :, :] = -1.0
    elif scenario in {
        "band_imbalance_null",
        "unequal_state_frequency_null",
        "overlapping_transition_dependence_null",
        "between_session_confounding_only",
        "nonlinear_symmetric_null",
        "session_length_selection_null",
        "left_censored_sessions_excluded",
    }:
        magnitudes *= rng.lognormal(0.0, 0.7, size=signs.shape)
    elif scenario in {"single_session_relationship_null", "single_session_change_null"}:
        magnitudes[:, 0, :] *= 50.0
    return signs * magnitudes, opportunities


def _family_p(
    values: np.ndarray,
    opportunities: np.ndarray,
    *,
    draws: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    signs = np.sign(values)
    informative = np.isfinite(signs) & (signs != 0)
    totals = informative.sum(axis=1)
    observed = np.abs(np.where(informative, signs, 0).sum(axis=1))
    supported = (totals >= MIN_SESSIONS) & (opportunities >= 30)
    null_positive = rng.binomial(
        totals[:, None, :], 0.5, size=(len(values), draws, values.shape[2])
    )
    null_statistic = np.abs(2 * null_positive - totals[:, None, :])
    component_p = (1 + (null_statistic >= observed[:, None, :]).sum(axis=1)) / (draws + 1)
    component_p = np.where(supported, component_p, 1.0)
    family_p = np.minimum(1.0, values.shape[2] * component_p.min(axis=1))
    theta = np.divide(
        np.where(informative, signs, 0).sum(axis=1),
        totals,
        out=np.zeros_like(observed, dtype=float),
        where=totals > 0,
    )
    return family_p, component_p, theta, totals, supported


def _simulate_type1(
    *, repetitions: int, draws: int, seed: int, batch_size: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = np.random.default_rng(seed)
    detail: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    for family in COMPONENTS:
        for scenario in (*COMMON_SCENARIOS, *FAMILY_SCENARIOS[family]):
            scenario_p: list[float] = []
            unsupported = 0
            for start in range(0, repetitions, batch_size):
                count = min(batch_size, repetitions - start)
                values, opportunities = _scenario_values(family, scenario, count, rng)
                family_p, component_p, theta, totals, supported = _family_p(
                    values, opportunities, draws=draws, rng=rng
                )
                scenario_p.extend(float(value) for value in family_p)
                unsupported += int(np.all(~supported, axis=1).sum())
                for offset in range(count):
                    detail.append(
                        {
                            "family": family,
                            "scenario": scenario,
                            "dataset": start + offset,
                            "family_p": float(family_p[offset]),
                            "reject_at_0_05": bool(family_p[offset] <= TARGET_ALPHA),
                            "component_p": json.dumps(component_p[offset].tolist()),
                            "theta_hat": json.dumps(theta[offset].tolist()),
                            "informative_sessions": json.dumps(totals[offset].tolist()),
                            "opportunities": json.dumps(opportunities[offset].tolist()),
                        }
                    )
            p_array = np.asarray(scenario_p)
            rejections = int((p_array <= TARGET_ALPHA).sum())
            lower, upper = _wilson(rejections, repetitions)
            verdict = (
                "PASS"
                if rejections / repetitions <= MAX_ACCEPTABLE_ALPHA and lower <= TARGET_ALPHA
                else "FAIL"
            )
            summary.append(
                {
                    "family": family,
                    "scenario": scenario,
                    "repetitions": repetitions,
                    "null_draws_per_dataset": draws,
                    "rejections": rejections,
                    "estimated_alpha": rejections / repetitions,
                    "mc_ci95_lower": lower,
                    "mc_ci95_upper": upper,
                    "mean_p": float(p_array.mean()),
                    "p05": float(np.quantile(p_array, 0.05)),
                    "p50": float(np.quantile(p_array, 0.50)),
                    "p95": float(np.quantile(p_array, 0.95)),
                    "unsupported_datasets": unsupported,
                    "acceptance_rule": f"alpha <= {MAX_ACCEPTABLE_ALPHA} and Wilson lower <= {TARGET_ALPHA}",
                    "verdict": verdict,
                }
            )
    return detail, summary


def _family_verdicts(type1_rows: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts: dict[str, Any] = {}
    for family in COMPONENTS:
        relevant = [row for row in type1_rows if row["family"] == family]
        failures = [row["scenario"] for row in relevant if row["verdict"] == "FAIL"]
        verdicts[family] = {
            "status": "METHOD_VALIDATED_WITH_LIMITATIONS"
            if not failures
            else "METHOD_REQUIRES_MODIFICATION",
            "type1_pass": not failures,
            "failed_scenarios": failures,
            "maximum_estimated_alpha": max(float(row["estimated_alpha"]) for row in relevant),
            "power_allowed": not failures,
            "limitations": [
                "signed prevalence does not estimate mean magnitude",
                "practical margins, stability gates, and external multiplicity remain unfrozen",
            ],
        }
    return verdicts


def _simulate_power(
    verdicts: dict[str, Any], *, repetitions: int, draws: int, seed: int, batch_size: int
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    sessions = 60
    for family, components in COMPONENTS.items():
        if not verdicts[family]["power_allowed"]:
            rows.append({"family": family, "status": "NOT_RUN_TYPE1_FAILURE"})
            continue
        for effect in EFFECTS:
            p_values: list[float] = []
            theta_values: list[float] = []
            covered = 0
            for start in range(0, repetitions, batch_size):
                count = min(batch_size, repetitions - start)
                values = rng.choice((-1.0, 1.0), size=(count, sessions, len(components)))
                values[:, :, 0] = np.where(
                    rng.random((count, sessions)) < (1 + effect) / 2, 1.0, -1.0
                )
                opportunities = np.full((count, len(components)), 120)
                family_p, _component_p, theta, totals, _supported = _family_p(
                    values, opportunities, draws=draws, rng=rng
                )
                p_values.extend(float(value) for value in family_p)
                theta_values.extend(float(value) for value in theta[:, 0])
                for successes, total in zip(
                    ((theta[:, 0] + 1) * totals[:, 0] / 2).astype(int),
                    totals[:, 0],
                    strict=True,
                ):
                    low, high = _wilson(int(successes), int(total))
                    covered += low <= (1 + effect) / 2 <= high
            p_array = np.asarray(p_values)
            theta_array = np.asarray(theta_values)
            rows.append(
                {
                    "family": family,
                    "status": "RUN",
                    "true_theta": effect,
                    "repetitions": repetitions,
                    "sessions_per_dataset": sessions,
                    "null_draws_per_dataset": draws,
                    "power_at_0_05": float((p_array <= TARGET_ALPHA).mean()),
                    "mean_theta_hat": float(theta_array.mean()),
                    "theta_bias": float(theta_array.mean() - effect),
                    "wilson_coverage_95": covered / repetitions,
                    "correct_direction_rate": float((theta_array > 0).mean()),
                    "support_failure_rate": 0.0,
                }
            )
    return rows


def _multiplicity_readiness(
    verdicts: dict[str, Any], *, repetitions: int, draws: int, seed: int
) -> dict[str, Any]:
    if not all(value["type1_pass"] for value in verdicts.values()):
        return {
            "status": "BLOCKED_BY_FAMILY_METHOD",
            "bh_finalized": False,
            "candidate_family_universe": list(COMPONENTS),
        }
    rng = np.random.default_rng(seed)
    sessions = 36
    covariance = np.full((4, 4), 0.45)
    np.fill_diagonal(covariance, 1.0)
    latent = rng.multivariate_normal(np.zeros(4), covariance, size=(repetitions, sessions))
    family_p: list[np.ndarray] = []
    for index, (_family, components) in enumerate(COMPONENTS.items()):
        values = rng.choice((-1.0, 1.0), size=(repetitions, sessions, len(components)))
        values[:, :, 0] = np.where(latent[:, :, index] >= 0, 1.0, -1.0)
        opportunities = np.full((repetitions, len(components)), 90)
        p_value, _component_p, _theta, _totals, _supported = _family_p(
            values, opportunities, draws=draws, rng=rng
        )
        family_p.append(p_value)
    correlation = np.corrcoef(np.column_stack(family_p), rowvar=False)
    labels = list(COMPONENTS)
    return {
        "status": "READY_FOR_FOUR_FAMILY_DEPENDENCY_VALIDATION",
        "bh_finalized": False,
        "candidate_family_universe": labels,
        "candidate_m": 4,
        "pool_in_family_universe": False,
        "synthetic_screen_repetitions": repetitions,
        "synthetic_latent_correlation": 0.45,
        "p_value_pearson_correlation": {
            labels[row]: {labels[column]: float(correlation[row, column]) for column in range(4)}
            for row in range(4)
        },
        "decision": "do not choose BH until retained p-value dependence is validated on the authorized tuning partition",
    }


def _self_check() -> None:
    rng = np.random.default_rng(7)
    values = np.array([[[1.0], [-1.0]] * 6, [[1.0], [1.0]] * 6])
    opportunities = np.full((2, 1), 30)
    family_p, _component_p, theta, totals, _supported = _family_p(
        values, opportunities, draws=2_000, rng=rng
    )
    assert totals.tolist() == [[12], [12]]
    assert theta[:, 0].tolist() == [0.0, 1.0]
    assert family_p[0] > 0.5 and family_p[1] < 0.01
    unsupported_p, *_ = _family_p(values[:, :11], opportunities, draws=2_000, rng=rng)
    assert unsupported_p.tolist() == [1.0, 1.0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=1_000)
    parser.add_argument("--draws", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    if args.repetitions < 1_000 or args.draws != 2_000:
        raise SystemExit("design validation requires >=1,000 datasets and exactly 2,000 null draws")
    _offline_guard()
    _self_check()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    contracts = _contracts()
    _write_json(output / "family_contracts.json", contracts)
    _write_json(output / "candidate_methods.json", _candidate_methods())
    detail, type1 = _simulate_type1(
        repetitions=args.repetitions,
        draws=args.draws,
        seed=args.seed,
        batch_size=args.batch_size,
    )
    _write_csv(output / "null_simulation_results.csv", detail)
    _write_csv(output / "type1_summary.csv", type1)
    verdicts = _family_verdicts(type1)
    _write_json(output / "family_method_verdicts.json", verdicts)
    power = _simulate_power(
        verdicts,
        repetitions=args.repetitions,
        draws=args.draws,
        seed=args.seed + 1,
        batch_size=args.batch_size,
    )
    _write_csv(output / "power_results.csv", power)
    _write_csv(
        output / "tuning_method_behavior.csv",
        [
            {
                "family": family,
                "status": "NOT_RUN_NOT_REQUIRED_FOR_METHOD_VALIDATION",
                "publication_yield_optimized": False,
            }
            for family in COMPONENTS
        ],
    )
    _write_csv(
        output / "margin_transferability.csv",
        [
            {
                "family": family,
                "old_margin_transferable": "NO",
                "reason": "estimand changed from magnitude/zone statistics to signed session prevalence",
                "next_action": "derive tuning-only practical margin after method and dependency validation",
            }
            for family in COMPONENTS
        ],
    )
    multiplicity = _multiplicity_readiness(
        verdicts, repetitions=args.repetitions, draws=args.draws, seed=args.seed + 2
    )
    _write_json(output / "multiplicity_readiness.json", multiplicity)
    all_pass = all(value["type1_pass"] for value in verdicts.values())
    aggregate = {
        "status": "PASS" if all_pass else "PARTIAL",
        "next_status": (
            "READY_FOR_MARGIN_STABILITY_AND_MULTIPLICITY_CALIBRATION"
            if all_pass
            else "BLOCKED_PENDING_FAMILY_METHOD"
        ),
        "method": "session_signed_prevalence_randomization",
        "families": verdicts,
        "type1_scenarios": len(type1),
        "repetitions_per_scenario": args.repetitions,
        "null_draws_per_dataset": args.draws,
        "acceptance_rule": f"estimated alpha <= {MAX_ACCEPTABLE_ALPHA} and Wilson lower <= {TARGET_ALPHA}",
        "power_run_only_after_type1_pass": True,
        "margins_derived": False,
        "bh_finalized": False,
        "holdout_reruns": 0,
        "external_collection_calls": 0,
        "production_changes": 0,
        "numpy_version": np.__version__,
        "seed": args.seed,
    }
    _write_json(output / "aggregate_summary.json", aggregate)
    print(json.dumps(aggregate, sort_keys=True))
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
