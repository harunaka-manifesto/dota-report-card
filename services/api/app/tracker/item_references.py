"""Patch-scoped, de-identified hero × role × mode × item timing references."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

# Core strategic items; KEY_ITEMS below extends them with the rest of the catalog.
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
# Key-item catalog, reviewed from the public dotaconstants item graph.
# It contains strategic recipe-built items and every upgraded boot, plus Blink
# Dagger. Consumables, neutral items, recipes, basic components, Boots of Speed,
# Magic Stick and Magic Wand are deliberately absent.
KEY_ITEMS = {
    **ITEMS,
    48: ("item_travel_boots", "Boots of Travel"),
    50: ("item_phase_boots", "Phase Boots"),
    63: ("item_power_treads", "Power Treads"),
    79: ("item_mekansm", "Mekansm"),
    81: ("item_vladmir", "Vladmir's Offering"),
    96: ("item_sheepstick", "Scythe of Vyse"),
    100: ("item_cyclone", "Eul's Scepter of Divinity"),
    102: ("item_force_staff", "Force Staff"),
    104: ("item_dagon", "Dagon"),
    106: ("item_necronomicon", "Necronomicon"),
    133: ("item_rapier", "Divine Rapier"),
    135: ("item_monkey_king_bar", "Monkey King Bar"),
    149: ("item_lesser_crit", "Crystalys"),
    152: ("item_invis_sword", "Shadow Blade"),
    162: ("item_sange", "Sange"),
    164: ("item_helm_of_the_dominator", "Helm of the Dominator"),
    170: ("item_yasha", "Yasha"),
    180: ("item_arcane_boots", "Arcane Boots"),
    185: ("item_ancient_janggo", "Drum of Endurance"),
    190: ("item_veil_of_discord", "Veil of Discord"),
    193: ("item_necronomicon_2", "Necronomicon 2"),
    194: ("item_necronomicon_3", "Necronomicon 3"),
    201: ("item_dagon_2", "Dagon 2"),
    202: ("item_dagon_3", "Dagon 3"),
    203: ("item_dagon_4", "Dagon 4"),
    204: ("item_dagon_5", "Dagon 5"),
    206: ("item_rod_of_atos", "Rod of Atos"),
    208: ("item_abyssal_blade", "Abyssal Blade"),
    210: ("item_heavens_halberd", "Heaven's Halberd"),
    214: ("item_tranquil_boots", "Tranquil Boots"),
    220: ("item_travel_boots_2", "Boots of Travel 2"),
    223: ("item_meteor_hammer", "Meteor Hammer"),
    229: ("item_solar_crest", "Solar Crest"),
    231: ("item_guardian_greaves", "Guardian Greaves"),
    232: ("item_aether_lens", "Aether Lens"),
    254: ("item_glimmer_cape", "Glimmer Cape"),
    256: ("item_aeon_disk", "Aeon Disk"),
    259: ("item_kaya", "Kaya"),
    267: ("item_spirit_vessel", "Spirit Vessel"),
    269: ("item_holy_locket", "Holy Locket"),
    273: ("item_kaya_and_sange", "Kaya and Sange"),
    277: ("item_yasha_and_kaya", "Yasha and Kaya"),
    534: ("item_witch_blade", "Witch Blade"),
    598: ("item_mage_slayer", "Mage Slayer"),
    600: ("item_overwhelming_blink", "Overwhelming Blink"),
    603: ("item_swift_blink", "Swift Blink"),
    604: ("item_arcane_blink", "Arcane Blink"),
    610: ("item_wind_waker", "Wind Waker"),
    635: ("item_helm_of_the_overlord", "Helm of the Overlord"),
    692: ("item_eternal_shroud", "Eternal Shroud"),
    908: ("item_wraith_pact", "Wraith Pact"),
    911: ("item_revenants_brooch", "Revenant's Brooch"),
    931: ("item_boots_of_bearing", "Boots of Bearing"),
    939: ("item_harpoon", "Harpoon"),
    1076: ("item_specialists_array", "Specialist's Array"),
    1097: ("item_disperser", "Disperser"),
    1107: ("item_phylactery", "Phylactery"),
    1466: ("item_gungir", "Gleipnir"),
    1806: ("item_devastator", "Parasma"),
    1808: ("item_angels_demise", "Khanda"),
    1852: ("item_essence_distiller", "Essence Distiller"),
    1854: ("item_consecrated_wraps", "Consecrated Wraps"),
    1856: ("item_crellas_crozier", "Crella's Crozier"),
    1858: ("item_hydras_breath", "Hydra's Breath"),
}
KEY_ITEM_BY_KEY = {key: (item_id, label) for item_id, (key, label) in KEY_ITEMS.items()}

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


def normalize_key_item_purchases(
    rows: Any, provider: str, duration_seconds: int,
) -> list[dict[str, int | str]] | None:
    """Return the first valid purchase of each key item in deterministic order."""
    if not isinstance(rows, list) or type(duration_seconds) is not int or duration_seconds < 0:
        return None
    first: dict[int, int] = {}
    for row in rows:
        if not isinstance(row, dict) or type(row.get("time")) is not int:
            continue
        second = row["time"]
        if not 0 <= second <= duration_seconds:
            continue
        if provider == "stratz":
            item_id = row.get("itemId")
            item_id = item_id if type(item_id) is int and item_id in KEY_ITEMS else None
        elif provider == "opendota":
            raw_key = row.get("key")
            key = (
                raw_key if raw_key.startswith("item_") else f"item_{raw_key}"
            ) if isinstance(raw_key, str) else None
            found = KEY_ITEM_BY_KEY.get(key) if key else None
            item_id = found[0] if found else None
        else:
            raise ValueError("Unsupported provider")
        if item_id is not None:
            first[item_id] = min(first.get(item_id, second), second)
    ordered = sorted(first.items(), key=lambda row: (row[1], row[0]))
    return [
        {
            "item_id": item_id,
            "item_key": KEY_ITEMS[item_id][0],
            "item_name": KEY_ITEMS[item_id][1],
            "purchase_time_seconds": second,
            "key_item_order": index,
        }
        for index, (item_id, second) in enumerate(ordered, 1)
    ]


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

