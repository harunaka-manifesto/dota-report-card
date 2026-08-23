from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.player_analysis_v6 import (
    PUBLIC_ELEMENT_KEYS,
    STORY_BEAT_KEYS,
    BaselineCell,
    BaselineContext,
    BaselineResolver,
    FreeCostLedger,
    InsufficientHistoryError,
    analyze_free_dna_v6,
    benjamini_hochberg,
    build_diagnostic_questions,
    build_share_candidates,
    clustered_bootstrap,
    compare_consistency_signals,
    compare_transfer_signals,
    finishing_share,
    shannon_effective_count,
)


def _match(index: int, *, session: int | None = None, hero: int | None = None) -> SimpleNamespace:
    start = 1_700_000_000 + index * 7_200
    return SimpleNamespace(
        match_id=index,
        hero_id=hero or (index % 4) + 1,
        started_at=start,
        duration_seconds=1_800,
        kills=3 + index % 3,
        deaths=2 + index % 2,
        assists=5 + index % 4,
        won=index % 2 == 0,
        role_hint="mid",
        session_id=f"session-{session or index}",
    )


def test_shannon_and_zero_event_formulas() -> None:
    assert shannon_effective_count({"a": 5, "b": 5}) == pytest.approx(2.0)
    assert finishing_share(0, 0) is None
    assert finishing_share(2, 2) == pytest.approx(0.5)


def test_cluster_bootstrap_is_session_clustered_and_deterministic() -> None:
    first = clustered_bootstrap({"s1": [0, 0, 0], "s2": [1, 1, 1]}, iterations=200, seed=4)
    second = clustered_bootstrap({"s1": [0, 0, 0], "s2": [1, 1, 1]}, iterations=200, seed=4)
    assert first == second
    assert first.independent_sessions == 2
    assert first.sample_size == 6


def test_baseline_fallback_requires_counts() -> None:
    cells = [
        BaselineCell("patch+hero+lane", patch="7.41", hero_id=1, lane_context="mid", metrics={"m": 5}, match_count=100, distinct_players=50),
        BaselineCell("patch+hero", patch="7.41", hero_id=1, metrics={"m": 7}, match_count=200, distinct_players=50),
    ]
    resolved = BaselineResolver(cells).resolve(BaselineContext("7.41", 1, lane_context="mid"), "m")
    assert resolved.level == "patch+hero"
    assert resolved.value == 7


def test_mixed_transfer_and_consistency_remain_mixed_or_two_of_three() -> None:
    transfer = compare_transfer_signals({"outcome": 0.2, "activity": 0.2, "survival": -0.2})
    assert transfer.direction == "mixed"
    consistency = compare_consistency_signals({"outcome": "stable", "activity": "variable", "death_exposure": "stable"}, usable_sessions=12)
    assert consistency.direction == "stable"


def test_bh_adjustment() -> None:
    assert benjamini_hochberg([0.01, 0.04, 0.2]) == pytest.approx((0.03, 0.06, 0.2))


def test_v6_report_contract_and_free_cost() -> None:
    matches = tuple(_match(index, session=index // 2) for index in range(60))
    report = analyze_free_dna_v6(matches, taxonomy_by_hero={1: ("teamfight",), 2: ("save",), 3: ("push",), 4: ("scaling",)})
    assert tuple(item.key for item in report.elements) == PUBLIC_ELEMENT_KEYS
    assert len(report.findings) == 5
    assert len(report.story) == 9
    assert tuple(item.key for item in report.story) == STORY_BEAT_KEYS
    assert sum(item.published for item in report.findings) <= 3
    assert report.cost == FreeCostLedger(history_reads=1)
    public = report.as_dict()
    assert not any("pos1" in repr(public).lower() for _ in [0])


def test_diagnostic_questions_and_share_candidates_are_gated() -> None:
    matches = tuple(_match(index, session=index // 2) for index in range(60))
    report = analyze_free_dna_v6(matches, taxonomy_by_hero={1: ("teamfight",), 2: ("save",), 3: ("push",), 4: ("scaling",)})
    assert len(build_diagnostic_questions(report.findings)) <= 3
    assert len(build_share_candidates(report.identity, report.findings)) == 3


def test_free_history_floor_is_enforced() -> None:
    with pytest.raises(InsufficientHistoryError):
        analyze_free_dna_v6(tuple(_match(index) for index in range(29)))
