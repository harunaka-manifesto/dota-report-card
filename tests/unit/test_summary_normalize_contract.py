from app.ingestion.summary_normalize import normalize_summary_rows


def _row(match_id: int, **updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "match_id": match_id,
        "start_time": 1_700_000_000,
        "duration": 1_800,
        "hero_id": 25,
        "player_slot": 0,
        "radiant_win": True,
        "game_mode": 1,
        "lobby_type": 7,
        "kills": 8,
        "deaths": 4,
        "assists": 10,
    }
    value.update(updates)
    return value


def test_lane_role_is_a_role_hint_but_spatial_lane_is_not_a_role() -> None:
    result = normalize_summary_rows(
        [
            _row(1, lane_role=4),
            _row(2, lane_role=5),
            _row(3, lane=1),
        ],
        account_id=42,
    )

    by_id = {item.match_id: item for item in result.matches}
    assert by_id[1].role_hint == "jungle"
    assert by_id[2].role_hint == "roamer"
    assert by_id[3].role_hint is None
    assert by_id[3].eligibility is not None
    assert by_id[3].eligibility["overall"].included
    assert not by_id[3].eligibility["role"].included
    assert "missing_role_hint" in by_id[3].eligibility["role"].reasons


def test_unsupported_modes_and_invalid_numbers_keep_explicit_reasons() -> None:
    result = normalize_summary_rows(
        [_row(1, lobby_type=1), _row(2, duration=-1, kills=-3)],
        account_id=42,
    )

    by_id = {item.match_id: item for item in result.matches}
    first_reasons = by_id[1].eligibility["overall"].reasons  # type: ignore[index]
    second_reasons = by_id[2].eligibility["overall"].reasons  # type: ignore[index]
    assert "unsupported_lobby_type" in first_reasons
    assert "invalid_duration" in second_reasons
    assert "invalid_kills" in second_reasons
    assert len(second_reasons) == len(set(second_reasons))
