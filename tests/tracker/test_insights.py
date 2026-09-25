from app.tracker.insights import (
    _attach_optional_history,
    _counterpart,
    _vision,
    classify_tier_b,
    derive_history_observations,
    evaluate,
    from_provider_snapshot,
    global_ineligibility,
    load_retained_history,
    select,
    severity,
)


def _match(**changes):
    curve = [10000 + i * 700 for i in range(50)]
    players = [
        {
            "team": "RADIANT" if slot < 5 else "DIRE",
            "position": f"POSITION_{slot % 5 + 1}",
            "leaverStatus": "NONE",
            "stats": {"networthPerMinute": curve},
            "deathEvents": [],
        }
        for slot in range(10)
    ]
    value = {
        "bucket": "STANDARD",
        "duration_seconds": 2400,
        "num_human_players": 10,
        "players": players,
    }
    value.update(changes)
    return value


def test_global_gate_and_feeding_golden_vector_tv2():
    match = _match()
    assert global_ineligibility(match) is None
    match["players"][9]["deathEvents"] = [{"time": t} for t in range(9)]
    assert evaluate(match)["status"] == "NOT_ELIGIBLE(FEEDING)"
    assert evaluate(match)["cards"] == []


def test_no_card_is_a_valid_evaluated_result_golden_tv1():
    result = evaluate(_match(), {"team": "RADIANT", "won": True})
    assert result == {
        "status": "EVALUATED",
        "contract_version": "post-match-insights 1.0.0",
        "cards": [],
    }


def test_global_positions_and_missing_evidence_fail_closed():
    match = _match()
    match["players"][0]["position"] = "POSITION_2"
    assert global_ineligibility(match) == "POSITIONS"
    match = _match()
    match["players"][0]["stats"]["networthPerMinute"] = []
    assert global_ineligibility(match) == "NET_WORTH"


def test_tier_b_classifier_is_mirror_symmetric_and_deterministic():
    match = _match()
    for player in match["players"]:
        if player["team"] == "DIRE":
            player["stats"]["networthPerMinute"] = [
                value // 2 for value in player["stats"]["networthPerMinute"]
            ]
    first = classify_tier_b(match, "RADIANT")
    assert first == classify_tier_b(match, "RADIANT")
    mirrored = classify_tier_b(match, "DIRE")["label"]
    expected = {
        "LE": "DR",
        "DR": "LE",
        "CT": "CT",
        "UNCLEAR": "UNCLEAR",
        "SHORT_WINDOW": "SHORT_WINDOW",
    }
    if first["label"].endswith("_FOR"):
        mirror = first["label"][:-4] + "_AGAINST"
    elif first["label"].endswith("_AGAINST"):
        mirror = first["label"][:-8] + "_FOR"
    else:
        mirror = expected[first["label"]]
    assert mirrored == mirror
    assert 0 <= first["confidence"] <= 1


def test_selection_applies_single_story_rule_class_and_cap_golden_tv4():
    def card(candidate_id, band, level):
        return {"candidate_id": candidate_id, "band": band, "level": level}

    cards = [
        card("COMEBACK_WIN", 2, 1.026),
        card("LEAD_FLIP", 1, 0.262),
        card("LATE_REVERSAL", 1, 0.5),
        card("OPP_START_VS_HISTORY", 2, 1.48),
        card("ENEMY_STACKING", 2, 1.0),
        card("ENEMY_EARLY_RICH", 2, 1.0),
        card("ENEMY_EARLY_ITEM", 3, 2.429),
    ]
    assert [card["candidate_id"] for card in select(cards)] == [
        "COMEBACK_WIN",
        "OPP_START_VS_HISTORY",
        "ENEMY_STACKING",
    ]


def test_ladder_boundary_rounding():
    assert severity(12, (12, 20, 30)) == (1, 0.0)
    assert severity(30, (12, 20, 30)) == (3, 2.0)
    assert severity(11.9, (12, 20, 30)) is None


def _positions():
    return {slot: slot % 5 + 1 for slot in range(10)}


def _opendota_snapshot():
    times = list(range(0, 2401, 60))
    players = []
    for slot in (*range(5), *range(128, 133)):
        players.append(
            {
                "player_slot": slot,
                "hero_id": slot + 1,
                "account_id": None,
                "leaver_status": 0,
                "times": times,
                "networth_t": [1000 + i * 100 for i in range(len(times))],
                "lh_t": [i * 5 for i in range(len(times))],
                "deaths_log": [],
                "purchase_log": [],
            }
        )
    return {
        "match_id": 99,
        "start_time": 1000,
        "duration": 2400,
        "radiant_win": True,
        "game_mode": 22,
        "lobby_type": 7,
        "version": 1,
        "human_players": 10,
        "players": players,
    }


def _stratz_snapshot():
    players = []
    for slot in (*range(5), *range(128, 133)):
        players.append(
            {
                "playerSlot": slot,
                "isRadiant": slot < 128,
                "heroId": slot + 1,
                "leaverStatus": "NONE",
                "itemPurchases": [],
                "stats": {
                    "networth": 10000,
                    "numLastHits": 100,
                    "numDenies": 0,
                    "goldPerMinute": 300,
                    "experiencePerMinute": 300,
                    "heroDamage": 1000,
                    "towerDamage": 0,
                    "heroHealing": 0,
                    "goldSpent": 5000,
                    "level": 20,
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "networthPerMinute": [1000 + i * 100 for i in range(41)],
                    "lastHitsPerMinute": [5] * 41,
                    "campStack": [0] * 40,
                    "deathEvents": [],
                    "itemUsed": [],
                    "wards": [],
                    "wardDestruction": [],
                },
            }
        )
    return {
        "id": 99,
        "startDateTime": 1000,
        "durationSeconds": 2400,
        "didRadiantWin": True,
        "gameMode": "ALL_PICK_RANKED",
        "lobbyType": "RANKED",
        "numHumanPlayers": 10,
        "isStats": True,
        "players": players,
        "towerDeaths": [],
    }


def test_provider_snapshot_adapter_uses_existing_neutral_replay_projection():
    od = from_provider_snapshot(_opendota_snapshot(), "opendota", _positions())
    sz = from_provider_snapshot(_stratz_snapshot(), "stratz", _positions())
    assert global_ineligibility(od) is None
    assert global_ineligibility(sz) is None
    assert len(od["players"][0]["stats"]["networthPerMinute"]) == 41
    assert len(sz["players"][0]["stats"]["lastHitsPerMinute"]) == 10
    assert evaluate(od, {"team": "RADIANT", "won": True, "player_slot": 0})["status"] == "EVALUATED"
    assert evaluate(sz, {"team": "RADIANT", "won": True, "player_slot": 0})["status"] == "EVALUATED"


def test_history_counterpart_accepts_canonical_position_strings():
    players = [
        {"team": "DIRE", "position": "POSITION_3", "lane": "OFF_LANE"},
        {"team": "DIRE", "position": "POSITION_3", "lane": "SAFE_LANE"},
    ]
    viewer = {"team": "RADIANT", "lane": "OFF_LANE"}
    assert _counterpart(players, viewer, "CARRY") is players[1]


def test_stats_only_vision_tv11_unmatched_clear_is_unresolved():
    match = _match(bucket="TURBO", duration_seconds=1560)
    for player in match["players"]:
        player["stats"].update(wards=[], wardDestruction=[])
    match["players"][0]["stats"]["wards"] = [
        {"time": 400, "x": 100, "y": 100, "type": 0},
        {"time": 410, "x": 150, "y": 140, "type": 0},
        {"time": 900, "x": 120, "y": 110, "type": 0},
        {"time": 950, "x": 180, "y": 60, "type": 0},
    ]
    match["players"][5]["stats"]["wards"] = [{"time": 440, "x": 102, "y": 101, "type": 1}]
    match["players"][5]["stats"]["wardDestruction"] = [
        {"time": 450, "isWard": True},
        {"time": 470, "isWard": True},
        {"time": 1000, "isWard": True},
    ]
    cards, summary = _vision(match, "RADIANT", [0] * 50)
    assert cards == []
    assert summary == {
        "placed": 4,
        "destroyed_total": 3,
        "identified": 2,
        "quick": 2,
        "within_60s": 2,
        "clears": [
            {"time": 450, "placed_at": 400, "life": 50, "x": 100, "y": 100, "region": "OWN_HALF", "match_tier": "A"},
            {"time": 470, "placed_at": 410, "life": 60, "x": 150, "y": 140, "region": "ENEMY_HALF", "match_tier": "C"},
        ],
    }


def test_smoke_kills_enrichment_uses_bounded_windows_and_exact_counts():
    match = _match(towerDeaths=[])
    match["duration_seconds"] = 2520
    smoke_times = [600, 700, 730, 1200, 1500, 1800, 2400]
    own_smoke_times = [800]
    victims = [650, 745, 1230, 1540, 1900, 2430]
    kill_rows = [
        {"time": time, "attackerHeroId": 6, "targetHeroId": 1}
        for time in victims
    ]
    confirmed = [
        {"time": time, "targetHeroId": 1, "isSmoke": True}
        for time in (650, 745, 1540)
    ]
    for index, player in enumerate(match["players"]):
        player["heroId"] = index + 1
        used_times = smoke_times if index == 5 else own_smoke_times if index == 0 else []
        player["stats"]["itemUsed"] = [
            {"itemId": 188, "count": len(used_times)}
        ]
        player["deathEvents"] = kill_rows if index == 0 else []
        player["playbackData"] = {
            "itemUsedEvents": [
                {"itemId": 188, "time": time} for time in used_times
            ],
            "killEvents": confirmed if index == 5 else [],
        }
    cards = evaluate(match, {"team": "RADIANT", "won": False})["cards"]
    smoke = next(card for card in cards if card["candidate_id"] == "ENEMY_SMOKE_VOLUME")
    assert smoke["slots"]["rate"] == 7 * 600 / 2520
    assert smoke["enrichments"] == [{"kind": "SMOKE_TO_KILLS", "k": 5, "n": 7}]


def test_annex_output_vectors_selection_tv3_tv5_tv6_tv7_tv8_tv9_tv12_tv13():
    def card(candidate_id, band, level):
        return {"candidate_id": candidate_id, "band": band, "level": level}
    assert [c["candidate_id"] for c in select([card("ENEMY_STACKING", 3, 2.0)])] == [
        "ENEMY_STACKING"
    ]
    assert [
        c["candidate_id"]
        for c in select([card("CLOSE_MOST_OF_GAME", 1, 0.462), card("LEAD_FLIP", 1, 0.262)])
    ] == ["CLOSE_MOST_OF_GAME"]
    assert [c["candidate_id"] for c in select([card("ENEMY_EARLY_ITEM", 2, 1.375)])] == [
        "ENEMY_EARLY_ITEM"
    ]
    assert [c["candidate_id"] for c in select([card("ENEMY_EARLY_RICH", 2, 1.0)])] == [
        "ENEMY_EARLY_RICH"
    ]
    assert [
        c["candidate_id"]
        for c in select(
            [
                card("ENEMY_SMOKE_VOLUME", 2, 1.0),
                card("VISION_QUICK_CLEARS", 2, 1.0),
                card("OWN_ITEM_VS_HISTORY", 1, 0.48),
            ]
        )
    ] == ["ENEMY_SMOKE_VOLUME", "VISION_QUICK_CLEARS", "OWN_ITEM_VS_HISTORY"]
    assert [c["candidate_id"] for c in select([card("ENEMY_EARLY_RICH", 2, 1.0)])] == [
        "ENEMY_EARLY_RICH"
    ]
    assert [
        c["candidate_id"]
        for c in select(
            [
                card("LOST_FROM_AHEAD", 1, 0.027),
                card("CLOSE_MOST_OF_GAME", 1, 0.1),
                card("ENEMY_STACKING", 3, 3.0),
                card("LEAD_FLIP", 1, 0.2),
            ]
        )
    ] == ["LOST_FROM_AHEAD", "ENEMY_STACKING"]


def _history_rows(metric, values, *, item=None, patch=None):
    return [
        {
            "metric": metric,
            "bucket": "STANDARD",
            "role": "MID",
            "item": item,
            "patch": patch,
            "value": value,
            "startDateTime": 100 + index,
            "matchId": index + 1,
        }
        for index, value in enumerate(values)
    ]


def test_retained_history_line_precedence_rarity_and_integer_limits():
    match = {"bucket": "STANDARD", "startDateTime": 1000, "matchId": 999,
             "major_patch": "7.40"}
    smoke = {"candidate_id": "ENEMY_SMOKE_VOLUME", "slots": {"rate": 3.85},
             "history_line": None}
    _attach_optional_history(
        match, {}, {"observations": _history_rows("SMOKE_RATE", [*(value / 10 for value in range(10, 39)), 3.9])}, [smoke]
    )
    assert smoke["history_line"] == (
        "One of the 3 highest enemy Smoke rates across your last 30 Standard matches."
    )
    stacks = {"candidate_id": "ENEMY_STACKING", "slots": {"enemy": 12},
              "history_line": None}
    _attach_optional_history(
        match, {}, {"observations": _history_rows("STACKS", list(range(1, 31)))}, [stacks]
    )
    assert stacks["history_line"] == "The median across your last 30 Standard matches was 15.5."


def test_retained_history_item_comparator_requires_same_patch_and_margin():
    match = {"bucket": "STANDARD", "startDateTime": 1000, "matchId": 999,
             "major_patch": "7.40"}
    item = {"candidate_id": "ENEMY_EARLY_ITEM", "slots": {
        "item": "item_black_king_bar", "item_name": "Black King Bar", "time": 1000,
    }, "history_line": None}
    rows = _history_rows("ENEMY_ITEM_TIME", [1200] * 29 + [1100],
                         item="item_black_king_bar", patch="7.40")
    _attach_optional_history(match, {}, {"observations": rows}, [item])
    assert "at least 1 minute earlier" in item["history_line"]
    item["history_line"] = None
    _attach_optional_history(
        {**match, "major_patch": None}, {}, {"observations": rows}, [item]
    )
    assert item["history_line"] is None


def test_canonical_source_emits_only_measured_history_comparators():
    match = _match(towerDeaths=[])
    for slot, player in enumerate(match["players"]):
        player["player_slot"] = slot
        player["lane"] = "SAFE_LANE" if player["position"] in {"POSITION_1", "POSITION_5"} else (
            "MID_LANE" if player["position"] == "POSITION_2" else "OFF_LANE"
        )
        player["heroId"] = slot + 1
        player["campStack"] = [1] * 20
        player["stats"]["lastHitsPerMinute"] = [5] * 10
        player["stats"]["itemUsed"] = [{"itemId": 188, "count": 1}]
        player["itemPurchases"] = [{"item": "item_black_king_bar", "time": 1000}]
    # Radiant safe lane and Dire off lane occupy the same physical lane.
    match["players"][7]["lane"] = "OFF_LANE"
    result = derive_history_observations(
        match, {"team": "RADIANT", "player_slot": 0, "effective_role": "CARRY",
                "lane": "SAFE_LANE"},
        startDateTime=1000, matchId=123, major_patch="7.40",
    )
    assert {(row["metric"], row.get("item")) for row in result} == {
        ("LANE_GAP", None), ("COUNTERPART_CS", None),
        ("FIRST_PURCHASE", "item_black_king_bar"), ("STACKS", None),
        ("SMOKE_RATE", None), ("GOAL_MINUTE", None),
        ("ENEMY_ITEM_TIME", "item_black_king_bar"),
    }
    match["players"][0]["stats"].pop("itemUsed")
    assert all(row["metric"] != "SMOKE_RATE" for row in derive_history_observations(
        match, {"team": "RADIANT", "player_slot": 0, "effective_role": "CARRY",
                "lane": "SAFE_LANE"}, startDateTime=1000, matchId=123,
    ))


def test_retained_history_reads_only_prior_ready_provider_snapshots(database):
    from datetime import timedelta

    from app.tracker.materialization import materialize_snapshot
    from app.tracker.schema import account_matches, matches, profiles
    from sqlalchemy import select

    from tests.tracker.test_finalization import _ready_link, _run
    from tests.tracker.test_materialization import MATCH_ID, raw, save

    profile_id = _ready_link(database)
    with database.begin() as connection:
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(
            active_scope="PRO",
        ))
        current_time = connection.scalar(select(account_matches.c.provider_started_at).where(
            account_matches.c.profile_id == profile_id,
        ))
        prior_id = MATCH_ID - 1
        payload = raw()
        payload["match_id"] = prior_id
        payload["start_time"] -= 86400
        snapshot_id = save(connection, payload)
        projection = materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=prior_id)
        connection.execute(matches.update().where(matches.c.match_id == prior_id).values(
            evidence_state="REPLAY_READY", replay_role_assignment=projection["role_assignment"],
            started_at=current_time - timedelta(days=1),
        ))
        connection.execute(account_matches.insert().values(
            profile_id=profile_id, match_id=prior_id, account_id=1001, player_slot=0,
            lifecycle="ANALYZING", mode="STANDARD", effective_role="CARRY",
            provider_started_at=current_time - timedelta(days=1),
            provider_source_match_id=prior_id, origin="BOOTSTRAP",
        ))
    from app.tracker.finalization import complete_finalization_job, enqueue_finalization
    from app.tracker.jobs import claim

    with database.begin() as connection:
        enqueue_finalization(connection, profile_id=profile_id, match_id=prior_id)
        job = claim(connection, priority=3)
    assert complete_finalization_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "READY"
    assert _run(database, profile_id, MATCH_ID) == "READY"
    with database.connect() as connection:
        history = load_retained_history(connection, profile_id=profile_id, match_id=MATCH_ID)
    observations = history["observations"]
    assert observations
    assert all(row["matchId"] == prior_id for row in observations)
    assert {row["metric"] for row in observations} >= {"GOAL_MINUTE", "STACKS"}
    assert all(row["startDateTime"] < 2_000_000_000 for row in observations)
