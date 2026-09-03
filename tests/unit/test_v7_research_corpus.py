from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.v7_research.corpus import (
    CANDIDATE_TEST,
    DISCOVERY,
    CorpusError,
    ReservedSplitAccess,
    corpus_paths,
    forbidden_fields_in,
    iter_players,
)


def _write_player(directory: Path, pseudonym: str, split: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "account_pseudonym": pseudonym,
        "split": split,
        "rows": [{"match_id": 1, "hero_id": 5}],
        "schema_version": "stratz-v7-canonical-history-1.0.0",
    }
    (directory / f"{pseudonym}.json").write_text(json.dumps(payload), encoding="utf-8")


def _corpus(tmp_path: Path) -> Path:
    history = tmp_path / "canonical" / "history"
    _write_player(history, "v7p_aaa", DISCOVERY)
    _write_player(history, "v7p_bbb", CANDIDATE_TEST)
    _write_player(history, "v7p_ccc", "CALIBRATION_RESERVED")
    _write_player(history, "v7p_ddd", "SEALED_VALIDATION")
    return tmp_path


def test_reserved_splits_are_not_requestable(tmp_path: Path) -> None:
    paths = corpus_paths(_corpus(tmp_path))
    for split in ("CALIBRATION_RESERVED", "SEALED_VALIDATION"):
        with pytest.raises(ReservedSplitAccess):
            list(iter_players(paths, "history", {DISCOVERY, split}))


def test_default_iteration_yields_research_splits_only(tmp_path: Path) -> None:
    paths = corpus_paths(_corpus(tmp_path))
    splits = sorted(document["split"] for document in iter_players(paths, "history"))
    assert splits == [CANDIDATE_TEST, DISCOVERY]


def test_discovery_only_iteration_excludes_candidate_test(tmp_path: Path) -> None:
    paths = corpus_paths(_corpus(tmp_path))
    splits = [document["split"] for document in iter_players(paths, "history", {DISCOVERY})]
    assert splits == [DISCOVERY]


def test_unknown_table_fails_closed(tmp_path: Path) -> None:
    paths = corpus_paths(_corpus(tmp_path))
    with pytest.raises(CorpusError):
        list(iter_players(paths, "playback"))


def test_missing_corpus_root_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("V7_CORPUS_ROOT", raising=False)
    with pytest.raises(CorpusError):
        corpus_paths(None)


@pytest.mark.parametrize(
    "field",
    [
        "rank",
        "rankTier",
        "seasonRank",
        "mmrEstimate",
        "imp",
        "behaviorScore",
        "smurfFlag",
        "predictedWin",
        "winProbability",
        "playbackData",
        "leaderboardRank",
        "awardScore",
    ],
)
def test_forbidden_provider_fields_are_detected(field: str) -> None:
    assert forbidden_fields_in({"rows": [{field: 1}]}) == {field}


def test_allowed_canonical_fields_are_not_flagged() -> None:
    row = {
        "match_id": 1,
        "hero_id": 5,
        "position_native": "POSITION_3",
        "role_native": "CORE",
        "lane_native": "OFF_LANE",
        "game_mode_native": "TURBO",
        "lobby_type_native": "RANKED",
        "leaver_status_native": "NONE",
        "game_version_id": 182,
        "kills": 1,
        "deaths": 2,
        "assists": 3,
        "is_victory": True,
        "is_radiant": True,
        "duration_seconds": 1800,
        "started_at": 1,
        "ended_at": 2,
        "parsed_at": 3,
        "is_parsed": True,
        "radiant_networth_leads": [0, 1],
        "item_purchases": [{"time": 1, "itemId": 2}],
        "kill_events": [{"time": 1}],
        "assist_events": [{"time": 1}],
    }
    assert forbidden_fields_in(row) == set()
