"""Frozen, versioned thresholds for match-achievements-v1.

Changing any value here changes what the badge means: bump RULE_VERSION, update the
pinned digest in tests/tracker/test_achievements.py, and replay through the
methodology rebuild. Copy, rarity and asset keys live in achievement_catalog.py.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

RULE_VERSION = "match-achievements-v1"

THRESHOLDS: dict[int, dict[str, Any]] = {
    6: {"min_duration": 1200, "last_hits_at_600": 60, "net_worth_at_1200": 12500},
    8: {"min_duration": 1200, "gap_at_600_max": -500, "gap_at_1200_min": 500},
    10: {"min_duration": 1200, "gain_600_to_1200_min": 7000, "deaths_max": 2},
    11: {"lead_at_600_min": 1500, "tower_damage_min": 1500, "tower_share_min": 0.30},
    13: {"involvement_min": 0.60, "deaths_max": 1, "team_kills_min": 10},
    14: {"assists_min": 10, "deaths_max": 0},
    15: {"kills_min": 10, "deaths_max": 0},
    17: {"kills": 5, "window_seconds": 90},
    18: {"kills_min": 2, "before_seconds": 600, "deaths_max": 0},
    20: {"player_kills_min": 3, "player_deaths_max": 0},
    22: {"player_damage_min": 2000, "damage_share_min": 0.5, "separate_fights": 2},
    23: {"enemy_deaths_min": 5, "allied_deaths_max": 0, "player_damage_min": 1500},
    25: {"team_gold_gap_max": -5000, "player_damage_min": 2000, "damage_share_min": 0.5},
    30: {"distinct_matches": 3},
    37: {"observers_placed_min": 5, "observer_kills_min": 5},
    41: {"stacks_at_1200_min": 5, "involvement_min": 0.5},
    42: {"involvement_min": 0.5, "observer_kills_min": 3},
    44: {"tower_damage_min": 2500, "tower_share_min": 0.3},
    45: {"tower_share_min": 0.5, "deaths_max": 0},
    49: {"hero_healing_min": 8000, "assists_min": 10},
    50: {"disable_seconds_min": 120, "assists_min": 10},
}

# #30 may repeat only a non-Common single-match feat with a measured incidence.
# History feats (#1, #2, #4) and the one Common badge (#42) are never a repeat base.
REPEATABLE_FEATS = frozenset({6, 8, 10, 11, 13, 14, 15, 17, 18, 20, 22, 23, 25,
                              37, 41, 44, 45, 49, 50})


# Frozen tiers (owner decision 2026-09-29): never re-derived from live data, so a badge's
# tier cannot move once real users have earned it. Single-match tiers come from corpus
# rates, #1/#2/#4/#30 from history simulation; see
# evidence/achievement-threshold-review-2026-09-29.md. Bands: Common >=20%, Rare 5%-<20%,
# Epic 1%-<5%, Legendary <1% of eligible Standard player-matches.
TIER_VERSION = "badge-tiers-v1"
BADGE_TIERS: dict[int, str] = {
    1: "EPIC", 2: "LEGENDARY", 4: "EPIC", 6: "EPIC", 8: "EPIC", 10: "EPIC", 11: "EPIC",
    13: "EPIC", 14: "LEGENDARY", 15: "LEGENDARY", 17: "EPIC", 18: "RARE", 20: "RARE",
    22: "RARE", 23: "RARE", 25: "EPIC", 30: "RARE", 37: "RARE", 41: "EPIC", 42: "COMMON",
    44: "RARE", 45: "LEGENDARY", 49: "RARE", 50: "RARE",
}


def rules_digest() -> str:
    body = {"version": RULE_VERSION, "thresholds": {str(k): v for k, v in sorted(THRESHOLDS.items())},
            "repeatable": sorted(REPEATABLE_FEATS), "tier_version": TIER_VERSION,
            "tiers": {str(k): v for k, v in sorted(BADGE_TIERS.items())}}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
