"""Internal immutable models for the Free DNA finding system.

The models in this module deliberately keep private provenance separate from
the public report projection.  A finding can therefore be replayed and tested
with match references without ever serializing those references to the web.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

EvidenceFamily = Literal[
    "dimension",
    "dna_feature",
    "summary_pattern",
    "hero_identity",
    "hero_pattern",
    "session",
    "derived_summary",
]

FindingKind = Literal[
    "thesis",
    "strength",
    "contradiction",
    "edge",
    "leak",
    "trajectory",
    "identity",
]

FindingConfidence = Literal["limited", "moderate", "high"]
SignalValue = float | int | str | bool | None


@dataclass(frozen=True, slots=True)
class FindingSignal:
    """One normalized observation that a finding rule can consume."""

    key: str
    family: EvidenceFamily
    value: SignalValue
    unit: str
    direction: str | None
    confidence_score: float
    sample_size: int
    coverage: float
    source_match_ids: tuple[int, ...] = ()
    public_receipt: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"Signal confidence must be within [0, 1]: {self.key}")
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError(f"Signal coverage must be within [0, 1]: {self.key}")
        if self.sample_size < 0:
            raise ValueError(f"Signal sample size cannot be negative: {self.key}")

    @property
    def confidence(self) -> FindingConfidence:
        if self.confidence_score >= 0.75:
            return "high"
        if self.confidence_score >= 0.60:
            return "moderate"
        return "limited"

    @property
    def receipt_key(self) -> str:
        value = self.metadata.get("receipt_key")
        return str(value or self.key.replace(".", "_"))

    @property
    def receipt_label(self) -> str:
        value = self.metadata.get("receipt_label")
        return str(value or self.key.replace(".", " ").replace("_", " ").title())

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "family": self.family,
            "value": self.value,
            "unit": self.unit,
            "direction": self.direction,
            "confidence_score": round(self.confidence_score, 6),
            "sample_size": self.sample_size,
            "coverage": round(self.coverage, 6),
            "source_match_ids": list(self.source_match_ids),
            "public_receipt": self.public_receipt,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class FindingDefinition:
    """Static metadata for a finite finding rule."""

    key: str
    kind: FindingKind
    required_signals: tuple[str, ...]
    optional_signals: tuple[str, ...]
    minimum_families: int
    minimum_confidence: float
    minimum_samples: Mapping[str, int]
    contradiction_bonus: float
    surprise_prior: float
    specificity_prior: float
    consequence_prior: float
    actionability_prior: float
    shareability_prior: float
    headline_template_key: str
    body_template_key: str
    interpretation_template_key: str
    experiment_key: str | None
    concept_tags: frozenset[str] = frozenset()
    related_dimensions: tuple[str, ...] = ()
    version: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class FindingExperiment:
    key: str
    title: str
    instruction: str
    hypothesis: str
    measurement: str
    window_matches: int | None
    window_sessions: int | None
    related_finding_key: str

    @property
    def window(self) -> str:
        if self.window_matches is not None:
            return f"{self.window_matches} matches"
        if self.window_sessions is not None:
            return f"{self.window_sessions} sessions"
        return "A small, deliberate sample"

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "instruction": self.instruction,
            "hypothesis": self.hypothesis,
            "measurement": self.measurement,
            "window_matches": self.window_matches,
            "window_sessions": self.window_sessions,
            "related_finding_key": self.related_finding_key,
        }


@dataclass(frozen=True, slots=True)
class FindingCandidate:
    key: str
    kind: FindingKind
    headline: str
    body: str
    interpretation: str
    evidence: tuple[FindingSignal, ...]
    confidence_score: float
    surprise_score: float
    specificity_score: float
    consequence_score: float
    actionability_score: float
    shareability_score: float
    priority_score: float
    experiment: FindingExperiment | None
    limitations: tuple[str, ...]
    publication_status: Literal["published", "suppressed"]
    suppression_reason: str | None
    definition_version: str
    concept_tags: frozenset[str] = frozenset()
    related_dimensions: tuple[str, ...] = ()
    related_heroes: tuple[int, ...] = ()
    share_copy: str | None = None

    @property
    def confidence(self) -> FindingConfidence:
        if self.confidence_score >= 0.75:
            return "high"
        if self.confidence_score >= 0.60:
            return "moderate"
        return "limited"

    @property
    def evidence_families(self) -> frozenset[EvidenceFamily]:
        return frozenset(item.family for item in self.evidence)

    @property
    def effective_sample_size(self) -> int:
        return min((item.sample_size for item in self.evidence), default=0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "kind": self.kind,
            "headline": self.headline,
            "body": self.body,
            "interpretation": self.interpretation,
            "evidence": [item.as_dict() for item in self.evidence],
            "confidence_score": round(self.confidence_score, 6),
            "surprise_score": round(self.surprise_score, 6),
            "specificity_score": round(self.specificity_score, 6),
            "consequence_score": round(self.consequence_score, 6),
            "actionability_score": round(self.actionability_score, 6),
            "shareability_score": round(self.shareability_score, 6),
            "priority_score": round(self.priority_score, 6),
            "experiment": self.experiment.as_dict() if self.experiment else None,
            "limitations": list(self.limitations),
            "publication_status": self.publication_status,
            "suppression_reason": self.suppression_reason,
            "definition_version": self.definition_version,
            "concept_tags": sorted(self.concept_tags),
            "related_dimensions": list(self.related_dimensions),
            "related_heroes": list(self.related_heroes),
            "share_copy": self.share_copy,
        }


@dataclass(frozen=True, slots=True)
class StorySelection:
    thesis_key: str | None
    strength_key: str | None
    contradiction_key: str | None
    edge_key: str | None
    leak_key: str | None
    experiment_key: str | None
    ordered_finding_keys: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "thesis_key": self.thesis_key,
            "strength_key": self.strength_key,
            "contradiction_key": self.contradiction_key,
            "edge_key": self.edge_key,
            "leak_key": self.leak_key,
            "experiment_key": self.experiment_key,
            "ordered_finding_keys": list(self.ordered_finding_keys),
        }
