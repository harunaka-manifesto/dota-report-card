from app.behavior.elements.registry import EXPECTED_ELEMENT_KEYS
from app.behavior.patterns.registry import EXPECTED_PATTERN_KEYS
from app.content.renderer import (
    resolve_element_copy,
    resolve_page_copy,
    resolve_pattern_copy,
    resolve_portfolio_copy,
    validate_copy_catalog,
)


def test_copy_catalog_covers_every_active_model_entry() -> None:
    catalog = validate_copy_catalog()
    assert set(catalog["elements"]) == set(EXPECTED_ELEMENT_KEYS)
    assert set(catalog["patterns"]) == set(EXPECTED_PATTERN_KEYS)
    assert resolve_element_copy("hero_pool_breadth")["title"] == "Breadth"
    assert resolve_pattern_copy("same_playbook")["title"] == "Same Playbook"


def test_copy_resolvers_require_exact_parameters() -> None:
    assert resolve_page_copy("final_card")["title"] == "The part worth sharing"
    assert resolve_portfolio_copy("common_thread.question")
    try:
        resolve_portfolio_copy("common_thread.answer")
    except ValueError as error:
        assert "trait" in str(error)
    else:
        raise AssertionError("portfolio answer should require its placeholder")
