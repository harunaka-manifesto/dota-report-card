"""Rank, MMR and the other forbidden surfaces stay out of the analysis.

Owner decision 5.1 says rank is display-only. Until this module existed the
rule was a docstring, and a docstring does not fail a build. These tests are
the enforcement, so they are written to fail loudly rather than to pass
easily.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from scripts.v7_research.corpus import FORBIDDEN_FIELD_TOKENS
from scripts.v7_research.rank_fence import (
    ANALYTICAL_MODULES,
    NON_ANALYTICAL_MODULES,
    RankFenceViolation,
    analytical_source_violations,
    assert_row_is_analysis_safe,
    reset_shape_cache,
    shape_signature,
    unlisted_research_modules,
)
from services.api.app.player_analysis_v7 import report_contract

# --------------------------------------------------------------------------
# static scan
# --------------------------------------------------------------------------


def test_no_analytical_module_references_a_forbidden_surface() -> None:
    assert analytical_source_violations() == []


def test_every_research_module_is_classified() -> None:
    """The scan is only as good as its list of what to scan."""

    assert unlisted_research_modules() == []


def test_the_two_module_lists_do_not_overlap() -> None:
    assert not set(ANALYTICAL_MODULES) & set(NON_ANALYTICAL_MODULES)


def test_the_scan_catches_a_planted_reference(tmp_path) -> None:
    """A guard nobody has seen fail is a guard nobody knows works."""

    module = tmp_path / "scripts" / "v7_research"
    module.mkdir(parents=True)
    (module / "leaky.py").write_text(
        "def cheat(row):\n    return row['rank_tier']\n", encoding="utf-8"
    )
    violations = analytical_source_violations(("scripts/v7_research/leaky.py",), root=tmp_path)
    assert len(violations) == 1
    assert "rank" in violations[0]


def test_the_scan_ignores_a_docstring_that_explains_the_rule(tmp_path) -> None:
    module = tmp_path / "scripts" / "v7_research"
    module.mkdir(parents=True)
    (module / "clean.py").write_text(
        '"""We never read rank or mmr here."""\n\n\ndef fine(row):\n    return row["kills"]\n',
        encoding="utf-8",
    )
    assert analytical_source_violations(("scripts/v7_research/clean.py",), root=tmp_path) == []


def test_the_scan_reports_a_listed_module_that_vanished(tmp_path) -> None:
    violations = analytical_source_violations(("scripts/v7_research/gone.py",), root=tmp_path)
    assert len(violations) == 1
    assert "does not exist" in violations[0]


def test_the_scan_does_not_trip_on_ordering_vocabulary(tmp_path) -> None:
    module = tmp_path / "scripts" / "v7_research"
    module.mkdir(parents=True)
    (module / "order.py").write_text("def go(d):\n    return rank_player(d)\n", encoding="utf-8")
    assert analytical_source_violations(("scripts/v7_research/order.py",), root=tmp_path) == []


# --------------------------------------------------------------------------
# runtime guard
# --------------------------------------------------------------------------


def test_a_clean_row_passes() -> None:
    reset_shape_cache()
    assert_row_is_analysis_safe({"match_id": 1, "self": {"kills": 3}}, source="test")


@pytest.mark.parametrize("field", ["rank", "rank_tier", "seasonRank", "mmr", "behavior_score"])
def test_a_forbidden_field_is_refused(field: str) -> None:
    reset_shape_cache()
    with pytest.raises(RankFenceViolation) as excinfo:
        assert_row_is_analysis_safe({"match_id": 1, field: 5}, source="test")
    assert field in str(excinfo.value)


def test_a_forbidden_field_is_refused_when_nested() -> None:
    reset_shape_cache()
    with pytest.raises(RankFenceViolation):
        assert_row_is_analysis_safe({"self": {"stats": {"rank_tier": 70}}}, source="test")


def test_a_forbidden_field_inside_a_list_is_refused() -> None:
    reset_shape_cache()
    with pytest.raises(RankFenceViolation):
        assert_row_is_analysis_safe({"all_players": [{"mmr": 4000}]}, source="test")


def test_the_shape_cache_does_not_let_a_later_bad_row_through() -> None:
    """Caching by shape is only safe if a different shape is a different key."""

    reset_shape_cache()
    assert_row_is_analysis_safe({"match_id": 1}, source="test")
    with pytest.raises(RankFenceViolation):
        assert_row_is_analysis_safe({"match_id": 1, "rank": 2}, source="test")


def test_shape_signature_ignores_values_but_not_keys() -> None:
    assert shape_signature({"a": 1}) == shape_signature({"a": 2})
    assert shape_signature({"a": 1}) != shape_signature({"b": 1})


def test_shape_signature_distinguishes_nesting() -> None:
    assert shape_signature({"a": {"b": 1}}) != shape_signature({"a": 1})


def test_an_empty_list_and_a_populated_one_are_both_signable() -> None:
    assert shape_signature({"xs": []}) != shape_signature({"xs": [{"a": 1}]})


# --------------------------------------------------------------------------
# contract
# --------------------------------------------------------------------------


def _forbidden_field_names(model: type[BaseModel]) -> list[str]:
    hits = []
    for name in model.model_fields:
        lowered = name.lower().replace("_", "")
        if any(token in lowered for token in FORBIDDEN_FIELD_TOKENS):
            hits.append(name)
    return hits


def test_no_analytical_contract_model_carries_a_forbidden_field() -> None:
    """``RankDisplay`` is display-only and lives under ``HistorySection``.
    Nothing that carries a Finding, a recommendation or an archetype may name
    a forbidden surface at all."""

    for model in (
        report_contract.Finding,
        report_contract.Recommendation,
        report_contract.RecommendationObservation,
        report_contract.ArchetypeSection,
    ):
        assert _forbidden_field_names(model) == []


def test_rank_display_is_reachable_only_through_history() -> None:
    assert "rank" in report_contract.HistorySection.model_fields
    assert _forbidden_field_names(report_contract.RankDisplay) != []  # it is the exception


def test_the_finding_section_union_excludes_history() -> None:
    """A Finding cannot claim to belong to the section rank is displayed in."""

    from typing import get_args

    assert "history" not in get_args(report_contract.FindingSectionKey)
