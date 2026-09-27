import json
from copy import deepcopy
from pathlib import Path

from app.tracker.core_fights import from_offlane_fights
from app.tracker.mobile_api import CoreFightsView
from app.tracker.offlane_context import evaluate_fights

FIXTURE = Path(__file__).parents[1] / "fixtures/tracker/paired-replay-v1/opendota.json"
GOLDEN = json.loads((FIXTURE.parent.parent / "core-graphs-v1.json").read_text())


def test_same_full_match_fight_measure_for_every_core_role():
    raw = json.loads(FIXTURE.read_text())
    assert raw["teamfights"][-1]["start"] > 900
    for viewer in (0, 1, 2):
        old = evaluate_fights(raw, viewer=viewer, duration=raw["duration"], quarantined=[])
        result = from_offlane_fights(old)
        assert result["contract_version"] == "core-fights-v1"
        assert result["state"] == "AVAILABLE"
        assert len(result["segments"]) == len(raw["teamfights"])
        if viewer == 0:
            assert CoreFightsView.model_validate(result).model_dump() == GOLDEN["opendota"]["core_fights"]
        for old_row, row in zip(old["segments"], result["segments"], strict=True):
            assert row["player_damage"] == old_row["offlaner_damage"]
            assert row["player_kills"] == old_row["offlaner_kills"]
            assert row["player_deaths"] == old_row["offlaner_deaths"]
            assert row["damage_share"] == old_row["damage_share"]
            assert row["start_seconds"] == old_row["start_seconds"]
            assert row["end_seconds"] == old_row["end_seconds"]
            assert "offlaner_damage" not in row


def test_missing_empty_invalid_and_zero_damage_fights_keep_readiness():
    raw = json.loads(FIXTURE.read_text())
    unavailable = from_offlane_fights(evaluate_fights(None, viewer=0, duration=raw["duration"], quarantined=[]))
    assert unavailable["state"] == "UNAVAILABLE" and unavailable["reason"] == "FIGHTS_UNAVAILABLE"
    assert CoreFightsView.model_validate(unavailable).model_dump() == GOLDEN["stratz"]["core_fights"]
    empty = deepcopy(raw)
    empty["teamfights"] = []
    result = from_offlane_fights(evaluate_fights(empty, viewer=0, duration=raw["duration"], quarantined=[]))
    assert result["state"] == "AVAILABLE" and result["segments"] == []
    invalid = deepcopy(raw)
    invalid["teamfights"][0]["end"] = raw["duration"] + 1
    result = from_offlane_fights(evaluate_fights(invalid, viewer=0, duration=raw["duration"], quarantined=[]))
    assert result["state"] == "UNAVAILABLE" and result["reason"] == "FIGHTS_INVALID"
    zero = deepcopy(raw)
    zero["teamfights"] = [deepcopy(raw["teamfights"][0])]
    for player in zero["teamfights"][0]["players"][:5]:
        player["damage"] = 0
    result = from_offlane_fights(evaluate_fights(zero, viewer=0, duration=raw["duration"], quarantined=[]))
    assert result["segments"][0]["damage_share"] is None
    assert result["segments"][0]["player_damage"] == 0
