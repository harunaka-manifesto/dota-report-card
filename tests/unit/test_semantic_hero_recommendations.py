from __future__ import annotations

from dataclasses import dataclass

from app.heroes.knowledge import (
    HERO_DEMAND_FAMILIES,
    NormalizedHeroKnowledge,
    SnapshotHeroKnowledgeProvider,
)
from app.heroes.recommendations import recommend_semantic_heroes
from app.ingestion.summary_normalize import normalize_summary_rows


@dataclass(frozen=True)
class _Provider:
    entries: tuple[NormalizedHeroKnowledge, ...]
    version: str = "hero-knowledge-test"

    def get(self, hero_id: int | None) -> NormalizedHeroKnowledge | None:
        return next((entry for entry in self.entries if entry.hero_id == hero_id), None)


def _hero(
    hero_id: int,
    name: str,
    roles: tuple[str, ...],
    primary: tuple[str, ...],
    secondary: tuple[str, ...] = (),
    *,
    confidence: str = "high",
    empirical_support: str = "unknown",
    demands: dict[str, str] | None = None,
) -> NormalizedHeroKnowledge:
    values = demands or {family: "low" for family in HERO_DEMAND_FAMILIES}
    return NormalizedHeroKnowledge(
        hero_id=hero_id,
        display_name=name,
        roles=roles,
        functional_jobs=primary + secondary,
        provenance_versions={"hero_knowledge": "hero-knowledge-test"},
        primary_functions=primary,
        secondary_functions=secondary,
        demands=values,
        capabilities={job: "high" for job in primary + secondary},
        empirical_support=empirical_support,
        confidence=confidence,
        evidence_refs=(f"fixture:{hero_id}",),
        review_status="approved",
    )


def _matches(*hero_ids: int, lane_role: int = 1):
    rows = [
        {
            "match_id": index + 1,
            "start_time": 1_800_000_000 + index * 100,
            "duration": 1_800,
            "hero_id": hero_id,
            "player_slot": 0,
            "radiant_win": True,
            "game_mode": 1,
            "lobby_type": 0,
            "kills": 5,
            "deaths": 2,
            "assists": 5,
            "lane_role": lane_role,
        }
        for index, hero_id in enumerate(hero_ids)
    ]
    return normalize_summary_rows(rows, account_id=42).matches


def test_unknown_empirical_support_is_explicit_and_lowers_confidence() -> None:
    provider = SnapshotHeroKnowledgeProvider()
    rationales = recommend_semantic_heroes(
        _matches(2, 2, 2, 13, 13, 13, lane_role=3),
        provider,
        intent="adjacent_move",
        limit=3,
    )

    assert rationales
    assert all(item.empirical_support == "unknown" for item in rationales)
    assert all(item.confidence == "medium" for item in rationales)
    assert all(
        any("Empirical support is unknown" in limitation for limitation in item.limitations)
        for item in rationales
    )
    assert all(item.eligible for item in rationales)


def test_low_confidence_candidate_is_suppressed_and_role_mismatch_is_blocked() -> None:
    observed = _hero(
        1,
        "Observed",
        ("carry",),
        ("initiation",),
        demands={family: "low" for family in HERO_DEMAND_FAMILIES},
    )
    low_confidence = _hero(
        2,
        "Low confidence bridge",
        ("carry",),
        ("initiation",),
        ("push",),
        confidence="low",
        empirical_support="low",
        demands={**{family: "low" for family in HERO_DEMAND_FAMILIES}, "economy": "high"},
    )
    role_mismatch = _hero(
        3,
        "Role mismatch bridge",
        ("support",),
        ("initiation",),
        ("wave_clear",),
        demands={**{family: "low" for family in HERO_DEMAND_FAMILIES}, "economy": "high"},
    )
    provider = _Provider((observed, low_confidence, role_mismatch))

    rationales = recommend_semantic_heroes(
        _matches(1, 1, 1, lane_role=1),
        provider,
        intent="fill_gap",
        limit=3,
    )
    ineligible = recommend_semantic_heroes(
        _matches(1, 1, 1, lane_role=1),
        provider,
        intent="fill_gap",
        limit=3,
        include_ineligible=True,
    )

    assert rationales == []
    assert {item.hero_id for item in ineligible} == {2, 3}
    assert all(item.eligible is False for item in ineligible)
    assert {item.role_fit for item in ineligible} == {"supported", "unsupported"}
