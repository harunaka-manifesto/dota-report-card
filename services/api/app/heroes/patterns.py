"""Weighted, source-controlled hero-pattern extraction."""

from __future__ import annotations

import math
from typing import Any

from app.heroes.identity import HeroCard
from app.heroes.taxonomy import TRAITS, HeroTaxonomy

_ROLE_KEYS = ("carry", "mid", "offlane", "soft_support", "hard_support", "roamer", "jungle")
_TRAIT_FAMILIES = {
    "engagement": ("initiation", "pickoff", "teamfight"),
    "movement": ("mobility", "repositioning", "global_presence"),
    "output": ("burst", "sustained_damage", "scaling"),
    "map_pressure": ("wave_clear", "push", "farm_dependency"),
    "protection": ("save", "sustain", "frontline"),
}
_CURATED_LABELS: dict[frozenset[str], tuple[str, str]] = {
    frozenset({"mobility", "initiation"}): ("mobile_initiators", "Mobile initiators"),
    frozenset({"save", "sustain"}): ("protective_enablers", "Protective enablers"),
    frozenset({"pickoff", "burst"}): ("pickoff_burst", "Pickoff and burst"),
    frozenset({"wave_clear", "push"}): ("map_pressure", "Map pressure"),
    frozenset({"sustained_damage", "scaling"}): ("scaling_damage", "Scaling damage"),
}


def extract_hero_patterns(
    signature: HeroCard,
    comfort: tuple[HeroCard, ...],
    taxonomy: HeroTaxonomy,
) -> list[dict[str, Any]]:
    """Return one primary theme and, when clearly distinct, one secondary theme."""

    cards_by_id = {card.hero_id: card for card in (signature, *comfort)}
    cards = tuple(cards_by_id.values())
    weights = {
        card.hero_id: (1.0 if card.hero_id == signature.hero_id else max(0.25, card.score))
        for card in cards
    }
    total_weight = sum(weights.values()) or 1.0
    heroes = {card.hero_id: taxonomy.get(card.hero_id) for card in cards}
    contributors = [card.name for card in cards]
    trait_scores = _trait_scores(heroes, weights, total_weight, taxonomy)
    role_traits = _role_scores(heroes, weights, total_weight)
    if not trait_scores:
        return [_fallback(contributors, role_traits)]

    family_winners: list[tuple[str, str, float]] = []
    for family, traits in _TRAIT_FAMILIES.items():
        available = [(trait, trait_scores[trait]) for trait in traits if trait in trait_scores]
        if available:
            trait, score = min(available, key=lambda item: (-item[1], item[0]))
            family_winners.append((family, trait, score))
    family_winners.sort(key=lambda item: (-item[2], item[0], item[1]))
    if not family_winners:
        return [_fallback(contributors, role_traits)]

    first_family, first_trait, first_score = family_winners[0]
    chosen = [first_trait]
    for family, trait, _score in family_winners[1:]:
        if family != first_family:
            chosen.append(trait)
            break
    primary = _pattern(chosen, role_traits, contributors, trait_scores)
    patterns = [primary]

    for family, trait, score in family_winners[1:]:
        if family == first_family or score < first_score * 0.80:
            continue
        secondary = _pattern([trait], role_traits, contributors, trait_scores, secondary=True)
        if secondary["key"] != primary["key"]:
            patterns.append(secondary)
        break
    return patterns


def _trait_scores(
    heroes: dict[int, Any],
    weights: dict[int, float],
    total_weight: float,
    taxonomy: HeroTaxonomy,
) -> dict[str, float]:
    hero_count = max(1, len(taxonomy.heroes))
    scores: dict[str, float] = {}
    for trait in TRAITS:
        agreeing_weight = sum(
            weights[hero_id]
            for hero_id, hero in heroes.items()
            if hero is not None and hero.traits.get(trait, 0.0) >= 0.65
        )
        agreement = agreeing_weight / total_weight
        if agreement < 0.60:
            continue
        document_frequency = sum(
            hero.traits.get(trait, 0.0) >= 0.65 for hero in taxonomy.heroes.values()
        )
        idf = math.log((hero_count + 1) / (document_frequency + 1))
        intensity = sum(
            weights[hero_id] * hero.traits.get(trait, 0.5)
            for hero_id, hero in heroes.items()
            if hero is not None
        ) / total_weight
        scores[trait] = agreement * idf * (0.5 + 0.5 * intensity)
    return scores


def _role_scores(
    heroes: dict[int, Any], weights: dict[int, float], total_weight: float
) -> list[str]:
    return [
        f"role_{role}"
        for role in _ROLE_KEYS
        if sum(
            weights[hero_id]
            for hero_id, hero in heroes.items()
            if hero is not None and role in hero.roles
        ) / total_weight >= 0.60
    ]


def _pattern(
    traits: list[str],
    role_traits: list[str],
    contributors: list[str],
    scores: dict[str, float],
    *,
    secondary: bool = False,
) -> dict[str, Any]:
    trait_set = frozenset(traits)
    key, label = _CURATED_LABELS.get(trait_set, ("mixed_toolsets", "Mixed toolsets"))
    if secondary:
        key = f"secondary_{key}"
    return {
        "key": key,
        "label": label,
        "copy_key": "hero_pattern_trait_cluster" if key != "mixed_toolsets" else "hero_pattern_mixed",
        "traits": list(traits),
        "role_traits": role_traits,
        "scores": {trait: round(scores.get(trait, 0.0), 6) for trait in traits},
        "contributors": sorted(set(contributors)),
    }


def _fallback(contributors: list[str], role_traits: list[str]) -> dict[str, Any]:
    return {
        "key": "mixed_toolsets",
        "label": "Mixed toolsets",
        "copy_key": "hero_pattern_mixed",
        "traits": [],
        "role_traits": role_traits,
        "scores": {},
        "contributors": sorted(set(contributors)),
    }
