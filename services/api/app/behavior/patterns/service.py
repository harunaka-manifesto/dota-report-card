"""Finite Pattern qualification over upstream Element results only."""

from __future__ import annotations

from collections.abc import Mapping

from app.behavior.comparisons import clamp, confidence_label
from app.behavior.evidence import BehaviorEvidence
from app.behavior.models import ElementResult, PatternResult
from app.behavior.patterns.registry import PATTERN_REGISTRY


def evaluate_patterns(elements: tuple[ElementResult, ...] | list[ElementResult]) -> tuple[PatternResult, ...]:
    element_map = {item.key: item for item in elements}
    results: list[PatternResult] = []
    for definition in PATTERN_REGISTRY.values():
        dependencies = [element_map.get(key) for key in definition.required_elements]
        missing = [key for key, result in zip(definition.required_elements, dependencies, strict=True) if result is None or result.status == "unavailable" or result.score is None]
        weak = [result.key for result in dependencies if result is not None and result.score is not None and result.confidence_score < definition.minimum_element_confidence]
        if missing:
            results.append(_unavailable(definition.key, tuple(missing), "required_element_unavailable"))
            continue
        if weak:
            results.append(_suppressed(definition.key, tuple(weak), "required_element_confidence_below_gate"))
            continue
        result = _evaluate(definition.key, element_map)
        results.append(result)
    return tuple(results)


def _evaluate(key: str, elements: Mapping[str, ElementResult]) -> PatternResult:
    definition = PATTERN_REGISTRY[key]
    values = [elements[element_key] for element_key in definition.required_elements]
    score = {item.key: item.score or 0.5 for item in values}
    qualified = False
    direction: str | None = None
    effect: dict[str, float | int | str | bool | None] = {}
    if key == "broad_pool_narrow_toolkit":
        qualified = score["hero_pool_breadth"] >= 0.62 and score["toolkit_breadth"] <= 0.42
        direction = "broad_pool_narrow_toolkit"
    elif key == "broad_pool_narrow_safety_zone":
        qualified = score["hero_pool_breadth"] >= 0.62 and score["off_pool_performance"] <= 0.43
        direction = "broad_pool_with_familiar_performance_edge"
    elif key == "specialist_transferable_style":
        qualified = score["hero_pool_breadth"] <= 0.42 and score["off_pool_activity_stability"] >= 0.62
        direction = "narrow_pool_activity_travels"
    elif key == "role_anchor_hero_explorer":
        qualified = score["role_breadth"] <= 0.42 and score["hero_pool_breadth"] >= 0.62
        direction = "role_anchor_hero_explorer"
    elif key == "hero_anchor_role_flex":
        qualified = score["hero_pool_breadth"] <= 0.42 and score["role_breadth"] >= 0.62
        direction = "hero_anchor_role_flex"
    elif key == "signature_strength_with_tax":
        qualified = score["signature_dependence"] >= 0.62 and score["off_pool_performance"] <= 0.43
        direction = "signature_strength_with_off_pool_tax"
    elif key == "activity_travels_better_than_results":
        qualified = score["off_pool_activity_stability"] >= 0.62 and score["off_pool_performance"] <= 0.43
        direction = "activity_outlasts_results"
    elif key == "high_involvement_controlled_exposure":
        qualified = score["combat_involvement"] >= 0.62 and score["death_exposure"] <= 0.42
        direction = "high_involvement_controlled_exposure"
    elif key == "high_involvement_high_exposure":
        qualified = score["combat_involvement"] >= 0.62 and score["death_exposure"] >= 0.62
        direction = "high_involvement_high_exposure"
    elif key == "selective_finisher":
        qualified = score["combat_involvement"] <= 0.55 and score["finisher_orientation"] >= 0.65 and score["death_exposure"] <= 0.45
        direction = "selective_finisher"
    elif key == "losses_change_picks_more_than_pace":
        qualified = score["post_loss_familiarity_shift"] >= 0.62 and abs(score["post_loss_activity_shift"] - 0.5) <= 0.14
        direction = "picks_move_more_than_activity"
    elif key == "losses_change_pace_more_than_picks":
        qualified = abs(score["post_loss_familiarity_shift"] - 0.5) <= 0.14 and abs(score["post_loss_activity_shift"] - 0.5) >= 0.22
        direction = "activity_moves_more_than_picks"
    elif key == "long_session_tax":
        qualified = score["session_length_tendency"] >= 0.62 and score["late_session_performance"] <= 0.43
        direction = "late_session_decline"
    elif key == "marathon_stability":
        qualified = score["session_length_tendency"] >= 0.62 and score["late_session_performance"] >= 0.55
        direction = "late_session_stability"
    elif key == "form_identity_divergence":
        qualified = abs(score["recent_form_shift"] - 0.5) >= 0.18 and score["hero_pool_stability"] >= 0.58 and abs(score["recent_activity_shift"] - 0.5) <= 0.18
        direction = "form_moves_style_holds"
    else:
        raise KeyError(f"No Pattern evaluator for {key}")

    confidence = _pattern_confidence(values, stable=qualified)
    strength = _pattern_strength(key, score) if qualified else 0.0
    for item in values:
        effect.update({f"{item.key}.score": item.score, **{f"{item.key}.{metric}": value for metric, value in item.raw_metrics.items() if metric in {"delta", "standardized_delta", "switch_rate"}}})
    evidence = tuple(
        BehaviorEvidence(
            key=f"element.{item.key}",
            value=item.score,
            unit="score",
            denominator=item.sample_size,
            coverage=item.coverage,
            confidence_score=item.confidence_score,
            comparison=item.label,
            source_match_ids=item.source_match_ids,
        )
        for item in values
    )
    return PatternResult(
        key=key,
        label=definition.label,
        kind=definition.kind,
        status="qualified" if qualified else "suppressed",
        direction=direction if qualified else None,
        strength=clamp(strength),
        confidence=confidence_label(confidence),
        confidence_score=confidence,
        element_keys=definition.required_elements,
        evidence=evidence,
        effect_metrics=effect,
        confounders=tuple(dict.fromkeys(confounder for item in values for confounder in item.confounders)),
        suppression_reasons=() if qualified else ("effect_threshold_not_met",),
        methodology_version=definition.version,
        diagnostic_questions=definition.diagnostic_questions,
        required_deep_elements=definition.required_deep_elements,
    )


def _pattern_confidence(elements: list[ElementResult], *, stable: bool) -> float:
    weakest = min((item.confidence_score for item in elements), default=0.0)
    mean = sum(item.confidence_score for item in elements) / max(len(elements), 1)
    relationship_stability = 1.0 if stable else 0.80
    return clamp(0.60 * weakest + 0.25 * mean + 0.15 * relationship_stability)


def _pattern_strength(key: str, score: dict[str, float]) -> float:
    pairs: tuple[float, ...]
    if key == "broad_pool_narrow_toolkit":
        pairs = (score["hero_pool_breadth"] - 0.5, 0.5 - score["toolkit_breadth"])
    elif key == "broad_pool_narrow_safety_zone":
        pairs = (score["hero_pool_breadth"] - 0.5, 0.5 - score["off_pool_performance"])
    elif key == "specialist_transferable_style":
        pairs = (0.5 - score["hero_pool_breadth"], score["off_pool_activity_stability"] - 0.5)
    elif key == "role_anchor_hero_explorer":
        pairs = (0.5 - score["role_breadth"], score["hero_pool_breadth"] - 0.5)
    elif key == "hero_anchor_role_flex":
        pairs = (0.5 - score["hero_pool_breadth"], score["role_breadth"] - 0.5)
    elif key == "signature_strength_with_tax":
        pairs = (score["signature_dependence"] - 0.5, 0.5 - score["off_pool_performance"])
    elif key == "activity_travels_better_than_results":
        pairs = (score["off_pool_activity_stability"] - 0.5, 0.5 - score["off_pool_performance"])
    elif key == "high_involvement_controlled_exposure":
        pairs = (score["combat_involvement"] - 0.5, 0.5 - score["death_exposure"])
    elif key == "high_involvement_high_exposure":
        pairs = (score["combat_involvement"] - 0.5, score["death_exposure"] - 0.5)
    elif key == "selective_finisher":
        pairs = (0.5 - score["combat_involvement"], score["finisher_orientation"] - 0.5, 0.5 - score["death_exposure"])
    elif key == "losses_change_picks_more_than_pace":
        pairs = (score["post_loss_familiarity_shift"] - 0.5, 0.14 - abs(score["post_loss_activity_shift"] - 0.5))
    elif key == "losses_change_pace_more_than_picks":
        pairs = (0.14 - abs(score["post_loss_familiarity_shift"] - 0.5), abs(score["post_loss_activity_shift"] - 0.5))
    elif key == "long_session_tax":
        pairs = (score["session_length_tendency"] - 0.5, 0.5 - score["late_session_performance"])
    elif key == "marathon_stability":
        pairs = (score["session_length_tendency"] - 0.5, score["late_session_performance"] - 0.5)
    elif key == "form_identity_divergence":
        pairs = (abs(score["recent_form_shift"] - 0.5), score["hero_pool_stability"] - 0.5, 0.18 - abs(score["recent_activity_shift"] - 0.5))
    else:
        return 0.0
    return clamp(sum(max(0.0, value) for value in pairs) / max(0.5 * len(pairs), 1.0))


def _unavailable(key: str, missing: tuple[str, ...], reason: str) -> PatternResult:
    definition = PATTERN_REGISTRY[key]
    return PatternResult(key, definition.label, definition.kind, "unavailable", None, 0.0, "unavailable", 0.0, definition.required_elements, suppression_reasons=(reason + ":" + ",".join(missing),), methodology_version=definition.version, diagnostic_questions=definition.diagnostic_questions, required_deep_elements=definition.required_deep_elements)


def _suppressed(key: str, weak: tuple[str, ...], reason: str) -> PatternResult:
    definition = PATTERN_REGISTRY[key]
    return PatternResult(key, definition.label, definition.kind, "suppressed", None, 0.0, "low", 0.0, definition.required_elements, suppression_reasons=(reason + ":" + ",".join(weak),), methodology_version=definition.version, diagnostic_questions=definition.diagnostic_questions, required_deep_elements=definition.required_deep_elements)
