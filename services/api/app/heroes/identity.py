from __future__ import annotations

import math
from dataclasses import dataclass, replace
from statistics import mean
from typing import Any

from app.dna.features.models import DnaFeatureSet
from app.heroes.knowledge import SnapshotHeroKnowledgeProvider
from app.heroes.taxonomy import HeroTaxonomy, HeroTaxonomyEntry, load_default_taxonomy

HERO_IDENTITY_VERSION = "hero-identity-1.1.0"


@dataclass(frozen=True, slots=True)
class HeroCard:
    hero_id: int
    name: str
    portrait_url: str | None
    score: float
    component_scores: dict[str, float]
    matches: int
    roles: tuple[str, ...]
    traits: tuple[str, ...]
    receipts: tuple[str, ...]
    reason_key: str
    confidence: str = "moderate"
    portrait_asset_version: str = "hero-assets-1.0.0"

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "name": self.name,
            "portrait_url": self.portrait_url,
            "score": round(self.score, 6),
            "component_scores": {key: round(value, 6) for key, value in self.component_scores.items()},
            "matches": self.matches,
            "roles": list(self.roles),
            "traits": list(self.traits),
            "receipts": list(self.receipts),
            "reason_key": self.reason_key,
            "confidence": self.confidence,
            "portrait_asset_version": self.portrait_asset_version,
        }


@dataclass(frozen=True, slots=True)
class HeroIdentityResult:
    signature: HeroCard | None
    comfort_picks: tuple[HeroCard, ...]
    patterns: tuple[dict[str, Any], ...]
    recommendations: tuple[dict[str, Any], ...]
    taxonomy_version: str | None
    limitations: tuple[str, ...] = ()
    identity_version: str = HERO_IDENTITY_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "signature": self.signature.as_dict() if self.signature else None,
            "comfort_picks": [item.as_dict() for item in self.comfort_picks],
            "patterns": [dict(item) for item in self.patterns],
            "recommendations": [dict(item) for item in self.recommendations],
            "taxonomy_version": self.taxonomy_version,
            "limitations": list(self.limitations),
            "identity_version": self.identity_version,
        }


def select_hero_identity(
    features: DnaFeatureSet,
    taxonomy: HeroTaxonomy | None = None,
) -> HeroIdentityResult:
    if taxonomy is None:
        try:
            taxonomy = load_default_taxonomy()
        except (OSError, ValueError, TypeError):
            # Hero taxonomy is editorial enrichment. A malformed/missing
            # snapshot must not turn an otherwise valid DNA report into a
            # failed analysis.
            return HeroIdentityResult(
                None,
                (),
                (),
                (),
                None,
                ("hero_taxonomy_unavailable",),
            )
    if not features.hero_counts:
        return HeroIdentityResult(None, (), (), (), taxonomy.version, ("no_valid_hero_history",))
    dated = sorted(
        (item for item in features.matches if item.started_at is not None),
        key=lambda item: (item.started_at or 0, item.match_id),
    )
    latest = max((item.started_at or 0 for item in dated), default=0)
    minimum_games = 5 if features.sample_size >= 60 else 3
    candidates = []
    for hero_id, count in features.hero_counts.items():
        if count < minimum_games:
            continue
        hero = taxonomy.get(hero_id)
        if hero is None or not hero.available:
            continue
        hero_rows = [item for item in features.matches if item.hero_id == hero_id]
        components = _components(hero_id, count, hero_rows, dated, latest, features, taxonomy)
        score = _weighted_score(components, taxonomy_available=True)
        candidates.append(_card(hero, score, components, hero_rows, features))

    if not candidates:
        return HeroIdentityResult(
            None,
            (),
            (),
            (),
            taxonomy.version,
            ("no_hero_reached_the_stability_threshold",),
        )

    candidates.sort(key=lambda item: (-item.score, -item.matches, item.hero_id))
    signature = replace(_stable_signature_candidate(candidates), reason_key="signature_identity")
    comfort_candidates = [
        item for item in candidates if _comfort_eligible(item, dated_count=len(dated))
    ]
    comfort_candidates.sort(key=lambda item: (-_comfort_score(item), -item.matches, item.hero_id))
    limit = 3 if features.sample_size < 60 else min(5, len(comfort_candidates))
    comfort = tuple(
        replace(
            item,
            score=_comfort_score(item),
            reason_key="signature_identity" if item.hero_id == signature.hero_id else "comfort_pick",
        )
        for item in comfort_candidates[:limit]
    )
    if not comfort:
        comfort = (signature,)
    limitations: list[str] = []
    if len(dated) < features.sample_size * 0.6:
        limitations.append("recency and persistence are based on partial timestamps")
    try:
        from app.heroes.patterns import extract_hero_patterns

        patterns = extract_hero_patterns(signature, comfort, taxonomy)
    except (KeyError, TypeError, ValueError):
        patterns = []
        limitations.append("hero_pattern_unavailable")
    try:
        from app.heroes.recommendations import recommend_heroes

        recommendations = recommend_heroes(
            comfort,
            features,
            taxonomy,
            hero_knowledge=SnapshotHeroKnowledgeProvider(),
        )
    except (KeyError, TypeError, ValueError):
        recommendations = []
        limitations.append("hero_recommendations_unavailable")
    return HeroIdentityResult(
        signature=signature,
        comfort_picks=comfort,
        patterns=tuple(patterns),
        recommendations=tuple(recommendations),
        taxonomy_version=taxonomy.version,
        limitations=tuple(limitations),
    )


def _components(
    hero_id: int,
    count: int,
    rows: list[Any],
    dated: list[Any],
    latest: int,
    features: DnaFeatureSet,
    taxonomy: HeroTaxonomy,
) -> dict[str, float]:
    total = max(features.sample_size, 1)
    frequency = _smoothed_share(count, total)
    if dated and latest:
        age_days = (latest - max((item.started_at or 0 for item in rows), default=latest)) / 86400
        recency = math.exp(-max(0.0, age_days) * math.log(2) / 60)
    else:
        recency = 0.5
    windows = _window_count(rows, dated)
    total_windows = max(1, min(4, len(dated)))
    repeat = windows / total_windows
    persistence = _persistence(rows)
    role_fit = _role_fit(hero_id, rows, features, taxonomy)
    output = mean(features.performance_by_match.get(item.match_id, 0.5) for item in rows) if rows else 0.5
    semantic = _semantic_fit(hero_id, features.familiar_heroes, taxonomy)
    return {
        "frequency": frequency,
        "recency": recency,
        "repeat": repeat,
        "persistence": persistence,
        "role_fit": role_fit,
        "comfort_output": max(0.0, min(1.0, output)),
        "semantic_fit": semantic,
    }


def _weighted_score(components: dict[str, float], *, taxonomy_available: bool) -> float:
    weights = {
        "frequency": 0.25,
        "recency": 0.15,
        "repeat": 0.15,
        "persistence": 0.10,
        "role_fit": 0.10,
        "comfort_output": 0.10,
        "semantic_fit": 0.15,
    }
    if not taxonomy_available:
        weights["semantic_fit"] = 0.0
        remainder = 1.0 / sum(value for key, value in weights.items() if key != "semantic_fit")
        for key in weights:
            if key != "semantic_fit":
                weights[key] *= remainder
    return sum(weights[key] * components[key] for key in weights)


def _stable_signature_candidate(candidates: list[HeroCard]) -> HeroCard:
    best_score = candidates[0].score
    tie_window = [item for item in candidates if best_score - item.score <= 0.02]
    return max(
        tie_window,
        key=lambda item: (
            item.component_scores.get("repeat", 0.0),
            item.component_scores.get("persistence", 0.0),
            item.matches,
            -item.hero_id,
        ),
    )


def _comfort_score(item: HeroCard) -> float:
    components = item.component_scores
    return (
        0.35 * components.get("frequency", 0.0)
        + 0.20 * components.get("recency", 0.0)
        + 0.20 * components.get("repeat", 0.0)
        + 0.10 * components.get("role_fit", 0.0)
        + 0.15 * components.get("comfort_output", 0.0)
    )


def _comfort_eligible(item: HeroCard, *, dated_count: int) -> bool:
    # With a short observed date range, recurrence cannot be measured fairly.
    return dated_count < 20 or item.component_scores.get("repeat", 0.0) >= 0.50


def _card(
    hero: HeroTaxonomyEntry,
    score: float,
    components: dict[str, float],
    rows: list[Any],
    features: DnaFeatureSet,
) -> HeroCard:
    receipts = (
        "keeps returning" if components["repeat"] >= 0.5 else "appears in a focused window",
        f"{len(rows)} observed games",
        "fits your role mix" if components["role_fit"] >= 0.6 else "adds a different role angle",
    )
    return HeroCard(
        hero_id=hero.hero_id,
        name=hero.name,
        portrait_url=hero.portrait_url,
        score=score,
        component_scores=components,
        matches=len(rows),
        roles=hero.roles,
        traits=tuple(sorted(key for key, value in hero.traits.items() if value >= 0.65)),
        receipts=receipts,
        reason_key="comfort_pick",
        confidence="high" if len(rows) >= 8 and components["repeat"] >= 0.5 else "moderate",
        portrait_asset_version=hero.portrait_asset_version,
    )


def _role_fit(hero_id: int, rows: list[Any], features: DnaFeatureSet, taxonomy: HeroTaxonomy) -> float:
    hero = taxonomy.get(hero_id)
    if not hero or not features.dominant_role:
        return 0.5
    return 1.0 if features.dominant_role in hero.roles else 0.45


def _semantic_fit(hero_id: int, familiar: frozenset[int], taxonomy: HeroTaxonomy) -> float:
    hero = taxonomy.get(hero_id)
    if not hero or not familiar:
        return 0.5
    other = [taxonomy.get(item) for item in familiar if item != hero_id and taxonomy.get(item)]
    if not other:
        return 0.5
    return sum(_trait_similarity(hero, item) for item in other if item) / len(other)


def _trait_similarity(left: HeroTaxonomyEntry, right: HeroTaxonomyEntry) -> float:
    keys = set(left.traits) | set(right.traits)
    if not keys:
        return 0.5
    distance = sum((left.traits.get(key, 0.5) - right.traits.get(key, 0.5)) ** 2 for key in keys) / len(keys)
    return max(0.0, min(1.0, 1.0 - math.sqrt(distance)))


def _smoothed_share(count: int, total: int) -> float:
    return (count + 1.5) / (total + 3.0)


def _window_count(rows: list[Any], dated: list[Any]) -> int:
    if not dated:
        return 1
    positions = {item.match_id: index for index, item in enumerate(dated)}
    windows = {min(3, positions[item.match_id] * 4 // max(1, len(dated))) for item in rows if item.match_id in positions}
    return len(windows)


def _persistence(rows: list[Any]) -> float:
    patches = {item.patch for item in rows if item.patch}
    dates = {((item.started_at or 0) // (30 * 86400)) for item in rows if item.started_at}
    observations = patches or dates
    return min(1.0, len(observations) / 4) if observations else 0.35
