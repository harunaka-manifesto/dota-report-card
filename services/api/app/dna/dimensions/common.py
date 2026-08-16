from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.dna.confidence import confidence_label, confidence_score, status_for
from app.dna.dimensions.models import DimensionKey, DimensionResult
from app.dna.features.models import FeatureEvidence


def result(
    key: DimensionKey,
    *,
    score: float | None,
    sample_size: int,
    effective_sample_size: float,
    coverage: float,
    minimum_sample: int,
    minimum_coverage: float = 0.0,
    stability: float = 1.0,
    quality: float = 1.0,
    evidence: tuple[FeatureEvidence, ...] = (),
    confounders: tuple[str, ...] = (),
    missing_reasons: tuple[str, ...] = (),
    copy: dict[str, Any] | None = None,
    source_match_ids: tuple[int, ...] = (),
    neutral: bool = False,
    descriptor_eligible: bool = True,
) -> DimensionResult:
    available = score is not None and sample_size >= minimum_sample and coverage >= minimum_coverage
    confidence = confidence_score(
        sample_size=sample_size,
        coverage=coverage,
        effective_sample_size=effective_sample_size,
        stability=stability,
        quality=quality,
        minimum_sample=minimum_sample,
    ) if available else 0.0
    label = _label(key, score, neutral=neutral) if score is not None else None
    copy = copy or {
        "headline_key": f"free_dna.dimension.{key}.headline",
        "receipt_key": f"free_dna.dimension.{key}.receipt",
        "receipt_params": {},
    }
    return DimensionResult(
        key=key,
        status=status_for(confidence, available=available, limited=confidence < 0.50),
        score=score if available else None,
        centered_score=((score - 0.5) * 2) if available and score is not None else None,
        label=label,
        confidence=confidence_label(confidence, unavailable=not available),
        confidence_score=confidence,
        sample_size=sample_size,
        effective_sample_size=effective_sample_size,
        coverage=coverage,
        evidence=evidence,
        confounders=confounders,
        missing_reasons=missing_reasons if not available else (),
        copy=copy,
        source_match_ids=source_match_ids,
        descriptor_eligible=descriptor_eligible,
    )


def cap_confidence(value: DimensionResult, maximum: float) -> DimensionResult:
    """Cap a provisional claim without changing its observed direction."""

    capped = max(0.0, min(maximum, value.confidence_score))
    return replace(
        value,
        confidence_score=capped,
        confidence=confidence_label(capped, unavailable=value.status == "unavailable"),
        status=status_for(capped, available=value.score is not None, limited=capped < 0.50),
    )


def mean(values: tuple[float, ...] | list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def median(values: tuple[float, ...] | list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def session_sensitivity_stability(features: Any, dimension: str | None = None) -> float:
    """Return the 60/90/120 score-direction agreement multiplier."""

    score_runs = getattr(features, "session_sensitivity_scores", {}) or {}
    if score_runs and dimension:
        baseline = score_runs.get(90, {}).get(dimension)
        if baseline is not None:
            baseline_direction = _score_direction(baseline)
            agreements = sum(
                _score_direction(scores.get(dimension)) == baseline_direction
                for gap, scores in score_runs.items()
                if gap in {60, 90, 120} and scores.get(dimension) is not None
            )
            return 1.0 if agreements >= 3 else 0.8 if agreements == 2 else 0.6

    # Backward-compatible fallback for old feature fixtures that only carry
    # the partition map.
    sensitivity = getattr(features, "session_sensitivity", {}) or {}
    baseline = sensitivity.get(90)
    if baseline is None:
        return 0.6
    agreements = sum(
        sensitivity.get(gap) == baseline
        for gap in (60, 90, 120)
        if sensitivity.get(gap) is not None
    )
    return 1.0 if agreements >= 3 else 0.8 if agreements == 2 else 0.6


def _score_direction(value: float | None) -> int:
    if value is None or abs(value) < 0.08:
        return 0
    return 1 if value > 0 else -1


def _label(key: DimensionKey, score: float | None, *, neutral: bool = False) -> str | None:
    if score is None:
        return None
    if neutral or 0.42 <= score <= 0.58:
        return {
            "breadth": "Balanced pool",
            "role": "Role balanced",
            "adaptability": "Mixed transfer",
            "activity": "Balanced involvement",
            "orientation": "Balanced contribution",
            "resilience": "Resetting",
            "endurance": "Steady pace",
            "rhythm": "Mixed rhythm",
        }[key]
    labels = {
        "breadth": ("Focused pool", "Wide explorer"),
        "role": ("Role anchored", "Role fluid"),
        "adaptability": ("Comfort-bound", "Transferable"),
        "activity": ("Reserved", "Highly involved"),
        "orientation": ("Facilitator", "Finisher"),
        "resilience": ("Resetting", "Outcome-sensitive"),
        "endurance": ("Front-loaded", "Sustained"),
        "rhythm": ("Short-burst", "Grinder"),
    }
    return labels[key][1 if score > 0.5 else 0]
