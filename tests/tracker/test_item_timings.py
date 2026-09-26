from __future__ import annotations

import pytest
from app.tracker import item_references, item_timings


@pytest.fixture
def reference_artifact(monkeypatch):
    monkeypatch.setattr(item_references, "artifact", lambda: ({"major_patch": "7.41"}, "test-digest"))
    monkeypatch.setattr(item_references, "reference", lambda *args: None)


def _reference_map(monkeypatch, mapping: dict[tuple, dict]):
    def reference(patch, mode, hero, role, item):
        return mapping.get((patch, mode, hero, role, item))

    monkeypatch.setattr(item_references, "reference", reference)


def _item(item_id: int, seconds: int, order: int = 1) -> dict[str, int | str]:
    key, name = item_references.KEY_ITEMS[item_id]
    return {
        "item_id": item_id,
        "item_key": key,
        "item_name": name,
        "purchase_time_seconds": seconds,
        "key_item_order": order,
    }


def _evaluate(
    purchases: list[dict[str, int | str]] | None,
    *,
    mode: str = "STANDARD",
    role: str = "CARRY",
    subpatch: str = "7.41f",
    history: dict | None = None,
) -> dict:
    player = {"player_slot": 0, "heroId": 94}
    if purchases is not None:
        player["keyItemPurchases"] = purchases
    return item_timings.evaluate(
        {
            "bucket": mode,
            "major_patch": "7.41",
            "subpatch": subpatch,
            "players": [player],
        },
        {"player_slot": 0, "effective_role": role},
        history,
        comparisons_allowed=True,
    )


def _observations(value: int, count: int, item: str = "item_bfury") -> dict[str, list[dict]]:
    return {
        "observations": [
            {
                "metric": "FIRST_KEY_ITEM_PURCHASE",
                "bucket": "STANDARD",
                "role": "CARRY",
                "hero": 94,
                "patch": "7.41",
                "item": item,
                "value": value,
            }
            for _ in range(count)
        ]
    }


def test_opendota_and_stratz_key_item_normalization_match_for_catalog():
    catalog = sorted(item_references.KEY_ITEMS.items())
    opendota_rows = [
        {"key": key if index % 2 else key.removeprefix("item_"), "time": 100 + index}
        for index, (_, (key, _)) in enumerate(catalog)
    ]
    stratz_rows = [
        {"itemId": item_id, "time": 100 + index}
        for index, (item_id, _) in enumerate(catalog)
    ]

    assert item_references.normalize_key_item_purchases(
        opendota_rows, "opendota", 10_000
    ) == item_references.normalize_key_item_purchases(stratz_rows, "stratz", 10_000)


def test_normalization_keeps_first_valid_purchase_and_orders_equal_times_by_id():
    rows = [
        {"key": "item_bfury", "time": 900},
        {"key": "bfury", "time": 800},  # rebuy; earliest valid time wins
        {"key": "item_bfury", "time": 1_000},
        {"key": "item_blink", "time": 700},
        {"key": "item_hand_of_midas", "time": 700},
        {"key": "item_assault", "time": 2_400},  # match-duration boundary is valid
        {"key": "item_heart", "time": 2_401},
        {"key": "item_heart", "time": -1},
        {"key": "item_heart", "time": "500"},
        {"key": "item_heart", "time": True},
        {"key": 114, "time": 500},
        None,
    ]

    result = item_references.normalize_key_item_purchases(rows, "opendota", 2_400)

    assert [(row["item_id"], row["purchase_time_seconds"], row["key_item_order"]) for row in result] == [
        (1, 700, 1),
        (65, 700, 2),
        (145, 800, 3),
        (112, 2_400, 4),
    ]


def test_normalization_excludes_base_items_and_keeps_upgraded_boots_and_upgrade_chain():
    excluded = [
        "boots",
        "magic_wand",
        "tango",
        "clarity",
        "branches",
        "recipe",
        "ward_observer",
    ]
    boot_ids = [48, 50, 63, 180, 214, 220, 231, 931]
    dagon_ids = [104, 201, 202, 203, 204]
    rows = [{"key": key, "time": index} for index, key in enumerate(excluded)]
    rows += [
        {"key": item_references.KEY_ITEMS[item_id][0], "time": 100 + index}
        for index, item_id in enumerate(boot_ids + dagon_ids)
    ]

    result = item_references.normalize_key_item_purchases(rows, "opendota", 1_000)

    assert [row["item_id"] for row in result] == boot_ids + dagon_ids
    assert [row["item_key"] for row in result[-len(dagon_ids):]] == [
        item_references.KEY_ITEMS[item_id][0] for item_id in dagon_ids
    ]
    assert [row["key_item_order"] for row in result[-len(dagon_ids):]] == [
        len(boot_ids) + index for index in range(1, len(dagon_ids) + 1)
    ]


def test_empty_evidence_is_available_and_missing_or_unsupported_evidence_is_unavailable(
    reference_artifact,
):
    empty = _evaluate([])
    missing = _evaluate(None)
    unsupported = _evaluate([], mode="ARCADE")

    assert empty["state"] == "AVAILABLE"
    assert empty["items"] == []
    assert empty["reference_digest"] == "test-digest"
    assert missing["state"] == "UNAVAILABLE"
    assert missing["reason"] == "SOURCE_EVIDENCE"
    assert missing["items"] == []
    assert unsupported["state"] == "UNAVAILABLE"
    assert unsupported["reason"] == "MODE"


# -- (a) personal best requires a population reference to become a card --------------


def test_personal_previous_best_needs_a_population_reference_to_become_a_card(monkeypatch, reference_artifact):
    window = _observations(1_800, 20)
    snapshot = _evaluate([_item(145, 900)], history=window)
    comparison = snapshot["items"][0]["comparison"]
    assert comparison["kind"] == "PERSONAL_PREVIOUS_BEST"

    no_reference_cards = item_timings.insight_cards(
        snapshot, hero=94, role="CARRY", mode="STANDARD", subpatch="7.41f",
    )
    assert no_reference_cards == []

    _reference_map(monkeypatch, {
        ("7.41f", "STANDARD", 94, "CARRY", "item_bfury"): {
            "median": 1_600, "p25": 700, "p10": 500, "purchase_count": 70,  # purchase misses p25 gate
        },
    })
    snapshot_with_reference = _evaluate([_item(145, 900)], history=window)
    with_reference_cards = item_timings.insight_cards(
        snapshot_with_reference, hero=94, role="CARRY", mode="STANDARD", subpatch="7.41f",
    )
    assert len(with_reference_cards) == 1
    assert with_reference_cards[0]["candidate_id"] == "OWN_HERO_ITEM"
    assert with_reference_cards[0]["slots"]["comparison_kind"] == "PERSONAL_PREVIOUS_BEST"


# -- (b) same rule applies to a boots item --------------------------------------------


def test_boots_personal_best_still_needs_a_population_reference(reference_artifact):
    window = _observations(1_800, 20, item="item_phase_boots")
    snapshot = _evaluate([_item(50, 900)], history=window)
    assert snapshot["items"][0]["comparison"]["kind"] == "PERSONAL_PREVIOUS_BEST"

    cards = item_timings.insight_cards(snapshot, hero=94, role="CARRY", mode="STANDARD", subpatch="7.41f")
    assert cards == []


# -- (c) population usual card carries N == purchase_count and the major patch --------


def test_population_usual_card_reports_purchase_count_and_major_patch(monkeypatch, reference_artifact):
    _reference_map(monkeypatch, {
        ("7.41f", "STANDARD", 94, "CARRY", "item_bfury"): {
            "median": 1_200, "p25": 600, "p10": 550, "purchase_count": 80,
        },
    })
    snapshot = _evaluate([_item(145, 450)])
    comparison = snapshot["items"][0]["comparison"]
    assert comparison["kind"] == "POPULATION_USUAL"

    cards = item_timings.insight_cards(snapshot, hero=94, role="CARRY", mode="STANDARD", subpatch="7.41f")
    assert len(cards) == 1
    card = cards[0]
    assert card["candidate_id"] == "OWN_HERO_ITEM"
    assert card["slots"]["comparison_kind"] == "POPULATION_USUAL"
    assert card["slots"]["N"] == 80
    assert card["slots"]["patch"] == "7.41"


# -- (d) personal gates: 19 vs 20 for previous best, 9 vs 10 for usual -----------------


def test_personal_previous_best_gate_is_20_prior_observations(reference_artifact):
    below = _evaluate([_item(145, 900)], history=_observations(1_800, 19))
    assert below["items"][0]["comparison"]["kind"] == "PERSONAL_USUAL"

    at_gate = _evaluate([_item(145, 900)], history=_observations(1_800, 20))
    assert at_gate["items"][0]["comparison"]["kind"] == "PERSONAL_PREVIOUS_BEST"
    assert at_gate["items"][0]["comparison"]["sample_size"] == 20


def test_personal_usual_gate_is_10_prior_observations(reference_artifact):
    below = _evaluate([_item(145, 900)], history=_observations(1_800, 9))
    assert below["items"][0]["comparison"] is None

    at_gate = _evaluate([_item(145, 900)], history=_observations(1_800, 10))
    assert at_gate["items"][0]["comparison"]["kind"] == "PERSONAL_USUAL"
    assert at_gate["items"][0]["comparison"]["sample_size"] == 10


# -- (e) a personal-usual-only item stays inline but never becomes a card -------------


def test_personal_usual_never_becomes_a_card_but_stays_inline(monkeypatch, reference_artifact):
    _reference_map(monkeypatch, {
        ("7.41f", "STANDARD", 94, "CARRY", "item_bfury"): {
            "median": 1_200, "p25": 600, "p10": 550, "purchase_count": 80,
        },
    })
    snapshot = _evaluate([_item(145, 900)], history=_observations(1_800, 15))
    comparison = snapshot["items"][0]["comparison"]
    assert comparison["kind"] == "PERSONAL_USUAL"

    cards = item_timings.insight_cards(snapshot, hero=94, role="CARRY", mode="STANDARD", subpatch="7.41f")
    assert cards == []
    # The factual timeline still carries the item and its personal comparison.
    assert snapshot["items"][0]["item_key"] == "item_bfury"


# -- (f) enemy card picks the largest delta/baseline ratio among cores ----------------


def test_enemy_card_picks_largest_ratio_among_cores_and_ignores_supports(monkeypatch):
    monkeypatch.setattr(item_references, "artifact", lambda: ({"major_patch": "7.41"}, "test-digest"))
    references = {
        ("7.41f", "STANDARD", 1, "CARRY", "item_blink"): {
            "median": 1_000, "p25": 900, "p10": 850, "purchase_count": 60,
        },
        ("7.41f", "STANDARD", 2, "MID", "item_blink"): {
            "median": 2_000, "p25": 1_900, "p10": 1_850, "purchase_count": 60,
        },
    }
    monkeypatch.setattr(
        item_references, "reference",
        lambda patch, mode, hero, role, item: references.get((patch, mode, hero, role, item)),
    )
    match = {
        "bucket": "STANDARD",
        "subpatch": "7.41f",
        "players": [
            {"team": "DIRE", "position": "POSITION_1", "heroId": 1,
             "keyItemPurchases": [_item(1, 100)]},  # small ratio: (1000-100)/1000 = 0.9
            {"team": "DIRE", "position": "POSITION_2", "heroId": 2,
             "keyItemPurchases": [_item(1, 100)]},  # bigger ratio: (2000-100)/2000 = 0.95
            {"team": "DIRE", "position": "POSITION_4", "heroId": 3,
             "keyItemPurchases": [_item(1, 1)]},  # ignored: not a core position
            {"team": "DIRE", "position": "POSITION_5", "heroId": 4,
             "keyItemPurchases": [_item(1, 1)]},  # ignored: not a core position
            {"team": "RADIANT", "position": "POSITION_1", "heroId": 5, "keyItemPurchases": []},
        ],
    }
    viewer = {"team": "RADIANT"}
    cards = item_timings.enemy_insight_cards(match, viewer)
    assert len(cards) == 1
    card = cards[0]
    assert card["candidate_id"] == "ENEMY_HERO_ITEM"
    assert card["slots"]["hero"] == 2
    assert card["slots"]["position"] == 2
    assert card["slots"]["role"] == "MID"


# -- a POPULATION_USUAL inline row needs a stricter p10 margin to become a card ------


def test_population_usual_card_needs_p10_margin_not_just_p25(monkeypatch, reference_artifact):
    _reference_map(monkeypatch, {
        ("7.41f", "STANDARD", 94, "CARRY", "item_bfury"): {
            "median": 1_200, "p25": 900, "p10": 900, "purchase_count": 80,
        },
    })
    # Beats p25/median (inline row), but 900 - 850 = 50 < margin(900) = 90: no card.
    close = _evaluate([_item(145, 850)])
    assert close["items"][0]["comparison"]["kind"] == "POPULATION_USUAL"
    assert item_timings.insight_cards(
        close, hero=94, role="CARRY", mode="STANDARD", subpatch="7.41f",
    ) == []

    # Beats the p10 margin too: 900 - 700 = 200 >= 90.
    far = _evaluate([_item(145, 700)])
    assert far["items"][0]["comparison"]["kind"] == "POPULATION_USUAL"
    cards = item_timings.insight_cards(far, hero=94, role="CARRY", mode="STANDARD", subpatch="7.41f")
    assert len(cards) == 1
    assert cards[0]["slots"]["comparison_kind"] == "POPULATION_USUAL"


# -- a card-excluded item never becomes a card, but keeps its inline comparison -------


def test_card_excluded_item_stays_inline_but_never_becomes_a_card(monkeypatch, reference_artifact):
    _reference_map(monkeypatch, {
        ("7.41f", "STANDARD", 94, "CARRY", "item_power_treads"): {
            "median": 1_200, "p25": 600, "p10": 550, "purchase_count": 80,
        },
    })
    snapshot = _evaluate([_item(63, 100)])  # item_power_treads: comfortably beats every margin
    comparison = snapshot["items"][0]["comparison"]
    assert comparison["kind"] == "POPULATION_USUAL"

    cards = item_timings.insight_cards(snapshot, hero=94, role="CARRY", mode="STANDARD", subpatch="7.41f")
    assert cards == []
    assert snapshot["items"][0]["item_key"] == "item_power_treads"


# -- (g) old-patch matches keep a timeline but never a population comparison ----------


def test_old_patch_match_has_no_population_comparisons(reference_artifact):
    assert item_references.reference("7.41e", "STANDARD", 94, "CARRY", "item_bfury") is None
    snapshot = _evaluate([_item(145, 900)], subpatch="7.41e", history=_observations(1_800, 20))
    assert snapshot["state"] == "AVAILABLE"
    assert all(
        item["comparison"] is None or item["comparison"]["kind"] != "POPULATION_USUAL"
        for item in snapshot["items"]
    )


# -- (h) Support keeps the factual timeline but never a comparison --------------------


def test_support_keeps_factual_timeline_with_null_comparison(reference_artifact, monkeypatch):
    def unexpected_reference(*args):
        raise AssertionError("support must not look up timing references")

    monkeypatch.setattr(item_references, "reference", unexpected_reference)
    snapshot = _evaluate([_item(145, 900)], role="SUPPORT", history=_observations(2_200, 20))

    assert snapshot["state"] == "AVAILABLE"
    assert snapshot["items"][0]["item_key"] == "item_bfury"
    assert snapshot["items"][0]["comparison"] is None
