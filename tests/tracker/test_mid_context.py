import json
from copy import deepcopy
from pathlib import Path

from app.tracker.mid_context import evaluate
from app.tracker.mobile_api import MidContextView
from app.tracker.normalization import opendota_summary, stratz_summary
from app.tracker.replay import replay_checkpoints

FIXTURES = Path(__file__).parents[1] / "fixtures/tracker/paired-replay-v1"
GOLDEN = json.loads((FIXTURES.parent / "core-graphs-v1.json").read_text())


def _source(provider):
    raw = json.loads((FIXTURES / f"{provider}.json").read_text())
    summary = opendota_summary(raw) if provider == "opendota" else stratz_summary(raw)
    replay = replay_checkpoints(raw, provider)
    features = [{"summary": player, "checkpoints": points["series"]}
                for player, points in zip(summary["players"], replay["players"], strict=True)]
    duration = raw["duration"] if provider == "opendota" else raw["durationSeconds"]
    return features, duration


def test_mid_compares_exact_ten_minute_net_worth_in_both_providers():
    for provider in ("opendota", "stratz"):
        features, duration = _source(provider)
        result = evaluate(features, viewer=0, positions={5: 2}, duration=duration, quarantined=[])
        assert result["contract_version"] == "mid-context-v1"
        assert result["enemy_mid_hero_id"] == features[5]["summary"]["hero_id"]
        points = result["net_worth"]["points"]
        assert [row["time_seconds"] for row in points] == list(range(0, 601, 60))
        assert all(row["difference"] == row["you"] - row["enemy_mid"] for row in points)
        assert points[10]["you"] == features[0]["checkpoints"]["net_worth"]["600"]
        assert MidContextView.model_validate(result).model_dump() == GOLDEN[provider]["mid_context"]


def test_mid_short_match_missing_conflicted_and_ambiguous_points():
    features, duration = _source("opendota")
    short = evaluate(features, viewer=0, positions={5: 2}, duration=185, quarantined=[])
    assert [row["time_seconds"] for row in short["net_worth"]["points"]] == [0, 60, 120, 180]
    partial = deepcopy(features)
    partial[0]["checkpoints"]["net_worth"]["60"] = None
    result = evaluate(partial, viewer=0, positions={5: 2}, duration=duration,
                      quarantined=["players.5.series.net_worth.120"])
    assert [row["time_seconds"] for row in result["net_worth"]["points"]] == [0, *range(180, 601, 60)]
    for positions in ({}, {5: 2, 6: 2}):
        unclear = evaluate(features, viewer=0, positions=positions, duration=duration, quarantined=[])
        assert unclear["net_worth"]["reason"] == "MID_UNCLEAR"
        assert unclear["net_worth"]["points"] == []
    conflicted = evaluate(features, viewer=0, positions={5: 2}, duration=duration,
                          quarantined=["players.5.hero_id"])
    assert conflicted["net_worth"]["reason"] == "SOURCE_DISAGREEMENT"
