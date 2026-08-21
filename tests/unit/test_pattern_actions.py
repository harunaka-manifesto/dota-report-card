from __future__ import annotations

from app.api.report_schemas import BehaviorPatternSchema
from app.behavior.actions import build_comfort_edge_action, build_same_playbook_action
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
            "methodology_version": "free-patterns-4.0.0",
            "action": action.as_dict(),
        }
    )

    assert pattern.action is not None
    assert pattern.action.action_type == "same_playbook"
