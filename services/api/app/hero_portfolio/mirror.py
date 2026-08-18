"""Hero Mirror: closest sufficiently sampled observable behavior, not lore."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.hero_portfolio.behavior import (
    ROLE_KEYS,
    aggregate_behavior,
    behavior_labels,
    row_has_metrics,
)
from app.hero_portfolio.eligibility import build_hero_eligibility, eligible_heroes
from app.hero_portfolio.models import HeroEligibility, HeroMirrorResult
from app.hero_portfolio.version import HERO_MIRROR_VERSION
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch

MIRROR_MIN_INDEPENDENT_REFERENCE = 12
MIRROR_SAMPLE_SATURATION = 20
MIRROR_MIN_SAMPLE_CONFIDENCE = 0.35
MIRROR_MIN_DIMENSION_COVERAGE = 0.75
MIRROR_MIN_FINAL_SCORE = 0.55
MIRROR_MIN_RUNNER_UP_MARGIN = 0.04

# These scales use the same units as the shared behavior normalizer:
# events/minute, kill share, deaths/10 minutes, and total-variation role
# distance. Role distribution is intentionally one component.
_DIMENSION_SCALES = {
    "involvement": 0.35,
    "finishing": 0.20,
    "deaths": 0.75,
    "role_distribution": 1.0,
}
_DIMENSION_WEIGHTS = {key: 1.0 for key in _DIMENSION_SCALES}


@dataclass(frozen=True, slots=True)
class HeroMirrorCandidateScore:
    hero_id: int
    similarity: float
    sample_confidence: float
    dimension_coverage: float
    uncertainty_penalty: float
    final_score: float
    excluded_reference_matches: int
    fallback_used: bool


def compute_hero_mirror(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    eligibility: Sequence[HeroEligibility] | None = None,
) -> HeroMirrorResult:
    eligibility = tuple(eligibility or build_hero_eligibility(matches, taxonomy))
    candidates = eligible_heroes(eligibility, insight="mirror")
    if not candidates:
        return _unavailable("No sufficiently sampled hero has the required summary metrics.")

    rows_by_hero: dict[int, list[NormalizedSummaryMatch]] = {item.hero_id: [] for item in candidates}
    for item in matches:
        if item.hero_id is not None and item.hero_id in rows_by_hero:
            rows_by_hero[item.hero_id].append(item)

    ranked: list[tuple[HeroMirrorCandidateScore, dict[str, float], dict[str, float]]] = []
    for candidate in candidates:
        hero_rows = [item for item in rows_by_hero[candidate.hero_id] if row_has_metrics(item)]
        independent_reference = [
            item for item in matches if item.hero_id != candidate.hero_id and row_has_metrics(item)
        ]
        excluded_reference_matches = len(independent_reference)
        fallback_used = False
        reference_rows = independent_reference
        if len(reference_rows) < MIRROR_MIN_INDEPENDENT_REFERENCE:
            if not reference_rows:
                continue
            fallback_used = True
            fallback_count = min(len(hero_rows), max(3, len(reference_rows) // 2))
            reference_rows = [*reference_rows, *hero_rows[:fallback_count]]
        reference = aggregate_behavior(reference_rows)
        observed = aggregate_behavior(hero_rows)
        if not reference or not observed:
            continue
        shrunk = _shrink(observed, reference, candidate.matches)
        similarity, coverage = _similarity(shrunk, reference)
        sample_confidence = min(1.0, candidate.matches / MIRROR_SAMPLE_SATURATION)
        uncertainty_penalty = 0.82 if fallback_used else 1.0
        final_score = similarity * (0.65 + 0.35 * sample_confidence) * uncertainty_penalty
        ranked.append(
            (
                HeroMirrorCandidateScore(
                    hero_id=candidate.hero_id,
                    similarity=similarity,
                    sample_confidence=sample_confidence,
                    dimension_coverage=coverage,
                    uncertainty_penalty=uncertainty_penalty,
                    final_score=final_score,
                    excluded_reference_matches=excluded_reference_matches,
                    fallback_used=fallback_used,
                ),
                reference,
                shrunk,
            )
        )
    if not ranked:
        return _unavailable("Candidate-excluded comparison could not form a stable reference.")

    ranked.sort(key=lambda item: (-item[0].final_score, -item[0].similarity, -item[0].hero_id))
    winner, reference, hero_vector = ranked[0]
    runner_score = ranked[1][0].final_score if len(ranked) > 1 else 0.0
    margin = winner.final_score - runner_score
    confidence = winner.sample_confidence * winner.dimension_coverage * winner.uncertainty_penalty
    status: Literal["available", "no_clear_mirror"] = (
        "available"
        if (
            confidence >= MIRROR_MIN_SAMPLE_CONFIDENCE
            and winner.dimension_coverage >= MIRROR_MIN_DIMENSION_COVERAGE
            and winner.final_score >= MIRROR_MIN_FINAL_SCORE
            and margin >= MIRROR_MIN_RUNNER_UP_MARGIN
        )
        else "no_clear_mirror"
    )
    entry = taxonomy.get(winner.hero_id)
    hero_name = entry.name if entry is not None else f"Hero {winner.hero_id}"
    limitations: list[str] = [
        "This is not a personality test.",
        "The comparison uses involvement, finishing, death exposure, and credible role context from summary history only.",
    ]
    if winner.fallback_used:
        limitations.append("Candidate exclusion left a small reference, so a capped fallback was used and confidence was reduced.")
    if status != "available":
        limitations.append("No candidate clears the confidence, coverage, score, and runner-up margin gates yet.")
    return HeroMirrorResult(
        status=status,
        hero_id=winner.hero_id if status == "available" else None,
        hero_name=hero_name if status == "available" else None,
        similarity_score=winner.final_score,
        runner_up_hero_id=ranked[1][0].hero_id if len(ranked) > 1 else None,
        margin=margin,
        player_behavior=behavior_labels(aggregate_behavior(matches) or reference),
        hero_behavior=behavior_labels(hero_vector),
        confidence_score=confidence,
        limitations=tuple(limitations),
    )


def _shrink(observed: dict[str, float], reference: dict[str, float], sample: int) -> dict[str, float]:
    """Pull small hero samples toward the candidate-excluded reference."""

    observed_weight = min(1.0, sample / MIRROR_SAMPLE_SATURATION)
    return {
        key: reference[key] + (observed.get(key, reference[key]) - reference[key]) * observed_weight
        for key in reference
        if key in observed
    }


def _similarity(left: dict[str, float], right: dict[str, float]) -> tuple[float, float]:
    components = _similarity_components(left, right)
    if not components:
        return 0.0, 0.0
    weight_total = sum(_DIMENSION_WEIGHTS[key] for key in components)
    weighted_distance = sum(
        _DIMENSION_WEIGHTS[key] * value for key, value in components.items()
    ) / max(weight_total, 1e-9)
    return math.exp(-weighted_distance), len(components) / len(_DIMENSION_SCALES)


def _similarity_components(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    components: dict[str, float] = {}
    for key in ("involvement", "finishing", "deaths"):
        if key in left and key in right:
            components[key] = min(2.0, abs(left[key] - right[key]) / _DIMENSION_SCALES[key])
    left_roles = {key.removeprefix("role:"): value for key, value in left.items() if key.startswith("role:")}
    right_roles = {key.removeprefix("role:"): value for key, value in right.items() if key.startswith("role:")}
    if left_roles and right_roles:
        components["role_distribution"] = 0.5 * sum(
            abs(left_roles.get(role, 0.0) - right_roles.get(role, 0.0)) for role in ROLE_KEYS
        ) / _DIMENSION_SCALES["role_distribution"]
    return components


# Compatibility aliases keep the method easy to inspect in focused tests.
_aggregate = aggregate_behavior
_behavior_labels = behavior_labels


def _unavailable(reason: str) -> HeroMirrorResult:
    return HeroMirrorResult(
        status="unavailable",
        hero_id=None,
        hero_name=None,
        similarity_score=None,
        runner_up_hero_id=None,
        margin=None,
        player_behavior={},
        hero_behavior={},
        confidence_score=0.0,
        limitations=(reason, "This is not a personality test."),
    )


__all__ = [
    "HERO_MIRROR_VERSION",
    "HeroMirrorCandidateScore",
    "compute_hero_mirror",
]
