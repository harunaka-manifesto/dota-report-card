from __future__ import annotations

from app.analysis.budget import BudgetState, CostPolicy, DataCostLedger
from app.analysis.deep_scan import plan_deep_scan
from app.dna.sessions import infer_sessions
from app.features.summary_calculators import calculate_summary_features
from app.ingestion.coverage import ParseCoverage, has_required_families, missing_required_families
from app.ingestion.summary_normalize import normalize_summary_rows
from app.patterns.detector import detect_patterns


def _summary(
    match_id: int,
    *,
    start_time: int,
    hero_id: int,
    won: bool,
    duration: int = 1800,
) -> dict[str, object]:
    return {
        "match_id": match_id,
        "start_time": start_time,
        "duration": duration,
        "game_mode": 1,
        "lobby_type": 7,
        "radiant_win": won,
        "player_slot": 0,
        "hero_id": hero_id,
        "lane_role": 3,
        "leaver_status": 0,
    }


def test_summary_fields_stay_nullable_and_sessionization_is_order_invariant() -> None:
    rows = [
        _summary(2, start_time=2_000, hero_id=2, won=False),
        _summary(1, start_time=1_000, hero_id=1, won=True),
        _summary(3, start_time=8_000, hero_id=1, won=True),
    ]
    rows[0].pop("lane_role")
    rows[0].pop("hero_id")
    rows[0]["hero_id"] = 2
    first = calculate_summary_features(rows, account_id=42, session_gap_minutes=60)
    second = calculate_summary_features(list(reversed(rows)), account_id=42, session_gap_minutes=60)

    assert first.as_dict() == second.as_dict()
    assert first.matches[0].match_id == 1
    assert first.matches[0].kills is None
    assert first.matches[0].gold_per_min is None
    assert [session.match_ids for session in first.sessions] == [(1, 2), (3,)]
    assert first.matches[1].session_index == 2


def test_session_gap_boundary_midnight_and_undated_rows_are_deterministic() -> None:
    first_start = 1_704_153_540  # 2024-01-01 23:59 UTC
    rows = [
        _summary(1, start_time=first_start, hero_id=1, won=True),
        # Queue gap is exactly 90 minutes, so the second match stays in-session.
        _summary(2, start_time=first_start + 1_800 + 90 * 60, hero_id=2, won=False),
        # One second beyond the threshold starts a new session.
        _summary(3, start_time=first_start + 1_800 + 90 * 60 + 1_800 + 90 * 60 + 1, hero_id=3, won=True),
        # A missing timestamp is retained for non-session dimensions but never
        # bridges or joins a dated session.
        _summary(4, start_time=first_start, hero_id=4, won=True),
    ]
    rows[-1]["start_time"] = None  # type: ignore[assignment]

    normalized = normalize_summary_rows(rows, account_id=42)
    session_result = infer_sessions(normalized.matches)

    assert [session.match_ids for session in session_result.sessions] == [(1, 2), (3,)]
    assert session_result.matches[-1].session_id is None


def test_summary_detector_finds_hero_overperformance_without_detail_data() -> None:
    rows = [
        _summary(index, start_time=1_700_000_000 + index * 3_600, hero_id=1, won=index <= 9)
        for index in range(1, 11)
    ]
    rows.extend(
        _summary(index, start_time=1_700_100_000 + index * 3_600, hero_id=2, won=False)
        for index in range(11, 21)
    )
    feature_set = calculate_summary_features(rows, account_id=42)
    patterns = detect_patterns(feature_set)

    hero = next(item for item in patterns if item.pattern_id == "hero_overperformance")
    assert hero.subject == {"hero_id": 1}
    assert hero.unexplained
    assert hero.sample_size == 10


def test_global_selector_deduplicates_and_rewards_multi_hypothesis_matches() -> None:
    rows = [
        _summary(index, start_time=1_700_000_000 + index * 3_600, hero_id=1, won=index <= 9)
        for index in range(1, 11)
    ]
    rows.extend(
        _summary(index, start_time=1_700_100_000 + index * 3_600, hero_id=2, won=index >= 19)
        for index in range(11, 21)
    )
    feature_set = calculate_summary_features(rows, account_id=42)
    patterns = detect_patterns(feature_set)
    _, plan = plan_deep_scan(
        patterns,
        feature_set,
        max_primary_hypotheses=3,
        max_deep_matches=25,
        max_data_cost=25,
        min_marginal_information_gain=0.05,
    )

    selected_ids = plan.selected_match_ids
    assert len(selected_ids) == len(set(selected_ids))
    assert len(selected_ids) <= 25
    assert plan.selected
    assert len(plan.selected[0].newly_supported_needs) >= 2
    assert plan.stopping_reason in {"marginal_gain_exhausted", "evidence_sufficient"}


def test_coverage_checks_specific_evidence_families() -> None:
    coverage = ParseCoverage(
        by_family={"summary": 1.0, "events": 1.0, "time_series": 0.0},
        parser_version=7,
    )

    assert has_required_families(coverage, ("summary", "events"))
    assert not has_required_families(coverage, ("events", "time_series"))
    assert missing_required_families(coverage, ("events", "time_series")) == {"time_series"}


def test_cost_ledger_and_budget_are_independent_of_monetary_pricing() -> None:
    policy = CostPolicy(detail_read_units=2.0, parse_request_units=5.0)
    ledger = DataCostLedger()
    ledger.record("detail", policy=policy, match_id=1)
    ledger.record("detail", policy=policy, match_id=2, existing=True, units=0.0)
    assert ledger.detail_requests == 1
    assert ledger.existing_deep_matches == 1
    assert ledger.estimated_cost_units == 2.0

    budget = BudgetState(max_parse_requests=1, max_data_cost_per_report=5.0)
    assert budget.can_spend("parse", 5.0).allowed
    assert budget.spend("parse", 5.0).allowed
    assert not budget.can_spend("parse", 5.0).allowed
