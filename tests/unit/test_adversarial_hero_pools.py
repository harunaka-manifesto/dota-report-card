from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from app.behavior.actions import build_versatile_core_action
from app.behavior.outcomes import classify_pattern_outcome, classify_recommendation_state
from app.content.renderer import resolve_pattern_presentation_copy
from app.hero_portfolio.common_thread import compute_common_thread
from app.hero_portfolio.config import PORTFOLIO_CONFIG
from app.hero_portfolio.eligibility import build_hero_eligibility
from app.hero_portfolio.exception import compute_hero_exception
from app.heroes.knowledge import (
    DOTA_POSITIONS,
    HERO_DEMAND_FAMILIES,
    POSITION_CREDIBILITY_BANDS,
    NormalizedHeroKnowledge,
    SnapshotHeroKnowledgeProvider,
)
from app.heroes.recommendations import recommend_semantic_heroes
from app.heroes.relationships import build_semantic_pool_profile
from app.heroes.taxonomy import load_default_taxonomy
from app.ingestion.summary_normalize import normalize_summary_rows

ROOT = Path(__file__).parents[2]
REGISTRY_PATH = ROOT / "tests/fixtures/adversarial/hero-pools.json"
REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
CASES = tuple(REGISTRY["cases"])
CASE_BY_KEY = {case["key"]: case for case in CASES}


@dataclass(frozen=True)
class _Provider:
    entries: tuple[NormalizedHeroKnowledge, ...]
    version: str = "hero-knowledge-adversarial-fixture"

    def get(self, hero_id: int | None) -> NormalizedHeroKnowledge | None:
        return next((entry for entry in self.entries if entry.hero_id == hero_id), None)


def _matches(
    hero_ids: tuple[int, ...],
    lane_roles: tuple[int, ...],
    *,
    repeats: int = 8,
) -> tuple[Any, ...]:
    rows: list[dict[str, Any]] = []
    match_id = 0
    for hero_id, lane_role in zip(hero_ids, lane_roles, strict=True):
        for _ in range(repeats):
            match_id += 1
            rows.append(
                {
                    "match_id": match_id,
                    "start_time": 1_800_000_000 + match_id * 100,
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
            )
    return normalize_summary_rows(rows, account_id=42).matches


def _case_matches(case: dict[str, Any], *, repeats: int = 8) -> tuple[Any, ...]:
    return _matches(tuple(case["hero_ids"]), tuple(case["lane_roles"]), repeats=repeats)


def _fixture_hero(
    hero_id: int,
    name: str,
    roles: tuple[str, ...],
    primary: tuple[str, ...],
    secondary: tuple[str, ...] = (),
    *,
    demands: dict[str, str] | None = None,
    confidence: str = "high",
    empirical_support: str = "high",
    specialist_markers: tuple[str, ...] = (),
) -> NormalizedHeroKnowledge:
    demand_map = demands or {family: "low" for family in HERO_DEMAND_FAMILIES}
    return NormalizedHeroKnowledge(
        hero_id=hero_id,
        display_name=name,
        roles=roles,
        functional_jobs=primary + secondary,
        provenance_versions={"hero_knowledge": "hero-knowledge-adversarial-fixture"},
        primary_functions=primary,
        secondary_functions=secondary,
        demands=demand_map,
        capabilities={job: "high" for job in primary + secondary},
        empirical_support=empirical_support,
        confidence=confidence,
        evidence_refs=(f"fixture:adversarial:{hero_id}",),
        review_status="approved",
        specialist_markers=specialist_markers,
    )


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _strings(item)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _strings(item)]
    return []


@pytest.mark.parametrize("case", CASES, ids=[case["key"] for case in CASES])
def test_adversarial_registry_cases_replay_against_reviewed_semantics(case: dict[str, Any]) -> None:
    provider = SnapshotHeroKnowledgeProvider()
    matches = _case_matches(case)
    known_ids = {entry.hero_id for entry in provider.entries}
    profile = build_semantic_pool_profile(matches, provider)

    assert len(case["hero_ids"]) == len(case["lane_roles"])
    assert set(profile.hero_ids) <= known_ids
    assert set(profile.functional_families) <= {
        "engage_control",
        "frontline_protection",
        "damage_finish",
        "map_objectives",
        "mobility_reach",
    }
    if "unknown_heroes_fail_closed" in case["assertions"]:
        unknown_ids = set(case["hero_ids"]) - known_ids
        assert unknown_ids
        assert unknown_ids.isdisjoint(profile.hero_ids)
        assert profile.semantic_coverage < 1.0


def test_magnus_techies_marci_never_get_broad_p04_copy_without_a_gap() -> None:
    case = CASE_BY_KEY["compact_magnus_techies_marci"]
    provider = SnapshotHeroKnowledgeProvider()
    taxonomy = load_default_taxonomy()
    action = build_versatile_core_action(
        _case_matches(case),
        taxonomy,
        hero_knowledge=provider,
    )
    action_dict = action.as_dict()
    coverage = action.coverage_summary
    gap_families = (
        *coverage.missing,
        *coverage.thin_coverage,
        *coverage.single_point_coverage,
    )

    assert gap_families, "The compact known case must expose an exact family gap or thin spot."
    semantic_outcome = classify_pattern_outcome("versatile_core", action_dict)
    assert semantic_outcome != "P04_NO_MEANINGFUL_GAP"

    recommendation = action.recommended_addition
    if recommendation is None:
        assert coverage.primary_gap
        assert any("candidate" in limitation.lower() or "gap" in limitation.lower() for limitation in action.limitations)
        semantic_recommendation = None
    else:
        rationale = recommendation.semantic_rationale
        assert rationale is not None
        assert rationale.target_family is not None
        assert coverage.family_map[rationale.target_family] == coverage.primary_gap
        semantic_recommendation = classify_recommendation_state("versatile_core", action_dict)

    params: dict[str, str] = {}
    copy_outcome = semantic_outcome
    if recommendation is not None:
        params["hero_name"] = recommendation.hero_name
        params["function_name"] = recommendation.adds_jobs[0] if recommendation.adds_jobs else coverage.primary_gap or "the missing job"
        params["familiar_anchor"] = recommendation.shared_anchors[0] if recommendation.shared_anchors else "a familiar job"
    elif semantic_outcome == "P04_GAP_WITH_BRIDGE":
        copy_outcome = "P04_GAP_NO_BRIDGE"
    copy = resolve_pattern_presentation_copy(
        "versatile_core",
        "P04_COMPACT_POOL_BROAD_JOBS",
        semantic_outcome_id=copy_outcome,
        semantic_recommendation_id=semantic_recommendation,
        params=params,
    )
    assert "already covers the important jobs" not in " ".join(_strings(copy)).lower()


def test_registry_role_cases_keep_role_fit_and_position_credibility_explicit() -> None:
    provider = SnapshotHeroKnowledgeProvider()
    for key in ("support_heavy", "carry_heavy", "role_switching_player"):
        case = CASE_BY_KEY[key]
        for hero_id in case["hero_ids"]:
            entry = provider.get(hero_id)
            assert entry is not None
            assert set(entry.position_credibility) == set(DOTA_POSITIONS)
            assert set(entry.position_credibility.values()) <= POSITION_CREDIBILITY_BANDS

    observed = _fixture_hero(1, "Observed carry", ("carry",), ("initiation",))
    support_candidate = _fixture_hero(
        2,
        "Support bridge",
        ("hard_support", "soft_support"),
        ("initiation",),
        ("save",),
    )
    carry_candidate = _fixture_hero(3, "Carry mismatch", ("carry",), ("initiation",), ("save",))
    fixture_provider = _Provider((observed, support_candidate, carry_candidate))
    matches = _matches((1, 1), (1, 1), repeats=1)
    recommendations = recommend_semantic_heroes(
        matches,
        fixture_provider,
        intent="double_down",
        limit=3,
    )

    assert recommendations
    support = next(item for item in recommendations if item.hero_id == 2)
    assert support.role_fit == "conditional"
    assert support.position_fit == "unknown"
    assert all(item.hero_id != 3 for item in recommendations)


def test_specialist_intent_requires_a_visible_learning_jump() -> None:
    low_demands = {family: "low" for family in HERO_DEMAND_FAMILIES}
    observed = _fixture_hero(1, "Observed anchor", ("carry",), ("initiation", "catch"), demands=low_demands)
    specialist = _fixture_hero(
        2,
        "Deliberate specialist",
        ("carry",),
        ("initiation", "catch"),
        demands={**low_demands, "economy": "high", "execution": "high", "micro": "high"},
        specialist_markers=("economy", "execution", "micro"),
    )
    recommendations = recommend_semantic_heroes(
        _matches((1, 1, 1, 1), (1, 1, 1, 1), repeats=1),
        _Provider((observed, specialist)),
        intent="specialist",
        limit=1,
    )

    assert recommendations
    result = recommendations[0]
    assert result.hero_id == 2
    assert result.intent == "specialist"
    assert result.eligible is True
    assert result.learning_distance == "high"
    assert set(result.new_demands) >= {"economy", "execution", "micro"}


def test_carry_case_exposes_economy_as_a_demand_not_a_similarity_reason() -> None:
    case = CASE_BY_KEY["carry_heavy"]
    provider = SnapshotHeroKnowledgeProvider()
    action = build_versatile_core_action(
        _case_matches(case),
        load_default_taxonomy(),
        hero_knowledge=provider,
    )
    serialized = action.as_dict()

    for hero_id in case["hero_ids"]:
        entry = provider.get(hero_id)
        assert entry is not None
        assert entry.demands.get("economy") in {"low", "medium", "high", "unknown"}
    assert "similarity" not in " ".join(_strings(serialized)).lower()


def test_no_functional_outlier_has_no_quiz_or_null_state_language() -> None:
    case = CASE_BY_KEY["no_functional_outlier"]
    provider = SnapshotHeroKnowledgeProvider()
    matches = _case_matches(case)
    taxonomy = load_default_taxonomy()
    common = compute_common_thread(matches, taxonomy, hero_knowledge=provider)
    exception = compute_hero_exception(matches, taxonomy, hero_knowledge=provider)

    assert common.status == "no_clear_thread"
    assert common.correct_option_key is None
    assert common.options == ()
    assert exception.status == "no_clear_exception"
    assert exception.hero_id is None
    assert exception.correct_option_key == "no_clear_exception"
    assert exception.options == ()
    assert all("null" not in text.lower() and "none" not in text.lower() for text in _strings(exception.as_dict()))


def test_one_functional_outlier_requires_distance_and_margin_and_is_not_called_bad() -> None:
    case = CASE_BY_KEY["one_functional_outlier"]
    result = compute_hero_exception(
        _case_matches(case),
        load_default_taxonomy(),
        hero_knowledge=SnapshotHeroKnowledgeProvider(),
    )

    assert result.status in {"available", "no_clear_exception"}
    if result.status == "available":
        assert result.hero_id is not None
        assert result.distance is not None and result.distance >= PORTFOLIO_CONFIG.exception_min_distance
        assert result.margin is not None and result.margin >= PORTFOLIO_CONFIG.exception_min_margin
    else:
        assert result.hero_id is None
        assert result.correct_option_key == "no_clear_exception"
    assert "bad" not in " ".join(_strings(result.as_dict())).lower()


def test_unknown_heroes_fail_closed_across_portfolio_and_semantic_actions() -> None:
    case = CASE_BY_KEY["sparse_semantic_coverage"]
    provider = SnapshotHeroKnowledgeProvider()
    taxonomy = load_default_taxonomy()
    matches = _case_matches(case)
    eligibility = build_hero_eligibility(matches, taxonomy, hero_knowledge=provider)
    by_id = {item.hero_id: item for item in eligibility}

    for hero_id in (999, 1000):
        assert by_id[hero_id].coverage == 0.0
        assert by_id[hero_id].eligible_for_common_thread is False
        assert by_id[hero_id].eligible_for_exception is False
        assert "hero_semantics_unavailable" in by_id[hero_id].exclusion_reasons

    common = compute_common_thread(matches, taxonomy, hero_knowledge=provider)
    exception = compute_hero_exception(matches, taxonomy, hero_knowledge=provider)
    action = build_versatile_core_action(matches, taxonomy, hero_knowledge=provider)
    assert common.status == "unavailable"
    assert common.options == ()
    assert exception.status == "unavailable"
    assert exception.options == ()
    assert 999 not in action.core_hero_ids and 1000 not in action.core_hero_ids
    assert all(item.hero_id not in {999, 1000} for item in action.alternative_additions)
