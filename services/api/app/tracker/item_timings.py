"""Frozen key-item timelines and the item insight cards for Match Detail.

Population references are keyed by hero, core role, mode and item. The purchase
order is reported as a fact but never selects a baseline.
"""

from __future__ import annotations

import statistics
from typing import Any

from . import item_references

CONTRACT_VERSION = "item-timings-v1"
CORE_ROLES = frozenset({"CARRY", "MID", "OFFLANE"})
COMPARABLE_MODES = frozenset({"STANDARD", "TURBO"})
# Boots upgrades and bare components stay in the timeline but never become a
# card: the 50-card relevance review judged their early timings not noteworthy.
CARD_EXCLUDED_ITEMS = frozenset({
    "item_power_treads", "item_phase_boots", "item_arcane_boots", "item_tranquil_boots",
    "item_travel_boots", "item_travel_boots_2", "item_guardian_greaves", "item_boots_of_bearing",
    "item_sange", "item_yasha", "item_kaya", "item_lesser_crit",
})


def _clock(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def _margin(mode: str, baseline: int, *, proportional: bool = True) -> int:
    floor = 60 if mode == "STANDARD" else 30
    return max(round(baseline * 0.10), floor) if proportional else floor


def _history_window(
    history: dict[str, Any] | None,
    *,
    mode: str,
    role: str,
    hero: int,
    patch: str,
    item: str,
) -> list[int]:
    rows = (history or {}).get("observations")
    if not isinstance(rows, list):
        return []
    values = [
        row["value"]
        for row in rows
        if isinstance(row, dict)
        and row.get("metric") == "FIRST_KEY_ITEM_PURCHASE"
        and row.get("bucket") == mode
        and row.get("role") == role
        and row.get("hero") == hero
        and row.get("patch") == patch
        and row.get("item") == item
        and type(row.get("value")) is int
    ]
    return values[-50:]


def _population(subpatch: str | None, mode: str, hero: int, role: str, item: str) -> dict[str, Any] | None:
    """Return a usable population reference, or None when the cell has no claim."""
    reference = item_references.reference(subpatch, mode, hero, role, item)
    if reference is None:
        return None
    fields = ("p10", "p25", "median", "purchase_count")
    if not all(type(reference.get(field)) is int for field in fields):
        return None
    return reference


def _comparison(
    *,
    mode: str,
    role: str,
    hero: int,
    major_patch: str | None,
    subpatch: str | None,
    item: dict[str, Any],
    history: dict[str, Any] | None,
) -> dict[str, Any] | None:
    second = item["purchase_time_seconds"]
    key = item["item_key"]
    population = _population(subpatch, mode, hero, role, key)
    # References pool earlier lettered updates, so the claim names the major patch.
    cohort_patch = item_references.artifact()[0].get("major_patch")
    if population is not None and isinstance(cohort_patch, str):
        baseline = population["median"]
        if second <= population["p25"] and baseline - second >= _margin(mode, baseline):
            return {
                "kind": "POPULATION_USUAL",
                "baseline_seconds": baseline,
                "delta_seconds": baseline - second,
                "sample_size": population["purchase_count"],
                "cohort_patch": cohort_patch,
            }
    if not isinstance(major_patch, str):
        return None
    window = _history_window(
        history, mode=mode, role=role, hero=hero, patch=major_patch, item=key,
    )
    if len(window) >= 20:
        previous = min(window)
        if previous - second >= _margin(mode, previous, proportional=False):
            return {
                "kind": "PERSONAL_PREVIOUS_BEST",
                "baseline_seconds": previous,
                "delta_seconds": previous - second,
                "sample_size": len(window),
                "cohort_patch": major_patch,
            }
    if len(window) >= 10:
        usual = round(statistics.median(window))
        if usual - second >= _margin(mode, usual):
            return {
                "kind": "PERSONAL_USUAL",
                "baseline_seconds": usual,
                "delta_seconds": usual - second,
                "sample_size": len(window),
                "cohort_patch": major_patch,
            }
    return None


def evaluate(
    match: dict[str, Any],
    viewer: dict[str, Any],
    history: dict[str, Any] | None,
    *,
    comparisons_allowed: bool,
) -> dict[str, Any]:
    mode = match.get("bucket")
    if mode not in COMPARABLE_MODES:
        return {
            "state": "UNAVAILABLE",
            "contract_version": CONTRACT_VERSION,
            "reason": "MODE",
            "reference_digest": None,
            "major_patch": match.get("major_patch"),
            "hero_id": None,
            "items": [],
        }
    players = match.get("players")
    slot = viewer.get("player_slot")
    player = next(
        (row for row in players or [] if isinstance(row, dict) and row.get("player_slot") == slot),
        None,
    )
    purchases = player.get("keyItemPurchases") if isinstance(player, dict) else None
    if not isinstance(purchases, list):
        return {
            "state": "UNAVAILABLE",
            "contract_version": CONTRACT_VERSION,
            "reason": "SOURCE_EVIDENCE",
            "reference_digest": None,
            "major_patch": match.get("major_patch"),
            "hero_id": player.get("heroId") if isinstance(player, dict) else None,
            "items": [],
        }
    assert isinstance(player, dict)
    role = viewer.get("effective_role")
    hero = player.get("heroId")
    comparable = comparisons_allowed and role in CORE_ROLES and type(hero) is int
    items = []
    for purchase in purchases:
        row = dict(purchase)
        row["comparison"] = None
        if comparable:
            assert isinstance(role, str) and type(hero) is int
            row["comparison"] = _comparison(
                mode=mode,
                role=role,
                hero=hero,
                major_patch=match.get("major_patch"),
                subpatch=match.get("subpatch"),
                item=row,
                history=history,
            )
        items.append(row)
    return {
        "state": "AVAILABLE",
        "contract_version": CONTRACT_VERSION,
        "reason": None,
        "reference_digest": item_references.artifact()[1],
        "major_patch": match.get("major_patch"),
        "hero_id": hero,
        "items": items,
    }


def _band(ratio: float) -> int:
    return 3 if ratio >= 0.25 else 2 if ratio >= 0.15 else 1


def _card_worthy(
    item: dict[str, Any], comparison: dict[str, Any], *, subpatch: str | None, mode: str, hero: int, role: str,
) -> bool:
    """Cards need a population reference and a stricter margin than the inline row.

    A population card must beat the reference's p10 by max(10%, 60s Standard /
    30s Turbo), not just its p25.
    """
    if item["item_key"] in CARD_EXCLUDED_ITEMS:
        return False
    population = _population(subpatch, mode, hero, role, item["item_key"])
    if population is None:
        return False
    if comparison["kind"] == "POPULATION_USUAL":
        p10 = population["p10"]
        return p10 - item["purchase_time_seconds"] >= _margin(mode, p10)
    return comparison["kind"] == "PERSONAL_PREVIOUS_BEST"


def insight_cards(
    snapshot: dict[str, Any], *, hero: int, role: str, mode: str, subpatch: str | None,
) -> list[dict[str, Any]]:
    """Return at most one OWN_HERO_ITEM card.

    Only items with a population reference for this hero, role and mode qualify
    (see _card_worthy), and only population or previous-best comparisons;
    personal medians stay inline.
    """
    best: tuple[int, dict[str, Any], dict[str, Any]] | None = None
    for item in snapshot.get("items", []):
        comparison = item.get("comparison") if isinstance(item, dict) else None
        if not isinstance(comparison, dict) or not _card_worthy(
            item, comparison, subpatch=subpatch, mode=mode, hero=hero, role=role,
        ):
            continue
        if best is None or comparison["delta_seconds"] > best[0]:
            best = (comparison["delta_seconds"], item, comparison)
    if best is None:
        return []
    delta, item, comparison = best
    baseline = comparison["baseline_seconds"]
    ratio = delta / baseline if baseline else 0.0
    kind = comparison["kind"]
    name, time, count = item["item_name"], _clock(item["purchase_time_seconds"]), comparison["sample_size"]
    if kind == "POPULATION_USUAL":
        copy = (
            f"You bought {name} at {time}, {_clock(delta)} earlier than players usually buy it "
            f"on this hero as {role.title()}, across {count} {mode.title()} purchases."
        )
        history_line = f"{name} at {time} was {_clock(delta)} earlier than usual across {count} purchases."
    else:
        copy = (
            f"You bought {name} at {time}, {_clock(delta)} earlier than your previous best "
            f"across {count} earlier {mode.title()} {role.title()} matches on this hero."
        )
        history_line = (
            f"{name} at {time} was {_clock(delta)} earlier than your previous best "
            f"across {count} earlier matches."
        )
    return [{
        "candidate_id": "OWN_HERO_ITEM",
        "tier": "A",
        "family": "Power Spikes & Item Timings",
        "band": _band(ratio),
        "level": round(ratio, 3),
        "slots": {
            "hero": hero,
            "role": role,
            "mode": mode,
            "item": item["item_key"],
            "item_name": name,
            "time": item["purchase_time_seconds"],
            "key_item_order": item["key_item_order"],
            "comparison_kind": kind,
            "reference_time": baseline,
            "delta": delta,
            "N": count,
            "patch": comparison["cohort_patch"],
            "reference_digest": snapshot.get("reference_digest"),
        },
        "enrichments": [],
        "copy": copy,
        "history_line": history_line,
    }]


def enemy_insight_cards(match: dict[str, Any], viewer: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the enemy core purchase that most beats its population median, if any."""
    mode = match.get("bucket")
    team = viewer.get("team")
    if mode not in COMPARABLE_MODES or team not in {"RADIANT", "DIRE"}:
        return []
    enemy = "DIRE" if team == "RADIANT" else "RADIANT"
    best: tuple[float, dict[str, Any], dict[str, Any], str, int, int] | None = None
    for player in match.get("players", []):
        if not isinstance(player, dict) or player.get("team") != enemy:
            continue
        position = player.get("position")
        position = int(position[-1]) if isinstance(position, str) and position[-1:].isdigit() else position
        if type(position) is not int:
            continue
        role = {1: "CARRY", 2: "MID", 3: "OFFLANE"}.get(position)
        hero = player.get("heroId")
        purchases = player.get("keyItemPurchases")
        if role is None or type(hero) is not int or not isinstance(purchases, list):
            continue
        for item in purchases:
            if not isinstance(item, dict):
                continue
            comparison = _comparison(
                mode=mode,
                role=role,
                hero=hero,
                major_patch=None,
                subpatch=match.get("subpatch"),
                item=item,
                history=None,
            )
            if comparison is None or comparison["kind"] != "POPULATION_USUAL" or not _card_worthy(
                item, comparison, subpatch=match.get("subpatch"), mode=mode, hero=hero, role=role,
            ):
                continue
            score = comparison["delta_seconds"] / comparison["baseline_seconds"]
            if best is None or score > best[0]:
                best = (score, item, comparison, role, position, hero)
    if best is None:
        return []
    score, item, comparison, role, position, hero = best
    name, time = item["item_name"], _clock(item["purchase_time_seconds"])
    delta, count = _clock(comparison["delta_seconds"]), comparison["sample_size"]
    return [{
        "candidate_id": "ENEMY_HERO_ITEM",
        "tier": "A",
        "family": "Power Spikes & Item Timings",
        "band": _band(score),
        "level": round(score, 3),
        "slots": {
            "hero": hero,
            "role": role,
            "position": position,
            "mode": mode,
            "item": item["item_key"],
            "item_name": name,
            "time": item["purchase_time_seconds"],
            "key_item_order": item["key_item_order"],
            "comparison_kind": "POPULATION_USUAL",
            "reference_time": comparison["baseline_seconds"],
            "delta": comparison["delta_seconds"],
            "N": count,
            "patch": comparison["cohort_patch"],
            "reference_digest": item_references.artifact()[1],
        },
        "enrichments": [],
        "copy": (
            f"Their {name} at {time} was {delta} earlier than players usually buy it on that hero "
            f"as {role.title()}, across {count} {mode.title()} purchases."
        ),
        "history_line": f"Their {name} at {time} was {delta} earlier than usual across {count} purchases.",
    }]
