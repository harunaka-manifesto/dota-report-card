"""Immutable contracts for the summary-only Elements → Patterns model."""

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
PatternTier = Literal["A", "B"]
StoryEligibility = Literal["eligible", "blocked"]
ActionStatus = Literal["available", "limited", "unavailable"]
ActionDirection = Literal["deepen", "stretch"]


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
    zone_labels: tuple[str, ...] = ()


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
    blocking_confounders: tuple[str, ...] = ()
    missing_reasons: tuple[str, ...] = ()
    methodology_version: str = "element-4.0.0"
    axis_left: str | None = None
    axis_right: str | None = None
    source_match_ids: tuple[int, ...] = ()
    zone: str | None = None

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
            "zone": self.zone,
            "confidence": self.confidence,
            "confidence_score": round(self.confidence_score, 6),
            "sample_size": self.sample_size,
            "effective_sample_size": round(self.effective_sample_size, 6),
            "coverage": round(self.coverage, 6),
            "receipts": [
                item.as_public_dict() if public else item.as_dict() for item in self.evidence
            ],
            "confounders": list(self.confounders),
            "blocking_confounders": list(self.blocking_confounders),
            "missing_reasons": list(self.missing_reasons),
            "methodology_version": self.methodology_version,
            **({"source_match_ids": list(self.source_match_ids)} if not public else {}),
        }


@dataclass(frozen=True, slots=True)
class ElementHighlight:
    """A deterministic story slot selected from the full Element result set."""

    element_key: str
    rank: int
    display_reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "element_key": self.element_key,
            "rank": self.rank,
            "display_reason": self.display_reason,
        }


@dataclass(frozen=True, slots=True)
class PatternDefinition:
    key: str
    label: str
    description: str
    kind: PatternKind
    dimension_keys: tuple[str, ...]
    required_elements: tuple[str, ...]
    modifier_elements: tuple[str, ...]
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
    family: str = "general"
    tier: PatternTier = "B"
    # Each clause is an AND of canonical Element-zone memberships. Multiple
    # clauses are OR-ed. Keeping the reviewed categorical contract beside the
    # registry prevents the evaluator from growing a second numeric gate.
    zone_clauses: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...] = ()

    @property
    def optional_elements(self) -> tuple[str, ...]:
        """Compatibility name for callers that still use the old vocabulary."""

        return self.modifier_elements


@dataclass(frozen=True, slots=True)
class PatternHeroRecommendation:
    """One explainable, taxonomy-backed P01 hero recommendation."""

    hero_id: int
    hero_name: str
    direction: ActionDirection
    anchor_traits: tuple[str, ...]
    added_traits: tuple[str, ...]
    role_fit: tuple[str, ...]
    similarity_score: float
    novelty_score: float
    confidence_score: float
    why_it_fits: str
    what_stays_familiar: str
    what_changes: str
    provenance_versions: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "direction": self.direction,
            "anchor_traits": list(self.anchor_traits),
            "added_traits": list(self.added_traits),
            "role_fit": list(self.role_fit),
            "similarity_score": round(self.similarity_score, 6),
            "novelty_score": round(self.novelty_score, 6),
            "confidence_score": round(self.confidence_score, 6),
            "why_it_fits": self.why_it_fits,
            "what_stays_familiar": self.what_stays_familiar,
            "what_changes": self.what_changes,
            "provenance_versions": dict(self.provenance_versions),
        }


@dataclass(frozen=True, slots=True)
class SamePlaybookAction:
    action_type: Literal["same_playbook"]
    status: ActionStatus
    dominant_traits: tuple[str, ...]
    underrepresented_traits: tuple[str, ...]
    deepen: tuple[PatternHeroRecommendation, ...]
    stretch: tuple[PatternHeroRecommendation, ...]
    confidence_score: float
    limitations: tuple[str, ...] = ()
    provenance_versions: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "status": self.status,
            "dominant_traits": list(self.dominant_traits),
            "underrepresented_traits": list(self.underrepresented_traits),
            "deepen": [item.as_dict() for item in self.deepen],
            "stretch": [item.as_dict() for item in self.stretch],
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "provenance_versions": dict(self.provenance_versions),
        }


@dataclass(frozen=True, slots=True)
class ComfortEdgeHeroReliability:
    hero_id: int
    hero_name: str
    reliability_rank: int
    reliability_score: float
    confidence_score: float
    matches: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "reliability_rank": self.reliability_rank,
            "reliability_score": round(self.reliability_score, 6),
            "confidence_score": round(self.confidence_score, 6),
            "matches": self.matches,
        }


@dataclass(frozen=True, slots=True)
class ComfortEdgeDevelopmentReason:
    hero_id: int
    hero_name: str
    reliability_rank: int
    reliability_score: float
    confidence_score: float
    reference_core_hero_ids: tuple[int, ...]
    reference_core_hero_names: tuple[str, ...]
    what_changes: tuple[str, ...]
    useful_situations: tuple[str, ...]
    teammate_examples: tuple[int, ...]
    teammate_example_names: tuple[str, ...]
    enemy_examples: tuple[int, ...]
    enemy_example_names: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    why_learn: str
    limitations: tuple[str, ...] = ()
    provenance_versions: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "reliability_rank": self.reliability_rank,
            "reliability_score": round(self.reliability_score, 6),
            "confidence_score": round(self.confidence_score, 6),
            "reference_core_hero_ids": list(self.reference_core_hero_ids),
            "reference_core_hero_names": list(self.reference_core_hero_names),
            "what_changes": list(self.what_changes),
            "useful_situations": list(self.useful_situations),
            "teammate_examples": list(self.teammate_examples),
            "teammate_example_names": list(self.teammate_example_names),
            "enemy_examples": list(self.enemy_examples),
            "enemy_example_names": list(self.enemy_example_names),
            "tradeoffs": list(self.tradeoffs),
            "why_learn": self.why_learn,
            "limitations": list(self.limitations),
            "provenance_versions": dict(self.provenance_versions),
        }


@dataclass(frozen=True, slots=True)
class ComfortEdgeAction:
    action_type: Literal["comfort_edge"]
    status: ActionStatus
    ranked_heroes: tuple[ComfortEdgeHeroReliability, ...]
    reference_core_hero_ids: tuple[int, ...]
    development: tuple[ComfortEdgeDevelopmentReason, ...]
    confidence_score: float
    limitations: tuple[str, ...] = ()
    provenance_versions: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "status": self.status,
            "ranked_heroes": [item.as_dict() for item in self.ranked_heroes],
            "reference_core_hero_ids": list(self.reference_core_hero_ids),
            "development": [item.as_dict() for item in self.development],
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "provenance_versions": dict(self.provenance_versions),
        }


PatternAction = SamePlaybookAction | ComfortEdgeAction


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
    blocking_confounders: tuple[str, ...] = ()
    suppression_reasons: tuple[str, ...] = ()
    methodology_version: str = "pattern-4.0.0"
    diagnostic_questions: tuple[str, ...] = ()
    required_deep_elements: tuple[str, ...] = ()
    modifier_element_keys: tuple[str, ...] = ()
    family: str = "general"
    tier: PatternTier = "B"
    relationship_strength: float = 0.0
    evidence_coverage: float = 0.0
    qualification_quality: float = 0.0
    story_eligibility: StoryEligibility = "eligible"
    story_blockers: tuple[str, ...] = ()
    action: PatternAction | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"Pattern strength must be within [0, 1]: {self.key}")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"Pattern confidence must be within [0, 1]: {self.key}")
        for name, value in (
            ("relationship_strength", self.relationship_strength),
            ("evidence_coverage", self.evidence_coverage),
            ("qualification_quality", self.qualification_quality),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]: {self.key}")

    def as_dict(self, *, public: bool = True) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "status": self.status,
            "direction": self.direction,
            "strength": round(self.strength, 6),
            "relationship_strength": round(self.relationship_strength, 6),
            "confidence": self.confidence,
            "confidence_score": round(self.confidence_score, 6),
            "evidence_coverage": round(self.evidence_coverage, 6),
            "qualification_quality": round(self.qualification_quality, 6),
            "element_keys": list(self.element_keys),
            "modifier_element_keys": list(self.modifier_element_keys),
            "family": self.family,
            "tier": self.tier,
            "receipts": [
                item.as_public_dict() if public else item.as_dict() for item in self.evidence
            ],
            "confounders": list(self.confounders),
            "blocking_confounders": list(self.blocking_confounders),
            "story_eligibility": self.story_eligibility,
            "story_blockers": list(self.story_blockers),
            "suppression_reasons": list(self.suppression_reasons),
            "methodology_version": self.methodology_version,
            "action": self.action.as_dict() if self.action is not None else None,
            **(
                {
                    "diagnostic_questions": list(self.diagnostic_questions),
                    "required_deep_elements": list(self.required_deep_elements),
                }
                if not public
                else {}
            ),
            **({"effect_metrics": dict(self.effect_metrics)} if not public else {}),
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

    def as_dict(self) -> dict[str, str]:
        return {
            "behavior_model": self.behavior_model,
            "dimension_registry": self.dimension_registry,
            "element_registry": self.element_registry,
            "pattern_registry": self.pattern_registry,
        }


@dataclass(frozen=True, slots=True)
class BehaviorAnalysisResult:
    elements: tuple[ElementResult, ...]
    patterns: tuple[PatternResult, ...]
    dimensions: tuple[DimensionSummary, ...]
    quality: BehaviorQualitySummary
    versions: BehaviorVersionMap

    @property
    def element_map(self) -> dict[str, ElementResult]:
        return {item.key: item for item in self.elements}

    @property
    def pattern_map(self) -> dict[str, PatternResult]:
        return {item.key: item for item in self.patterns}

    def as_dict(self, *, public: bool = True) -> dict[str, Any]:
        return {
            "elements": [item.as_dict(public=public) for item in self.elements],
            "patterns": [item.as_dict(public=public) for item in self.patterns],
            "dimensions": [item.as_dict() for item in self.dimensions],
            "quality": self.quality.as_dict(),
            "versions": self.versions.as_dict(),
        }
