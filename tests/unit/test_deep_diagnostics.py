from app.analysis.deep_scan import plan_diagnostic_deep_scan
from app.features.summary_calculators import calculate_summary_features


def _summary(index: int, *, hero_id: int = 1) -> dict[str, object]:
    return {
        "match_id": index,
        "start_time": 1_700_000_000 + index * 3_600,
        "duration": 1_800,
        "game_mode": 1,
        "lobby_type": 7,
        "radiant_win": index % 2 == 0,
        "player_slot": 0,
        "hero_id": hero_id,
        "lane_role": 3,
        "leaver_status": 0,
    }


def test_diagnostic_plan_has_one_primary_and_only_high_reuse_secondary() -> None:
    features = calculate_summary_features([_summary(index) for index in range(1, 31)], account_id=42)
    question = {
        "diagnostic_question_id": "q-transfer",
        "statement": "Does this transfer beyond your signature hero?",
        "primary_hypothesis": {
            "hypothesis_id": "transfer-primary",
            "required_data_families": ["summary", "events"],
        },
        "secondary_hypothesis": {
            "hypothesis_id": "transfer-secondary",
            "required_data_families": ["summary"],
        },
        "secondary_reuse_fraction": 0.49,
    }
    hypotheses, plan = plan_diagnostic_deep_scan(question, features)
    assert [item.hypothesis_id for item in hypotheses] == ["transfer-primary"]
    assert len(plan.selected) <= 25
    assert all(item.candidate.estimated_detail_cost <= 1 for item in plan.selected)
    assert sum(item.candidate.estimated_parse_cost for item in plan.selected) <= 125
    assert plan.stopping_reason

    question["secondary_reuse_fraction"] = 0.5
    hypotheses, _ = plan_diagnostic_deep_scan(question, features)
    assert [item.hypothesis_id for item in hypotheses] == [
        "transfer-primary",
        "transfer-secondary",
    ]


def test_diagnostic_plan_prefers_cached_families_and_persists_abstention_reason() -> None:
    features = calculate_summary_features([_summary(index) for index in range(1, 16)], account_id=42)
    question = {
        "diagnostic_question_id": "q-cached",
        "primary_hypothesis": {
            "hypothesis_id": "cached-primary",
            "required_data_families": ["summary", "events"],
        },
    }
    available = {index: frozenset({"summary", "events"}) for index in range(1, 4)}
    _, plan = plan_diagnostic_deep_scan(
        question,
        features,
        available_families_by_match=available,
        max_deep_matches=1,
    )
    assert plan.selected[0].candidate.already_available
    assert plan.selected[0].candidate.estimated_detail_cost == 0
    assert plan.selected[0].candidate.estimated_parse_cost == 0

