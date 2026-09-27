import json
from copy import deepcopy
from pathlib import Path

import pytest
from app.tracker.normalization import (
    InvalidEvidence,
    opendota_summary,
    stratz_summary,
    summary_disagreements,
)
from app.tracker.replay import quarantine_checkpoint_conflicts, replay_checkpoints

FIXTURES = Path(__file__).parents[1] / "fixtures/tracker/paired-replay-v1"


def pair():
    return [json.loads((FIXTURES / f"{provider}.json").read_text()) for provider in ("opendota", "stratz")]


def test_real_ten_player_pair_summary_and_exact_checkpoints():
    od, sz = pair()
    assert summary_disagreements(opendota_summary(od), stratz_summary(sz)) == []
    left, right = replay_checkpoints(od, "opendota"), replay_checkpoints(sz, "stratz")
    for a, b in zip(left["players"], right["players"], strict=True):
        for name in ("net_worth", "last_hits", "camps_stacked"):
            for timestamp in ("600", "1200"):
                assert a["series"][name][timestamp] == b["series"][name][timestamp]
                assert a["series"][name][timestamp] is not None
    assert left["players"][0]["series"]["camps_stacked"]["1200"] == 4
    assert right["players"][0]["series"]["camps_stacked"]["1200"] == 4
    for left_player, right_player in zip(left["players"], right["players"], strict=True):
        assert left_player["series"]["xp_earned"]["0"] == right_player["series"]["xp_earned"]["0"] == 0
        assert left_player["series"]["xp_earned"]["600"] == right_player["series"]["xp_earned"]["600"]


def test_real_discrepancies_quarantine_only_conflicting_points_without_mutation():
    od, sz = pair()
    left, right = replay_checkpoints(od, "opendota"), replay_checkpoints(sz, "stratz")
    saved = deepcopy(left)
    result = quarantine_checkpoint_conflicts(left, right)
    assert result["conflicts"]
    assert "players.7.series.net_worth.420" in result["conflicts"]
    assert result["players"][7]["series"]["net_worth"]["420"] is None
    assert result["players"][7]["series"]["net_worth"]["600"] == 2125
    assert left == saved
    assert all(not p.endswith((".600", ".1200")) for p in result["conflicts"]
               if ".hero_damage_earned." not in p)
    assert "players.3.series.hero_damage_earned.600" in result["conflicts"]


def test_missing_malformed_short_or_unparsed_series_never_become_zero():
    od, sz = pair()
    od["players"][0]["networth_t"] = None
    assert replay_checkpoints(od, "opendota")["players"][0]["series"]["net_worth"] is None
    sz["players"][0]["stats"]["lastHitsPerMinute"] = [0, None, 1]
    sz["players"][0]["stats"]["campStack"] = [0]
    sz["players"][0]["stats"]["networthPerMinute"] = [True, 100]
    sz["players"][0]["stats"]["experiencePerMinute"] = [50, None, 80]
    values = replay_checkpoints(sz, "stratz")["players"][0]["series"]
    assert values["last_hits"] == {"60": 0, "120": None, "180": None}
    assert values["camps_stacked"] == {"60": 0}
    assert values["net_worth"] == {"0": None, "60": 100}
    assert values["xp_earned"] == {"0": 0, "60": 50, "120": None, "180": None}
    sz["isStats"] = False
    sz["statsDateTime"] = None
    assert all(v is None for v in replay_checkpoints(sz, "stratz")["players"][0]["series"].values())
    od["version"] = None
    assert all(v is None for v in replay_checkpoints(od, "opendota")["players"][0]["series"].values())


def test_exact_time_alignment_duration_and_roster_guards():
    od, sz = pair()
    od["players"][0]["times"][1] = 0
    assert all(v is None for v in replay_checkpoints(od, "opendota")["players"][0]["series"].values())
    od["players"][0]["times"] = [time * 60 + 60 for time in range(len(od["players"][0]["times"]))]
    assert all(v is None for v in replay_checkpoints(od, "opendota")["players"][0]["series"]["xp_earned"].values())
    sz["durationSeconds"] = 599
    projected = replay_checkpoints(sz, "stratz")
    assert "600" not in projected["players"][0]["series"]["net_worth"]
    other = deepcopy(projected)
    other["players"][0] = None
    with pytest.raises(InvalidEvidence):
        quarantine_checkpoint_conflicts(projected, other)
    other = deepcopy(projected)
    other["match_id"] += 1
    with pytest.raises(InvalidEvidence):
        quarantine_checkpoint_conflicts(projected, other)


def test_historical_selection_without_minute_xp_keeps_net_worth():
    _, sz = pair()
    sz["players"][0]["stats"].pop("experiencePerMinute")
    series = replay_checkpoints(sz, "stratz")["players"][0]["series"]
    assert series["xp_earned"] is None
    assert series["net_worth"]["600"] is not None
    sz["players"][0]["stats"]["experiencePerMinute"] = []
    assert replay_checkpoints(sz, "stratz")["players"][0]["series"]["xp_earned"] is None


def test_damage_missing_and_malformed_samples_keep_only_real_checkpoints():
    od, sz = pair()
    od["players"][0]["hero_damage_t"][2] = None
    od_damage = replay_checkpoints(od, "opendota")["players"][0]["series"]["hero_damage_earned"]
    assert od_damage["0"] == 0 and od_damage["120"] is None
    assert od_damage["180"] is not None
    od["players"][0]["hero_damage_t"][3] = -1
    assert replay_checkpoints(od, "opendota")["players"][0]["series"]["hero_damage_earned"]["180"] is None
    sz["players"][0]["stats"]["heroDamagePerMinute"] = [20, None, 30]
    sz_damage = replay_checkpoints(sz, "stratz")["players"][0]["series"]["hero_damage_earned"]
    assert sz_damage == {"0": 0, "60": 20, "120": None, "180": None}
    sz["players"][0]["stats"].pop("heroDamagePerMinute")
    assert replay_checkpoints(sz, "stratz")["players"][0]["series"]["hero_damage_earned"] is None


def test_sanitized_pair_has_no_private_identity_keys():
    forbidden = {"name", "personaname", "chat", "replay_url"}

    def check(value):
        if isinstance(value, dict):
            for key, child in value.items():
                lower = key.lower()
                assert lower not in forbidden
                assert not any(word in lower for word in ("account", "steam", "token", "mmr", "rank"))
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    for payload in pair():
        check(payload)
    od, sz = pair()
    assert od["match_id"] == sz["id"] == 9000000002
