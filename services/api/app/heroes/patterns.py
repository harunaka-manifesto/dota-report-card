from __future__ import annotations

import math
from typing import Any

from app.heroes.identity import HeroCard
from app.heroes.taxonomy import HeroTaxonomy


def extract_hero_patterns(
    signature: HeroCard,
    comfort: tuple[HeroCard, ...],
    taxonomy: HeroTaxonomy,
) -> list[dict[str, Any]]:
    contributors = [item for item in comfort if item.hero_id != signature.hero_id]
    if len(contributors) < 2:
        return [{"key": "mixed_toolsets", "label": "Mixed toolsets", "copy_key": "hero_pattern_mixed", "traits": [], "contributors": [signature.name]}]
    hero_count = max(1, len(taxonomy.heroes))
    trait_scores: dict[str, float] = {}
    trait_contributors: dict[str, list[str]] = {}
    for trait in _all_traits(taxonomy):
        agreeing = []
        for item in contributors:
            hero = taxonomy.get(item.hero_id)
            if hero and hero.traits.get(trait, 0.0) >= 0.65:
                agreeing.append(item)
        agreement = len(agreeing) / len(contributors)
        if agreement < 0.60:
            continue
        document_frequency = sum(
            bool(hero.traits.get(trait, 0.0) >= 0.65)
            for hero in taxonomy.heroes.values()
        )
        idf = math.log((hero_count + 1) / (document_frequency + 1))
        trait_scores[trait] = agreement * idf
        trait_contributors[trait] = [item.name for item in agreeing]
    if not trait_scores:
        return [{"key": "mixed_toolsets", "label": "Mixed toolsets", "copy_key": "hero_pattern_mixed", "traits": [], "contributors": [item.name for item in comfort]}]
    ordered = sorted(trait_scores, key=lambda key: (-trait_scores[key], key))
    chosen = ordered[:2]
    if {"mobility", "initiation"}.issubset(chosen):
        label = "Mobile initiators"
        key = "mobile_initiators"
    elif {"save", "sustain"}.issubset(chosen):
        label = "Protective enablers"
        key = "protective_enablers"
    elif "pickoff" in chosen:
        label = "Pickoff-focused heroes"
        key = "pickoff_focused"
    else:
        label = " and ".join(item.replace("_", " ") for item in chosen).title()
        key = "_".join(chosen)
    return [{
        "key": key,
        "label": label,
        "copy_key": "hero_pattern_trait_cluster",
        "traits": chosen,
        "scores": {trait: round(trait_scores[trait], 6) for trait in chosen},
        "contributors": sorted({name for trait in chosen for name in trait_contributors[trait]}),
    }]


def _all_traits(taxonomy: HeroTaxonomy) -> set[str]:
    values: set[str] = set()
    for hero in taxonomy.heroes.values():
        values.update(hero.traits)
    return values
