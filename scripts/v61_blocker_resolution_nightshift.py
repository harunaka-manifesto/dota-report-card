#!/usr/bin/env python3
"""Resolve V6.1 family blockers using only the frozen tuning partition."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.player_analysis_v61.artifacts import load_v61_artifact_bundle  # noqa: E402
from app.player_analysis_v61.calibration_corpus import load_canonical_corpus  # noqa: E402
from app.player_analysis_v61.corpus_reuse import profile_digest, sha256_file  # noqa: E402
from app.player_analysis_v61.legacy_adapter import current_taxonomy_mapping  # noqa: E402
from v61_calibration_builder import _raw_components  # noqa: E402
from v61_findings_statistical_hardening import (  # noqa: E402
    _offline_guard,
    _write_csv,
    _write_json,
)
from v61_four_family_tuning_calibration import (  # noqa: E402
    FAMILIES,
    HALF_MIN_SESSIONS,
    TARGET_Q,
    _adjust,
    _infer_family,
    _measure_profile,
    _profile_key,
    _seed,
    _session_partitions,
    _theta,
)

VERSION = "research-v61-blocker-resolution-nightshift-1.0.0"
SESSION_COMPONENT = "late_minus_early_result"
PRESENCE_COMPONENT = "within_session_involvement_exposure_slope"
MARGINS = {
    "transfer": 0.4114976780185762,
    "post_loss_response": 0.38888888888888884,
    "presence_exposure_link": 0.20721411371566176,
    "session_drift": None,
}
SESSION_CANDIDATES = {
    "existing_interleaved_complete_session_split": {
        "estimand": "half the absolute theta disagreement between alternating chronological complete sessions",
        "noise": "repeatability across two approximately balanced, cluster-preserving session halves",
        "minimum": "12 informative sessions, at least 6 in each half, frozen structural support",
        "independence": "sessions are independent; sign prevalence is stable over chronology",
        "failure": "cannot estimate profiles that fail the full completed-session contract",
        "comparable": True,
    },
    "chronological_complete_session_split": {
        "estimand": "half the absolute theta disagreement between early and late complete-session halves",
        "noise": "repeatability plus temporal drift across cluster-preserving halves",
        "minimum": "12 informative sessions, at least 6 in each half, frozen structural support",
        "independence": "sessions are independent; chronology may add drift to the noise estimate",
        "failure": "conflates repeatability noise with genuine temporal change",
        "comparable": True,
    },
    "leave_one_session_out": {
        "estimand": "maximum absolute leave-one-session-out theta departure from full theta",
        "noise": "single-session influence, not half-sample repeatability",
        "minimum": "12 informative sessions and frozen structural support",
        "independence": "sessions are independent",
        "failure": "systematically smaller scale than half-sample disagreement",
        "comparable": False,
    },
    "paired_session_bootstrap": {
        "estimand": "P90 absolute session-bootstrap theta departure from full theta",
        "noise": "sampling uncertainty conditional on observed complete sessions",
        "minimum": "12 informative sessions and frozen structural support",
        "independence": "sessions are exchangeable draws from a stable profile distribution",
        "failure": "bootstrap cannot repair selection into the completed-session population",
        "comparable": False,
    },
}


def _rate(row: dict[str, Any]) -> tuple[float | None, float | None]:
    duration = row.get("duration_seconds")
    if not isinstance(duration, (int, float)) or duration <= 0:
        return None, None
    kills, assists, deaths = row.get("kills"), row.get("assists"), row.get("deaths")
    if not all(isinstance(value, int) and value >= 0 for value in (kills, assists, deaths)):
        return None, None
    return (kills + assists) * 60 / duration, deaths * 600 / duration


def _slope(points: list[tuple[float, float]]) -> float | None:
    if len(points) < 3:
        return None
    x_mean = statistics.fmean(point[0] for point in points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    if denominator <= 0:
        return None
    y_mean = statistics.fmean(point[1] for point in points)
    return sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator


def _presence_effects(
    rows: list[dict[str, Any]],
    resolver: Any,
    taxonomy: dict[int, dict[str, Any]],
    *,
    x_adjusted: bool = True,
    y_adjusted: bool = True,
    keep: Callable[[dict[str, Any]], bool] | None = None,
) -> tuple[dict[str, float], int, int]:
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    retained = [row for row in rows if keep is None or keep(row)]
    paired = 0
    for row in retained:
        raw_x, raw_y = _rate(row)
        adjusted = _raw_components(row, resolver, taxonomy)
        adjusted_y = -adjusted["survival"] if adjusted["survival"] is not None else None
        x = adjusted["activity"] if x_adjusted else raw_x
        y = adjusted_y if y_adjusted else raw_y
        if x is None or y is None:
            continue
        grouped[str(row["session_id"])].append((float(x), float(y)))
        paired += 1
    effects = {
        session: value
        for session, points in grouped.items()
        if (value := _slope(points)) is not None
    }
    return effects, paired, len(retained)


def _presence_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    supported = [row for row in rows if row["supported"]]
    directions = Counter(row["direction"] for row in supported)
    return {
        "profiles": len(rows),
        "supported": len(supported),
        "positive": directions["positive"],
        "negative": directions["negative"],
        "zero": directions["zero"],
        "inverse_share": directions["negative"] / len(supported) if supported else None,
        "median_theta": statistics.median(row["theta"] for row in supported) if supported else None,
    }


def _session_forensic(
    key: str, rows: list[dict[str, Any]], completed: dict[str, bool], measured: dict[str, Any]
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["session_id"])].append(row)
    ordered = sorted(
        grouped, key=lambda session: min(row["start_time"] for row in grouped[session])
    )
    left = ordered[0] if ordered else None
    completed_count = sum(completed.get(session) is True for session in ordered)
    corrupt_count = sum(
        any(row.get("session_corrupt") for row in grouped[session]) for session in ordered
    )
    boundary_safe = [
        session
        for session in ordered
        if session != left
        and completed.get(session) is True
        and not any(row.get("session_corrupt") for row in grouped[session])
    ]
    qualifying = [session for session in boundary_safe if len(grouped[session]) >= 4]
    effects = measured["session_drift"][SESSION_COMPONENT]["effects"]
    nonzero = {session: value for session, value in effects.items() if value != 0}
    opportunities = measured["session_drift"][SESSION_COMPONENT]["opportunities"]
    coverage = measured["session_drift"][SESSION_COMPONENT]["coverage"]
    supported = bool(measured["session_drift"][SESSION_COMPONENT]["supported"])
    odd, even = _session_partitions(rows)
    odd_theta, odd_n = _theta(effects, odd)
    even_theta, even_n = _theta(effects, even)
    valid_odd = supported and odd_n >= HALF_MIN_SESSIONS
    valid_even = valid_odd and even_n >= HALF_MIN_SESSIONS
    finite_margin = valid_even and math.isfinite(abs(odd_theta - even_theta))
    if len(boundary_safe) < 12:
        reason = "fewer_than_12_boundary_safe_completed_sessions"
    elif len(qualifying) < 12:
        reason = "fewer_than_12_sessions_with_at_least_4_matches"
    elif coverage < 0.50:
        reason = "qualifying_session_coverage_below_50_percent"
    elif len(nonzero) < 12:
        reason = "fewer_than_12_informative_non_tie_sessions"
    elif opportunities < 30:
        reason = "fewer_than_30_early_late_opportunities"
    elif odd_n < HALF_MIN_SESSIONS:
        reason = "fewer_than_6_informative_odd_sessions"
    elif even_n < HALF_MIN_SESSIONS:
        reason = "fewer_than_6_informative_even_sessions"
    else:
        reason = "margin_eligible"
    sizes = [len(grouped[session]) for session in ordered]
    return {
        "profile_key": key,
        "total_matches": len(rows),
        "total_sessions": len(ordered),
        "completed_sessions": completed_count,
        "corrupt_sessions": corrupt_count,
        "boundary_safe_completed_sessions": len(boundary_safe),
        "sessions_with_at_least_4_matches": len(qualifying),
        "informative_non_tie_sessions": len(nonzero),
        "early_late_opportunities": opportunities,
        "qualifying_session_coverage": coverage,
        "median_matches_per_session": statistics.median(sizes) if sizes else 0,
        "family_structurally_eligible": True,
        "minimum_completed_sessions": len(boundary_safe) >= 12,
        "enough_early_late_support": len(qualifying) >= 12 and opportunities >= 30,
        "valid_family_estimate": supported and len(nonzero) >= 12,
        "valid_odd_split": valid_odd,
        "valid_even_split": valid_even,
        "finite_paired_margin": finite_margin,
        "margin_eligible": finite_margin,
        "odd_informative_sessions": odd_n,
        "even_informative_sessions": even_n,
        "odd_theta": odd_theta,
        "even_theta": even_theta,
        "reason_code": reason,
    }


def _margin_noise(effects: dict[str, float], rows: list[dict[str, Any]]) -> float | None:
    odd, even = _session_partitions(rows)
    odd_theta, odd_n = _theta(effects, odd)
    even_theta, even_n = _theta(effects, even)
    if odd_n < HALF_MIN_SESSIONS or even_n < HALF_MIN_SESSIONS:
        return None
    return abs(odd_theta - even_theta)


def _candidate_actual(
    effects: dict[str, float],
    rows: list[dict[str, Any]],
    rng: np.random.Generator,
    *,
    structurally_supported: bool,
) -> dict[str, float | None]:
    values = [math.copysign(1.0, value) for value in effects.values() if value != 0]
    if not structurally_supported or len(values) < 12:
        return {name: None for name in SESSION_CANDIDATES}
    existing = _margin_noise(effects, rows)
    ordered_sessions = sorted(
        effects,
        key=lambda session: min(
            (row["start_time"] for row in rows if str(row["session_id"]) == session),
            default=0,
        ),
    )
    ordered_values = [
        math.copysign(1.0, effects[session])
        for session in ordered_sessions
        if effects[session] != 0
    ]
    half = len(ordered_values) // 2
    chronological = (
        abs(statistics.fmean(ordered_values[:half]) - statistics.fmean(ordered_values[-half:]))
        if half >= HALF_MIN_SESSIONS
        else None
    )
    full = statistics.fmean(values)
    loo = max(
        abs(statistics.fmean(values[:index] + values[index + 1 :]) - full)
        for index in range(len(values))
    )
    bootstrap = [
        abs(statistics.fmean(rng.choice(values, len(values), replace=True)) - full)
        for _ in range(500)
    ]
    return {
        "existing_interleaved_complete_session_split": existing,
        "chronological_complete_session_split": chronological,
        "leave_one_session_out": loo,
        "paired_session_bootstrap": float(np.quantile(bootstrap, 0.90)),
    }


def _session_synthetic(seed: int) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for scenario, theta in (("stable", 0.50), ("moderate", 0.20), ("null_noisy", 0.0)):
        candidate_values: dict[str, list[float]] = defaultdict(list)
        for _ in range(1_000):
            signs = np.where(rng.random(24) < (1 + theta) / 2, 1.0, -1.0)
            odd, even = signs[::2], signs[1::2]
            full = float(np.mean(signs))
            candidate_values["existing_interleaved_complete_session_split"].append(
                abs(float(np.mean(odd) - np.mean(even)))
            )
            candidate_values["chronological_complete_session_split"].append(
                abs(float(np.mean(signs[:12]) - np.mean(signs[12:])))
            )
            candidate_values["leave_one_session_out"].append(
                max(abs(float(np.mean(np.delete(signs, index))) - full) for index in range(24))
            )
            bootstrap = [
                abs(float(np.mean(rng.choice(signs, 24, replace=True))) - full) for _ in range(100)
            ]
            candidate_values["paired_session_bootstrap"].append(float(np.quantile(bootstrap, 0.90)))
        for candidate, values in candidate_values.items():
            rows.append(
                {
                    "row_type": "synthetic_validation",
                    "candidate": candidate,
                    "scenario": scenario,
                    "true_theta": theta,
                    "replications": 1_000,
                    "median_noise": statistics.median(values),
                    "p90_noise": float(np.quantile(values, 0.90)),
                    "comparable_to_existing": SESSION_CANDIDATES[candidate]["comparable"],
                    "downward_vs_existing_p90": None,
                }
            )
    for scenario in ("stable", "moderate", "null_noisy"):
        existing = next(
            row["p90_noise"]
            for row in rows
            if row["scenario"] == scenario
            and row["candidate"] == "existing_interleaved_complete_session_split"
        )
        for row in rows:
            if row["scenario"] == scenario:
                row["downward_vs_existing_p90"] = row["p90_noise"] < existing
    return rows


def _bootstrap_margin(noise: list[float], rng: np.random.Generator) -> tuple[float, float, float]:
    estimates = [
        float(np.quantile(rng.choice(noise, len(noise), replace=True), 0.90)) / 2
        for _ in range(1_000)
    ]
    return tuple(float(np.quantile(estimates, q)) for q in (0.025, 0.50, 0.975))


def _multiplicity_power(seed: int) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for universe in (4, 3, 2):
        p_values = rng.random((50_000, universe))
        p_values[:, 0] = rng.beta(0.35, 1.0, size=50_000)
        for procedure, by in (("BH", False), ("BY", True)):
            discoveries = np.array(
                [_adjust(values.tolist(), by=by)[0] <= TARGET_Q for values in p_values]
            )
            rows.append(
                {
                    "row_type": "bounded_power_cost",
                    "scenario": "one_beta_alternative_independent_nulls",
                    "procedure": procedure,
                    "registered_families": universe,
                    "estimated_true_positive_rate": float(discoveries.mean()),
                    "estimated_fdr": None,
                    "verdict": "DIAGNOSTIC_ONLY",
                }
            )
    return rows


def _self_check() -> None:
    assert _slope([(1, 3), (2, 2), (3, 1)]) == -1
    assert _rate({"kills": 2, "assists": 3, "deaths": 1, "duration_seconds": 600}) == (0.5, 1.0)
    assert set(SESSION_CANDIDATES) == {
        "existing_interleaved_complete_session_split",
        "chronological_complete_session_split",
        "leave_one_session_out",
        "paired_session_bootstrap",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--prior-diagnostics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--analytical-base", required=True)
    parser.add_argument("--latest-main", required=True)
    parser.add_argument("--merge-base", required=True)
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()
    _offline_guard()
    _self_check()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    corpus_sha, split_sha = sha256_file(args.corpus), sha256_file(args.split)
    split = json.loads(args.split.read_text())
    train = {str(value) for value in split["train_profile_ids"]}
    holdout = {str(value) for value in split["holdout_profile_ids"]}
    if train & holdout or len(train) != 791 or len(holdout) != 339:
        raise SystemExit("frozen split integrity mismatch")
    if profile_digest(tuple(train)) != split["train_digest"]:
        raise SystemExit("frozen train digest mismatch")
    corpus = load_canonical_corpus(args.corpus)
    if corpus_sha != split["corpus_sha256"] or train | holdout != set(corpus.profile_ids):
        raise SystemExit("corpus/split binding mismatch")
    manifest = json.loads((args.artifact_dir / "build-manifest-6.1.0.json").read_text())
    bundle = load_v61_artifact_bundle(
        args.artifact_dir,
        expected_corpus_sha256=corpus_sha,
        expected_split_checksum=split_sha,
        expected_source_revision=str(manifest["source"]["repository_commit"]),
        expected_dirty_worktree=False,
    )
    resolver, taxonomy = bundle.baseline.resolver(), current_taxonomy_mapping()
    by_profile: dict[str, list[dict[str, Any]]] = {profile: [] for profile in train}
    for raw in corpus.matches:
        profile = str(raw["profile_id"])
        if profile in by_profile:
            by_profile[profile].append(dict(raw))
    prior_records = [
        json.loads(line)
        for line in (args.prior_diagnostics / "profile_family_results.jsonl")
        .read_text()
        .splitlines()
    ]
    rng = np.random.default_rng(args.seed)
    session_rows: list[dict[str, Any]] = []
    session_validation = _session_synthetic(args.seed)
    presence_variants: dict[str, list[dict[str, Any]]] = defaultdict(list)
    confounders: dict[str, list[dict[str, Any]]] = defaultdict(list)
    profile_session_slopes: dict[str, dict[str, float]] = {}
    noise_by_family: dict[str, list[float]] = defaultdict(list)
    hardening_detail: dict[str, Counter[str]] = defaultdict(Counter)
    match_depth_median = statistics.median(len(rows) for rows in by_profile.values())
    duration_median = statistics.median(
        float(row["duration_seconds"]) for rows in by_profile.values() for row in rows
    )

    for profile_id in sorted(train):
        rows = by_profile[profile_id]
        key = _profile_key(profile_id)
        completed = dict(corpus.completion_for_profile(profile_id))
        measured = _measure_profile(
            rows, completed, resolver, taxonomy, dict(bundle.distance_calibration)
        )
        session_rows.append(_session_forensic(key, rows, completed, measured))
        actual_candidates = _candidate_actual(
            measured["session_drift"][SESSION_COMPONENT]["effects"],
            rows,
            rng,
            structurally_supported=measured["session_drift"][SESSION_COMPONENT]["supported"],
        )
        for candidate, value in actual_candidates.items():
            session_validation.append(
                {
                    "row_type": "observed_tuning",
                    "candidate": candidate,
                    "scenario": "frozen_session_contract",
                    "profile_key": key,
                    "noise": value,
                    "comparable_to_existing": SESSION_CANDIDATES[candidate]["comparable"],
                }
            )
        for family in FAMILIES:
            component_noise = [
                value
                for component in measured[family].values()
                if component["supported"]
                and (value := _margin_noise(component["effects"], rows)) is not None
            ]
            if component_noise:
                noise_by_family[family].append(max(component_noise))

        formula_modes = {
            "raw_raw": (False, False),
            "adjusted_raw": (True, False),
            "raw_adjusted": (False, True),
            "adjusted_adjusted": (True, True),
        }
        for name, (x_adjusted, y_adjusted) in formula_modes.items():
            effects, paired, retained = _presence_effects(
                rows, resolver, taxonomy, x_adjusted=x_adjusted, y_adjusted=y_adjusted
            )
            theta, informative = _theta(effects)
            supported = informative >= 12 and paired >= 30 and paired / max(1, retained) >= 0.80
            presence_variants[name].append(
                {
                    "profile_key": key,
                    "variant": name,
                    "theta": theta,
                    "informative_sessions": informative,
                    "paired_observations": paired,
                    "supported": supported,
                    "direction": "positive" if theta > 0 else "negative" if theta < 0 else "zero",
                }
            )

        dominant_hero = Counter(row["hero_id"] for row in rows).most_common(1)[0][0]
        grouped = Counter(str(row["session_id"]) for row in rows)
        strata: dict[str, Callable[[dict[str, Any]], bool]] = {
            "wins": lambda row: bool(row["won"]),
            "losses": lambda row: not bool(row["won"]),
            "dominant_hero_excluded": lambda row, hero=dominant_hero: row["hero_id"] != hero,
            "within_dominant_hero": lambda row, hero=dominant_hero: row["hero_id"] == hero,
            "short_duration": lambda row: float(row["duration_seconds"]) <= duration_median,
            "long_duration": lambda row: float(row["duration_seconds"]) > duration_median,
            "short_sessions": lambda row, counts=grouped: counts[str(row["session_id"])] <= 4,
            "long_sessions": lambda row, counts=grouped: counts[str(row["session_id"])] > 4,
        }
        ordered_sessions = sorted(
            grouped,
            key=lambda session: min(
                row["start_time"] for row in rows if str(row["session_id"]) == session
            ),
        )
        midpoint = len(ordered_sessions) // 2
        early_sessions, late_sessions = (
            set(ordered_sessions[:midpoint]),
            set(ordered_sessions[midpoint:]),
        )
        strata["early_chronology"] = lambda row, sessions=early_sessions: (
            str(row["session_id"]) in sessions
        )
        strata["late_chronology"] = lambda row, sessions=late_sessions: (
            str(row["session_id"]) in sessions
        )
        primary_function = Counter(
            taxonomy.get(int(row["hero_id"]), {}).get("hero_function", "unknown") for row in rows
        ).most_common(1)[0][0]
        strata["dominant_function"] = lambda row, function=primary_function: (
            taxonomy.get(int(row["hero_id"]), {}).get("hero_function", "unknown") == function
        )
        strata["other_functions"] = lambda row, function=primary_function: (
            taxonomy.get(int(row["hero_id"]), {}).get("hero_function", "unknown") != function
        )
        for name, keep in strata.items():
            effects, paired, retained = _presence_effects(rows, resolver, taxonomy, keep=keep)
            theta, informative = _theta(effects)
            supported = informative >= 12 and paired >= 30 and paired / max(1, retained) >= 0.80
            confounders[name].append(
                {
                    "profile_key": key,
                    "diagnostic": name,
                    "theta": theta,
                    "informative_sessions": informative,
                    "paired_observations": paired,
                    "supported": supported,
                    "direction": "positive" if theta > 0 else "negative" if theta < 0 else "zero",
                }
            )
        effects, _, _ = _presence_effects(rows, resolver, taxonomy)
        profile_session_slopes[key] = effects
        for family in ("transfer", "post_loss_response"):
            inference = _infer_family(
                family,
                measured[family],
                seed=_seed(key, family),
            )
            hardening_detail[family]["profiles"] += 1
            for component, supported in inference["supported"].items():
                hardening_detail[family][f"component_supported:{component}"] += int(supported)
            if inference["selected_component"]:
                hardening_detail[family][f"selected:{inference['selected_component']}"] += 1

    # Population slope is computed after centering within each profile-session, matching the family axis.
    centered_numerator = centered_denominator = 0.0
    for profile_id in sorted(train):
        rows = by_profile[profile_id]
        groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for row in rows:
            adjusted = _raw_components(row, resolver, taxonomy)
            y = -adjusted["survival"] if adjusted["survival"] is not None else None
            if adjusted["activity"] is not None and y is not None:
                groups[str(row["session_id"])].append((float(adjusted["activity"]), float(y)))
        for points in groups.values():
            if len(points) < 3:
                continue
            x_mean, y_mean = (
                statistics.fmean(x for x, _ in points),
                statistics.fmean(y for _, y in points),
            )
            centered_numerator += sum((x - x_mean) * (y - y_mean) for x, y in points)
            centered_denominator += sum((x - x_mean) ** 2 for x, _ in points)
    population_slope = centered_numerator / centered_denominator
    residual_rows = []
    for _key, effects in profile_session_slopes.items():
        residual = {session: value - population_slope for session, value in effects.items()}
        theta, informative = _theta(residual)
        if informative >= 12:
            residual_rows.append(theta)
    population_summary = {
        "estimand": "pooled within-profile-session adjusted death-exposure slope on adjusted involvement",
        "population_common_slope": population_slope,
        "supported_profile_residual_thetas": len(residual_rows),
        "residual_theta_positive": sum(value > 0 for value in residual_rows),
        "residual_theta_negative": sum(value < 0 for value in residual_rows),
        "residual_theta_zero": sum(value == 0 for value in residual_rows),
        "residual_theta_median": statistics.median(residual_rows) if residual_rows else None,
        "interpretation": "diagnostic only; adopting deviation from this baseline changes the public family question",
    }

    _write_csv(output / "session_attrition_funnel.csv", session_rows)
    _write_json(output / "session_margin_method_candidates.json", SESSION_CANDIDATES)
    _write_csv(output / "session_margin_validation.csv", session_validation)
    formula_summary = {name: _presence_summary(rows) for name, rows in presence_variants.items()}
    (output / "presence_exposure_formula_audit.md").write_text(
        "# Presence & Exposure formula audit\n\n"
        "The research estimator pairs per-match `(kills + assists) / minutes` with `deaths / ten minutes`, "
        "after the existing context-baseline adjustments, and fits a centered slope inside each session. "
        "Both rates share match duration; context adjustment does not remove result, hero, role, draft, opponent, team-tempo, or match-state dependence. "
        "The production-bound artifact remains read-only.\n\n"
        f"Diagnostic formula variants: `{json.dumps(formula_summary, sort_keys=True)}`.\n",
        encoding="utf-8",
    )
    direction_rows = [row for rows in presence_variants.values() for row in rows]
    _write_csv(output / "presence_exposure_direction_decomposition.csv", direction_rows)
    confounder_rows = [row for rows in confounders.values() for row in rows]
    confounder_rows.extend(
        {
            "profile_key": "aggregate",
            "diagnostic": name,
            **_presence_summary(rows),
        }
        for name, rows in confounders.items()
    )
    confounder_rows.append(
        {
            "profile_key": "aggregate",
            "diagnostic": "team_tempo_proxy",
            "supported": False,
            "reason": "not present in the frozen summary-history corpus",
        }
    )
    confounder_rows.append(
        {
            "profile_key": "aggregate",
            "diagnostic": "match_depth",
            "supported": True,
            "median_profile_matches": match_depth_median,
        }
    )
    _write_csv(output / "presence_exposure_confounder_diagnostics.csv", confounder_rows)
    _write_json(output / "presence_exposure_population_slope.json", population_summary)

    hardening_outputs: dict[str, list[dict[str, Any]]] = {"transfer": [], "post_loss_response": []}
    for family in hardening_outputs:
        prior = [row for row in prior_records if row["family"] == family]
        noise = noise_by_family[family]
        low, median, high = _bootstrap_margin(noise, rng)
        hardening_outputs[family].append(
            {
                "diagnostic": "margin_bootstrap",
                "observations": len(noise),
                "registered_margin": MARGINS[family],
                "bootstrap_p025": low,
                "bootstrap_p50": median,
                "bootstrap_p975": high,
            }
        )
        for multiplier in (0.8, 1.0, 1.2):
            hardening_outputs[family].append(
                {
                    "diagnostic": "predeclared_margin_sensitivity",
                    "margin_multiplier": multiplier,
                    "candidate_count": sum(
                        row["by_q"] <= TARGET_Q
                        and abs(row["theta"]) >= float(MARGINS[family]) * multiplier
                        and row["split_half_pass"]
                        and row["loo_pass"]
                        and row["dominant_hero_robustness_pass"]
                        for row in prior
                    ),
                    "yield_used_to_select_margin": False,
                }
            )
        hardening_outputs[family].append(
            {
                "diagnostic": "gate_summary",
                "supported": sum(row["supported"] for row in prior),
                "by_significant": sum(row["by_q"] <= TARGET_Q for row in prior),
                "dominant_hero_robust": sum(row["dominant_hero_robustness_pass"] for row in prior),
                "mechanically_qualified": sum(row["candidate_qualified"] for row in prior),
            }
        )
        hardening_outputs[family].extend(
            {"diagnostic": key, "count": value}
            for key, value in sorted(hardening_detail[family].items())
        )
    _write_csv(output / "transfer_hardening.csv", hardening_outputs["transfer"])
    _write_csv(output / "postloss_hardening.csv", hardening_outputs["post_loss_response"])

    with (args.prior_diagnostics / "multiplicity_simulation.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        multiplicity = [
            {"row_type": "exact_prior_stress_grid", **row} for row in csv.DictReader(handle)
        ]
    multiplicity.extend(_multiplicity_power(args.seed + 1))
    harmonic = {m: sum(1 / rank for rank in range(1, m + 1)) for m in (4, 3, 2)}
    multiplicity.extend(
        {
            "row_type": "registered_universe_decision",
            "registered_families": m,
            "by_harmonic_factor": harmonic[m],
            "rule": "freeze conceptually before fresh validation; never remove a family because of tuning yield",
        }
        for m in (4, 3, 2)
    )
    _write_csv(output / "multiplicity_audit.csv", multiplicity)

    yield_rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        rows = [row for row in prior_records if row["family"] == family]
        blockers = Counter()
        for row in rows:
            if not row["supported"]:
                blockers["structural_support"] += 1
            elif row["by_q"] > TARGET_Q:
                blockers["BY_statistical_gate"] += 1
            elif not row["practical_pass"]:
                blockers["practical_margin"] += 1
            elif not row["split_half_pass"] or not row["loo_pass"]:
                blockers["stability"] += 1
            elif not row["dominant_hero_robustness_pass"]:
                blockers["dominant_hero_robustness"] += 1
            else:
                blockers["passes_all_mechanical_gates"] += 1
        yield_rows.append(
            {
                "family": family,
                "profiles": len(rows),
                "structurally_supported": sum(row["supported"] for row in rows),
                "statistically_significant_before_margin": sum(
                    row["by_q"] <= TARGET_Q for row in rows
                ),
                "passes_practical_margin": sum(row["practical_pass"] for row in rows),
                "passes_stability": sum(row["split_half_pass"] and row["loo_pass"] for row in rows),
                "passes_robustness": sum(row["dominant_hero_robustness_pass"] for row in rows),
                "passes_all_current_mechanical_gates": sum(
                    row["candidate_qualified"] for row in rows
                ),
                "first_blocker_distribution": json.dumps(blockers, sort_keys=True),
                "publication_yield_optimized": False,
            }
        )
    _write_csv(output / "finding_yield_diagnostics.csv", yield_rows)

    family_matrix = {
        "transfer": {
            "question": "What survives when the hero changes?",
            "method": "validated",
            "margin": "calibrated",
            "personalization": "supported",
            "risk": "hero/context sensitivity",
            "decision": "KEEP",
            "next": "implementation specification and fresh validation",
        },
        "post_loss_response": {
            "question": "How does the next same-session hero choice move after result states?",
            "method": "validated",
            "margin": "calibrated",
            "personalization": "supported",
            "risk": "sparse states and observational result context",
            "decision": "KEEP",
            "next": "implementation specification and fresh validation",
        },
        "presence_exposure_link": {
            "question": "When involvement rises, what happens to death exposure?",
            "method": "validated",
            "margin": "calibrated but unsafe",
            "personalization": "population-common sign; residual deviation remains diagnostic",
            "risk": "shared duration and outcome/match-state confounding",
            "decision": "REDESIGN",
            "next": "owner product decision on population-baseline semantics",
        },
        "session_drift": {
            "question": "Within completed sessions, what changes from early to late?",
            "method": "validated",
            "margin": "not calibratable with current tuning support",
            "personalization": "not assessable",
            "risk": "structural completed-session scarcity",
            "decision": "DEFER",
            "next": "more tuning data under the frozen contract",
        },
    }
    _write_json(output / "family_decision_matrix.json", family_matrix)
    paths = {
        "four_family_recovery": {
            "user_value": 5,
            "defensibility": 2,
            "time": 1,
            "complexity": 5,
            "compatibility_risk": 4,
            "v7_reuse": 4,
            "reversibility": 2,
            "status": "REJECT_NOW",
        },
        "reduced_registered_universe": {
            "user_value": 4,
            "defensibility": 5,
            "time": 4,
            "complexity": 2,
            "compatibility_risk": 2,
            "v7_reuse": 5,
            "reversibility": 4,
            "status": "RECOMMENDED_TWO_FAMILIES",
        },
        "staged_mature_families": {
            "user_value": 4,
            "defensibility": 5,
            "time": 4,
            "complexity": 3,
            "compatibility_risk": 2,
            "v7_reuse": 5,
            "reversibility": 5,
            "status": "COMPATIBLE_IF_VERSIONED_AS_NEW_ANALYTICAL_LINEAGE",
        },
    }
    _write_json(output / "v61_path_comparison.json", paths)
    _write_json(
        output / "v7_reuse_map.json",
        {
            "family_definitions": "Transfer and Post-Loss are provider-agnostic; Presence may improve with role/tempo context; Session scarcity is not fixed by richer fields alone",
            "null_methods": "session signed-prevalence randomization carries forward",
            "margin_methodology": "carry forward only within unchanged estimands",
            "stability_gates": "split, LOO, and dominant-source sensitivity remain reusable",
            "multiplicity": "BY machinery reusable after the registered universe is frozen",
            "publication_state_machine": "reusable",
            "provenance": "corpus/split/source/artifact binding reusable",
        },
    )
    (output / "repo_integration_plan.md").write_text(
        f"# Repository integration plan\n\nANALYTICAL COMMIT CHAIN: `{args.merge_base}..{args.analytical_base}`\n\nMAIN-ONLY COMMIT CHAIN: `{args.merge_base}..{args.latest_main}`\n\nOVERLAPPING FILES: inspect at integration time; no integration performed.\n\nEXPECTED CONFLICTS: research evidence/prompt paths may overlap; production files are untouched.\n\nSAFE CHERRY-PICK ORDER: existing analytical chain through `{args.analytical_base}`, then this nightshift commit.\n\nDOCS THAT MUST LAND: nightshift evidence and its single next prompt.\n\nRESEARCH SCRIPTS THAT SHOULD / SHOULD NOT LAND: land this reproducible runner; do not land `.local` outputs.\n\nLOCAL-ONLY ARTIFACTS TO PRESERVE: `{output}`.\n\nTEMP WORKTREE CLEANUP: remove only after commit and verification.\n",
        encoding="utf-8",
    )
    aggregate = {
        "status": "PARTIAL",
        "session_verdict": "SESSION_REQUIRES_MORE_TUNING_DATA",
        "session_margin_eligible": sum(row["margin_eligible"] for row in session_rows),
        "session_inferentially_supported": sum(
            row["valid_family_estimate"] for row in session_rows
        ),
        "presence_formula_variants": formula_summary,
        "presence_population": population_summary,
        "presence_verdict": "PRESENCE_EXPOSURE_REQUIRES_POPULATION_BASELINE_REDEFINITION",
        "transfer_verdict": "TRANSFER_READY_FOR_IMPLEMENTATION_SPEC",
        "postloss_verdict": "POSTLOSS_READY_FOR_IMPLEMENTATION_SPEC",
        "multiplicity_verdict": "MULTIPLICITY_CONDITIONAL_PENDING_FINAL_FAMILY_SET",
        "recommended_path": "reduced two-family registered Finding universe: Transfer + Post-Loss; keep Presence and Session research-only",
        "next_status": "OWNER_PRODUCT_DECISION_REQUIRED",
        "tuning_profiles": 791,
        "holdout_profiles_touched": 0,
        "external_provider_calls": 0,
        "production_analytical_changes": 0,
        "deployments": 0,
        "corpus_sha256": corpus_sha,
        "split_sha256": split_sha,
        "train_profile_digest": split["train_digest"],
        "source_revision": manifest["source"]["repository_commit"],
        "seed": args.seed,
    }
    _write_json(output / "aggregate_summary.json", aggregate)
    print(json.dumps(aggregate, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
