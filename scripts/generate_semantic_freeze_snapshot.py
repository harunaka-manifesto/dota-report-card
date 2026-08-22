#!/usr/bin/env python3
"""Generate the deterministic full-roster semantic freeze.

The checked-in pilot remains an immutable historical artifact. This generator
builds the active layer from the local factual identity snapshot, the reviewed
editorial trait snapshot, and the local hero research files. It never calls a
network service or an LLM and it never upgrades an unavailable Valve or
OpenDota field into a fabricated fact.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.hero_knowledge.manifest import (
    build_knowledge_snapshot,
    build_manifest,
    sha256_file,
    write_json,
)
from scripts.hero_knowledge.validate import (
    assert_valid,
    validate_knowledge_snapshot,
    validate_semantic_layer,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "services/api/app/heroes/data"
FACTUAL_PATH = DATA_ROOT / "factual/2026-08-16.json"
EDITORIAL_PATH = DATA_ROOT / "editorial/2026-08-16.json"
SEMANTICS_PATH = DATA_ROOT / "semantics/full-roster-v1.json"
KNOWLEDGE_PATH = DATA_ROOT / "knowledge/hero-knowledge-semantic-freeze-full-roster-v1.json"
MANIFEST_PATH = DATA_ROOT / "hero-knowledge-manifest.json"
KNOWLEDGE_VERSION = "hero-knowledge-semantic-freeze-full-roster-v1"
SEMANTICS_VERSION = "hero-semantics-full-roster-v1"
GENERATED_AT = "2026-08-22T00:00:00Z"
PATCH = "7.41e"

FUNCTIONAL_JOBS = (
    "initiation",
    "counter_initiation",
    "catch",
    "frontline",
    "fight_control",
    "save",
    "sustain",
    "forced_movement",
    "repositioning",
    "mobility",
    "burst",
    "sustained_damage",
    "wave_clear",
    "push",
    "global_presence",
    "scaling",
    "vision",
)
DEMANDS = (
    "commitment",
    "access",
    "repositioning",
    "economy",
    "timing",
    "execution",
    "exposure",
    "micro",
)
BANDS = ("low", "medium", "high", "unknown")

# Editorial trait names are the only reviewed semantic signals used directly.
# Markdown keyword matches are narrow and are recorded as a derived rule.
FUNCTION_TRAITS: dict[str, tuple[str, ...]] = {
    "initiation": ("initiation",),
    "catch": ("pickoff",),
    "fight_control": ("teamfight",),
    "frontline": ("frontline",),
    "save": ("save",),
    "sustain": ("sustain",),
    "repositioning": ("repositioning", "mobility"),
    "mobility": ("mobility", "repositioning"),
    "burst": ("burst",),
    "sustained_damage": ("sustained_damage",),
    "wave_clear": ("wave_clear",),
    "push": ("push",),
    "global_presence": ("global_presence",),
    "scaling": ("scaling",),
    "vision": (),
    "counter_initiation": (),
    "forced_movement": (),
}
FUNCTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "initiation": (
        r"\binitiator?\b",
        r"\binitiat(?:e|es|ing|ion)\b",
        r"\bengage\b",
        r"\btaunt\b",
        r"\bcharge(?:s|d|ing)?\b[^.\n]{0,90}\b(?:enemy|enemies|hero|heroes|target|opponent|opponents|midst)\b",
        r"\b(?:enemy|enemies|hero|heroes|target|opponent|opponents)\b[^.\n]{0,90}\bcharge(?:s|d|ing)?\b",
        r"\bhurtle(?:s|d)? .*enemy",
        r"\benemy.?s midst\b",
    ),
    "counter_initiation": (r"counter[- ]?initiat", r"\bretaliat", r"\bpunish(?:es|ing)? .*commit"),
    "catch": (
        r"^(?!.*\b(?:no longer|does not|doesn't|is not|isn't|cannot|can't|without|removed)\b).*\b(?:hex(?:es|ed)?|root(?:s|ed|ing)?|stun(?:s|ned|ning)?|silence(?:s|d|ing)?|ensnar(?:e|es|ed|ing)?|trap(?:s|ped|ping)?)\b[^.\n]{0,90}\b(?:enemy|enemies|hero|heroes|unit|units|target|opponent|opponents|them)\b",
        r"^(?!.*\b(?:no longer|does not|doesn't|is not|isn't|cannot|can't|without|removed)\b).*\b(?:enemy|enemies|hero|heroes|unit|units|target|opponent|opponents|them)\b[^.\n]{0,90}\b(?:hex(?:es|ed)?|root(?:s|ed|ing)?|stun(?:s|ned|ning)?|silence(?:s|d|ing)?|ensnar(?:e|es|ed|ing)?|trap(?:s|ped|ping)?)\b",
    ),
    "frontline": (r"\bfrontline\b", r"\bdurable\b", r"\btank\b"),
    "fight_control": (
        r"\bteamfight\b",
        r"\barea denial\b",
        r"\bdisarm",
        r"\bzone",
        r"\bwall\b",
        r"\bbarrier\b",
    ),
    "save": (
        r"\bprotect(?:s|ed|ing)?\b[^.\n]{0,90}\b(?:ally|allies|allied|teammate|teammates|friendly|friend)\b",
        r"\b(?:ally|allies|allied|teammate|teammates|friendly|friend)\b[^.\n]{0,90}\b(?:protect(?:s|ed|ing)?|shield|barrier|invulnerab|safe)\b",
        r"\binvulnerab[^.\n]{0,90}\b(?:ally|allies|allied|teammate|teammates|friendly|friend)\b",
        r"\bprevent(?:s|ing)?\b[^.\n]{0,90}\b(?:death|damage|harm|disabl|kill)\b[^.\n]{0,60}\b(?:ally|allies|allied|teammate|teammates|friendly|friend)\b",
        r"\b(?:ally|allies|allied|teammate|teammates|friendly|friend)\b[^.\n]{0,90}\b(?:safe|protected|invulnerab)\b",
    ),
    "sustain": (
        r"\b(?:health|hp)\s+regen(?:eration)?\b",
        r"\b(?:lifesteal|life steal)\b",
        r"\b(?:heal(?:s|ed|ing)?|healing)\b[^.\n]{0,80}\b(?:ally|allies|friendly|friend|self|himself|herself|itself|target|unit|hero|heroes)\b",
        r"\b(?:ally|allies|friendly|friend|self|himself|herself|itself|target|unit|hero|heroes)\b[^.\n]{0,80}\b(?:heal(?:s|ed|ing)?|healing)\b",
        r"\brestor(?:e|es|ed|ing)\b[^.\n]{0,60}\b(?:health|hp|life)\b",
    ),
    "forced_movement": (
        r"\b(?:knock(?:s|ed|ing)?|knock[- ]?back)\b[^.\n]{0,90}\b(?:enemy|enemies|hero|heroes|unit|units|target|them)\b",
        r"\b(?:enemy|enemies|hero|heroes|unit|units|target|them)\b[^.\n]{0,90}\b(?:knock(?:s|ed|ing)?|knock[- ]?back)\b",
        r"\bpull(?:s|ed|ing)?\b[^.\n]{0,90}\b(?:enemy|enemies|ally|allies|hero|heroes|unit|units|target|them)\b",
        r"\b(?:enemy|enemies|ally|allies|hero|heroes|unit|units|target|them)\b[^.\n]{0,90}\bpull(?:s|ed|ing)?\b",
        r"\b(?:swap|swaps|swapped)\b[^.\n]{0,90}\bposition(?:s)?\b[^.\n]{0,80}\b(?:enemy|enemies|ally|allies|hero|heroes|unit|units|target)\b",
        r"\b(?:enemy|enemies|ally|allies|hero|heroes|unit|units|target)\b[^.\n]{0,90}\b(?:swap|swaps|swapped)\b[^.\n]{0,80}\bposition(?:s)?\b",
        r"\bdisplac(?:e|es|ed|ing)\b[^.\n]{0,90}\b(?:enemy|enemies|ally|allies|hero|heroes|unit|units|target|them)\b",
        r"\b(?:throw|toss|fling)(?:s|n|ed)?\b[^.\n]{0,90}\b(?:enemy|enemies|ally|allies|hero|heroes|unit|units|target|them)\b[^.\n]{0,80}\b(?:behind|back|away|toward|towards|direction|air|ground|landing|rear)\b",
        r"\b(?:enemy|enemies|ally|allies|hero|heroes|unit|units|target|them)\b[^.\n]{0,90}\b(?:throw|toss|fling)(?:s|n|ed)?\b[^.\n]{0,80}\b(?:behind|back|away|toward|towards|direction|air|ground|landing|rear)\b",
        r"\bteleport(?:s|ed|ing)?\b[^.\n]{0,80}\b(?:enemy|enemies|hero|heroes|unit|units|target|them)\b[^.\n]{0,40}\b(?:away|back)\b",
    ),
    "repositioning": (
        r"\breposition",
        r"\bblink\b",
        r"\bteleport",
        r"\bdash(?:es|ed)?\b",
        r"\bleap(?:s|ed)?\b",
        r"\bjump(?:s|ed)?\b",
    ),
    "mobility": (
        r"\bblink\b",
        r"\bteleport",
        r"\bdash(?:es|ed)?\b",
        r"\bleap(?:s|ed)?\b",
        r"\bescape\b",
    ),
    "burst": (
        r"\bnuke\b",
        r"\b(?:massive|huge|significant)[^.\n]{0,40}\bdamage\b",
        r"\binstant(?:ly)? .*damage",
    ),
    "sustained_damage": (
        r"\bburn(?:s|ed|ing)?\b",
        r"\bpoison",
        r"\bbleed",
        r"\battack speed\b",
        r"\bright[- ]click",
    ),
    "wave_clear": (r"\bwave clear\b", r"\bclear(?:s|ing)? (?:creep )?waves?\b", r"\bcreep wave\b"),
    "push": (
        r"\btower\b",
        r"\bbuilding\b",
        r"\bstructures?\b",
        r"\bsiege\b",
        r"\bpusher\b",
        r"\btreants?\b",
    ),
    "global_presence": (
        r"\bglobal(?:ly)? target\b",
        r"\banywhere on the map\b",
        r"\bany point on the map\b",
        r"\bacross the map\b",
        r"\bmap[- ]wide\b",
        r"\bglobal range\b",
        r"\bglobal cast range\b",
    ),
    # Generic occurrences such as "damage scales with distance" or
    # "accumulated damage" describe one spell's formula, not a reviewed
    # hero-level late-game job. Hero-level scaling comes from editorial traits
    # (with narrowly reviewed overrides below).
    "scaling": (),
    "vision": (r"\breveal", r"\btrue sight\b", r"\bscout", r"\bwards?\b"),
}
STRATEGY_PATTERNS: dict[str, tuple[str, ...]] = {
    "burst": (r"\bburst potential\b", r"\bburst damage\b", r"\bmassive burst\b"),
    "wave_clear": (
        r"\b(?:use|using|cast|casting|spam|spamming)\b[^.\n]{0,80}\b(?:clear|push out)\b[^.\n]{0,50}\b(?:wave|waves|creeps?)\b",
        r"\b(?:clear|push out)\b[^.\n]{0,50}\b(?:wave|waves|creeps?)\b[^.\n]{0,50}\b(?:using|with)\b",
    ),
    # Strategy prose can explain how to play against a hero. Save is therefore
    # earned from an explicit ally-protection mechanic (or a reviewed
    # per-hero override), not from the word "save" in advice.
    "save": (),
    "global_presence": (r"\bacross the map\b", r"\bglobally target\b", r"\bglobal cast range\b"),
}
DEMAND_TRAITS: dict[str, tuple[str, ...]] = {
    "commitment": ("frontline", "initiation"),
    "access": ("mobility", "global_presence", "repositioning"),
    "repositioning": ("mobility", "repositioning"),
    "economy": ("farm_dependency", "scaling"),
    "timing": ("complexity", "teamfight", "initiation"),
    "execution": ("complexity", "micro_intensity"),
    "exposure": ("frontline", "initiation"),
    "micro": ("micro_intensity",),
}
HERO_FUNCTION_OVERRIDES: dict[str, dict[str, tuple[str, ...]]] = {
    # Conservative conflict removals are explicit so future corpus wording
    # cannot silently reintroduce a job that the local evidence does not earn.
    "nyx_assassin": {
        "remove": ("frontline", "scaling", "sustain"),
        "priority": ("burst", "catch", "mobility", "repositioning"),
    },
    "abaddon": {"remove": ("burst", "catch")},
    "lycan": {"remove": ("catch",), "ensure": ("push",)},
    "rubick": {
        "remove": ("frontline", "wave_clear"),
    },
    "bane": {
        "ensure": ("catch",),
        "priority": ("catch", "fight_control", "sustain"),
    },
    "crystal_maiden": {
        "ensure": ("catch",),
        "priority": ("catch", "fight_control", "sustain"),
    },
    "morphling": {
        "ensure": ("mobility", "repositioning", "sustained_damage"),
        "priority": ("mobility", "repositioning", "sustained_damage", "catch"),
    },
    "nevermore": {
        "ensure": ("burst", "fight_control"),
        "priority": ("burst", "fight_control", "sustained_damage"),
    },
    "razor": {
        "ensure": ("sustained_damage", "frontline"),
        "priority": ("sustained_damage", "frontline", "fight_control"),
    },
    "sand_king": {
        "ensure": ("initiation", "mobility", "fight_control"),
        "priority": ("initiation", "mobility", "fight_control", "catch"),
    },
    "sven": {
        "ensure": ("burst", "sustained_damage", "frontline"),
        "priority": ("burst", "sustained_damage", "frontline", "initiation"),
    },
    "kunkka": {
        "ensure": ("burst", "fight_control"),
        "priority": ("burst", "fight_control", "forced_movement", "catch"),
    },
    "lich": {
        "ensure": ("burst", "fight_control", "save"),
        "priority": ("burst", "fight_control", "save", "catch"),
    },
    "necrolyte": {
        "ensure": ("sustained_damage", "scaling"),
        "priority": ("sustained_damage", "scaling", "fight_control", "sustain"),
    },
    "warlock": {
        "ensure": ("fight_control", "push"),
        "priority": ("fight_control", "push", "sustain", "catch"),
    },
    "death_prophet": {
        "ensure": ("sustain", "sustained_damage", "wave_clear"),
        "priority": ("sustain", "sustained_damage", "wave_clear", "push"),
    },
    "phantom_assassin": {"remove": ("forced_movement",)},
    "dazzle": {"remove": ("forced_movement",)},
    "alchemist": {"remove": ("forced_movement",)},
    "troll_warlord": {"remove": ("forced_movement",)},
    "elder_titan": {
        "remove": ("forced_movement",),
        "ensure": ("catch", "fight_control"),
        "priority": ("catch", "fight_control", "sustained_damage"),
    },
    "terrorblade": {"remove": ("forced_movement",)},
    "oracle": {"remove": ("forced_movement",)},
    "arc_warden": {"remove": ("forced_movement",)},
    "mirana": {"remove": ("initiation",)},
    "storm_spirit": {"remove": ("initiation",)},
    "sniper": {"remove": ("initiation",)},
    "skeleton_king": {"remove": ("initiation",)},
    "templar_assassin": {"remove": ("initiation",)},
    "clinkz": {"remove": ("initiation",)},
    "batrider": {
        "ensure": ("initiation",),
        "priority": ("initiation", "forced_movement", "mobility", "push"),
    },
    "ursa": {"remove": ("initiation",)},
    "invoker": {"remove": ("initiation",)},
    "broodmother": {"remove": ("initiation", "save")},
    "treant": {"remove": ("initiation",), "ensure": ("save",)},
    "visage": {
        "remove": ("initiation", "save", "scaling"),
        "ensure": ("burst", "catch", "push"),
        "priority": ("catch", "fight_control", "burst", "push"),
    },
    "ember_spirit": {"remove": ("initiation", "save")},
    "earth_spirit": {
        "remove": ("save",),
        "ensure": ("initiation",),
        "priority": ("initiation", "catch", "forced_movement", "mobility"),
    },
    "hoodwink": {
        "remove": ("initiation", "scaling"),
        "ensure": ("burst", "mobility"),
        "priority": ("burst", "mobility", "catch", "forced_movement"),
    },
    "ringmaster": {"remove": ("initiation", "catch")},
    "pudge": {"remove": ("save",)},
    "lion": {"remove": ("save",)},
    "viper": {
        "remove": ("save",),
        "ensure": ("catch", "frontline"),
        "priority": ("catch", "frontline", "sustained_damage", "sustain"),
    },
    "leshrac": {
        "ensure": ("catch", "wave_clear", "push"),
        "priority": ("catch", "wave_clear", "push", "sustained_damage"),
    },
    "life_stealer": {
        "ensure": ("frontline", "mobility"),
        "priority": ("frontline", "mobility", "sustained_damage", "sustain"),
    },
    "jakiro": {
        "ensure": ("fight_control", "wave_clear", "push"),
        "priority": ("fight_control", "wave_clear", "push", "sustained_damage"),
    },
    "dragon_knight": {"remove": ("save",)},
    "furion": {
        "remove": ("save", "scaling"),
        "ensure": ("global_presence",),
        "priority": ("global_presence", "mobility", "push", "fight_control"),
    },
    "dark_seer": {"remove": ("save",)},
    "ancient_apparition": {
        "remove": ("save", "sustain"),
        "ensure": ("burst", "global_presence", "catch"),
        "priority": ("burst", "global_presence", "catch", "fight_control"),
    },
    "doom_bringer": {
        "ensure": ("catch", "frontline"),
        "priority": ("catch", "frontline", "sustained_damage", "initiation"),
    },
    "gyrocopter": {
        "ensure": ("burst", "sustained_damage", "wave_clear"),
        "priority": ("burst", "sustained_damage", "wave_clear", "fight_control"),
    },
    "silencer": {
        "ensure": ("global_presence", "fight_control"),
        "priority": ("global_presence", "fight_control", "catch", "sustained_damage"),
    },
    "obsidian_destroyer": {
        "ensure": ("burst", "save"),
        "priority": ("burst", "save", "catch", "sustained_damage"),
    },
    "medusa": {"remove": ("save",)},
    "skywrath_mage": {"remove": ("save",)},
    "pangolier": {"remove": ("save",)},
    "grimstroke": {
        "remove": ("save",),
        "ensure": ("fight_control", "burst"),
        "priority": ("fight_control", "burst", "catch", "sustain"),
    },
    "void_spirit": {"remove": ("save",)},
    "mars": {"remove": ("save",)},
    "brewmaster": {
        "remove": ("scaling",),
        "ensure": ("fight_control", "frontline"),
        "priority": ("fight_control", "frontline", "catch", "sustained_damage"),
    },
    "undying": {
        "ensure": ("frontline", "fight_control"),
        "priority": ("frontline", "fight_control", "sustain", "catch"),
    },
    "shredder": {
        "ensure": ("frontline", "mobility", "burst"),
        "priority": ("frontline", "mobility", "burst", "sustained_damage"),
    },
    "huskar": {"remove": ("scaling",)},
    "wisp": {"remove": ("scaling",)},
    "dark_willow": {
        "remove": ("scaling",),
        "ensure": ("burst", "fight_control", "mobility"),
        "priority": ("burst", "fight_control", "mobility", "catch"),
    },
    "tinker": {"remove": ("scaling",)},
    "drow_ranger": {"remove": ("scaling",)},
    "rattletrap": {
        "ensure": ("initiation", "fight_control", "global_presence"),
        "priority": ("initiation", "catch", "fight_control", "global_presence"),
    },
    "meepo": {
        "remove": ("forced_movement", "global_presence", "mobility", "repositioning"),
        "ensure": ("catch", "sustained_damage", "push", "scaling"),
        "priority": ("catch", "sustained_damage", "push", "scaling"),
    },
    "techies": {
        "remove": ("save",),
        "ensure": ("initiation", "burst", "wave_clear"),
        "priority": ("initiation", "burst", "wave_clear", "fight_control", "push"),
    },
    "marci": {
        "ensure": ("forced_movement",),
        "priority": ("forced_movement", "catch", "mobility", "sustained_damage"),
    },
    "chen": {
        "remove": ("mobility", "repositioning", "scaling"),
        "ensure": ("sustain", "save", "push", "global_presence"),
        "priority": ("sustain", "push", "global_presence", "save"),
    },
}
SPECIALIST_MARKER_OVERRIDES: dict[str, tuple[str, ...]] = {
    "visage": ("multi_unit_control",),
    "brewmaster": ("multi_unit_control",),
}


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def _source_ref(relative: str, fragment: str) -> str:
    return f"editorial:{relative}#{fragment}"


def _derived_ref(hero_id: int, section: str, key: str) -> str:
    return f"derived:{SEMANTICS_VERSION}#hero:{hero_id}#{section}:{key}"


def _trait_ref(hero_id: int, trait: str) -> str:
    return _source_ref(
        "services/api/app/heroes/data/editorial/2026-08-16.json",
        f"hero:{hero_id}#trait:{trait}",
    )


def _catalog_add(
    catalog: dict[str, dict[str, Any]],
    ref: str,
    *,
    namespace: str,
    source_file: str | None = None,
    rule_version: str | None = None,
) -> None:
    value: dict[str, Any] = {"namespace": namespace}
    if source_file is not None:
        value["source_file"] = source_file
    if rule_version is not None:
        value["rule_version"] = rule_version
    catalog[ref] = value


def _metadata_path(row: Mapping[str, Any], root: Path) -> tuple[str, Path]:
    provenance = row.get("provenance", {})
    relative = provenance.get("source_file") if isinstance(provenance, Mapping) else None
    if not isinstance(relative, str) or not relative:
        relative = str(row.get("research_file", ""))
    path = root / relative
    if not path.is_file():
        raise ValueError(
            f"Missing local editorial research file for hero {row.get('hero_id')}: {relative}"
        )
    return relative, path


_NEGATED_PREFIX = re.compile(
    r"\b(?:no|not|never|without|cannot|can't|doesn't|does not|isn't|is not|won't|will not|don't|do not|removed|no longer)\b[^.!?]{0,60}$"
)


def _mechanic_lines(text: str) -> tuple[str, ...]:
    """Return narrative mechanics, excluding headings, stat rows, and patches."""

    lines: list[str] = []
    in_patch = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.casefold().startswith("#### patch"):
            in_patch = True
            continue
        if in_patch:
            if stripped == "* * *":
                in_patch = False
            continue
        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith("**")
            or stripped.startswith("*   ")
            or stripped == "* * *"
        ):
            continue
        lines.append(line)
    return tuple(lines)


def _match_score(text: str, patterns: tuple[str, ...]) -> float:
    matches = 0
    for pattern in patterns:
        for line in _mechanic_lines(text):
            found = next(re.finditer(pattern, line), None)
            if found is None:
                continue
            # A mechanic mentioned only as something that does *not* happen
            # (for example "hex doesn't remove ...") is not evidence for the
            # corresponding capability.
            if _NEGATED_PREFIX.search(line[: found.start()]):
                continue
            matches += 1
            break
    return min(0.95, 0.60 + 0.10 * matches) if matches else 0.0


def _trait_score(traits: Mapping[str, Any], names: tuple[str, ...]) -> float:
    values = [float(traits.get(name, 0.5)) for name in names]
    return max((value for value in values if value >= 0.60), default=0.0)


def _function_scores(
    hero_key: str, traits: Mapping[str, Any], text: str, strategy_text: str
) -> dict[str, float]:
    scores: dict[str, float] = {}
    overrides = HERO_FUNCTION_OVERRIDES.get(hero_key, {})
    removed = set(overrides.get("remove", ()))
    for function in FUNCTIONAL_JOBS:
        score = max(
            _trait_score(traits, FUNCTION_TRAITS.get(function, ())),
            _match_score(text, FUNCTION_PATTERNS.get(function, ())),
            _match_score(strategy_text, STRATEGY_PATTERNS.get(function, ())),
        )
        if score >= 0.60 and function not in removed:
            scores[function] = score
    for function in overrides.get("ensure", ()):
        if function not in removed:
            scores[function] = max(scores.get(function, 0.0), 0.70)
    if not scores:
        # This fallback is a derived low-confidence observation, never a
        # direct mechanic fact. Research files normally produce explicit hits.
        scores["sustained_damage"] = 0.60
    return scores


def _band(score: float) -> str:
    return "high" if score >= 0.80 else "medium" if score >= 0.60 else "unknown"


def _function_trait(function: str, traits: Mapping[str, Any]) -> str | None:
    for trait in FUNCTION_TRAITS.get(function, ()):
        if float(traits.get(trait, 0.5)) >= 0.60:
            return trait
    return None


def _demand_scores(
    traits: Mapping[str, Any], text: str, function_scores: Mapping[str, float]
) -> dict[str, float]:
    values: dict[str, float] = {}
    for demand in DEMANDS:
        trait_names = DEMAND_TRAITS[demand]
        score = max(
            [_trait_score(traits, trait_names)]
            + [function_scores.get(name, 0.0) for name in trait_names if name in FUNCTIONAL_JOBS]
        )
        if demand == "access":
            mobility = max(
                function_scores.get("mobility", 0.0), function_scores.get("global_presence", 0.0)
            )
            score = 0.60 if mobility else 0.0
        if demand == "repositioning" and not (
            function_scores.get("mobility") or function_scores.get("repositioning")
        ):
            score = 0.0
        if demand in {"timing", "execution"} and score == 0.0:
            score = _match_score(
                text, (r"\btiming\b", r"\bwindow\b", r"\bsequence\b", r"\bprecision\b")
            )
        if demand == "micro" and score == 0.0:
            score = _match_score(
                text, (r"\billusions?\b", r"\bsummon(?:s|ed)?\b", r"\bmultiple units\b")
            )
        if demand == "economy" and score == 0.0:
            score = _match_score(text, (r"\bfarm(?:ing)?\b", r"\bgold\b", r"\bitems?\b"))
        if score >= 0.60:
            values[demand] = score
    return values


def _semantic_value(band: str, refs: list[str]) -> dict[str, Any]:
    return {"band": band, "evidence_refs": list(dict.fromkeys(refs))}


def _build_full_semantics(factual: dict[str, Any], editorial: dict[str, Any]) -> dict[str, Any]:
    factual_rows = {
        int(row["hero_id"]): row for row in factual.get("heroes", []) if isinstance(row, dict)
    }
    editorial_rows = {
        int(row["hero_id"]): row for row in editorial.get("entries", []) if isinstance(row, dict)
    }
    if set(factual_rows) != set(editorial_rows) or len(factual_rows) != 127:
        raise ValueError("Full semantic freeze requires exactly 127 factual/editorial IDs")
    catalog: dict[str, dict[str, Any]] = {}
    heroes: list[dict[str, Any]] = []
    for hero_id in sorted(factual_rows):
        factual_row = factual_rows[hero_id]
        editorial_row = editorial_rows[hero_id]
        merged = {**factual_row, **editorial_row}
        relative, metadata = _metadata_path(merged, ROOT)
        full_text = metadata.read_text(encoding="utf-8").casefold()
        # Ability mechanics are the stable local evidence surface. Strategy
        # and counter-strategy prose contains advice about facing the hero
        # (for example "save the hero ..."), which must not become a claimed
        # capability of that hero.
        abilities_start = full_text.find("## abilities")
        talents_start = full_text.find("## talents", abilities_start + 1)
        text = full_text[
            abilities_start : talents_start if talents_start > abilities_start else None
        ]
        strategy_start = full_text.find("## strategy")
        counter_strategy_start = full_text.find("## counter strategy", strategy_start + 1)
        strategy_text = full_text[
            strategy_start : counter_strategy_start
            if counter_strategy_start > strategy_start
            else None
        ]
        traits = editorial_row.get("traits", {})
        if not isinstance(traits, Mapping):
            traits = {}
        source_ref = _source_ref(relative, "strategy")
        editorial_ref = _source_ref(relative, "abilities")
        _catalog_add(catalog, source_ref, namespace="editorial", source_file=relative)
        _catalog_add(catalog, editorial_ref, namespace="editorial", source_file=relative)
        _catalog_add(
            catalog,
            _source_ref(
                "services/api/app/heroes/data/editorial/2026-08-16.json", f"hero:{hero_id}#traits"
            ),
            namespace="editorial",
            source_file="services/api/app/heroes/data/editorial/2026-08-16.json",
        )
        hero_key = str(factual_row.get("key", ""))
        function_scores = _function_scores(hero_key, traits, text, strategy_text)
        priority = HERO_FUNCTION_OVERRIDES.get(hero_key, {}).get("priority", ())
        priority_index = {key: index for index, key in enumerate(priority)}
        ranked = sorted(
            function_scores,
            key=lambda key: (
                priority_index.get(key, len(priority_index)),
                -function_scores[key],
                key,
            ),
        )
        primary, secondary = ranked[:3], ranked[3:7]
        capabilities: dict[str, dict[str, Any]] = {}
        function_refs: dict[str, list[str]] = {}
        for function in (*primary, *secondary):
            derived_ref = _derived_ref(hero_id, "function", function)
            trait = _function_trait(function, traits)
            ability_signal = _match_score(text, FUNCTION_PATTERNS.get(function, ()))
            strategy_signal = _match_score(strategy_text, STRATEGY_PATTERNS.get(function, ()))
            source = source_ref if strategy_signal > ability_signal else editorial_ref
            if trait:
                refs = [_trait_ref(hero_id, trait)]
            else:
                refs = [source]
            refs.append(derived_ref)
            if trait:
                _catalog_add(
                    catalog,
                    _trait_ref(hero_id, trait),
                    namespace="editorial",
                    source_file="services/api/app/heroes/data/editorial/2026-08-16.json",
                )
            _catalog_add(catalog, derived_ref, namespace="derived", rule_version=SEMANTICS_VERSION)
            function_refs[function] = refs
            capabilities[function] = _semantic_value(_band(function_scores[function]), refs)
        demand_scores = _demand_scores(traits, f"{text}\n{strategy_text}", function_scores)
        demands: dict[str, dict[str, Any]] = {}
        demand_refs: dict[str, list[str]] = {}
        for demand in DEMANDS:
            derived_ref = _derived_ref(hero_id, "demand", demand)
            trait = next(
                (name for name in DEMAND_TRAITS[demand] if float(traits.get(name, 0.5)) >= 0.60),
                None,
            )
            refs = [_trait_ref(hero_id, trait)] if trait else [source_ref]
            refs.append(derived_ref)
            if trait:
                _catalog_add(
                    catalog,
                    _trait_ref(hero_id, trait),
                    namespace="editorial",
                    source_file="services/api/app/heroes/data/editorial/2026-08-16.json",
                )
            _catalog_add(catalog, derived_ref, namespace="derived", rule_version=SEMANTICS_VERSION)
            demand_refs[demand] = refs
            demands[demand] = _semantic_value(_band(demand_scores.get(demand, 0.0)), refs)
        # Broad role labels describe hero archetype, not a reviewed patch-
        # specific 1--5 position. Keep every position explicitly unknown until
        # a position-specific local review exists.
        position_credibility = {position: "unknown" for position in ("1", "2", "3", "4", "5")}
        position_ref = _derived_ref(hero_id, "position", "credibility")
        _catalog_add(catalog, position_ref, namespace="derived", rule_version=SEMANTICS_VERSION)
        strengths = [
            {"semantic_key": function, "evidence_refs": function_refs[function]}
            for function in primary[:2]
        ]
        weakness_order = sorted(
            DEMANDS,
            key=lambda key: (
                {"high": 3, "medium": 2, "low": 1, "unknown": 0}[demands[key]["band"]],
                key,
            ),
            reverse=True,
        )
        weaknesses = [
            {"semantic_key": demand, "evidence_refs": demand_refs[demand]}
            for demand in weakness_order[:2]
        ]
        if not strengths:
            strengths = [
                {
                    "semantic_key": "sustained_damage",
                    "evidence_refs": [
                        editorial_ref,
                        _derived_ref(hero_id, "function", "sustained_damage"),
                    ],
                }
            ]
        teamfight_candidates = [
            function
            for function in (*primary, *secondary)
            if function
            in {
                "initiation",
                "counter_initiation",
                "catch",
                "fight_control",
                "frontline",
                "save",
                "sustain",
                "forced_movement",
            }
        ]
        if not teamfight_candidates:
            teamfight_candidates = [primary[0] if primary else "sustained_damage"]
        teamfight_profile = [
            {
                "semantic_key": function,
                "priority": "primary" if function in primary else "secondary",
                "evidence_refs": function_refs.get(
                    function, [editorial_ref, _derived_ref(hero_id, "function", function)]
                ),
            }
            for function in teamfight_candidates[:2]
        ]
        review_ref = _derived_ref(hero_id, "review", "record")
        _catalog_add(catalog, review_ref, namespace="derived", rule_version=SEMANTICS_VERSION)
        specialist_markers: list[str] = []
        if float(traits.get("micro_intensity", 0.5)) >= 0.80:
            specialist_markers.append("micro_intensive")
        if float(traits.get("complexity", 0.5)) >= 0.80:
            specialist_markers.append("high_execution")
        if hero_key in {"meepo", "chen"}:
            specialist_markers.append("multi_unit_control")
        for marker in SPECIALIST_MARKER_OVERRIDES.get(hero_key, ()):
            if marker not in specialist_markers:
                specialist_markers.append(marker)
        heroes.append(
            {
                "hero_id": hero_id,
                "review_status": "approved",
                "position_credibility": position_credibility,
                "position_evidence_refs": [position_ref],
                "position_credibility_reason": "Broad role tags do not establish patch-specific 1-5 evidence.",
                "functions": {"primary": primary, "secondary": secondary},
                "capabilities": capabilities,
                "demands": demands,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "teamfight_profile": teamfight_profile,
                "specialist_markers": specialist_markers,
                "empirical_support": "unknown",
                # Semantic confidence is the confidence in this reviewed local
                # classification. It is intentionally independent from
                # empirical/current-meta support, which remains explicitly
                # unknown in this local-corpus freeze.
                "confidence": "high",
                "review": {
                    "sources": [source_ref, editorial_ref, review_ref],
                    "reviewer": "full-roster-semantic-freeze",
                    "reviewed_at": "2026-08-22",
                    "patch": PATCH,
                },
            }
        )
    # Add the two top-level review references to the same catalog used by all
    # field-level references, keeping resolution strict and deterministic.
    top_editorial_ref = "editorial:services/api/app/heroes/data/editorial/2026-08-16.json#snapshot"
    top_derived_ref = f"derived:{SEMANTICS_VERSION}#rule-set"
    _catalog_add(
        catalog,
        top_editorial_ref,
        namespace="editorial",
        source_file="services/api/app/heroes/data/editorial/2026-08-16.json",
    )
    _catalog_add(catalog, top_derived_ref, namespace="derived", rule_version=SEMANTICS_VERSION)
    return {
        "schema_version": "hero-semantics-1.1.0",
        "version": SEMANTICS_VERSION,
        "review_status": "reviewed",
        "hero_count": len(heroes),
        "vocabulary": {
            "functional_jobs": list(FUNCTIONAL_JOBS),
            "demands": list(DEMANDS),
            "bands": list(BANDS),
        },
        "review": {
            "reviewer": "full-roster-semantic-freeze",
            "reviewed_at": "2026-08-22",
            "patch": PATCH,
            "sources": [top_editorial_ref, top_derived_ref],
        },
        "evidence_sources": {
            "valve": {
                "namespace": "valve",
                "status": "unavailable",
                "reason": "No normalized Valve ability payload is in the allowed local corpus.",
            },
            "opendota": {
                "namespace": "opendota",
                "status": "unavailable",
                "reason": "No OpenDota aggregate payload is in the allowed local corpus.",
            },
            "editorial": {
                "namespace": "editorial",
                "status": "available",
                "source_file": "services/api/app/heroes/data/editorial/2026-08-16.json",
            },
            "derived": {
                "namespace": "derived",
                "status": "available",
                "rule_version": SEMANTICS_VERSION,
            },
        },
        "evidence_catalog": catalog,
        "heroes": heroes,
    }


def _source_snapshots(
    factual: dict[str, Any], semantics: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], set[int]]:
    factual_rows = {
        int(row["hero_id"]): row for row in factual.get("heroes", []) if isinstance(row, dict)
    }
    selected = set(factual_rows)
    semantic_ids = {
        int(row["hero_id"])
        for row in semantics.get("heroes", [])
        if isinstance(row, dict) and row.get("hero_id") is not None
    }
    if selected != semantic_ids:
        raise ValueError("Semantic and factual snapshots do not cover the same 127 hero IDs")
    valve_roster, valve_heroes, opendota_heroes = [], [], []
    for hero_id in sorted(selected):
        factual_row = factual_rows[hero_id]
        identity = {
            "hero_id": hero_id,
            "key": str(factual_row["key"]),
            "internal_name": str(factual_row["key"]),
            "display_name": str(factual_row["name"]),
            "primary_attribute": "unknown",
            "complexity": None,
            "portrait_ref": factual_row.get("portrait_ref"),
            "available": bool(factual_row.get("available", True)),
            "aliases": [str(factual_row["name"])],
            "roles": list(factual_row.get("roles", [])),
        }
        valve_roster.append(identity)
        valve_heroes.append(
            {
                "hero_id": hero_id,
                "identity": identity,
                "abilities": [],
                "facets": [],
                "talents": [],
                "base_stats": {},
                "facet_abilities": [],
            }
        )
        opendota_heroes.append(
            {
                "hero_id": hero_id,
                "bracket_performance": [],
                "duration_profile": [],
                "item_profile": [],
                "matchup_profile": [],
                "status": "unknown",
                "provenance": {"source": "unavailable_local_corpus"},
            }
        )
    return (
        {
            "snapshot_id": "factual-editorial-local-2026-08-16",
            "source_namespace": "factual",
            "patch": PATCH,
            "roster": valve_roster,
            "heroes": valve_heroes,
        },
        {
            "snapshot_id": "opendota-unavailable-local-corpus",
            "status": "unavailable",
            "required": False,
            "reason": "No OpenDota aggregate payload is in the allowed local corpus.",
            "heroes": opendota_heroes,
            "endpoint_semantics": {"population": "unknown"},
        },
        selected,
    )


def main() -> int:
    factual, editorial = _read(FACTUAL_PATH), _read(EDITORIAL_PATH)
    semantics = _build_full_semantics(factual, editorial)
    canonical_ids = {int(row["hero_id"]) for row in factual.get("heroes", [])}
    assert_valid(
        validate_semantic_layer(
            semantics, canonical_ids, require_complete=True, repo_root=ROOT, strict_evidence=True
        ),
        "full semantic layer",
    )
    write_json(SEMANTICS_PATH, semantics)
    valve, opendota, selected = _source_snapshots(factual, semantics)
    knowledge = build_knowledge_snapshot(
        valve,
        opendota,
        repo_root=ROOT,
        generated_at=GENERATED_AT,
        hero_ids=selected,
        knowledge_version=KNOWLEDGE_VERSION,
        reviewed_semantics=semantics,
    )
    # The active manifest is switched only after both semantic and generated
    # knowledge contracts pass their validation gates.
    assert_valid(validate_knowledge_snapshot(knowledge), "full knowledge snapshot")
    knowledge["freeze"] = {
        "status": "full-roster-reviewed",
        "hero_count": len(selected),
        "pilot_history_path": "semantics/pilot-v1.json",
        "semantic_vocabulary_version": semantics["version"],
        "copy_authoring_status": "not_started",
    }
    write_json(KNOWLEDGE_PATH, knowledge)
    manifest = build_manifest(knowledge, knowledge_path=KNOWLEDGE_PATH, generated_at=GENERATED_AT)
    manifest.update(
        {
            "knowledge_path": str(KNOWLEDGE_PATH.relative_to(DATA_ROOT)),
            "semantic_layer_path": str(SEMANTICS_PATH.relative_to(DATA_ROOT)),
            "semantic_layer_sha256": sha256_file(SEMANTICS_PATH),
            "semantic_vocabulary_version": semantics["version"],
            "freeze_status": "full-roster-reviewed",
            "hero_count": len(selected),
            "pilot_history_path": "semantics/pilot-v1.json",
        }
    )
    write_json(MANIFEST_PATH, manifest)
    print(
        json.dumps(
            {
                "knowledge": str(KNOWLEDGE_PATH),
                "semantic_layer": str(SEMANTICS_PATH),
                "manifest": str(MANIFEST_PATH),
                "heroes": len(selected),
                "reviewed": sum(
                    row.get("review_status") == "approved" for row in semantics["heroes"]
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
