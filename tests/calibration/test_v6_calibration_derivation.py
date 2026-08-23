from __future__ import annotations

from app.player_analysis_v6.baselines import BaselineCell, BaselineResolver
from app.player_analysis_v6.calibration_derivation import (
    derive_profile_estimates,
    odd_even_session_ids,
)


def _rows() -> list[dict]:
    rows = []
    starts = {"session-1": 100, "session-2": 200, "session-10": 300}
    match_id = 1
    for sid, start in starts.items():
        for index in range(12):
            rows.append({
                "profile_id": "a" * 64, "match_id": match_id, "hero_id": 1 if match_id <= 22 else 2,
                "start_time": start + index, "duration_seconds": 600, "won": match_id % 2 == 0,
                "kills": 2, "deaths": 1, "assists": 3, "patch": "7.41", "lane_context": "safe_lane",
                "session_id": sid, "session_index": index + 1, "session_corrupt": False,
            })
            match_id += 1
    return rows


def _large_rows() -> list[dict]:
    rows: list[dict] = []
    match_id = 1
    for session in range(1, 17):
        for index in range(4):
            rows.append({
                "profile_id": "a" * 64, "match_id": match_id, "hero_id": 1 if match_id <= 40 else 2,
                "start_time": session * 10_000 + index, "duration_seconds": 600, "won": match_id % 2 == 0,
                "kills": 2, "deaths": 1, "assists": 3, "patch": "7.41", "lane_context": "safe_lane",
                "session_id": f"session-{session}", "session_index": index + 1, "session_corrupt": False,
            })
            match_id += 1
    return rows


def test_odd_even_sessions_use_chronology_not_lexical_ids() -> None:
    odd, even = odd_even_session_ids(_rows())
    assert odd == {"session-1", "session-10"}
    assert even == {"session-2"}


def test_derivation_emits_exactly_19_metrics_without_bootstrap() -> None:
    resolver = BaselineResolver([BaselineCell(
        level="overall", metrics={"involvement_adjusted": 0.25, "finishing_adjusted": 0.4, "death_exposure_adjusted": 1.0},
        match_count=10_000, distinct_players=100,
    )])
    estimates = derive_profile_estimates(
        _large_rows(), baseline_resolver=resolver,
        taxonomy_by_hero={1: {"roles": ["carry"]}, 2: {"roles": ["support"]}},
        completed_sessions={f"session-{index}": True for index in range(1, 17)},
    )
    assert len(estimates.metrics) == 19
    assert estimates.metrics["breadth_effective_count"].value is not None
    assert estimates.metrics["involvement_adjusted"].value == 0.25
    assert estimates.metrics["death_exposure_adjusted"].value == 0.0
