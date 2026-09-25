"""Allowlisted public projection built only from a persisted V7 report."""

from __future__ import annotations

from typing import Literal

from report_card.player_analysis_v7.descriptive import (
    ActivityMemory,
    DescriptiveFacts,
    HeroUsage,
    TimeWindow,
)
from report_card.player_analysis_v7.display_semantics import DisplaySemantics
from report_card.player_analysis_v7.report_contract import (
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
    # Finding sections are topical, and no approved metric-level polarity
    # policy exists yet. Do not guess that a section, z-score, or direction is
    # favorable; retain the schema for historical payloads and use a safe
    # descriptive fallback until that policy is explicitly approved.
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
