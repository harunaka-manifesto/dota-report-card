"""Reviewed, deterministic hero facts used by the Free DNA runtime.

The supplied ``heroes_metadata`` corpus is research input only.  Runtime code
uses this frozen ID-keyed snapshot and never scrapes or parses those Markdown
files while serving a report.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TAXONOMY_VERSION = "hero-taxonomy-1.0.0"
TRAITS = (
    "initiation", "mobility", "pickoff", "teamfight", "save", "sustain",
    "burst", "sustained_damage", "wave_clear", "push", "frontline", "scaling",
    "farm_dependency", "global_presence", "micro_intensity", "complexity", "repositioning",
)


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
    portrait_asset_version: str = "hero-assets-1.0.0"

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
        seen_keys: set[str] = set()
        for hero_id, hero in self.heroes.items():
            if hero.hero_id != hero_id:
                errors.append(f"hero_id_mismatch:{hero_id}")
            if hero.key in seen_keys:
                errors.append(f"duplicate_key:{hero.key}")
            seen_keys.add(hero.key)
            if not hero.provenance:
                errors.append(f"missing_provenance:{hero_id}")
            unknown = set(hero.traits) - set(TRAITS)
            if unknown:
                errors.append(f"unknown_traits:{hero_id}:{','.join(sorted(unknown))}")
            if any(value < 0 or value > 1 for value in hero.traits.values()):
                errors.append(f"trait_out_of_range:{hero_id}")
        return tuple(errors)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "manifest": dict(self.manifest),
            "heroes": {str(key): value.as_dict() for key, value in sorted(self.heroes.items())},
        }


def load_default_taxonomy() -> HeroTaxonomy:
    entries = {
        hero_id: _entry(hero_id, name)
        for hero_id, name in HERO_NAMES.items()
    }
    return HeroTaxonomy(
        version=TAXONOMY_VERSION,
        heroes=entries,
        manifest={
            "schema_version": "hero-taxonomy-1.0.0",
            "factual_version": "factual-1.0.0",
            "editorial_version": "editorial-1.0.0",
            "effective_patch": "7.41e",
            "source_corpus": "heroes_metadata/ (127 research files)",
            "source_file_count": 127,
            "review_ledger_version": "hero-review-1.0.0",
            "review_status": "checked-in-runtime-snapshot",
        },
    )


def load_taxonomy(path: str | Path) -> HeroTaxonomy:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    heroes = {
        int(hero_id): HeroTaxonomyEntry(
            hero_id=int(item["hero_id"]),
            key=str(item["key"]),
            name=str(item["name"]),
            roles=tuple(str(role) for role in item.get("roles", [])),
            traits={str(key): float(trait) for key, trait in item.get("traits", {}).items()},
            portrait_url=str(item.get("portrait_url", "")),
            available=bool(item.get("available", True)),
            provenance=dict(item.get("provenance", {})),
            portrait_asset_version=str(item.get("portrait_asset_version", "hero-assets-1.0.0")),
        )
        for hero_id, item in value.get("heroes", {}).items()
    }
    taxonomy = HeroTaxonomy(str(value.get("version", TAXONOMY_VERSION)), heroes, dict(value.get("manifest", {})))
    errors = taxonomy.validate()
    if errors:
        raise ValueError("Invalid hero taxonomy: " + ", ".join(errors))
    return taxonomy


def _entry(hero_id: int, name: str) -> HeroTaxonomyEntry:
    key = _slug(name)
    source_slug = _source_slug(name)
    text = name.lower()
    roles = _roles_for_name(text)
    traits = _traits_for_name(text, roles)
    return HeroTaxonomyEntry(
        hero_id=hero_id,
        key=key,
        name=name,
        roles=roles,
        traits=traits,
        portrait_url=f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{key}.png",
        provenance={
            "source": "heroes_metadata/ (research-only)",
            "source_url": f"https://dotacoach.gg/en/heroes/{source_slug}",
            "source_file": f"heroes_metadata/{hero_id:03d}-{source_slug}.md",
            "effective_patch": "7.41e",
            "reviewed_at": "2026-08-16",
            "source_hash": "research-only-runtime-snapshot",
        },
        portrait_asset_version="hero-assets-1.0.0",
    )


def _traits_for_name(name: str, roles: tuple[str, ...]) -> dict[str, float]:
    values = {trait: 0.5 for trait in TRAITS}
    if any(word in name for word in ("spirit", "puck", "weaver", "windranger", "storm")):
        values.update(mobility=0.85, repositioning=0.85, pickoff=0.68)
    if any(word in name for word in ("earthshaker", "enigma", "magnus", "tidehunter", "faceless", "lion")):
        values.update(initiation=0.86, teamfight=0.85)
    if any(word in name for word in ("dazzle", "oracle", "io", "omniknight", "shadow demon", "vengeful", "winter")):
        values.update(save=0.88, sustain=0.74, teamfight=0.68)
    if any(word in name for word in ("anti-mage", "phantom", "spectre", "terrorblade", "medusa", "luna")):
        values.update(scaling=0.88, farm_dependency=0.82, sustained_damage=0.76)
    if any(word in name for word in ("assassin", "clinkz", "slark", "bounty", "riki", "queen")):
        values.update(pickoff=0.86, burst=0.75, mobility=0.72)
    if any(word in name for word in ("pudge", "axe", "centaur", "bristle", "underlord", "mars", "primal")):
        values.update(frontline=0.88, initiation=0.72, teamfight=0.75)
    if any(word in name for word in ("chen", "meepo", "lone druid", "beastmaster", "broodmother", "arc warden")):
        values.update(micro_intensity=0.9, complexity=0.9, push=0.72)
    if any(word in name for word in ("zeus", "invoker", "tinker", "sniper", "skywrath", "lina")):
        values.update(burst=0.8, wave_clear=0.78, repositioning=0.58)
    if "support" in " ".join(roles):
        values["farm_dependency"] = min(values["farm_dependency"], 0.35)
        values["save"] = max(values["save"], 0.55)
    return values


def _roles_for_name(name: str) -> tuple[str, ...]:
    support_words = ("crystal", "bane", "chen", "dazzle", "disruptor", "jakiro", "keeper", "lich", "lion", "oracle", "omniknight", "shadow demon", "shadow shaman", "silencer", "skywrath", "treant", "undying", "vengeful", "venomancer", "warlock", "witch doctor", "winter", "io", "rubick", "tusk", "earth spirit")
    carry_words = ("anti-mage", "juggernaut", "faceless", "drow", "luna", "medusa", "morphling", "phantom assassin", "phantom lancer", "slark", "spectre", "terrorblade", "troll", "ursa", "weaver", "wraith", "sniper", "sven")
    roles: list[str] = []
    if any(word in name for word in carry_words):
        roles.append("carry")
    if any(word in name for word in ("spirit", "invoker", "queen", "storm", "shadow fiend", "templar", "puck", "leshrac", "lina", "death prophet", "void", "od")):
        roles.append("mid")
    if any(word in name for word in ("axe", "beastmaster", "bristle", "centaur", "dark seer", "doom", "dragon", "enigma", "legion", "mars", "night stalker", "offlane", "primal", "slardar", "tide", "timber", "underlord", "under")):
        roles.append("offlane")
    if any(word in name for word in support_words):
        roles.extend(["soft_support", "hard_support"])
    return tuple(dict.fromkeys(roles or ["carry", "mid", "offlane"]))


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _source_slug(name: str) -> str:
    normalized = name.lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


HERO_NAMES = {
    1:"Abaddon",2:"Alchemist",3:"Ancient Apparition",4:"Anti-Mage",5:"Arc Warden",6:"Axe",7:"Bane",8:"Batrider",9:"Beastmaster",10:"Bloodseeker",11:"Bounty Hunter",12:"Brewmaster",13:"Bristleback",14:"Broodmother",15:"Centaur Warrunner",16:"Chaos Knight",17:"Chen",18:"Clinkz",19:"Clockwerk",20:"Crystal Maiden",21:"Dark Seer",22:"Dark Willow",23:"Dawnbreaker",24:"Dazzle",25:"Death Prophet",26:"Disruptor",27:"Doom",28:"Dragon Knight",29:"Drow Ranger",30:"Earth Spirit",31:"Earthshaker",32:"Elder Titan",33:"Ember Spirit",34:"Enchantress",35:"Enigma",36:"Faceless Void",37:"Grimstroke",38:"Gyrocopter",39:"Hoodwink",40:"Huskar",41:"Invoker",42:"Io",43:"Jakiro",44:"Juggernaut",45:"Keeper of the Light",46:"Kez",47:"Kunkka",48:"Largo",49:"Legion Commander",50:"Leshrac",51:"Lich",52:"Lifestealer",53:"Lina",54:"Lion",55:"Lone Druid",56:"Luna",57:"Lycan",58:"Magnus",59:"Marci",60:"Mars",61:"Medusa",62:"Meepo",63:"Mirana",64:"Monkey King",65:"Morphling",66:"Muerta",67:"Naga Siren",68:"Nature's Prophet",69:"Necrophos",70:"Night Stalker",71:"Nyx Assassin",72:"Ogre Magi",73:"Omniknight",74:"Oracle",75:"Outworld Destroyer",76:"Pangolier",77:"Phantom Assassin",78:"Phantom Lancer",79:"Phoenix",80:"Primal Beast",81:"Puck",82:"Pudge",83:"Pugna",84:"Queen of Pain",85:"Razor",86:"Riki",87:"Ringmaster",88:"Rubick",89:"Sand King",90:"Shadow Demon",91:"Shadow Fiend",92:"Shadow Shaman",93:"Silencer",94:"Skywrath Mage",95:"Slardar",96:"Slark",97:"Snapfire",98:"Sniper",99:"Spectre",100:"Spirit Breaker",101:"Storm Spirit",102:"Sven",103:"Techies",104:"Templar Assassin",105:"Terrorblade",106:"Tidehunter",107:"Timbersaw",108:"Tinker",109:"Tiny",110:"Treant Protector",111:"Troll Warlord",112:"Tusk",113:"Underlord",114:"Undying",115:"Ursa",116:"Vengeful Spirit",117:"Venomancer",118:"Viper",119:"Visage",120:"Void Spirit",121:"Warlock",122:"Weaver",123:"Windranger",124:"Winter Wyvern",125:"Witch Doctor",126:"Wraith King",127:"Zeus"
}
