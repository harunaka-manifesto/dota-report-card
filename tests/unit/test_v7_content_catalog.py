"""The machine-readable content catalog must not drift from the code.

A design agent will build UI from this file. If a dimension is renamed, a
weight changed or a threshold moved and the catalog still says the old thing,
the design is wrong and nobody finds out until it ships. So the catalog is
generated, and this test regenerates it and fails on any difference.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.player_analysis_v7.research import archetype, ranking, recommendation

from scripts.v7_build_content_catalog import CATALOG_VERSION, build

CATALOG_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "product" / "v7-content-catalog.json"
)


def _committed() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_the_committed_catalog_matches_a_fresh_build() -> None:
    expected = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    assert CATALOG_PATH.read_text(encoding="utf-8") == expected, (
        "docs/product/v7-content-catalog.json is stale; regenerate it with "
        "scripts/v7_build_content_catalog.py"
    )


def test_catalog_declares_itself_uncertified() -> None:
    catalog = _committed()
    assert catalog["schema_version"] == CATALOG_VERSION
    assert catalog["validation_status"] == "development"
    assert catalog["production_certified"] is False
    assert catalog["sealed_validation_read"] is False


def test_catalog_ships_sixteen_findings_and_withholds_five() -> None:
    catalog = _committed()
    assert len(catalog["findings"]["shipping_dimensions"]) == 16
    assert len(catalog["findings"]["withheld_dimensions"]) == 5


def test_the_negative_control_is_withheld_and_labelled() -> None:
    withheld = _committed()["findings"]["withheld_dimensions"]
    control = [row for row in withheld if row["is_negative_control"]]
    assert len(control) == 1
    assert control[0]["id"] == "side_sensitivity"
    assert "never be surfaced" in control[0]["withheld_reason"]


def test_no_shipping_dimension_is_the_negative_control() -> None:
    for row in _committed()["findings"]["shipping_dimensions"]:
        assert row["is_negative_control"] is False


def test_catalog_records_that_strength_bands_do_not_exist() -> None:
    assert _committed()["findings"]["strength_bands_exist"] is False


def test_catalog_flags_reliability_upper_bounds() -> None:
    """A dimension whose dependence curve never plateaued has an upper-bound
    reliability, and a design agent weighing dimensions should be able to see
    that without reading the statistics."""

    rows = _committed()["findings"]["shipping_dimensions"]
    for row in rows:
        assert row["reliability_is_upper_bound"] == (not row["dependence_curve_plateaued"])
    assert any(row["reliability_is_upper_bound"] for row in rows)


def test_recommendation_catalog_matches_the_registry() -> None:
    catalog = _committed()["recommendation"]
    assert catalog["minimum_matches_per_arm"] == recommendation.MIN_PER_ARM
    assert catalog["modal_sign_share_limit"] == recommendation.MODAL_SIGN_SHARE_LIMIT
    assert catalog["share_safe"] is False
    assert catalog["claims_causation"] is False
    ids = {row["id"] for row in catalog["dimensions"]}
    assert ids == set(recommendation.RECOMMENDATION_REGISTRY)
    eligible = {row["id"] for row in catalog["dimensions"] if row["eligible"]}
    assert eligible == set(recommendation.eligible_dimensions())


def test_canonical_recommendation_copy_is_carried_verbatim() -> None:
    for row in _committed()["recommendation"]["dimensions"]:
        source = recommendation.RECOMMENDATION_REGISTRY[row["id"]]
        assert row["canonical_recommendation_text"] == source.recommendation
        assert row["canonical_verification_text"] == source.verification


def test_finding_questions_match_their_measured_semantics() -> None:
    questions = {
        row["id"]: row["display_concept"]
        for row in _committed()["findings"]["shipping_dimensions"]
    }
    assert questions["vision_coverage"] == (
        "How much of each match has one of your observer wards active?"
    )
    assert questions["deaths_alone_share"] == (
        "How many of your deaths happen in minutes without team kill activity?"
    )
    assert questions["purchase_tempo"] == (
        "How far into a game are you when you make your eighth purchase?"
    )
    assert questions["post_loss_requeue_latency"] == (
        "After a loss, how long until your next recorded game?"
    )


def test_archetype_catalog_carries_all_twenty_labels() -> None:
    catalog = _committed()["archetype"]
    assert len(catalog["grid_labels"]) == 18
    assert len(catalog["special_labels"]) == 2
    labels = {row["label"] for row in catalog["grid_labels"]}
    assert labels == set(archetype.GRID_LABELS.values())
    assert catalog["refusal_has_no_default_label"] is True
    assert catalog["is_analytical"] is False


def test_every_special_is_marked_provisional() -> None:
    for row in _committed()["archetype"]["special_labels"]:
        assert row["provisional"] is True
        assert row["percentile_cut"] == archetype.SPECIAL_PERCENTILE


def test_finding_policy_matches_the_ranking_module() -> None:
    catalog = _committed()["findings"]
    assert catalog["finding_floor"] == ranking.FINDING_FLOOR
    assert catalog["score_line"] == ranking.SCORE_LINE
    assert catalog["report_slots"] == ranking.REPORT_SLOTS
    assert catalog["sections"] == list(ranking.FINDING_SECTIONS)


def test_no_refusal_state_permits_a_fabricated_fallback() -> None:
    """The rule the design agent most needs held: a refusal is a refusal."""

    for row in _committed()["refusal_states"]:
        assert row["fallback_permitted"] is False


def test_catalog_is_honest_about_what_is_not_built() -> None:
    catalog = _committed()
    assert catalog["report_payload_producer_exists"] is False
    assert catalog["acquisition"]["persistence_wiring_implemented"] is False


def test_catalog_records_that_no_decision_needs_a_reserved_split() -> None:
    assert _committed()["decisions_needing_a_reserved_split"] == []


def test_catalog_contains_no_pseudonyms() -> None:
    assert "v7p_" not in CATALOG_PATH.read_text(encoding="utf-8")
