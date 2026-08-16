from __future__ import annotations

from app.content.renderer import validate_copy_catalog
from app.findings.copy import copy_lint_value


def test_finding_copy_catalog_is_complete_and_neutral() -> None:
    catalog = validate_copy_catalog()

    assert catalog["findings"]
    assert catalog["experiments"]
    for key, value in catalog["findings"].items():
        assert isinstance(value, dict), key
        for field in ("headline", "body", "interpretation", "share"):
            assert copy_lint_value(value[field]) == [], f"{key}.{field}"


def test_copy_lint_rejects_causal_or_psychological_claims() -> None:
    assert "causes" in copy_lint_value("This causes the result.")
    assert "you tilt" in copy_lint_value("You tilt after losses.")
