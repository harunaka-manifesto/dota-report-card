import json
from copy import deepcopy
from pathlib import Path

from app.tracker.metrics import measure
from app.tracker.normalization import opendota_summary
from app.tracker.offlane_context import evaluate, evaluate_fights
from app.tracker.replay import replay_checkpoints

FIXTURE = Path(__file__).parents[1] / "fixtures/tracker/paired-replay-v1/opendota.json"


def evidence():
    raw = json.loads(FIXTURE.read_text())
    summary = opendota_summary(raw)
    replay = replay_checkpoints(raw, "opendota")
    features = [{"summary": player, "checkpoints": points["series"]}
                for player, points in zip(summary["players"], replay["players"], strict=True)]
    return raw, features


def test_minute_points_have_exact_tooltips_and_existing_ten_minute_delta():
    raw, features = evidence()
    context = evaluate(features, viewer=0, positions={5: 1},
                       duration=raw["duration"], quarantined=[])
    assert context["contract_version"] == "offlane-context-v2"
    assert context["enemy_carry_hero_id"] == features[5]["summary"]["hero_id"]
    for panel in (context["net_worth"], context["xp"]):
        assert panel["state"] == "AVAILABLE" and panel["reason"] is None
        assert [point["time_seconds"] for point in panel["points"]] == list(range(0, 601, 60))
        assert all(point["difference"] == point["you"] - point["enemy_carry"] for point in panel["points"])
    xp = context["xp"]["points"]
    assert xp[0]["you"] == xp[0]["enemy_carry"] == 0
    assert xp[10]["you"] == raw["players"][0]["xp_t"][10] - raw["players"][0]["xp_t"][0]
    metric = measure("offlane.lane_net_worth_advantage_at_10.v1", players=features,
                     player_slot=0, duration_seconds=raw["duration"],
                     replay_ready=True, positions={5: 1})
    assert context["net_worth"]["points"][10]["difference"] == metric.raw_value


def test_short_match_missing_points_conflicts_and_independent_panels():
    raw, features = evidence()
    short = evaluate(features, viewer=0, positions={5: 1}, duration=185, quarantined=[])
    assert [point["time_seconds"] for point in short["net_worth"]["points"]] == [0, 60, 120, 180]
    partial = deepcopy(features)
    partial[0]["checkpoints"]["xp_earned"] = None
    partial[0]["checkpoints"]["net_worth"]["60"] = None
    result = evaluate(partial, viewer=0, positions={5: 1}, duration=raw["duration"],
                      quarantined=["players.0.series.net_worth.120"])
    assert result["xp"] == {"state": "UNAVAILABLE", "reason": "TRAJECTORY_UNAVAILABLE", "points": []}
    assert result["net_worth"]["state"] == "AVAILABLE"
    assert [point["time_seconds"] for point in result["net_worth"]["points"]] == [0, *range(180, 601, 60)]


def test_ambiguous_or_missing_carry_withholds_both_panels():
    raw, features = evidence()
    for positions in ({}, {5: 1, 6: 1}):
        result = evaluate(features, viewer=0, positions=positions,
                          duration=raw["duration"], quarantined=[])
        assert result["enemy_carry_hero_id"] is None
        assert result["net_worth"]["state"] == result["xp"]["state"] == "UNAVAILABLE"
        assert result["net_worth"]["reason"] == result["xp"]["reason"] == "CARRY_UNCLEAR"


def test_detected_fights_use_player_deaths_and_preserve_overlaps():
    raw, features = evidence()
    first = deepcopy(raw["teamfights"][0])
    second = deepcopy(first)
    second["start"], second["end"] = first["end"] - 1, first["end"] + 5
    first["deaths"] = second["deaths"] = 999  # Headers can disagree with player entries.
    raw["teamfights"] = [first, second]
    fights = evaluate_fights(raw, viewer=0, duration=raw["duration"], quarantined=[])
    assert fights["state"] == "AVAILABLE"
    assert [segment["segment_index"] for segment in fights["segments"]] == [1, 2]
    assert fights["segments"][0]["end_seconds"] > fights["segments"][1]["start_seconds"]
    segment = fights["segments"][0]
    assert segment["offlaner_damage"] == first["players"][0]["damage"]
    assert segment["allied_damage_total"] == sum(player["damage"] for player in first["players"][:5])
    assert segment["damage_share"] == segment["offlaner_damage"] / segment["allied_damage_total"]
    assert segment["allied_hero_deaths"] == sum(player["deaths"] for player in first["players"][:5])
    assert segment["enemy_hero_deaths"] == sum(player["deaths"] for player in first["players"][5:])
    assert segment["death_trade"] == "UNFAVORABLE"
    dire = evaluate_fights(raw, viewer=6, duration=raw["duration"], quarantined=[])["segments"][0]
    assert dire["allied_hero_deaths"] == segment["enemy_hero_deaths"]
    assert dire["death_trade"] == "FAVORABLE"
    context = evaluate(features, viewer=0, positions={}, duration=raw["duration"],
                       quarantined=[], fights=fights)
    assert context["net_worth"]["state"] == "UNAVAILABLE"
    assert context["fights"] == fights


def test_detected_fight_zero_damage_tied_trade_and_empty_array():
    raw, _ = evidence()
    raw["teamfights"] = [deepcopy(raw["teamfights"][0])]
    fight = raw["teamfights"][0]
    fight["players"][0]["damage"] = 0
    fight["players"][0]["killed"] = {"npc_dota_hero_example": 1, "npc_dota_neutral": 5}
    for player in fight["players"]:
        player["deaths"] = 0
    result = evaluate_fights(raw, viewer=0, duration=raw["duration"], quarantined=[])
    segment = result["segments"][0]
    assert segment["damage_share"] == 0 and not segment["damage_participated"]
    assert segment["offlaner_kills"] == 1 and segment["death_trade"] == "EVEN"
    for player in fight["players"][:5]:
        player["damage"] = 0
    segment = evaluate_fights(raw, viewer=0, duration=raw["duration"], quarantined=[])["segments"][0]
    assert segment["allied_damage_total"] == 0 and segment["damage_share"] is None
    raw["teamfights"] = []
    assert evaluate_fights(raw, viewer=0, duration=raw["duration"], quarantined=[]) == {
        "state": "AVAILABLE", "reason": None, "segments": [],
    }


def test_detected_fights_fail_closed_on_missing_or_malformed_evidence():
    raw, _ = evidence()
    assert evaluate_fights(None, viewer=0, duration=raw["duration"], quarantined=[])["state"] == "UNAVAILABLE"
    assert evaluate_fights(raw, viewer=0, duration=raw["duration"],
                           quarantined=["players.0.hero_id"])["reason"] == "SOURCE_DISAGREEMENT"
    invalid = deepcopy(raw)
    invalid["teamfights"][0]["start"] = invalid["teamfights"][0]["end"]
    assert evaluate_fights(invalid, viewer=0, duration=raw["duration"], quarantined=[])["reason"] == "FIGHTS_INVALID"
    invalid = deepcopy(raw)
    invalid["teamfights"][-1]["start"] = raw["duration"]
    invalid["teamfights"][-1]["end"] = raw["duration"] + 15
    assert evaluate_fights(invalid, viewer=0, duration=raw["duration"], quarantined=[])["reason"] == "FIGHTS_INVALID"
    invalid = deepcopy(raw)
    invalid["teamfights"][0]["players"][0]["damage"] = None
    assert evaluate_fights(invalid, viewer=0, duration=raw["duration"], quarantined=[])["reason"] == "FIGHTS_INVALID"


def test_pregame_fights_are_dropped_and_final_fight_is_cut_at_match_end():
    raw, _ = evidence()
    full = evaluate_fights(raw, viewer=0, duration=raw["duration"], quarantined=[])["segments"]
    edited = deepcopy(raw)
    edited["teamfights"][0]["start"] = -30
    edited["teamfights"][-1]["end"] = raw["duration"] + 12
    result = evaluate_fights(edited, viewer=0, duration=raw["duration"], quarantined=[])
    assert result["state"] == "AVAILABLE"
    segments = result["segments"]
    assert len(segments) == len(full) - 1
    assert [segment["segment_index"] for segment in segments] == list(range(1, len(full)))
    assert segments[0]["start_seconds"] == full[1]["start_seconds"]
    assert segments[-1]["end_seconds"] == raw["duration"]
    assert segments[-1]["offlaner_damage"] == full[-1]["offlaner_damage"]
    only_pregame = deepcopy(raw)
    only_pregame["teamfights"] = [deepcopy(raw["teamfights"][0])]
    only_pregame["teamfights"][0]["start"] = -60
    only_pregame["teamfights"][0]["end"] = -5
    assert evaluate_fights(only_pregame, viewer=0, duration=raw["duration"], quarantined=[]) == {
        "state": "AVAILABLE", "reason": None, "segments": [],
    }


def test_lane_chart_needs_three_real_minutes_and_eighty_percent_coverage():
    raw, features = evidence()
    all_minutes = [f"players.0.series.net_worth.{second}" for second in range(60, 601, 60)]
    only_start = evaluate(features, viewer=0, positions={5: 1}, duration=raw["duration"],
                          quarantined=all_minutes)
    assert only_start["net_worth"] == {"state": "UNAVAILABLE", "reason": "TRAJECTORY_INCOMPLETE", "points": []}
    # 11 marks in 0-10 min: 9 present passes (81.8%), 8 present fails (72.7%).
    passes = evaluate(features, viewer=0, positions={5: 1}, duration=raw["duration"],
                      quarantined=all_minutes[:2])
    assert passes["net_worth"]["state"] == "AVAILABLE" and len(passes["net_worth"]["points"]) == 9
    fails = evaluate(features, viewer=0, positions={5: 1}, duration=raw["duration"],
                     quarantined=all_minutes[:3])
    assert fails["net_worth"]["reason"] == "TRAJECTORY_INCOMPLETE"
    too_short = evaluate(features, viewer=0, positions={5: 1}, duration=150, quarantined=[])
    assert too_short["net_worth"]["reason"] == "TRAJECTORY_INCOMPLETE"
