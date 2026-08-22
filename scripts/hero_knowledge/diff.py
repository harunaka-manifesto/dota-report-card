"""Diff versioned knowledge snapshots without rewriting editorial content."""

from __future__ import annotations

from typing import Any


def _map(items: Any, key: str) -> dict[Any, dict[str, Any]]:
    if not isinstance(items, list):
        return {}
    return {
        item.get(key): item
        for item in items
        if isinstance(item, dict) and item.get(key) is not None
    }


def _changed(old: Any, new: Any) -> bool:
    return old != new


def diff_knowledge_snapshots(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    # Hero identity is nested in the product record, so use a stable ID map.
    old_heroes = {
        row.get("identity", {}).get("hero_id"): row
        for row in old.get("heroes", [])
        if isinstance(row, dict) and isinstance(row.get("identity"), dict)
    }
    new_heroes = {
        row.get("identity", {}).get("hero_id"): row
        for row in new.get("heroes", [])
        if isinstance(row, dict) and isinstance(row.get("identity"), dict)
    }
    changes: list[dict[str, Any]] = []
    for hero_id in sorted(
        set(old_heroes) | set(new_heroes), key=lambda value: (value is None, value)
    ):
        before = old_heroes.get(hero_id)
        after = new_heroes.get(hero_id)
        if before is None:
            changes.append({"hero_id": hero_id, "change": "hero_added"})
            continue
        if after is None:
            changes.append({"hero_id": hero_id, "change": "hero_removed"})
            continue
        before_abilities = _map(before.get("mechanics", {}).get("abilities"), "internal_name")
        after_abilities = _map(after.get("mechanics", {}).get("abilities"), "internal_name")
        added_abilities = sorted(set(after_abilities) - set(before_abilities))
        removed_abilities = sorted(set(before_abilities) - set(after_abilities))
        before_talents = _map(before.get("mechanics", {}).get("talents"), "internal_name")
        after_talents = _map(after.get("mechanics", {}).get("talents"), "internal_name")
        added_talents = sorted(set(after_talents) - set(before_talents))
        removed_talents = sorted(set(before_talents) - set(after_talents))
        hero_changes: list[dict[str, Any]] = []
        before_identity = before.get("identity", {})
        after_identity = after.get("identity", {})
        identity_changes = [
            field
            for field in ("key", "internal_name", "display_name", "primary_attribute", "complexity")
            if before_identity.get(field) != after_identity.get(field)
        ]
        if identity_changes:
            hero_changes.append({"change": "identity_changed", "fields": identity_changes})
        if added_abilities or removed_abilities:
            hero_changes.append(
                {
                    "change": "ability_added_removed",
                    "added": added_abilities,
                    "removed": removed_abilities,
                }
            )
        if any(
            _changed(before_abilities[name], after_abilities[name])
            for name in set(before_abilities) & set(after_abilities)
        ):
            hero_changes.append({"change": "mechanics_changed"})
        if _changed(
            before.get("mechanics", {}).get("facets"), after.get("mechanics", {}).get("facets")
        ):
            hero_changes.append({"change": "facet_changed"})
        if (
            added_talents
            or removed_talents
            or _changed(
                before.get("mechanics", {}).get("talents"),
                after.get("mechanics", {}).get("talents"),
            )
        ):
            hero_changes.append(
                {"change": "talent_changed", "added": added_talents, "removed": removed_talents}
            )
        if _changed(
            before.get("mechanics", {}).get("base_stats"),
            after.get("mechanics", {}).get("base_stats"),
        ):
            hero_changes.append({"change": "base_stats_changed"})
        if _changed(before.get("empirical"), after.get("empirical")):
            hero_changes.append({"change": "empirical_changed"})
        if hero_changes:
            approved = (
                before.get("editorial", {}).get("review_status") == "approved"
                or after.get("editorial", {}).get("review_status") == "approved"
            )
            changes.append(
                {
                    "hero_id": hero_id,
                    "name": after.get("identity", {}).get("display_name"),
                    "changes": hero_changes,
                    "editorial_review_required": approved
                    and any(item["change"] != "empirical_changed" for item in hero_changes),
                }
            )
    return {
        "old_version": old.get("knowledge_version"),
        "new_version": new.get("knowledge_version"),
        "hero_changes": changes,
        "changed_hero_count": len(changes),
    }
