from __future__ import annotations

from typing import Any

import pytest
from app.player_analysis_v7.research.tables import (
    SESSION_GAP_SECONDS,
    expected_trajectory_length,
    has_role_context,
    is_product_context,
    is_structurally_observable,
    iter_sessions,
    minute_grid_length,
    mode_stratum,
    order_by_time,
    player_networth_lead,
    team_kill_trajectories,
)


def row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "match_id": 1,
        "started_at": 1_000,
        "ended_at": 2_000,
        "duration_seconds": 1_000,
        "game_mode_native": "ALL_PICK_RANKED",
        "lobby_type_native": "RANKED",
        "leaver_status_native": "NONE",
        "position_native": "POSITION_3",
        "role_native": "CORE",
        "lane_native": "OFF_LANE",
        "is_radiant": True,
        "is_victory": True,
        "enum_failure": False,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(1350, 24), (1435, 25), (1556, 27), (3002, 52), (4579, 78), (60, 2)],
)
def test_expected_trajectory_length_matches_observed_corpus_rule(
    duration: int, expected: int
) -> None:
    assert expected_trajectory_length(duration) == expected


def test_minute_grid_clips_an_over_long_trajectory() -> None:
    candidate = row(duration_seconds=1350, radiant_networth_leads=list(range(30)))
    assert minute_grid_length(candidate) == 24


def test_minute_grid_clips_a_short_trajectory() -> None:
    candidate = row(duration_seconds=1350, radiant_networth_leads=[0, 1, 2])
    assert minute_grid_length(candidate) == 3


def test_networth_lead_is_flipped_for_a_dire_player() -> None:
    trajectory = [0, 500, -250]
    radiant = row(duration_seconds=180, is_radiant=True, radiant_networth_leads=trajectory)
    dire = row(duration_seconds=180, is_radiant=False, radiant_networth_leads=trajectory)
    assert player_networth_lead(radiant) == [0, 500, -250]
    assert player_networth_lead(dire) == [0, -500, 250]


def test_networth_lead_fails_closed_without_a_known_side() -> None:
    candidate = row(duration_seconds=180, is_radiant=None, radiant_networth_leads=[0, 1, 2])
    assert player_networth_lead(candidate) is None


def test_team_kill_trajectories_follow_the_player_side() -> None:
    radiant_kills = [0, 2, 1]
    dire_kills = [0, 1, 3]
    dire = row(
        duration_seconds=180,
        is_radiant=False,
        radiant_networth_leads=[0, 0, 0],
        radiant_kills=radiant_kills,
        dire_kills=dire_kills,
    )
    assert team_kill_trajectories(dire) == ([0, 1, 3], [0, 2, 1])


def test_structural_observability_ignores_the_enum_failure_flag() -> None:
    # enum_failure also fires on a missing position/role/lane, which in this
    # corpus means "unparsed". Structural observability must not inherit that.
    unparsed = row(
        enum_failure=True,
        position_native=None,
        role_native=None,
        lane_native=None,
    )
    assert is_structurally_observable(unparsed) is True
    assert is_product_context(unparsed) is True
    assert has_role_context(unparsed) is False


def test_structural_observability_fails_closed_on_unknown_match_context() -> None:
    for field in ("game_mode_native", "lobby_type_native", "leaver_status_native"):
        assert is_structurally_observable(row(**{field: None})) is False
        assert is_structurally_observable(row(**{field: "UNKNOWN"})) is False


@pytest.mark.parametrize("status", ["ABANDONED", "AFK", "DISCONNECTED", "DISCONNECTED_TOO_LONG"])
def test_unfinished_matches_are_outside_product_context(status: str) -> None:
    assert is_product_context(row(leaver_status_native=status)) is False


@pytest.mark.parametrize("lobby", ["PRACTICE", "BATTLE_CUP"])
def test_non_matchmaking_lobbies_are_outside_product_context(lobby: str) -> None:
    assert is_product_context(row(lobby_type_native=lobby)) is False


def test_turbo_is_product_context_but_a_separate_stratum() -> None:
    turbo = row(game_mode_native="TURBO")
    assert is_product_context(turbo) is True
    assert mode_stratum(turbo) == "TURBO"
    assert mode_stratum(row()) == "STANDARD"
    assert mode_stratum(row(game_mode_native="EVENT")) == "UNKNOWN"


def test_unknown_lane_is_not_role_context() -> None:
    assert has_role_context(row(lane_native="UNKNOWN")) is False
    assert has_role_context(row()) is True


def test_sessions_split_on_the_declared_gap() -> None:
    rows = [
        row(match_id=1, started_at=0, ended_at=1_000),
        row(match_id=2, started_at=1_500, ended_at=2_500),
        row(match_id=3, started_at=2_500 + SESSION_GAP_SECONDS + 1, ended_at=3_000),
    ]
    sessions = list(iter_sessions(order_by_time(rows)))
    assert [(session.start_index, session.end_index) for session in sessions] == [(0, 1), (2, 2)]
    assert [session.length for session in sessions] == [2, 1]


def test_a_gap_exactly_at_the_threshold_does_not_break_the_session() -> None:
    rows = [
        row(match_id=1, started_at=0, ended_at=1_000),
        row(match_id=2, started_at=1_000 + SESSION_GAP_SECONDS, ended_at=2_000),
    ]
    assert [session.length for session in iter_sessions(order_by_time(rows))] == [2]


def test_no_rows_yields_no_sessions() -> None:
    assert list(iter_sessions([])) == []


def test_rows_are_ordered_deterministically_when_timestamps_tie() -> None:
    rows = [row(match_id=9, started_at=5), row(match_id=2, started_at=5)]
    assert [candidate["match_id"] for candidate in order_by_time(rows)] == [2, 9]
