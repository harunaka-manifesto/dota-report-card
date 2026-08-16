"""Deterministic adjacent-hero recommendations for Free DNA."""

from __future__ import annotations

import math
from typing import Any

from app.dna.features.models import DnaFeatureSet
from app.heroes.identity import HeroCard
from app.heroes.taxonomy import TRAITS, HeroTaxonomy, HeroTaxonomyEntry

RECOMMENDATION_VERSION = "hero-recommendations-1.1.0"


def recommend_heroes(
    comfort: tuple[HeroCard, ...],
    features: DnaFeatureSet,
    taxonomy: HeroTaxonomy,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Select a small, diverse set using score + maximal marginal relevance.

    Exposure is an eligibility constraint, not a reason to hide every hero the
    player has ever touched: only heroes with five or more games, or heroes in
    the player's personal top-ten pool, are excluded.
    """

    if not comfort or limit <= 0:
        return []
    centroid = _centroid_traits(comfort, taxonomy)
    top_ten = {
        hero_id
        for hero_id, _count in sorted(
            features.hero_counts.items(), key=lambda item: (-item[1], item[0])
        )[:10]
    }
    candidates: list[dict[str, Any]] = []
    for candidate_hero in taxonomy.heroes.values():
        exposure = features.hero_counts.get(candidate_hero.hero_id, 0)
        if not candidate_hero.available or exposure >= 5 or candidate_hero.hero_id in top_ten:
            continue
        active_traits = _active_traits(candidate_hero)
        familiar = _familiar_traits(active_traits, centroid)
        adjacent = _adjacent_traits(active_traits, centroid)
        if not familiar or not adjacent:
            continue
        role_fit, role_outside = _role_fit(candidate_hero, features)
        novelty = _novelty(candidate_hero.hero_id, features)
        complexity_fit = _complexity_gap_fit(centroid, candidate_hero)
        similarity = _similarity(centroid, candidate_hero)
        score = (
            0.40 * similarity
            + 0.25 * role_fit
            + 0.15 * novelty
            + 0.15 * adjacent[0][1]
            + 0.05 * complexity_fit
        )
        candidates.append(
            {
                "hero": candidate_hero,
                "score": score,
                "vector": _vector(candidate_hero),
                "familiar_traits": [key for key, _ in familiar[:3]],
                "new_traits": [key for key, _ in adjacent[:3]],
                "role_fit": role_fit,
                "role_outside": role_outside,
                "novelty": novelty,
                "complexity_fit": complexity_fit,
            }
        )

    selected: list[dict[str, Any]] = []
    selected_candidates: list[dict[str, Any]] = []
    outside_selected = False
    remaining = list(candidates)
    while remaining and len(selected) < limit:
        ranked: list[tuple[float, dict[str, Any]]] = []
        for candidate in remaining:
            if candidate["role_outside"] and outside_selected:
                continue
            diversity_penalty = max(
                (_vector_similarity(candidate["vector"], item["vector"]) for item in selected_candidates),
                default=0.0,
            )
            mmr = candidate["score"] - 0.20 * diversity_penalty
            ranked.append((mmr, candidate))
        if not ranked:
            break
        _mmr, candidate = min(
            ranked,
            key=lambda item: (-item[0], -item[1]["score"], item[1]["hero"].hero_id),
        )
        remaining.remove(candidate)
        hero: HeroTaxonomyEntry = candidate["hero"]
        role_outside = bool(candidate["role_outside"])
        selected.append(
            {
                "hero_id": hero.hero_id,
                "name": hero.name,
                "portrait_url": hero.portrait_url,
                "portrait_asset_version": hero.portrait_asset_version,
                "fit_band": _fit_band(candidate["score"]),
                "score": round(candidate["score"], 6),
                "familiar_traits": candidate["familiar_traits"],
                "new_traits": candidate["new_traits"],
                "plausible_roles": list(hero.roles),
                "role_change": role_outside,
                "reason_key": "role_change_adjacent" if role_outside else "familiar_plus_adjacent_trait",
                "recommendation_version": RECOMMENDATION_VERSION,
            }
        )
        selected_candidates.append(candidate)
        outside_selected = outside_selected or role_outside
    return selected


def _centroid_traits(comfort: tuple[HeroCard, ...], taxonomy: HeroTaxonomy) -> dict[str, float]:
    weights = {item.hero_id: max(item.score, 0.01) for item in comfort}
    total = sum(weights.values()) or 1.0
    result = {trait: 0.5 for trait in TRAITS}
    for hero_id, weight in weights.items():
        hero = taxonomy.get(hero_id)
        if not hero:
            continue
        for trait in TRAITS:
            result[trait] += (hero.traits.get(trait, 0.5) - 0.5) * weight / total
    return result


def _active_traits(hero: HeroTaxonomyEntry) -> dict[str, float]:
    return {key: value for key, value in hero.traits.items() if value >= 0.65}


def _familiar_traits(active: dict[str, float], centroid: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(
        ((key, value) for key, value in active.items() if centroid.get(key, 0.5) >= 0.55),
        key=lambda item: (-centroid.get(item[0], 0.5), -item[1], item[0]),
    )


def _adjacent_traits(active: dict[str, float], centroid: dict[str, float]) -> list[tuple[str, float]]:
    candidates = [
        (key, max(0.0, value - centroid.get(key, 0.5)))
        for key, value in active.items()
        if centroid.get(key, 0.5) < 0.45
    ]
    if not candidates:
        candidates = [
            (key, max(0.0, value - centroid.get(key, 0.5)))
            for key, value in active.items()
            if value - centroid.get(key, 0.5) >= 0.10
        ]
    return sorted(candidates, key=lambda item: (-item[1], item[0]))


def _role_fit(hero: HeroTaxonomyEntry, features: DnaFeatureSet) -> tuple[float, bool]:
    credible = {
        role: count
        for role, count in features.role_counts.items()
        if count >= 3
    }
    if not credible:
        return 0.5, False
    total = sum(credible.values()) or 1
    overlap = sum(count for role, count in credible.items() if role in hero.roles) / total
    return max(0.25, overlap), overlap < 0.25


def _novelty(hero_id: int, features: DnaFeatureSet) -> float:
    exposure = features.hero_counts.get(hero_id, 0)
    total = max(features.sample_size, 1)
    return max(0.0, min(1.0, 1.0 - exposure / total))


def _complexity_gap_fit(centroid: dict[str, float], hero: HeroTaxonomyEntry) -> float:
    return max(0.0, min(1.0, 1.0 - abs(hero.traits.get("complexity", 0.5) - centroid.get("complexity", 0.5))))


def _similarity(centroid: dict[str, float], hero: HeroTaxonomyEntry) -> float:
    distance = sum(
        (centroid.get(trait, 0.5) - hero.traits.get(trait, 0.5)) ** 2 for trait in TRAITS
    ) / len(TRAITS)
    return max(0.0, min(1.0, 1.0 - math.sqrt(distance)))


def _vector(hero: HeroTaxonomyEntry) -> tuple[float, ...]:
    return tuple(hero.traits.get(trait, 0.5) for trait in TRAITS)


def _vector_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if not left or not right:
        return 0.0
    distance = sum((a - b) ** 2 for a, b in zip(left, right, strict=False)) / min(len(left), len(right))
    return max(0.0, min(1.0, 1.0 - math.sqrt(distance)))


def _fit_band(score: float) -> str:
    if score >= 0.70:
        return "strong"
    if score >= 0.52:
        return "good"
    return "exploratory"
