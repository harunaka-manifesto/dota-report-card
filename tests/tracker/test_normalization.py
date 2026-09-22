import json
from copy import deepcopy
from pathlib import Path

import pytest
from app.tracker.normalization import (
    InvalidEvidence,
    opendota_summary,
    player_summary,
    replay_available,
)

FIXTURES = Path(__file__).parents[1] / "fixtures/tracker/provider-summary-v1"


def test_real_paired_player_summaries_agree_where_both_observed():
    observed = set()
    pairs = json.loads((FIXTURES / "paired-players.json").read_text())
    assert len(pairs) == 13
    for pair in pairs:
        a = player_summary(pair["opendota"], "opendota")
        b = player_summary(pair["stratz"], "stratz")
        assert (a["player_slot"], a["hero_id"], a["team"]) == (b["player_slot"], b["hero_id"], b["team"])
        for metric in a["values"]:
            if a["values"][metric] is not None and b["values"][metric] is not None:
                assert a["values"][metric] == b["values"][metric], metric
                observed.add(metric)
    assert {"kills", "deaths", "assists", "last_hits", "denies", "gold_per_min", "xp_per_min"} <= observed


def test_real_unparsed_roster_missing_values_and_vendor_exclusion():
    raw = json.loads((FIXTURES / "unparsed-match.json").read_text())
    raw["players"][0].update(kills=0, deaths=None, assists=True, benchmarks={"kills": 99}, position="POSITION_1")
    result = opendota_summary(raw)
    assert [p["player_slot"] for p in result["players"]] == list(range(10))
    player = result["players"][0]
    assert player["values"]["kills"] == 0
    assert "kills" not in player["unavailable"]
    assert player["values"]["deaths"] is None
    assert player["unavailable"]["deaths"] == "MISSING"
    assert player["values"]["assists"] is None
    assert player["unavailable"]["assists"] == "MALFORMED"
    assert "benchmarks" not in str(result) and "POSITION_1" not in str(result)
    assert not replay_available(raw, "opendota")
    for mode, expected in [(23, "TURBO"), (22, "STANDARD"), (1, "STANDARD"), (2, "UNSUPPORTED"), (None, "UNSUPPORTED")]:
        assert opendota_summary({**raw, "game_mode": mode})["mode"] == expected


def test_partial_or_conflicting_roster_never_becomes_summary_ready():
    raw = json.loads((FIXTURES / "unparsed-match.json").read_text())
    for mutation in (lambda r: r["players"].pop(), lambda r: r["players"].__setitem__(1, r["players"][0]), lambda r: r.update(radiant_win=None)):
        broken = deepcopy(raw)
        mutation(broken)
        with pytest.raises(InvalidEvidence):
            opendota_summary(broken)
    with pytest.raises(InvalidEvidence):
        player_summary({"playerSlot": 128, "isRadiant": True, "heroId": 1}, "stratz")


def test_replay_gate_uses_statistics_not_ingestion_marker():
    assert not replay_available({"parsedDateTime": 123}, "stratz")
    assert not replay_available({"parsedDateTime": 123, "statsDateTime": 124, "isStats": False}, "stratz")
    assert replay_available({"statsDateTime": 124, "isStats": True}, "stratz")
    assert replay_available({"version": 21}, "opendota")
    assert not replay_available({"version": True}, "opendota")


def test_stage_one_build_and_draft_keep_unknown_distinct_from_empty():
    raw = json.loads((FIXTURES / "unparsed-match.json").read_text())
    raw["players"][0].update(item_0=0, item_1=42, ability_upgrades_arr=[10, 20, 10])
    raw["picks_bans"] = [{"hero_id": 1, "order": 1, "team": 1, "is_pick": False}]
    summary = opendota_summary(raw)
    player = summary["players"][0]
    assert player["items"]["item_0"] == 0
    assert player["items"]["item_1"] == 42
    assert player["items"]["item_2"] is None
    assert player["ability_build"] == [10, 20, 10]
    assert summary["draft"] == [{"hero_id": 1, "order": 1, "team": "DIRE", "is_pick": False}]
    raw["players"][0]["ability_upgrades_arr"] = [True]
    raw["picks_bans"][0]["team"] = True
    assert opendota_summary(raw)["draft"] is None
    assert opendota_summary(raw)["players"][0]["ability_build"] is None
    raw["picks_bans"] = []
    raw["players"][0]["ability_upgrades_arr"] = []
    assert opendota_summary(raw)["draft"] == []
    assert opendota_summary(raw)["players"][0]["ability_build"] == []
