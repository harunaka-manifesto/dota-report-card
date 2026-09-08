"""Allowlisted public projection built only from a persisted V7 report."""

from __future__ import annotations

from typing import Literal

from app.player_analysis_v7.descriptive import (
    ActivityMemory,
    DescriptiveFacts,
    HeroUsage,
    TimeWindow,
)
from app.player_analysis_v7.display_semantics import DisplaySemantics
from app.player_analysis_v7.report_contract import (
    ArchetypeSection,
    Direction,
    Finding,
    PublicV7Model,
)

PUBLIC_PROJECTION_VERSION = "v7-public-projection-1.0.0"


class PublicFinding(PublicV7Model):
    dimension_key: str
    player_facing_question: str
    direction: Direction
    display_unit: str
    sample_size: int


class PublicWindow(PublicV7Model):
    observed_window: TimeWindow | None
    eligible_match_count: int
    coverage_status: Literal["complete", "truncated"]


class PublicProjection(PublicV7Model):
    version: Literal["v7-public-projection-1.0.0"] = "v7-public-projection-1.0.0"
    selected_kind: Literal[
        "special", "archetype", "favorable_finding", "hero", "activity", "window", "none"
    ]
    archetype: ArchetypeSection | None = None
    dominant_mode: Literal["STANDARD", "TURBO"] | None = None
    finding: PublicFinding | None = None
    hero: HeroUsage | None = None
    activity: ActivityMemory | None = None
    window: PublicWindow


def build_public_projection(
    *,
    facts: DescriptiveFacts,
    semantics: DisplaySemantics,
    findings: list[Finding],
    archetype: ArchetypeSection | None,
    dominant_mode: Literal["STANDARD", "TURBO"] | None,
) -> PublicProjection:
    window = PublicWindow(
        observed_window=facts.scope.observed_window,
        eligible_match_count=facts.scope.eligible_match_count,
        coverage_status=facts.scope.coverage_status,
    )
    if archetype is not None:
        return PublicProjection(
            selected_kind="special" if archetype.is_special else "archetype",
            archetype=archetype,
            dominant_mode=dominant_mode,
            window=window,
        )
    for finding in findings:
        display = semantics.findings.get(finding.dimension_key)
        if display is None:
            continue
        if finding.section != "what_is_good":
            continue
        if display.direction_source == "own_contrast_direction":
            direction = finding.own_contrast_direction
            if direction is None:
                continue
        else:
            direction = finding.direction
        return PublicProjection(
            selected_kind="favorable_finding",
            finding=PublicFinding(
                dimension_key=finding.dimension_key,
                player_facing_question=finding.player_facing_question,
                direction=direction,
                display_unit=display.display_unit,
                sample_size=finding.sample_size,
            ),
            window=window,
        )
    if facts.hero_cast.heroes:
        return PublicProjection(selected_kind="hero", hero=facts.hero_cast.heroes[0], window=window)
    if facts.activity_memory is not None:
        return PublicProjection(
            selected_kind="activity", activity=facts.activity_memory, window=window
        )
    return PublicProjection(
        selected_kind="window" if facts.scope.eligible_match_count else "none",
        window=window,
    )


__all__ = [
    "PUBLIC_PROJECTION_VERSION",
    "PublicFinding",
    "PublicProjection",
    "PublicWindow",
    "build_public_projection",
]
