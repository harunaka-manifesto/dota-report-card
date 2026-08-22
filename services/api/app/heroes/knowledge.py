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
HERO_SEMANTICS_VERSION = "hero-semantics-pilot-v1"

# These vocabularies are intentionally small.  They are the product-facing
# contract; source adapters may emit richer evidence, but story code only sees
# these stable semantic keys.
FUNCTIONAL_JOBS = (
    "initiation",
    "counter_initiation",
    "catch",
    "frontline",
    "teamfight_control",
    "save",
    "sustain",
    "displacement",
    "repositioning",
    "mobility",
    "pickoff",
    "burst",
    "sustained_damage",
    "wave_clear",
    "push",
    "global_presence",
    "scaling",
    "vision",
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
SEMANTIC_BANDS = frozenset({"low", "medium", "high", "unknown"})
REVIEW_STATUSES = frozenset({"unreviewed", "draft", "reviewed", "approved", "stale"})
EMPIRICAL_SUPPORT_BANDS = frozenset({"high", "medium", "low", "unknown"})
SEMANTIC_CONFIDENCE_BANDS = frozenset({"high", "medium", "low"})


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


def normalized_hero_knowledge(entry: HeroTaxonomyEntry, *, version: str) -> NormalizedHeroKnowledge:
    # Import lazily because app.behavior.presentation imports this module to
    # type its provider seam; importing the display helper at module import
    # time would create a behavior ↔ hero circular import.
    from app.behavior.display_bands import job_display_label

    active = tuple(
        _canonical_function_key(key)
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
    )


def _function_keys(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    result: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            item = item.get("semantic_key", item.get("characteristic", item.get("key")))
        if item is not None:
            result.append(_canonical_function_key(str(item)))
    return tuple(result)


def _canonical_function_key(value: str) -> str:
    aliases = {
        "teamfight": "teamfight_control",
        "global_pressure": "global_presence",
        "damage": "sustained_damage",
    }
    return aliases.get(value, value)


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
        result[str(key)] = normalized if normalized in SEMANTIC_BANDS else "unknown"
    return {key: value for key, value in result.items() if key in HERO_DEMAND_FAMILIES or key in FUNCTIONAL_JOBS}


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
    "FUNCTIONAL_JOBS",
    "HERO_DEMAND_FAMILIES",
    "SEMANTIC_BANDS",
    "NormalizedHeroKnowledge",
    "TaxonomyHeroKnowledgeProvider",
    "HeroKnowledgeRecord",
    "HeroKnowledgeRepository",
    "SnapshotHeroKnowledgeProvider",
    "normalized_hero_knowledge",
]
