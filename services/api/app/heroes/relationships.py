"""Deterministic, explainable relationships between reviewed hero vectors.

The full roster is not hand-paired.  Relationships are generated from the
checked-in taxonomy, a usage-capped player-pool centroid, role compatibility,
and finite learning-distance guardrails.  This keeps P01 recommendations
stable and inspectable without introducing a runtime model or network call.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from app.heroes.taxonomy import TRAITS, HeroTaxonomy, HeroTaxonomyEntry
from app.ingestion.summary_normalize import NormalizedSummaryMatch

HERO_RELATIONSHIPS_VERSION = "hero-relationships-1.0.0"
HERO_EXPRESSIONS_VERSION = "hero-expressions-1.0.0"

_TRAIT_LABELS = {
    "initiation": "initiation",
    "mobility": "mobility",
    "pickoff": "pickoff",
    "teamfight": "teamfight",
    "save": "save / reset",
    "sustain": "sustain",
    "burst": "burst damage",
    "sustained_damage": "sustained damage",
    "wave_clear": "wave clear",
    "push": "push",
    "frontline": "frontline presence",
    "scaling": "scaling",
    "farm_dependency": "farm dependency",
    "global_presence": "global presence",
    "micro_intensity": "micro intensity",
    "complexity": "complexity",
    "repositioning": "repositioning",
}


@dataclass(frozen=True, slots=True)
class HeroRelationship:
    hero_a_id: int
    hero_b_id: int
    shared_primary_traits: tuple[str, ...]
    shared_secondary_traits: tuple[str, ...]
    unique_to_a: tuple[str, ...]
    unique_to_b: tuple[str, ...]
    functional_similarity: float
    role_compatibility: float
    complexity_distance: float
    micro_distance: float
    relationship_version: str = HERO_RELATIONSHIPS_VERSION


@dataclass(frozen=True, slots=True)
class HeroPoolProfile:
    hero_ids: tuple[int, ...]
    usage_counts: dict[int, int]
    centroid: dict[str, float]
    dominant_traits: tuple[str, ...]
    underrepresented_traits: tuple[str, ...]
    credible_roles: tuple[str, ...]
    confidence_score: float


def build_pool_profile(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    *,
    hero_ids: Sequence[int] | None = None,
) -> HeroPoolProfile:
    usage = Counter(int(item.hero_id) for item in matches if item.hero_id is not None)
    selected_ids = set(hero_ids or usage)
    selected = {
        hero_id: count
        for hero_id, count in usage.items()
        if hero_id in selected_ids and taxonomy.get(hero_id) is not None and taxonomy.get(hero_id).available  # type: ignore[union-attr]
    }
    total = sum(selected.values())
    cap = max(3.0, total * 0.35)
    weighted_total = sum(min(float(count), cap) for count in selected.values())
    centroid = {trait: 0.5 for trait in TRAITS}
    for hero_id, count in selected.items():
        entry = taxonomy.get(hero_id)
        if entry is None:
            continue
        weight = min(float(count), cap)
        for trait in TRAITS:
            centroid[trait] += (entry.traits.get(trait, 0.5) - 0.5) * weight / max(weighted_total, 1.0)

    dominant = tuple(
        trait
        for trait, value in sorted(centroid.items(), key=lambda item: (-item[1], item[0]))[:5]
        if value >= 0.55
    )
    underrepresented = tuple(
        trait
        for trait, value in sorted(centroid.items(), key=lambda item: (item[1], item[0]))[:6]
        if value <= 0.45 and trait not in {"complexity", "micro_intensity"}
    )
    role_counts = Counter(item.role_hint for item in matches if item.role_hint and int(item.hero_id or 0) in selected)
    credible_roles = tuple(
        role for role, count in sorted(role_counts.items(), key=lambda item: (-item[1], item[0])) if count >= 3
    )
    confidence = min(1.0, 0.45 * min(1.0, len(selected) / 5.0) + 0.55 * min(1.0, total / 40.0))
    return HeroPoolProfile(
        hero_ids=tuple(sorted(selected)),
        usage_counts=dict(selected),
        centroid=centroid,
        dominant_traits=dominant,
        underrepresented_traits=underrepresented,
        credible_roles=credible_roles,
        confidence_score=confidence,
    )


def relationship_between(
    left: HeroTaxonomyEntry,
    right: HeroTaxonomyEntry,
    *,
    credible_roles: Sequence[str] = (),
) -> HeroRelationship:
    left_vector = _vector(left)
    right_vector = _vector(right)
    shared_primary = _shared_traits(left_vector, right_vector, threshold=0.65)
    shared_secondary = tuple(
        trait
        for trait in _shared_traits(left_vector, right_vector, threshold=0.35)
        if trait not in shared_primary
    )
    unique_to_left = tuple(
        trait
        for trait in TRAITS
        if left_vector[trait] >= 0.65 and right_vector[trait] < 0.45
    )
    unique_to_right = tuple(
        trait
        for trait in TRAITS
        if right_vector[trait] >= 0.65 and left_vector[trait] < 0.45
    )
    role_overlap = _role_compatibility(left.roles, right.roles, credible_roles)
    return HeroRelationship(
        hero_a_id=left.hero_id,
        hero_b_id=right.hero_id,
        shared_primary_traits=shared_primary,
        shared_secondary_traits=shared_secondary,
        unique_to_a=unique_to_left,
        unique_to_b=unique_to_right,
        functional_similarity=_similarity(left_vector, right_vector),
        role_compatibility=role_overlap,
        complexity_distance=abs(left_vector["complexity"] - right_vector["complexity"]),
        micro_distance=abs(left_vector["micro_intensity"] - right_vector["micro_intensity"]),
    )


def pool_similarity(entry: HeroTaxonomyEntry, profile: HeroPoolProfile) -> float:
    return _similarity(_vector(entry), profile.centroid)


def role_compatibility(entry: HeroTaxonomyEntry, profile: HeroPoolProfile) -> float:
    if not profile.credible_roles:
        return 0.5
    return max(0.25, sum(role in entry.roles for role in profile.credible_roles) / len(profile.credible_roles))


def learning_distance(entry: HeroTaxonomyEntry, profile: HeroPoolProfile) -> float:
    return min(
        1.0,
        0.55 * abs(entry.traits.get("complexity", 0.5) - profile.centroid.get("complexity", 0.5))
        + 0.45 * abs(entry.traits.get("micro_intensity", 0.5) - profile.centroid.get("micro_intensity", 0.5)),
    )


def candidate_traits(entry: HeroTaxonomyEntry, profile: HeroPoolProfile) -> tuple[tuple[str, ...], tuple[str, ...]]:
    anchors = tuple(
        trait
        for trait in profile.dominant_traits
        if entry.traits.get(trait, 0.0) >= 0.55
    )
    added = tuple(
        trait
        for trait in profile.underrepresented_traits
        if entry.traits.get(trait, 0.0) >= 0.60
    )
    return anchors, added


def trait_label(trait: str) -> str:
    return _TRAIT_LABELS.get(trait, trait.replace("_", " "))


def expression_difference(entry: HeroTaxonomyEntry, profile: HeroPoolProfile, *, limit: int = 3) -> tuple[str, ...]:
    differences = sorted(
        (
            abs(entry.traits.get(trait, 0.5) - profile.centroid.get(trait, 0.5)),
            trait,
        )
        for trait in TRAITS
        if trait not in {"complexity", "micro_intensity"}
    )
    return tuple(trait_label(trait) for distance, trait in reversed(differences) if distance >= 0.18)[:limit]


def _vector(entry: HeroTaxonomyEntry) -> dict[str, float]:
    return {trait: float(entry.traits.get(trait, 0.5)) for trait in TRAITS}


def _similarity(left: dict[str, float], right: dict[str, float]) -> float:
    distance = math.sqrt(sum((left.get(trait, 0.5) - right.get(trait, 0.5)) ** 2 for trait in TRAITS) / len(TRAITS))
    return max(0.0, min(1.0, 1.0 - distance))


def _shared_traits(left: dict[str, float], right: dict[str, float], *, threshold: float) -> tuple[str, ...]:
    return tuple(
        trait
        for trait, _value in sorted(
            ((trait, min(left[trait], right[trait])) for trait in TRAITS if left[trait] >= threshold and right[trait] >= threshold),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _role_compatibility(left: Sequence[str], right: Sequence[str], credible_roles: Sequence[str]) -> float:
    if credible_roles:
        return max(0.25, sum(role in left and role in right for role in credible_roles) / len(credible_roles))
    if not left or not right:
        return 0.5
    return len(set(left) & set(right)) / max(len(set(left) | set(right)), 1)


__all__ = [
    "HERO_EXPRESSIONS_VERSION",
    "HERO_RELATIONSHIPS_VERSION",
    "HeroPoolProfile",
    "HeroRelationship",
    "build_pool_profile",
    "candidate_traits",
    "expression_difference",
    "learning_distance",
    "pool_similarity",
    "relationship_between",
    "role_compatibility",
    "trait_label",
]
