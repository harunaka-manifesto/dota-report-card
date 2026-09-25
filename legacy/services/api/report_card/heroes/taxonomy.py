"""Stable, checked-in hero taxonomy used by Free DNA.

The runtime deliberately does not infer hero identity from the research-file
order, filenames, or hero names. Factual identity comes from the frozen
OpenDota/Valve-compatible snapshot and editorial traits come from a separate
reviewed snapshot. The Markdown research corpus is build-time input only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TAXONOMY_VERSION = "hero-taxonomy-2026-08-16"
FACTUAL_VERSION = "factual-2026-08-16"
EDITORIAL_VERSION = "editorial-2026-08-16"
TRAITS = (
    "initiation", "mobility", "pickoff", "teamfight", "save", "sustain",
    "burst", "sustained_damage", "wave_clear", "push", "frontline", "scaling",
    "farm_dependency", "global_presence", "micro_intensity", "complexity", "repositioning",
)
ROLES = frozenset({"carry", "mid", "offlane", "soft_support", "hard_support", "roamer", "jungle"})
_DATA_ROOT = Path(__file__).with_name("data")
_FACTUAL_PATH = _DATA_ROOT / "factual" / "2026-08-16.json"
_EDITORIAL_PATH = _DATA_ROOT / "editorial" / "2026-08-16.json"
_MANIFEST_PATH = _DATA_ROOT / "taxonomy-manifest.json"


@dataclass(frozen=True, slots=True)
class HeroTaxonomyEntry:
    hero_id: int
    key: str
    name: str
    roles: tuple[str, ...]
    traits: dict[str, float]
    portrait_url: str
    available: bool = True
    provenance: dict[str, Any] | None = None
    portrait_asset_version: str = "hero-assets-2026-08-16"

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "key": self.key,
            "name": self.name,
            "roles": list(self.roles),
            "traits": dict(self.traits),
            "portrait_url": self.portrait_url,
            "available": self.available,
            "provenance": self.provenance or {},
            "portrait_asset_version": self.portrait_asset_version,
        }


@dataclass(frozen=True, slots=True)
class HeroTaxonomy:
    version: str
    heroes: dict[int, HeroTaxonomyEntry]
    manifest: dict[str, Any]

    def get(self, hero_id: int | None) -> HeroTaxonomyEntry | None:
        return self.heroes.get(hero_id) if hero_id is not None else None

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        manifest_status = self.manifest.get("review_status")
        if not self.manifest.get("reviewer") or manifest_status not in {"reviewed", "reviewed_snapshot"}:
            errors.append("missing_manifest_review_status")
        for checksum_key in ("factual_checksum", "editorial_checksum"):
            checksum = self.manifest.get(checksum_key)
            if not isinstance(checksum, str) or len(checksum) != 64:
                errors.append(f"invalid_manifest_checksum:{checksum_key}")
        seen_keys: set[str] = set()
        for hero_id, hero in self.heroes.items():
            if hero.hero_id != hero_id:
                errors.append(f"hero_id_mismatch:{hero_id}")
            if hero.key in seen_keys:
                errors.append(f"duplicate_key:{hero.key}")
            seen_keys.add(hero.key)
            if not hero.provenance:
                errors.append(f"missing_provenance:{hero_id}")
            elif (
                not hero.provenance.get("source")
                or not hero.provenance.get("research_file")
                or not hero.provenance.get("editorial")
                or not hero.provenance.get("review_status")
            ):
                errors.append(f"incomplete_provenance:{hero_id}")
            if not hero.portrait_url:
                errors.append(f"missing_portrait:{hero_id}")
            if not set(hero.roles).issubset(ROLES):
                errors.append(f"unknown_roles:{hero_id}")
            if set(hero.traits) != set(TRAITS):
                errors.append(f"incomplete_traits:{hero_id}")
            if any(value < 0 or value > 1 for value in hero.traits.values()):
                errors.append(f"trait_out_of_range:{hero_id}")
        if int(self.manifest.get("source_file_coverage_count", 0) or 0) != 127:
            errors.append("incomplete_research_file_coverage")
        if len(self.heroes) != 127:
            errors.append("incomplete_active_roster")
        return tuple(errors)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "manifest": dict(self.manifest),
            "heroes": {str(key): value.as_dict() for key, value in sorted(self.heroes.items())},
        }


def load_default_taxonomy() -> HeroTaxonomy:
    """Load only immutable checked-in snapshots; never scrape at report time."""

    factual = _read_json(_FACTUAL_PATH)
    editorial = _read_json(_EDITORIAL_PATH)
    manifest = _read_json(_MANIFEST_PATH)
    factual_list = factual.get("heroes", [])
    editorial_list = editorial.get("entries", [])
    if not isinstance(factual_list, list) or not isinstance(editorial_list, list):
        raise ValueError("Hero taxonomy snapshots must contain list records")
    factual_ids = [int(row["hero_id"]) for row in factual_list]
    editorial_ids = [int(row["hero_id"]) for row in editorial_list]
    if len(factual_ids) != len(set(factual_ids)) or len(editorial_ids) != len(set(editorial_ids)):
        raise ValueError("Hero taxonomy snapshots contain duplicate IDs")
    factual_rows = {int(row["hero_id"]): row for row in factual_list}
    editorial_rows = {int(row["hero_id"]): row for row in editorial_list}
    if set(factual_rows) != set(editorial_rows):
        raise ValueError("Hero taxonomy factual/editorial IDs do not match")

    heroes: dict[int, HeroTaxonomyEntry] = {}
    for hero_id in sorted(factual_rows):
        factual_row = factual_rows[hero_id]
        editorial_row = editorial_rows[hero_id]
        roles = tuple(str(role) for role in editorial_row.get("roles", factual_row.get("roles", [])))
        provenance = {
            **dict(factual_row.get("provenance", {})),
            "research_file": factual_row.get("research_file"),
            "editorial": dict(editorial_row.get("provenance", {})),
            "review_status": editorial_row.get("review_status"),
        }
        heroes[hero_id] = HeroTaxonomyEntry(
            hero_id=hero_id,
            key=str(factual_row["key"]),
            name=str(factual_row["name"]),
            roles=roles,
            traits={str(key): float(value) for key, value in editorial_row["traits"].items()},
            portrait_url=str(factual_row.get("portrait_ref", "")),
            available=bool(factual_row.get("available", True)),
            provenance=provenance,
        )
    combined_manifest = {
        **manifest,
        "factual_version": factual.get("version", FACTUAL_VERSION),
        "editorial_version": editorial.get("version", EDITORIAL_VERSION),
        "factual_checksum": _sha256(_FACTUAL_PATH),
        "editorial_checksum": _sha256(_EDITORIAL_PATH),
    }
    taxonomy = HeroTaxonomy(TAXONOMY_VERSION, heroes, combined_manifest)
    errors = taxonomy.validate()
    if errors:
        raise ValueError("Invalid hero taxonomy: " + ", ".join(errors))
    return taxonomy


def load_taxonomy(path: str | Path) -> HeroTaxonomy:
    """Load an aggregate taxonomy fixture while preserving strict validation."""

    value = _read_json(Path(path))
    heroes = {
        int(hero_id): HeroTaxonomyEntry(
            hero_id=int(item["hero_id"]),
            key=str(item["key"]),
            name=str(item["name"]),
            roles=tuple(str(role) for role in item.get("roles", [])),
            traits={str(key): float(trait) for key, trait in item.get("traits", {}).items()},
            portrait_url=str(item.get("portrait_url", item.get("portrait_ref", ""))),
            available=bool(item.get("available", True)),
            provenance=dict(item.get("provenance", {})),
            portrait_asset_version=str(item.get("portrait_asset_version", "hero-assets-2026-08-16")),
        )
        for hero_id, item in value.get("heroes", {}).items()
    }
    taxonomy = HeroTaxonomy(str(value.get("version", TAXONOMY_VERSION)), heroes, dict(value.get("manifest", {})))
    errors = taxonomy.validate()
    if errors:
        raise ValueError("Invalid hero taxonomy: " + ", ".join(errors))
    return taxonomy


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Hero taxonomy snapshot is missing: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Hero taxonomy snapshot must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
