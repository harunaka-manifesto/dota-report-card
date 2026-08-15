from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MetricObservation:
    player_value: float | None
    cohort_value: float | None
    unit: str
    effect: float | None
    interval: tuple[float, float] | None
    numerator: float | None
    denominator: int
    situation_count: int
    relevant_matches: int
    parsed_matches: int
    source_match_ids: tuple[int, ...]
    direction: str | None
    evidence_facts: tuple[str, ...]
    confounders: tuple[str, ...]
    action_behavior: str
    measurable_target: str
    practice_window: str = "next 20 matches"


@dataclass(frozen=True, slots=True)
class EvidenceObject:
    insight_id: str
    concept_id: str
    categories: tuple[str, ...]
    report_scope: str
    player: dict[str, Any]
    cohort: dict[str, Any] | None
    effect: dict[str, Any]
    interval: dict[str, Any] | None
    unit: str
    denominators: dict[str, int]
    parse_coverage: dict[str, Any]
    role_certainty: dict[str, Any]
    selected_cohort: dict[str, Any] | None
    evidence_statements: tuple[str, ...]
    confidence: str
    material_confounders: tuple[str, ...]
    action: dict[str, Any]
    versions: dict[str, str]
    source_match_ids: tuple[int, ...]
    provenance: dict[str, Any]
    publication_status: str
    publication_reason: str | None
    ivs: float
    definition_version: str
    statement_template_id: str
    action_template_id: str
    investigation: dict[str, Any] | None = None

    @property
    def published(self) -> bool:
        return self.publication_status == "published"

    def as_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "concept_id": self.concept_id,
            "categories": list(self.categories),
            "report_scope": self.report_scope,
            "player": dict(self.player),
            "cohort": dict(self.cohort) if self.cohort else None,
            "effect": dict(self.effect),
            "interval": dict(self.interval) if self.interval else None,
            "unit": self.unit,
            "denominators": dict(self.denominators),
            "parse_coverage": dict(self.parse_coverage),
            "role_certainty": dict(self.role_certainty),
            "selected_cohort": dict(self.selected_cohort) if self.selected_cohort else None,
            "evidence_statements": list(self.evidence_statements),
            "confidence": self.confidence,
            "material_confounders": list(self.material_confounders),
            "action": dict(self.action),
            "versions": dict(self.versions),
            "source_match_ids": list(self.source_match_ids),
            "provenance": dict(self.provenance),
            "publication_status": self.publication_status,
            "publication_reason": self.publication_reason,
            "ivs": round(self.ivs, 6),
            "definition_version": self.definition_version,
            "statement_template_id": self.statement_template_id,
            "action_template_id": self.action_template_id,
            "investigation": dict(self.investigation) if self.investigation else None,
        }
