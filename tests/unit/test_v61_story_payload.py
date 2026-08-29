from __future__ import annotations

from datetime import UTC, datetime

from app.player_analysis_v61.story_payload import (
    build_busiest_day_module,
    build_busiest_week_module,
    build_hero_era_payoff_module,
    build_hero_eras_module,
    build_hero_pool_module,
    build_hours_module,
    build_kills_module,
    build_longest_match_module,
    build_losing_streak_module,
    build_rank_points_module,
    build_story_modules,
    build_top_loss_heroes_module,
    build_top_win_heroes_module,
    build_win_summary_module,
    build_winning_streak_module,
)


def _ts(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())


def _row(
    match_id: int,
    when: str,
    *,
    hero_id: int = 1,
    won: bool = True,
    duration: int | None = 1_800,
    game_mode: int = 1,
    lobby_type: int = 0,
    kills: int | None = 2,
    deaths: int | None = 1,
    assists: int | None = 3,
) -> dict[str, object]:
    return {
        "match_id": match_id,
        "started_at": _ts(when),
        "hero_id": hero_id,
        "won": won,
        "duration_seconds": duration,
        "game_mode": game_mode,
        "lobby_type": lobby_type,
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
    }


HEROES = {
    1: {"display_name": "Anti-Mage"},
    2: {"display_name": "Axe"},
    3: {"display_name": "Bane"},
}


def test_complete_story_module_map_uses_typed_state_boundary_and_excludes_death_context() -> None:
    modules = build_story_modules([_row(1, "2026-01-01T12:00:00+00:00")], hero_metadata=HEROES)

    assert set(modules) == {
        "hello",
        "match_count",
        "hours_in_matches",
        "rank_points",
        "busiest_week",
        "busiest_day",
        "longest_match",
        "wins_bridge",
        "win_summary",
        "winning_streak",
        "top_win_heroes",
        "losing_streak",
        "top_loss_heroes",
        "hero_pool",
        "hero_eras",
        "hero_era_payoff",
        "kills",
        "assists",
        "deaths",
        "element_distinctiveness",
        "archetype",
        "card_collage",
        "final_identity_card",
        "deep",
    }
    assert all(set(module) == {"state", "reason", "copy_variant", "data"} for module in modules.values())
    assert all(module["state"] in {"available", "degraded", "omitted", "not_ready"} for module in modules.values())
    assert all(
        module["data"] is not None
        for module in modules.values()
        if module["state"] in {"available", "degraded"}
    )
    assert all(
        module["data"] is None
        for module in modules.values()
        if module["state"] == "omitted"
    )
    assert "death_context" not in modules
    assert modules["element_distinctiveness"]["state"] == "not_ready"
    assert modules["archetype"]["state"] == "not_ready"
    assert modules["archetype"]["data"]["production_ready"] is False
    assert modules["card_collage"]["state"] == "omitted"
    assert modules["deep"]["state"] == "degraded"
    assert modules["deep"]["data"] == {"available": False}


def test_active_story_modules_include_hello_and_match_count_facts() -> None:
    rows = [_row(index, f"2026-01-{(index % 28) + 1:02d}T00:00:00+00:00") for index in range(1, 31)]

    modules = build_story_modules(
        rows,
        hero_metadata=HEROES,
        display_name="Story Player",
        window_start=_ts("2025-01-01T00:00:00+00:00"),
        window_end=_ts("2025-12-31T23:59:59+00:00"),
    )

    assert modules["hello"]["state"] == "available"
    assert modules["hello"]["data"]["display_name"] == "Story Player"
    assert modules["hello"]["data"]["window_start"] == "2025-01-01"
    assert modules["hello"]["data"]["window_end"] == "2025-12-31"
    assert modules["match_count"] == {
        "state": "available",
        "reason": None,
        "copy_variant": "limited",
        "data": {"match_count": 30, "volume_variant": "limited"},
    }


def test_hello_short_history_uses_observed_span_not_requested_window() -> None:
    rows = [
        _row(index, f"2026-01-{index:02d}T00:00:00+00:00")
        for index in range(1, 31)
    ]

    modules = build_story_modules(
        rows,
        window_start=_ts("2025-01-01T00:00:00+00:00"),
        window_end=_ts("2025-12-31T23:59:59+00:00"),
    )

    assert modules["hello"]["data"]["history_materially_short"] is True
    assert modules["hello"]["copy_variant"] == "anonymous_short"


def test_hours_use_utc_and_round_minutes_then_decimal_then_whole_hours() -> None:
    rows = [
        _row(1, "2026-01-01T23:59:00+00:00", duration=59 * 60 + 31),
        _row(2, "2026-01-02T00:01:00+00:00", duration=3_600),
    ]

    module = build_hours_module(rows)

    assert module["state"] == "available"
    assert module["data"]["total_duration_seconds"] == 7_171
    assert module["data"]["display_value"] == 2.0
    assert module["data"]["display_unit"] == "hours"
    assert module["data"]["hours_available"] is True
    assert module["data"]["coverage_numerator"] == 2
    assert module["data"]["coverage_denominator"] == 2
    assert module["data"]["coverage_ratio"] == 1.0

    assert build_hours_module([_row(1, "2026-01-01T00:00:00+00:00", duration=29 * 60 + 31)])["data"]["display_value"] == 30


def test_hours_omit_below_ninety_five_percent_while_periods_degrade() -> None:
    rows = [
        _row(index, "2026-02-01T00:00:00+00:00", duration=None if index <= 2 else 3_600)
        for index in range(1, 21)
    ]

    hours = build_hours_module(rows)
    assert hours["state"] == "omitted"
    assert hours["reason"] == "duration_coverage_below_threshold"
    assert hours["data"] is None

    week = build_busiest_week_module(rows)
    day = build_busiest_day_module(rows, busiest_week=week)
    assert week["state"] == "degraded"
    assert day["state"] == "degraded"
    assert week["data"]["match_count"] == 20
    assert day["data"]["match_count"] == 20


def test_busiest_week_and_day_use_iso_utc_ties_and_day_threshold() -> None:
    rows = [
        _row(10, "2026-01-05T00:01:00+00:00"),
        _row(11, "2026-01-06T00:01:00+00:00"),
        _row(12, "2026-01-14T00:01:00+00:00"),
        _row(13, "2026-01-14T01:01:00+00:00"),
        _row(14, "2026-01-14T02:01:00+00:00"),
    ]

    week = build_busiest_week_module(rows)
    day = build_busiest_day_module(rows, busiest_week=week)

    assert week["data"]["date_start"] == "2026-01-12"
    assert week["data"]["date_end"] == "2026-01-18"
    assert day["data"]["date"] == "2026-01-14"
    assert day["data"]["inside_busiest_week"] is True
    assert build_busiest_day_module(rows[:2])["state"] == "omitted"


def test_rank_points_accept_only_ranked_all_pick_and_captains_mode() -> None:
    rows = [
        _row(index, f"2026-01-{index:02d}T00:00:00+00:00", won=index <= 6, game_mode=22, lobby_type=7)
        for index in range(1, 11)
    ]
    rows.extend(
        [
            _row(20, "2026-02-01T00:00:00+00:00", game_mode=2, lobby_type=7),
            _row(21, "2026-02-02T00:00:00+00:00", game_mode=22, lobby_type=0),
            _row(22, "2026-02-03T00:00:00+00:00", game_mode=99, lobby_type=7),
        ]
    )

    module = build_rank_points_module(rows)

    assert module["state"] == "available"
    assert module["data"]["ranked_matches"] == 11
    assert module["data"]["ranked_wins"] == 7
    assert module["data"]["ranked_losses"] == 4
    assert module["data"]["points_absolute"] == 75
    assert module["data"]["direction"] == "positive"
    assert build_rank_points_module(rows, mode_map_valid=False)["state"] == "omitted"


def test_longest_requires_full_duration_and_known_selected_hero() -> None:
    rows = [
        _row(1, "2026-01-01T00:00:00+00:00", hero_id=1, duration=3_599),
        _row(2, "2026-01-02T00:00:00+00:00", hero_id=2, duration=3_600),
    ]

    module = build_longest_match_module(rows, hero_metadata=HEROES, busiest_day="2026-01-02")

    assert module["state"] == "available"
    assert module["data"]["hero_name"] == "Axe"
    assert module["data"]["formatted_duration"] == "1h 00m"
    assert module["data"]["refused_to_end"] is True
    assert module["data"]["on_busiest_day"] is True
    assert build_longest_match_module(
        [_row(1, "2026-01-01T00:00:00+00:00", duration=None)], hero_metadata=HEROES
    )["state"] == "omitted"
    assert build_longest_match_module(rows)["state"] == "omitted"


def test_win_loss_streak_ties_choose_latest_and_preserve_breaker_or_boundary() -> None:
    rows = [
        _row(1, "2026-01-01T00:00:00+00:00", won=False, hero_id=1),
        _row(2, "2026-01-02T00:00:00+00:00", won=False, hero_id=1),
        _row(3, "2026-01-03T00:00:00+00:00", won=True, hero_id=2),
        _row(4, "2026-01-04T00:00:00+00:00", won=False, hero_id=2),
        _row(5, "2026-01-05T00:00:00+00:00", won=False, hero_id=2),
        _row(6, "2026-01-06T00:00:00+00:00", won=True, hero_id=3),
    ]

    losing = build_losing_streak_module(rows, hero_metadata=HEROES)
    assert losing["data"]["start_date"] == "2026-01-04"
    assert losing["data"]["terminal_state"] == "broken_by_win"
    assert losing["data"]["breaker"]["hero_name"] == "Bane"
    assert losing["data"]["breaker"]["outcome"] == "win"

    winning = build_winning_streak_module(rows)
    assert winning["data"]["length"] == 1
    assert winning["data"]["start_date"] == "2026-01-06"

    boundary = build_losing_streak_module(rows[:-1], history_completeness="possibly_truncated")
    assert boundary["data"]["terminal_state"] == "history_boundary"
    assert build_win_summary_module(rows)["data"]["winningest_day"] == {
        "date": "2026-01-06",
        "daily_wins": 1,
    }


def test_hero_rankings_pool_and_loss_breaker_exclusion_are_raw_and_tied_deterministically() -> None:
    rows = [
        _row(1, "2026-01-01T00:00:00+00:00", hero_id=1, won=True),
        _row(2, "2026-01-02T00:00:00+00:00", hero_id=2, won=True),
        _row(3, "2026-01-03T00:00:00+00:00", hero_id=1, won=False),
        _row(4, "2026-01-04T00:00:00+00:00", hero_id=2, won=False),
        _row(5, "2026-01-05T00:00:00+00:00", hero_id=3, won=False),
    ]

    wins = build_top_win_heroes_module(rows, hero_metadata=HEROES)
    pool = build_hero_pool_module(rows, hero_metadata=HEROES)
    losses = build_top_loss_heroes_module(rows, hero_metadata=HEROES, breaker_hero_id=3)

    assert [row["hero_id"] for row in wins["data"]["rows"]] == [2, 1]
    assert wins["data"]["rows"][0]["matches"] == 2
    assert pool["data"]["top_five_share"] == 1.0
    assert pool["data"]["concentration_band"] == "concentrated"
    assert all(row["hero_id"] != 3 for row in losses["data"]["rows"])


def test_hero_eras_fall_back_to_three_equal_thirds_and_payoff_requires_non_sparse_periods() -> None:
    rows = [
        _row(1, "2026-01-10T00:00:00+00:00", hero_id=1),
        _row(2, "2026-01-11T00:00:00+00:00", hero_id=1),
        _row(3, "2026-01-12T00:00:00+00:00", hero_id=1),
        _row(4, "2026-03-10T00:00:00+00:00", hero_id=2),
        _row(5, "2026-03-11T00:00:00+00:00", hero_id=2),
        _row(6, "2026-03-12T00:00:00+00:00", hero_id=2),
        _row(7, "2026-06-10T00:00:00+00:00", hero_id=3),
        _row(8, "2026-06-11T00:00:00+00:00", hero_id=3),
        _row(9, "2026-06-12T00:00:00+00:00", hero_id=3),
    ]

    eras = build_hero_eras_module(rows, hero_metadata=HEROES)

    assert eras["data"]["sparse_fallback"] is True
    assert eras["data"]["period_kind"] == "third"
    assert len(eras["data"]["periods"]) == 3
    assert all("empty" in period and "sparse" in period for period in eras["data"]["periods"])
    assert build_hero_era_payoff_module(eras, hero_metadata=HEROES)["state"] == "available"


def test_hero_era_payoff_emits_persistence_for_one_non_sparse_period() -> None:
    eras = {
        "state": "available",
        "data": {
            "periods": [
                {
                    "id": "2026-01",
                    "date_end": "2026-01-31",
                    "sparse": False,
                    "top_heroes": [{"hero_id": 1, "matches": 3}],
                }
            ]
        },
    }

    module = build_hero_era_payoff_module(eras, hero_metadata=HEROES)

    assert module["data"]["persistence"] == {
        "hero": {"hero_id": 1, "hero_name": "Anti-Mage"},
        "top_five_periods": 1,
    }


def test_combat_modules_keep_zero_totals_available_and_rank_individuals() -> None:
    rows = [
        _row(1, "2026-01-01T00:00:00+00:00", hero_id=1, kills=0, assists=2, deaths=1),
        _row(2, "2026-01-02T00:00:00+00:00", hero_id=2, kills=4, assists=1, deaths=0, duration=2_400),
        _row(3, "2026-01-03T00:00:00+00:00", hero_id=1, kills=4, assists=0, deaths=2, duration=1_800),
    ]

    kills = build_kills_module(rows, hero_metadata=HEROES)
    zero = build_kills_module([_row(4, "2026-01-04T00:00:00+00:00", kills=0)])

    assert kills["data"]["total"] == 8
    assert kills["data"]["leading_hero"]["hero_id"] == 1
    assert kills["data"]["individuals"][0]["duration_seconds"] == 2_400
    assert zero["state"] == "available"
    assert zero["data"]["leading_hero"] is None
    assert zero["data"]["individuals"] == []
