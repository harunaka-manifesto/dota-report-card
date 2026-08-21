"""Finite Pattern qualification over upstream Element results only."""

from __future__ import annotations

from collections.abc import Mapping

from app.behavior.comparisons import clamp, confidence_label
from app.behavior.elements.registry import ELEMENT_REGISTRY, zone_for_score
from app.behavior.evidence import BehaviorEvidence
from app.behavior.models import ElementResult, PatternDefinition, PatternResult
from app.behavior.patterns.registry import PATTERN_REGISTRY


def evaluate_patterns(
    elements: tuple[ElementResult, ...] | list[ElementResult],
) -> tuple[PatternResult, ...]:
    """Evaluate every reviewed Pattern without mining normalized matches again."""

    element_map = {item.key: item for item in elements}
    results: list[PatternResult] = []
    for definition in PATTERN_REGISTRY.values():
        _gate_values, missing, weak = _qualification_gate(definition, element_map)
        if missing:
            results.append(_unavailable(definition.key, missing, "required_element_unavailable"))
        elif weak:
            results.append(_suppressed(definition.key, weak, "required_element_confidence_below_gate"))
        else:
            results.append(_evaluate(definition.key, element_map))
    return tuple(results)


def _evaluate(key: str, elements: Mapping[str, ElementResult]) -> PatternResult:
    definition = PATTERN_REGISTRY[key]
    values = list(_available_values(definition, elements))
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
        story_eligibility="blocked" if blocking_confounders else "eligible",
        story_blockers=blocking_confounders,
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

    def zone(name: str) -> str:
        item = elements.get(name)
        if item is None:
            return "Unavailable"
        if isinstance(item, ElementResult):
            return zone_for_score(name, item.score) or "Unavailable"
        return zone_for_score(name, float(item)) or "Unavailable"

    def component(name: str, accepted: tuple[str, ...]) -> float:
        labels = ELEMENT_REGISTRY[name].zone_labels
        if not labels:
            return 0.0
        current = zone(name)
        if current not in labels:
            return 0.0
        distance = min(abs(labels.index(current) - labels.index(item)) for item in accepted if item in labels)
        return clamp(1.0 - distance / max(len(labels) - 1, 1))

    definition = PATTERN_REGISTRY[key]
    clause_scores: list[tuple[bool, tuple[float, ...]]] = []
    for clause in definition.zone_clauses:
        components = tuple(component(element_key, accepted_zones) for element_key, accepted_zones in clause)
        clause_scores.append(
            (
                all(zone(element_key) in accepted_zones for element_key, accepted_zones in clause),
                components,
            )
        )
    qualified, components = max(
        clause_scores,
        key=lambda value: (value[0], sum(value[1])),
        default=(False, ()),
    )
    direction = _direction_for(key, elements) if qualified else None
    return qualified, direction, components


def _direction_for(key: str, elements: Mapping[str, ElementResult] | Mapping[str, float]) -> str:
    def zone(name: str) -> str:
        item = elements.get(name)
        if item is None:
            return "Unavailable"
        score = item.score if isinstance(item, ElementResult) else float(item)
        return zone_for_score(name, score) or "Unavailable"

    if key == "same_playbook":
        return "hero_names_change_toolkit_holds"
    if key == "comfort_edge":
        return "wide_pool_results_slip_off_pool"
    if key == "partial_transfer":
        return "presence_holds_results_slip"
    if key == "versatile_core":
        return "focused_pool_varied_toolkit"
    if key == "proven_flexibility":
        return "wide_pool_results_travel"
    if key in {"bounceback", "performance_slide"}:
        familiarity_moved = "post_loss_familiarity_shift" in elements and zone("post_loss_familiarity_shift") != "Unchanged"
        tempo_moved = "post_loss_activity_shift" in elements and zone("post_loss_activity_shift") != "Same"
        movement = "familiarity_and_tempo" if familiarity_moved and tempo_moved else "familiarity" if familiarity_moved else "tempo"
        return f"{'positive' if key == 'bounceback' else 'negative'}_recovery_with_{movement}"
    if key == "controlled_presence":
        return "active_with_controlled_exposure"
    if key == "presence_tax":
        return "active_with_presence_tax"
    if key == "session_fade":
        return "late_session_decline"
    if key == "session_rise":
        return "late_session_improvement"
    raise KeyError(f"No Pattern direction for {key}")


def _pattern_confidence(elements: list[ElementResult], *, stable: bool) -> float:
    weakest = min((item.confidence_score for item in elements), default=0.0)
    mean = sum(item.confidence_score for item in elements) / max(len(elements), 1)
    relationship_stability = 1.0 if stable else 0.80
    return clamp(0.60 * weakest + 0.25 * mean + 0.15 * relationship_stability)


def _available_values(
    definition: PatternDefinition, elements: Mapping[str, ElementResult]
) -> tuple[ElementResult, ...]:
    required = definition.required_elements
    return tuple(
        result
        for key in required
        if (result := elements.get(key)) is not None
        and result.status != "unavailable"
        and result.score is not None
    )


def _qualification_gate(
    definition: PatternDefinition, elements: Mapping[str, ElementResult]
) -> tuple[tuple[ElementResult, ...], tuple[str, ...], tuple[str, ...]]:
    required = tuple(definition.required_elements)
    minimum_confidence = float(definition.minimum_element_confidence)
    key = definition.key
    if key not in {"bounceback", "performance_slide"}:
        values = tuple(elements.get(item) for item in required)
        missing = tuple(
            item
            for item, result in zip(required, values, strict=True)
            if result is None or result.status == "unavailable" or result.score is None
        )
        weak = tuple(
            result.key
            for result in values
            if result is not None and result.score is not None and result.confidence_score < minimum_confidence
        )
        return tuple(result for result in values if result is not None), missing, weak

    clauses = tuple(definition.zone_clauses)
    viable = [
        tuple(elements[item] for item, _zones in clause)
        for clause in clauses
        if all(
            (result := elements.get(item)) is not None
            and result.status != "unavailable"
            and result.score is not None
            for item, _zones in clause
        )
    ]
    if not viable:
        recovery = "post_loss_performance_response"
        support = "post_loss_familiarity_shift_or_post_loss_activity_shift"
        return (), (recovery, support), ()
    strong = [
        group for group in viable
        if all(result.confidence_score >= minimum_confidence for result in group)
    ]
    weak = () if strong else tuple(
        result.key
        for result in viable[0]
        if result.confidence_score < minimum_confidence
    )
    return _available_values(definition, elements), (), weak


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
