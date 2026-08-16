from __future__ import annotations

from typing import Literal

ConfidenceLabel = Literal["high", "moderate", "low", "unavailable"]


def confidence_score(
    *,
    sample_size: int,
    coverage: float,
    effective_sample_size: float,
    stability: float = 1.0,
    quality: float = 1.0,
    minimum_sample: int = 1,
) -> float:
    if sample_size < minimum_sample or coverage <= 0.0:
        return 0.0
    sample_factor = min(1.0, effective_sample_size / max(minimum_sample, 1))
    score = (
        0.35 * max(0.0, min(1.0, coverage))
        + 0.35 * sample_factor
        + 0.20 * max(0.0, min(1.0, stability))
        + 0.10 * max(0.0, min(1.0, quality))
    )
    return max(0.0, min(1.0, score))


def confidence_label(score: float, *, unavailable: bool = False) -> ConfidenceLabel:
    if unavailable or score <= 0.0:
        return "unavailable"
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "moderate"
    return "low"


def status_for(
    score: float, *, available: bool, limited: bool = False
) -> Literal["available", "limited", "unavailable"]:
    if not available:
        return "unavailable"
    return "limited" if limited or score < 0.50 else "available"
