import json
from copy import deepcopy
from pathlib import Path

from app.tracker.carry_context import evaluate
from app.tracker.events import replay_events
from app.tracker.normalization import opendota_summary, stratz_summary
from app.tracker.replay import replay_checkpoints

FIXTURES = Path(__file__).parents[1] / "fixtures/tracker/paired-replay-v1"


def source(provider):
    raw = json.loads((FIXTURES / f"{provider}.json").read_text())
    summary = opendota_summary(raw) if provider == "opendota" else stratz_summary(raw)
    replay = replay_checkpoints(raw, provider)
    events = replay_events(raw, provider)
    features = [
        {"summary": player, "checkpoints": points["series"], "events": event["events"]}
        for player, points, event in zip(summary["players"], replay["players"], events["players"], strict=True)
    ]
    return raw, features


def test_carry_graphs_and_annotations_use_recorded_pair():
    for provider in ("opendota", "stratz"):
        raw, features = source(provider)
        duration = raw["duration"] if provider == "opendota" else raw["durationSeconds"]
        result = evaluate(features, viewer=0, positions={5: 1}, duration=duration,
                          quarantined=[], raw=raw, provider=provider)
        assert result["contract_version"] == "carry-context-v1"
        assert result["enemy_carry_hero_id"] == features[5]["summary"]["hero_id"]
        for key in ("net_worth", "hero_damage"):
            points = result[key]["points"]
            assert result[key]["state"] == "AVAILABLE"
            assert [p["time_seconds"] for p in points] == list(range(0, 3541, 60))
            assert all(p["difference"] == p["you"] - p["enemy_carry"] for p in points)
            assert points[-1]["time_seconds"] < duration
        assert result["hero_damage"]["points"][0]["you"] == 0
        assert result["hero_damage"]["points"][10]["you"] == features[0]["checkpoints"]["hero_damage_earned"]["600"]
        assert result["enemy_key_items"]["state"] == "AVAILABLE"
        assert result["enemy_key_items"]["items"]
        for side in ("you_kills", "enemy_carry_kills"):
            assert result[side]["state"] == "AVAILABLE"
            assert [e["time_seconds"] for e in result[side]["events"]] == sorted(
                e["time"] for e in features[0 if side == "you_kills" else 5]["events"]["kills"]
            )


def test_missing_damage_does_not_hide_net_worth_items_or_kills():
    raw, features = source("stratz")
    partial = deepcopy(features)
    partial[0]["checkpoints"]["hero_damage_earned"] = None
    result = evaluate(partial, viewer=0, positions={5: 1}, duration=raw["durationSeconds"],
                      quarantined=[], raw=raw, provider="stratz")
    assert result["hero_damage"]["state"] == "UNAVAILABLE"
    assert result["net_worth"]["state"] == "AVAILABLE"
    assert result["enemy_key_items"]["state"] == "AVAILABLE"
    assert result["you_kills"]["state"] == "AVAILABLE"


def test_short_match_conflicts_ambiguous_enemy_and_invalid_annotations():
    raw, features = source("opendota")
    short = evaluate(features, viewer=0, positions={5: 1}, duration=185,
                     quarantined=[], raw=raw, provider="opendota")
    assert [p["time_seconds"] for p in short["net_worth"]["points"]] == [0, 60, 120, 180]
    conflicted = evaluate(features, viewer=0, positions={5: 1}, duration=raw["duration"],
                          quarantined=["players.0.series.net_worth.60"], raw=raw,
                          provider="opendota")
    assert 60 not in [p["time_seconds"] for p in conflicted["net_worth"]["points"]]
    assert conflicted["hero_damage"]["state"] == "AVAILABLE"
    kill_conflict = evaluate(features, viewer=0, positions={5: 1}, duration=raw["duration"],
                             quarantined=["players.5.values.kills"], raw=raw, provider="opendota")
    assert kill_conflict["enemy_carry_kills"]["reason"] == "SOURCE_DISAGREEMENT"
    assert kill_conflict["you_kills"]["state"] == "AVAILABLE"
    ambiguous = evaluate(features, viewer=0, positions={5: 1, 6: 1}, duration=raw["duration"],
                         quarantined=[], raw=raw, provider="opendota")
    assert all(ambiguous[key]["reason"] == "CARRY_UNCLEAR" for key in (
        "net_worth", "hero_damage", "enemy_key_items", "you_kills", "enemy_carry_kills"
    ))
    partial = deepcopy(features)
    partial[0]["events"]["kills"] = None
    no_kills = evaluate(partial, viewer=0, positions={5: 1}, duration=raw["duration"],
                        quarantined=[], raw=raw, provider="opendota")
    assert no_kills["you_kills"]["state"] == "UNAVAILABLE"
    assert no_kills["enemy_carry_kills"]["state"] == "AVAILABLE"


def test_damage_translation_and_duplicate_key_item_rule():
    od, od_features = source("opendota")
    sz, sz_features = source("stratz")
    assert od_features[0]["checkpoints"]["hero_damage_earned"]["600"] == (
        od["players"][0]["hero_damage_t"][10] - od["players"][0]["hero_damage_t"][0]
    )
    assert sz_features[0]["checkpoints"]["hero_damage_earned"]["600"] == sum(
        sz["players"][0]["stats"]["heroDamagePerMinute"][:10]
    )
    first = od["players"][5]["purchase_log"][0]
    od["players"][5]["purchase_log"].append(dict(first))
    result = evaluate(od_features, viewer=0, positions={5: 1}, duration=od["duration"],
                      quarantined=[], raw=od, provider="opendota")
    ids = [item["item_id"] for item in result["enemy_key_items"]["items"]]
    assert len(ids) == len(set(ids))


def test_kills_keep_exact_seconds_and_exclude_pregame_events():
    raw, features = source("opendota")
    features[0]["events"]["kills"] = [{"time": -5}, {"time": 125}, {"time": 125}]
    result = evaluate(features, viewer=0, positions={5: 1}, duration=raw["duration"],
                      quarantined=[], raw=raw, provider="opendota")
    assert result["you_kills"]["events"] == [
        {"time_seconds": 125}, {"time_seconds": 125},
    ]


def test_paired_damage_disagreement_does_not_withhold_cards_or_comparisons():
    from app.tracker.finalization import _decision_conflicts
    from app.tracker.replay import quarantine_checkpoint_conflicts

    od, _ = source("opendota")
    sz, _ = source("stratz")
    conflicts = quarantine_checkpoint_conflicts(
        replay_checkpoints(od, "opendota"), replay_checkpoints(sz, "stratz"),
    )["conflicts"]
    assert any(".series.hero_damage_earned." in path for path in conflicts)
    assert not any(".series.hero_damage_earned." in path for path in _decision_conflicts(conflicts))
    assert any(".series.xp_earned." in path for path in conflicts)
    assert not any(".series.xp_earned." in path for path in _decision_conflicts(conflicts))
    assert _decision_conflicts(["players.0.series.net_worth.600"]) == ["players.0.series.net_worth.600"]


def test_chart_left_with_only_the_start_minute_is_incomplete():
    """Paired sources disagree on slot 3's damage at every minute after 0:00."""
    from app.tracker.replay import quarantine_checkpoint_conflicts

    od, features = source("opendota")
    sz, _ = source("stratz")
    conflicts = quarantine_checkpoint_conflicts(
        replay_checkpoints(od, "opendota"), replay_checkpoints(sz, "stratz"),
    )["conflicts"]
    viewer = 5  # Dire viewer; slot 3 is the Radiant carry.
    result = evaluate(features, viewer=viewer, positions={3: 1}, duration=od["duration"],
                      quarantined=conflicts, raw=od, provider="opendota")
    assert result["hero_damage"] == {"state": "UNAVAILABLE", "reason": "TRAJECTORY_INCOMPLETE", "points": []}
    assert result["net_worth"]["state"] == "AVAILABLE"
