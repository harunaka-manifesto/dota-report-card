from __future__ import annotations

import json
from pathlib import Path

import pytest
from report_card.player_analysis_v7.research.corpus import (
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


def test_default_iteration_is_discovery_only(tmp_path: Path) -> None:
    # The default must not include CANDIDATE_TEST. An earlier version defaulted
    # to both research splits, and a purely descriptive atlas silently read all
    # 900 accounts because a caller left the argument off.
    paths = corpus_paths(_corpus(tmp_path))
    splits = sorted(document["split"] for document in iter_players(paths, "history"))
    assert splits == [DISCOVERY]


def test_candidate_test_requires_a_written_reason(tmp_path: Path) -> None:
    paths = corpus_paths(_corpus(tmp_path))
    with pytest.raises(CorpusError):
        list(iter_players(paths, "history", {DISCOVERY, CANDIDATE_TEST}))


def test_candidate_test_read_is_ledgered_before_any_row_is_yielded(tmp_path: Path) -> None:
    paths = corpus_paths(_corpus(tmp_path))
    ledger = tmp_path / "ledger.jsonl"
    stream = iter_players(
        paths,
        "history",
        {DISCOVERY, CANDIDATE_TEST},
        candidate_test_reason="unit test",
        ledger=ledger,
    )
    next(stream)
    assert ledger.is_file()
    entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    assert entries[0]["reason"] == "unit test"


def test_an_abandoned_candidate_test_read_still_leaves_a_ledger_line(tmp_path: Path) -> None:
    # The failure this control exists for: the data was seen, the run died, and
    # an after-the-fact ledger write never happened.
    paths = corpus_paths(_corpus(tmp_path))
    ledger = tmp_path / "ledger.jsonl"
    stream = iter_players(
        paths,
        "history",
        {DISCOVERY, CANDIDATE_TEST},
        candidate_test_reason="abandoned",
        ledger=ledger,
    )
    next(stream)
    stream.close()
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


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
