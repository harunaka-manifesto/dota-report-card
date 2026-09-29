"""Hero names for Matches search (matches/SSOT.md); presentation only, never analytical input.

Names come from the public dotaconstants hero table (snapshot 2026-09-29, 127 heroes),
checked in so nothing is fetched at runtime. Aliases are the common community shorthands.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Final, Literal

CONTRACT: Final[Literal["hero-catalog-v1"]] = "hero-catalog-v1"
MIN_PREFIX = 2

HEROES: Final[dict[int, tuple[str, str]]] = {
    1: ("antimage", "Anti-Mage"),
    2: ("axe", "Axe"),
    3: ("bane", "Bane"),
    4: ("bloodseeker", "Bloodseeker"),
    5: ("crystal_maiden", "Crystal Maiden"),
    6: ("drow_ranger", "Drow Ranger"),
    7: ("earthshaker", "Earthshaker"),
    8: ("juggernaut", "Juggernaut"),
    9: ("mirana", "Mirana"),
    10: ("morphling", "Morphling"),
    11: ("nevermore", "Shadow Fiend"),
    12: ("phantom_lancer", "Phantom Lancer"),
    13: ("puck", "Puck"),
    14: ("pudge", "Pudge"),
    15: ("razor", "Razor"),
    16: ("sand_king", "Sand King"),
    17: ("storm_spirit", "Storm Spirit"),
    18: ("sven", "Sven"),
    19: ("tiny", "Tiny"),
    20: ("vengefulspirit", "Vengeful Spirit"),
    21: ("windrunner", "Windranger"),
    22: ("zuus", "Zeus"),
    23: ("kunkka", "Kunkka"),
    25: ("lina", "Lina"),
    26: ("lion", "Lion"),
    27: ("shadow_shaman", "Shadow Shaman"),
    28: ("slardar", "Slardar"),
    29: ("tidehunter", "Tidehunter"),
    30: ("witch_doctor", "Witch Doctor"),
    31: ("lich", "Lich"),
    32: ("riki", "Riki"),
    33: ("enigma", "Enigma"),
    34: ("tinker", "Tinker"),
    35: ("sniper", "Sniper"),
    36: ("necrolyte", "Necrophos"),
    37: ("warlock", "Warlock"),
    38: ("beastmaster", "Beastmaster"),
    39: ("queenofpain", "Queen of Pain"),
    40: ("venomancer", "Venomancer"),
    41: ("faceless_void", "Faceless Void"),
    42: ("skeleton_king", "Wraith King"),
    43: ("death_prophet", "Death Prophet"),
    44: ("phantom_assassin", "Phantom Assassin"),
    45: ("pugna", "Pugna"),
    46: ("templar_assassin", "Templar Assassin"),
    47: ("viper", "Viper"),
    48: ("luna", "Luna"),
    49: ("dragon_knight", "Dragon Knight"),
    50: ("dazzle", "Dazzle"),
    51: ("rattletrap", "Clockwerk"),
    52: ("leshrac", "Leshrac"),
    53: ("furion", "Nature's Prophet"),
    54: ("life_stealer", "Lifestealer"),
    55: ("dark_seer", "Dark Seer"),
    56: ("clinkz", "Clinkz"),
    57: ("omniknight", "Omniknight"),
    58: ("enchantress", "Enchantress"),
    59: ("huskar", "Huskar"),
    60: ("night_stalker", "Night Stalker"),
    61: ("broodmother", "Broodmother"),
    62: ("bounty_hunter", "Bounty Hunter"),
    63: ("weaver", "Weaver"),
    64: ("jakiro", "Jakiro"),
    65: ("batrider", "Batrider"),
    66: ("chen", "Chen"),
    67: ("spectre", "Spectre"),
    68: ("ancient_apparition", "Ancient Apparition"),
    69: ("doom_bringer", "Doom"),
    70: ("ursa", "Ursa"),
    71: ("spirit_breaker", "Spirit Breaker"),
    72: ("gyrocopter", "Gyrocopter"),
    73: ("alchemist", "Alchemist"),
    74: ("invoker", "Invoker"),
    75: ("silencer", "Silencer"),
    76: ("obsidian_destroyer", "Outworld Devourer"),
    77: ("lycan", "Lycan"),
    78: ("brewmaster", "Brewmaster"),
    79: ("shadow_demon", "Shadow Demon"),
    80: ("lone_druid", "Lone Druid"),
    81: ("chaos_knight", "Chaos Knight"),
    82: ("meepo", "Meepo"),
    83: ("treant", "Treant Protector"),
    84: ("ogre_magi", "Ogre Magi"),
    85: ("undying", "Undying"),
    86: ("rubick", "Rubick"),
    87: ("disruptor", "Disruptor"),
    88: ("nyx_assassin", "Nyx Assassin"),
    89: ("naga_siren", "Naga Siren"),
    90: ("keeper_of_the_light", "Keeper of the Light"),
    91: ("wisp", "Io"),
    92: ("visage", "Visage"),
    93: ("slark", "Slark"),
    94: ("medusa", "Medusa"),
    95: ("troll_warlord", "Troll Warlord"),
    96: ("centaur", "Centaur Warrunner"),
    97: ("magnataur", "Magnus"),
    98: ("shredder", "Timbersaw"),
    99: ("bristleback", "Bristleback"),
    100: ("tusk", "Tusk"),
    101: ("skywrath_mage", "Skywrath Mage"),
    102: ("abaddon", "Abaddon"),
    103: ("elder_titan", "Elder Titan"),
    104: ("legion_commander", "Legion Commander"),
    105: ("techies", "Techies"),
    106: ("ember_spirit", "Ember Spirit"),
    107: ("earth_spirit", "Earth Spirit"),
    108: ("abyssal_underlord", "Underlord"),
    109: ("terrorblade", "Terrorblade"),
    110: ("phoenix", "Phoenix"),
    111: ("oracle", "Oracle"),
    112: ("winter_wyvern", "Winter Wyvern"),
    113: ("arc_warden", "Arc Warden"),
    114: ("monkey_king", "Monkey King"),
    119: ("dark_willow", "Dark Willow"),
    120: ("pangolier", "Pangolier"),
    121: ("grimstroke", "Grimstroke"),
    123: ("hoodwink", "Hoodwink"),
    126: ("void_spirit", "Void Spirit"),
    128: ("snapfire", "Snapfire"),
    129: ("mars", "Mars"),
    131: ("ringmaster", "Ring Master"),
    135: ("dawnbreaker", "Dawnbreaker"),
    136: ("marci", "Marci"),
    137: ("primal_beast", "Primal Beast"),
    138: ("muerta", "Muerta"),
    145: ("kez", "Kez"),
    155: ("largo", "Largo"),
}
ALIASES: Final[dict[str, int]] = {
    "aa": 68,  # Ancient Apparition
    "am": 1,  # Anti-Mage
    "bara": 71,  # Spirit Breaker
    "bh": 62,  # Bounty Hunter
    "cent": 96,  # Centaur Warrunner
    "ck": 81,  # Chaos Knight
    "cm": 5,  # Crystal Maiden
    "dk": 49,  # Dragon Knight
    "dp": 43,  # Death Prophet
    "ds": 55,  # Dark Seer
    "dw": 119,  # Dark Willow
    "es": 7,  # Earthshaker
    "et": 103,  # Elder Titan
    "furion": 53,  # Nature's Prophet
    "fv": 41,  # Faceless Void
    "kotl": 90,  # Keeper of the Light
    "lc": 104,  # Legion Commander
    "ld": 80,  # Lone Druid
    "ls": 54,  # Lifestealer
    "magina": 1,  # Anti-Mage
    "mk": 114,  # Monkey King
    "naix": 54,  # Lifestealer
    "np": 53,  # Nature's Prophet
    "ns": 60,  # Night Stalker
    "od": 76,  # Outworld Devourer
    "pa": 44,  # Phantom Assassin
    "pango": 120,  # Pangolier
    "pb": 137,  # Primal Beast
    "pl": 12,  # Phantom Lancer
    "qop": 39,  # Queen of Pain
    "rhasta": 27,  # Shadow Shaman
    "sb": 71,  # Spirit Breaker
    "sf": 11,  # Shadow Fiend
    "shaker": 7,  # Earthshaker
    "sk": 16,  # Sand King
    "ss": 27,  # Shadow Shaman
    "ta": 46,  # Templar Assassin
    "tb": 109,  # Terrorblade
    "tree": 83,  # Treant Protector
    "venge": 20,  # Vengeful Spirit
    "vs": 20,  # Vengeful Spirit
    "wd": 30,  # Witch Doctor
    "wisp": 91,  # Io
    "wk": 42,  # Wraith King
    "wr": 21,  # Windranger
    "ww": 112,  # Winter Wyvern
}


def normalize(text: str) -> str:
    """Lowercase ASCII words: accents folded, apostrophes dropped, other punctuation to spaces."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded.replace("'", "")).split())


def name(hero_id: int) -> str | None:
    hero = HEROES.get(hero_id)
    return hero[1] if hero else None


@lru_cache(maxsize=1)
def _index() -> tuple[tuple[int, tuple[str, ...]], ...]:
    # Each hero is searchable by its name words and by the words joined ("antimage", "shadowfiend").
    entries = []
    for hero_id, (_, display) in HEROES.items():
        words = normalize(display).split()
        entries.append((hero_id, (*words, "".join(words))))
    return tuple(entries)


def match_heroes(token: str, *, prefix: bool = True) -> frozenset[int]:
    """Heroes whose alias or name word equals the token or, with `prefix`, starts with it.

    Prefixes need two letters; callers pass prefix=False for reserved words such as "win",
    which must not also mean every hero whose name starts with it.
    """
    token = normalize(token).replace(" ", "")
    found = {ALIASES[token]} if token in ALIASES else set()
    if token:
        found |= {hero_id for hero_id, words in _index() if any(
            word == token or (prefix and len(token) >= MIN_PREFIX and word.startswith(token)) for word in words)}
    return frozenset(found)
