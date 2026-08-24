from __future__ import annotations

import pytest
from app.player_analysis_v61.calibration_evaluation import validate_aggregate_payload
from app.player_analysis_v61.legacy_adapter import (
    adapt_legacy_row,
    legacy_canonical_history,
    redacted_runtime_record,
)


def _row() -> dict[str, object]:
    return {
        "profile_id": "profile-private",
        "match_id": 123,
        "start_time": 1_700_000_000,
        "duration_seconds": 1_800,
        "won": True,
        "kills": 8,
        "deaths": 2,
        "assists": 12,
        "hero_id": 1,
        "hero_function": "legacy-label",
        "patch": "7.39",
        "session_id": "session-private",
        "session_index": 1,
        "session_corrupt": False,
        "lane_context": None,
    }


def test_legacy_adapter_rederives_taxonomy_and_redacts_runtime_identifiers() -> None:
    adapted = adapt_legacy_row(
        _row(),
        taxonomy_by_hero={1: {"hero_function": "control", "functional_jobs": ["control"]}},
    )

    assert adapted["hero_function"] == "control"
    assert adapted["metrics"]["involvement_per_minute"] > 0
    assert adapted["metrics"]["finishing_share"] == pytest.approx(0.4)
    redacted = redacted_runtime_record(adapted)
    assert not {"profile_id", "match_id", "session_id"} & set(redacted)


def test_compact_rows_can_enter_the_same_canonical_report_contract() -> None:
    history = legacy_canonical_history([_row()], account_id=42)

    assert history.audit.request_count == 1
    assert history.audit.rank_or_mmr_used is False
    assert history.normalization.eligible_matches[0].match_id == 123


def test_aggregate_privacy_allows_schema_field_names_but_rejects_identifiers() -> None:
    validate_aggregate_payload(
        {
            "required_compact_field_coverage": {"session_id": 1.0},
            "canonical_required_field_coverage": {"match_id": 1.0},
            "mmr_used": False,
            "no_rank_mmr": True,
        }
    )

    with pytest.raises(ValueError, match="identifier field"):
        validate_aggregate_payload({"profile_id": "private"})
    with pytest.raises(ValueError, match="rank/MMR field"):
        validate_aggregate_payload({"mmr_used": True})
