import pytest
from app.content.renderer import resolve_dimension_copy, resolve_page_copy, validate_copy_catalog


def test_free_copy_catalog_covers_dimensions_pages_and_neutral_resolution() -> None:
    catalog = validate_copy_catalog()
    assert catalog["copy_version"] == "free-dna-copy-1.0.1"
    for key in ("breadth", "role", "adaptability", "activity", "orientation", "resilience", "endurance", "rhythm"):
        copy = resolve_dimension_copy(key, "limited")
        assert copy["headline_key"].startswith("free_dna.dimension.")
        assert copy["receipt_params"] == {"status": "limited"}
        assert copy["body"]
    assert resolve_page_copy("final_card")["title"] == "Your fingerprint"


def test_copy_resolution_rejects_missing_or_extra_parameters() -> None:
    with pytest.raises(ValueError, match="Missing copy parameters"):
        resolve_page_copy("player_found")
    with pytest.raises(ValueError, match="Unexpected copy parameters"):
        resolve_page_copy("final_card", display_name="not-needed")
