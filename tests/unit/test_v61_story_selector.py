from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from app.ingestion.summary_normalize import normalize_summary_rows
from app.player_analysis_v61.story_selector import (
    MODE_MAP_CATEGORIES,
    MODE_MAP_PATH,
    MODE_MAP_SHA256,
    StoryModeMapError,
    load_mode_map_artifact,
    select_story_matches,
)


def _row(match_id: int, **updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "match_id": match_id,
        "start_time": 1_700_000_000 + match_id,
        "duration": 1_800,
        "hero_id": 25,
        "player_slot": 0,
        "radiant_win": True,
        "game_mode": 1,
        "lobby_type": 0,
        "kills": 8,
        "deaths": 4,
        "assists": 10,
        "leaver_status": 0,
    }
    value.update(updates)
    return value


def test_mode_map_is_checked_in_and_byte_checksum_linked() -> None:
    artifact = load_mode_map_artifact()

    assert MODE_MAP_PATH.is_file()
    assert hashlib.sha256(MODE_MAP_PATH.read_bytes()).hexdigest() == MODE_MAP_SHA256
    assert artifact.checksum == MODE_MAP_SHA256
    assert dict(artifact.categories) == MODE_MAP_CATEGORIES
    assert artifact.category_for(1, 0) == "unranked_all_pick"
    assert artifact.category_for(1, 7) is None


def test_mode_map_loader_rejects_checksum_and_tuple_drift(tmp_path: Path) -> None:
    payload = json.loads(MODE_MAP_PATH.read_text(encoding="utf-8"))
    payload["categories"]["ranked_all_pick"]["lobby_type"] = 0
    path = tmp_path / MODE_MAP_PATH.name
    path.write_text(json.dumps(payload), encoding="utf-8")

    expected_checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(StoryModeMapError, match="unexpected tuple"):
        load_mode_map_artifact(path, expected_checksum=expected_checksum)
    with pytest.raises(StoryModeMapError, match="checksum"):
        load_mode_map_artifact(path)


def test_story_selector_keeps_ap_inferential_population_and_adds_exact_cm_rows() -> None:
    rows = [
        _row(1, game_mode=1, lobby_type=0),
        _row(2, game_mode=22, lobby_type=7),
        _row(3, game_mode=2, lobby_type=0),
        _row(4, game_mode=2, lobby_type=7),
        # Independently supported dimensions, but not one of the pinned tuples.
        _row(5, game_mode=1, lobby_type=7),
        _row(6, game_mode=99, lobby_type=0),
    ]
    normalized = normalize_summary_rows(rows, account_id=42)
    inferential_ids = tuple(item.match_id for item in normalized.eligible_matches)

    selection = select_story_matches(normalized.matches)

    assert tuple(item.match_id for item in selection.matches) == (1, 2, 3, 4)
    assert dict(selection.mode_counts) == {
        "unranked_all_pick": 1,
        "ranked_all_pick": 1,
        "unranked_captains_mode": 1,
        "ranked_captains_mode": 1,
    }
    assert selection.excluded_or_unknown_count == 2
    assert selection.exclusion_reasons == {"unsupported_mode_lobby_tuple": 2}
    # CM admission is a separate story view; the existing AP-only gate is unchanged.
    assert inferential_ids == (1, 2, 5)
    assert tuple(item.match_id for item in normalized.eligible_matches) == inferential_ids


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"duration": -1}, "invalid_duration"),
        ({"radiant_win": None}, "missing_outcome"),
        ({"hero_id": None}, "missing_hero"),
        ({"player_slot": None}, "missing_side"),
        ({"leaver_status": 2}, "abandoned"),
        ({"leagueid": 123}, "pro_or_league"),
        ({"kills": -1}, "invalid_kills"),
        ({"start_time": None}, "missing_start_time"),
    ],
)
def test_captains_mode_may_ignore_only_unsupported_mode(
    updates: dict[str, object], reason: str
) -> None:
    normalized = normalize_summary_rows(
        [_row(1, game_mode=2, lobby_type=0, **updates)],
        account_id=42,
    )
    common = normalized.matches[0].eligibility["overall"]  # type: ignore[index]
    assert "unsupported_game_mode" in common.reasons
    assert reason in common.reasons

    selection = select_story_matches(normalized.matches)

    assert selection.matches == ()
    assert selection.excluded_or_unknown_count == 1
    assert reason in selection.exclusion_reasons


def test_missing_common_eligibility_fails_closed() -> None:
    normalized = normalize_summary_rows([_row(1)], account_id=42)
    row = replace(normalized.matches[0], eligibility=None)

    selection = select_story_matches((row,))

    assert selection.matches == ()
    assert selection.exclusion_reasons == {"missing_common_eligibility": 1}
