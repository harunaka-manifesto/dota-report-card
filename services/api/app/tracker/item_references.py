"""Patch-scoped, de-identified hero item timing references for insight V2."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

# Store only strategic completed items. IDs follow the public Dota item catalog.
ITEMS = {
    1: ("item_blink", "Blink Dagger"),
    65: ("item_hand_of_midas", "Hand of Midas"),
    90: ("item_pipe", "Pipe of Insight"),
    98: ("item_orchid", "Orchid Malevolence"),
    108: ("item_ultimate_scepter", "Aghanim's Scepter"),
    110: ("item_refresher", "Refresher Orb"),
    112: ("item_assault", "Assault Cuirass"),
    114: ("item_heart", "Heart of Tarrasque"),
    116: ("item_black_king_bar", "Black King Bar"),
    119: ("item_shivas_guard", "Shiva's Guard"),
    121: ("item_bloodstone", "Bloodstone"),
    123: ("item_sphere", "Linken's Sphere"),
    125: ("item_vanguard", "Vanguard"),
    127: ("item_blade_mail", "Blade Mail"),
    137: ("item_radiance", "Radiance"),
    139: ("item_butterfly", "Butterfly"),
    141: ("item_greater_crit", "Daedalus"),
    143: ("item_basher", "Skull Basher"),
    145: ("item_bfury", "Battle Fury"),
    147: ("item_manta", "Manta Style"),
    151: ("item_armlet", "Armlet"),
    154: ("item_sange_and_yasha", "Sange and Yasha"),
    156: ("item_satanic", "Satanic"),
    158: ("item_mjollnir", "Mjollnir"),
    160: ("item_skadi", "Eye of Skadi"),
    166: ("item_maelstrom", "Maelstrom"),
    168: ("item_desolator", "Desolator"),
    172: ("item_mask_of_madness", "Mask of Madness"),
    174: ("item_diffusal_blade", "Diffusal Blade"),
    176: ("item_ethereal_blade", "Ethereal Blade"),
    225: ("item_nullifier", "Nullifier"),
    226: ("item_lotus_orb", "Lotus Orb"),
    235: ("item_octarine_core", "Octarine Core"),
    236: ("item_dragon_lance", "Dragon Lance"),
    242: ("item_crimson_guard", "Crimson Guard"),
    249: ("item_silver_edge", "Silver Edge"),
    250: ("item_bloodthorn", "Bloodthorn"),
    252: ("item_echo_sabre", "Echo Sabre"),
    263: ("item_hurricane_pike", "Hurricane Pike"),
}
ITEM_BY_KEY = {key: label for key, label in ITEMS.values()}

# Release-day records are excluded because the public announcement's date is
# insufficient to disambiguate games played before and after deployment.
PATCH_START = {
    "7.41b": "2026-04-08",
    "7.41c": "2026-05-07",
    "7.41d": "2026-06-06",
    "7.41e": "2026-07-31",
    "7.41f": "2026-09-16",
}
PATCH_RELEASE = {
    "7.41b": "2026-04-07",
    "7.41c": "2026-05-06",
    "7.41d": "2026-06-05",
    "7.41e": "2026-07-30",
    "7.41f": "2026-09-15",
}
CURRENT_PATCH = "7.41f"
STRATZ_VERSION_IDS = frozenset({182})

# 7.41f changed these heroes and item mechanics/costs. Hold their old timing
# baselines until an f shard or a direct build review clears each pair.
SUSPENDED_HEROES = frozenset({
    70, 61, 1, 80, 87, 129, 107, 37, 28, 91, 36, 106, 51, 67, 65,
    74, 112, 123, 145, 33, 62, 85, 90, 96, 9, 155, 3, 59, 54,
    66, 108, 136, 25, 83, 11,
})
SUSPENDED_ITEMS = frozenset({
    "item_mask_of_madness", "item_satanic", "item_silver_edge",
    "item_heart", "item_shivas_guard", "item_greater_crit", "item_manta",
    "item_mjollnir", "item_octarine_core", "item_dragon_lance",
    "item_hurricane_pike",
})


def suspended(hero: int, item: str) -> bool:
    # Battle Fury's 7.41f change only altered Chop Tree cooldown. PA's current
    # build evidence still lists it; Medusa's current builds still list Manta.
    return hero in SUSPENDED_HEROES or (
        item in SUSPENDED_ITEMS and (hero, item) != (94, "item_manta")
    )


def subpatch(started_at: int | None, *, major: str | None) -> str | None:
    if type(started_at) is not int or major != "7.41":
        return None
    day = datetime.fromtimestamp(started_at, UTC).date().isoformat()
    for name in reversed(tuple(PATCH_START)):
        if day >= PATCH_START[name]:
            return name
        if day == PATCH_RELEASE[name]:
            return None
    return None


def major_patch(raw: dict[str, Any], provider: str, started_at: int | None) -> str | None:
    if provider == "opendota":
        return "7.41" if raw.get("patch") == 60 else None
    # STRATZ 182 spans multiple gameplay updates in the retained corpus. Verify
    # the major-patch date interval as well as the provider version ID.
    if raw.get("gameVersionId") not in STRATZ_VERSION_IDS or type(started_at) is not int:
        return None
    day = datetime.fromtimestamp(started_at, UTC).date().isoformat()
    return "7.41" if day >= "2026-03-25" else None


def normalize_purchases(rows: Any, provider: str, mode: str) -> list[dict[str, int | str]] | None:
    if not isinstance(rows, list):
        return None
    purchases = []
    for row in rows:
        if not isinstance(row, dict) or type(row.get("time")) is not int:
            continue
        if provider == "stratz":
            item_id = row.get("itemId")
            item = ITEMS.get(item_id) if type(item_id) is int else None
            key = item[0] if item else None
        else:
            raw_key = row.get("key")
            key = (raw_key if raw_key.startswith("item_") else f"item_{raw_key}") if isinstance(raw_key, str) else None
        earliest = 180 if mode == "TURBO" else 300
        if key in ITEM_BY_KEY and row["time"] >= earliest:
            purchases.append({"item": key, "time": row["time"]})
    return purchases


@lru_cache(maxsize=1)
def artifact() -> tuple[dict[str, Any], str]:
    path = Path(__file__).with_name("item_references.json")
    body = path.read_bytes()
    return json.loads(body), hashlib.sha256(body).hexdigest()


def reference(patch: str | None, mode: str, hero: int, role: str, item: str) -> dict[str, Any] | None:
    if patch != CURRENT_PATCH:
        return None
    data, _ = artifact()
    return data["references"].get(f"{mode}:{hero}:{role}:{item}")
