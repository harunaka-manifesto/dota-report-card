"""Finite Pattern qualification over upstream Element results only."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.behavior.comparisons import clamp, confidence_label
from app.behavior.elements.registry import ELEMENT_REGISTRY, zone_for_score
from app.behavior.evidence import BehaviorEvidence
from app.behavior.models import ElementResult, PatternDefinition, PatternResult
from app.behavior.patterns.registry import PATTERN_REGISTRY


@dataclass(frozen=True, slots=True)
class ElementGateFailure:
    key: str
    reason: str


@dataclass(frozen=True, slots=True)
class QualificationClauseEvaluation:
    clause_index: int
    element_keys: tuple[str, ...]
    zones: tuple[str, ...]
    zone_qualified: bool
    qualified: bool
    components: tuple[float, ...]
    min_confidence: float
    mean_confidence: float
    min_coverage: float
    missing: tuple[str, ...] = ()
    coverage_failures: tuple[str, ...] = ()
    confidence_failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QualificationDecision:
    qualified: bool
    direction: str | None
    clause_index: int | None
    qualification_element_keys: tuple[str, ...]
    components: tuple[float, ...]
    selected_clause: QualificationClauseEvaluation | None = None


@dataclass(frozen=True, slots=True)
class QualificationGate:
    values: tuple[ElementResult, ...]
    missing: tuple[str, ...] = ()
    coverage: tuple[str, ...] = ()
    weak: tuple[str, ...] = ()


def _element_gate_failure(
    key: str,
    result: ElementResult | None,
    *,
    minimum_confidence: float,
) -> ElementGateFailure | None:
    definition = ELEMENT_REGISTRY[key]
    if result is None or result.status == "unavailable" or result.score is None:
        return ElementGateFailure(key, "unavailable")
    if result.coverage < definition.minimum_coverage:
        return ElementGateFailure(key, "coverage")
    if result.confidence_score < minimum_confidence:
        return ElementGateFailure(key, "confidence")
    return None


def evaluate_patterns(
    elements: tuple[ElementResult, ...] | list[ElementResult],
) -> tuple[PatternResult, ...]:
    """Evaluate every reviewed Pattern without mining normalized matches again."""

    element_map = {item.key: item for item in elements}
    results: list[PatternResult] = []
    for definition in PATTERN_REGISTRY.values():
        gate = _qualification_gate(definition, element_map)
        if gate.missing:
            results.append(_unavailable(definition.key, gate.missing, "required_element_unavailable"))
        elif gate.coverage:
            results.append(
                _suppressed(
                    definition.key,
                    gate.coverage,
                    "required_element_coverage_below_gate",
                )
            )
        elif gate.weak:
            results.append(
                _suppressed(
                    definition.key,
                    gate.weak,
                    "required_element_confidence_below_gate",
                )
            )
        else:
            results.append(_evaluate(definition.key, element_map))
    return tuple(results)


def _evaluate(key: str, elements: Mapping[str, ElementResult]) -> PatternResult:
    definition = PATTERN_REGISTRY[key]
    decision = _qualification_decision(key, elements)
    values = [elements[item] for item in decision.qualification_element_keys if item in elements]
    zone_qualified = decision.qualified
    components = decision.components
    relationship = clamp(sum(components) / max(len(components), 1))
    confidence = _pattern_confidence(values, stable=zone_qualified)
    coverage = min((item.coverage for item in values), default=0.0)
    quality = clamp(sum(item.quality for item in values) / max(len(values), 1))
    blocking_confounders = tuple(
        dict.fromkeys(
            blocker
            for item in values
            for blocker in item.blocking_confounders
        )
    )
    qualified = zone_qualified and not blocking_confounders
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
        direction=decision.direction if qualified else None,
        strength=strength,
        confidence=confidence_label(confidence),
        confidence_score=confidence,
        element_keys=definition.required_elements,
        qualification_element_keys=decision.qualification_element_keys,
        qualification_clause_index=decision.clause_index,
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
    """Compatibility tuple for older internal callers.

    New evaluation code consumes an explicit qualification decision so OR
    clause authority cannot be lost in a loose tuple.
    """

    decision = _qualification_decision(key, elements)
    return decision.qualified, decision.direction, decision.components


def _score_value(value: ElementResult | float | None) -> float | None:
    if value is None:
        return None
    return value.score if isinstance(value, ElementResult) else float(value)


def _zone_for_value(name: str, value: ElementResult | float | None) -> str:
    return zone_for_score(name, _score_value(value)) or "Unavailable"


def _component_for_zone(name: str, current: str, accepted: tuple[str, ...]) -> float:
    labels = ELEMENT_REGISTRY[name].zone_labels
    accepted_indexes = [labels.index(item) for item in accepted if item in labels]
    if current not in labels or not accepted_indexes:
        return 0.0
    distance = min(abs(labels.index(current) - index) for index in accepted_indexes)
    return clamp(1.0 - distance / max(len(labels) - 1, 1))


def _clause_evaluation(
    definition: PatternDefinition,
    clause_index: int,
    clause: tuple[tuple[str, tuple[str, ...]], ...],
    elements: Mapping[str, ElementResult] | Mapping[str, float],
) -> QualificationClauseEvaluation:
    element_keys = tuple(item for item, _accepted in clause)
    values = tuple(elements.get(item) for item in element_keys)
    missing = tuple(
        item
        for item, value in zip(element_keys, values, strict=True)
        if value is None
        or isinstance(value, ElementResult)
        and (value.status == "unavailable" or value.score is None)
    )
    coverage_failures = tuple(
        item
        for item, value in zip(element_keys, values, strict=True)
        if isinstance(value, ElementResult)
        and value.score is not None
        and value.status != "unavailable"
        and value.coverage < ELEMENT_REGISTRY[item].minimum_coverage
    )
    minimum_confidence = float(definition.minimum_element_confidence)
    confidence_failures = tuple(
        item
        for item, value in zip(element_keys, values, strict=True)
        if isinstance(value, ElementResult)
        and value.score is not None
        and value.status != "unavailable"
        and value.coverage >= ELEMENT_REGISTRY[item].minimum_coverage
        and value.confidence_score < minimum_confidence
    )
    zones = tuple(
        _zone_for_value(item, value)
        for item, value in zip(element_keys, values, strict=True)
    )
    components = tuple(
        _component_for_zone(item, zone, accepted)
        for (item, accepted), zone in zip(clause, zones, strict=True)
    )
    zone_qualified = all(
        zone in accepted
        for (_item, accepted), zone in zip(clause, zones, strict=True)
    )
    confidence_values = [
        value.confidence_score
        for value in values
        if isinstance(value, ElementResult) and value.score is not None
    ]
    coverage_values = [
        value.coverage
        for value in values
        if isinstance(value, ElementResult) and value.score is not None
    ]
    return QualificationClauseEvaluation(
        clause_index=clause_index,
        element_keys=element_keys,
        zones=zones,
        zone_qualified=zone_qualified,
        qualified=not missing and not coverage_failures and not confidence_failures and zone_qualified,
        components=components,
        min_confidence=min(confidence_values, default=0.0),
        mean_confidence=sum(confidence_values) / max(len(confidence_values), 1),
        min_coverage=min(coverage_values, default=0.0),
        missing=missing,
        coverage_failures=coverage_failures,
        confidence_failures=confidence_failures,
    )


def _clause_rank(clause: QualificationClauseEvaluation) -> tuple[float, float, float, float, int]:
    """Rank qualifying clauses using the reviewed deterministic tie-break."""

    return (
        clause.min_confidence,
        clause.mean_confidence,
        clause.min_coverage,
        sum(clause.components),
        -clause.clause_index,
    )


def _qualification_decision(
    key: str,
    elements: Mapping[str, ElementResult] | Mapping[str, float],
) -> QualificationDecision:
    definition = PATTERN_REGISTRY[key]
    clauses = tuple(
        _clause_evaluation(definition, index, clause, elements)
        for index, clause in enumerate(definition.zone_clauses)
    )
    gate_eligible = [
        clause
        for clause in clauses
        if not clause.missing and not clause.coverage_failures and not clause.confidence_failures
    ]
    qualifying = [clause for clause in gate_eligible if clause.qualified]
    selected = max(qualifying or gate_eligible, key=_clause_rank, default=None)
    if selected is None:
        return QualificationDecision(False, None, None, (), ())
    qualified = selected in qualifying
    direction = (
        _direction_for(key, elements, selected.element_keys)
        if qualified
        else None
    )
    return QualificationDecision(
        qualified=qualified,
        direction=direction,
        clause_index=selected.clause_index,
        qualification_element_keys=selected.element_keys,
        components=selected.components,
        selected_clause=selected,
    )


def _direction_for(
    key: str,
    elements: Mapping[str, ElementResult] | Mapping[str, float],
    qualification_element_keys: tuple[str, ...] | None = None,
) -> str:
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
        selected = set(qualification_element_keys or elements)
        familiarity_moved = (
            "post_loss_familiarity_shift" in selected
            and zone("post_loss_familiarity_shift") != "Unchanged"
        )
        tempo_moved = (
            "post_loss_activity_shift" in selected
            and zone("post_loss_activity_shift") != "Same"
        )
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


def _qualification_gate(
    definition: PatternDefinition, elements: Mapping[str, ElementResult]
) -> QualificationGate:
    clauses = tuple(
        _clause_evaluation(definition, index, clause, elements)
        for index, clause in enumerate(definition.zone_clauses)
    )
    gate_eligible = [
        clause
        for clause in clauses
        if not clause.missing and not clause.coverage_failures and not clause.confidence_failures
    ]
    values = tuple(
        elements[key]
        for key in definition.required_elements
        if key in elements
    )
    if any(clause.qualified for clause in clauses):
        return QualificationGate(values=values)

    zone_qualified = [clause for clause in clauses if clause.zone_qualified]
    if zone_qualified:
        coverage_failures = tuple(
            dict.fromkeys(key for clause in zone_qualified for key in clause.coverage_failures)
        )
        if coverage_failures:
            return QualificationGate(values=values, coverage=coverage_failures)
        confidence_failures = tuple(
            dict.fromkeys(key for clause in zone_qualified for key in clause.confidence_failures)
        )
        if confidence_failures:
            return QualificationGate(values=values, weak=confidence_failures)

    if gate_eligible:
        return QualificationGate(values=values)

    coverage_failures = tuple(
        dict.fromkeys(
            key
            for clause in clauses
            if not clause.missing
            for key in clause.coverage_failures
        )
    )
    if coverage_failures:
        return QualificationGate(values=values, coverage=coverage_failures)

    confidence_failures = tuple(
        dict.fromkeys(
            key
            for clause in clauses
            if not clause.missing and not clause.coverage_failures
            for key in clause.confidence_failures
        )
    )
    if confidence_failures:
        return QualificationGate(values=values, weak=confidence_failures)

    missing = tuple(
        dict.fromkeys(key for clause in clauses for key in clause.missing)
    )
    return QualificationGate(values=values, missing=missing)


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
