"""Deterministic session-clustered uncertainty and multiple-testing helpers."""

from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any

from .constants import (
    BOOTSTRAP_CONFIDENCE_LEVEL,
    BOOTSTRAP_VERSION,
    DEFAULT_BOOTSTRAP_ITERATIONS,
    FDR_Q,
    STATS_BOOTSTRAP_METHOD,
)

Number = int | float


def _as_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _seed_value(seed: int | str) -> int:
    if isinstance(seed, int):
        return seed
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(float(item) for item in values)
    p = min(1.0, max(0.0, float(probability))) * (len(ordered) - 1)
    lower = int(math.floor(p))
    upper = min(len(ordered) - 1, lower + 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (p - lower)


def _normal_cdf(value: float) -> float:
    return NormalDist().cdf(value)


def _normal_ppf(value: float) -> float:
    return NormalDist().inv_cdf(min(1.0 - 1e-12, max(1e-12, value)))


def _bca_probabilities(alpha: float, bias_correction: float, acceleration: float) -> tuple[float, float] | None:
    def adjusted(probability: float) -> float:
        z_alpha = _normal_ppf(probability)
        denominator = 1.0 - acceleration * (bias_correction + z_alpha)
        if abs(denominator) < 1e-12:
            return math.nan
        return _normal_cdf(
            bias_correction
            + (bias_correction + z_alpha) / denominator
        )

    lower = adjusted(alpha)
    upper = adjusted(1.0 - alpha)
    if not (math.isfinite(lower) and math.isfinite(upper) and 0.0 <= lower < upper <= 1.0):
        return None
    return lower, upper


def _flatten_groups(
    observations: Sequence[Any] | Mapping[Any, Sequence[Any] | Any],
    session_ids: Sequence[Hashable] | None,
) -> tuple[tuple[Hashable, tuple[Any, ...]], ...]:
    """Normalise common caller forms into stable session groups."""

    groups: dict[Hashable, list[Any]] = defaultdict(list)
    if isinstance(observations, Mapping):
        for session, values in observations.items():
            if isinstance(values, (str, bytes)):
                numeric = _as_float(values)
                groups[session].append(numeric if numeric is not None else values)
            elif isinstance(values, Iterable) and not isinstance(values, (int, float)):
                for value in values:
                    numeric = _as_float(value)
                    groups[session].append(numeric if numeric is not None else value)
            else:
                numeric = _as_float(values)
                groups[session].append(numeric if numeric is not None else values)
    else:
        if session_ids is not None and len(session_ids) != len(observations):
            raise ValueError("session_ids must have the same length as observations")
        for index, raw_value in enumerate(observations):
            numeric = _as_float(raw_value)
            if numeric is None:
                groups[session_ids[index] if session_ids is not None else f"session-{index + 1}"].append(raw_value)
                continue
            session = f"session-{index + 1}" if session_ids is None else session_ids[index]
            groups[session].append(numeric)
    # Sorting by repr handles mixed integer/string session identifiers without
    # relying on Python's incomparable ordering.
    return tuple(
        (session, tuple(groups[session]))
        for session in sorted(groups, key=lambda item: (type(item).__name__, repr(item)))
        if groups[session]
    )


def _flatten(selected: Sequence[tuple[Hashable, tuple[Any, ...]]]) -> list[Any]:
    return [value for _, values in selected for value in values]


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    point_estimate: float | None
    lower: float | None
    upper: float | None
    confidence_level: float
    iterations: int
    independent_sessions: int
    sample_size: int
    method: str = STATS_BOOTSTRAP_METHOD
    seed: int = 0
    replicates: tuple[float, ...] = ()
    bias_correction: float | None = None
    acceleration: float | None = None
    limitations: tuple[str, ...] = ()
    version: str = BOOTSTRAP_VERSION

    @property
    def interval(self) -> tuple[float, float] | None:
        if self.lower is None or self.upper is None:
            return None
        return (self.lower, self.upper)

    @property
    def available(self) -> bool:
        return self.point_estimate is not None and self.interval is not None

    def as_dict(self, *, include_replicates: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            "point_estimate": self.point_estimate,
            "interval": list(self.interval) if self.interval else None,
            "confidence_level": self.confidence_level,
            "iterations": self.iterations,
            "independent_sessions": self.independent_sessions,
            "sample_size": self.sample_size,
            "method": self.method,
            "seed": self.seed,
            "bias_correction": self.bias_correction,
            "acceleration": self.acceleration,
            "limitations": list(self.limitations),
            "version": self.version,
        }
        if include_replicates:
            result["replicates"] = list(self.replicates)
        return result


def mean_estimator(values: Sequence[Any]) -> float:
    numbers = [float(value) for value in values]
    return sum(numbers) / len(numbers) if numbers else math.nan


def clustered_bootstrap(
    observations: Sequence[Any] | Mapping[Any, Sequence[Any] | Any],
    session_ids: Sequence[Hashable] | None = None,
    *,
    estimator: Callable[[Sequence[Any]], float] = mean_estimator,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    seed: int | str = 0,
    confidence_level: float = BOOTSTRAP_CONFIDENCE_LEVEL,
) -> BootstrapResult:
    """Resample independent sessions with replacement.

    The interval is BCa when at least three independent clusters have usable
    leave-one-cluster-out estimates.  Degenerate or very small corpora use a
    deterministic percentile approximation, and the returned ``method`` says
    so explicitly.  Match rows inside a selected session are never sampled
    independently.
    """

    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")
    if iterations < 1:
        raise ValueError("iterations must be positive")
    seed_value = _seed_value(seed)
    groups = _flatten_groups(observations, session_ids)
    sample = _flatten(groups)
    if not groups or not sample:
        return BootstrapResult(
            None,
            None,
            None,
            confidence_level,
            iterations,
            len(groups),
            len(sample),
            method="clustered-percentile-approximation-1.0.0",
            seed=seed_value,
            limitations=("no finite observations",),
        )
    point = float(estimator(sample))
    if not math.isfinite(point):
        return BootstrapResult(
            None,
            None,
            None,
            confidence_level,
            iterations,
            len(groups),
            len(sample),
            method="clustered-percentile-approximation-1.0.0",
            seed=seed_value,
            limitations=("estimator returned a non-finite value",),
        )

    rng = random.Random(seed_value)
    replicates: list[float] = []
    cluster_count = len(groups)
    for _ in range(int(iterations)):
        selected = [groups[rng.randrange(cluster_count)] for _ in range(cluster_count)]
        value = float(estimator(_flatten(selected)))
        if math.isfinite(value):
            replicates.append(value)
    if not replicates:
        return BootstrapResult(
            point,
            None,
            None,
            confidence_level,
            iterations,
            len(groups),
            len(sample),
            method="clustered-percentile-approximation-1.0.0",
            seed=seed_value,
            limitations=("bootstrap estimator returned no finite replicates",),
        )

    alpha = (1.0 - confidence_level) / 2.0
    bias_correction: float | None = None
    acceleration: float | None = None
    method = STATS_BOOTSTRAP_METHOD
    low_probability = alpha
    high_probability = 1.0 - alpha

    # BCa correction over independent sessions.  With fewer than three
    # clusters, acceleration is not estimable and percentile approximation is
    # the principled conservative fallback.
    if cluster_count >= 3:
        below = sum(value < point for value in replicates)
        equal = sum(value == point for value in replicates)
        z0 = _normal_ppf((below + 0.5 * equal) / len(replicates))
        jackknife: list[float] = []
        for omitted in range(cluster_count):
            kept = [groups[index] for index in range(cluster_count) if index != omitted]
            estimate = float(estimator(_flatten(kept)))
            if math.isfinite(estimate):
                jackknife.append(estimate)
        if len(jackknife) >= 3:
            jack_mean = sum(jackknife) / len(jackknife)
            deviations = [jack_mean - value for value in jackknife]
            numerator = sum(value**3 for value in deviations)
            denominator = 6.0 * (sum(value**2 for value in deviations) ** 1.5)
            acceleration = numerator / denominator if denominator else 0.0
            bias_correction = z0

            probabilities = _bca_probabilities(alpha, z0, acceleration)
            if probabilities is None:
                method = "clustered-percentile-approximation-1.0.0"
                bias_correction = None
                acceleration = None
            else:
                low_probability, high_probability = probabilities
        else:
            method = "clustered-percentile-approximation-1.0.0"
    else:
        method = "clustered-percentile-approximation-1.0.0"

    lower = _quantile(replicates, low_probability)
    upper = _quantile(replicates, high_probability)
    return BootstrapResult(
        point,
        lower,
        upper,
        confidence_level,
        iterations,
        len(groups),
        len(sample),
        method=method,
        seed=seed_value,
        replicates=tuple(replicates),
        bias_correction=bias_correction,
        acceleration=acceleration,
        limitations=tuple(
            ["independent sessions are the resampling unit"]
            + (["percentile approximation used because acceleration was unavailable"] if method.startswith("clustered-percentile") else [])
        ),
    )


def session_clustered_bootstrap(*args: Any, **kwargs: Any) -> BootstrapResult:
    """Compatibility spelling for :func:`clustered_bootstrap`."""

    return clustered_bootstrap(*args, **kwargs)


def bootstrap_session_clusters(*args: Any, **kwargs: Any) -> BootstrapResult:
    """Descriptive alias naming the independent sampling unit."""

    return clustered_bootstrap(*args, **kwargs)


def bootstrap_stability(
    replicates: Sequence[Number],
    *,
    direction: str | None = None,
    center: float | None = None,
    practical_margin: float = 0.0,
) -> float:
    """Fraction of bootstrap draws supporting a stable zone or direction."""

    values = [float(item) for item in replicates if _as_float(item) is not None]
    if not values:
        return 0.0
    if direction in {"positive", "negative"}:
        midpoint = float(center or 0.0)
        if direction == "positive":
            supported = sum(value > midpoint + practical_margin for value in values)
        else:
            supported = sum(value < midpoint - practical_margin for value in values)
        return supported / len(values)
    if center is None:
        center = sum(values) / len(values)
    return sum(abs(value - center) <= abs(practical_margin) for value in values) / len(values)


def direction_stability(
    replicates: Sequence[Number],
    *,
    center: float = 0.0,
    practical_margin: float = 0.0,
) -> dict[str, float]:
    values = [float(item) for item in replicates if _as_float(item) is not None]
    if not values:
        return {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
    return {
        "positive": sum(value > center + practical_margin for value in values) / len(values),
        "negative": sum(value < center - practical_margin for value in values) / len(values),
        "neutral": sum(abs(value - center) <= practical_margin for value in values) / len(values),
    }


def benjamini_hochberg(
    p_values: Sequence[Number] | Mapping[Hashable, Number],
    *,
    q: float = FDR_Q,
) -> tuple[float, ...] | dict[Hashable, float]:
    """Return BH adjusted q-values in input order.

    The function is pure and deterministic; equal p-values retain their input
    order, which prevents report order from changing across Python versions.
    """

    if not 0 < q <= 1:
        raise ValueError("q must be within (0, 1]")
    is_mapping = isinstance(p_values, Mapping)
    if isinstance(p_values, Mapping):
        items = list(p_values.items())
    else:
        items = list(enumerate(p_values))
    validated: list[tuple[Hashable, float]] = []
    for key, value in items:
        numeric = _as_float(value)
        if numeric is None:
            raise ValueError(f"p-value for {key!r} is not finite")
        validated.append((key, min(1.0, max(0.0, numeric))))
    count = len(validated)
    adjusted: dict[Hashable, float] = {}
    running = 1.0
    for rank, (key, value) in reversed(list(enumerate(sorted(validated, key=lambda item: (item[1], repr(item[0]))), start=1))):
        candidate = min(running, value * count / rank)
        running = candidate
        adjusted[key] = min(1.0, max(0.0, candidate))
    if is_mapping:
        return {key: adjusted[key] for key, _ in validated}
    return tuple(adjusted[index] for index in range(count))


def fdr_qualified(p_value: float | None, q_value: float | None, *, q: float = FDR_Q) -> bool:
    return p_value is not None and q_value is not None and q_value <= q


bh_adjust = benjamini_hochberg
bh_fdr = benjamini_hochberg


__all__ = [
    "BootstrapResult",
    "mean_estimator",
    "clustered_bootstrap",
    "session_clustered_bootstrap",
    "bootstrap_session_clusters",
    "bootstrap_stability",
    "direction_stability",
    "benjamini_hochberg",
    "fdr_qualified",
    "bh_adjust",
    "bh_fdr",
]
