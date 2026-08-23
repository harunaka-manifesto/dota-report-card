from __future__ import annotations

import copy
import json
import stat

import pytest
from app.player_analysis_v6.calibration_corpus import (
    CalibrationCorpusError,
    load_calibration_corpus,
    migrate_calibration_corpus,
    validate_calibration_corpus,
)


def _payload() -> dict:
    profile_id = "a" * 64
    matches = []
    for index in range(30):
        matches.append({
            "profile_id": profile_id, "match_id": index + 1, "hero_id": 1,
            "start_time": 1_000 + index * 100, "duration_seconds": 60, "won": index % 2 == 0,
            "kills": 1, "deaths": 2, "assists": 3, "patch": "7.41",
            "session_id": f"session-{index // 3 + 1}", "session_index": index % 3 + 1,
            "session_corrupt": False,
        })
    return {
        "schema_version": "v6-calibration-corpus-1.0.0",
        "window": {"days": 365, "start_time": 900, "end_time": 9_999},
        "source": {"rank_or_mmr_used": False},
        "summary": {"eligible_profile_count": 1, "eligible_match_count": 30},
        "profiles": [{"profile_id": profile_id, "status": "eligible", "eligible_match_count": 30, "session_count": 10, "completed_session_count": 9}],
        "matches": matches,
    }


def test_valid_corpus_returns_aggregate_only_diagnostics() -> None:
    corpus = validate_calibration_corpus(_payload(), checksum="abc")
    assert corpus.aggregate_diagnostics() == {
        "schema_version": "v6-calibration-corpus-1.0.0", "profile_count": 1,
        "match_count": 30, "session_count": 10, "corrupt_match_count": 0,
        "checksum": "abc", "rank_or_mmr_used": False,
    }


@pytest.mark.parametrize("mutation", ["raw_id", "duplicate", "mmr", "session_order", "summary"])
def test_corpus_fails_closed_on_private_contract_violations(mutation: str) -> None:
    payload = copy.deepcopy(_payload())
    if mutation == "raw_id":
        payload["profiles"][0]["profile_id"] = "123456"
    elif mutation == "duplicate":
        payload["matches"][1]["match_id"] = payload["matches"][0]["match_id"]
    elif mutation == "mmr":
        payload["matches"][0]["mmr"] = 4000
    elif mutation == "session_order":
        payload["matches"][1]["session_index"] = 3
    else:
        payload["summary"]["eligible_match_count"] = 29
    with pytest.raises(CalibrationCorpusError):
        validate_calibration_corpus(payload)


def test_private_migration_drops_only_out_of_window_rows_and_reindexes(tmp_path) -> None:
    payload = _payload()
    extra = copy.deepcopy(payload["matches"][-1])
    extra["match_id"] = 31
    extra["session_id"] = "session-11"
    extra["session_index"] = 1
    payload["matches"].append(extra)
    payload["profiles"][0]["eligible_match_count"] = 31
    payload["profiles"][0]["session_count"] = 11
    payload["profiles"][0]["completed_session_count"] = 10
    payload["summary"]["eligible_match_count"] = 31
    payload["matches"][0]["start_time"] = payload["window"]["start_time"] - 1
    source = tmp_path / "source.json"
    destination = tmp_path / "migrated.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    diagnostics = migrate_calibration_corpus(source, destination)
    migrated = load_calibration_corpus(destination)

    assert diagnostics["removed_out_of_window_matches"] == 1
    assert diagnostics["dropped_profiles"] == 0
    assert len(migrated.matches) == 30
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
