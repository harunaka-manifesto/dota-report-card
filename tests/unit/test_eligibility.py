from app.ingestion.eligibility import ExclusionReason, assess_match


def base_match() -> dict[str, object]:
    return {
        "match_id": 1,
        "duration": 1800,
        "game_mode": 1,
        "lobby_type": 7,
        "radiant_win": True,
        "account_id": 42,
        "player_slot": 0,
    }


def test_non_ranked_all_pick_is_eligible() -> None:
    result = assess_match(base_match(), account_id=42)
    assert result.eligible
    assert result.reasons == ()


def test_ranked_all_pick_is_eligible() -> None:
    value = base_match()
    value.update({"game_mode": 22, "lobby_type": 7})
    result = assess_match(value, account_id=42)
    assert result.eligible
    assert result.reasons == ()


def test_turbo_rows_are_excluded_with_reasons() -> None:
    value = base_match()
    value.update({"game_mode": 23, "lobby_type": 0})
    result = assess_match(value, account_id=42)
    assert not result.eligible
    assert ExclusionReason.NON_STANDARD_MODE in result.reasons


def test_league_and_abandon_are_excluded() -> None:
    value = base_match()
    value["leagueid"] = 99
    value["leaver_status"] = 3
    result = assess_match(value, account_id=42)
    assert set(result.reasons) == {ExclusionReason.PRO_OR_LEAGUE, ExclusionReason.ABANDONED}
