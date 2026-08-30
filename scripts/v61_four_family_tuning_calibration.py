#!/usr/bin/env python3
"""Calibrate four-family signed-prevalence gates on the frozen tuning split."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.player_analysis_v61.artifacts import load_v61_artifact_bundle  # noqa: E402
from app.player_analysis_v61.calibration_corpus import load_canonical_corpus  # noqa: E402
from app.player_analysis_v61.corpus_reuse import profile_digest, sha256_file  # noqa: E402
from app.player_analysis_v61.legacy_adapter import current_taxonomy_mapping  # noqa: E402
from app.player_analysis_v61.portfolio_shape import cross_fitted_distance_records  # noqa: E402
from v61_calibration_builder import _raw_components  # noqa: E402
from v61_findings_statistical_hardening import (  # noqa: E402
    _offline_guard,
    _write_csv,
    _write_json,
)
from v61_four_family_inference_design import (  # noqa: E402
    COMPONENTS,
    MIN_SESSIONS,
    _family_p,
)

VERSION = "research-signed-prevalence-calibration-1.0.0"
FAMILIES = tuple(COMPONENTS)
TARGET_Q = 0.05
HALF_MIN_SESSIONS = 6
LOO_AGREEMENT = 0.80
MIN_MARGIN_PROFILES = 100
MULTIPLICITY_MAX_FDR = 0.055
COMMON_DIRECTION_REVIEW = 0.90


def _predeclared_rules() -> dict[str, Any]:
    return {
        "version": VERSION,
        "family_universe": list(FAMILIES),
        "pool_family_test": None,
        "practical_margin": {
            "unit": "absolute signed prevalence theta",
            "rule": "P90 of per-profile maximum odd/even component disagreement divided by two",
            "minimum_profiles": MIN_MARGIN_PROFILES,
            "yield_used": False,
        },
        "stability": {
            "split_half": "odd and even session theta directions both match the full selected-component direction",
            "minimum_sessions_per_half": HALF_MIN_SESSIONS,
            "leave_one_session_out_direction_agreement": LOO_AGREEMENT,
        },
        "robustness": {
            "perturbation": "exclude the profile's most-used hero and recompute all measurements",
            "gate": "selected component retains structural support and full direction",
        },
        "multiplicity": {
            "procedure": "Benjamini-Yekutieli",
            "q": TARGET_Q,
            "fixed_m": 4,
            "unsupported_family_p": 1.0,
            "reason": "finite-family FDR control under arbitrary dependence",
            "bh_status": "diagnostic comparator only",
        },
        "qualification": "BY q<=.05, abs(theta)>=margin, split-half pass, LOO pass, dominant-hero robustness pass, and evidence complete",
        "conservative_safety_stop": {
            "status": "added after the first tuning run; not a predeclared calibration threshold",
            "trigger": "at least 90% one-direction prevalence requires confounder/product review",
            "effect": "can only block approval; cannot change a margin or increase candidate yield",
        },
        "holdout": "forbidden",
        "production_change": False,
    }


def _sid(row: dict[str, Any]) -> str:
    return str(row["session_id"])


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _theta(effects: dict[str, float], sessions: set[str] | None = None) -> tuple[float, int]:
    values = [
        math.copysign(1.0, value)
        for session, value in effects.items()
        if value != 0 and (sessions is None or session in sessions)
    ]
    return (sum(values) / len(values), len(values)) if values else (0.0, 0)


def _slope(rows: list[tuple[float, float]]) -> float | None:
    if len(rows) < 3:
        return None
    x_mean = _mean([row[0] for row in rows])
    denominator = sum((row[0] - x_mean) ** 2 for row in rows)
    if denominator <= 0:
        return None
    y_mean = _mean([row[1] for row in rows])
    return sum((x - x_mean) * (y - y_mean) for x, y in rows) / denominator


def _transfer(
    rows: list[dict[str, Any]],
    records: tuple[Any, ...],
    resolver: Any,
    taxonomy: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    covered: Counter[str] = Counter()
    for record in records:
        values = _raw_components(record.match, resolver, taxonomy)
        for component in COMPONENTS["transfer"]:
            value = values[component]
            if value is None:
                continue
            grouped[component][_sid(record.match)][record.band].append(float(value))
            counts[component][record.band] += 1
            covered[component] += 1
    result: dict[str, Any] = {}
    for component in COMPONENTS["transfer"]:
        effects = {
            session: _mean(bands["reliable_stretch"]) - _mean(bands["core"])
            for session, bands in grouped[component].items()
            if bands.get("core") and bands.get("reliable_stretch")
        }
        core = counts[component]["core"]
        stretch = counts[component]["reliable_stretch"]
        coverage = covered[component] / len(rows) if rows else 0.0
        result[component] = {
            "effects": effects,
            "opportunities": min(core, stretch),
            "core_matches": core,
            "stretch_matches": stretch,
            "coverage": coverage,
            "supported": len(effects) >= MIN_SESSIONS
            and core >= 30
            and stretch >= 30
            and coverage >= 0.80,
        }
    return result


def _transitions(rows: list[dict[str, Any]], records: tuple[Any, ...]) -> list[dict[str, Any]]:
    distance = {id(record.match): record.combined_distance for record in records}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_sid(row)].append(row)
    result: list[dict[str, Any]] = []
    for session, items in grouped.items():
        ordered = sorted(
            items, key=lambda row: (row["start_time"], row["session_index"], row["match_id"])
        )
        loss_run = win_run = 0
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous["won"]:
                win_run += 1
                loss_run = 0
                state = "win" if win_run == 1 else "win_streak"
            else:
                loss_run += 1
                win_run = 0
                state = "one_loss" if loss_run == 1 else "two_plus_losses"
            result.append(
                {
                    "session": session,
                    "state": state,
                    "movement": distance[id(current)] - distance[id(previous)],
                    "same_hero": previous["hero_id"] == current["hero_id"],
                }
            )
    return result


def _post_loss(rows: list[dict[str, Any]], records: tuple[Any, ...]) -> dict[str, Any]:
    transitions = _transitions(rows, records)
    by_state: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    counts: Counter[str] = Counter()
    for row in transitions:
        by_state[row["state"]][row["session"]].append(float(row["movement"]))
        counts[row["state"]] += 1
    result: dict[str, Any] = {}
    for target, component in zip(
        ("one_loss", "two_plus_losses", "win_streak"),
        COMPONENTS["post_loss_response"],
        strict=True,
    ):
        effects = {
            session: _mean(values) - _mean(by_state["win"][session])
            for session, values in by_state[target].items()
            if by_state["win"].get(session)
        }
        opportunities = counts[target] + counts["win"]
        result[component] = {
            "effects": effects,
            "opportunities": opportunities,
            "target_opportunities": counts[target],
            "reference_opportunities": counts["win"],
            "coverage": 1.0 if transitions else 0.0,
            "supported": len(effects) >= MIN_SESSIONS and opportunities >= 30,
        }
    return result


def _presence(
    rows: list[dict[str, Any]], resolver: Any, taxonomy: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    paired: dict[str, list[tuple[float, float]]] = defaultdict(list)
    paired_count = 0
    for row in rows:
        values = _raw_components(row, resolver, taxonomy)
        if values["activity"] is None or values["survival"] is None:
            continue
        paired[_sid(row)].append((float(values["activity"]), -float(values["survival"])))
        paired_count += 1
    effects = {
        session: slope
        for session, values in paired.items()
        if (slope := _slope(values)) is not None
    }
    coverage = paired_count / len(rows) if rows else 0.0
    component = COMPONENTS["presence_exposure_link"][0]
    return {
        component: {
            "effects": effects,
            "opportunities": paired_count,
            "coverage": coverage,
            "supported": len(effects) >= MIN_SESSIONS and paired_count >= 30 and coverage >= 0.80,
        }
    }


def _session_drift(rows: list[dict[str, Any]], completed: dict[str, bool]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_sid(row)].append(row)
    ordered_sessions = sorted(
        grouped, key=lambda session: min(row["start_time"] for row in grouped[session])
    )
    left_censored = ordered_sessions[0] if ordered_sessions else None
    boundary_safe = [
        session
        for session in ordered_sessions
        if session != left_censored
        and completed.get(session) is True
        and not any(row.get("session_corrupt") for row in grouped[session])
    ]
    effects: dict[str, float] = {}
    opportunities = 0
    for session in boundary_safe:
        items = sorted(
            grouped[session],
            key=lambda row: (row["start_time"], row["session_index"], row["match_id"]),
        )
        if len(items) < 4:
            continue
        half = len(items) // 2
        early, late = items[:half], items[-half:]
        effects[session] = _mean([float(row["won"]) for row in late]) - _mean(
            [float(row["won"]) for row in early]
        )
        opportunities += len(early) + len(late)
    coverage = len(effects) / len(boundary_safe) if boundary_safe else 0.0
    component = COMPONENTS["session_drift"][0]
    return {
        component: {
            "effects": effects,
            "opportunities": opportunities,
            "coverage": coverage,
            "boundary_safe_sessions": len(boundary_safe),
            "supported": len(effects) >= MIN_SESSIONS and opportunities >= 30 and coverage >= 0.50,
        }
    }


def _measure_profile(
    rows: list[dict[str, Any]],
    completed: dict[str, bool],
    resolver: Any,
    taxonomy: dict[int, dict[str, Any]],
    distance: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = cross_fitted_distance_records(rows, taxonomy, calibration=distance)
    return {
        "transfer": _transfer(rows, records, resolver, taxonomy),
        "post_loss_response": _post_loss(rows, records),
        "presence_exposure_link": _presence(rows, resolver, taxonomy),
        "session_drift": _session_drift(rows, completed),
    }


def _infer_family(
    family: str,
    components: dict[str, Any],
    *,
    seed: int,
) -> dict[str, Any]:
    names = COMPONENTS[family]
    sessions = sorted({session for name in names for session in components[name]["effects"]})
    values = np.full((1, len(sessions), len(names)), np.nan)
    for column, name in enumerate(names):
        for row, session in enumerate(sessions):
            if session in components[name]["effects"]:
                values[0, row, column] = components[name]["effects"][session]
    opportunities = np.array(
        [
            [
                components[name]["opportunities"] if components[name]["supported"] else 0
                for name in names
            ]
        ]
    )
    family_p, component_p, theta, totals, supported = _family_p(
        values, opportunities, draws=2_000, rng=np.random.default_rng(seed)
    )
    eligible = [index for index, value in enumerate(supported[0]) if value]
    selected = (
        min(eligible, key=lambda index: (component_p[0, index], names[index])) if eligible else None
    )
    return {
        "family_p": float(family_p[0]),
        "component_p": {name: float(component_p[0, index]) for index, name in enumerate(names)},
        "theta": {name: float(theta[0, index]) for index, name in enumerate(names)},
        "informative_sessions": {name: int(totals[0, index]) for index, name in enumerate(names)},
        "supported": {name: bool(supported[0, index]) for index, name in enumerate(names)},
        "selected_component": names[selected] if selected is not None else None,
    }


def _seed(profile_key: str, family: str) -> int:
    raw = hashlib.sha256(f"{VERSION}:{profile_key}:{family}".encode()).digest()
    return int.from_bytes(raw[:8], "big")


def _profile_key(profile_id: str) -> str:
    return hashlib.sha256(f"{VERSION}:{profile_id}".encode()).hexdigest()


def _session_partitions(rows: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    sessions = sorted(
        {_sid(row) for row in rows},
        key=lambda session: min(row["start_time"] for row in rows if _sid(row) == session),
    )
    return set(sessions[::2]), set(sessions[1::2])


def _loo_agreement(effects: dict[str, float], direction: float) -> float:
    signs = [math.copysign(1.0, value) for value in effects.values() if value != 0]
    if not signs or direction == 0:
        return 0.0
    total = sum(signs)
    return sum(math.copysign(1.0, total - value) == direction for value in signs) / len(signs)


def _adjust(p_values: list[float], *, by: bool) -> list[float]:
    count = len(p_values)
    factor = sum(1 / rank for rank in range(1, count + 1)) if by else 1.0
    ordered = sorted(range(count), key=lambda index: (p_values[index], index))
    result = [1.0] * count
    running = 1.0
    for reverse in range(count - 1, -1, -1):
        index = ordered[reverse]
        rank = reverse + 1
        running = min(running, p_values[index] * count * factor / rank)
        result[index] = max(0.0, min(1.0, running))
    return result


def _rank(values: list[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=lambda index: (values[index], index))
    result = [0.0] * len(values)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        average = (start + 1 + end) / 2
        for offset in range(start, end):
            result[ordered[offset]] = average
        start = end
    return result


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or np.std(left) == 0 or np.std(right) == 0:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def _multiplicity_simulation(repetitions: int, seed: int) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    sessions = 36
    for rho in (-0.25, 0.0, 0.50, 0.90):
        covariance = np.full((4, 4), rho)
        np.fill_diagonal(covariance, 1.0)
        for scenario in ("global_null", "one_moderate_alternative"):
            fdp = {"BH": [], "BY": []}
            for start in range(0, repetitions, 200):
                count = min(200, repetitions - start)
                latent = rng.multivariate_normal(np.zeros(4), covariance, size=(count, sessions))
                p_matrix = np.ones((count, 4))
                for family_index, (_family, names) in enumerate(COMPONENTS.items()):
                    values = rng.choice((-1.0, 1.0), size=(count, sessions, len(names)))
                    values[:, :, 0] = np.where(latent[:, :, family_index] >= 0, 1.0, -1.0)
                    if scenario != "global_null" and family_index == 0:
                        values[:, :, 0] = np.where(rng.random((count, sessions)) < 0.65, 1.0, -1.0)
                    opportunities = np.full((count, len(names)), 90)
                    p_matrix[:, family_index] = _family_p(
                        values, opportunities, draws=2_000, rng=rng
                    )[0]
                for dataset in range(count):
                    for procedure, by in (("BH", False), ("BY", True)):
                        adjusted = _adjust(p_matrix[dataset].tolist(), by=by)
                        rejected = [
                            index for index, value in enumerate(adjusted) if value <= TARGET_Q
                        ]
                        nulls = set(range(4)) if scenario == "global_null" else {1, 2, 3}
                        false = sum(index in nulls for index in rejected)
                        fdp[procedure].append(false / max(1, len(rejected)))
            for procedure in ("BH", "BY"):
                estimated = float(np.mean(fdp[procedure]))
                rows.append(
                    {
                        "scenario": scenario,
                        "latent_correlation": rho,
                        "procedure": procedure,
                        "repetitions": repetitions,
                        "estimated_fdr": estimated,
                        "acceptance_limit": MULTIPLICITY_MAX_FDR,
                        "verdict": "PASS" if estimated <= MULTIPLICITY_MAX_FDR else "FAIL",
                    }
                )
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def _self_check() -> None:
    assert _theta({"a": 1.0, "b": -4.0, "c": 2.0}) == (1 / 3, 3)
    assert (_slope([(1.0, 2.0), (2.0, 4.0), (3.0, 6.0)]) or 0) > 0
    assert (
        _adjust([0.01, 0.02, 0.5, 1.0], by=True)[0] > _adjust([0.01, 0.02, 0.5, 1.0], by=False)[0]
    )
    assert _rank([2.0, 1.0, 1.0]) == [3.0, 1.5, 1.5]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--multiplicity-repetitions", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()
    if args.multiplicity_repetitions < 10_000:
        raise SystemExit("multiplicity validation requires at least 10,000 datasets per scenario")
    _offline_guard()
    _self_check()
    corpus_sha = sha256_file(args.corpus)
    split_sha = sha256_file(args.split)
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
    resolver = bundle.baseline.resolver()
    taxonomy = current_taxonomy_mapping()
    by_profile: dict[str, list[dict[str, Any]]] = {profile: [] for profile in train}
    for row in corpus.matches:
        profile = str(row["profile_id"])
        if profile in by_profile:
            by_profile[profile].append(dict(row))
    records: list[dict[str, Any]] = []
    internal: list[dict[str, Any]] = []
    for profile_id in sorted(train):
        rows = by_profile[profile_id]
        key = _profile_key(profile_id)
        completed = dict(corpus.completion_for_profile(profile_id))
        measured = _measure_profile(
            rows, completed, resolver, taxonomy, dict(bundle.distance_calibration)
        )
        dominant = Counter(row["hero_id"] for row in rows).most_common(1)[0]
        reduced_rows = [row for row in rows if row["hero_id"] != dominant[0]]
        reduced = (
            _measure_profile(
                reduced_rows, completed, resolver, taxonomy, dict(bundle.distance_calibration)
            )
            if len(reduced_rows) >= 30
            else None
        )
        odd, even = _session_partitions(rows)
        for family in FAMILIES:
            inference = _infer_family(family, measured[family], seed=_seed(key, family))
            selected = inference["selected_component"]
            noise: list[float] = []
            for component in COMPONENTS[family]:
                effects = measured[family][component]["effects"]
                odd_theta, odd_n = _theta(effects, odd)
                even_theta, even_n = _theta(effects, even)
                if (
                    inference["supported"][component]
                    and odd_n >= HALF_MIN_SESSIONS
                    and even_n >= HALF_MIN_SESSIONS
                ):
                    noise.append(abs(odd_theta - even_theta))
            full_theta = inference["theta"].get(selected, 0.0) if selected else 0.0
            direction = math.copysign(1.0, full_theta) if full_theta else 0.0
            selected_effects = measured[family][selected]["effects"] if selected else {}
            odd_theta, odd_n = _theta(selected_effects, odd)
            even_theta, even_n = _theta(selected_effects, even)
            split_pass = bool(
                direction
                and odd_n >= HALF_MIN_SESSIONS
                and even_n >= HALF_MIN_SESSIONS
                and math.copysign(1.0, odd_theta) == direction
                and math.copysign(1.0, even_theta) == direction
                and odd_theta != 0
                and even_theta != 0
            )
            loo = _loo_agreement(selected_effects, direction)
            robust_theta = 0.0
            robust_supported = False
            if selected and reduced is not None:
                robust_inference = _infer_family(
                    family, reduced[family], seed=_seed(key + ":dominant-excluded", family)
                )
                robust_theta = robust_inference["theta"].get(selected, 0.0)
                robust_supported = robust_inference["supported"].get(selected, False)
            robust_pass = bool(
                direction
                and robust_supported
                and robust_theta != 0
                and math.copysign(1.0, robust_theta) == direction
            )
            internal.append(
                {
                    "profile_key": key,
                    "family": family,
                    "inference": inference,
                    "noise": max(noise) if noise else None,
                    "split_pass": split_pass,
                    "loo_agreement": loo,
                    "robust_pass": robust_pass,
                    "robust_theta": robust_theta,
                    "dominant_hero_share": dominant[1] / len(rows),
                    "evidence_complete": bool(selected),
                    "component_coverage": {
                        component: measured[family][component]["coverage"]
                        for component in COMPONENTS[family]
                    },
                }
            )

    margins: dict[str, float | None] = {}
    margin_rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        noise = [
            float(row["noise"])
            for row in internal
            if row["family"] == family and row["noise"] is not None
        ]
        p90 = _quantile(noise, 0.90)
        margins[family] = p90 / 2 if len(noise) >= MIN_MARGIN_PROFILES and p90 is not None else None
        margin_rows.append(
            {
                "family": family,
                "observations": len(noise),
                "noise_p50": _quantile(noise, 0.50),
                "noise_p90": p90,
                "practical_theta_margin": margins[family],
                "status": "CALIBRATED" if margins[family] is not None else "INSUFFICIENT_EVIDENCE",
                "rule": "P90_MAX_COMPONENT_ODD_EVEN_DISAGREEMENT_DIVIDED_BY_TWO",
                "yield_used": False,
            }
        )

    by_profile_internal: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in internal:
        by_profile_internal[row["profile_key"]].append(row)
    for profile_rows in by_profile_internal.values():
        profile_rows.sort(key=lambda row: FAMILIES.index(row["family"]))
        p_values = [float(row["inference"]["family_p"]) for row in profile_rows]
        bh = _adjust(p_values, by=False)
        by = _adjust(p_values, by=True)
        for index, row in enumerate(profile_rows):
            family = row["family"]
            inference = row["inference"]
            selected = inference["selected_component"]
            theta = inference["theta"].get(selected, 0.0) if selected else 0.0
            practical = margins[family] is not None and abs(theta) >= margins[family]
            stable = row["split_pass"] and row["loo_agreement"] >= LOO_AGREEMENT
            qualified = bool(
                by[index] <= TARGET_Q
                and practical
                and stable
                and row["robust_pass"]
                and row["evidence_complete"]
            )
            records.append(
                {
                    "profile_key": row["profile_key"],
                    "family": family,
                    "supported": any(inference["supported"].values()),
                    "selected_component": selected,
                    "family_p": p_values[index],
                    "bh_q_diagnostic": bh[index],
                    "by_q": by[index],
                    "theta": theta,
                    "practical_margin": margins[family],
                    "selected_coverage": (
                        row["component_coverage"][selected] if selected is not None else 0.0
                    ),
                    "practical_pass": practical,
                    "split_half_pass": row["split_pass"],
                    "loo_agreement": row["loo_agreement"],
                    "loo_pass": row["loo_agreement"] >= LOO_AGREEMENT,
                    "dominant_hero_share": row["dominant_hero_share"],
                    "dominant_hero_robustness_pass": row["robust_pass"],
                    "candidate_qualified": qualified,
                    "component_p": inference["component_p"],
                    "component_theta": inference["theta"],
                    "component_sessions": inference["informative_sessions"],
                }
            )
    records.sort(key=lambda row: (row["profile_key"], row["family"]))
    record_lookup = {(row["profile_key"], row["family"]): row for row in records}

    dependency_rows: list[dict[str, Any]] = []
    for left_index, left in enumerate(FAMILIES):
        for right in FAMILIES[left_index + 1 :]:
            paired = [
                (float(a["family_p"]), float(b["family_p"]))
                for key in by_profile_internal
                if (a := record_lookup[(key, left)])["supported"]
                and (b := record_lookup[(key, right)])["supported"]
            ]
            left_p, right_p = [item[0] for item in paired], [item[1] for item in paired]
            dependency_rows.append(
                {
                    "left_family": left,
                    "right_family": right,
                    "paired_supported_profiles": len(paired),
                    "pearson_p": _correlation(left_p, right_p),
                    "spearman_p": _correlation(_rank(left_p), _rank(right_p)),
                }
            )

    simulation = _multiplicity_simulation(args.multiplicity_repetitions, args.seed)
    by_simulation_pass = all(
        row["verdict"] == "PASS" for row in simulation if row["procedure"] == "BY"
    )
    tuning_rows: list[dict[str, Any]] = []
    stability_rows: list[dict[str, Any]] = []
    verdicts: dict[str, Any] = {}
    blocked_confounders: list[str] = []
    for family in FAMILIES:
        family_rows = [row for row in records if row["family"] == family]
        supported = [row for row in family_rows if row["supported"]]
        directions = Counter(
            "positive" if row["theta"] > 0 else "negative" if row["theta"] < 0 else "zero"
            for row in supported
        )
        dominant_direction_share = (
            max(directions.get("positive", 0), directions.get("negative", 0)) / len(supported)
            if supported
            else 0.0
        )
        common_direction_review = (
            family == "presence_exposure_link"
            and dominant_direction_share >= COMMON_DIRECTION_REVIEW
        )
        if common_direction_review:
            blocked_confounders.append(family)
        tuning_rows.append(
            {
                "family": family,
                "profiles": len(family_rows),
                "supported": sum(row["supported"] for row in family_rows),
                "raw_p_at_0_05": sum(row["family_p"] <= TARGET_Q for row in family_rows),
                "bh_q_at_0_05_diagnostic": sum(
                    row["bh_q_diagnostic"] <= TARGET_Q for row in family_rows
                ),
                "by_q_at_0_05": sum(row["by_q"] <= TARGET_Q for row in family_rows),
                "candidate_qualified_before_safety_review": sum(
                    row["candidate_qualified"] for row in family_rows
                ),
                "positive_direction": directions.get("positive", 0),
                "negative_direction": directions.get("negative", 0),
                "zero_direction": directions.get("zero", 0),
                "dominant_direction_share": dominant_direction_share,
                "common_direction_review_required": common_direction_review,
                "publication_yield_optimized": False,
            }
        )
        stability_rows.append(
            {
                "family": family,
                "supported_profiles": len(supported),
                "split_half_pass": sum(row["split_half_pass"] for row in supported),
                "loo_pass": sum(row["loo_pass"] for row in supported),
                "dominant_hero_robustness_pass": sum(
                    row["dominant_hero_robustness_pass"] for row in supported
                ),
                "all_stability_robustness_pass": sum(
                    row["split_half_pass"]
                    and row["loo_pass"]
                    and row["dominant_hero_robustness_pass"]
                    for row in supported
                ),
            }
        )
        status = (
            "BLOCKED_INSUFFICIENT_MARGIN_EVIDENCE"
            if margins[family] is None
            else "BLOCKED_COMMON_DIRECTION_CONFOUNDER_REVIEW"
            if common_direction_review
            else "CALIBRATED_WITH_LIMITATIONS"
            if by_simulation_pass
            else "BLOCKED_MULTIPLICITY_FAILURE"
        )
        verdicts[family] = {
            "status": status,
            "practical_theta_margin": margins[family],
            "margin_observations": next(
                row["observations"] for row in margin_rows if row["family"] == family
            ),
            "support_profiles": len(supported),
            "candidate_qualified_profiles_before_safety_review": sum(
                row["candidate_qualified"] for row in family_rows
            ),
            "direction_counts": dict(directions),
            "dominant_direction_share": dominant_direction_share,
            "limitations": [
                "tuning data has no independent truth labels",
                "dominant-hero exclusion is a bounded robustness screen, not confounder removal",
                "fresh sealed holdout validation remains required",
            ],
        }

    output = args.output_dir
    _write_json(output / "predeclared_rules.json", _predeclared_rules())
    _write_json(
        output / "provenance.json",
        {
            "version": VERSION,
            "corpus_sha256": corpus_sha,
            "split_sha256": split_sha,
            "train_profile_digest": split["train_digest"],
            "train_profiles": len(train),
            "holdout_profiles_excluded": len(holdout),
            "artifact_checksums": dict(bundle.checksums),
            "source_revision": manifest["source"]["repository_commit"],
            "external_collection_calls": 0,
            "holdout_outputs_loaded": False,
        },
    )
    _write_jsonl(output / "profile_family_results.jsonl", records)
    _write_csv(output / "margin_derivation.csv", margin_rows)
    _write_csv(output / "stability_robustness_summary.csv", stability_rows)
    _write_csv(output / "multiplicity_dependency.csv", dependency_rows)
    _write_csv(output / "multiplicity_simulation.csv", simulation)
    _write_csv(output / "tuning_behavior.csv", tuning_rows)
    _write_json(output / "family_verdicts.json", verdicts)
    blocked_margins = [family for family in FAMILIES if margins[family] is None]
    all_pass = by_simulation_pass and not blocked_margins and not blocked_confounders
    aggregate = {
        "status": "PASS_WITH_LIMITATIONS" if all_pass else "PARTIAL",
        "next_status": (
            "READY_FOR_CANDIDATE_IMPLEMENTATION_AND_FRESH_SEALED_HOLDOUT_PROTOCOL"
            if all_pass
            else "BLOCKED_PENDING_SESSION_MARGIN_AND_PRESENCE_CONFOUNDER_REVIEW"
            if blocked_margins and blocked_confounders
            else "BLOCKED_PENDING_MARGIN_EVIDENCE"
            if blocked_margins
            else "BLOCKED_PENDING_CONFOUNDER_REVIEW"
            if blocked_confounders
            else "BLOCKED_PENDING_MULTIPLICITY_METHOD"
        ),
        "blocked_margin_families": blocked_margins,
        "blocked_confounder_families": blocked_confounders,
        "families": verdicts,
        "multiplicity": {
            "selected": "Benjamini-Yekutieli",
            "fixed_m": 4,
            "q": TARGET_Q,
            "simulation_pass": by_simulation_pass,
        },
        "tuning_profiles": len(train),
        "holdout_profiles_evaluated": 0,
        "external_collection_calls": 0,
        "production_changes": 0,
        "seed": args.seed,
        "numpy_version": np.__version__,
    }
    _write_json(output / "aggregate_summary.json", aggregate)
    print(json.dumps(aggregate, sort_keys=True))
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
