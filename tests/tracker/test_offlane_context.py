import json
from copy import deepcopy
from pathlib import Path

from app.tracker.metrics import measure
from app.tracker.normalization import opendota_summary
from app.tracker.offlane_context import evaluate
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
    assert context["contract_version"] == "offlane-context-v1"
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
