from app.tracker.insights import classify_tier_b, evaluate, global_ineligibility, select, severity


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


def test_global_positions_and_missing_evidence_fail_closed():
    match = _match()
    match["players"][0]["position"] = "POSITION_2"
    assert global_ineligibility(match) == "POSITIONS"
    match = _match()
    match["players"][0]["stats"]["networthPerMinute"] = []
    assert global_ineligibility(match) == "NET_WORTH"


def test_tier_b_classifier_is_mirror_symmetric_and_deterministic():
    match = _match()
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
    assert mirrored == expected.get(
        first["label"], first["label"].replace("_FOR", "_AGAINST").replace("_AGAINST", "_FOR")
    )
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
