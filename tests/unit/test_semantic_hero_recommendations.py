from __future__ import annotations

from dataclasses import dataclass

from app.behavior.actions import build_versatile_core_action
from app.heroes.knowledge import (
    COVERAGE_FAMILIES,
    HERO_DEMAND_FAMILIES,
    FullRosterHeroKnowledgeProvider,
    NormalizedHeroKnowledge,
    SnapshotHeroKnowledgeProvider,
)
from app.heroes.recommendations import recommend_semantic_heroes
from app.heroes.taxonomy import load_default_taxonomy
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
    position_credibility: dict[str, str] | None = None,
    specialist_markers: tuple[str, ...] = (),
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
        position_credibility=position_credibility or {},
        specialist_markers=specialist_markers,
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
    assert {item.role_fit for item in ineligible} == {"conditional", "unsupported"}


def test_intents_use_distinct_semantic_contracts() -> None:
    low_demands = {family: "low" for family in HERO_DEMAND_FAMILIES}
    observed = _hero(1, "Observed", ("carry",), ("initiation", "catch"), demands=low_demands)
    double_down = _hero(2, "Same answer", ("carry",), ("initiation", "catch"), demands=low_demands, empirical_support="high")
    adjacent = _hero(3, "Map branch", ("carry",), ("initiation", "wave_clear"), demands=low_demands, empirical_support="high")
    angle = _hero(
        4,
        "Same job, new demand",
        ("carry",),
        ("initiation", "catch"),
        demands={**low_demands, "economy": "high"},
        empirical_support="high",
    )
    specialist = _hero(
        5,
        "Specialist",
        ("carry",),
        ("initiation", "catch"),
        demands={**low_demands, "economy": "high", "micro": "high", "execution": "high"},
        empirical_support="high",
        specialist_markers=("high_execution",),
    )
    provider = _Provider((observed, double_down, adjacent, angle, specialist))
    matches = _matches(1, 1, 1, lane_role=1)

    deep = recommend_semantic_heroes(matches, provider, intent="double_down", limit=1)
    stretch = recommend_semantic_heroes(matches, provider, intent="adjacent_move", limit=1)
    angle_result = recommend_semantic_heroes(matches, provider, intent="change_angle", limit=1)
    specialist_result = recommend_semantic_heroes(matches, provider, intent="specialist", limit=1)

    assert deep and deep[0].hero_id == 2
    assert stretch and stretch[0].hero_id == 3
    assert angle_result and angle_result[0].hero_id in {4, 5}
    assert specialist_result and specialist_result[0].hero_id == 5
    assert {item.intent for item in (*deep, *stretch, *angle_result, *specialist_result)} == {
        "double_down",
        "adjacent_move",
        "change_angle",
        "specialist",
    }


def test_fill_gap_requires_and_reports_the_exact_target_family() -> None:
    low_demands = {family: "low" for family in HERO_DEMAND_FAMILIES}
    observed = _hero(1, "Observed", ("carry",), ("initiation",), demands=low_demands)
    exact = _hero(
        2,
        "Map branch",
        ("carry",),
        ("initiation",),
        ("wave_clear",),
        demands=low_demands,
        empirical_support="high",
    )
    wrong_family = _hero(
        3,
        "Damage branch",
        ("carry",),
        ("initiation",),
        ("burst",),
        demands=low_demands,
        empirical_support="high",
    )
    provider = _Provider((observed, exact, wrong_family))

    rationales = recommend_semantic_heroes(
        _matches(1, 1, 1, lane_role=1),
        provider,
        intent="fill_gap",
        target_family="map_objectives",
        limit=3,
    )

    assert [item.hero_id for item in rationales] == [2]
    assert rationales[0].target_family == "map_objectives"
    assert "wave_clear" in rationales[0].adds
    assert all(item.target_family == "map_objectives" for item in rationales)


def test_position_credibility_is_explicit_and_does_not_replace_role_fit() -> None:
    primary = {"1": "unsupported", "2": "unsupported", "3": "primary", "4": "unsupported", "5": "unsupported"}
    observed = _hero(
        1,
        "Observed offlaner",
        ("offlane",),
        ("initiation",),
        demands={family: "low" for family in HERO_DEMAND_FAMILIES},
    )
    candidate = _hero(
        2,
        "Offlane bridge",
        ("offlane",),
        ("initiation",),
        ("wave_clear",),
        demands={family: "low" for family in HERO_DEMAND_FAMILIES},
        empirical_support="high",
        position_credibility=primary,
    )
    provider = _Provider((observed, candidate))
    result = recommend_semantic_heroes(_matches(1, 1, 1, lane_role=3), provider, limit=1)

    assert result and result[0].hero_id == 2
    assert result[0].position_fit == "primary"
    assert set(candidate.position_credibility) == {"1", "2", "3", "4", "5"}
    assert candidate.position_credibility["3"] == "primary"


def test_p04_fill_gap_rationale_matches_the_displayed_primary_family() -> None:
    taxonomy = load_default_taxonomy()
    provider = FullRosterHeroKnowledgeProvider(taxonomy)
    action = build_versatile_core_action(
        _matches(2, 2, 2, 13, 13, 13, lane_role=3),
        taxonomy,
        hero_knowledge=provider,
    )

    assert action.recommended_addition is not None
    rationale = action.recommended_addition.semantic_rationale
    assert rationale is not None
    assert rationale.target_family is not None
    assert action.coverage_summary.family_map[rationale.target_family] == action.coverage_summary.primary_gap
    assert rationale.adds
    assert any(
        function in COVERAGE_FAMILIES[rationale.target_family]["functions"]
        for function in rationale.adds
    )


def test_unknown_demand_families_do_not_become_a_neutral_bridge() -> None:
    observed = _hero(
        1,
        "Observed",
        ("carry",),
        ("initiation",),
        demands={family: "low" for family in HERO_DEMAND_FAMILIES},
    )
    incomplete = _hero(
        2,
        "Incomplete review",
        ("carry",),
        ("initiation", "wave_clear"),
        demands={"commitment": "low", "access": "unknown", "repositioning": "unknown", "economy": "unknown", "timing": "unknown", "execution": "unknown", "exposure": "low", "micro": "low"},
        empirical_support="high",
    )

    result = recommend_semantic_heroes(
        _matches(1, 1, 1, lane_role=1),
        _Provider((observed, incomplete)),
        intent="adjacent_move",
        limit=1,
    )

    assert result == []


def test_full_roster_provider_covers_all_five_intents_beyond_the_pilot() -> None:
    provider = SnapshotHeroKnowledgeProvider()
    familiar_core = _matches(2, 13, 2, 13, 2, 13, lane_role=3)
    support_core = _matches(50, 111, 50, 111, 50, 111, lane_role=3)
    intent_results = {
        "double_down": recommend_semantic_heroes(
            familiar_core, provider, intent="double_down", limit=3
        ),
        "adjacent_move": recommend_semantic_heroes(
            familiar_core, provider, intent="adjacent_move", limit=3
        ),
        "fill_gap": recommend_semantic_heroes(
            _matches(53, 44, 53, 44, 53, 44, lane_role=1),
            provider,
            intent="fill_gap",
            target_family="engage_control",
            limit=3,
        ),
        "change_angle": recommend_semantic_heroes(
            support_core, provider, intent="change_angle", limit=3
        ),
        "specialist": recommend_semantic_heroes(
            support_core, provider, intent="specialist", limit=3
        ),
    }

    assert all(intent_results.values())
    assert all(
        rationale.intent == intent
        for intent, rationales in intent_results.items()
        for rationale in rationales
    )
    assert all(
        provider.get(rationale.hero_id).specialist_markers  # type: ignore[union-attr]
        for rationale in intent_results["specialist"]
    )
    assert all(
        rationale.learning_distance == "high"
        for rationale in intent_results["specialist"]
    )
    pilot_ids = {2, 13, 38, 44, 50, 53, 74, 82, 96, 111}
    surfaced = {
        rationale.hero_id for rationales in intent_results.values() for rationale in rationales
    }
    assert len(surfaced - pilot_ids) >= 5
