from __future__ import annotations

from app.behavior.archetypes.registry import ARCHETYPE_GROUP_REGISTRY
from app.behavior.catalog import validate_behavior_catalog
from app.behavior.dimensions import DIMENSIONS_BY_KEY
from app.behavior.elements.registry import ELEMENT_REGISTRY
from app.behavior.patterns.registry import PATTERN_REGISTRY


def test_free_behavior_catalog_has_the_planned_finite_surface() -> None:
    validate_behavior_catalog()

    assert len(DIMENSIONS_BY_KEY) == 10
    assert len(ELEMENT_REGISTRY) == 23
    assert len(PATTERN_REGISTRY) == 15
    assert set(ARCHETYPE_GROUP_REGISTRY) == {
        "hero_identity",
        "combat_expression",
        "session_style",
    }
    assert all(item.product_tier == "free" for item in ELEMENT_REGISTRY.values())
    assert all(len(item.required_elements) >= 2 for item in PATTERN_REGISTRY.values())


def test_every_archetype_prototype_references_registered_elements_and_patterns() -> None:
    for group in ARCHETYPE_GROUP_REGISTRY.values():
        for prototype in group.prototypes:
            assert set(prototype.required_elements) <= set(ELEMENT_REGISTRY)
            assert set(prototype.optional_patterns) <= set(PATTERN_REGISTRY)
