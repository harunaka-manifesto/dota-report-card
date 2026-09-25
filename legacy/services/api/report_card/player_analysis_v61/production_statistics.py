"""Deterministic production V6.1 statistics.

Fixture approximations remain in ``family_statistics.py`` for State-A tests.
The functions here are the artifact-driven path: session-cluster bootstrap,
full recomputation for learned boundaries, interval-inside-ROPE equivalence,
five-family omnibus BH, and deterministic checkpoint-friendly seeds.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

BOOTSTRAP_ITERATIONS = 2_000
BOOTSTRAP_VERSION = "session-cluster-bootstrap-2.0.0"
FAMILY_COUNT = 5
_T = TypeVar("_T")


def deterministic_seed(
    *,
    version: str,
    artifact_checksums: Mapping[str, str],
    profile_digest: str,
    salt: str = "",
) -> int:
    material = "\0".join(
        [version, profile_digest, salt, *[f"{key}={artifact_checksums[key]}" for key in sorted(artifact_checksums)]]
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def session_clusters(matches: Sequence[Mapping[str, Any]]) -> dict[str, tuple[Mapping[str, Any], ...]]:
    clusters: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for index, match in enumerate(matches):
        session = match.get("session_id") if isinstance(match, Mapping) else getattr(match, "session_id", None)
        sid = str(session) if session not in (None, "") else f"row:{index}"
        clusters[sid].append(match)
    return {key: tuple(value) for key, value in sorted(clusters.items())}


def cluster_resample(
    matches: Sequence[Any],
    *,
    iteration: int,
    seed: int,
) -> tuple[Mapping[str, Any], ...]:
    clusters = session_clusters(matches)
    if not clusters:
        return ()
    rng = random.Random(seed + iteration)
    keys = tuple(clusters)
    sampled = [keys[rng.randrange(len(keys))] for _ in keys]
    rows: list[Mapping[str, Any]] = []
    for key in sampled:
        rows.extend(clusters[key])
    return tuple(rows)


def percentile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * fraction
    lower, upper = int(position), int(position + 0.999999999)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def bootstrap_recompute(
    matches: Sequence[Any],
    estimator: Callable[[Sequence[Any]], _T],
    *,
    seed: int,
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> tuple[_T, tuple[_T, ...]]:
    """Recompute the supplied estimator on every session-cluster resample."""

    if iterations != BOOTSTRAP_ITERATIONS:
        raise ValueError("production V6.1 bootstrap requires exactly 2,000 iterations")
    point = estimator(tuple(matches))
    samples = tuple(
        estimator(cluster_resample(matches, iteration=index, seed=seed))
        for index in range(iterations)
    )
    return point, samples


def scalar_interval(
    samples: Sequence[float | None],
    *,
    level: float = 0.95,
) -> dict[str, Any]:
    values = [float(value) for value in samples if value is not None]
    alpha = (1.0 - level) / 2.0
    lower = percentile(values, alpha)
    upper = percentile(values, 1.0 - alpha)
    return {
        "lower": lower,
        "upper": upper,
        "level": level,
        "iterations": len(samples),
        "usable_iterations": len(values),
        "method": BOOTSTRAP_VERSION,
    }


def interval_inside_rope(interval: Mapping[str, Any] | None, rope: float) -> bool:
    if not isinstance(interval, Mapping):
        return False
    lower, upper = interval.get("lower"), interval.get("upper")
    if not isinstance(lower, (int, float)) or not isinstance(upper, (int, float)):
        return False
    return float(lower) >= -abs(float(rope)) and float(upper) <= abs(float(rope))


def _bh(p_values: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running = 1.0
    for reverse_index, (key, value) in enumerate(reversed(ordered), start=1):
        rank = count - reverse_index + 1
        running = min(running, float(value) * count / max(1, rank))
        adjusted[key] = min(1.0, max(0.0, running))
    return adjusted


def five_family_bh(
    family_p_values: Mapping[str, float | None],
    *,
    expected_families: Sequence[str],
    q: float = 0.05,
) -> dict[str, dict[str, Any]]:
    if len(expected_families) != FAMILY_COUNT or set(family_p_values) != set(expected_families):
        raise ValueError("V6.1 production BH requires exactly five family roots")
    finite: dict[str, float] = {}
    for key, value in family_p_values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError("V6.1 production BH requires finite family p-values")
        if not 0 <= float(value) <= 1:
            raise ValueError("V6.1 production BH requires p-values in [0, 1]")
        finite[key] = float(value)
    adjusted = _bh(finite)
    return {
        family: {
            "raw_p_value": family_p_values[family],
            "adjusted_q_value": adjusted.get(family, 1.0),
            "qualified": family in adjusted and adjusted[family] <= q,
            "procedure": "benjamini-hochberg-exactly-five-family-omnibus",
        }
        for family in expected_families
    }


def bootstrap_metric(
    matches: Sequence[Any],
    estimator: Callable[[Sequence[Any]], float | None],
    *,
    seed: int,
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> dict[str, Any]:
    point, samples = bootstrap_recompute(matches, estimator, seed=seed, iterations=iterations)
    interval = scalar_interval(samples)
    interval["point"] = point
    interval["seed"] = seed
    return interval


__all__ = [
    "BOOTSTRAP_ITERATIONS",
    "BOOTSTRAP_VERSION",
    "bootstrap_metric",
    "bootstrap_recompute",
    "cluster_resample",
    "deterministic_seed",
    "five_family_bh",
    "interval_inside_rope",
    "scalar_interval",
    "session_clusters",
]
