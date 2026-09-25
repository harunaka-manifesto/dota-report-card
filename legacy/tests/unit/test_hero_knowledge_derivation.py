from __future__ import annotations

import json
from pathlib import Path

from scripts.hero_knowledge.derive.behavior import derive_behavior
from scripts.hero_knowledge.derive.mechanics import derive_mechanics
from scripts.hero_knowledge.valve.normalize import normalize_hero_detail, normalize_hero_list

FIXTURES = Path(__file__).parents[1] / "fixtures" / "hero_knowledge" / "valve"


def _hero(filename: str, hero_id: int) -> dict:
    identities = normalize_hero_list(
        json.loads((FIXTURES / "herolist.json").read_text(encoding="utf-8"))
    )
    identity = next(item for item in identities if item.hero_id == hero_id)
    return normalize_hero_detail(
        json.loads((FIXTURES / filename).read_text(encoding="utf-8")),
        identity,
        source_url="https://www.dota2.com/datafeed/herodata",
        fetched_at="2026-08-22T00:00:00Z",
    )


def test_mechanical_rules_emit_provenance_and_do_not_fill_unmatched_fields() -> None:
    result = derive_mechanics(_hero("axe.json", 2))

    assert result["capabilities"]["initiation"]["band"] == "medium"
    assert result["capabilities"]["frontline"]["band"] == "high"
    assert result["capabilities"]["sustained_damage"]["derived_from"] == [
        "ability:axe_battle_hunger"
    ]
    assert result["capabilities"]["initiation"]["rule_version"] == "mechanic-rules-1.0.0"
    assert "save" not in result["capabilities"]


def test_mobility_and_execution_are_derived_from_mechanics() -> None:
    result = derive_mechanics(_hero("puck.json", 13))

    assert result["capabilities"]["mobility"]["derived_from"] == ["ability:puck_ethereal_jaunt"]
    assert result["capabilities"]["repositioning"]["band"] == "medium"


def test_behavior_uses_explicit_unknown_for_small_samples() -> None:
    result = derive_behavior(
        {
            "bracket_performance": [
                {"population": "public_aggregate", "picks": 3, "wins": 1}
            ],
            "duration_profile": [],
            "item_profile": [],
            "matchup_profile": [],
            "provenance": {"source": "opendota.heroStats"},
        },
        minimum_matches=20,
    )

    assert result["role_flexibility"]["band"] == "unknown"
    assert result["item_dependency"]["band"] == "unknown"
    assert result["meta_confidence"]["band"] == "unknown"
