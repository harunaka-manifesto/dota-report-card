"""Finite Pattern qualification over upstream Element results only."""

from __future__ import annotations

from collections.abc import Mapping

from app.behavior.comparisons import clamp, confidence_label
from app.behavior.elements.registry import ELEMENT_REGISTRY, zone_for_score
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
    qualified, direction, components = _qualification(key, {item.key: item for item in values})
    zone_qualified = qualified
    relationship = clamp(sum(components) / max(len(components), 1))
    confidence = _pattern_confidence(values, stable=qualified)
    coverage = min((item.coverage for item in values), default=0.0)
    quality = clamp(sum(item.quality for item in values) / max(len(values), 1))
    blocking_confounders = tuple(
        dict.fromkeys(
            blocker
            for item in values
            for blocker in item.blocking_confounders
        )
    )
    qualified = qualified and not blocking_confounders
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
        blocking_confounders=blocking_confounders,
        suppression_reasons=(
            ()
            if qualified
            else (
                *(f"blocking_confounder:{item}" for item in blocking_confounders),
                *(("relationship_zone_not_met",) if not zone_qualified else ()),
            )
        ),
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


def _qualification(
    key: str,
    elements: Mapping[str, ElementResult] | Mapping[str, float],
) -> tuple[bool, str | None, tuple[float, ...]]:
    """Apply the reviewed public zone contract for one Pattern.

    Scores remain available for relationship magnitude, but qualification is
    deliberately expressed in the same named zones that the report shows.
    This prevents a local numeric cutoff from drifting away from the public
    Element methodology.
    """

    def value(name: str) -> float:
        item = elements[name]
        return float(item.score if isinstance(item, ElementResult) and item.score is not None else item if not isinstance(item, ElementResult) else 0.5)

    def zone(name: str) -> str:
        item = elements[name]
        if isinstance(item, ElementResult):
            return item.zone or zone_for_score(name, item.score) or "Unavailable"
        return zone_for_score(name, float(item)) or "Unavailable"

    def in_zones(name: str, accepted: set[str]) -> bool:
        return zone(name) in accepted

    def component(name: str, accepted: set[str]) -> float:
        labels = ELEMENT_REGISTRY[name].zone_labels
        if not labels:
            return 0.0
        current = zone(name)
        if current not in labels:
            return 0.0
        distance = min(abs(labels.index(current) - labels.index(item)) for item in accepted if item in labels)
        return clamp(1.0 - distance / max(len(labels) - 1, 1))

    def moved(name: str, neutral: set[str]) -> bool:
        return zone(name) not in neutral

    if key == "same_playbook":
        accepted_breadth, accepted_toolkit = {"Varied", "Wide"}, {"Compact", "Focused"}
        ok = in_zones("hero_pool_breadth", accepted_breadth) and in_zones("toolkit_breadth", accepted_toolkit)
        return ok, "hero_names_change_toolkit_holds" if ok else None, (component("hero_pool_breadth", accepted_breadth), component("toolkit_breadth", accepted_toolkit))
    if key == "comfort_edge":
        accepted_breadth, accepted_transfer = {"Varied", "Wide"}, {"Slips", "Falls off"}
        ok = in_zones("hero_pool_breadth", accepted_breadth) and in_zones("off_pool_performance", accepted_transfer)
        return ok, "wide_pool_results_slip_off_pool" if ok else None, (component("hero_pool_breadth", accepted_breadth), component("off_pool_performance", accepted_transfer))
    if key == "partial_transfer":
        accepted_presence, accepted_transfer = {"Holds", "Unchanged"}, {"Slips", "Falls off"}
        ok = in_zones("off_pool_activity_stability", accepted_presence) and in_zones("off_pool_performance", accepted_transfer)
        return ok, "presence_holds_results_slip" if ok else None, (component("off_pool_activity_stability", accepted_presence), component("off_pool_performance", accepted_transfer))
    if key == "stable_style":
        form_zones, stability_zones, pace_zones = {"Rising", "Surging", "Sliding", "Cooling"}, {"Settled", "Steady"}, {"Calmer", "Same", "Busier"}
        ok = in_zones("recent_form_shift", form_zones) and in_zones("hero_pool_stability", stability_zones) and in_zones("recent_activity_shift", pace_zones)
        direction = "form_rises_style_holds" if zone("recent_form_shift") in {"Rising", "Surging"} else "form_slides_style_holds"
        return ok, direction if ok else None, (component("recent_form_shift", form_zones), component("hero_pool_stability", stability_zones), component("recent_activity_shift", pace_zones))
    if key == "versatile_core":
        accepted_breadth, accepted_toolkit = {"Focused", "Selective"}, {"Versatile", "Diverse"}
        ok = in_zones("hero_pool_breadth", accepted_breadth) and in_zones("toolkit_breadth", accepted_toolkit)
        return ok, "focused_pool_varied_toolkit" if ok else None, (component("hero_pool_breadth", accepted_breadth), component("toolkit_breadth", accepted_toolkit))
    if key == "proven_flexibility":
        accepted_breadth, accepted_transfer = {"Varied", "Wide"}, {"Travels", "Carries over"}
        ok = in_zones("hero_pool_breadth", accepted_breadth) and in_zones("off_pool_performance", accepted_transfer)
        return ok, "wide_pool_results_travel" if ok else None, (component("hero_pool_breadth", accepted_breadth), component("off_pool_performance", accepted_transfer))
    if key == "selective_closer":
        accepted_involvement, accepted_finishing = {"Quiet", "Selective", "Present"}, {"Closer", "Cleanup"}
        ok = in_zones("combat_involvement", accepted_involvement) and in_zones("finisher_orientation", accepted_finishing)
        return ok, "selective_involvement_finishes" if ok else None, (component("combat_involvement", accepted_involvement), component("finisher_orientation", accepted_finishing))
    if key == "loss_response":
        neutral_familiarity, neutral_tempo = {"Unchanged"}, {"Same"}
        familiarity = moved("post_loss_familiarity_shift", neutral_familiarity)
        tempo = moved("post_loss_activity_shift", neutral_tempo)
        direction = "full_reset" if familiarity and tempo else "pick_reset" if familiarity else "pace_reset"
        return (familiarity or tempo), direction if familiarity or tempo else None, (
            component("post_loss_familiarity_shift", neutral_familiarity),
            component("post_loss_activity_shift", neutral_tempo),
        )
    if key == "controlled_presence":
        accepted_involvement, accepted_deaths = {"Active", "Everywhere"}, {"Elusive", "Safe"}
        ok = in_zones("combat_involvement", accepted_involvement) and in_zones("death_exposure", accepted_deaths)
        return ok, "active_with_controlled_exposure" if ok else None, (component("combat_involvement", accepted_involvement), component("death_exposure", accepted_deaths))
    if key == "heavy_exposure":
        accepted_involvement, accepted_deaths = {"Active", "Everywhere"}, {"Exposed", "Frequent"}
        ok = in_zones("combat_involvement", accepted_involvement) and in_zones("death_exposure", accepted_deaths)
        return ok, "active_with_heavy_exposure" if ok else None, (component("combat_involvement", accepted_involvement), component("death_exposure", accepted_deaths))
    if key == "session_fade":
        accepted_duration, accepted_drift = {"Long", "Marathon"}, {"Drops", "Fades"}
        ok = in_zones("session_length_tendency", accepted_duration) and in_zones("late_session_performance", accepted_drift)
        return ok, "late_session_decline" if ok else None, (component("session_length_tendency", accepted_duration), component("late_session_performance", accepted_drift))
    if key == "session_rise":
        accepted_duration, accepted_drift = {"Medium", "Long", "Marathon"}, {"Warms up", "Finishes strong"}
        ok = in_zones("session_length_tendency", accepted_duration) and in_zones("late_session_performance", accepted_drift)
        return ok, "late_session_improvement" if ok else None, (component("session_length_tendency", accepted_duration), component("late_session_performance", accepted_drift))
    if key == "session_hold":
        accepted_duration, accepted_drift = {"Long", "Marathon"}, {"Holds"}
        ok = in_zones("session_length_tendency", accepted_duration) and in_zones("late_session_performance", accepted_drift)
        return ok, "late_session_result_holds" if ok else None, (component("session_length_tendency", accepted_duration), component("late_session_performance", accepted_drift))
    if key == "assist_presence":
        accepted_involvement, accepted_finishing = {"Present", "Active", "Everywhere"}, {"Setup", "Support"}
        ok = in_zones("combat_involvement", accepted_involvement) and in_zones("finisher_orientation", accepted_finishing)
        return ok, "involvement_assist_leaning" if ok else None, (component("combat_involvement", accepted_involvement), component("finisher_orientation", accepted_finishing))
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
