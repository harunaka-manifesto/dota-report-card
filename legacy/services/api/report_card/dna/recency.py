"""Versioned recency weighting for the one-year Free DNA population."""

from __future__ import annotations

from collections.abc import Sequence
from math import exp

RECENCY_WEIGHTING_VERSION = "recency-weighting-5.0.0"
DEFAULT_HALF_LIFE_DAYS = 180.0


def recency_weight(
    started_at: int,
    *,
    window_end: int,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """Return an exponential half-life weight in ``(0, 1]``."""

    half_life_seconds = max(float(half_life_days), 1e-6) * 24.0 * 60.0 * 60.0
    age = max(0.0, float(window_end - started_at))
    return exp(-0.6931471805599453 * age / half_life_seconds)


def effective_sample_size(weights: Sequence[float]) -> float:
    """Kish effective sample size for weighted observations."""

    clean = [max(0.0, float(weight)) for weight in weights]
    total = sum(clean)
    denominator = sum(weight * weight for weight in clean)
    return (total * total / denominator) if denominator else 0.0


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float | None:
    pairs = [
        (float(value), max(0.0, float(weight)))
        for value, weight in zip(values, weights, strict=False)
    ]
    total = sum(weight for _value, weight in pairs)
    return sum(value * weight for value, weight in pairs) / total if total else None


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float | None:
    pairs = sorted(
        (
            (float(value), max(0.0, float(weight)))
            for value, weight in zip(values, weights, strict=False)
            if weight > 0
        ),
        key=lambda item: item[0],
    )
    if not pairs:
        return None
    total = sum(weight for _value, weight in pairs)
    threshold = total / 2.0
    running = 0.0
    for value, weight in pairs:
        running += weight
        if running >= threshold:
            return value
    return pairs[-1][0]


def session_weight(
    session_start: int,
    *,
    window_end: int,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """Weight a session once, so a marathon session cannot gain authority per game."""

    return recency_weight(
        session_start,
        window_end=window_end,
        half_life_days=half_life_days,
    )


def weighted_session_mean(values: Sequence[float], weights: Sequence[float]) -> float | None:
    """Alias documenting the session-balanced aggregation contract."""

    return weighted_mean(values, weights)


__all__ = [
    "RECENCY_WEIGHTING_VERSION",
    "DEFAULT_HALF_LIFE_DAYS",
    "recency_weight",
    "session_weight",
    "effective_sample_size",
    "weighted_mean",
    "weighted_median",
    "weighted_session_mean",
]
