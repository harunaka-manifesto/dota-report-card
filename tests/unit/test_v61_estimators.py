from __future__ import annotations

from app.player_analysis_v61.estimators import (
    duration_context_involvement,
    information_weighted_consistency,
    overdispersed_death_exposure,
    stabilized_finishing,
)
from app.player_analysis_v61.portfolio_shape import (
    build_portfolio_shape,
    cross_fitted_distance_records,
)
from app.player_analysis_v61.relationships import result_response_summary, session_position_curve


def _match(
    index: int,
    *,
    session_id: str,
    kills: int = 5,
    assists: int = 5,
    deaths: int = 3,
    won: bool = True,
    hero_id: int = 1,
) -> dict[str, object]:
    return {
        "match_id": index + 1,
        "start_time": 1_700_000_000 + index * 2_000,
        "duration_seconds": 1_800,
        "hero_id": hero_id,
        "kills": kills,
        "assists": assists,
        "deaths": deaths,
        "won": won,
        "session_id": session_id,
        "session_index": index,
    }


def test_finishing_is_event_weighted_and_abstains_without_events() -> None:
    zero = [_match(index, session_id=f"s{index}", kills=0, assists=0) for index in range(40)]
    result = stabilized_finishing(zero)

    assert result["status"] == "unavailable"
    assert result["estimate"] is None
    assert result["events"] == 0


def test_finishing_interval_reflects_event_volume_not_match_ratio_count() -> None:
    low_volume = [
        _match(index, session_id=f"s{index}", kills=1, assists=1) for index in range(60)
    ]
    high_volume = [
        _match(index, session_id=f"s{index}", kills=10, assists=10) for index in range(60)
    ]
    low = stabilized_finishing(low_volume)
    high = stabilized_finishing(high_volume)

    assert abs(float(low["estimate"]) - float(high["estimate"])) < 0.001
    assert high["interval"][1] - high["interval"][0] < low["interval"][1] - low["interval"][0]


def test_involvement_records_duration_model_and_context_coverage() -> None:
    rows = [
        {
            **_match(index, session_id=f"s{index // 6}", kills=5, assists=5),
            "duration_seconds": 1_200 if index % 2 else 2_400,
        }
        for index in range(60)
    ]
    result = duration_context_involvement(
        rows,
        baseline_resolver=None,
        taxonomy_by_hero=None,
    )

    assert result["status"] == "available"
    assert result["matches"] == 60
    assert result["sessions"] == 10
    assert result["coverage"] == 1.0
    assert result["duration_log_slope"] != 0.0


def test_death_exposure_interval_records_overdispersion() -> None:
    rows = [
        _match(
            index,
            session_id=f"s{index // 5}",
            deaths=0 if index % 2 else 12,
        )
        for index in range(60)
    ]
    result = overdispersed_death_exposure(
        rows,
        baseline_resolver=None,
        taxonomy_by_hero=None,
    )

    assert result["status"] == "available"
    assert result["overdispersion"] > 1.0
    assert result["interval"][0] < result["estimate"] < result["interval"][1]


def test_consistency_gives_long_sessions_more_information_than_one_game_sessions() -> None:
    tiny = [
        _match(index, session_id=f"tiny-{index}", won=index % 2 == 0)
        for index in range(12)
    ]
    long = [
        _match(
            session * 10 + index,
            session_id=f"long-{session}",
            won=(session + index) % 2 == 0,
        )
        for session in range(12)
        for index in range(10)
    ]
    tiny_result = information_weighted_consistency(
        tiny, baseline_resolver=None, taxonomy_by_hero=None
    )
    long_result = information_weighted_consistency(
        long, baseline_resolver=None, taxonomy_by_hero=None
    )

    assert long_result["information_weight"] > tiny_result["information_weight"]


def test_portfolio_job_mass_weights_matches_fractionally() -> None:
    matches = [
        *[_match(index, session_id=f"s{index}", hero_id=1) for index in range(40)],
        *[_match(100 + index, session_id=f"r{index}", hero_id=2) for index in range(5)],
    ]
    taxonomy = {1: ("catch", "save"), 2: ("push",)}
    shape = build_portfolio_shape(matches, taxonomy)

    assert shape["fractional_job_mass"]["catch"] == 20.0
    assert shape["fractional_job_mass"]["save"] == 20.0
    assert shape["fractional_job_mass"]["push"] == 5.0
    assert shape["taxonomy_coverage"] == 1.0
    assert shape["taxonomy_sensitivity"]["version"] == "taxonomy-leave-one-label-1.0.0"
    assert shape["job_redundancy"]["catch"] == 1


def test_transfer_distance_is_cross_fitted_by_session() -> None:
    matches = [
        _match(index, session_id=f"s{index // 2}", hero_id=1 + index % 5)
        for index in range(60)
    ]
    taxonomy = {hero_id: ("catch",) if hero_id < 4 else ("push",) for hero_id in range(1, 6)}
    records = cross_fitted_distance_records(matches, taxonomy)

    assert len(records) == len(matches)
    assert {record.fold for record in records} == {0, 1}
    assert {record.band for record in records}.issubset(
        {"core", "reliable_stretch", "experimental_edge"}
    )


def test_direct_g4_opportunity_is_not_penalized_by_unrelated_one_game_sessions() -> None:
    long_sessions = [
        _match(session * 10 + index, session_id=f"long-{session}")
        for session in range(12)
        for index in range(4)
    ]
    short_sessions = [
        _match(1_000 + index, session_id=f"short-{index}") for index in range(100)
    ]
    completed = {
        **{f"long-{session}": True for session in range(12)},
        **{f"short-{index}": True for index in range(100)},
    }
    curve = session_position_curve([*long_sessions, *short_sessions], completed_sessions=completed)

    assert curve["positions"]["g4"]["sessions"] == 12
    assert curve["positions"]["g4"]["available"] is True


def test_result_response_separates_one_loss_and_two_plus_states_without_controls() -> None:
    matches = []
    for session in range(15):
        for index, won in enumerate((False, False, True, True)):
            matches.append(
                _match(
                    session * 10 + index,
                    session_id=f"s{session}",
                    won=won,
                    hero_id=1 + index % 3,
                )
            )
    result = result_response_summary(matches, {1: ("catch",), 2: ("save",), 3: ("push",)})

    assert result["states"]["one_loss"]["opportunities"] == 15
    assert result["states"]["two_plus_losses"]["opportunities"] == 15
    assert result["control_reuse"] == 0
    assert result["cross_session_transitions"] == 0
