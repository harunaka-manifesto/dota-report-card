"""The Exception: a functional outlier in the established hero pool."""

from __future__ import annotations

import math
from collections.abc import Sequence

from app.content.renderer import resolve_portfolio_copy
from app.hero_portfolio.eligibility import build_hero_eligibility, eligible_heroes
from app.hero_portfolio.models import ChoiceOption, HeroEligibility, HeroExceptionResult
from app.hero_portfolio.ordering import stable_pseudo_shuffle
from app.heroes.taxonomy import TRAITS, HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch


def compute_hero_exception(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    eligibility: Sequence[HeroEligibility] | None = None,
) -> HeroExceptionResult:
    eligibility = tuple(eligibility or build_hero_eligibility(matches, taxonomy))
    candidates = eligible_heroes(eligibility, insight="exception")
    if len(candidates) < 4:
        return _no_clear("At least four established heroes are needed to compare functional shapes.", candidates, taxonomy)

    vectors = {
        item.hero_id: tuple(float(taxonomy.get(item.hero_id).traits.get(trait, 0.0)) for trait in TRAITS)  # type: ignore[union-attr]
        for item in candidates
    }
    distances: list[tuple[float, HeroEligibility]] = []
    for candidate in candidates:
        others = [vectors[item.hero_id] for item in candidates if item.hero_id != candidate.hero_id]
        centroid = _centroid(others)
        distance = _distance(vectors[candidate.hero_id], centroid)
        distances.append((distance, candidate))
    distances.sort(key=lambda item: (-item[0], item[1].hero_id))
    winner_distance, winner = distances[0]
    runner_distance = distances[1][0] if len(distances) > 1 else 0.0
    margin = winner_distance - runner_distance
    pool_centroid = _centroid(list(vectors.values()))
    pool_traits = _top_traits(pool_centroid)
    exception_traits = _top_traits(vectors[winner.hero_id], minimum=0.55)
    seed = "|".join(f"{item.hero_id}:{distance:.4f}" for distance, item in distances)
    options = _options(distances, winner, taxonomy, seed=seed)
    confidence = min(
        1.0,
        0.35 * min(1.0, winner.matches / 10.0)
        + 0.35 * min(1.0, winner_distance / 0.45)
        + 0.30 * min(1.0, margin / 0.15),
    )
    if winner_distance < 0.32 or margin < 0.06:
        return HeroExceptionResult(
            status="no_clear_exception",
            hero_id=None,
            hero_name=None,
            pool_traits=pool_traits,
            exception_traits=(),
            options=_no_clear_options(distances, taxonomy, seed=seed),
            correct_option_key="no_clear_exception",
            distance=winner_distance,
            margin=margin,
            confidence_score=confidence,
            limitations=("Different does not mean better or worse. No single hero clears the outlier margin in this pool.",),
        )
    entry = taxonomy.get(winner.hero_id)
    return HeroExceptionResult(
        status="available",
        hero_id=winner.hero_id,
        hero_name=entry.name if entry else None,
        pool_traits=pool_traits,
        exception_traits=exception_traits,
        options=options,
        correct_option_key=f"hero:{winner.hero_id}",
        distance=winner_distance,
        margin=margin,
        confidence_score=confidence,
        limitations=("Different does not mean better or worse.",),
    )


def _centroid(vectors: list[tuple[float, ...]]) -> tuple[float, ...]:
    if not vectors:
        return tuple(0.0 for _ in TRAITS)
    return tuple(sum(vector[index] for vector in vectors) / len(vectors) for index in range(len(TRAITS)))


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) / max(len(left), 1))


def _top_traits(vector: tuple[float, ...], *, minimum: float = 0.50) -> tuple[str, ...]:
    return tuple(
        trait
        for trait, value in sorted(zip(TRAITS, vector, strict=True), key=lambda item: (-item[1], item[0]))[:4]
        if value >= minimum
    )


def _options(
    distances: list[tuple[float, HeroEligibility]],
    winner: HeroEligibility,
    taxonomy: HeroTaxonomy,
    *,
    seed: str,
) -> tuple[ChoiceOption, ...]:
    # The three nearest-to-pool heroes make plausible same-shape distractors.
    distractors = [item for _, item in sorted(distances[1:], key=lambda value: (value[0], value[1].hero_id))[:3]]
    selected = [winner, *distractors]
    ordered = stable_pseudo_shuffle(selected, seed=f"exception|{seed}", key=lambda item: str(item.hero_id))
    return tuple(
        ChoiceOption(
            key=f"hero:{item.hero_id}",
            label=_hero_label(item.hero_id, taxonomy),
            hero_id=item.hero_id,
            feedback=(
                resolve_portfolio_copy(
                    "exception.correct_feedback",
                    hero=_hero_label(item.hero_id, taxonomy),
                )
                if item.hero_id == winner.hero_id
                else resolve_portfolio_copy(
                    "exception.incorrect_feedback",
                    selected=_hero_label(item.hero_id, taxonomy),
                    hero=_hero_label(winner.hero_id, taxonomy),
                )
            ),
        )
        for item in ordered
    )


def _no_clear_options(
    distances: list[tuple[float, HeroEligibility]],
    taxonomy: HeroTaxonomy,
    *,
    seed: str,
) -> tuple[ChoiceOption, ...]:
    candidates = [item for _, item in sorted(distances, key=lambda value: (-value[0], value[1].hero_id))[:3]]
    choices = [
        *(
            ChoiceOption(
                key=f"hero:{item.hero_id}",
                label=_hero_label(item.hero_id, taxonomy),
                hero_id=item.hero_id,
                feedback=resolve_portfolio_copy(
                    "exception.no_clear_feedback",
                    selected=_hero_label(item.hero_id, taxonomy),
                ),
            )
            for item in candidates
        ),
        ChoiceOption(
            key="no_clear_exception",
            label="No clear exception",
            feedback=resolve_portfolio_copy("exception.no_clear_feedback", selected="No clear exception"),
        ),
    ]
    return stable_pseudo_shuffle(choices, seed=f"exception-no-clear|{seed}", key=lambda item: item.key)


def _no_clear(
    reason: str,
    candidates: Sequence[HeroEligibility],
    taxonomy: HeroTaxonomy,
) -> HeroExceptionResult:
    distances = [(0.0, item) for item in candidates]
    seed = "|".join(f"{item.hero_id}:{item.matches}" for item in candidates)
    return HeroExceptionResult(
        status="unavailable",
        hero_id=None,
        hero_name=None,
        pool_traits=(),
        exception_traits=(),
        options=_no_clear_options(distances, taxonomy, seed=seed),
        correct_option_key="no_clear_exception",
        distance=None,
        margin=None,
        confidence_score=0.0,
        limitations=(reason,),
    )


def _hero_label(hero_id: int, taxonomy: HeroTaxonomy) -> str:
    entry = taxonomy.get(hero_id)
    return entry.name if entry is not None else str(hero_id)


__all__ = ["compute_hero_exception"]
