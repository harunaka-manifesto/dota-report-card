"""Item-level population reference builder: thresholds, coverage and de-identification."""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.build_item_references import compose

ITEM = 116  # item_black_king_bar; never suspended, never a boot.


def _shard(counts: dict[str, int]) -> dict:
    return {"patch": "7.41f", "counts": counts, "ordered_counts": {}}


def test_purchase_count_gate_is_50_not_49():
    below = compose([_shard({
        "STANDARD:201:CARRY:games": 200,
        f"STANDARD:201:CARRY:{ITEM}:10": 49,
    })])
    assert "STANDARD:201:CARRY:item_black_king_bar" not in below["references"]
    assert below["coverage"]["STANDARD:201:CARRY"]["reason"] == "no_qualified_item"

    at_gate = compose([_shard({
        "STANDARD:201:CARRY:games": 200,
        f"STANDARD:201:CARRY:{ITEM}:10": 50,
    })])
    reference = at_gate["references"]["STANDARD:201:CARRY:item_black_king_bar"]
    assert reference["purchase_count"] == 50
    assert reference["cohort_games"] == 200
    assert at_gate["coverage"]["STANDARD:201:CARRY"]["items"] == ["item_black_king_bar"]
    assert at_gate["coverage"]["STANDARD:201:CARRY"]["reason"] is None


def test_purchase_rate_gate_is_20_percent_not_19():
    below = compose([_shard({
        "STANDARD:202:MID:games": 500,
        f"STANDARD:202:MID:{ITEM}:10": 95,  # 19%
    })])
    assert "STANDARD:202:MID:item_black_king_bar" not in below["references"]
    assert below["coverage"]["STANDARD:202:MID"]["reason"] == "no_qualified_item"

    at_gate = compose([_shard({
        "STANDARD:202:MID:games": 500,
        f"STANDARD:202:MID:{ITEM}:10": 100,  # 20%
    })])
    reference = at_gate["references"]["STANDARD:202:MID:item_black_king_bar"]
    assert reference["purchase_rate"] == 0.2


def test_no_five_item_cap_all_qualifying_items_kept():
    hero = 200  # not in SUSPENDED_HEROES
    items = [1, 65, 90, 98, 108, 110]  # blink, midas, pipe, orchid, scepter, refresher
    counts = {f"STANDARD:{hero}:OFFLANE:games": 1000}
    for item in items:
        counts[f"STANDARD:{hero}:OFFLANE:{item}:10"] = 250  # 25% purchase rate each
    result = compose([_shard(counts)])
    qualifying = [
        key for key in result["references"] if key.startswith(f"STANDARD:{hero}:OFFLANE:")
    ]
    assert len(qualifying) == len(items) == 6
    assert set(result["coverage"][f"STANDARD:{hero}:OFFLANE"]["items"]) == {
        "item_blink", "item_hand_of_midas", "item_pipe", "item_orchid",
        "item_ultimate_scepter", "item_refresher",
    }


def test_suspended_hero_yields_patch_change_pending_and_no_reference():
    result = compose([_shard({
        "STANDARD:70:CARRY:games": 200,
        f"STANDARD:70:CARRY:{ITEM}:10": 100,
    })])
    assert "STANDARD:70:CARRY:item_black_king_bar" not in result["references"]
    assert result["coverage"]["STANDARD:70:CARRY"]["reason"] == "patch_change_pending"


IDENTIFIER_KEYS = ("account_id", "match_id", "player_slot", "account_pseudonym")
IDENTIFIER_PATTERN = re.compile("|".join(IDENTIFIER_KEYS))


def test_checked_in_artifact_is_schema_3_complete_and_deidentified():
    path = Path(__file__).parents[2] / "services/api/app/tracker/item_references.json"
    body = path.read_bytes()
    artifact = json.loads(body)
    assert artifact["schema"] == 3
    assert len(artifact["coverage"]) == 762
    assert len(artifact["references"]) > 0
    assert {row["reason"] for row in artifact["coverage"].values()} <= {
        None, "sparse", "patch_change_pending", "no_qualified_item",
    }
    assert not IDENTIFIER_PATTERN.search(body.decode())

    shard_dir = path.with_name("item_shards")
    for shard_path in shard_dir.glob("7.41*.json"):
        assert not IDENTIFIER_PATTERN.search(shard_path.read_text())
