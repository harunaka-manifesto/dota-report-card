"""Deterministic adjacent-hero recommendations for Free DNA."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from app.dna.features.models import DnaFeatureSet
from app.heroes.identity import HeroCard
from app.heroes.knowledge import (
    EMPIRICAL_SUPPORT_BANDS,
    FUNCTIONAL_JOBS,
    HERO_DEMAND_FAMILIES,
    HERO_KNOWLEDGE_SCHEMA_VERSION,
    SEMANTIC_CONFIDENCE_BANDS,
    HeroKnowledgeProvider,
    NormalizedHeroKnowledge,
)
from app.heroes.taxonomy import TRAITS, HeroTaxonomy, HeroTaxonomyEntry
from app.ingestion.summary_normalize import NormalizedSummaryMatch

RECOMMENDATION_VERSION = "hero-recommendations-1.1.0"
SEMANTIC_RECOMMENDATION_VERSION = "hero-recommendations-semantic-1.0.0"

RecommendationIntent = Literal[
    "double_down",
    "adjacent_move",
    "fill_gap",
    "change_angle",
    "specialist",
]
RECOMMENDATION_INTENTS = frozenset(
    {"double_down", "adjacent_move", "fill_gap", "change_angle", "specialist"}
)
LearningDistance = Literal["low", "moderate", "high"]
LEARNING_DISTANCES = frozenset({"low", "moderate", "high"})
RoleFit = Literal["supported", "conditional", "unsupported"]
ROLE_FITS = frozenset({"supported", "conditional", "unsupported"})
EmpiricalSupport = Literal["high", "medium", "low", "unknown"]
SemanticConfidence = Literal["high", "medium", "low"]


@dataclass(frozen=True, slots=True)
class HeroRecommendationRationale:
    """Finite, evidence-carrying handoff from hero semantics to copy."""

    hero_id: int
    intent: RecommendationIntent
    familiar_anchors: tuple[str, ...]
    adds: tuple[str, ...]
    new_demands: tuple[str, ...]
    learning_distance: LearningDistance
    role_fit: RoleFit
    empirical_support: EmpiricalSupport
    confidence: SemanticConfidence
    limitations: tuple[str, ...] = ()
    provenance_versions: Mapping[str, str] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    eligible: bool = True

    def __post_init__(self) -> None:
        if self.hero_id <= 0:
            raise ValueError("Hero recommendation rationale requires a positive hero ID")
        if self.intent not in RECOMMENDATION_INTENTS:
            raise ValueError("Hero recommendation rationale contains an unknown intent")
        if self.learning_distance not in LEARNING_DISTANCES:
            raise ValueError("Hero recommendation rationale contains an unknown learning distance")
        if self.role_fit not in ROLE_FITS:
            raise ValueError("Hero recommendation rationale contains an unknown role fit")
        if any(item not in FUNCTIONAL_JOBS for item in (*self.familiar_anchors, *self.adds)):
            raise ValueError("Hero recommendation rationale contains an unknown functional job")
        if any(item not in HERO_DEMAND_FAMILIES for item in self.new_demands):
            raise ValueError("Hero recommendation rationale contains an unknown demand family")
        if self.empirical_support not in EMPIRICAL_SUPPORT_BANDS:
            raise ValueError("Hero recommendation rationale contains an unknown empirical band")
        if self.confidence not in SEMANTIC_CONFIDENCE_BANDS:
            raise ValueError("Hero recommendation rationale contains an unknown confidence band")

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "intent": self.intent,
            "familiar_anchors": list(self.familiar_anchors),
            "adds": list(self.adds),
            "new_demands": list(self.new_demands),
            "learning_distance": self.learning_distance,
            "role_fit": self.role_fit,
            "empirical_support": self.empirical_support,
            "confidence": self.confidence,
            "limitations": list(self.limitations),
            "provenance_versions": dict(self.provenance_versions),
            "evidence_refs": list(self.evidence_refs),
            "eligible": self.eligible,
        }


def recommend_semantic_heroes(
    matches: Sequence[NormalizedSummaryMatch],
    provider: HeroKnowledgeProvider,
    *,
    intent: RecommendationIntent = "adjacent_move",
    limit: int = 3,
    include_ineligible: bool = False,
) -> list[HeroRecommendationRationale]:
    """Rank candidates from normalized functions and demands only.

    The ranking is decomposable: anchors, useful additions, role fit, demand
    distance, empirical support, and confidence are each explicit.  Unknown
    values remain unknown and only reduce eligibility/confidence; they are not
    converted into a neutral numeric trait.
    """

    if limit <= 0:
        return []
    entries = tuple(getattr(provider, "entries", ()))
    if not entries:
        return []
    usage = Counter(int(item.hero_id) for item in matches if item.hero_id is not None)
    observed_jobs, observed_demands = _observed_semantics(matches, provider)
    credible_roles = {
        role
        for role, count in Counter(item.role_hint for item in matches if item.role_hint).items()
        if count >= 3
    }
    candidates: list[tuple[tuple[Any, ...], HeroRecommendationRationale]] = []
    for entry in sorted(entries, key=lambda item: item.hero_id):
        if entry.hero_id in usage:
            continue
        rationale = _rationale_for_candidate(
            entry,
            observed_jobs=observed_jobs,
            observed_demands=observed_demands,
            credible_roles=credible_roles,
            intent=intent,
            provider_version=provider.version,
        )
        if not rationale.eligible and not include_ineligible:
            continue
        rank = _semantic_rank(rationale, entry)
        candidates.append((rank, rationale))
    candidates.sort(key=lambda item: (*item[0], item[1].hero_id))
    selected: list[HeroRecommendationRationale] = []
    selected_adds: set[str] = set()
    for _rank, rationale in candidates:
        if len(selected) >= limit:
            break
        if selected and rationale.adds and set(rationale.adds).issubset(selected_adds):
            continue
        selected.append(rationale)
        selected_adds.update(rationale.adds)
    return selected


def _observed_semantics(
    matches: Sequence[NormalizedSummaryMatch], provider: HeroKnowledgeProvider
) -> tuple[set[str], dict[str, str]]:
    jobs: set[str] = set()
    demands: dict[str, str] = {}
    for hero_id in sorted({int(item.hero_id) for item in matches if item.hero_id is not None}):
        entry = provider.get(hero_id)
        if entry is None:
            continue
        jobs.update(entry.primary_functions)
        jobs.update(entry.secondary_functions)
        for key, band in entry.demands.items():
            previous = demands.get(key)
            if previous == "high" or band == previous:
                continue
            if band == "high" or previous is None:
                demands[key] = band
            elif previous == "unknown":
                demands[key] = band
    return jobs, demands


def _rationale_for_candidate(
    entry: NormalizedHeroKnowledge,
    *,
    observed_jobs: set[str],
    observed_demands: Mapping[str, str],
    credible_roles: set[str],
    intent: RecommendationIntent,
    provider_version: str,
) -> HeroRecommendationRationale:
    functions = tuple(dict.fromkeys((*entry.primary_functions, *entry.secondary_functions)))
    familiar = tuple(item for item in functions if item in observed_jobs)
    adds = tuple(item for item in functions if item not in observed_jobs)
    new_demands = tuple(
        key
        for key in HERO_DEMAND_FAMILIES
        if entry.demands.get(key) in {"medium", "high"}
        and observed_demands.get(key) not in {"medium", "high"}
    )
    role_fit = _semantic_role_fit(entry.roles, credible_roles)
    learning_distance = _learning_distance(entry, observed_demands, new_demands)
    empirical_support = _empirical_support(entry.empirical_support)
    confidence = _semantic_confidence(entry, role_fit, empirical_support, new_demands)
    limitations: list[str] = []
    if empirical_support == "unknown":
        limitations.append("Empirical support is unknown; this is not a current-meta claim.")
    if any(entry.demands.get(key) == "unknown" for key in HERO_DEMAND_FAMILIES):
        limitations.append("Some hero-demand families are unknown in the frozen snapshot.")
    if role_fit == "conditional":
        limitations.append("Role fit is conditional because stable observed role context is unavailable.")
    if role_fit == "unsupported":
        limitations.append("Observed role context does not support this hero as an active bridge.")
    if not functions:
        limitations.append("No reviewed functional jobs are available for this hero.")
    if intent in {"adjacent_move", "fill_gap"} and not adds:
        limitations.append("The candidate does not add a clearly missing functional job.")
    if not new_demands and entry.demands:
        limitations.append("No new reviewed demand family is clearly separated from the observed pool.")
    eligible = bool(functions and familiar and role_fit != "unsupported" and confidence != "low")
    if intent in {"adjacent_move", "fill_gap"}:
        eligible = eligible and bool(adds)
    if intent == "fill_gap":
        eligible = eligible and bool(adds)
    if learning_distance == "high" and intent in {"adjacent_move", "fill_gap"}:
        eligible = False
        limitations.append("The learning jump is high for an adjacent bridge.")
    if not any(entry.demands.get(key) in {"low", "medium", "high"} for key in HERO_DEMAND_FAMILIES):
        eligible = False
    return HeroRecommendationRationale(
        hero_id=entry.hero_id,
        intent=intent,
        familiar_anchors=familiar[:4],
        adds=adds[:4],
        new_demands=new_demands[:4],
        learning_distance=learning_distance,
        role_fit=role_fit,
        empirical_support=empirical_support,
        confidence=confidence,
        limitations=tuple(dict.fromkeys(limitations)),
        provenance_versions={
            **dict(entry.provenance_versions),
            "hero_recommendations_semantic": SEMANTIC_RECOMMENDATION_VERSION,
            "hero_knowledge_schema": HERO_KNOWLEDGE_SCHEMA_VERSION,
            "hero_knowledge": provider_version,
        },
        evidence_refs=entry.evidence_refs,
        eligible=eligible,
    )


def _semantic_role_fit(roles: Sequence[str], credible_roles: set[str]) -> RoleFit:
    if not credible_roles or not roles:
        return "conditional"
    return "supported" if set(roles) & credible_roles else "unsupported"


def _learning_distance(
    entry: NormalizedHeroKnowledge,
    observed_demands: Mapping[str, str],
    new_demands: Sequence[str],
) -> LearningDistance:
    unknown = sum(entry.demands.get(key) == "unknown" for key in HERO_DEMAND_FAMILIES)
    high_new = sum(
        entry.demands.get(key) == "high" and observed_demands.get(key) not in {"medium", "high"}
        for key in HERO_DEMAND_FAMILIES
    )
    if high_new >= 3 or "micro" in new_demands and entry.demands.get("micro") == "high":
        return "high"
    if len(new_demands) >= 2 or unknown >= 4:
        return "moderate"
    return "low"


def _empirical_support(value: str) -> EmpiricalSupport:
    normalized = str(value).casefold()
    return normalized if normalized in EMPIRICAL_SUPPORT_BANDS else "unknown"  # type: ignore[return-value]


def _semantic_confidence(
    entry: NormalizedHeroKnowledge,
    role_fit: RoleFit,
    empirical_support: EmpiricalSupport,
    new_demands: Sequence[str],
) -> SemanticConfidence:
    value = str(entry.confidence).casefold()
    if value == "moderate":
        value = "medium"
    if value not in SEMANTIC_CONFIDENCE_BANDS or entry.review_status not in {"reviewed", "approved"}:
        return "low"
    if role_fit == "conditional" or empirical_support == "unknown" or not new_demands:
        return "medium" if value == "high" else "low"
    return value  # type: ignore[return-value]


def _semantic_rank(
    rationale: HeroRecommendationRationale, entry: NormalizedHeroKnowledge
) -> tuple[Any, ...]:
    # Lower tuples rank first.  Every component maps to a finite semantic band
    # or a count; no aggregate score is exposed to the player.
    role_rank = {"supported": 0, "conditional": 1, "unsupported": 2}[rationale.role_fit]
    confidence_rank = {"high": 0, "medium": 1, "low": 2}[rationale.confidence]
    empirical_rank = {"high": 0, "medium": 1, "low": 2, "unknown": 3}[rationale.empirical_support]
    distance_rank = {"low": 0, "moderate": 1, "high": 2}[rationale.learning_distance]
    return (
        -len(rationale.familiar_anchors),
        -len(rationale.adds),
        role_rank,
        distance_rank,
        empirical_rank,
        confidence_rank,
        -len(entry.primary_functions),
    )


def recommend_heroes(
    comfort: tuple[HeroCard, ...],
    features: DnaFeatureSet,
    taxonomy: HeroTaxonomy,
    *,
    hero_knowledge: HeroKnowledgeProvider | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Select a small, diverse set using score + maximal marginal relevance.

    Exposure is an eligibility constraint, not a reason to hide every hero the
    player has ever touched: only heroes with five or more games, or heroes in
    the player's personal top-ten pool, are excluded.
    """

    if not comfort or limit <= 0:
        return []
    if hero_knowledge is not None:
        return _recommend_heroes_from_semantics(features, taxonomy, hero_knowledge, limit=limit)
    # Historical 5.0/5.1 callers remain on the taxonomy adapter until their
    # report snapshots are migrated; active v5.2 passes hero_knowledge above.
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


def _recommend_heroes_from_semantics(
    features: DnaFeatureSet,
    taxonomy: HeroTaxonomy,
    provider: HeroKnowledgeProvider,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    rationales = recommend_semantic_heroes(
        features.matches,
        provider,
        intent="adjacent_move",
        limit=limit,
    )
    result: list[dict[str, Any]] = []
    for index, rationale in enumerate(rationales):
        entry = taxonomy.get(rationale.hero_id)
        knowledge = provider.get(rationale.hero_id)
        if entry is None or knowledge is None:
            continue
        result.append(
            {
                "hero_id": entry.hero_id,
                "name": knowledge.display_name,
                "portrait_url": entry.portrait_url,
                "portrait_asset_version": entry.portrait_asset_version,
                "fit_band": "strong" if rationale.confidence == "high" else "good",
                "score": round(1.0 / (index + 1), 6),
                "familiar_traits": list(rationale.familiar_anchors),
                "new_traits": list(rationale.adds),
                "plausible_roles": list(knowledge.roles),
                "role_change": rationale.role_fit == "unsupported",
                "reason_key": "semantic_adjacent_move",
                "rationale": rationale.as_dict(),
                "recommendation_version": SEMANTIC_RECOMMENDATION_VERSION,
            }
        )
    return result


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


__all__ = [
    "HeroRecommendationRationale",
    "RECOMMENDATION_INTENTS",
    "LEARNING_DISTANCES",
    "ROLE_FITS",
    "recommend_semantic_heroes",
    "recommend_heroes",
    "RECOMMENDATION_VERSION",
    "SEMANTIC_RECOMMENDATION_VERSION",
]
