from app.behavior.elements.registry import EXPECTED_ELEMENT_KEYS
from app.behavior.outcomes import SEMANTIC_OUTCOME_BRANCHES, SEMANTIC_RECOMMENDATION_BRANCHES
from app.behavior.patterns.registry import EXPECTED_PATTERN_KEYS
from app.behavior.presentation import PATTERN_PRESENTATION_CONTRACT, PatternPresentationPayload
from app.content.catalog import load_free_dna_copy
from app.content.renderer import (
    resolve_element_copy,
    resolve_evolution_copy,
    resolve_page_copy,
    resolve_pattern_copy,
    resolve_pattern_presentation_copy,
    resolve_portfolio_copy,
    validate_copy_catalog,
)
from app.reports.dna_assembly import _pattern_presentation_copy


def test_copy_catalog_covers_every_active_model_entry() -> None:
    catalog = validate_copy_catalog()
    assert set(catalog["elements"]) == set(EXPECTED_ELEMENT_KEYS)
    assert set(catalog["patterns"]) == set(EXPECTED_PATTERN_KEYS)
    assert resolve_element_copy("hero_pool_breadth")["title"] == "Breadth"
    assert resolve_pattern_copy("same_playbook")["title"] == "Same Playbook"


def test_copy_resolvers_require_exact_parameters() -> None:
    assert resolve_page_copy("final_card")["title"] == "The part worth taking with you"
    assert resolve_portfolio_copy("common_thread.question")
    assert (
        resolve_portfolio_copy("exception.no_clear_insight.headline")
        == "Your pool has no odd one out."
    )
    assert "odd-one-out" in resolve_portfolio_copy("exception.no_clear_insight.body")
    assert resolve_evolution_copy("new_heroes_same_toolkit")["heading"] == "New heroes. Same taste."
    try:
        resolve_portfolio_copy("common_thread.answer")
    except ValueError as error:
        assert "trait" in str(error)
    else:
        raise AssertionError("portfolio answer should require its placeholder")


def test_drift_and_recovery_copy_is_plain_language_without_motive_claims() -> None:
    catalog = load_free_dna_copy()
    drift = catalog["elements"]["late_session_performance"]["body"]
    recovery = catalog["elements"]["post_loss_performance_response"]["body"]
    assert "longer sessions" in drift.lower()
    assert "next game" in recovery.lower()
    jargon = ("comparable personal baseline", "bounded summary", "result signal")
    assert all(term not in drift.lower() for term in jargon)
    assert all(term not in recovery.lower() for term in jargon)
    banned = ("fatigue", "warm-up", "tilt", "mental", "resilience", "confidence", "focus")
    assert all(word not in drift.lower() for word in banned)
    assert all(word not in recovery.lower() for word in banned)


def test_every_semantic_outcome_and_recommendation_resolves_to_complete_copy() -> None:
    hero_copy_ids = {
        "HR_DOUBLE_DOWN",
        "HR_ADJACENT_MOVE_ADD_FUNCTION",
        "HR_CHANGE_ANGLE",
        "HR_FILL_GAP_ADD_FUNCTION",
        "HR_SPECIALIST",
    }
    for pattern_key, outcome_ids in SEMANTIC_OUTCOME_BRANCHES.items():
        for outcome_id in outcome_ids:
            params = {}
            if outcome_id in {"P01_NARROW_JOB_BRIDGE_FOUND", "P04_GAP_WITH_BRIDGE"}:
                params["hero_name"] = "Magnus"
            if outcome_id in {"P10_STABLE_BREAKPOINT", "P11_STABLE_BREAKPOINT"}:
                params["session_game_label"] = "Game 4"
            copy = resolve_pattern_presentation_copy(
                pattern_key,
                "unused-by-semantic-resolution",
                semantic_outcome_id=outcome_id,
                params=params,
            )
            assert copy["headline"]
            assert copy["interpretation"]["body"]
            assert copy["fallback"]["body"]

        for recommendation_id in SEMANTIC_RECOMMENDATION_BRANCHES[pattern_key]:
            params = {}
            if outcome_ids[0] in {"P01_NARROW_JOB_BRIDGE_FOUND", "P04_GAP_WITH_BRIDGE"}:
                params["hero_name"] = "Magnus"
            if outcome_ids[0] in {"P10_STABLE_BREAKPOINT", "P11_STABLE_BREAKPOINT"}:
                params["session_game_label"] = "Game 4"
            if recommendation_id in hero_copy_ids:
                params["hero_name"] = "Magnus"
            if recommendation_id == "HR_FILL_GAP_ADD_FUNCTION":
                params.update(function_name="save", familiar_anchor="fight start")
            if recommendation_id == "HR_CHECKPOINT_AT_BREAKPOINT":
                params["session_game_label"] = "Game 4"
            copy = resolve_pattern_presentation_copy(
                pattern_key,
                "unused-by-semantic-resolution",
                semantic_outcome_id=outcome_ids[0],
                semantic_recommendation_id=recommendation_id,
                params=params,
            )
            assert copy["recommendation"]["title"]
            assert "{" not in copy["recommendation"]["body"]


def test_missing_named_candidate_downgrades_to_useful_practice_copy() -> None:
    contract = PATTERN_PRESENTATION_CONTRACT["same_playbook"]
    payload = PatternPresentationPayload(
        pattern_id="same_playbook",
        outcome_id=contract["outcome_id"],
        visual_variant=contract["visual_variant"],
        interpretation_id=contract["interpretation_id"],
        recommendation_id=contract["recommendation_id"],
        semantic_outcome_id="P01_NARROW_JOB_BRIDGE_FOUND",
        semantic_recommendation_id="HR_ADJACENT_MOVE_ADD_FUNCTION",
        recommendation_context={},
    )

    copy = _pattern_presentation_copy(payload)

    assert copy["headline"] == "Your pool keeps solving Dota the same way."
    assert copy["recommendation"]["title"] == "Practice the gap before adding a hero"
    assert "{" not in copy["recommendation"]["body"]
