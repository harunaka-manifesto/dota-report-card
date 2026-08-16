from __future__ import annotations

from typing import Any

from app.dna.features.models import DnaFeatureSet
from app.heroes.identity import HeroCard
from app.heroes.taxonomy import HeroTaxonomy, HeroTaxonomyEntry


def recommend_heroes(
    comfort: tuple[HeroCard, ...],
    features: DnaFeatureSet,
    taxonomy: HeroTaxonomy,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    played = set(features.hero_counts)
    if not comfort:
        return []
    familiar_traits = _centroid_traits(comfort, taxonomy)
    candidates: list[dict[str, Any]] = []
    for candidate_hero in taxonomy.heroes.values():
        if not candidate_hero.available or candidate_hero.hero_id in played:
            continue
        similarity = _similarity(familiar_traits, candidate_hero)
        role_fit = 1.0 if any(role in candidate_hero.roles for role in _common_roles(features)) else 0.35
        novelty = 1.0
        adjacent = _adjacent_bonus(familiar_traits, candidate_hero)
        score = 0.40 * similarity + 0.25 * role_fit + 0.15 * novelty + 0.15 * adjacent + 0.05 * (1.0 - candidate_hero.traits.get("complexity", 0.5) * 0.25)
        familiar = sorted(key for key, value in candidate_hero.traits.items() if value >= 0.65 and familiar_traits.get(key, 0.0) >= 0.55)
        new = sorted(key for key, value in candidate_hero.traits.items() if value >= 0.65 and familiar_traits.get(key, 0.0) < 0.45)
        if not familiar or not new:
            continue
        candidates.append({
            "hero": candidate_hero,
            "score": score,
            "familiar_traits": familiar[:3],
            "new_traits": new[:3],
            "role_fit": role_fit,
        })
    candidates.sort(key=lambda item: (-item["score"], item["hero"].hero_id))
    selected: list[dict[str, Any]] = []
    selected_traits: list[set[str]] = []
    for candidate in candidates:
        traits = set(candidate["hero"].traits)
        if selected_traits and max(_set_similarity(traits, other) for other in selected_traits) > 0.93:
            continue
        hero: HeroTaxonomyEntry = candidate["hero"]
        selected.append({
            "hero_id": hero.hero_id,
            "name": hero.name,
            "portrait_url": hero.portrait_url,
            "portrait_asset_version": hero.portrait_asset_version,
            "fit_band": "strong" if candidate["score"] >= 0.70 else "good",
            "score": round(candidate["score"], 6),
            "familiar_traits": candidate["familiar_traits"],
            "new_traits": candidate["new_traits"],
            "plausible_roles": list(hero.roles),
            "reason_key": "familiar_plus_adjacent_trait",
        })
        selected_traits.append(traits)
        if len(selected) >= limit:
            break
    return selected


def _centroid_traits(comfort: tuple[HeroCard, ...], taxonomy: HeroTaxonomy) -> dict[str, float]:
    weights = {item.hero_id: item.score for item in comfort}
    total = sum(weights.values()) or 1.0
    result: dict[str, float] = {}
    for hero_id, weight in weights.items():
        hero = taxonomy.get(hero_id)
        if not hero:
            continue
        for trait, value in hero.traits.items():
            result[trait] = result.get(trait, 0.0) + weight * value / total
    return result


def _common_roles(features: DnaFeatureSet) -> set[str]:
    return {features.dominant_role} if features.dominant_role else set()


def _adjacent_bonus(centroid: dict[str, float], hero: HeroTaxonomyEntry) -> float:
    return 1.0 if any(value >= 0.65 and centroid.get(key, 0.0) < 0.45 for key, value in hero.traits.items()) else 0.35


def _similarity(centroid: dict[str, float], hero: HeroTaxonomyEntry) -> float:
    keys = set(centroid) | set(hero.traits)
    if not keys:
        return 0.5
    distance = sum((centroid.get(key, 0.5) - hero.traits.get(key, 0.5)) ** 2 for key in keys) / len(keys)
    return max(0.0, min(1.0, 1.0 - distance ** 0.5))


def _trait_set(values: set[str]) -> dict[str, float]:
    return {value: 1.0 for value in values}


def _set_similarity(left: set[str], right: set[str]) -> float:
    keys = left | right
    if not keys:
        return 1.0
    return 1.0 - sum((float(key in left) - float(key in right)) ** 2 for key in keys) / len(keys)
