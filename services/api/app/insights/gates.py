from __future__ import annotations

from dataclasses import dataclass

from app.insights.models import MetricObservation
from app.insights.registry import InsightDefinition


@dataclass(frozen=True, slots=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...]
    confidence: str


def apply_publication_gates(
    definition: InsightDefinition,
    observation: MetricObservation,
    *,
    role_confidence: float,
    role_confidence_threshold: float = 0.60,
    parse_coverage: float,
    minimum_parse_coverage: float | None = None,
    holdout_survives: bool,
) -> GateResult:
    reasons: list[str] = []
    effective_parse_coverage = (
        definition.minimum_parse_coverage
        if minimum_parse_coverage is None
        else minimum_parse_coverage
    )
    if observation.relevant_matches < definition.minimum_matches:
        reasons.append("INSUFFICIENT_MATCHES")
    if observation.situation_count < definition.minimum_situations:
        reasons.append("INSUFFICIENT_SITUATIONS")
    if (
        effective_parse_coverage is not None
        and parse_coverage < effective_parse_coverage
    ):
        reasons.append("INSUFFICIENT_PARSE_COVERAGE")
    if (
        definition.eligibility.require_role_confidence
        and role_confidence < role_confidence_threshold
    ):
        reasons.append("LOW_ROLE_CONFIDENCE")
    if definition.requires_valid_cohort and observation.cohort_value is None:
        reasons.append("COHORT_UNAVAILABLE")
    if definition.effect_gate.minimum_absolute_effect > 0 and observation.effect is None:
        reasons.append("EFFECT_UNAVAILABLE")
    if observation.effect is not None:
        if abs(observation.effect) < definition.effect_gate.minimum_absolute_effect:
            reasons.append("PRACTICAL_EFFECT_TOO_SMALL")
        if (
            definition.effect_gate.confidence_interval_excludes_null
            and observation.interval is not None
            and observation.interval[0] <= 0 <= observation.interval[1]
        ):
            reasons.append("INTERVAL_CROSSES_NULL")
    if observation.direction and not holdout_survives:
        reasons.append("HOLDOUT_DIRECTION_UNSTABLE")

    confidence = _confidence(
        observation,
        role_confidence=role_confidence,
        parse_coverage=parse_coverage,
    )
    return GateResult(not reasons, tuple(reasons), confidence)


def _confidence(
    observation: MetricObservation,
    *,
    role_confidence: float,
    parse_coverage: float,
) -> str:
    if observation.denominator < 20 or role_confidence < 0.75 or parse_coverage < 0.70:
        return "low"
    if (
        observation.interval
        and observation.interval[0] > 0
        or observation.interval
        and observation.interval[1] < 0
    ):
        return "high"
    return "moderate"
