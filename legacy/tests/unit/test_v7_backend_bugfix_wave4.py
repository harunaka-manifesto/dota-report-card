from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from report_card.player_analysis_v7.capability_payload import V7CapabilityPayload
from report_card.player_analysis_v7.runtime import analyze_v7

from tests.unit.test_v7_capability_payload import payload
from tests.unit.test_v7_runtime_service import _deep_row, _history


def test_event_detail_count_uses_accepted_deep_rows_not_history_parsed_flags() -> None:
    report = analyze_v7(
        history=_history(),
        deep_rows=[],
        hero_metadata={},
        generated_at="2026-09-08T00:00:00Z",
    )

    assert report.descriptive_facts.scope.parsed_match_count == 1
    assert report.descriptive_facts.scope.acquired_event_detail_match_count == 0
    assert report.metadata.matches_with_event_detail == 0

    with_deep = analyze_v7(
        history=_history(),
        deep_rows=[_deep_row()],
        hero_metadata={1: {"display_name": "Anti-Mage"}},
        generated_at="2026-09-08T00:00:00Z",
    )
    assert with_deep.descriptive_facts.scope.acquired_event_detail_match_count == 1
    assert with_deep.metadata.matches_with_event_detail == 1


def test_old_payload_without_acquired_event_detail_count_keeps_legacy_meaning() -> None:
    persisted = payload().model_dump(mode="json")
    persisted["descriptive_facts"]["scope"].pop("acquired_event_detail_match_count")

    loaded = V7CapabilityPayload.model_validate(persisted).validate_payload()

    assert loaded.descriptive_facts.scope.acquired_event_detail_match_count is None
    assert loaded.metadata.matches_with_event_detail == loaded.descriptive_facts.scope.parsed_match_count


def test_persisted_recommendation_direction_must_match_gap() -> None:
    persisted = json.loads(payload().model_dump_json())
    persisted["recommendation"]["direction"] = "positive"

    with pytest.raises(ValidationError, match="must match the gap sign"):
        V7CapabilityPayload.model_validate(persisted)


@pytest.mark.parametrize("field", ["interval_low", "interval_high"])
def test_persisted_finding_interval_bounds_must_be_finite(field: str) -> None:
    persisted = payload().model_dump(mode="python")
    persisted["findings"][0]["estimate"][field] = float("-inf" if field == "interval_low" else "inf")

    with pytest.raises(ValidationError, match="must be finite"):
        V7CapabilityPayload.model_validate(persisted)


def test_valid_payload_round_trips_through_json_without_non_finite_values() -> None:
    serialized = payload().model_dump_json()
    loaded = V7CapabilityPayload.model_validate(json.loads(serialized)).validate_payload()

    assert loaded.model_dump_json() == serialized
