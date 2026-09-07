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
from app.analysis.source import MappingSource
from app.api.routes import router
from app.core.config import Settings
from app.main import create_app
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
from app.player_analysis_v7.descriptive import (
    DescriptiveFacts,
    HeroCast,
    ReportScope,
    TimeWindow,
)
from app.player_analysis_v7.display_semantics import build_display_semantics
from app.player_analysis_v7.lifecycle import V7ReportLifecycle, analytical_identity
from app.player_analysis_v7.public_projection import build_public_projection
from app.player_analysis_v7.report_contract import (
    ArchetypeSection,
    Finding,
    PointEstimateWithInterval,
    RankDisplay,
    Recommendation,
    RecommendationObservation,
)
from app.storage.repository import InMemoryRepository
from fastapi.testclient import TestClient
from pydantic import ValidationError


def finding(key: str, section: str, z: float, reliability: float) -> Finding:
    semantics = build_display_semantics().findings.get(key)
    return Finding(
        dimension_key=key,
        section=section,  # type: ignore[arg-type]
        direction="positive" if z >= 0 else "negative",
        own_contrast_direction=(
            "positive"
            if semantics is not None and semantics.direction_source == "own_contrast_direction"
            else None
        ),
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
        descriptive_producer_version="v7-descriptive-facts-1.0.0",
        display_semantics_version="v7-display-semantics-1.0.0",
        public_projection_version="v7-public-projection-1.0.0",
        reuse_status="generated",
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
    facts = DescriptiveFacts(
        scope=ReportScope(
            requested_window=TimeWindow(start=1756745426, end=1788281426),
            observed_window=TimeWindow(start=1756745426, end=1788281426),
            eligible_match_count=1180,
            parsed_match_count=493,
            acquired_match_count=1474,
            acquisition_depth_limit=500,
            coverage_status="complete",
            coverage_boundary_reason="provider_reported_complete",
            generated_at="2026-09-07T02:00:00Z",
        ),
        hero_cast=HeroCast(
            heroes=[], missing_display_metadata_hero_ids=[], has_unique_most_played=False
        ),
    )
    semantics = build_display_semantics()
    base: dict[str, Any] = {
        "metadata": metadata(),
        "descriptive_facts": facts,
        "display_semantics": semantics,
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
    base.setdefault(
        "public_projection",
        build_public_projection(
            facts=base["descriptive_facts"],
            semantics=base["display_semantics"],
            findings=base["findings"],
            archetype=base["archetype"],
            dominant_mode=base["player_context"].dominant_mode,
        ),
    )
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
    leaky_finding = finding("vision_coverage", "what_is_good", 2.0, 0.9).model_copy(
        update={"player_facing_question": "v7p_leak"}
    )
    leaky = payload(
        findings=[leaky_finding],
    )
    with pytest.raises(ValueError, match="research pseudonym"):
        leaky.validate_payload()


def test_rank_display_survives_the_forbidden_field_scan() -> None:
    """Rank is display-only and sanctioned in exactly one place; the scan must
    not reject the payload for carrying it there."""

    document = payload().validate_payload().model_dump(mode="json")
    assert document["player_context"]["rank_display"]["start_rank_label"] == "Legend 3"


def test_semantics_bind_all_shipping_dimensions_without_fake_unit_conversion() -> None:
    semantics = build_display_semantics()
    assert len(semantics.findings) == 16
    assert len(semantics.recommendations) == 7
    assert "decided-ahead" in semantics.findings["lead_retention"].exact_definition
    assert "eighth item purchase" in semantics.findings["purchase_tempo"].exact_definition
    assert (
        semantics.findings["post_loss_requeue_latency"].numeric_conversion
        == "omit_without_baseline"
    )
    assert semantics.findings["closer_vs_comeback"].direction_source == "own_contrast_direction"
    note = semantics.recommendations["first_real_item_time"].measurement_note
    assert note is not None and "not the first purchase" in note


def test_population_direction_cannot_replace_own_contrast_direction() -> None:
    contrast = finding("closer_vs_comeback", "response_to_a_loss", 2.0, 0.9).model_copy(
        update={
            "own_contrast_direction": "positive",
            "estimate": PointEstimateWithInterval(point=-0.1, interval_low=-0.2, interval_high=0.0),
        }
    )
    with pytest.raises(ValidationError, match="own contrast direction 'negative'"):
        payload(findings=[contrast])


def test_recommendation_copy_is_bound_to_the_registry() -> None:
    rewritten = recommendation().model_copy(update={"recommendation_text": "Try to last-hit more."})
    with pytest.raises(ValidationError, match="canonical registry"):
        payload(recommendation=rewritten)


def test_public_projection_never_contains_recommendation_or_private_provenance() -> None:
    document = payload().public_projection.model_dump(mode="json")
    assert document["selected_kind"] == "archetype"
    assert document["dominant_mode"] == "TURBO"
    assert "recommendation" not in json.dumps(document).lower()
    assert "provenance" not in document


def test_v7_lifecycle_coalesces_and_reuses_persisted_reports() -> None:
    repository = InMemoryRepository()
    lifecycle = V7ReportLifecycle(repository, versions={"analysis": "fixture-1"})
    first, reused = lifecycle.locate_or_start(7, "fixture-player")
    assert reused is False
    joined, reused = lifecycle.locate_or_start(7, "fixture-player")
    assert reused is True
    assert joined.job_id == first.job_id
    report_id = lifecycle.complete(first, payload())
    reopened, reused = lifecycle.locate_or_start(7, "fixture-player")
    assert reused is True
    assert reopened.report_id == report_id
    assert lifecycle.load(report_id) == payload()


def test_analytical_identity_is_independent_of_mapping_order() -> None:
    versions = {"features": "1", "inference": "1"}
    assert analytical_identity(versions) == analytical_identity(
        dict(reversed(list(versions.items())))
    )


def test_the_schema_version_is_pinned() -> None:
    assert payload().schema_version == V7_CAPABILITY_SCHEMA_VERSION


def test_v7_persisted_report_route_is_typed_in_openapi() -> None:
    route = next(item for item in router.routes if item.path == "/v1/v7/reports/{report_id}")
    assert route.response_model is V7CapabilityPayload


def test_v7_persisted_report_route_validates_and_sets_noindex() -> None:
    repository = InMemoryRepository()
    report_id = repository.save_report(
        account_id=7,
        data_cutoff=payload().metadata.window_end,
        model_version="v7-fixture",
        template_version=V7_CAPABILITY_SCHEMA_VERSION,
        report=payload().model_dump(mode="json"),
        evidence=[],
    )
    source = MappingSource(player={"profile": {"account_id": 7}}, matches=[], details={})
    response = TestClient(
        create_app(Settings(), source=source, repository=repository)
    ).get(f"/v1/v7/reports/{report_id}")
    assert response.status_code == 200
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert response.json()["schema_version"] == V7_CAPABILITY_SCHEMA_VERSION
