"""End-to-end Elements → Patterns orchestration."""

from __future__ import annotations

from collections.abc import Callable

from app.behavior.dimensions import DIMENSION_DEFINITIONS
from app.behavior.elements.registry import ELEMENT_REGISTRY_VERSION
from app.behavior.elements.service import SummaryBehaviorContext, score_all_elements
from app.behavior.models import (
    BehaviorAnalysisResult,
    BehaviorQualitySummary,
    BehaviorVersionMap,
    Confidence,
    DimensionSummary,
    ElementResult,
    PatternResult,
)
from app.behavior.patterns.registry import PATTERN_REGISTRY_VERSION
from app.behavior.patterns.service import evaluate_patterns

BEHAVIOR_MODEL_VERSION = "behavior-model-4.0.0"


def analyze_behavior(
    context: SummaryBehaviorContext,
    *,
    on_stage: Callable[[str, str], None] | None = None,
) -> BehaviorAnalysisResult:
    if on_stage is not None:
        on_stage("behavior_elements", "Measuring the 17 Elements behind the report.")
    elements = score_all_elements(context)
    if on_stage is not None:
        on_stage("behavior_patterns", "Checking which of the 14 reviewed Patterns survive the evidence gates.")
    patterns = evaluate_patterns(elements)
    dimensions = _summarize_dimensions(elements, patterns)
    quality = _quality(elements, patterns, context.history_tier)
    versions = BehaviorVersionMap(
        behavior_model=BEHAVIOR_MODEL_VERSION,
        dimension_registry="dimensions-1.0.0",
        element_registry=ELEMENT_REGISTRY_VERSION,
        pattern_registry=PATTERN_REGISTRY_VERSION,
    )
    return BehaviorAnalysisResult(elements, patterns, dimensions, quality, versions)


def _summarize_dimensions(
    elements: tuple[ElementResult, ...],
    patterns: tuple[PatternResult, ...],
) -> tuple[DimensionSummary, ...]:
    element_map: dict[str, list[ElementResult]] = {
        key: [] for key in {item.dimension_key for item in elements}
    }
    for item in elements:
        element_map.setdefault(item.dimension_key, []).append(item)
    pattern_map: dict[str, list[str]] = {key: [] for key in element_map}
    for pattern in patterns:
        if pattern.status != "qualified":
            continue
        for dimension in _pattern_dimensions(pattern.key):
            pattern_map.setdefault(dimension, []).append(pattern.key)
    summaries: list[DimensionSummary] = []
    for definition in DIMENSION_DEFINITIONS:
        group = element_map.get(definition.key, [])
        available = sum(item.status == "available" for item in group)
        limited = sum(item.status == "limited" for item in group)
        confidence: Confidence
        if not group or available == 0 and limited == 0:
            confidence = "unavailable"
        elif available == len(group) and min(item.confidence_score for item in group) >= 0.75:
            confidence = "high"
        elif available + limited > 0:
            confidence = "moderate" if available else "low"
        else:
            confidence = "unavailable"
        summaries.append(
            DimensionSummary(
                key=definition.key,
                label=definition.label,
                element_keys=tuple(item.key for item in group),
                qualified_pattern_keys=tuple(pattern_map.get(definition.key, [])),
                available_elements=available,
                total_free_elements=len(group),
                confidence=confidence,
            )
        )
    return tuple(summaries)


def _pattern_dimensions(key: str) -> tuple[str, ...]:
    from app.behavior.patterns.registry import PATTERN_REGISTRY

    definition = PATTERN_REGISTRY.get(key)
    return definition.dimension_keys if definition else ()


def _quality(elements, patterns, history_tier: str) -> BehaviorQualitySummary:
    available = sum(item.status == "available" for item in elements)
    limited = sum(item.status == "limited" for item in elements)
    unavailable = sum(item.status == "unavailable" for item in elements)
    qualified = sum(item.status == "qualified" for item in patterns)
    confidence_values = [item.confidence_score for item in elements if item.score is not None]
    if not confidence_values:
        overall: Confidence = "unavailable"
    else:
        mean = sum(confidence_values) / len(confidence_values)
        overall = "high" if mean >= 0.75 and history_tier != "limited" else "moderate" if mean >= 0.50 else "low"
    warnings: list[str] = []
    if history_tier == "limited":
        warnings.append("This is a limited-history report; more matches will make the pattern steadier.")
    if unavailable:
        warnings.append(f"{unavailable} Elements stayed unavailable because their required fields or sample gates were not met.")
    return BehaviorQualitySummary(overall, available, limited, unavailable, qualified, tuple(warnings))
