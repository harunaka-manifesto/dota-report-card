"""Independent, gated classification for each context archetype group."""

from __future__ import annotations

import math
from collections.abc import Mapping

from app.behavior.archetypes.registry import ARCHETYPE_GROUP_REGISTRY, ARCHETYPE_REGISTRY_VERSION
from app.behavior.comparisons import clamp
from app.behavior.models import (
    ArchetypePrototype,
    Confidence,
    ContextArchetypeResult,
    ElementResult,
    PatternResult,
)


def classify_archetypes(
    elements: tuple[ElementResult, ...] | list[ElementResult],
    patterns: tuple[PatternResult, ...] | list[PatternResult],
) -> tuple[ContextArchetypeResult, ...]:
    element_map = {item.key: item for item in elements}
    pattern_map = {item.key: item for item in patterns}
    return tuple(
        _classify_group(group, element_map, pattern_map)
        for group in ARCHETYPE_GROUP_REGISTRY.values()
    )


def _classify_group(group, elements: Mapping[str, ElementResult], patterns: Mapping[str, PatternResult]) -> ContextArchetypeResult:
    reliable = {
        key: item
        for key, item in elements.items()
        if item.score is not None and item.confidence_score >= group.minimum_confidence_score
        and key in (*group.required_elements, *group.optional_elements)
    }
    required_reliable = sum(key in reliable for key in group.required_elements)
    if len(reliable) < group.minimum_reliable_elements or required_reliable < min(len(group.required_elements), group.minimum_reliable_elements):
        return _fallback(group, f"fewer than {group.minimum_reliable_elements} reliable Elements")

    ranked: list[tuple[ArchetypePrototype, float, tuple[dict[str, float], ...]]] = []
    for prototype in group.prototypes:
        active = {key: reliable[key] for key in prototype.expected if key in reliable}
        if not set(prototype.required_elements).issubset(active):
            continue
        weighted_distance = 0.0
        active_weight = 0.0
        contributions: list[dict[str, float]] = []
        for key, expected in prototype.expected.items():
            result = active.get(key)
            if result is None or result.score is None:
                continue
            weight = float(prototype.weights.get(key, 1.0)) * result.confidence_score
            distance = (result.score - expected) ** 2
            weighted_distance += weight * distance
            active_weight += weight
            contributions.append({"key": key, "weight": round(weight, 6), "contribution": round(weight * distance, 6)})
        if not active_weight:
            continue
        fit = clamp(1.0 - math.sqrt(weighted_distance / active_weight) / 1.25)
        fit -= 0.06 * max(0.0, 1.0 - len(contributions) / max(len(prototype.expected), 1))
        ranked.append((prototype, clamp(fit), tuple(contributions)))
    if not ranked:
        return _fallback(group, "no prototype cleared its required Element gate")
    ranked.sort(key=lambda item: (-item[1], item[0].key))
    winner = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None
    winner_prototype, winner_fit, winner_contributions = winner
    runner_fit = runner[1] if runner else 0.0
    margin = winner_fit - runner_fit
    contributing_patterns = tuple(
        key for key in group.optional_patterns
        if patterns.get(key) is not None and patterns[key].status == "qualified"
        and any(element_key in reliable for element_key in patterns[key].element_keys)
    )
    confidence: Confidence = "low" if margin < 0.04 else "high" if winner_fit >= 0.72 and margin >= 0.10 else "moderate"
    if margin < 0.04:
        return ContextArchetypeResult(
            group_key=group.key,
            group_label=group.label,
            key="unclassified",
            label="Still taking shape",
            fit=winner_fit,
            confidence="low",
            runner_up={"key": winner_prototype.key, "fit": winner_fit},
            descriptors=({"key": "mixed_signals", "label": "Signals still mixed", "dimension": group.key},),
            contributing_elements=winner_contributions,
            contributing_patterns=contributing_patterns,
            explanation_evidence=("The leading styles are too close to call cleanly.",),
            classifier_version=ARCHETYPE_REGISTRY_VERSION,
        )
    prototype = winner_prototype
    return ContextArchetypeResult(
        group_key=group.key,
        group_label=group.label,
        key=prototype.key,
        label=prototype.label,
        fit=winner_fit,
        confidence=confidence,
        runner_up={"key": runner[0].key, "fit": runner_fit} if runner else None,
        descriptors=tuple(
            {"key": item.key, "label": _descriptor_label(item.key, item.score), "dimension": item.dimension_key}
            for item in sorted((reliable[key] for key in prototype.expected if key in reliable), key=lambda item: (-abs((item.score or 0.5) - 0.5) * item.confidence_score, item.key))[:3]
        ),
            contributing_elements=winner_contributions,
        contributing_patterns=contributing_patterns,
        explanation_evidence=tuple(
            f"{item['key']} contributed {float(item['contribution']):.3f} distance"
            for item in sorted(winner_contributions, key=lambda value: float(value["contribution"]))[:3]
        ),
        classifier_version=ARCHETYPE_REGISTRY_VERSION,
    )


def _fallback(group, reason: str) -> ContextArchetypeResult:
    return ContextArchetypeResult(
        group_key=group.key,
        group_label=group.label,
        key="unclassified",
        label="Still taking shape",
        fit=0.0,
        confidence="unavailable",
        runner_up=None,
        descriptors=({"key": "bounded_evidence", "label": "Evidence remains bounded", "dimension": group.key},),
        contributing_elements=(),
        contributing_patterns=(),
        explanation_evidence=(reason,),
        classifier_version=ARCHETYPE_REGISTRY_VERSION,
    )


def _descriptor_label(key: str, score: float | None) -> str:
    if score is None:
        return "Signal unavailable"
    labels = {
        "hero_pool_breadth": ("Specialized", "Broad"),
        "hero_pool_stability": ("Changing", "Stable"),
        "hero_exploration_rate": ("Familiar picks", "Exploratory picks"),
        "toolkit_breadth": ("Narrow toolkit", "Diverse toolkit"),
        "signature_dependence": ("Little dependence", "High dependence"),
        "combat_involvement": ("Lower involvement", "Higher involvement"),
        "finisher_orientation": ("Assist-oriented", "Kill-oriented"),
        "death_exposure": ("Lower exposure", "Higher exposure"),
        "session_length_tendency": ("Short bursts", "Long sessions"),
        "late_session_performance": ("Declines later", "Improves later"),
        "post_loss_performance_response": ("Lower after losses", "Higher after losses"),
    }
    pair = labels.get(key, ("Lower", "Higher"))
    return pair[1] if score > 0.5 else pair[0]
