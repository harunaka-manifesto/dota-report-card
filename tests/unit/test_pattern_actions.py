from __future__ import annotations

from dataclasses import replace

from app.api.report_schemas import (
    BehaviorPatternSchema,
    BouncebackActionSchema,
    PartialTransferDiagnosticSchema,
    PerformanceSlideActionSchema,
    ProvenFlexibilityActionSchema,
    VersatileCoreActionSchema,
)
from app.behavior.actions import (
    _p03_claim,
    _p03_signal_coverage,
    build_bounceback_action,
    build_comfort_edge_action,
    build_controlled_presence_action,
    build_partial_transfer_action,
    build_performance_slide_action,
    build_presence_tax_action,
    build_proven_flexibility_action,
    build_same_playbook_action,
    build_session_curve_action,
    build_versatile_core_action,
)
from app.heroes.taxonomy import TRAITS, HeroTaxonomy, HeroTaxonomyEntry
from app.ingestion.summary_normalize import normalize_summary_rows


def _taxonomy() -> HeroTaxonomy:
    heroes: dict[int, HeroTaxonomyEntry] = {}
    for hero_id in range(1, 9):
        traits = {trait: 0.10 for trait in TRAITS}
        if hero_id <= 5:
            traits.update(initiation=0.9, frontline=0.85, teamfight=0.8)
        if hero_id == 6:
            traits.update(initiation=0.85, frontline=0.8, mobility=0.85)
        if hero_id == 7:
            traits.update(initiation=0.75, frontline=0.7, save=0.85)
        if hero_id == 8:
            traits.update(initiation=0.7, global_presence=0.9, push=0.9)
        heroes[hero_id] = HeroTaxonomyEntry(
            hero_id=hero_id,
            key=f"hero_{hero_id}",
            name=f"Hero {hero_id}",
            roles=("offlane",),
            traits=traits,
            portrait_url=f"https://example.test/{hero_id}.png",
            provenance={"source": "fixture", "research_file": "fixture", "editorial": "fixture", "review_status": "reviewed"},
        )
    return HeroTaxonomy("actions-fixture", heroes, {})


def _matches(per_hero: int = 12):
    rows = []
    index = 0
    for hero_id in range(1, 6):
        for _ in range(per_hero):
            rows.append(
                {
                    "match_id": 810_000 + index,
                    "start_time": 1_700_000_000 + index * 3_600,
                    "duration": 1_800,
                    "hero_id": hero_id,
                    "player_slot": 0,
                    "radiant_win": index % 3 != 0,
                    "game_mode": 1,
                    "lobby_type": 0,
                    "kills": 7 + hero_id,
                    "deaths": 4 + hero_id % 2,
                    "assists": 12,
                    "lane_role": 3,
                }
            )
            index += 1
    return normalize_summary_rows(rows, account_id=42).matches


def test_same_playbook_action_returns_two_named_directions_without_established_heroes() -> None:
    action = build_same_playbook_action(_matches(), _taxonomy())

    assert action.action_type == "same_playbook"
    assert action.status in {"available", "limited"}
    assert action.dominant_traits
    assert all(item.hero_id not in {1, 2, 3, 4, 5} for item in (*action.deepen, *action.stretch))
    assert all(item.provenance_versions["hero_relationships"] for item in (*action.deepen, *action.stretch))


def test_comfort_edge_action_requires_five_rankable_heroes_and_explains_development_side() -> None:
    action = build_comfort_edge_action(_matches(), _taxonomy())

    assert action.action_type == "comfort_edge"
    assert action.status == "limited"
    assert len(action.ranked_heroes) == 5
    assert action.reference_core_hero_ids == tuple(item.hero_id for item in action.ranked_heroes[:2])
    assert [item.reliability_rank for item in action.development] == [3, 4, 5]
    assert all(item.why_learn for item in action.development)
    assert all(item.reference_core_hero_ids == action.reference_core_hero_ids for item in action.development)


def test_comfort_edge_action_abstains_below_rankability_count() -> None:
    taxonomy = _taxonomy()
    rows = _matches(per_hero=9)

    action = build_comfort_edge_action(rows, taxonomy)

    assert action.status == "unavailable"
    assert action.development == ()


def test_same_playbook_action_round_trips_through_public_pattern_schema() -> None:
    action = build_same_playbook_action(_matches(), _taxonomy())
    pattern = BehaviorPatternSchema.model_validate(
        {
            "key": "same_playbook",
            "label": "Same Playbook",
            "kind": "identity",
            "status": "qualified",
            "direction": "hero_names_change_toolkit_holds",
            "strength": 0.8,
            "relationship_strength": 0.9,
            "confidence": "high",
            "confidence_score": 0.9,
            "evidence_coverage": 0.9,
            "qualification_quality": 0.9,
            "element_keys": ["hero_pool_breadth", "toolkit_breadth"],
            "modifier_element_keys": [],
            "family": "breadth_toolkit",
            "tier": "A",
            "receipts": [],
            "confounders": [],
            "blocking_confounders": [],
            "story_eligibility": "eligible",
            "story_blockers": [],
            "suppression_reasons": [],
            "methodology_version": "free-patterns-5.1.0",
            "action": action.as_dict(),
        }
    )

    assert pattern.action is not None
    assert pattern.action.action_type == "same_playbook"


def test_presence_actions_fall_back_when_no_subgroup_clears_the_qualifying_gates() -> None:
    controlled = build_controlled_presence_action(_matches(), _taxonomy())
    tax = build_presence_tax_action(_matches(), _taxonomy())

    assert controlled.strongest_context is None
    assert controlled.comparison_rows == ()
    assert controlled.fallback_level == "overall"
    assert "positioning" in controlled.limitations[0]
    assert tax.shape in {"job_shaped", "hero_specific", "cross_context", "unresolved"}
    assert tax.comparison_contexts
    assert "cannot establish" in tax.limitations[0]


def test_controlled_presence_can_use_an_overall_fallback_context() -> None:
    rows = tuple(replace(item, deaths=0) for item in _matches())

    action = build_controlled_presence_action(rows, HeroTaxonomy("empty", {}, {}))

    assert action.strongest_context is not None
    assert action.strongest_context.label == "Overall"
    assert action.fallback_level == "overall"


def test_new_p03_p04_p05_actions_round_trip_through_public_schemas() -> None:
    rows = _matches()
    taxonomy = _taxonomy()
    partial_transfer = build_partial_transfer_action(rows, taxonomy)
    versatile_core = build_versatile_core_action(rows, taxonomy)
    proven_flexibility = build_proven_flexibility_action(rows, taxonomy)

    PartialTransferDiagnosticSchema.model_validate(partial_transfer.as_dict())
    VersatileCoreActionSchema.model_validate(versatile_core.as_dict())
    ProvenFlexibilityActionSchema.model_validate(proven_flexibility.as_dict())
    assert proven_flexibility.window_start is not None
    assert proven_flexibility.window_end is not None


def test_every_reviewed_action_exposes_the_common_evidence_envelope() -> None:
    rows = _matches()
    taxonomy = _taxonomy()
    actions = (
        build_same_playbook_action(rows, taxonomy),
        build_comfort_edge_action(rows, taxonomy),
        build_partial_transfer_action(rows, taxonomy),
        build_versatile_core_action(rows, taxonomy),
        build_proven_flexibility_action(rows, taxonomy),
        build_bounceback_action(rows, taxonomy),
        build_performance_slide_action(rows, taxonomy),
        build_controlled_presence_action(rows, taxonomy),
        build_presence_tax_action(rows, taxonomy),
        build_session_curve_action(rows, taxonomy, direction="fade"),
        build_session_curve_action(rows, taxonomy, direction="rise"),
    )
    for action in actions:
        assert action.evidence_summary is not None
        assert action.evidence_summary.status in {"resolved", "fallback", "unresolved", "not_applicable"}
        assert action.evidence_summary.provenance_versions["pattern_actions"]
        assert "evidence_summary" in action.as_dict()


def _transfer_rows(*, per_hero: int = 15, off_pool_deaths: int = 10):
    rows = []
    index = 0
    for hero_id in (4, 1, 2, 3):
        for _ in range(per_hero):
            rows.append(
                {
                    "match_id": 850_000 + index,
                    "start_time": 1_700_000_000 + index * 3_600,
                    "duration": 1_800,
                    "hero_id": hero_id,
                    "player_slot": 0,
                    "radiant_win": True,
                    "game_mode": 1,
                    "lobby_type": 0,
                    "kills": 6,
                    "deaths": off_pool_deaths if hero_id == 4 else 1,
                    "assists": 6,
                    "lane_role": 3,
                }
            )
            index += 1
    return normalize_summary_rows(rows, account_id=42).matches


def test_p03_direct_signal_requires_sample_confidence_coverage_and_keeps_death_copy_literal() -> None:
    action = build_partial_transfer_action(_transfer_rows(), _taxonomy())
    assert action.status == "direct_signal"
    assert action.summary_differences
    assert any(item.signal_key == "death_exposure" for item in action.summary_differences)
    assert all("survivability" not in item.player_facing_claim for item in action.summary_differences)
    assert all("positioning" not in item.player_facing_claim for item in action.summary_differences)

    sample_limited = build_partial_transfer_action(_transfer_rows(per_hero=9), _taxonomy())
    assert not sample_limited.summary_differences

    confidence_limited = build_partial_transfer_action(_transfer_rows(per_hero=12), _taxonomy())
    assert not confidence_limited.summary_differences

    assert _p03_signal_coverage(9, 20, 20, 20) == 0.45
    assert _p03_signal_coverage(10, 10, 10, 10) == 1.0


def test_p03_claims_are_evidence_literal_for_each_direct_signal() -> None:
    claims = {
        key: _p03_claim(key, 0.4)
        for key in ("death_exposure", "combat_involvement", "finisher_orientation", "result_distribution")
    }
    assert "death exposure" in claims["death_exposure"]
    assert all(word not in claim.lower() for claim in claims.values() for word in ("tilt", "mental weakness", "positioning"))


def test_recovery_actions_do_not_bridge_invalid_session_rows() -> None:
    rows = []
    for session_number in range(15):
        base_match_id = 910_000 + session_number * 10
        rows.extend(
            [
                {
                    "match_id": base_match_id,
                    "start_time": 1_800_000_000 + session_number * 100_000,
                    "duration": 1_800,
                    "hero_id": 1,
                    "player_slot": 0,
                    "radiant_win": True,
                    "game_mode": 1,
                    "lobby_type": 0,
                    "kills": 2,
                    "deaths": 2,
                    "assists": 2,
                    "lane_role": 3,
                },
                {
                    "match_id": base_match_id + 1,
                    "start_time": 1_800_000_100 + session_number * 100_000,
                    "duration": 1_800,
                    "hero_id": 1,
                    "player_slot": 0,
                    "radiant_win": True,
                    "game_mode": 1,
                    "lobby_type": 0,
                    "kills": 2,
                    "deaths": 2,
                    "assists": 2,
                    "lane_role": 3,
                },
                {
                    "match_id": base_match_id + 2,
                    "start_time": 1_800_000_200 + session_number * 100_000,
                    "duration": 1_800,
                    "hero_id": 1,
                    "player_slot": 0,
                    "radiant_win": False,
                    "game_mode": 1,
                    "lobby_type": 0,
                    "kills": 2,
                    "deaths": 2,
                    "assists": 2,
                    "lane_role": 3,
                },
                {
                    "match_id": base_match_id + 3,
                    "start_time": 1_800_000_300 + session_number * 100_000,
                    "duration": 300,
                    "hero_id": 1,
                    "player_slot": 0,
                    "radiant_win": True,
                    "game_mode": 1,
                    "lobby_type": 0,
                    "kills": 20,
                    "deaths": 0,
                    "assists": 20,
                    "lane_role": 3,
                },
                {
                    "match_id": base_match_id + 4,
                    "start_time": 1_800_000_400 + session_number * 100_000,
                    "duration": 1_800,
                    "hero_id": 1,
                    "player_slot": 0,
                    "radiant_win": True,
                    "game_mode": 1,
                    "lobby_type": 0,
                    "kills": 20,
                    "deaths": 0,
                    "assists": 20,
                    "lane_role": 3,
                },
            ]
        )
    normalized = normalize_summary_rows(rows, account_id=42).matches
    assigned = [
        item.with_session(f"session-{index // 5 + 1}", index % 5 + 1)
        for index, item in enumerate(normalized)
    ]

    bounceback = build_bounceback_action(assigned, _taxonomy())
    performance_slide = build_performance_slide_action(assigned, _taxonomy())

    assert bounceback.strongest_context is None
    assert performance_slide.strongest_context is None
    BouncebackActionSchema.model_validate(bounceback.as_dict())
    PerformanceSlideActionSchema.model_validate(performance_slide.as_dict())
