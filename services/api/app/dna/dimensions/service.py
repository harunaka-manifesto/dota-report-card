from __future__ import annotations

import logging
from collections.abc import Callable

from app.dna.dimensions import (
    activity,
    adaptability,
    breadth,
    endurance,
    orientation,
    resilience,
    rhythm,
    role,
)
from app.dna.dimensions.models import DimensionKey, DimensionResult
from app.dna.features.models import DnaFeatureSet

logger = logging.getLogger(__name__)

SCORERS: tuple[tuple[DimensionKey, Callable[[DnaFeatureSet], DimensionResult]], ...] = (
    ("breadth", breadth.score),
    ("role", role.score),
    ("adaptability", adaptability.score),
    ("activity", activity.score),
    ("orientation", orientation.score),
    ("resilience", resilience.score),
    ("endurance", endurance.score),
    ("rhythm", rhythm.score),
)


def score_dimensions(features: DnaFeatureSet) -> tuple[DimensionResult, ...]:
    """Score every dimension and contain one scorer's failure locally."""

    results: list[DimensionResult] = []
    for key, scorer in SCORERS:
        try:
            results.append(scorer(features))
        except Exception:
            logger.exception("dna_dimension_failed key=%s", key)
            results.append(
                DimensionResult(
                    key=key,
                    status="unavailable",
                    score=None,
                    centered_score=None,
                    label=None,
                    confidence="unavailable",
                    confidence_score=0.0,
                    sample_size=0,
                    effective_sample_size=0.0,
                    coverage=0.0,
                    missing_reasons=("scorer_failed",),
                )
            )
    return tuple(results)
