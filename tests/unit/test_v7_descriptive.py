from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.player_analysis_v7.assembly import assemble_v7_capability
from app.player_analysis_v7.descriptive import derive_descriptive_facts
from app.providers.base import (
    CanonicalProfile,
    HistoryWindow,
    ProviderProvenance,
    V7CanonicalHistory,
    V7CanonicalMatch,
)

FIXTURE = Path(__file__).parents[1] / "fixtures/v7/master-plan-descriptive-states.json"


def ts(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())


def match(
    match_id: int, when: str, hero_id: int, won: bool, *, parsed: bool = True
) -> V7CanonicalMatch:
    return V7CanonicalMatch(
        provider="stratz",
        provider_schema_version="fixture",
        match_id=match_id,
        hero_id=hero_id,
        started_at=ts(when),
        duration_seconds=2400,
        side="radiant",
        won=won,
        kills=1,
        deaths=1,
        assists=1,
        game_version_id=1,
        position="POSITION_1",
        role="CORE",
        lane="SAFE_LANE",
        game_mode_native="ALL_PICK",
        lobby_native="RANKED",
        leaver_status_native="NONE",
        is_parsed=parsed,
    )


def history(matches: list[V7CanonicalMatch], *, complete: bool = True) -> V7CanonicalHistory:
    return V7CanonicalHistory(
        profile=CanonicalProfile("stratz", "fixture", 1, None, None, False, True),
        window=HistoryWindow(ts("2026-01-01"), ts("2026-04-01"), 90),
        matches=tuple(matches),
        provenance=ProviderProvenance(
            "stratz",
            "fixture",
            "history",
            "1",
            "a",
            "1",
            1,
            1,
            "2026-04-01T00:00:00Z",
            "b",
            "complete" if complete else "truncated",
            1.0,
        ),
    )


def test_descriptive_facts_keep_ties_and_incomplete_maximums_honest() -> None:
    rows = [
        match(1, "2026-01-02", 1, False),
        match(2, "2026-01-03", 2, False),
        match(3, "2026-01-04", 1, False),
        match(4, "2026-01-05", 2, True),
        match(5, "2026-01-15", 1, True),
        match(6, "2026-01-16", 2, True),
    ]
    result = derive_descriptive_facts(
        history(rows, complete=False),
        {1: {"display_name": "Axe"}, 2: {"display_name": "Bane"}},
        generated_at="2026-04-01T00:00:00Z",
    )
    assert result.scope.coverage_status == "truncated"
    assert result.hero_cast.has_unique_most_played is False
    assert [hero.tied_for_most_played for hero in result.hero_cast.heroes] == [True, True]
    assert result.activity_memory is not None
    assert result.activity_memory.claim_status == "recorded"
    assert result.completed_loss_run is not None
    assert result.completed_loss_run.loss_count == 3
    assert result.completed_loss_run.share_safe is False


def test_monthly_contrast_requires_full_adjacent_months_and_unique_leaders() -> None:
    rows: list[V7CanonicalMatch] = []
    for index in range(10):
        rows.append(match(index + 1, f"2026-02-{index + 1:02d}", 1 if index < 4 else 3, True))
        rows.append(match(index + 20, f"2026-03-{index + 1:02d}", 2 if index < 4 else 3, True))
    result = derive_descriptive_facts(
        history(rows),
        {
            1: {"display_name": "Axe"},
            2: {"display_name": "Bane"},
            3: {"display_name": "Chen"},
        },
        generated_at="2026-04-01T00:00:00Z",
    )
    # Chen is the unique leader in both months, so there is no change claim.
    assert result.monthly_hero_contrast is None


def test_monthly_contrast_selects_changed_unique_leaders() -> None:
    rows: list[V7CanonicalMatch] = []
    for index in range(10):
        rows.append(match(index + 1, f"2026-02-{index + 1:02d}", 1 if index < 6 else 3, True))
        rows.append(match(index + 20, f"2026-03-{index + 1:02d}", 2 if index < 6 else 3, True))
    result = derive_descriptive_facts(
        history(rows),
        {
            1: {"display_name": "Axe"},
            2: {"display_name": "Bane"},
            3: {"display_name": "Chen"},
        },
        generated_at="2026-04-01T00:00:00Z",
    )
    assert result.monthly_hero_contrast is not None
    assert result.monthly_hero_contrast.earlier.display_name == "Axe"
    assert result.monthly_hero_contrast.later.display_name == "Bane"


def test_unresolved_or_known_gap_loss_runs_are_not_completed() -> None:
    unresolved = [
        match(1, "2026-01-02", 1, False),
        match(2, "2026-01-03", 1, False),
        match(3, "2026-01-04", 1, False),
    ]
    assert derive_descriptive_facts(
        history(unresolved),
        {1: {"display_name": "Axe"}},
        generated_at="2026-04-01T00:00:00Z",
    ).completed_loss_run is None
    gapped = unresolved + [match(4, "2026-01-05", 1, True)]
    assert derive_descriptive_facts(
        history(gapped),
        {1: {"display_name": "Axe"}},
        generated_at="2026-04-01T00:00:00Z",
        known_gap_after_match_ids=[2],
    ).completed_loss_run is None


def test_assembly_keeps_unavailable_analytics_explicit_and_share_projection_safe() -> None:
    payload = assemble_v7_capability(
        history=history([match(1, "2026-01-02", 1, True)]),
        hero_metadata={1: {"display_name": "Axe"}},
        generated_at="2026-04-01T00:00:00Z",
        findings=[],
        recommendation=None,
        archetype=None,
        dominant_mode=None,
        rank_display=None,
        refused={
            "findings": "no_valid_opportunities",
            "recommendation": "insufficient_wins_or_losses_per_arm",
            "archetype": "insufficient_sessions",
            "dominant_mode": "no_dominant_mode_stratum",
            "rank_display": "not_collected",
        },
        feature_version="fixture-features",
        inference_version="fixture-inference",
    )
    assert payload.public_projection.selected_kind == "hero"
    assert payload.public_projection.hero is not None
    assert payload.public_projection.hero.display_name == "Axe"
    assert payload.recommendation is None


def test_master_plan_fixture_is_synthetic_and_covers_safety_states() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    serialized = json.dumps(document)
    names = {state["name"] for state in document["states"]}
    assert document["synthetic"] is True
    assert "v7p_" not in serialized
    assert "truncated-recorded-only-missing-hero-metadata" in names
    assert "completed-loss-run-private" in names
