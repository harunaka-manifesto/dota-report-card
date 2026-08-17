from app.behavior.catalog import validate_behavior_catalog
from app.behavior.elements.registry import ELEMENT_REGISTRY, EXPECTED_ELEMENT_KEYS
from app.behavior.patterns.registry import EXPECTED_PATTERN_KEYS, PATTERN_REGISTRY


def test_v4_catalog_contains_exactly_17_elements_and_14_patterns() -> None:
    validate_behavior_catalog()
    assert set(ELEMENT_REGISTRY) == set(EXPECTED_ELEMENT_KEYS)
    assert set(PATTERN_REGISTRY) == set(EXPECTED_PATTERN_KEYS)
    assert len(ELEMENT_REGISTRY) == 17
    assert len(PATTERN_REGISTRY) == 14


def test_patterns_keep_required_and_modifier_elements_separate() -> None:
    for pattern in PATTERN_REGISTRY.values():
        assert len(pattern.required_elements) >= 2
        assert not set(pattern.required_elements) & set(pattern.modifier_elements)
        assert all(key in ELEMENT_REGISTRY for key in (*pattern.required_elements, *pattern.modifier_elements))


def test_retired_element_keys_are_not_public_registry_entries() -> None:
    retired = {
        "signature_dependence",
        "role_switch_rate",
        "off_role_performance",
        "long_game_performance_shift",
        "post_loss_performance_response",
        "post_loss_death_shift",
    }
    assert not retired & set(ELEMENT_REGISTRY)
