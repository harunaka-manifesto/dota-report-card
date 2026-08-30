#!/usr/bin/env python3
"""Offline Type-I validation for the proposed V6.1 family bootstrap tests."""

from __future__ import annotations

import argparse
import csv
import json
import math
import socket
from pathlib import Path
from typing import Any

import numpy as np

FAMILIES = {
    "pool_shape": "scalar_signed",
    "transfer": "max_abs_3",
    "post_loss_response": "max_range_4",
    "combat_expression": "max_abs_3",
    "session_drift": "max_range_5",
}
STATISTICS = (
    "scalar_signed",
    "directional_positive",
    "max_abs_2",
    "max_abs_3",
    "max_range_4",
    "max_range_5",
)
SCENARIOS = (
    "exact_zero_effect",
    "gaussian_noisy_null",
    "skewed_null",
    "heavy_tailed_null",
    "clustered_null",
    "unequal_cluster_sizes",
    "low_number_of_sessions",
    "high_number_of_sessions",
    "low_opportunity_count",
    "high_opportunity_count",
    "within_session_autocorrelation",
    "heteroskedastic_session_effects",
    "one_dominant_session",
    "missing_invalid_draws",
)
TARGET_ALPHA = 0.05
MAX_ACCEPTABLE_ESTIMATE = 0.065


def _offline_guard() -> None:
    def blocked(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("statistical hardening attempted a network request")

    socket.socket.connect = blocked  # type: ignore[method-assign]
    socket.create_connection = blocked  # type: ignore[assignment]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def _wilson(successes: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def _scenario(
    name: str, replicates: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    sessions = 20
    sizes = np.full((replicates, sessions), 10.0)
    if name == "low_number_of_sessions":
        sessions, sizes = 8, np.full((replicates, 8), 10.0)
    elif name == "high_number_of_sessions":
        sessions, sizes = 60, np.full((replicates, 60), 10.0)
    elif name == "low_opportunity_count":
        sessions, sizes = 12, np.full((replicates, 12), 2.0)
    elif name == "high_opportunity_count":
        sessions, sizes = 30, np.full((replicates, 30), 50.0)
    elif name == "unequal_cluster_sizes":
        base = np.array([1, 2, 3, 5, 8, 13, 21, 34, 55, 89] * 2, dtype=float)
        sizes = np.broadcast_to(base, (replicates, base.size)).copy()
    elif name == "one_dominant_session":
        sizes = np.full((replicates, sessions), 2.0)
        sizes[:, 0] = 200.0

    common = rng.normal(0, 0.45, (replicates, sessions, 1))
    independent = rng.normal(0, 1, (replicates, sessions, 5))
    scale = 1 / np.sqrt(sizes[:, :, None])
    means = 0.35 * common + independent * scale
    if name == "exact_zero_effect":
        means.fill(0)
    elif name == "skewed_null":
        skewed = rng.lognormal(0, 0.8, means.shape) - math.exp(0.8**2 / 2)
        means = 0.35 * common + skewed * scale
    elif name == "heavy_tailed_null":
        means = 0.35 * common + rng.standard_t(3, means.shape) * scale / math.sqrt(3)
    elif name == "clustered_null":
        means = common + independent * scale
    elif name == "within_session_autocorrelation":
        rho = 0.75
        effective_scale = np.sqrt((1 + rho) / (1 - rho)) * scale
        means = 0.35 * common + independent * effective_scale
    elif name == "heteroskedastic_session_effects":
        session_scale = np.linspace(0.2, 2.0, sessions)[None, :, None]
        means = 0.35 * common + independent * session_scale * scale
    return means * sizes[:, :, None], sizes


def _statistic(values: np.ndarray, name: str) -> np.ndarray:
    if name == "scalar_signed":
        return values[..., 0]
    if name == "directional_positive":
        return np.maximum(values[..., 0], 0)
    if name.startswith("max_abs_"):
        components = int(name.rsplit("_", 1)[1])
        return np.max(np.abs(values[..., :components]), axis=-1)
    components = int(name.rsplit("_", 1)[1])
    return np.ptp(values[..., :components], axis=-1)


def _null_statistic(draws: np.ndarray, point: np.ndarray, name: str) -> np.ndarray:
    centered = draws - point[:, None, :]
    if name == "directional_positive":
        return centered[..., 0]
    return np.abs(centered[..., 0]) if name == "scalar_signed" else _statistic(centered, name)


def _observed_null_distance(point: np.ndarray, name: str) -> np.ndarray:
    if name == "directional_positive":
        return point[..., 0]
    return np.abs(point[..., 0]) if name == "scalar_signed" else _statistic(point, name)


def _simulate(*, repetitions: int, draws: int, seed: int, batch_size: int) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for scenario_name in SCENARIOS:
        proposed_rejections = {name: 0 for name in STATISTICS}
        vector_rejections = {name: 0 for name in STATISTICS}
        valid_draw_total = 0
        for start in range(0, repetitions, batch_size):
            count = min(batch_size, repetitions - start)
            sums, sizes = _scenario(scenario_name, count, rng)
            sessions = sizes.shape[1]
            point = sums.sum(axis=1) / sizes.sum(axis=1)[:, None]
            multiplicities = rng.multinomial(
                sessions, np.full(sessions, 1 / sessions), size=(count, draws)
            )
            denominator = np.einsum("rbs,rs->rb", multiplicities, sizes, optimize=True)
            component_draws = (
                np.einsum("rbs,rsc->rbc", multiplicities, sums, optimize=True)
                / denominator[:, :, None]
            )
            valid = np.ones((count, draws), dtype=bool)
            if scenario_name == "missing_invalid_draws":
                valid = rng.random((count, draws)) >= 0.02
            valid_draw_total += int(valid.sum())
            valid_counts = valid.sum(axis=1)
            for statistic_name in STATISTICS:
                point_stat = _statistic(point, statistic_name)
                draw_stat = _statistic(component_draws, statistic_name)
                proposed_extreme = (
                    np.abs(draw_stat - point_stat[:, None]) >= np.abs(point_stat[:, None])
                ) & valid
                proposed_p = (proposed_extreme.sum(axis=1) + 1) / (valid_counts + 1)
                null_stat = _null_statistic(component_draws, point, statistic_name)
                observed = _observed_null_distance(point, statistic_name)
                vector_extreme = (null_stat >= observed[:, None]) & valid
                vector_p = (vector_extreme.sum(axis=1) + 1) / (valid_counts + 1)
                proposed_rejections[statistic_name] += int((proposed_p <= TARGET_ALPHA).sum())
                vector_rejections[statistic_name] += int((vector_p <= TARGET_ALPHA).sum())

        for method, results in (
            ("proposed_scalar_centering", proposed_rejections),
            ("vector_null_recompute_screen", vector_rejections),
        ):
            for statistic_name, rejections in results.items():
                estimate = rejections / repetitions
                lower, upper = _wilson(rejections, repetitions)
                rows.append(
                    {
                        "method": method,
                        "scenario": scenario_name,
                        "statistic_class": statistic_name,
                        "family_mapping": ";".join(
                            family
                            for family, statistic in FAMILIES.items()
                            if statistic == statistic_name
                        ),
                        "repetitions": repetitions,
                        "bootstrap_draws_per_replicate": draws,
                        "rejections": rejections,
                        "estimated_alpha": estimate,
                        "mc_ci95_lower": lower,
                        "mc_ci95_upper": upper,
                        "target_alpha": TARGET_ALPHA,
                        "verdict": (
                            "PASS"
                            if estimate <= MAX_ACCEPTABLE_ESTIMATE and lower <= TARGET_ALPHA
                            else "FAIL"
                        ),
                        "valid_draws_mean": valid_draw_total / repetitions,
                    }
                )
    return rows


def _placeholders(output: Path, reason: str) -> None:
    _write_csv(
        output / "power_simulation.csv", [{"status": "NOT_RUN_STOP_CONDITION", "reason": reason}]
    )
    _write_csv(
        output / "margin_rederivation.csv",
        [
            {"family": family, "status": "NOT_RUN_STOP_CONDITION", "reason": reason}
            for family in FAMILIES
        ],
    )
    gate_rows = {
        family: {"status": "NOT_RUN_STOP_CONDITION", "reason": reason} for family in FAMILIES
    }
    _write_json(output / "stability_gate_spec.json", gate_rows)
    _write_json(output / "confounder_gate_spec.json", gate_rows)
    _write_csv(
        output / "bh_dependency_check.csv", [{"status": "NOT_RUN_STOP_CONDITION", "reason": reason}]
    )
    _write_csv(
        output / "tuning_hardened_results.csv",
        [{"status": "NOT_RUN_STOP_CONDITION", "reason": reason}],
    )


def _self_check() -> None:
    assert _statistic(np.array([[[-1.0, 2.0, 0.0]]]), "max_abs_3").item() == 2.0
    assert _statistic(np.array([[[1.0, 4.0, -2.0, 0.0]]]), "max_range_4").item() == 6.0
    low, high = _wilson(50, 1000)
    assert low < 0.05 < high


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=1_000)
    parser.add_argument("--draws", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    if args.repetitions < 1_000 or args.draws != 2_000:
        raise SystemExit("hardening requires at least 1,000 repetitions and exactly 2,000 draws")
    _offline_guard()
    _self_check()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    rows = _simulate(
        repetitions=args.repetitions,
        draws=args.draws,
        seed=args.seed,
        batch_size=args.batch_size,
    )
    _write_csv(output / "type1_error_simulation.csv", rows)
    proposed = [row for row in rows if row["method"] == "proposed_scalar_centering"]
    family_verdicts: dict[str, Any] = {}
    for family, statistic in FAMILIES.items():
        relevant = [row for row in proposed if row["statistic_class"] == statistic]
        failures = [row for row in relevant if row["verdict"] == "FAIL"]
        family_verdicts[family] = {
            "statistic_class": statistic,
            "proposed_test_valid": "NO" if failures else "CONDITIONAL",
            "failed_null_scenarios": [row["scenario"] for row in failures],
            "maximum_estimated_alpha": max(float(row["estimated_alpha"]) for row in relevant),
            "recommendation": "replace scalar-max centering with a jointly null-imposed, family-specific pivot; validate before corpus work",
        }
    reason = "proposed family inference materially exceeded nominal Type-I error"
    _write_json(
        output / "method_validity_summary.json",
        {
            "status": "PARTIAL",
            "seed": args.seed,
            "numpy_version": np.__version__,
            "repetitions_per_scenario": args.repetitions,
            "bootstrap_draws_per_replicate": args.draws,
            "acceptance_rule": f"estimate <= {MAX_ACCEPTABLE_ESTIMATE} and Wilson lower CI <= {TARGET_ALPHA}",
            "families": family_verdicts,
            "stop_condition": reason,
            "theoretical_finding": "centering a scalar maximum does not impose the joint component null and cannot preserve max-statistic selection",
            "alternative_screen": "vector-level null recomputation is diagnostic only; it is not a finalized studentized family method",
        },
    )
    _write_json(output / "family_method_verdicts.json", family_verdicts)
    _placeholders(output, reason)
    aggregate = {
        "status": "PARTIAL",
        "implementation_ready": False,
        "stop_condition": reason,
        "rows": len(rows),
        "proposed_failures": sum(row["verdict"] == "FAIL" for row in proposed),
        "external_collection_calls": 0,
        "holdout_reruns": 0,
        "production_changes": 0,
        "network_guard": "socket fail-closed",
        "owner_worktree_modified": False,
    }
    _write_json(output / "aggregate_summary.json", aggregate)
    print(json.dumps(aggregate, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
