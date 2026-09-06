"""The frontend-facing capability payload and its invariants.

The payload is what a frontend agent codes against, so an invariant that is
documented but unenforced is worse than none: it invites a design built on a
promise the backend does not keep. Every invariant in
``docs/architecture/v7-runtime-capability-payload.md`` section 4 is tested here
with both a passing and a failing case.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from app.player_analysis_v7.capability_payload import (
    CAPABILITY_KEYS,
    V7_CAPABILITY_SCHEMA_VERSION,
    WITHHELD_DIMENSIONS,
    CapabilityAvailability,
    PlayerContext,
    Refusal,
    ReportMetadata,
    V7CapabilityPayload,
    V7Provenance,
    availability_map,
)
from app.player_analysis_v7.report_contract import (
    ArchetypeSection,
    Finding,
    PointEstimateWithInterval,
    RankDisplay,
    Recommendation,
    RecommendationObservation,
)
from pydantic import ValidationError


def finding(key: str, section: str, z: float, reliability: float) -> Finding:
    return Finding(
        dimension_key=key,
        section=section,  # type: ignore[arg-type]
        direction="positive" if z >= 0 else "negative",
        z=z,
        reliability=reliability,
        score=abs(z) * reliability,
        estimate=PointEstimateWithInterval(point=0.34, interval_low=0.29, interval_high=0.39),
        sample_size=412,
        player_facing_question="how much of the map do you keep lit?",
    )


def metadata() -> ReportMetadata:
    return ReportMetadata(
        generated_at="2026-09-07T02:00:00Z",
        window_days=365,
        window_start=1756745426,
        window_end=1788281426,
        matches_total=1474,
        matches_analysed=1180,
        matches_with_event_detail=493,
        acquisition_depth=500,
    )


def provenance() -> V7Provenance:
    return V7Provenance(
        schema_version=V7_CAPABILITY_SCHEMA_VERSION,
        population_parameters_version="v7-population-parameters-1.0.0",
        ranking_model_version="v7-luna-f-ranking-1.0.0",
        recommendation_model_version="v7-improvement-recommendation-1.0.0",
        archetype_model_version="v7-archetype-axes-1.0.0",
        feature_version="v7-luna-b-features-1.0.0",
        inference_version="v7-luna-c-inference-1.0.0",
        owner_decisions_version="v7-owner-decisions-2026-09-06b",
    )


def recommendation() -> Recommendation:
    return Recommendation(
        dimension_key="last_hits_at_ten",
        observation=RecommendationObservation(win_value=61.2, loss_value=58.8, gap=-2.4),
        direction="negative",
        recommendation_text="For five games, care about nothing but last hits until minute 10.",
        verification="last_hits_per_minute cumulated to minute 10",
        sample_wins=214,
        sample_losses=198,
        reliability=0.98,
        actionability_weight=0.95,
        priority_score=0.34,
    )


def archetype() -> ArchetypeSection:
    return ArchetypeSection(
        tempo="early", fight_style="frontliner", modifier="metronome", label="The Alarm Clock"
    )


def payload(**overrides: Any) -> V7CapabilityPayload:
    base: dict[str, Any] = {
        "metadata": metadata(),
        "player_context": PlayerContext(
            dominant_mode="TURBO",
            rank_display=RankDisplay(
                start_rank_label="Legend 3", end_rank_label="Ancient 1", direction="positive"
            ),
        ),
        "findings": [
            finding("vision_coverage", "what_is_good", 2.0, 0.98),
            finding("deaths_alone_share", "what_is_costing_you", 1.5, 0.89),
            finding("post_loss_hero_switch", "response_to_a_loss", 1.0, 0.46),
        ],
        "recommendation": recommendation(),
        "archetype": archetype(),
        "availability": availability_map(available=CAPABILITY_KEYS),
        "refusals": [],
        "provenance": provenance(),
    }
    base.update(overrides)
    return V7CapabilityPayload(**base)


# --------------------------------------------------------------------------
# happy paths
# --------------------------------------------------------------------------


def test_a_fully_populated_payload_validates() -> None:
    assert payload().validate_payload() is not None


def test_a_payload_with_every_optional_capability_refused_validates() -> None:
    result = payload(
        findings=[],
        recommendation=None,
        archetype=None,
        player_context=PlayerContext(),
        availability=availability_map(
            refused={
                "findings": "no_valid_opportunities",
                "recommendation": "insufficient_wins_or_losses_per_arm",
                "archetype": "insufficient_sessions",
                "dominant_mode": "no_dominant_mode_stratum",
                "rank_display": "not_collected",
            }
        ),
        refusals=[
            Refusal.of("findings", "no_valid_opportunities"),
            Refusal.of("recommendation", "insufficient_wins_or_losses_per_arm"),
            Refusal.of("archetype", "insufficient_sessions"),
            Refusal.of("dominant_mode", "no_dominant_mode_stratum"),
            Refusal.of("rank_display", "not_collected"),
        ],
    )
    assert result.validate_payload() is not None


# --------------------------------------------------------------------------
# invariants
# --------------------------------------------------------------------------


def test_a_withheld_dimension_is_rejected() -> None:
    for key in sorted(WITHHELD_DIMENSIONS):
        with pytest.raises(ValidationError, match="withheld dimension"):
            payload(findings=[finding(key, "what_is_good", 2.0, 0.9)])


def test_findings_out_of_rank_order_are_rejected() -> None:
    with pytest.raises(ValidationError, match="ordered by"):
        payload(
            findings=[
                finding("deaths_alone_share", "what_is_costing_you", 1.0, 0.5),
                finding("vision_coverage", "what_is_good", 2.0, 0.98),
            ]
        )


def test_more_findings_than_slots_are_rejected() -> None:
    many = [finding(f"d{i}", "what_is_good", 3.0 - i * 0.1, 0.9) for i in range(6)]
    with pytest.raises(ValidationError):
        payload(findings=many)


def test_availability_must_cover_every_capability() -> None:
    partial = {"findings": CapabilityAvailability(status="available")}
    with pytest.raises(ValidationError, match="every capability"):
        payload(availability=partial)


def test_a_refused_capability_carrying_a_value_is_rejected() -> None:
    with pytest.raises(ValidationError, match="refused but carries a value"):
        payload(
            availability=availability_map(
                available=[k for k in CAPABILITY_KEYS if k != "archetype"],
                refused={"archetype": "insufficient_sessions"},
            ),
            refusals=[Refusal.of("archetype", "insufficient_sessions")],
        )


def test_an_available_capability_that_is_null_is_rejected() -> None:
    with pytest.raises(ValidationError, match="available but is null"):
        payload(archetype=None)


def test_refusals_must_match_availability() -> None:
    with pytest.raises(ValidationError, match="refusals must match"):
        payload(refusals=[Refusal.of("archetype", "insufficient_sessions")])


def test_a_refusal_contradicting_its_documented_semantics_is_rejected() -> None:
    with pytest.raises(ValidationError, match="documented semantics"):
        Refusal(
            capability="archetype",
            code="insufficient_sessions",
            retry_may_change=False,
            more_matches_may_change=False,
            permanently_unsupported=True,
        )


def test_the_d1_gate_is_enforced_beyond_the_floor() -> None:
    """A fourth Finding below the line that duplicates a covered section would
    have been trimmed by the gate, so a payload carrying it is malformed."""

    with pytest.raises(ValidationError, match="D1 gate"):
        payload(
            findings=[
                finding("vision_coverage", "what_is_good", 2.0, 0.98),
                finding("deaths_alone_share", "what_is_costing_you", 1.5, 0.89),
                finding("post_loss_hero_switch", "response_to_a_loss", 1.0, 0.46),
                finding("duration_tempo", "what_is_good", 0.1, 0.5),
            ]
        )


def test_the_d1_gate_permits_a_sections_only_representative_below_the_line() -> None:
    """The clause that stops the gate undoing section stratification."""

    result = payload(
        findings=[
            finding("vision_coverage", "what_is_good", 2.0, 0.98),
            finding("duration_tempo", "what_is_good", 1.5, 0.9),
            finding("deaths_alone_share", "what_is_costing_you", 1.0, 0.9),
            finding("post_loss_hero_switch", "response_to_a_loss", 0.1, 0.5),
        ]
    )
    assert len(result.findings) == 4


def test_a_finding_in_a_non_finding_section_is_rejected() -> None:
    with pytest.raises(ValidationError):
        payload(findings=[finding("vision_coverage", "history", 2.0, 0.9)])


def test_a_non_finite_score_is_rejected() -> None:
    bad = finding("vision_coverage", "what_is_good", 2.0, 0.98)
    with pytest.raises(ValidationError, match="finite"):
        payload(findings=[bad.model_copy(update={"z": float("nan"), "score": float("nan")})])


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        payload(unexpected_field="nope")


def test_incoherent_metadata_counts_are_rejected() -> None:
    with pytest.raises(ValidationError, match="exceeds matches_total"):
        ReportMetadata(
            generated_at="2026-09-07T02:00:00Z",
            window_days=365,
            window_start=1,
            window_end=2,
            matches_total=10,
            matches_analysed=11,
            matches_with_event_detail=0,
            acquisition_depth=500,
        )


# --------------------------------------------------------------------------
# serialisation
# --------------------------------------------------------------------------


def test_the_payload_is_json_safe() -> None:
    document = payload().model_dump(mode="json")
    serialized = json.dumps(document)
    assert "NaN" not in serialized
    assert "Infinity" not in serialized
    assert "v7p_" not in serialized


def test_an_internal_pseudonym_is_caught_at_the_payload_level() -> None:
    leaky = payload(
        findings=[finding("v7p_leak", "what_is_good", 2.0, 0.9)],
    )
    with pytest.raises(ValueError, match="research pseudonym"):
        leaky.validate_payload()


def test_rank_display_survives_the_forbidden_field_scan() -> None:
    """Rank is display-only and sanctioned in exactly one place; the scan must
    not reject the payload for carrying it there."""

    document = payload().validate_payload().model_dump(mode="json")
    assert document["player_context"]["rank_display"]["start_rank_label"] == "Legend 3"


def test_the_schema_version_is_pinned() -> None:
    assert payload().schema_version == V7_CAPABILITY_SCHEMA_VERSION
