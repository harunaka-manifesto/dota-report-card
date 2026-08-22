"""Derive structured hero characteristics from Valve mechanics.

Rules return evidence references, not prose.  A missing match is represented by
an absent characteristic; it is never filled with a neutral score.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .. import MECHANIC_RULE_VERSION


@dataclass(frozen=True, slots=True)
class _Rule:
    characteristic: str
    patterns: tuple[str, ...]
    minimum_matches: int = 1
    field: str = "ability"


RULES = (
    _Rule(
        "initiation", (r"taunt", r"stun", r"root", r"leash", r"latch", r"charge", r"force.*attack")
    ),
    _Rule("catch", (r"stun", r"root", r"leash", r"hex", r"silence", r"slow", r"taunt")),
    _Rule(
        "save",
        (
            r"ally.*(invulnerab|immun|prevent.*damage|damage.*barrier|grave|false promise)",
            r"damage.*(prevent|immun)",
            r"purge.*ally",
            r"protect.*ally",
        ),
    ),
    _Rule(
        "displacement",
        (r"knockback", r"forced movement", r"push", r"pull", r"swap", r"toss", r"throw"),
    ),
    _Rule(
        "mobility",
        (
            r"blink",
            r"dash",
            r"leap",
            r"jump",
            r"teleport",
            r"charge",
            r"roll",
            r"waveform",
            r"remnant",
        ),
    ),
    _Rule(
        "global_pressure",
        (r"global", r"anywhere", r"all enemy heroes", r"teleport.*location", r"across the map"),
    ),
    _Rule("vision", (r"provides? vision", r"reveals?", r"true sight", r"ward", r"scouting")),
    _Rule(
        "micro",
        (
            r"illusion",
            r"summon",
            r"controlled unit",
            r"clone",
            r"spirit",
            r"bear",
            r"treant",
            r"familiar",
            r"multiple meepos",
        ),
    ),
    _Rule("push", (r"building", r"structures", r"tower", r"summon", r"damage.*buildings")),
    _Rule(
        "sustained_damage",
        (r"damage over time", r"damage per second", r"burn", r"poison", r"bleed", r"attack speed"),
    ),
    _Rule("burst", (r"deals? .*damage", r"damage.*enemy", r"nuke")),
)


def _text(ability: dict[str, Any]) -> str:
    values = [
        ability.get("internal_name"),
        ability.get("display_name"),
        ability.get("description"),
        ability.get("lore"),
        ability.get("scepter_text"),
        ability.get("shard_text"),
    ]
    notes = ability.get("notes")
    if isinstance(notes, list):
        values.extend(notes)
    facets = ability.get("facet_text")
    if isinstance(facets, list):
        values.extend(facets)
    return " ".join(str(value) for value in values if value).casefold()


def _ability_ref(ability: dict[str, Any]) -> str:
    return f"ability:{ability.get('internal_name') or ability.get('ability_id')}"


def _band(count: int) -> str:
    return "high" if count >= 2 else "medium"


def _evidence(characteristic: str, refs: list[str], *, band: str | None = None) -> dict[str, Any]:
    value = {
        "characteristic": characteristic,
        "band": band or _band(len(refs)),
        "derived_from": sorted(set(refs)),
        "rule_version": MECHANIC_RULE_VERSION,
    }
    return value


def _matches(abilities: list[dict[str, Any]], rule: _Rule) -> list[str]:
    refs: list[str] = []
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in rule.patterns]
    for ability in abilities:
        text = _text(ability)
        if any(pattern.search(text) for pattern in compiled):
            refs.append(_ability_ref(ability))
    return refs


def _ability_count(
    abilities: list[dict[str, Any]], predicate: Callable[[str, dict[str, Any]], bool]
) -> list[str]:
    return [_ability_ref(ability) for ability in abilities if predicate(_text(ability), ability)]


def derive_mechanics(hero: dict[str, Any]) -> dict[str, Any]:
    abilities = [
        item
        for item in [*hero.get("abilities", []), *hero.get("facet_abilities", [])]
        if isinstance(item, dict)
    ]
    capabilities: dict[str, dict[str, Any]] = {}
    for rule in RULES:
        refs = _matches(abilities, rule)
        if len(refs) >= rule.minimum_matches:
            capabilities[rule.characteristic] = _evidence(rule.characteristic, refs)

    base = hero.get("base_stats", {})
    frontline_refs: list[str] = []
    try:
        if float(base.get("max_health")) >= 600 and float(base.get("armor")) >= 3:
            frontline_refs = ["base_stats:max_health", "base_stats:armor"]
    except (TypeError, ValueError):
        pass
    if "initiation" in capabilities and frontline_refs:
        capabilities["frontline"] = _evidence(
            "frontline", frontline_refs + capabilities["initiation"]["derived_from"], band="high"
        )
    elif frontline_refs:
        capabilities["frontline"] = _evidence("frontline", frontline_refs)

    aoe_refs = _ability_count(
        abilities,
        lambda text, ability: (
            ("radius" in text or "area" in text or "nearby" in text)
            and ("damage" in text or bool(ability.get("damages")))
        ),
    )
    if aoe_refs:
        capabilities["teamfight"] = _evidence("teamfight", aoe_refs)
        if len(aoe_refs) >= 2:
            capabilities["wave_clear"] = _evidence("wave_clear", aoe_refs)
    if "initiation" in capabilities and (
        "burst" in capabilities or "sustained_damage" in capabilities
    ):
        capabilities["pickoff"] = _evidence(
            "pickoff",
            capabilities["initiation"]["derived_from"]
            + capabilities.get("burst", capabilities.get("sustained_damage", {})).get(
                "derived_from", []
            ),
        )
    if "mobility" in capabilities:
        capabilities["repositioning"] = _evidence(
            "repositioning",
            capabilities["mobility"]["derived_from"],
            band=capabilities["mobility"]["band"],
        )
        capabilities["access"] = _evidence(
            "access",
            capabilities["mobility"]["derived_from"],
            band=capabilities["mobility"]["band"],
        )
    if "displacement" in capabilities:
        capabilities["counter_initiation"] = _evidence(
            "counter_initiation", capabilities["displacement"]["derived_from"]
        )
    if "micro" in capabilities:
        capabilities["execution"] = _evidence(
            "execution", capabilities["micro"]["derived_from"], band="high"
        )
    complexity = hero.get("identity", {}).get("complexity")
    if complexity == 3:
        capabilities["execution"] = _evidence("execution", ["identity:complexity"], band="high")

    primary = sorted(
        (key for key, value in capabilities.items() if value.get("band") == "high"),
        key=lambda key: (key not in {"teamfight", "initiation", "save", "mobility"}, key),
    )[:3]
    secondary = sorted(key for key in capabilities if key not in primary)[:4]

    demands: dict[str, dict[str, Any]] = {}
    if "frontline" in capabilities or "initiation" in capabilities:
        refs = capabilities.get("frontline", capabilities.get("initiation", {})).get(
            "derived_from", []
        )
        demands["commitment"] = _evidence(
            "commitment", refs, band="high" if "frontline" in capabilities else "medium"
        )
        demands["exposure"] = _evidence(
            "exposure", refs, band="high" if "frontline" in capabilities else "medium"
        )
    if "mobility" not in capabilities and "global_pressure" not in capabilities and abilities:
        demands["access"] = _evidence("access", ["rule:no_mobility_signal"], band="high")
    if "micro" in capabilities or complexity == 3:
        demands["execution"] = _evidence(
            "execution",
            capabilities.get("micro", {}).get("derived_from", ["identity:complexity"]),
            band="high",
        )

    return {
        "capabilities": capabilities,
        "functions": {"primary": primary, "secondary": secondary},
        "demands": demands,
        "provenance": {
            "rule_version": MECHANIC_RULE_VERSION,
            "source": "Valve normalized abilities and base stats",
        },
    }
