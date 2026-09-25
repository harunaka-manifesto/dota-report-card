from __future__ import annotations

import pytest
from report_card.player_analysis_v7.descriptive import (
    DescriptiveFacts,
    HeroCast,
    ReportScope,
    TimeWindow,
)
from report_card.player_analysis_v7.display_semantics import build_display_semantics
from report_card.player_analysis_v7.public_projection import (
    PublicFinding,
    PublicProjection,
    PublicWindow,
    build_public_projection,
)
from report_card.player_analysis_v7.report_contract import Finding, PointEstimateWithInterval


def _facts() -> DescriptiveFacts:
    return DescriptiveFacts(
        scope=ReportScope(
            requested_window=TimeWindow(start=1, end=2),
            observed_window=TimeWindow(start=1, end=2),
            eligible_match_count=1,
            parsed_match_count=0,
            acquired_match_count=1,
            acquisition_depth_limit=500,
            coverage_status="complete",
            coverage_boundary_reason="provider_reported_complete",
            generated_at="2026-09-09T00:00:00Z",
        ),
        hero_cast=HeroCast(
            heroes=[], missing_display_metadata_hero_ids=[], has_unique_most_played=False
        ),
    )


def _finding(z: float, direction: str) -> Finding:
    return Finding(
        dimension_key="vision_coverage",
        section="what_is_good",
        direction=direction,  # type: ignore[arg-type]
        z=z,
        reliability=0.9,
        score=abs(z) * 0.9,
        estimate=PointEstimateWithInterval(point=0.34, interval_low=0.29, interval_high=0.39),
        sample_size=20,
        player_facing_question="How often are your own observer wards active?",
    )


@pytest.mark.parametrize(
    ("z", "direction"),
    [(-3.0, "negative"), (0.0, "zero"), (3.0, "positive")],
)
def test_findings_never_become_favorable_without_approved_polarity(
    z: float, direction: str
) -> None:
    projection = build_public_projection(
        facts=_facts(),
        semantics=build_display_semantics(),
        findings=[_finding(z, direction)],
        archetype=None,
        dominant_mode=None,
    )

    assert projection.selected_kind == "window"
    assert projection.finding is None


def test_historical_favorable_finding_shape_remains_in_public_schema() -> None:
    projection = PublicProjection(
        selected_kind="favorable_finding",
        finding=PublicFinding(
            dimension_key="vision_coverage",
            player_facing_question="How often are your own observer wards active?",
            direction="positive",
            display_unit="proportion",
            sample_size=20,
        ),
        window=PublicWindow(
            observed_window=TimeWindow(start=1, end=2),
            eligible_match_count=1,
            coverage_status="complete",
        ),
    )

    assert projection.selected_kind == "favorable_finding"
    assert projection.finding is not None
