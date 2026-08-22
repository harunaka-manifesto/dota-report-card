"""Small, serialization-friendly schemas shared by source adapters."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from . import SCHEMA_VERSION


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_key(value: str) -> str:
    """Normalize a source hero label for alias matching."""

    return "".join(character for character in value.casefold() if character.isalnum())


@dataclass(frozen=True, slots=True)
class HeroIdentity:
    hero_id: int
    key: str
    internal_name: str
    display_name: str
    primary_attribute: str
    complexity: int | None
    portrait_ref: str | None
    available: bool
    aliases: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "key": self.key,
            "internal_name": self.internal_name,
            "display_name": self.display_name,
            "primary_attribute": self.primary_attribute,
            "complexity": self.complexity,
            "portrait_ref": self.portrait_ref,
            "available": self.available,
            "aliases": list(self.aliases),
        }


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    source: str
    source_url: str | None
    fetched_at: str
    raw_sha256: str | None = None
    parser_version: str | None = None
    source_window: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "source": self.source,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at,
            "raw_sha256": self.raw_sha256,
        }
        if self.parser_version is not None:
            value["parser_version"] = self.parser_version
        if self.source_window is not None:
            value["source_window"] = self.source_window
        if self.context:
            value["context"] = self.context
        return value


@dataclass(frozen=True, slots=True)
class HeroKnowledgeRecord:
    """In-memory shape of one normalized product-facing hero record."""

    identity: dict[str, Any]
    mechanics: dict[str, Any]
    functions: dict[str, Any]
    demands: dict[str, Any]
    capabilities: dict[str, Any]
    empirical: dict[str, Any]
    editorial: dict[str, Any]
    provenance: dict[str, Any]
    derived_characteristics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "mechanics": self.mechanics,
            "functions": self.functions,
            "demands": self.demands,
            "capabilities": self.capabilities,
            "empirical": self.empirical,
            "editorial": self.editorial,
            "derived_characteristics": self.derived_characteristics,
            "provenance": self.provenance,
        }


def empty_empirical_context() -> dict[str, Any]:
    """Return explicit unknowns without manufacturing neutral scores."""

    return {
        "bracket_performance": [],
        "duration_profile": [],
        "item_profile": [],
        "matchup_profile": [],
        "optional_valve_plus": {},
        "status": "unknown",
    }


def empty_knowledge_record(
    identity: dict[str, Any], source_file: str | None = None
) -> dict[str, Any]:
    return HeroKnowledgeRecord(
        identity=identity,
        mechanics={"abilities": [], "facets": [], "talents": [], "base_stats": {}},
        functions={"primary": [], "secondary": []},
        demands={},
        capabilities={},
        empirical=empty_empirical_context(),
        editorial={
            "strengths": [],
            "weaknesses": [],
            "teamfight_jobs": [],
            "notes": [],
            "review_status": "unreviewed",
            "source_file": source_file,
        },
        provenance={
            "schema_version": SCHEMA_VERSION,
            "field_sources": {},
            "source_versions": {},
            "generated_at": None,
        },
    ).as_dict()
