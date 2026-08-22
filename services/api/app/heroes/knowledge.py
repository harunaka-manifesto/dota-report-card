"""Provider-neutral seam for normalized hero knowledge.

The report and recommendation layers consume this shape, not raw Valve,
OpenDota, or optional experimental source payloads. The checked-in taxonomy is
the current provider; a generated ingestion snapshot can implement the same
protocol without changing story code.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.heroes.taxonomy import HeroTaxonomy, HeroTaxonomyEntry

HERO_KNOWLEDGE_SCHEMA_VERSION = "hero-knowledge-schema-1.0.0"


@dataclass(frozen=True, slots=True)
class NormalizedHeroKnowledge:
    hero_id: int
    display_name: str
    roles: tuple[str, ...]
    functional_jobs: tuple[str, ...]
    provenance_versions: Mapping[str, str]


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

    jobs = tuple(
        job_display_label(key)
        for key, value in sorted(entry.traits.items())
        if value >= 0.60 and key not in {"complexity", "micro_intensity", "farm_dependency"}
    )
    return NormalizedHeroKnowledge(
        hero_id=entry.hero_id,
        display_name=entry.name,
        roles=entry.roles,
        functional_jobs=jobs,
        provenance_versions={
            "hero_knowledge": version,
            "hero_knowledge_schema": HERO_KNOWLEDGE_SCHEMA_VERSION,
        },
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

    def get(self, hero_id: int) -> HeroKnowledgeRecord | None:
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


__all__ = [
    "HeroKnowledgeProvider",
    "HERO_KNOWLEDGE_SCHEMA_VERSION",
    "NormalizedHeroKnowledge",
    "TaxonomyHeroKnowledgeProvider",
    "HeroKnowledgeRecord",
    "HeroKnowledgeRepository",
    "normalized_hero_knowledge",
]
