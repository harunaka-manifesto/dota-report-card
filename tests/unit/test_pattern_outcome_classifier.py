from __future__ import annotations

import json
from pathlib import Path

from app.behavior.outcomes import (
    SEMANTIC_OUTCOME_IDS,
    SEMANTIC_RECOMMENDATION_IDS,
    classify_pattern_outcome,
    classify_recommendation_state,
)
from app.behavior.presentation import _safe_semantic_presentation_state

CASES_PATH = Path(__file__).parents[1] / "fixtures/semantic_freeze/pattern-outcome-cases.json"


def test_every_frozen_outcome_branch_is_fixture_reachable_and_registered() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    reached = {classify_pattern_outcome(case["pattern_key"], case["action"]) for case in cases}

    assert reached == SEMANTIC_OUTCOME_IDS


def test_missing_or_ineligible_hero_candidates_have_practice_fallbacks() -> None:
    assert classify_pattern_outcome("same_playbook", {"stretch": []}) == "P01_NARROW_JOB_NO_BRIDGE"
    assert classify_recommendation_state("same_playbook", {"stretch": []}) == "HR_PRACTICE_FALLBACK"
    assert (
        classify_recommendation_state(
            "same_playbook",
            {"stretch": [{"semantic_rationale": {"eligible": False}}]},
        )
        == "HR_PRACTICE_FALLBACK"
    )
    assert (
        classify_recommendation_state(
            "versatile_core",
            {"coverage_summary": {"missing": ["Save"]}},
        )
        == "HR_PRACTICE_FALLBACK"
    )
    assert (
        classify_recommendation_state("partial_transfer", {"status": "unresolved"})
        == "HR_PRACTICE_FALLBACK"
    )


def test_recommendation_ids_are_independent_and_registered() -> None:
    states = {
        classify_recommendation_state(
            "same_playbook",
            {"stretch": [{"semantic_rationale": {"intent": "adjacent_move", "eligible": True}}]},
        ),
        classify_recommendation_state(
            "same_playbook",
            {"deepen": [{"semantic_rationale": {"intent": "double_down", "eligible": True}}]},
        ),
        classify_recommendation_state(
            "versatile_core", {"recommended_addition": {"semantic_rationale": {"eligible": True}}}
        ),
        classify_recommendation_state("partial_transfer", {"status": "capability_hypothesis"}),
    }

    assert states <= SEMANTIC_RECOMMENDATION_IDS
    assert "P01_NARROW_JOB_BRIDGE_FOUND" != "HR_ADJACENT_MOVE_ADD_FUNCTION"


def test_later_eligible_candidate_and_specialist_intent_are_not_lost() -> None:
    action = {
        "stretch": [
            {"semantic_rationale": {"intent": "adjacent_move", "eligible": False}},
            {"semantic_rationale": {"intent": "specialist", "eligible": True}},
        ]
    }

    assert classify_pattern_outcome("same_playbook", action) == "P01_NARROW_JOB_BRIDGE_FOUND"
    assert classify_recommendation_state("same_playbook", action) == "HR_SPECIALIST"


def test_missing_named_candidate_keeps_serialized_ids_on_the_practice_fallback() -> None:
    assert _safe_semantic_presentation_state(
        "P04_GAP_WITH_BRIDGE",
        "HR_FILL_GAP_ADD_FUNCTION",
        {"kind": "practice"},
    ) == ("P04_GAP_NO_BRIDGE", "HR_PRACTICE_FALLBACK")
    assert _safe_semantic_presentation_state(
        "P04_GAP_WITH_BRIDGE",
        "HR_FILL_GAP_ADD_FUNCTION",
        {"kind": "hero", "hero_name": "Tidehunter"},
    ) == ("P04_GAP_WITH_BRIDGE", "HR_FILL_GAP_ADD_FUNCTION")
