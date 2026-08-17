"""Immutable domain contracts for the layered behavioral model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from app.behavior.evidence import BehaviorEvidence
from app.behavior.tiers import DataCapability, EvidenceTier, ModelStatus, ProductTier

Confidence = Literal["low", "moderate", "high", "unavailable"]
ElementStatus = Literal["available", "limited", "unavailable"]
PatternStatus = Literal["qualified", "suppressed", "unavailable"]
PatternKind = Literal["identity", "contradiction", "edge", "leak", "trajectory", "style"]


@dataclass(frozen=True, slots=True)
class ElementDefinition:
    key: str
    label: str
    dimension_key: str
    description: str
    user_question: str
    why_it_exists: str
    product_tier: ProductTier
    minimum_evidence_tier: EvidenceTier
    required_capabilities: tuple[DataCapability, ...]
    scorer_key: str
    minimum_sample: int
    minimum_coverage: float
    axis_left: str | None
    axis_right: str | None
    normalization_basis: str
    confounders: tuple[str, ...]
    copy_guardrails: tuple[str, ...]
    version: str
    status: ModelStatus = "active"


@dataclass(frozen=True, slots=True)
class ElementResult:
    key: str
    label: str
    dimension_key: str
    status: ElementStatus
    score: float | None
    centered_score: float | None
    confidence: Confidence
    confidence_score: float
    sample_size: int
    effective_sample_size: float
    coverage: float
    stability: float
    quality: float
    raw_metrics: Mapping[str, float | int | str | bool | None] = field(default_factory=dict)
    evidence: tuple[BehaviorEvidence, ...] = ()
    confounders: tuple[str, ...] = ()
    missing_reasons: tuple[str, ...] = ()
    methodology_version: str = "element-1.0.0"
    axis_left: str | None = None
    axis_right: str | None = None
    source_match_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("confidence_score", self.confidence_score),
            ("coverage", self.coverage),
            ("stability", self.stability),
            ("quality", self.quality),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]: {self.key}")
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Element score must be within [0, 1]: {self.key}")
        if self.centered_score is not None and not -1.0 <= self.centered_score <= 1.0:
            raise ValueError(f"Centered score must be within [-1, 1]: {self.key}")

    def as_dict(self, *, public: bool = True) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "dimension_key": self.dimension_key,
            "status": self.status,
            "score": round(self.score, 6) if self.score is not None else None,
            "centered_score": round(self.centered_score, 6) if self.centered_score is not None else None,
            "axis": {"left": self.axis_left, "right": self.axis_right},
            "confidence": self.confidence,
            "confidence_score": round(self.confidence_score, 6),
            "sample_size": self.sample_size,
            "effective_sample_size": round(self.effective_sample_size, 6),
            "coverage": round(self.coverage, 6),
            "raw_metrics": dict(self.raw_metrics),
            "receipts": [
                item.as_public_dict() if public else item.as_dict() for item in self.evidence
            ],
            "confounders": list(self.confounders),
            "missing_reasons": list(self.missing_reasons),
            "methodology_version": self.methodology_version,
            **({"source_match_ids": list(self.source_match_ids)} if not public else {}),
        }


@dataclass(frozen=True, slots=True)
class PatternDefinition:
    key: str
    label: str
    description: str
    kind: PatternKind
    dimension_keys: tuple[str, ...]
    required_elements: tuple[str, ...]
    optional_elements: tuple[str, ...]
    minimum_element_confidence: float
    evaluator_key: str
    product_tier: ProductTier
    minimum_evidence_tier: EvidenceTier
    why_it_matters: str
    copy_guardrails: tuple[str, ...]
    version: str
    status: ModelStatus = "active"
    diagnostic_questions: tuple[str, ...] = ()
    required_deep_elements: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PatternResult:
    key: str
    label: str
    kind: PatternKind
    status: PatternStatus
    direction: str | None
    strength: float
    confidence: Confidence
    confidence_score: float
    element_keys: tuple[str, ...]
    evidence: tuple[BehaviorEvidence, ...] = ()
    effect_metrics: Mapping[str, float | int | str | bool | None] = field(default_factory=dict)
    confounders: tuple[str, ...] = ()
    suppression_reasons: tuple[str, ...] = ()
    methodology_version: str = "pattern-1.0.0"
    diagnostic_questions: tuple[str, ...] = ()
    required_deep_elements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"Pattern strength must be within [0, 1]: {self.key}")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"Pattern confidence must be within [0, 1]: {self.key}")

    def as_dict(self, *, public: bool = True) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "status": self.status,
            "direction": self.direction,
            "strength": round(self.strength, 6),
            "confidence": self.confidence,
            "confidence_score": round(self.confidence_score, 6),
            "element_keys": list(self.element_keys),
            "receipts": [
                item.as_public_dict() if public else item.as_dict() for item in self.evidence
            ],
            "effect_metrics": dict(self.effect_metrics),
            "confounders": list(self.confounders),
            "suppression_reasons": list(self.suppression_reasons),
            "methodology_version": self.methodology_version,
            **(
                {
                    "diagnostic_questions": list(self.diagnostic_questions),
                    "required_deep_elements": list(self.required_deep_elements),
                }
                if not public
                else {}
            ),
        }


@dataclass(frozen=True, slots=True)
class ArchetypePrototype:
    key: str
    label: str
    identity_statement: str
    expected: Mapping[str, float]
    weights: Mapping[str, float]
    required_elements: tuple[str, ...]
    optional_patterns: tuple[str, ...] = ()
    version: str = "archetype-1.0.0"


@dataclass(frozen=True, slots=True)
class ArchetypeGroupDefinition:
    key: str
    label: str
    description: str
    product_tier: ProductTier
    required_elements: tuple[str, ...]
    optional_elements: tuple[str, ...]
    optional_patterns: tuple[str, ...]
    minimum_reliable_elements: int
    minimum_confidence_score: float
    prototypes: tuple[ArchetypePrototype, ...]
    version: str
    status: ModelStatus = "active"


@dataclass(frozen=True, slots=True)
class ContextArchetypeResult:
    group_key: str
    group_label: str
    key: str
    label: str
    fit: float
    confidence: Confidence
    runner_up: Mapping[str, Any] | None
    descriptors: tuple[Mapping[str, Any], ...]
    contributing_elements: tuple[Mapping[str, Any], ...]
    contributing_patterns: tuple[str, ...]
    explanation_evidence: tuple[str, ...]
    classifier_version: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "group_key": self.group_key,
            "group_label": self.group_label,
            "key": self.key,
            "label": self.label,
            "fit": round(self.fit, 6),
            "confidence": self.confidence,
            "runner_up": dict(self.runner_up) if self.runner_up else None,
            "descriptors": [dict(item) for item in self.descriptors],
            "contributing_element_keys": [
                str(item.get("key")) for item in self.contributing_elements
            ],
            "contributing_elements": [dict(item) for item in self.contributing_elements],
            "contributing_pattern_keys": list(self.contributing_patterns),
            "explanation_evidence": list(self.explanation_evidence),
            "classifier_version": self.classifier_version,
        }


@dataclass(frozen=True, slots=True)
class DimensionSummary:
    key: str
    label: str
    element_keys: tuple[str, ...]
    qualified_pattern_keys: tuple[str, ...]
    available_elements: int
    total_free_elements: int
    confidence: Confidence

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "element_keys": list(self.element_keys),
            "qualified_pattern_keys": list(self.qualified_pattern_keys),
            "available_elements": self.available_elements,
            "total_free_elements": self.total_free_elements,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class BehaviorQualitySummary:
    overall_confidence: Confidence
    available_elements: int
    limited_elements: int
    unavailable_elements: int
    qualified_patterns: int
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "overall_confidence": self.overall_confidence,
            "available_elements": self.available_elements,
            "limited_elements": self.limited_elements,
            "unavailable_elements": self.unavailable_elements,
            "qualified_patterns": self.qualified_patterns,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class BehaviorVersionMap:
    behavior_model: str
    dimension_registry: str
    element_registry: str
    pattern_registry: str
    archetype_registry: str
    finding_registry: str
    finding_ranking: str
    story: str
    copy: str

    def as_dict(self) -> dict[str, str]:
        return {
            "behavior_model": self.behavior_model,
            "dimension_registry": self.dimension_registry,
            "element_registry": self.element_registry,
            "pattern_registry": self.pattern_registry,
            "archetype_registry": self.archetype_registry,
            "finding_registry": self.finding_registry,
            "finding_ranking": self.finding_ranking,
            "story": self.story,
            "copy": self.copy,
        }


@dataclass(frozen=True, slots=True)
class BehaviorAnalysisResult:
    elements: tuple[ElementResult, ...]
    patterns: tuple[PatternResult, ...]
    archetypes: tuple[ContextArchetypeResult, ...]
    dimensions: tuple[DimensionSummary, ...]
    quality: BehaviorQualitySummary
    versions: BehaviorVersionMap

    @property
    def element_map(self) -> dict[str, ElementResult]:
        return {item.key: item for item in self.elements}

    @property
    def pattern_map(self) -> dict[str, PatternResult]:
        return {item.key: item for item in self.patterns}

    @property
    def archetype_map(self) -> dict[str, ContextArchetypeResult]:
        return {item.group_key: item for item in self.archetypes}

    def as_dict(self, *, public: bool = True) -> dict[str, Any]:
        return {
            "elements": [item.as_dict(public=public) for item in self.elements],
            "patterns": [item.as_dict(public=public) for item in self.patterns],
            "archetypes": [item.as_dict() for item in self.archetypes],
            "dimensions": [item.as_dict() for item in self.dimensions],
            "quality": self.quality.as_dict(),
            "versions": self.versions.as_dict(),
        }
