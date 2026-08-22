"""Provider-neutral seam for normalized hero knowledge.

The report and recommendation layers consume this shape, not raw Valve,
OpenDota, or optional experimental source payloads. The generated semantic
freeze snapshot is the active v5.2 provider; the checked-in taxonomy adapter
remains for historical and compatibility callers.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.heroes.taxonomy import HeroTaxonomy, HeroTaxonomyEntry

HERO_KNOWLEDGE_SCHEMA_VERSION = "hero-knowledge-schema-1.0.0"
HERO_SEMANTICS_VERSION = "hero-semantics-5.2.0"

# Position labels are deliberately separate from OpenDota's lane-role hint.
# The summary endpoint cannot establish a 1--5 position, so a reviewed
# semantic record must carry an explicit finite credibility band instead of
# letting a lane hint masquerade as position evidence.
DOTA_POSITIONS = ("1", "2", "3", "4", "5")
POSITION_CREDIBILITY_BANDS = frozenset(
    {"primary", "secondary", "unsupported", "unknown"}
)

# These vocabularies are intentionally small. Source adapters may emit richer
# evidence, but scoring and story code only sees these stable semantic keys.
# ``teamfight`` and the other legacy aliases are accepted by the adapters below
# but never emitted by the active product-facing layer.
FUNCTIONAL_JOBS = (
    "initiation",
    "counter_initiation",
    "catch",
    "fight_control",
    "frontline",
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
    "vision",
    "scaling",
)
HERO_DEMAND_FAMILIES = (
    "commitment",
    "access",
    "repositioning",
    "economy",
    "timing",
    "execution",
    "exposure",
    "micro",
)
DEMAND_GLOSSARY: dict[str, dict[str, str]] = {
    "commitment": {
        "internal_definition": "How much danger the hero usually accepts to create value.",
        "public_label": "Commitment",
        "public_short_description": "How much danger this hero accepts to create value.",
    },
    "access": {
        "internal_definition": "How much help the hero needs to reach a useful position or target.",
        "public_label": "Access",
        "public_short_description": "How much help this hero needs to reach a useful position.",
    },
    "repositioning": {
        "internal_definition": "How demanding it is to keep a useful position while the fight changes.",
        "public_label": "Repositioning",
        "public_short_description": "How demanding it is to keep a useful position.",
    },
    "economy": {
        "internal_definition": "How strongly the hero's value depends on resources and time.",
        "public_label": "Resource needs",
        "public_short_description": "How strongly value depends on resources and time.",
    },
    "timing": {
        "internal_definition": "How much value depends on choosing a narrow timing window.",
        "public_label": "Timing",
        "public_short_description": "How much value depends on a narrow timing window.",
    },
    "execution": {
        "internal_definition": "How much precision is needed to convert the hero's tools.",
        "public_label": "Execution",
        "public_short_description": "How much precision is needed to convert the hero's tools.",
    },
    "exposure": {
        "internal_definition": "How exposed the hero must be to create or absorb pressure.",
        "public_label": "Exposure",
        "public_short_description": "How exposed this hero must be to create pressure.",
    },
    "micro": {
        "internal_definition": "How much simultaneous control or attention the hero demands.",
        "public_label": "Attention load",
        "public_short_description": "How much simultaneous control or attention the hero demands.",
    },
}
SEMANTIC_BANDS = frozenset({"low", "medium", "high", "unknown"})
REVIEW_STATUSES = frozenset({"unreviewed", "unknown", "draft", "reviewed", "approved", "stale"})
EMPIRICAL_SUPPORT_BANDS = frozenset({"high", "medium", "low", "unknown"})
SEMANTIC_CONFIDENCE_BANDS = frozenset({"high", "medium", "low"})

# Public glossary. Keep the internal definition beside the label so a new
# surface cannot accidentally expose a raw semantic key without a useful
# explanation. The wording is deliberately neutral; production tone belongs
# in the copy catalog.
JOB_GLOSSARY: dict[str, dict[str, Any]] = {
    "initiation": {
        "internal_definition": "Reliably starts a fight on the team's terms.",
        "public_label": "Fight start",
        "public_short_description": "Starts fights on your terms.",
    },
    "counter_initiation": {
        "internal_definition": "Punishes an enemy commitment after it begins.",
        "public_label": "Counter-engage",
        "public_short_description": "Punishes enemies after they commit.",
    },
    "catch": {
        "internal_definition": "Prevents a target from escaping or repositioning.",
        "public_label": "Catch",
        "public_short_description": "Locks down a target before they escape.",
    },
    "fight_control": {
    "internal_definition": "Limits where enemies can stand, move, or act after the fight starts.",
        "public_label": "Fight control",
        "public_short_description": "Restricts where enemies can move or act once the fight starts.",
    },
    "frontline": {
        "internal_definition": "Can occupy dangerous space for the team.",
        "public_label": "Frontline",
        "public_short_description": "Can occupy dangerous space for the team.",
    },
    "save": {
        "internal_definition": "Prevents an ally from dying or being disabled.",
        "public_label": "Save",
        "public_short_description": "Prevents an ally from dying or being disabled.",
    },
    "sustain": {
        "internal_definition": "Keeps allies healthy through longer fights.",
        "public_label": "Sustain",
        "public_short_description": "Keeps allies healthy through longer fights.",
    },
    "forced_movement": {
        "internal_definition": "Moves heroes away from where they wanted to be.",
        "public_label": "Forced movement",
        "public_short_description": "Moves heroes from where they wanted to be.",
    },
    "repositioning": {
        "internal_definition": "Creates a new position during or after contact.",
        "public_label": "Repositioning",
        "public_short_description": "Reaches a better position during the fight.",
    },
    "mobility": {
        "internal_definition": "Reaches or leaves positions quickly.",
        "public_label": "Mobility",
        "public_short_description": "Reaches or leaves positions quickly.",
    },
    "burst": {
        "internal_definition": "Deals a large amount of damage in a short window.",
        "public_label": "Burst damage",
        "public_short_description": "Deals a lot of damage in a short window.",
    },
    "sustained_damage": {
        "internal_definition": "Keeps damage flowing through a longer fight.",
        "public_label": "Sustained damage",
        "public_short_description": "Keeps damage flowing through a longer fight.",
    },
    "wave_clear": {
        "internal_definition": "Removes creep waves quickly and safely.",
        "public_label": "Wave clear",
        "public_short_description": "Removes creep waves quickly.",
    },
    "push": {
        "internal_definition": "Converts space and time into building pressure.",
        "public_label": "Tower pressure",
        "public_short_description": "Converts space into building pressure.",
    },
    "global_presence": {
        "internal_definition": "Influences distant parts of the map quickly.",
        "public_label": "Global reach",
        "public_short_description": "Influences distant parts of the map quickly.",
    },
    "vision": {
        "internal_definition": "Creates or denies information about the map.",
        "public_label": "Vision",
        "public_short_description": "Creates or denies information.",
    },
    "scaling": {
        "internal_definition": "Gains unusually high value as resources accumulate.",
        "public_label": "Late-game scaling",
        "public_short_description": "Gains more value as resources accumulate.",
    },
}

COVERAGE_FAMILIES: dict[str, dict[str, Any]] = {
    "engage_control": {
        "public_label": "Engage & Control",
        "public_short_description": "Start fights and shape what happens after contact.",
        "functions": ("initiation", "counter_initiation", "catch", "fight_control", "forced_movement"),
    },
    "frontline_protection": {
        "public_label": "Frontline & Protection",
        "public_short_description": "Occupy danger and keep teammates in the fight.",
        "functions": ("frontline", "save", "sustain"),
    },
    "damage_finish": {
        "public_label": "Damage & Finish",
        "public_short_description": "Create and convert damage over short or long windows.",
        "functions": ("burst", "sustained_damage", "scaling"),
    },
    "map_objectives": {
        "public_label": "Map & Objectives",
        "public_short_description": "Turn map space into waves, information, and buildings.",
        "functions": ("wave_clear", "push", "global_presence", "vision"),
    },
    "mobility_reach": {
        "public_label": "Mobility & Reach",
        "public_short_description": "Reach the right place or change position quickly.",
        "functions": ("mobility", "repositioning"),
    },
}

ROLE_RELEVANT_FAMILIES: dict[str, tuple[str, ...]] = {
    "carry": ("engage_control", "damage_finish", "map_objectives", "mobility_reach"),
    "mid": tuple(COVERAGE_FAMILIES),
    "offlane": ("engage_control", "frontline_protection", "damage_finish", "map_objectives", "mobility_reach"),
    "soft_support": ("engage_control", "frontline_protection", "map_objectives", "mobility_reach"),
    "hard_support": ("engage_control", "frontline_protection", "map_objectives", "mobility_reach"),
    "roamer": ("engage_control", "frontline_protection", "map_objectives", "mobility_reach"),
    "jungle": ("damage_finish", "map_objectives", "mobility_reach"),
}

_FUNCTION_ALIASES = {
    "teamfight": "fight_control",
    "teamfight_control": "fight_control",
    "pickoff": "catch",
    "displacement": "forced_movement",
    "global_pressure": "global_presence",
    "damage": "sustained_damage",
}


def canonical_function_key(value: str) -> str:
    """Normalize legacy semantic labels into the active public vocabulary."""

    return _FUNCTION_ALIASES.get(value, value)


def job_definition(value: str) -> dict[str, Any] | None:
    return JOB_GLOSSARY.get(canonical_function_key(value))


def demand_definition(value: str) -> dict[str, str] | None:
    return DEMAND_GLOSSARY.get(value)


def role_relevant_families(roles: Sequence[str]) -> tuple[str, ...]:
    """Return the smallest reviewed coverage universe for observed roles."""

    selected = {family for role in roles for family in ROLE_RELEVANT_FAMILIES.get(role, ())}
    return tuple(family for family in COVERAGE_FAMILIES if family in selected) or tuple(COVERAGE_FAMILIES)


def family_for_function(value: str) -> str | None:
    key = canonical_function_key(value)
    return next(
        (family for family, definition in COVERAGE_FAMILIES.items() if key in definition["functions"]),
        None,
    )


@dataclass(frozen=True, slots=True)
class NormalizedHeroKnowledge:
    hero_id: int
    display_name: str
    roles: tuple[str, ...]
    functional_jobs: tuple[str, ...]
    provenance_versions: Mapping[str, str]
    primary_functions: tuple[str, ...] = ()
    secondary_functions: tuple[str, ...] = ()
    demands: Mapping[str, str] = field(default_factory=dict)
    capabilities: Mapping[str, str] = field(default_factory=dict)
    empirical_support: str = "unknown"
    confidence: str = "low"
    evidence_refs: tuple[str, ...] = ()
    review_status: str = "unreviewed"
    position_credibility: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Keep the contract explicit even for compatibility fixtures and
        # structural adapters that omit the map: every Dota position is a
        # finite credibility band, never an implicit neutral score.
        object.__setattr__(
            self,
            "position_credibility",
            _position_credibility(self.position_credibility),
        )


class HeroKnowledgeProvider(Protocol):
    """Read-only interface used by deterministic recommendation consumers."""

    version: str

    def get(self, hero_id: int | None) -> NormalizedHeroKnowledge | None: ...


class TaxonomyHeroKnowledgeProvider:
    """Adapt the reviewed taxonomy snapshot to the normalized interface."""

    def __init__(self, taxonomy: HeroTaxonomy) -> None:
        self._taxonomy = taxonomy
        snapshot = taxonomy.version.removeprefix("hero-taxonomy-")
        self.version = f"hero-knowledge-{snapshot}"

    def get(self, hero_id: int | None) -> NormalizedHeroKnowledge | None:
        entry = self._taxonomy.get(hero_id)
        return normalized_hero_knowledge(entry, version=self.version) if entry else None

    @property
    def entries(self) -> Sequence[NormalizedHeroKnowledge]:
        return tuple(
            normalized_hero_knowledge(entry, version=self.version)
            for entry in self._taxonomy.heroes.values()
        )

    @property
    def taxonomy(self) -> HeroTaxonomy:
        return self._taxonomy


def normalized_hero_knowledge(entry: HeroTaxonomyEntry, *, version: str) -> NormalizedHeroKnowledge:
    # Import lazily because app.behavior.presentation imports this module to
    # type its provider seam; importing the display helper at module import
    # time would create a behavior ↔ hero circular import.
    from app.behavior.display_bands import job_display_label

    active = tuple(
        canonical_function_key(key)
        for key, value in sorted(entry.traits.items())
        if value >= 0.60 and _canonical_function_key(key) in FUNCTIONAL_JOBS
    )
    primary = active[:3]
    secondary = tuple(item for item in active if item not in primary)[:4]
    demands: dict[str, str] = {}
    if entry.traits.get("frontline", 0.0) >= 0.60 or entry.traits.get("initiation", 0.0) >= 0.60:
        demands["commitment"] = "high" if entry.traits.get("frontline", 0.0) >= 0.60 else "medium"
        demands["exposure"] = "high" if entry.traits.get("frontline", 0.0) >= 0.60 else "medium"
    if entry.traits.get("mobility", 0.0) < 0.60 and entry.traits.get("global_presence", 0.0) < 0.60:
        demands["access"] = "unknown"
    if entry.traits.get("farm_dependency", 0.0) >= 0.60:
        demands["economy"] = "high"
    if entry.traits.get("micro_intensity", 0.0) >= 0.60:
        demands["micro"] = "high"
    if entry.traits.get("complexity", 0.0) >= 0.60:
        demands["execution"] = "high"
    capabilities = {key: "high" for key in (*primary, *secondary)}
    # Taxonomy roles are a structural compatibility hint, not reviewed
    # position evidence.  Keep the role-derived map available to compatibility
    # callers, while FullRosterHeroKnowledgeProvider explicitly downgrades it
    # to unknown for structural fallback records.
    position_credibility = _position_credibility_from_roles(entry.roles)
    return NormalizedHeroKnowledge(
        hero_id=entry.hero_id,
        display_name=entry.name,
        roles=entry.roles,
        functional_jobs=tuple(job_display_label(key) for key in (*primary, *secondary)),
        provenance_versions={
            "hero_knowledge": version,
            "hero_knowledge_schema": HERO_KNOWLEDGE_SCHEMA_VERSION,
        },
        primary_functions=primary,
        secondary_functions=secondary,
        demands=demands,
        capabilities=capabilities,
        empirical_support="unknown",
        confidence="medium",
        evidence_refs=(),
        review_status="reviewed",
        position_credibility=position_credibility,
    )


@dataclass(frozen=True, slots=True)
class HeroKnowledgeRecord:
    """One generated, product-facing record loaded from a frozen snapshot."""

    data: dict[str, Any]

    @property
    def hero_id(self) -> int:
        return int(self.data["identity"]["hero_id"])

    @property
    def name(self) -> str:
        identity = self.data["identity"]
        return str(identity.get("display_name", identity.get("name", "")))

    def as_dict(self) -> dict[str, Any]:
        return dict(self.data)


class HeroKnowledgeRepository:
    """Read generated knowledge without introducing runtime network calls."""

    def __init__(
        self, snapshot_path: str | Path | None = None, *, data_root: str | Path | None = None
    ) -> None:
        if snapshot_path is None:
            root = Path(data_root) if data_root is not None else Path(__file__).with_name("data")
            manifest_path = root / "hero-knowledge-manifest.json"
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                relative_path = Path(str(manifest["knowledge_path"]))
                snapshot_path = (
                    relative_path if relative_path.is_absolute() else root / relative_path
                )
            except (FileNotFoundError, KeyError, json.JSONDecodeError):
                snapshot_path = None
        self._snapshot_path = Path(snapshot_path) if snapshot_path is not None else None
        self._snapshot = self._load(self._snapshot_path) if self._snapshot_path else None

    @staticmethod
    def _load(path: Path | None) -> dict[str, Any] | None:
        if path is None or not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None

    def get(self, hero_id: int | None) -> HeroKnowledgeRecord | None:
        if hero_id is None:
            return None
        if not self._snapshot:
            return None
        for row in self._snapshot.get("heroes", []):
            if isinstance(row, dict) and row.get("identity", {}).get("hero_id") == hero_id:
                return HeroKnowledgeRecord(row)
        return None

    def list_all(self) -> list[HeroKnowledgeRecord]:
        if not self._snapshot:
            return []
        return [
            HeroKnowledgeRecord(row)
            for row in self._snapshot.get("heroes", [])
            if isinstance(row, dict)
        ]

    def version(self) -> str | None:
        if not self._snapshot or not self._snapshot.get("knowledge_version"):
            return None
        return str(self._snapshot["knowledge_version"])


class SnapshotHeroKnowledgeProvider:
    """Adapt a generated, reviewed snapshot to the runtime provider seam.

    The repository deliberately remains a raw-record reader for build and
    migration tooling.  This adapter is the only shape consumed by active
    recommendation and presentation code.
    """

    def __init__(
        self,
        repository: HeroKnowledgeRepository | None = None,
        *,
        snapshot_path: str | Path | None = None,
        data_root: str | Path | None = None,
    ) -> None:
        self.repository = repository or HeroKnowledgeRepository(
            snapshot_path=snapshot_path,
            data_root=data_root,
        )
        self.version = self.repository.version() or "hero-knowledge-unavailable"

    @property
    def available(self) -> bool:
        return self.repository.version() is not None

    def get(self, hero_id: int | None) -> NormalizedHeroKnowledge | None:
        record = self.repository.get(hero_id)
        return _normalize_generated_record(record, version=self.version) if record else None

    @property
    def entries(self) -> Sequence[NormalizedHeroKnowledge]:
        return tuple(
            _normalize_generated_record(record, version=self.version)
            for record in self.repository.list_all()
        )


class FullRosterHeroKnowledgeProvider:
    """Compose reviewed semantic records with structural full-roster coverage.

    The reviewed snapshot is preferred for heroes it contains. The checked-in
    roster adapter supplies an explicit, lower-confidence structural record for
    every remaining hero so missing pilot records cannot silently become zero
    coverage in production scoring.
    """

    def __init__(
        self,
        taxonomy: HeroTaxonomy,
        reviewed: SnapshotHeroKnowledgeProvider | None = None,
    ) -> None:
        self._structural = TaxonomyHeroKnowledgeProvider(taxonomy)
        self._reviewed = reviewed or SnapshotHeroKnowledgeProvider()
        self.version = f"{self._reviewed.version}+{self._structural.version}"

    @property
    def available(self) -> bool:
        return bool(self._structural.entries)

    def get(self, hero_id: int | None) -> NormalizedHeroKnowledge | None:
        reviewed = self._reviewed.get(hero_id)
        if reviewed is not None and reviewed.review_status in {"approved", "reviewed"}:
            return reviewed
        structural = self._structural.get(hero_id)
        if structural is None:
            return None
        # Structural records are intentionally explicit about their lower
        # confidence and provenance; callers can gate claims on this status.
        return NormalizedHeroKnowledge(
            hero_id=structural.hero_id,
            display_name=structural.display_name,
            roles=structural.roles,
            functional_jobs=structural.functional_jobs,
            provenance_versions={
                **dict(structural.provenance_versions),
                "hero_semantics": self.version,
            },
            primary_functions=structural.primary_functions,
            secondary_functions=structural.secondary_functions,
            demands=structural.demands,
            capabilities=structural.capabilities,
            empirical_support="unknown",
            confidence="low",
            evidence_refs=structural.evidence_refs,
            review_status="unreviewed",
            position_credibility={position: "unknown" for position in DOTA_POSITIONS},
        )

    @property
    def entries(self) -> Sequence[NormalizedHeroKnowledge]:
        return tuple(
            entry
            for hero_id in sorted(self._structural.taxonomy.heroes)
            if (entry := self.get(hero_id)) is not None
        )


def _normalize_generated_record(
    record: HeroKnowledgeRecord, *, version: str
) -> NormalizedHeroKnowledge:
    data = record.data
    functions = data.get("functions", {})
    primary = _function_keys(functions.get("primary", []) if isinstance(functions, Mapping) else [])
    secondary = _function_keys(functions.get("secondary", []) if isinstance(functions, Mapping) else [])
    primary = _dedupe_known(primary)
    secondary = tuple(item for item in _dedupe_known(secondary) if item not in primary)
    demands = _band_map(data.get("demands"))
    capabilities = _band_map(data.get("capabilities"))
    empirical_support = _normalize_empirical_support(data)
    confidence = _normalize_confidence(data)
    review_status = str(data.get("editorial", {}).get("review_status", "unreviewed"))
    position_credibility = _position_credibility(data.get("position_credibility"))
    source_versions = data.get("provenance", {}).get("source_versions", {})
    provenance_versions = {
        "hero_knowledge": version,
        "hero_knowledge_schema": HERO_KNOWLEDGE_SCHEMA_VERSION,
    }
    if isinstance(source_versions, Mapping):
        for key, value in source_versions.items():
            if value is not None:
                provenance_versions[str(key)] = str(value)
    if data.get("semantic_version"):
        provenance_versions["hero_semantics"] = str(data["semantic_version"])
    evidence_refs = _evidence_refs(data, (*primary, *secondary), demands, capabilities)
    return NormalizedHeroKnowledge(
        hero_id=record.hero_id,
        display_name=record.name,
        roles=tuple(str(role) for role in data.get("identity", {}).get("roles", [])),
        functional_jobs=tuple(_display_job(item) for item in (*primary, *secondary)),
        provenance_versions=provenance_versions,
        primary_functions=primary,
        secondary_functions=secondary,
        demands=demands,
        capabilities=capabilities,
        empirical_support=empirical_support,
        confidence=confidence,
        evidence_refs=evidence_refs,
        review_status=review_status,
        position_credibility=position_credibility,
    )


def _function_keys(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    result: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            item = item.get("semantic_key", item.get("characteristic", item.get("key")))
        if item is not None:
            result.append(canonical_function_key(str(item)))
    return tuple(result)


def _canonical_function_key(value: str) -> str:
    return canonical_function_key(value)


def _dedupe_known(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value in FUNCTIONAL_JOBS))


def _band_map(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, raw in value.items():
        if isinstance(raw, Mapping):
            raw = raw.get("band", "unknown")
        normalized = str(raw).casefold()
        result[canonical_function_key(str(key))] = normalized if normalized in SEMANTIC_BANDS else "unknown"
    return {
        key: value
        for key, value in result.items()
        if key in HERO_DEMAND_FAMILIES or key in FUNCTIONAL_JOBS
    }


def _normalize_empirical_support(data: Mapping[str, Any]) -> str:
    raw = data.get("empirical_support")
    if raw is None:
        empirical = data.get("empirical", {})
        status = empirical.get("status") if isinstance(empirical, Mapping) else None
        raw = "unknown" if status in {None, "unknown", "unavailable"} else "medium"
    value = str(raw).casefold()
    return value if value in EMPIRICAL_SUPPORT_BANDS else "unknown"


def _normalize_confidence(data: Mapping[str, Any]) -> str:
    raw = data.get("semantic_confidence", data.get("confidence"))
    if raw is None:
        provenance = data.get("provenance", {})
        confidence = provenance.get("confidence", {}) if isinstance(provenance, Mapping) else {}
        raw = confidence.get("band", "low") if isinstance(confidence, Mapping) else "low"
    value = str(raw).casefold()
    if value == "moderate":
        value = "medium"
    return value if value in SEMANTIC_CONFIDENCE_BANDS else "low"


def _position_credibility(value: Any) -> dict[str, str]:
    """Normalize a reviewed 1--5 credibility map without neutral filling."""

    source = value if isinstance(value, Mapping) else {}
    result: dict[str, str] = {}
    for position in DOTA_POSITIONS:
        raw = source.get(position, source.get(int(position), "unknown"))
        normalized = str(raw).casefold()
        result[position] = (
            normalized if normalized in POSITION_CREDIBILITY_BANDS else "unknown"
        )
    return result


def _position_credibility_from_roles(roles: Sequence[str]) -> dict[str, str]:
    """Derive a low-confidence structural position hint from taxonomy roles.

    This helper is intentionally not used for reviewed semantic coverage.  It
    only keeps the historical taxonomy adapter useful to compatibility callers.
    The order in a reviewed taxonomy role tuple determines primary versus
    secondary; absent positions stay explicitly unsupported rather than
    becoming a neutral score.
    """

    role_positions = {
        "carry": "1",
        "mid": "2",
        "offlane": "3",
        "soft_support": "4",
        "roamer": "4",
        "hard_support": "5",
    }
    result = {position: "unsupported" for position in DOTA_POSITIONS}
    assigned: set[str] = set()
    for index, role in enumerate(roles):
        position = role_positions.get(str(role))
        if position is None or position in assigned:
            continue
        result[position] = "primary" if index == 0 else "secondary"
        assigned.add(position)
    return result


def _evidence_refs(
    data: Mapping[str, Any],
    functions: Sequence[str],
    demands: Mapping[str, str],
    capabilities: Mapping[str, str],
) -> tuple[str, ...]:
    refs: list[str] = []
    for section in (functions, demands, capabilities):
        for key in section:
            value = data.get("capabilities", {}).get(key) if isinstance(data.get("capabilities"), Mapping) else None
            if value is None:
                value = data.get("demands", {}).get(key) if isinstance(data.get("demands"), Mapping) else None
            if isinstance(value, Mapping):
                derived = value.get("derived_from", value.get("evidence_refs", []))
                if isinstance(derived, Sequence) and not isinstance(derived, (str, bytes)):
                    refs.extend(str(item) for item in derived)
    editorial = data.get("editorial", {})
    if isinstance(editorial, Mapping):
        for field_name in ("strengths", "weaknesses", "teamfight_jobs"):
            values = editorial.get(field_name, [])
            if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
                for value in values:
                    if isinstance(value, Mapping):
                        evidence = value.get("evidence_refs", [])
                        if isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
                            refs.extend(str(item) for item in evidence)
    return tuple(dict.fromkeys(refs))


def _display_job(key: str) -> str:
    from app.behavior.display_bands import job_display_label

    return job_display_label(key)


__all__ = [
    "HeroKnowledgeProvider",
    "HERO_KNOWLEDGE_SCHEMA_VERSION",
    "HERO_SEMANTICS_VERSION",
    "DOTA_POSITIONS",
    "POSITION_CREDIBILITY_BANDS",
    "FUNCTIONAL_JOBS",
    "HERO_DEMAND_FAMILIES",
    "DEMAND_GLOSSARY",
    "JOB_GLOSSARY",
    "COVERAGE_FAMILIES",
    "ROLE_RELEVANT_FAMILIES",
    "SEMANTIC_BANDS",
    "canonical_function_key",
    "demand_definition",
    "family_for_function",
    "job_definition",
    "role_relevant_families",
    "NormalizedHeroKnowledge",
    "TaxonomyHeroKnowledgeProvider",
    "HeroKnowledgeRecord",
    "HeroKnowledgeRepository",
    "SnapshotHeroKnowledgeProvider",
    "FullRosterHeroKnowledgeProvider",
    "normalized_hero_knowledge",
]
