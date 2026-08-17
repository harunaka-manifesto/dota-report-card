"""Finite Pattern qualification over upstream Element results only."""

from __future__ import annotations

from collections.abc import Mapping

from app.behavior.comparisons import clamp, confidence_label
from app.behavior.evidence import BehaviorEvidence
from app.behavior.models import ElementResult, PatternResult
from app.behavior.patterns.registry import PATTERN_REGISTRY


def evaluate_patterns(
    elements: tuple[ElementResult, ...] | list[ElementResult],
) -> tuple[PatternResult, ...]:
    """Evaluate every reviewed Pattern without mining normalized matches again."""

    element_map = {item.key: item for item in elements}
    results: list[PatternResult] = []
    for definition in PATTERN_REGISTRY.values():
        required = [element_map.get(key) for key in definition.required_elements]
        missing = tuple(
            key
            for key, result in zip(definition.required_elements, required, strict=True)
            if result is None or result.status == "unavailable" or result.score is None
        )
        weak = tuple(
            result.key
            for result in required
            if result is not None
            and result.score is not None
            and result.confidence_score < definition.minimum_element_confidence
        )
        if missing:
            results.append(_unavailable(definition.key, missing, "required_element_unavailable"))
        elif weak:
            results.append(_suppressed(definition.key, weak, "required_element_confidence_below_gate"))
        else:
            results.append(_evaluate(definition.key, element_map))
    return tuple(results)


def _evaluate(key: str, elements: Mapping[str, ElementResult]) -> PatternResult:
    definition = PATTERN_REGISTRY[key]
    values = [elements[element_key] for element_key in definition.required_elements]
    scores = {item.key: float(item.score or 0.5) for item in values}
    qualified, direction, components = _qualification(key, scores)
    relationship = clamp(sum(components) / max(len(components), 1))
    confidence = _pattern_confidence(values, stable=qualified)
    coverage = min((item.coverage for item in values), default=0.0)
    quality = clamp(sum(item.quality for item in values) / max(len(values), 1))
    strength = clamp(relationship * confidence * coverage * quality) if qualified else 0.0
    effect: dict[str, float | int | str | bool | None] = {
        f"{item.key}.score": item.score for item in values
    }
    for item in values:
        effect.update(
            {
                f"{item.key}.{metric}": value
                for metric, value in item.raw_metrics.items()
                if metric in {"delta", "standardized_delta", "method"}
            }
        )
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
        strength=strength,
        confidence=confidence_label(confidence),
        confidence_score=confidence,
        element_keys=definition.required_elements,
        evidence=evidence,
        effect_metrics=effect,
        confounders=tuple(
            dict.fromkeys(confounder for item in values for confounder in item.confounders)
        ),
        suppression_reasons=() if qualified else ("relationship_threshold_not_met",),
        methodology_version=definition.version,
        diagnostic_questions=definition.diagnostic_questions,
        required_deep_elements=definition.required_deep_elements,
        modifier_element_keys=definition.modifier_elements,
        family=definition.family,
        tier=definition.tier,
        relationship_strength=relationship,
        evidence_coverage=coverage,
        qualification_quality=quality,
    )


def _qualification(key: str, score: dict[str, float]) -> tuple[bool, str | None, tuple[float, ...]]:
    def high(name: str) -> bool:
        return score[name] >= 0.62

    def low(name: str) -> bool:
        return score[name] <= 0.42

    def moved(name: str) -> bool:
        return abs(score[name] - 0.5) >= 0.18

    def near(name: str) -> bool:
        return abs(score[name] - 0.5) <= 0.18

    def mild(name: str) -> bool:
        return abs(score[name] - 0.5) <= 0.18

    def movement(name: str) -> float:
        return min(1.0, abs(score[name] - 0.5) / 0.5)

    def high_component(name: str) -> float:
        return min(1.0, max(0.0, (score[name] - 0.5) / 0.5))

    def low_component(name: str) -> float:
        return min(1.0, max(0.0, (0.5 - score[name]) / 0.5))

    def stable_component(name: str) -> float:
        return max(0.0, 1.0 - abs(score[name] - 0.5) / 0.5)

    if key == "same_playbook":
        ok = high("hero_pool_breadth") and low("toolkit_breadth")
        return ok, "hero_names_change_toolkit_holds" if ok else None, (high_component("hero_pool_breadth"), low_component("toolkit_breadth"))
    if key == "comfort_edge":
        ok = high("hero_pool_breadth") and low("off_pool_performance")
        return ok, "wide_pool_results_slip_off_pool" if ok else None, (high_component("hero_pool_breadth"), low_component("off_pool_performance"))
    if key == "partial_transfer":
        ok = high("off_pool_activity_stability") and low("off_pool_performance")
        return ok, "presence_holds_results_slip" if ok else None, (high_component("off_pool_activity_stability"), low_component("off_pool_performance"))
    if key == "stable_style":
        ok = moved("recent_form_shift") and high("hero_pool_stability") and mild("recent_activity_shift")
        return ok, "form_moves_style_holds" if ok else None, (movement("recent_form_shift"), high_component("hero_pool_stability"), stable_component("recent_activity_shift"))
    if key == "versatile_core":
        ok = low("hero_pool_breadth") and high("toolkit_breadth")
        return ok, "focused_pool_varied_toolkit" if ok else None, (low_component("hero_pool_breadth"), high_component("toolkit_breadth"))
    if key == "proven_flexibility":
        ok = high("hero_pool_breadth") and high("off_pool_performance")
        return ok, "wide_pool_results_travel" if ok else None, (high_component("hero_pool_breadth"), high_component("off_pool_performance"))
    if key == "selective_closer":
        ok = not high("combat_involvement") and score["combat_involvement"] <= 0.55 and high("finisher_orientation")
        return ok, "selective_involvement_finishes" if ok else None, (low_component("combat_involvement"), high_component("finisher_orientation"))
    if key == "loss_response":
        ok = moved("post_loss_familiarity_shift") or moved("post_loss_activity_shift")
        if not ok:
            return False, None, (movement("post_loss_familiarity_shift"), movement("post_loss_activity_shift"))
        familiarity = moved("post_loss_familiarity_shift")
        tempo = moved("post_loss_activity_shift")
        direction = "full_reset" if familiarity and tempo else "pick_reset" if familiarity else "pace_reset"
        return True, direction, (movement("post_loss_familiarity_shift"), movement("post_loss_activity_shift"))
    if key == "controlled_presence":
        ok = high("combat_involvement") and low("death_exposure")
        return ok, "active_with_controlled_exposure" if ok else None, (high_component("combat_involvement"), low_component("death_exposure"))
    if key == "heavy_exposure":
        ok = high("combat_involvement") and high("death_exposure")
        return ok, "active_with_heavy_exposure" if ok else None, (high_component("combat_involvement"), high_component("death_exposure"))
    if key == "session_fade":
        ok = high("session_length_tendency") and low("late_session_performance")
        return ok, "late_session_decline" if ok else None, (high_component("session_length_tendency"), low_component("late_session_performance"))
    if key == "session_rise":
        ok = score["session_length_tendency"] >= 0.45 and high("late_session_performance")
        return ok, "late_session_improvement" if ok else None, (high_component("session_length_tendency"), high_component("late_session_performance"))
    if key == "session_hold":
        ok = high("session_length_tendency") and near("late_session_performance")
        return ok, "late_session_result_holds" if ok else None, (high_component("session_length_tendency"), stable_component("late_session_performance"))
    if key == "assist_presence":
        ok = score["combat_involvement"] >= 0.55 and low("finisher_orientation")
        return ok, "involvement_assist_leaning" if ok else None, (high_component("combat_involvement"), low_component("finisher_orientation"))
    raise KeyError(f"No Pattern evaluator for {key}")


def _pattern_confidence(elements: list[ElementResult], *, stable: bool) -> float:
    weakest = min((item.confidence_score for item in elements), default=0.0)
    mean = sum(item.confidence_score for item in elements) / max(len(elements), 1)
    relationship_stability = 1.0 if stable else 0.80
    return clamp(0.60 * weakest + 0.25 * mean + 0.15 * relationship_stability)


def _unavailable(key: str, missing: tuple[str, ...], reason: str) -> PatternResult:
    definition = PATTERN_REGISTRY[key]
    return PatternResult(
        key=key,
        label=definition.label,
        kind=definition.kind,
        status="unavailable",
        direction=None,
        strength=0.0,
        confidence="unavailable",
        confidence_score=0.0,
        element_keys=definition.required_elements,
        modifier_element_keys=definition.modifier_elements,
        suppression_reasons=(reason + ":" + ",".join(missing),),
        methodology_version=definition.version,
        diagnostic_questions=definition.diagnostic_questions,
        required_deep_elements=definition.required_deep_elements,
        family=definition.family,
        tier=definition.tier,
    )


def _suppressed(key: str, weak: tuple[str, ...], reason: str) -> PatternResult:
    definition = PATTERN_REGISTRY[key]
    return PatternResult(
        key=key,
        label=definition.label,
        kind=definition.kind,
        status="suppressed",
        direction=None,
        strength=0.0,
        confidence="low",
        confidence_score=0.0,
        element_keys=definition.required_elements,
        modifier_element_keys=definition.modifier_elements,
        suppression_reasons=(reason + ":" + ",".join(weak),),
        methodology_version=definition.version,
        diagnostic_questions=definition.diagnostic_questions,
        required_deep_elements=definition.required_deep_elements,
        family=definition.family,
        tier=definition.tier,
    )
