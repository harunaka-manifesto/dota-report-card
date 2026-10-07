from __future__ import annotations

from app.stratz.field_policy import FORBIDDEN_FIELD_TOKENS, forbidden_fields_in


def test_forbidden_fields_are_found_at_any_depth() -> None:
    assert "rank" in FORBIDDEN_FIELD_TOKENS
    assert forbidden_fields_in({"rank_tier": 70, "matchId": 1})
    assert forbidden_fields_in({"nested": {"predictedWinner": True, "safe_field": 1}})
    assert forbidden_fields_in([{"mmrEstimate": 4000}, {"heroId": 1}])
    assert not forbidden_fields_in({"no_forbidden_fields_here": 1})
    assert not forbidden_fields_in({})
