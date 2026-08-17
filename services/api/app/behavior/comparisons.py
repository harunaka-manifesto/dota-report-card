"""Small robust comparison helpers shared by summary Elements."""

from __future__ import annotations

import math
from collections.abc import Iterable
from statistics import median
from typing import Literal


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def robust_median(values: Iterable[float]) -> float | None:
    cleaned = [float(value) for value in values if math.isfinite(float(value))]
    return float(median(cleaned)) if cleaned else None


def mad(values: Iterable[float]) -> float:
    cleaned = [float(value) for value in values if math.isfinite(float(value))]
    centre = robust_median(cleaned)
    return float(median([abs(value - centre) for value in cleaned])) if centre is not None else 0.0


def robust_delta(left: Iterable[float], right: Iterable[float]) -> float | None:
    left_value = robust_median(left)
    right_value = robust_median(right)
    if left_value is None or right_value is None:
        return None
    return right_value - left_value


def bounded_delta_score(delta: float, scale: float = 0.5) -> float:
    return clamp(0.5 + 0.5 * math.tanh(delta / max(scale, 1e-6)))


def similarity_score(left: Iterable[float], right: Iterable[float], scale: float = 0.5) -> float | None:
    delta = robust_delta(left, right)
    if delta is None:
        return None
    return clamp(0.5 + 0.5 * math.tanh(delta / max(scale, 1e-6)))


def confidence_score(
    *,
    sample_size: int,
    effective_sample_size: float,
    coverage: float,
    stability: float,
    quality: float,
    minimum_sample: int,
) -> float:
    if sample_size <= 0 or minimum_sample <= 0:
        return 0.0
    sample_factor = clamp(math.sqrt(sample_size / minimum_sample))
    effective_factor = clamp(math.sqrt(max(0.0, effective_sample_size) / minimum_sample))
    return clamp(
        0.25 * sample_factor
        + 0.20 * effective_factor
        + 0.20 * clamp(coverage)
        + 0.20 * clamp(stability)
        + 0.15 * clamp(quality)
    )


def confidence_label(
    score: float,
    *,
    unavailable: bool = False,
) -> Literal["low", "moderate", "high", "unavailable"]:
    if unavailable:
        return "unavailable"
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "moderate"
    return "low"
