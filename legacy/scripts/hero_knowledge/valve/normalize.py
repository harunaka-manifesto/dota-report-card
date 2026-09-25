"""Normalize Valve datafeed payloads into source-specific facts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import SCHEMA_VERSION
from ..config import isoformat
from ..errors import SourceSchemaError
from ..schemas import HeroIdentity, canonical_key

PRIMARY_ATTRIBUTES = {
    0: "strength",
    1: "agility",
    2: "intelligence",
    3: "universal",
}

ROLE_LEVEL_NAMES = (
    "carry",
    "support",
    "nuker",
    "disabler",
    "jungler",
    "durable",
    "escape",
    "pusher",
    "initiator",
)


def _as_optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _hero_key(internal_name: str) -> str:
    return internal_name.removeprefix("npc_dota_hero_")


def _aliases(internal_name: str, display_name: str, key: str) -> tuple[str, ...]:
    values = {internal_name, display_name, key}
    if key == "zuus":
        values.add("zeus")
    if key == "nevermore":
        values.add("shadow fiend")
    if key == "skeleton king":
        values.add("wraith king")
    return tuple(sorted(values, key=lambda value: (canonical_key(value), value)))


def normalize_hero_list(payload: dict[str, Any]) -> list[HeroIdentity]:
    try:
        rows = payload["result"]["data"]["heroes"]
    except (KeyError, TypeError) as exc:
        raise SourceSchemaError("Valve hero list is missing result.data.heroes") from exc
    if not isinstance(rows, list) or not rows:
        raise SourceSchemaError("Valve hero list is empty")
    identities: list[HeroIdentity] = []
    seen_ids: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise SourceSchemaError("Valve hero list contains a non-object row")
        try:
            hero_id = int(row["id"])
            internal_name = str(row["name"])
            display_name = str(row.get("name_english_loc") or row.get("name_loc") or internal_name)
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceSchemaError("Valve hero list contains an incomplete hero row") from exc
        if hero_id in seen_ids:
            raise SourceSchemaError(f"Valve hero list contains duplicate hero id {hero_id}")
        seen_ids.add(hero_id)
        key = _hero_key(internal_name)
        try:
            primary_attribute = PRIMARY_ATTRIBUTES.get(int(row.get("primary_attr", -1)), "unknown")
        except (TypeError, ValueError):
            primary_attribute = "unknown"
        identities.append(
            HeroIdentity(
                hero_id=hero_id,
                key=key,
                internal_name=internal_name,
                display_name=display_name,
                primary_attribute=primary_attribute,
                complexity=_as_optional_int(row.get("complexity")),
                portrait_ref=(
                    f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{key}.png"
                ),
                available=True,
                aliases=_aliases(internal_name, display_name, key),
            )
        )
    return sorted(identities, key=lambda item: item.hero_id)


def _role_levels(raw: Any) -> dict[str, int | None]:
    if not isinstance(raw, list):
        return {name: None for name in ROLE_LEVEL_NAMES}
    return {
        name: _as_optional_int(raw[index]) if index < len(raw) else None
        for index, name in enumerate(ROLE_LEVEL_NAMES)
    }


def _normalize_special_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceSchemaError("Valve special_values contains a non-object entry")
    return {
        "name": value.get("name"),
        "values": value.get("values_float", []),
        "is_percentage": value.get("is_percentage"),
        "heading": value.get("heading_loc"),
        "bonuses": value.get("bonuses", []),
        "values_shard": value.get("values_shard", []),
        "values_scepter": value.get("values_scepter", []),
        "facet_bonus": value.get("facet_bonus"),
        "required_facet": value.get("required_facet") or None,
    }


def _normalize_ability(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or "id" not in raw or "name" not in raw:
        raise SourceSchemaError("Valve hero abilities contain an incomplete ability")
    return {
        "ability_id": int(raw["id"]),
        "internal_name": str(raw["name"]),
        "display_name": raw.get("name_loc"),
        "description": raw.get("desc_loc"),
        "lore": raw.get("lore_loc"),
        "notes": raw.get("notes_loc", []),
        "behavior": raw.get("behavior"),
        "target_team": raw.get("target_team"),
        "target_type": raw.get("target_type"),
        "damage_type": raw.get("damage"),
        "immunity_interaction": raw.get("immunity"),
        "dispellability": raw.get("dispellable"),
        "max_level": raw.get("max_level"),
        "cast_ranges": raw.get("cast_ranges", []),
        "cast_points": raw.get("cast_points", []),
        "cooldowns": raw.get("cooldowns", []),
        "durations": raw.get("durations", []),
        "damages": raw.get("damages", []),
        "mana_costs": raw.get("mana_costs", []),
        "special_values": [
            _normalize_special_value(item) for item in raw.get("special_values", [])
        ],
        "is_innate": bool(raw.get("ability_is_innate", False)),
        "has_scepter": bool(raw.get("ability_has_scepter", False)),
        "has_shard": bool(raw.get("ability_has_shard", False)),
        "granted_by_scepter": bool(raw.get("ability_is_granted_by_scepter", False)),
        "granted_by_shard": bool(raw.get("ability_is_granted_by_shard", False)),
        "scepter_text": raw.get("scepter_loc") or None,
        "shard_text": raw.get("shard_loc") or None,
        "facet_text": raw.get("facets_loc", []),
    }


def _normalize_talent(raw: Any) -> dict[str, Any]:
    value = _normalize_ability(raw)
    value["level"] = raw.get("level") if isinstance(raw, dict) else None
    value["option"] = raw.get("type") if isinstance(raw, dict) else None
    return value


def _normalize_facet(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"raw": raw}
    return {
        "facet_id": raw.get("id"),
        "internal_name": raw.get("name"),
        "display_name": raw.get("name_loc"),
        "description": raw.get("desc_loc"),
        "ability_modifications": raw.get("ability_modifications", raw.get("abilities", [])),
        "required_facets": raw.get("required_facets", []),
    }


def normalize_hero_detail(
    payload: dict[str, Any],
    identity: HeroIdentity,
    *,
    source_url: str | None = None,
    fetched_at: str | None = None,
    raw_sha256: str | None = None,
    patch: str | None = None,
) -> dict[str, Any]:
    try:
        raw = payload["result"]["data"]["heroes"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise SourceSchemaError(
            f"Valve hero detail is missing hero data for {identity.hero_id}"
        ) from exc
    try:
        returned_id = int(raw.get("id", -1)) if isinstance(raw, dict) else -1
    except (TypeError, ValueError):
        returned_id = -1
    if not isinstance(raw, dict) or returned_id != identity.hero_id:
        raise SourceSchemaError(f"Valve hero detail does not match hero {identity.hero_id}")
    abilities = [_normalize_ability(item) for item in raw.get("abilities", [])]
    talents = [_normalize_talent(item) for item in raw.get("talents", [])]
    ability_ids = [item["ability_id"] for item in abilities]
    if len(ability_ids) != len(set(ability_ids)):
        raise SourceSchemaError(f"Valve hero {identity.hero_id} contains duplicate ability ids")
    base_stats = {
        "str_base": raw.get("str_base"),
        "str_gain": raw.get("str_gain"),
        "agi_base": raw.get("agi_base"),
        "agi_gain": raw.get("agi_gain"),
        "int_base": raw.get("int_base"),
        "int_gain": raw.get("int_gain"),
        "attack_type": raw.get("attack_capability"),
        "damage_min": raw.get("damage_min"),
        "damage_max": raw.get("damage_max"),
        "attack_rate": raw.get("attack_rate"),
        "attack_range": raw.get("attack_range"),
        "projectile_speed": raw.get("projectile_speed"),
        "armor": raw.get("armor"),
        "magic_resistance": raw.get("magic_resistance"),
        "movement_speed": raw.get("movement_speed"),
        "turn_rate": raw.get("turn_rate"),
        "sight_range_day": raw.get("sight_range_day"),
        "sight_range_night": raw.get("sight_range_night"),
        "max_health": raw.get("max_health"),
        "health_regen": raw.get("health_regen"),
        "max_mana": raw.get("max_mana"),
        "mana_regen": raw.get("mana_regen"),
        "role_levels": _role_levels(raw.get("role_levels")),
    }
    return {
        "hero_id": identity.hero_id,
        "identity": identity.as_dict(),
        "bio": raw.get("bio_loc"),
        "hype": raw.get("hype_loc"),
        "new_player_description": raw.get("npe_desc_loc"),
        "patch": patch,
        "base_stats": base_stats,
        "abilities": abilities,
        "facets": [_normalize_facet(item) for item in raw.get("facets", [])],
        "talents": talents,
        "facet_abilities": [_normalize_ability(item) for item in raw.get("facet_abilities", [])],
        "provenance": {
            "source": "Valve Dota 2 public datafeed",
            "source_url": source_url,
            "fetched_at": fetched_at or isoformat(),
            "raw_sha256": raw_sha256,
            "field_sources": {
                "identity": "herolist/herodata",
                "base_stats": "herodata",
                "abilities": "herodata.abilities",
                "facets": "herodata.facets",
                "talents": "herodata.talents",
            },
        },
    }


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SourceSchemaError(f"Expected JSON object: {path}")
    return value


def _latest_patch(payload: dict[str, Any]) -> str | None:
    patches = payload.get("patches", [])
    if not isinstance(patches, list):
        return None
    values = [
        item.get("patch_number")
        for item in patches
        if isinstance(item, dict) and item.get("patch_number")
    ]
    return str(values[-1]) if values else None


def normalize_valve_snapshot(
    snapshot_dir: str | Path, *, output_path: str | Path | None = None
) -> dict[str, Any]:
    root = Path(snapshot_dir)
    metadata = _read_json(root / "metadata.json")
    hero_list_path = root / "herolist.json"
    identities = normalize_hero_list(_read_json(hero_list_path))
    by_id = {identity.hero_id: identity for identity in identities}
    patch = metadata.get("patch")
    patch_path = root / "patchnoteslist.json"
    if patch is None and patch_path.exists():
        patch = _latest_patch(_read_json(patch_path))
    selected_ids = metadata.get("hero_ids")
    if isinstance(selected_ids, list) and selected_ids:
        detail_ids = sorted(int(hero_id) for hero_id in selected_ids)
    else:
        detail_ids = [identity.hero_id for identity in identities]
    heroes: list[dict[str, Any]] = []
    for hero_id in detail_ids:
        identity = by_id.get(hero_id)
        if identity is None:
            raise SourceSchemaError(f"Valve snapshot metadata references unknown hero {hero_id}")
        path = root / "heroes" / f"{identity.hero_id}.json"
        if not path.exists():
            raise SourceSchemaError(f"Valve snapshot is incomplete; missing {path.name}")
        payload = _read_json(path)
        heroes.append(
            normalize_hero_detail(
                payload,
                by_id[identity.hero_id],
                source_url=(
                    f"https://www.dota2.com/datafeed/herodata?hero_id={identity.hero_id}&language=english"
                ),
                fetched_at=str(metadata.get("fetched_at", isoformat())),
                raw_sha256=str(metadata.get("hero_hashes", {}).get(str(identity.hero_id), ""))
                or None,
                patch=str(patch) if patch is not None else None,
            )
        )
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "source": "valve",
        "snapshot_id": metadata.get("snapshot_id", root.name),
        "patch": patch,
        "generated_at": isoformat(),
        "roster": [identity.as_dict() for identity in identities],
        "heroes": heroes,
        "provenance": {
            "source": "Valve Dota 2 public datafeed",
            "source_urls": metadata.get("source_urls", {}),
            "raw_snapshot": str(root),
            "fetched_at": metadata.get("fetched_at"),
            "hero_count": len(heroes),
        },
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(normalized, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return normalized
