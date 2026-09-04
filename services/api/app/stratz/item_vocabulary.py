"""Load and classify the STRATZ item vocabulary.

The item vocabulary is fetched once and committed as a static JSON file. This
module loads it at runtime and provides classifiers to distinguish consumables
from real items — a critical distinction for item-timing analysis.

A "real item" is something a player keeps in their inventory (a BKB, a Blink, etc.),
not something they use and discard (a Tango, a Clarity, etc.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ItemInfo:
    """Immutable item metadata from the STRATZ vocabulary."""

    id: int
    name: str
    short_name: str
    cost: int | None


# Consumable short_names derived from the STRATZ item vocabulary.
# These are items that are used up or disappear after a single use or cooldown.
# They do not represent a permanent slot in a player's inventory.
#
# Determined by inspecting the actual fetched vocabulary:
#  - Eating consumables: tango, tango_single, clarity, enchanted_mango, flask
#  - Single-use items: faerie_fire, greater_faerie_fire, blood_grenade
#  - Wards (zero or low cost): ward_observer, ward_sentry, ward_dispenser
#  - Utility: smoke_of_deceit, dust, tpscroll (Town Portal Scroll), bottle, tome_of_knowledge
#
_CONSUMABLE_SHORT_NAMES: frozenset[str] = frozenset(
    (
        # Eating consumables
        "tango",
        "tango_single",
        "clarity",
        "enchanted_mango",
        "flask",  # Healing Salve
        # Single-use items
        "faerie_fire",
        "greater_faerie_fire",
        "blood_grenade",
        # Wards
        "ward_observer",
        "ward_sentry",
        "ward_dispenser",
        # Utility consumables
        "smoke_of_deceit",
        "dust",  # Dust of Appearance
        "tpscroll",  # Town Portal Scroll
        "bottle",  # Can store runes, provides charges
        "tome_of_knowledge",  # Instant XP, one-time use per availability
    )
)

# Real items must have a cost >= 500 gold to be considered a true inventory item
# rather than a minor component or consumable. This threshold is chosen to
# filter out recipe components, cheap utility items, and early-game consumables.
_REAL_ITEM_MIN_COST = 500


def load_item_vocabulary(path: Path | None = None) -> dict[int, ItemInfo]:
    """Load the STRATZ item vocabulary from the committed JSON file.

    Args:
        path: Path to the vocabulary JSON file. If None, uses the default
            location relative to this module.

    Returns:
        A mapping from item id to ItemInfo.

    Raises:
        FileNotFoundError: If the vocabulary file does not exist.
        ValueError: If the file is malformed or missing required fields.
    """
    if path is None:
        path = Path(__file__).parent / "item_vocabulary.json"

    if not path.is_file():
        raise FileNotFoundError(f"item vocabulary not found at {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    items_raw = data.get("items") or []

    items: dict[int, ItemInfo] = {}
    for raw in items_raw:
        if not isinstance(raw, dict):
            continue
        try:
            item_id = raw["id"]
            name = raw["name"]
            short_name = raw["short_name"]
            cost = raw.get("cost")
            items[item_id] = ItemInfo(id=item_id, name=name, short_name=short_name, cost=cost)
        except KeyError:
            # Skip malformed entries.
            continue

    return items


def is_consumable(item: ItemInfo) -> bool:
    """Return True if the item is a consumable that disappears after use.

    Consumables are items with a single or limited use that disappear from
    the inventory after use (or have a global cooldown). They are not counted
    as permanent inventory items for timing analysis.
    """
    return item.short_name in _CONSUMABLE_SHORT_NAMES


def is_real_item(item: ItemInfo) -> bool:
    """Return True if the item is a real, permanent inventory item.

    A real item is:
    - Not a consumable.
    - Has a non-None cost.
    - Has a cost of at least {_REAL_ITEM_MIN_COST} gold.

    This filters out consumables, recipes, components, and other temporary items.
    """
    if is_consumable(item):
        return False
    if item.cost is None:
        return False
    return item.cost >= _REAL_ITEM_MIN_COST


__all__ = [
    "ItemInfo",
    "is_consumable",
    "is_real_item",
    "load_item_vocabulary",
]
