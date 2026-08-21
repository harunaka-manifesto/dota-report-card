"""Server-owned, reviewed action modules for P01 and P02.

These actions are deliberately separate from Pattern qualification.  A
qualified Pattern identifies an evidence-backed relationship; this module
turns only the two reviewed relationships into deterministic, explainable
next-step choices.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from app.behavior.models import (
    ActionStatus,
    ComfortEdgeAction,
    ComfortEdgeDevelopmentReason,
    ComfortEdgeHeroReliability,
    PatternHeroRecommendation,
    PatternResult,
    SamePlaybookAction,
)
from app.hero_portfolio.config import PORTFOLIO_CONFIG
from app.hero_portfolio.version import (
    HERO_EXPRESSIONS_VERSION,
    HERO_MATCHUPS_VERSION,
    HERO_RELATIONSHIPS_VERSION,
    HERO_RELIABILITY_VERSION,
    HERO_SITUATIONS_VERSION,
    HERO_SYNERGIES_VERSION,
    PATTERN_ACTIONS_VERSION,
)
from app.heroes.evidence import (
    representative_matchups,
    representative_synergies,
    situations_for_traits,
)
from app.heroes.relationships import (
    build_pool_profile,
    candidate_traits,
    expression_difference,
    learning_distance,
    pool_similarity,
    role_compatibility,
    trait_label,
)
from app.heroes.taxonomy import HeroTaxonomy, HeroTaxonomyEntry
from app.ingestion.summary_normalize import NormalizedSummaryMatch

_PROVENANCE_KEYS = {
    "pattern_actions": PATTERN_ACTIONS_VERSION,
    "hero_relationships": HERO_RELATIONSHIPS_VERSION,
    "hero_expressions": HERO_EXPRESSIONS_VERSION,
    "hero_reliability": HERO_RELIABILITY_VERSION,
    "hero_matchups": HERO_MATCHUPS_VERSION,
    "hero_synergies": HERO_SYNERGIES_VERSION,
    "hero_situations": HERO_SITUATIONS_VERSION,
}


def attach_pattern_actions(
    patterns: Sequence[PatternResult],
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
) -> tuple[PatternResult, ...]:
    """Attach only reviewed actions to qualified Pattern results."""

    result: list[PatternResult] = []
    for pattern in patterns:
        action: SamePlaybookAction | ComfortEdgeAction | None = None
        if pattern.status == "qualified":
            if pattern.key == "same_playbook":
                action = build_same_playbook_action(matches, taxonomy)
            elif pattern.key == "comfort_edge":
                action = build_comfort_edge_action(matches, taxonomy)
        result.append(replace(pattern, action=action))
    return tuple(result)


def build_same_playbook_action(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
) -> SamePlaybookAction:
    profile = build_pool_profile(matches, taxonomy)
    if len(profile.hero_ids) < 2 or not profile.dominant_traits:
        return SamePlaybookAction(
            action_type="same_playbook",
            status="unavailable",
            dominant_traits=tuple(trait_label(item) for item in profile.dominant_traits),
            underrepresented_traits=tuple(trait_label(item) for item in profile.underrepresented_traits),
            deepen=(),
            stretch=(),
            confidence_score=profile.confidence_score,
            limitations=("At least two established, taxonomy-covered heroes are needed to build a playbook path.",),
            provenance_versions=dict(_PROVENANCE_KEYS),
        )

    deepen = _recommendations(matches, taxonomy, profile, direction="deepen")
    stretch = _recommendations(matches, taxonomy, profile, direction="stretch")
    status: ActionStatus = "available" if deepen and stretch else "limited" if deepen or stretch else "unavailable"
    limitations: list[str] = []
    if len(deepen) < 3:
        limitations.append("Fewer than three high-confidence deepen candidates cleared the functional-fit gates.")
    if len(stretch) < 3:
        limitations.append("Fewer than three high-confidence stretch candidates cleared the anchor and learning-distance gates.")
    if status == "unavailable":
        limitations.append("No reviewed hero relationship was strong enough to recommend without filler.")
    return SamePlaybookAction(
        action_type="same_playbook",
        status=status,
        dominant_traits=tuple(trait_label(item) for item in profile.dominant_traits),
        underrepresented_traits=tuple(trait_label(item) for item in profile.underrepresented_traits),
        deepen=deepen,
        stretch=stretch,
        confidence_score=profile.confidence_score,
        limitations=tuple(limitations),
        provenance_versions=dict(_PROVENANCE_KEYS),
    )


def build_comfort_edge_action(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
) -> ComfortEdgeAction:
    rows = _latest_usable_rows(matches)
    reliability = _rank_hero_reliability(rows, taxonomy)
    if len(reliability) < PORTFOLIO_CONFIG.p02_min_action_heroes:
        return ComfortEdgeAction(
            action_type="comfort_edge",
            status="unavailable",
            ranked_heroes=tuple(reliability),
            reference_core_hero_ids=tuple(item.hero_id for item in reliability[:2]),
            development=(),
            confidence_score=min((item.confidence_score for item in reliability), default=0.0),
            limitations=(
                f"Comfort Edge needs {PORTFOLIO_CONFIG.p02_min_action_heroes} sufficiently rankable heroes; "
                f"only {len(reliability)} cleared the per-hero sample gate.",
            ),
            provenance_versions=dict(_PROVENANCE_KEYS),
        )

    top_five = tuple(reliability[:5])
    profile = build_pool_profile(rows, taxonomy, hero_ids=[item.hero_id for item in top_five])
    reference_core = top_five[: PORTFOLIO_CONFIG.p02_reference_core_size]
    development = tuple(
        _development_reason(item, reference_core, profile, taxonomy)
        for item in top_five[PORTFOLIO_CONFIG.p02_reference_core_size :]
    )
    examples_complete = all(
        reason.teammate_examples and reason.enemy_examples
        for reason in development
    )
    status: ActionStatus = "available" if examples_complete else "limited"
    limitations = [
        "Reliability is player-relative and confidence-adjusted; it is not a current-patch hero tier list.",
    ]
    if not examples_complete:
        limitations.append(
            "Concrete teammate and enemy examples remain limited until reviewed aggregate artifacts clear their confidence gate."
        )
    else:
        limitations.append(
            "Concrete teammate or enemy examples appear only when the versioned aggregate evidence clears its confidence gate."
        )
    return ComfortEdgeAction(
        action_type="comfort_edge",
        status=status,
        ranked_heroes=top_five,
        reference_core_hero_ids=tuple(item.hero_id for item in reference_core),
        development=development,
        confidence_score=min(item.confidence_score for item in top_five),
        limitations=tuple(limitations),
        provenance_versions=dict(_PROVENANCE_KEYS),
    )


def _recommendations(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    profile: Any,
    *,
    direction: str,
) -> tuple[PatternHeroRecommendation, ...]:
    candidates: list[tuple[float, HeroTaxonomyEntry, tuple[str, ...], tuple[str, ...], float, float]] = []
    for entry in sorted(taxonomy.heroes.values(), key=lambda item: item.hero_id):
        if not entry.available or entry.hero_id in profile.usage_counts:
            continue
        anchors, added = candidate_traits(entry, profile)
        similarity = pool_similarity(entry, profile)
        role_fit = role_compatibility(entry, profile)
        distance = learning_distance(entry, profile)
        if direction == "deepen":
            if not anchors or similarity < 0.55 or distance > 0.62:
                continue
            score = 0.55 * similarity + 0.25 * role_fit + 0.20 * (1.0 - distance)
        else:
            if not anchors or not added or similarity < 0.42 or similarity > 0.94 or distance > 0.68:
                continue
            anchor_score = min(1.0, len(anchors) / max(len(profile.dominant_traits), 1))
            added_score = min(1.0, len(added) / max(len(profile.underrepresented_traits), 1))
            score = 0.35 * anchor_score + 0.30 * added_score + 0.20 * role_fit + 0.15 * (1.0 - distance)
        confidence = min(1.0, profile.confidence_score * (0.70 + 0.30 * role_fit) * (1.0 - 0.25 * distance))
        candidates.append((score, entry, anchors, added, similarity, confidence))

    candidates.sort(key=lambda item: (-item[0], -item[5], item[1].hero_id))
    selected: list[PatternHeroRecommendation] = []
    selected_traits: set[str] = set()
    for _score, entry, anchors, added, similarity, confidence in candidates:
        if len(selected) >= 3:
            break
        # Keep the small recommendation set meaningfully varied where the
        # taxonomy gives us a choice, rather than returning three clones.
        novelty = min(1.0, len(set(added) - selected_traits) / max(len(added), 1)) if added else 0.25
        if selected and direction == "deepen" and added and set(added).issubset(selected_traits) and novelty == 0:
            continue
        expression = expression_difference(entry, profile)
        anchor_labels = tuple(trait_label(item) for item in anchors[:2])
        added_labels = tuple(trait_label(item) for item in added[:2])
        changed = added_labels or expression or ("a different secondary expression of the same jobs",)
        familiar_text = ", ".join(anchor_labels) or "part of your current functional core"
        changed_text = ", ".join(changed)
        selected.append(
            PatternHeroRecommendation(
                hero_id=entry.hero_id,
                hero_name=entry.name,
                direction=direction,  # type: ignore[arg-type]
                anchor_traits=anchors[:3],
                added_traits=added[:3],
                role_fit=tuple(entry.roles),
                similarity_score=max(0.0, min(1.0, similarity)),
                novelty_score=max(0.0, min(1.0, novelty)),
                confidence_score=max(0.0, min(1.0, confidence)),
                why_it_fits=f"You already lean on {familiar_text}. {entry.name} keeps that anchor while offering {changed_text}.",
                what_stays_familiar=f"You still get the {familiar_text} part of your current game.",
                what_changes=f"This adds {changed_text} without asking you to leave the whole playbook behind.",
                provenance_versions=dict(_PROVENANCE_KEYS),
            )
        )
        selected_traits.update(added)
    return tuple(selected)


def _latest_usable_rows(matches: Sequence[NormalizedSummaryMatch]) -> tuple[NormalizedSummaryMatch, ...]:
    ordered = sorted(
        (
            item
            for item in matches
            if item.hero_id is not None
            and item.won is not None
            and item.duration_seconds is not None
            and item.duration_seconds >= 600
            and item.kills is not None
            and item.deaths is not None
            and item.assists is not None
        ),
        key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id),
    )
    return tuple(ordered[-PORTFOLIO_CONFIG.p02_history_limit :])


def _rank_hero_reliability(
    rows: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
) -> tuple[ComfortEdgeHeroReliability, ...]:
    by_hero: dict[int, list[NormalizedSummaryMatch]] = {}
    for item in rows:
        if item.hero_id is not None and taxonomy.get(item.hero_id) is not None:
            by_hero.setdefault(int(item.hero_id), []).append(item)
    if not by_hero:
        return ()

    credible_roles = Counter(item.role_hint for item in rows if item.role_hint)
    role_order = {role for role, count in credible_roles.items() if count >= 3}
    player_baseline = _weighted_performance(rows, role_order)
    scores: list[ComfortEdgeHeroReliability] = []
    for hero_id, hero_rows in by_hero.items():
        if len(hero_rows) < PORTFOLIO_CONFIG.p02_min_rankable_matches:
            continue
        raw = _weighted_performance(hero_rows, role_order)
        shrink = len(hero_rows) / (len(hero_rows) + PORTFOLIO_CONFIG.p02_shrinkage_prior)
        score = player_baseline + (raw - player_baseline) * shrink
        coverage = len(hero_rows) / max(len(rows), 1)
        confidence = min(1.0, len(hero_rows) / 25.0) * min(1.0, len(hero_rows) / max(len(hero_rows), 1))
        # A small but rankable hero remains visibly uncertain; it can rank,
        # but it cannot silently become a high-confidence recommendation.
        confidence *= 0.85 + 0.15 * min(1.0, coverage * 8.0)
        entry = taxonomy.get(hero_id)
        if entry is None:
            continue
        scores.append(
            ComfortEdgeHeroReliability(
                hero_id=hero_id,
                hero_name=entry.name,
                reliability_rank=0,
                reliability_score=max(0.0, min(1.0, score)),
                confidence_score=max(0.0, min(1.0, confidence)),
                matches=len(hero_rows),
            )
        )
    ordered = sorted(scores, key=lambda item: (-item.reliability_score, -item.confidence_score, item.hero_id))[:5]
    return tuple(replace(item, reliability_rank=index) for index, item in enumerate(ordered, start=1))


def _weighted_performance(
    rows: Sequence[NormalizedSummaryMatch],
    credible_roles: set[str],
) -> float:
    if not rows:
        return 0.5
    ordered = sorted(rows, key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id))
    total_weight = 0.0
    weighted_score = 0.0
    for index, item in enumerate(ordered):
        recency = PORTFOLIO_CONFIG.p02_recency_floor + (1.0 - PORTFOLIO_CONFIG.p02_recency_floor) * (index / max(len(ordered) - 1, 1))
        duration_minutes = max(float(item.duration_seconds or 0) / 60.0, 1.0)
        contribution = min(1.0, ((item.kills or 0) + (item.assists or 0)) / max(duration_minutes * 1.2, 1.0))
        survival = 1.0 - min(1.0, (item.deaths or 0) / max(duration_minutes * 0.75, 1.0))
        outcome = 1.0 if item.won else 0.0
        role = 1.0 if not credible_roles or item.role_hint in credible_roles else 0.5
        row_score = 0.42 * outcome + 0.28 * contribution + 0.20 * survival + 0.10 * role
        weight = recency
        weighted_score += weight * row_score
        total_weight += weight
    return weighted_score / max(total_weight, 1e-9)


def _development_reason(
    item: ComfortEdgeHeroReliability,
    reference_core: Sequence[ComfortEdgeHeroReliability],
    profile: Any,
    taxonomy: HeroTaxonomy,
) -> ComfortEdgeDevelopmentReason:
    entry = taxonomy.get(item.hero_id)
    core_ids = tuple(hero.hero_id for hero in reference_core)
    core_names = tuple(hero.hero_name for hero in reference_core)
    changes = expression_difference(entry, profile) if entry is not None else ()
    if not changes:
        changes = ("a different expression of the jobs your stronger heroes already cover",)
    situations = situations_for_traits(tuple(
        trait for trait in profile.underrepresented_traits if entry is not None and entry.traits.get(trait, 0.0) >= 0.60
    ))
    if not situations:
        situations = ("a draft where the stronger core needs a different way to solve the same broad problem",)
    matchup_records = representative_matchups(item.hero_id)
    synergy_records = representative_synergies(item.hero_id)
    enemy_ids = tuple(record.related_hero_id for record in matchup_records)
    teammate_ids = tuple(record.related_hero_id for record in synergy_records)
    enemy_names = tuple(_hero_name(taxonomy, hero_id) for hero_id in enemy_ids)
    teammate_names = tuple(_hero_name(taxonomy, hero_id) for hero_id in teammate_ids)
    what_changes = ", ".join(changes[:2])
    useful = situations[0]
    why = (
        f"Compared with your stronger {', '.join(core_names)}, {item.hero_name} changes {what_changes}. "
        f"That can matter when {useful}."
    )
    limitations: list[str] = []
    if not enemy_ids:
        limitations.append("No high-confidence aggregate matchup examples are available in the checked-in artifact.")
    if not teammate_ids:
        limitations.append("No high-confidence aggregate teammate-synergy examples are available in the checked-in artifact.")
    return ComfortEdgeDevelopmentReason(
        hero_id=item.hero_id,
        hero_name=item.hero_name,
        reliability_rank=item.reliability_rank,
        reliability_score=item.reliability_score,
        confidence_score=item.confidence_score,
        reference_core_hero_ids=core_ids,
        reference_core_hero_names=core_names,
        what_changes=tuple(changes),
        useful_situations=situations,
        teammate_examples=teammate_ids,
        teammate_example_names=teammate_names,
        enemy_examples=enemy_ids,
        enemy_example_names=enemy_names,
        tradeoffs=("It may ask for a different learning rhythm than the stronger reference core.",),
        why_learn=why,
        limitations=tuple(limitations),
        provenance_versions=dict(_PROVENANCE_KEYS),
    )


def _hero_name(taxonomy: HeroTaxonomy, hero_id: int) -> str:
    entry = taxonomy.get(hero_id)
    return entry.name if entry is not None else str(hero_id)


__all__ = [
    "attach_pattern_actions",
    "build_comfort_edge_action",
    "build_same_playbook_action",
]
