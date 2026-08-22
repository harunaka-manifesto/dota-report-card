from __future__ import annotations

import json
from pathlib import Path

from scripts.hero_knowledge.validate import validate_semantic_layer

ROOT = Path(__file__).parents[2]
SEMANTICS_PATH = ROOT / "services/api/app/heroes/data/semantics/pilot-v1.json"


def test_ten_hero_semantic_pilot_is_approved_and_vocab_bounded() -> None:
    snapshot = json.loads(SEMANTICS_PATH.read_text(encoding="utf-8"))

    assert validate_semantic_layer(snapshot) == ()
    assert snapshot["review_status"] == "approved"
    assert {row["hero_id"] for row in snapshot["heroes"]} == {
        2,
        13,
        38,
        44,
        50,
        53,
        74,
        82,
        96,
        111,
    }
    assert snapshot["vocabulary"]["demands"] == [
        "commitment",
        "access",
        "repositioning",
        "economy",
        "timing",
        "execution",
        "exposure",
        "micro",
    ]


def test_pilot_covers_distinct_semantic_shapes() -> None:
    snapshot = json.loads(SEMANTICS_PATH.read_text(encoding="utf-8"))
    by_id = {row["hero_id"]: row for row in snapshot["heroes"]}

    assert "initiation" in by_id[2]["functions"]["primary"]
    assert by_id[2]["demands"]["exposure"] == "high"
    assert "mobility" in by_id[96]["functions"]["secondary"]
    assert "forced_movement" not in by_id[96]["functions"]["secondary"]
    assert "repositioning" in by_id[13]["functions"]["primary"]
    assert by_id[13]["demands"]["execution"] == "high"
    assert "save" in by_id[50]["functions"]["primary"]
    assert "global_presence" in by_id[53]["functions"]["primary"]
    assert by_id[53]["demands"]["economy"] == "high"
    assert by_id[82]["demands"]["micro"] == "high"
    assert by_id[74]["demands"]["execution"] == "high"
    assert set(by_id[2]["position_credibility"]) == {"1", "2", "3", "4", "5"}
    assert by_id[2]["position_credibility"]["3"] == "primary"
    assert all(row["review_status"] == "approved" for row in snapshot["heroes"])
