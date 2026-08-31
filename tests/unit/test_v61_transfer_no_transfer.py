from __future__ import annotations

from app.player_analysis_v61.estimators import continuous_transfer
from app.player_analysis_v61.family_statistics import _transfer_component_bootstrap_p
from app.player_analysis_v61.portfolio_shape import DistanceRecord


def _reference_records() -> tuple[DistanceRecord, ...]:
    records: list[DistanceRecord] = []
    match_id = 0
    for band, count, sessions, won, kills, deaths in (
        ("core", 96, 37, None, 6, 3),
        ("reliable_stretch", 16, 14, True, 15, 9),
        ("experimental_edge", 28, 17, False, 6, 3),
    ):
        for index in range(count):
            match_id += 1
            records.append(
                DistanceRecord(
                    {
                        "match_id": match_id,
                        "session_id": f"{band}-{index % sessions}",
                        "won": (index % 2 == 0) if won is None else won,
                        "kills": kills,
                        "assists": 0,
                        "deaths": deaths,
                        "duration_seconds": 1_800,
                    },
                    familiarity_distance=0.5,
                    function_distance=0.5,
                    combined_distance=0.5,
                    band=band,
                    fold=index % 2,
                )
            )
    return tuple(records)


def _promoted_records(frontier: str) -> tuple[DistanceRecord, ...]:
    records: list[DistanceRecord] = []
    index = 0
    for band in ("core", "reliable_stretch", "experimental_edge"):
        for session in range(6):
            for _ in range(3):
                changed = band == "experimental_edge" and frontier == "reliable_stretch"
                records.append(
                    DistanceRecord(
                        {
                            "match_id": index + 1,
                            "session_id": f"{band}-{session}",
                            "won": not changed,
                            "kills": 10 if not changed else 0,
                            "assists": 0,
                            "deaths": 1 if not changed else 10,
                            "duration_seconds": 1_800,
                        },
                        0.0,
                        0.0,
                        0.0,
                        band,
                        session % 2,
                    )
                )
                index += 1
    return tuple(records)


def _below_support_records() -> tuple[DistanceRecord, ...]:
    records: list[DistanceRecord] = []
    match_id = 0
    for band, count, sessions, won, kills, deaths in (
        ("core", 24, 8, None, 6, 3),
        ("reliable_stretch", 11, 5, True, 15, 9),
    ):
        for index in range(count):
            match_id += 1
            records.append(
                DistanceRecord(
                    {
                        "match_id": match_id,
                        "session_id": f"{band}-{index % sessions}",
                        "won": (index % 2 == 0) if won is None else won,
                        "kills": kills,
                        "assists": 0,
                        "deaths": deaths,
                        "duration_seconds": 1_800,
                    },
                    familiarity_distance=0.5,
                    function_distance=0.5,
                    combined_distance=0.5,
                    band=band,
                    fold=index % 2,
                )
            )
    return tuple(records)


def _transfer_result(records: tuple[DistanceRecord, ...]) -> dict[str, object]:
    return continuous_transfer(
        [record.match for record in records],
        baseline_resolver=None,
        taxonomy_by_hero=None,
        distance_records=records,
    )


def test_reference_shape_should_select_no_transfer_at_core_frontier() -> None:
    result = _transfer_result(_reference_records())

    assert result["frontier"] == "core"
    assert result["bands"]["reliable_stretch"]["supported"] is True
    assert result["bands"]["experimental_edge"]["supported"] is True
    assert result["semantic_subtype"] == "no_transfer"


def test_promoted_reliable_and_experimental_frontiers_never_select_no_transfer() -> None:
    reliable = _transfer_result(_promoted_records("reliable_stretch"))
    experimental = _transfer_result(_promoted_records("experimental_edge"))

    assert reliable["frontier"] == "reliable_stretch"
    assert experimental["frontier"] == "experimental_edge"
    assert reliable["semantic_subtype"] != "no_transfer"
    assert experimental["semantic_subtype"] != "no_transfer"


def test_below_transfer_support_suppresses_no_transfer() -> None:
    result = _transfer_result(_below_support_records())

    assert result["bands"]["reliable_stretch"]["supported"] is False
    assert result["semantic_subtype"] != "no_transfer"


def test_transfer_component_bootstrap_p_rejects_tight_null_centered_draws() -> None:
    point = {"outcome": 0.167, "activity": -0.081, "survival": 0.315}
    ropes = {"outcome": 0.08, "activity": 0.08, "survival": 0.35}
    samples = {
        "outcome": [0.167 + 0.001 * (index % 2) for index in range(40)],
        "activity": [-0.081 + 0.001 * (index % 2) for index in range(40)],
        "survival": [0.315 + 0.001 * (index % 2) for index in range(40)],
    }

    p_value = _transfer_component_bootstrap_p(
        point_deltas=point,
        samples=samples,
        ropes=ropes,
    )

    assert p_value < 0.05
    assert p_value != 1.0


def test_transfer_component_bootstrap_p_fails_closed_on_incomplete_evidence() -> None:
    point = {"outcome": 0.167, "activity": -0.081, "survival": 0.315}
    ropes = {"outcome": 0.08, "activity": 0.08, "survival": 0.35}

    assert (
        _transfer_component_bootstrap_p(
            point_deltas=point,
            samples={"outcome": [0.167], "activity": ["bad"], "survival": [0.315]},
            ropes=ropes,
        )
        == 1.0
    )
    assert (
        _transfer_component_bootstrap_p(
            point_deltas=point,
            samples={"outcome": [0.167], "activity": [-0.081], "survival": []},
            ropes=ropes,
        )
        == 1.0
    )
