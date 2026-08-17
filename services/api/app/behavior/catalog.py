"""Validation and version aggregation for the behavioral registries."""

from __future__ import annotations

from app.behavior.dimensions import DIMENSIONS_BY_KEY
from app.behavior.elements.registry import ELEMENT_REGISTRY
from app.behavior.patterns.registry import PATTERN_REGISTRY

CATALOG_VERSION = "behavior-catalog-1.0.0"


def validate_behavior_catalog() -> None:
    """Fail fast on broken registry references or unsupported Free capabilities."""

    for key, definition in ELEMENT_REGISTRY.items():
        if key != definition.key:
            raise ValueError(f"Element registry key mismatch: {key}")
        if definition.dimension_key not in DIMENSIONS_BY_KEY:
            raise ValueError(f"Element {key} references unknown dimension {definition.dimension_key}")
        if not definition.scorer_key:
            raise ValueError(f"Element {key} is missing a scorer key")
        if definition.product_tier == "free" and definition.minimum_evidence_tier != "summary_history":
            raise ValueError(f"Free Element {key} requires non-summary evidence")
    for key, pattern_definition in PATTERN_REGISTRY.items():
        if key != pattern_definition.key:
            raise ValueError(f"Pattern registry key mismatch: {key}")
        if len(set(pattern_definition.required_elements)) < 2:
            raise ValueError(f"Pattern {key} must depend on at least two Elements")
        for element_key in (*pattern_definition.required_elements, *pattern_definition.modifier_elements):
            if element_key not in ELEMENT_REGISTRY:
                raise ValueError(f"Pattern {key} references unknown Element {element_key}")


validate_behavior_catalog()
