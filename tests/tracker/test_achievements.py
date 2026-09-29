"""Small, recorded-shape checks for the 24 frozen match rules."""
from copy import deepcopy

import pytest
from app.tracker.achievement_catalog import (
    COPY,
    RATE_COUNTS,
    REPEATABLE_IDS,
    band,
    catalog_entry,
    rarity,
    rarity_key,
)
from app.tracker.achievement_rules import BADGE_TIERS, REPEATABLE_FEATS, THRESHOLDS, rules_digest
from app.tracker.achievements import IDS, evaluate_match, gold_advantage_valid
from app.tracker.materialization import _achievement_source, _gold_advantage


def roster():
    rows = []
    for _slot in range(10):
        rows.append({
            "summary": {"hero_id": 7, "values": {"kills": 2, "assists": 2, "deaths": 2,
                        "tower_damage": 1000, "hero_healing": 0}},
            "checkpoints": {"net_worth": {"600": 1000, "1200": 3000},
                            "last_hits": {"600": 20}, "camps_stacked": {"1200": 0}},
            "events": {"dead_intervals": [], "dead_intervals_complete": True, "wards": []},
            "achievement_source": {"observer_kills": 0, "disable_seconds": 0,
                                   "hero_kill_times": [], "death_times": []},
            "match": {"radiant_gold_advantage": {str(m * 60): 0 for m in range(31)}},
        })
    return rows


def fight(**changes):
    return {"start_seconds": 125, "end_seconds": 175, "player_damage": 2000,
            "allied_damage_total": 4000, "damage_share": .5, "player_kills": 0,
            "player_deaths": 0, "enemy_hero_deaths": 2, "allied_hero_deaths": 1,
            "death_trade": "FAVORABLE", **changes}


def earned(rows, *, slot=0, role="CARRY", mode="STANDARD", fights=None, pb=None,
           prior=None, repeatable=None, pb_ready_count=4):
    result = evaluate_match(features=rows, slot=slot, role=role, mode=mode,
        progression=mode, duration=1800,
        positions={i: i % 5 + 1 for i in range(10)},
        core_fights={"state": "AVAILABLE", "segments": fights} if fights is not None else None,
        pb_metrics=pb or [], pb_ready_count=pb_ready_count, prior=prior or [],
        repeatable=repeatable or set(REPEATABLE_IDS), quarantined=[])
    return {award["id"] for award in result["awards"]}, result


@pytest.mark.parametrize("ident,slot,role,change,fights,pb,prior", [
    (1, 0, "CARRY", {}, None, ["a", "b"], None),
    (2, 0, "CARRY", {}, None, ["a", "b", "c"], None),
    (4, 0, "CARRY", {}, None, ["a"], [{"hero_id": 8, "result": {"achievement_pb_metrics": ["a"]}}]),
    (6, 0, "CARRY", {"checkpoints.last_hits.600": 60, "checkpoints.net_worth.1200": 12500}, None, None, None),
    (8, 1, "MID", {"checkpoints.net_worth.600": 500, "checkpoints.net_worth.1200": 3500}, None, None, None),
    (10, 0, "CARRY", {"checkpoints.net_worth.1200": 8000}, None, None, None),
    (11, 1, "MID", {"checkpoints.net_worth.600": 3000, "summary.values.tower_damage": 5000}, None, None, None),
    (13, 0, "CARRY", {"summary.values.assists": 4, "summary.values.deaths": 1}, None, None, None),
    (14, 0, "CARRY", {"summary.values.assists": 10, "summary.values.deaths": 0}, None, None, None),
    (15, 0, "CARRY", {"summary.values.kills": 10, "summary.values.deaths": 0}, None, None, None),
    (17, 0, "CARRY", {"summary.values.kills": 5,
                       "achievement_source.hero_kill_times": [100, 110, 130, 150, 180]}, None, None, None),
    (18, 0, "CARRY", {"achievement_source.hero_kill_times": [100, 500]}, None, None, None),
    (20, 0, "CARRY", {}, [fight(player_kills=3)], None, None),
    (22, 0, "CARRY", {}, [fight(), fight(start_seconds=200, end_seconds=240)], None, None),
    (23, 0, "CARRY", {}, [fight(enemy_hero_deaths=5, allied_hero_deaths=0)], None, None),
    (25, 0, "CARRY", {"match.radiant_gold_advantage": {str(m * 60): 0 if m == 0 else -6000 for m in range(31)}}, [fight()], None, None),
    (30, 0, "CARRY", {"summary.values.assists": 10, "summary.values.deaths": 0}, None, None,
     [{"hero_id": 7, "result": {"achievements": {"awards": [{"id": 14}]}}},
      {"hero_id": 7, "result": {"achievements": {"awards": [{"id": 14}]}}}]),
    (37, 3, "SUPPORT", {"achievement_source.observer_kills": 5,
                         "events.wards": [{"type": "OBSERVER"}] * 5}, None, None, None),
    (41, 3, "SUPPORT", {"checkpoints.camps_stacked.1200": 5,
                         "summary.values.assists": 3}, None, None, None),
    (42, 3, "SUPPORT", {"achievement_source.observer_kills": 3,
                         "summary.values.assists": 4}, None, None, None),
    (44, 2, "OFFLANE", {"summary.values.tower_damage": 2500}, None, None, None),
    (45, 0, "CARRY", {"summary.values.tower_damage": 4000,
                       "summary.values.deaths": 0}, None, None, None),
    (49, 3, "SUPPORT", {"summary.values.hero_healing": 8000,
                         "summary.values.assists": 10}, None, None, None),
    (50, 3, "SUPPORT", {"achievement_source.disable_seconds": 120,
                         "summary.values.assists": 10}, None, None, None),
])
def test_each_frozen_rule(ident, slot, role, change, fights, pb, prior):
    rows = roster()
    for path, value in change.items():
        target = rows[slot]
        parts = path.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    if ident == 8:
        rows[6]["checkpoints"]["net_worth"] = {"600": 1000, "1200": 3000}
    ids, _ = earned(rows, slot=slot, role=role, fights=fights, pb=pb, prior=prior)
    assert ident in ids


def test_missing_is_not_zero_and_turbo_cannot_earn():
    rows = roster()
    rows[0]["summary"]["values"].update(assists=10, deaths=0)
    assert 14 in earned(rows)[0]
    assert not earned(rows, mode="TURBO")[0]
    rows[0]["summary"]["values"]["deaths"] = None
    ids, result = earned(rows)
    assert 14 not in ids and 14 not in result["evaluable_ids"]
    rows[3]["achievement_source"]["observer_kills"] = None
    _, result = earned(rows, slot=3, role="SUPPORT")
    assert 37 not in result["evaluable_ids"]
    rows[3]["achievement_source"]["observer_kills"] = 0
    _, result = earned(rows, slot=3, role="SUPPORT")
    assert 37 in result["evaluable_ids"]


def test_overlap_chronology_and_nonoverlap():
    rows = roster()
    rows[0]["summary"]["values"].update(kills=10, assists=10, deaths=0)
    ids, _ = earned(rows, pb=["a", "b", "c"])
    assert {1, 2, 13, 14, 15} <= ids
    overlap = [fight(start_seconds=125, end_seconds=175),
               fight(start_seconds=160, end_seconds=210)]
    assert 22 not in earned(rows, fights=overlap)[0]
    first = {"hero_id": 7, "result": {"achievements": {"awards": [{"id": 14}]}}}
    prior = [deepcopy(first), {**deepcopy(first), "hero_id": 8}]
    assert 30 not in earned(rows, prior=prior)[0]


def test_catalog_and_validated_opendota_source_shape():
    assert set(COPY) == set(IDS)
    assert set(RATE_COUNTS) <= set(IDS)
    assert catalog_entry(50, "id")["asset_key"] == "match-achievement-50"
    assert rarity(50)["tier"] == "RARE"
    raw = {"players": [{"player_slot": 0, "observer_kills": 2, "kills": 1,
                        "killed": {"npc_dota_observer_wards": 2}, "stuns": 120.5,
                        "kills_log": [{"time": 4, "key": "npc_dota_hero_axe"},
                                      {"time": 5, "key": "npc_dota_observer_wards"}]}]}
    source = _achievement_source(raw, "opendota", 0)
    assert source == {"observer_kills": 2, "disable_seconds": 120.5, "hero_kill_times": [4],
                      "death_times": None}  # no deaths_log: withheld, never zero
    raw["players"][0].update(deaths=2, deaths_log=[{"time": 30}, {"time": 700, "time_dead": None}])
    assert _achievement_source(raw, "opendota", 0)["death_times"] == [30, 700]
    raw["players"][0]["deaths"] = 3  # summary disagrees with the log
    assert _achievement_source(raw, "opendota", 0)["death_times"] is None
    raw["players"][0]["observer_kills"] = 3
    assert _achievement_source(raw, "opendota", 0)["observer_kills"] is None
    assert _gold_advantage({"radiant_gold_adv": [0, -200, -300]}, "opendota", 120) == {"0": 0, "60": -200, "120": -300}
    # Clock contract: nonzero origin or a map short of the last full minute is unusable.
    assert _gold_advantage({"radiant_gold_adv": [403, -200, -300]}, "opendota", 120) == {
        "0": 403, "60": -200, "120": -300}  # index 0 is a real 0:00 reading, not necessarily 0
    assert _gold_advantage({"radiant_gold_adv": [0, -200]}, "opendota", 120) is None


def test_gold_clock_contract_gates_fight_25():
    good = {str(m * 60): 0 if m == 0 else -6000 for m in range(31)}
    assert gold_advantage_valid(good, 1800)
    assert gold_advantage_valid({**good, "0": 403}, 1800)  # nonzero origin is a real reading
    assert not gold_advantage_valid({k: v for k, v in good.items() if k != "600"}, 1800)
    assert not gold_advantage_valid({k: v for k, v in good.items() if int(k) <= 1200}, 1800)
    assert not gold_advantage_valid(None, 1800)
    rows = roster()
    rows[0]["match"]["radiant_gold_advantage"] = good
    assert 25 in earned(rows, fights=[fight()])[0]
    rows[0]["match"]["radiant_gold_advantage"] = {k: v for k, v in good.items() if k != "600"}
    ids, result = earned(rows, fights=[fight()])
    assert 25 not in ids and 25 not in result["evaluable_ids"]
    assert {"id": 25, "reason": "EVIDENCE_MISSING"} in result["unavailable"]
    # A fight before the first minute checkpoint has no real gold reading to use.
    rows[0]["match"]["radiant_gold_advantage"] = good
    assert 25 not in earned(rows, fights=[fight(start_seconds=30, end_seconds=50)])[0]


def test_role_peer_requires_matching_positions():
    rows = roster()
    rows[1]["checkpoints"]["net_worth"] = {"600": 500, "1200": 3500}
    rows[6]["checkpoints"]["net_worth"] = {"600": 1000, "1200": 3000}
    assert 8 in earned(rows, slot=1, role="MID")[0]
    # Own role corrected away from the assigned position: peer comparison is unavailable.
    _, result = earned(rows, slot=1, role="OFFLANE")
    assert 8 not in result["evaluable_ids"]
    # Two enemies at the peer position is ambiguous and never guessed.
    result = evaluate_match(features=rows, slot=1, role="MID", mode="STANDARD", progression="STANDARD",
        duration=1800, positions={**{i: i % 5 + 1 for i in range(10)}, 7: 2}, core_fights=None,
        pb_metrics=[], pb_ready_count=0, prior=[], repeatable=set(), quarantined=[])
    assert 8 not in result["evaluable_ids"]


def test_unavailable_reasons_are_explicit():
    rows = roster()
    _, result = earned(rows, pb_ready_count=0)
    reasons = {u["id"]: u["reason"] for u in result["unavailable"]}
    assert reasons[1] == "INSUFFICIENT_HISTORY" and reasons[30] == "INSUFFICIENT_HISTORY"
    assert reasons[20] == "EVIDENCE_MISSING"  # no detected-fight evidence supplied
    assert 14 not in reasons and 37 not in reasons  # support-only badge never listed for Carry
    short = evaluate_match(features=rows, slot=0, role="CARRY", mode="STANDARD", progression="STANDARD",
        duration=900, positions={}, core_fights=None, pb_metrics=[], pb_ready_count=5, prior=[],
        repeatable=set(), quarantined=[])
    assert {"id": 6, "reason": "MATCH_TOO_SHORT"} in short["unavailable"]
    assert set(short["evaluable_ids"]) | {u["id"] for u in short["unavailable"]} >= {6, 10, 14}


def test_frozen_rule_artifact_is_pinned():
    assert set(THRESHOLDS) == set(IDS)
    assert REPEATABLE_FEATS <= set(THRESHOLDS) - {30}
    # Any threshold or repeat-list change must bump RULE_VERSION and this digest together.
    assert rules_digest() == (
        "166964eb03267b96d14fbbe99d3471702d7929120e1fe1e75221d92b4ef9d382")


def test_early_duelist_needs_complete_death_times_not_respawn_durations():
    rows = roster()
    rows[0]["achievement_source"].update(hero_kill_times=[100, 500], death_times=[700])
    assert 18 in earned(rows)[0]
    rows[0]["achievement_source"]["death_times"] = [550]
    assert 18 not in earned(rows)[0]
    rows[0]["achievement_source"]["death_times"] = None
    ids, result = earned(rows)
    assert 18 not in ids and 18 not in result["evaluable_ids"]


def test_frozen_tiers_cover_all_badges_and_match_the_corpus_bands():
    assert set(BADGE_TIERS) == set(IDS)
    # Every tier is populated, and each measured badge sits in its frozen band.
    assert set(BADGE_TIERS.values()) == {"COMMON", "RARE", "EPIC", "LEGENDARY"}
    for ident, (hits, eligible, _) in RATE_COUNTS.items():
        assert band(hits / eligible) == BADGE_TIERS[ident], ident
    assert set(RATE_COUNTS) == set(IDS) - {1, 2, 4, 30}
    # The tier is frozen data: a live-looking rate can never change it.
    assert rarity(14)["tier"] == "LEGENDARY" and rarity(14)["provisional"] is False
    assert rarity(1)["rate"] is None and rarity(1)["tier"] == "EPIC"
    assert 42 not in REPEATABLE_FEATS  # the only Common badge is never a #30 base
    assert min(IDS, key=rarity_key) in {14, 15, 45, 2}
    assert catalog_entry(1, "en")["order"] == 1 and catalog_entry(50, "id")["order"] == 24
    assert [catalog_entry(i, "en")["order"] for i in IDS] == list(range(1, 25))


def prior_4(hero, metrics, awards=()):
    return {"hero_id": hero, "result": {"achievement_pb_metrics": metrics,
            "achievements": {"awards": [{"id": i} for i in awards]}}}


def test_record_on_new_hero_is_once_per_hero_and_needs_a_new_hero_for_that_metric():
    rows = roster()
    prior = [prior_4(8, ["a"]), prior_4(9, ["b"])]
    ids, result = earned(rows, pb=["a"], prior=prior)
    assert 4 in ids
    assert next(a for a in result["awards"] if a["id"] == 4)["proof"]["metric_ids"] == ["a"]
    # Hero 7 already earned #4 once: another metric on the same hero never repeats it.
    assert 4 not in earned(rows, pb=["b"], prior=[*prior, prior_4(7, ["a"], awards=[4])])[0]
    # The same hero already held this metric's record: not a new hero for that metric.
    assert 4 not in earned(rows, pb=["a"], prior=[prior_4(7, ["a"]), prior_4(8, ["a"])])[0]
    # Several qualifying metrics in one match are still one award.
    ids, result = earned(rows, pb=["a", "b"], prior=prior)
    assert [a["id"] for a in result["awards"]].count(4) == 1
    # A history built under other rules is not judged.
    _, result = earned(rows, pb=["a"], prior=prior, )
    assert 4 in result["evaluable_ids"]
    incomplete = evaluate_match(features=rows, slot=0, role="CARRY", mode="STANDARD", progression="STANDARD",
        duration=1800, positions={}, core_fights=None, pb_metrics=["a"], pb_ready_count=4, prior=prior,
        repeatable=set(), quarantined=[], history_complete=False)
    assert 4 not in incomplete["evaluable_ids"] and 30 not in incomplete["evaluable_ids"]


def test_hero_specialist_proof_reports_the_named_feats_own_count():
    rows = roster()
    rows[0]["summary"]["values"].update(assists=10, deaths=0, kills=10)  # earns #14 and #15
    three = [prior_4(7, [], awards=[14]), prior_4(7, [], awards=[14]), prior_4(7, [], awards=[14, 15])]
    ids, result = earned(rows, prior=three)
    proof = next(a for a in result["awards"] if a["id"] == 30)["proof"]
    # #14 has 4 matches, #15 has 2: the proof names #14 and reports 4, never a mix.
    assert proof == {"hero_id": 7, "feat_id": 14, "distinct_matches": 4}
    # A tie names the lowest id.
    tie = [prior_4(7, [], awards=[14, 15]), prior_4(7, [], awards=[14, 15]), prior_4(7, [], awards=[14, 15])]
    proof = next(a for a in earned(rows, prior=tie)[1]["awards"] if a["id"] == 30)["proof"]
    assert proof["feat_id"] == 14 and proof["distinct_matches"] == 4


def test_ineligible_standard_match_is_explicitly_ineligible_not_empty():
    result = evaluate_match(features=roster(), slot=0, role="CARRY", mode="STANDARD", progression="NONE",
        duration=1800, positions={}, core_fights=None, pb_metrics=[], pb_ready_count=0, prior=[],
        repeatable=set(), quarantined=[])
    assert result["eligible"] is False and not result["awards"] and not result["unavailable"]
    assert earned(roster())[1]["eligible"] is True


def test_real_zeros_are_evidence_not_gaps():
    rows = roster()
    for row in rows:
        row["summary"]["values"].update(kills=0, assists=0, tower_damage=0)
    _, result = earned(rows, slot=3, role="SUPPORT")
    assert {13, 41, 42} <= set(result["evaluable_ids"])
    _, mid = earned(rows, slot=1, role="MID")
    assert 13 in mid["evaluable_ids"]
    _, off = earned(rows, slot=2, role="OFFLANE")
    assert 44 in off["evaluable_ids"] and 45 not in off["evaluable_ids"]  # #45 is Carry/Mid only
    _, carry = earned(rows)
    assert 45 in carry["evaluable_ids"] and 45 not in {a["id"] for a in carry["awards"]}


def test_kill_log_must_match_the_summary_exactly_and_below_threshold_does_not_award():
    raw = {"players": [{"player_slot": 0, "kills": 5, "deaths": 0, "deaths_log": [],
                        "kills_log": [{"time": t, "key": "npc_dota_hero_axe"} for t in (1, 2, 3, 4)]}]}
    assert _achievement_source(raw, "opendota", 0)["hero_kill_times"] is None  # log short of 5 kills
    raw["players"][0]["kills_log"].append({"time": 5, "key": "npc_dota_hero_axe"})
    assert _achievement_source(raw, "opendota", 0)["hero_kill_times"] == [1, 2, 3, 4, 5]
    rows = roster()
    rows[0]["summary"]["values"].update(assists=9, deaths=0, kills=9)
    assert not {14, 15} & earned(rows)[0]  # one below each threshold
