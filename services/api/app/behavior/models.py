"""Immutable contracts for the summary-only Elements → Patterns model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from app.behavior.context_baseline import CONTEXT_BASELINE_VERSION
from app.behavior.evidence import BehaviorEvidence
from app.behavior.tiers import DataCapability, EvidenceTier, ModelStatus, ProductTier
from app.hero_portfolio.version import PATTERN_ACTIONS_VERSION
from app.heroes.recommendations import HeroRecommendationRationale

Confidence = Literal["low", "moderate", "high", "unavailable"]
ElementStatus = Literal["available", "limited", "unavailable"]
PatternStatus = Literal["qualified", "suppressed", "unavailable"]
PatternKind = Literal["identity", "contradiction", "edge", "leak", "trajectory", "style"]
PatternTier = Literal["A", "B"]
StoryEligibility = Literal["eligible", "blocked"]
ActionStatus = Literal["available", "limited", "unavailable"]
PatternActionResolutionStatus = Literal["resolved", "fallback", "unresolved", "not_applicable"]
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
    methodology_version: str = "element-5.1.0"
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
class PatternActionEvidence:
    """The additive evidence receipt shared by every Pattern action.

    Action-specific payloads remain intentionally different.  This envelope
    gives callers one stable place to read resolution semantics and the core
    evidence dimensions without erasing those payloads.
    """

    status: PatternActionResolutionStatus = "unresolved"
    sample_size: int = 0
    effective_sample_size: float = 0.0
    coverage: float = 0.0
    confidence_score: float = 0.0
    independent_group_count: int | None = None
    evidence_keys: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    provenance_versions: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sample_size < 0:
            raise ValueError("Pattern action sample_size must be non-negative")
        if self.effective_sample_size < 0:
            raise ValueError("Pattern action effective_sample_size must be non-negative")
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError("Pattern action coverage must be within [0, 1]")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Pattern action confidence_score must be within [0, 1]")
        if self.independent_group_count is not None and self.independent_group_count < 0:
            raise ValueError("Pattern action independent_group_count must be non-negative")

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "sample_size": self.sample_size,
            "effective_sample_size": round(self.effective_sample_size, 6),
            "coverage": round(self.coverage, 6),
            "confidence_score": round(self.confidence_score, 6),
            "independent_group_count": self.independent_group_count,
            "evidence_keys": list(self.evidence_keys),
            "limitations": list(self.limitations),
            "provenance_versions": dict(self.provenance_versions),
        }


def _action_resolution_status(action: Any) -> PatternActionResolutionStatus:
    raw_status = getattr(action, "status", None)
    if raw_status in {"resolved", "fallback", "unresolved", "not_applicable"}:
        return raw_status
    if raw_status in {
        "available",
        "direct_signal",
        "peak_window",
        "no_obvious_gap",
        "coverage_plus_recommendation",
        "coverage_plus_alternatives",
    }:
        return "resolved"
    if raw_status in {
        "limited",
        "capability_hypothesis",
        "deep_candidate",
        "distributed_flexibility",
        "coverage_only",
    }:
        return "fallback"
    if getattr(action, "shape", None) == "unresolved":
        return "unresolved"
    if getattr(action, "shape", None) in {"job_shaped", "hero_specific", "cross_context"}:
        return "resolved"
    if getattr(action, "strongest_context", None) is not None:
        return "fallback" if getattr(action, "fallback_level", "hero") != "hero" else "resolved"
    if getattr(action, "strongest_contexts", ()):
        return "resolved"
    return "unresolved"


def _default_action_evidence(action: Any) -> PatternActionEvidence:
    """Build a conservative envelope for legacy action constructors.

    Builders may provide a more precise envelope, but the default keeps all
    existing constructor call sites and historical payloads compatible.
    """

    action_type = getattr(action, "action_type", "pattern_action")
    contexts = tuple(
        item
        for name in ("comparison_contexts", "comparison_rows", "strongest_contexts")
        for item in getattr(action, name, ())
    )
    strongest = getattr(action, "strongest_context", None)
    if strongest is not None:
        contexts = (strongest, *contexts)
    differences = getattr(action, "summary_differences", ())
    samples = [
        int(getattr(action, "total_games", 0) or 0),
        int(getattr(action, "sample_size", 0) or 0),
        sum(int(getattr(item, "sample_size", 0) or 0) for item in contexts),
        sum(int(getattr(item, "matches", 0) or 0) for item in getattr(action, "ranked_heroes", ())),
        sum(int(getattr(item, "sample_size", 0) or 0) for item in getattr(action, "curve", ())),
    ]
    sample_size = max(samples, default=0)
    if differences:
        coverage = min(float(getattr(item, "coverage", 0.0)) for item in differences)
    else:
        coverage = 1.0 if sample_size else 0.0
    confidence = float(getattr(action, "confidence_score", 0.0) or 0.0)
    independent = getattr(action, "independent_session_count", None)
    if independent is None and contexts:
        independent = max(
            (int(getattr(item, "session_count", 0) or 0) for item in contexts),
            default=0,
        )
    effective = float(getattr(action, "effective_sample_size", sample_size) or sample_size)
    provenance_versions = dict(getattr(action, "provenance_versions", {}) or {})
    provenance_versions.setdefault("pattern_actions", PATTERN_ACTIONS_VERSION)
    if contexts or action_type in {"bounceback", "performance_slide", "session_fade", "session_rise"}:
        provenance_versions.setdefault("context_baseline", CONTEXT_BASELINE_VERSION)
    return PatternActionEvidence(
        status=_action_resolution_status(action),
        sample_size=sample_size,
        effective_sample_size=effective,
        coverage=max(0.0, min(1.0, coverage)),
        confidence_score=max(0.0, min(1.0, confidence)),
        independent_group_count=independent,
        evidence_keys=(f"pattern_action.{action_type}",),
        limitations=tuple(getattr(action, "limitations", ()) or ()),
        provenance_versions=provenance_versions,
    )


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
    semantic_rationale: HeroRecommendationRationale | None = None

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
            "semantic_rationale": self.semantic_rationale.as_dict() if self.semantic_rationale else None,
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
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

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
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
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
    semantic_rationale: HeroRecommendationRationale | None = None

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
            "semantic_rationale": self.semantic_rationale.as_dict() if self.semantic_rationale else None,
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
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

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
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


@dataclass(frozen=True, slots=True)
class ObservedDifference:
    signal_key: str
    core_value: float | None
    off_pool_value: float | None
    effect_size: float | None
    confidence_score: float
    player_facing_claim: str
    coverage: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_key": self.signal_key,
            "core_value": self.core_value,
            "off_pool_value": self.off_pool_value,
            "effect_size": self.effect_size,
            "confidence_score": round(self.confidence_score, 6),
            "player_facing_claim": self.player_facing_claim,
            "coverage": round(self.coverage, 6),
        }


@dataclass(frozen=True, slots=True)
class CapabilityHypothesis:
    capability_key: str
    core_prevalence: float
    off_pool_prevalence: float
    separation_score: float
    confidence_score: float
    player_facing_hypothesis: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability_key": self.capability_key,
            "core_prevalence": round(self.core_prevalence, 6),
            "off_pool_prevalence": round(self.off_pool_prevalence, 6),
            "separation_score": round(self.separation_score, 6),
            "confidence_score": round(self.confidence_score, 6),
            "player_facing_hypothesis": self.player_facing_hypothesis,
        }


@dataclass(frozen=True, slots=True)
class PartialTransferDiagnostic:
    action_type: Literal["partial_transfer"]
    status: Literal["direct_signal", "capability_hypothesis", "unresolved", "deep_candidate"]
    summary_differences: tuple[ObservedDifference, ...]
    capability_hypotheses: tuple[CapabilityHypothesis, ...]
    strongest_supported_lead: str | None
    core_hero_ids: tuple[int, ...]
    off_pool_hero_ids: tuple[int, ...]
    confidence_score: float
    limitations: tuple[str, ...]
    deep_analysis_eligible: bool
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "status": self.status,
            "summary_differences": [item.as_dict() for item in self.summary_differences],
            "capability_hypotheses": [item.as_dict() for item in self.capability_hypotheses],
            "strongest_supported_lead": self.strongest_supported_lead,
            "core_hero_ids": list(self.core_hero_ids),
            "off_pool_hero_ids": list(self.off_pool_hero_ids),
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "deep_analysis_eligible": self.deep_analysis_eligible,
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


@dataclass(frozen=True, slots=True)
class HeroJobMap:
    hero_id: int
    hero_name: str
    primary_jobs: tuple[str, ...]
    expression_summary: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "primary_jobs": list(self.primary_jobs),
            "expression_summary": self.expression_summary,
        }


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    strongly_covered: tuple[str, ...]
    single_point_coverage: tuple[str, ...]
    thin_coverage: tuple[str, ...]
    missing: tuple[str, ...]
    family_map: Mapping[str, str] = field(default_factory=dict)
    family_descriptions: Mapping[str, str] = field(default_factory=dict)
    primary_gap: str | None = None
    secondary_gaps: tuple[str, ...] = ()
    semantic_coverage: float | None = None
    role_adjusted_coverage: float | None = None
    pairwise_functional_overlap: float | None = None
    unique_contribution_count: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "strongly_covered": list(self.strongly_covered),
            "single_point_coverage": list(self.single_point_coverage),
            "thin_coverage": list(self.thin_coverage),
            "missing": list(self.missing),
            "family_map": dict(self.family_map),
            "family_descriptions": dict(self.family_descriptions),
            "primary_gap": self.primary_gap,
            "secondary_gaps": list(self.secondary_gaps),
            "semantic_coverage": self.semantic_coverage,
            "role_adjusted_coverage": self.role_adjusted_coverage,
            "pairwise_functional_overlap": self.pairwise_functional_overlap,
            "unique_contribution_count": self.unique_contribution_count,
        }


@dataclass(frozen=True, slots=True)
class HeroAdditionRecommendation:
    hero_id: int
    hero_name: str
    adds_jobs: tuple[str, ...]
    shared_anchors: tuple[str, ...]
    solves_gap: str
    player_facing_reason: str
    confidence_score: float
    semantic_rationale: HeroRecommendationRationale | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "adds_jobs": list(self.adds_jobs),
            "shared_anchors": list(self.shared_anchors),
            "solves_gap": self.solves_gap,
            "player_facing_reason": self.player_facing_reason,
            "confidence_score": round(self.confidence_score, 6),
            "semantic_rationale": self.semantic_rationale.as_dict() if self.semantic_rationale else None,
        }


@dataclass(frozen=True, slots=True)
class VersatileCoreAction:
    action_type: Literal["versatile_core"]
    status: Literal[
        "coverage_only",
        "coverage_plus_recommendation",
        "coverage_plus_alternatives",
        "no_obvious_gap",
    ]
    core_hero_ids: tuple[int, ...]
    hero_job_maps: tuple[HeroJobMap, ...]
    coverage_summary: CoverageSummary
    recommended_addition: HeroAdditionRecommendation | None
    alternative_additions: tuple[HeroAdditionRecommendation, ...]
    confidence_score: float
    limitations: tuple[str, ...]
    complementarity_qualified: bool = True
    semantic_confidence: float | None = None
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "status": self.status,
            "core_hero_ids": list(self.core_hero_ids),
            "hero_job_maps": [item.as_dict() for item in self.hero_job_maps],
            "coverage_summary": self.coverage_summary.as_dict(),
            "recommended_addition": self.recommended_addition.as_dict() if self.recommended_addition else None,
            "alternative_additions": [item.as_dict() for item in self.alternative_additions],
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "complementarity_qualified": self.complementarity_qualified,
            "semantic_confidence": round(self.semantic_confidence, 6) if self.semantic_confidence is not None else None,
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


@dataclass(frozen=True, slots=True)
class ProvenFlexibilityAction:
    action_type: Literal["proven_flexibility"]
    status: Literal["peak_window", "distributed_flexibility"]
    window_start: date | None
    window_end: date | None
    total_games: int
    hero_ids: tuple[int, ...]
    hero_names: tuple[str, ...]
    hero_game_counts: tuple[tuple[int, int], ...]
    meaningful_hero_count: int
    functional_jobs: tuple[str, ...]
    functional_job_count: int
    repeated_hero_count: int
    longest_same_hero_streak: int | None
    secondary_proof: str | None
    flex_week_score: float | None
    activity_confidence: float
    distribution_quality: float | None
    confidence_score: float
    limitations: tuple[str, ...]
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "status": self.status,
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "total_games": self.total_games,
            "hero_ids": list(self.hero_ids),
            "hero_names": list(self.hero_names),
            "hero_game_counts": [list(item) for item in self.hero_game_counts],
            "meaningful_hero_count": self.meaningful_hero_count,
            "functional_jobs": list(self.functional_jobs),
            "functional_job_count": self.functional_job_count,
            "repeated_hero_count": self.repeated_hero_count,
            "longest_same_hero_streak": self.longest_same_hero_streak,
            "secondary_proof": self.secondary_proof,
            "flex_week_score": round(self.flex_week_score, 6) if self.flex_week_score is not None else None,
            "activity_confidence": round(self.activity_confidence, 6),
            "distribution_quality": round(self.distribution_quality, 6) if self.distribution_quality is not None else None,
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


@dataclass(frozen=True, slots=True)
class RecoveryContext:
    label: str
    hero_id: int | None
    function_family: str | None
    role_context: str | None
    performance_delta: float
    baseline_performance: float
    observed_performance: float
    sample_size: int
    session_count: int
    primary_jobs: tuple[str, ...]
    confidence_score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "hero_id": self.hero_id,
            "function_family": self.function_family,
            "role_context": self.role_context,
            "performance_delta": round(self.performance_delta, 6),
            "baseline_performance": round(self.baseline_performance, 6),
            "observed_performance": round(self.observed_performance, 6),
            "sample_size": self.sample_size,
            "session_count": self.session_count,
            "primary_jobs": list(self.primary_jobs),
            "confidence_score": round(self.confidence_score, 6),
        }


@dataclass(frozen=True, slots=True)
class BouncebackAction:
    action_type: Literal["bounceback"]
    strongest_context: RecoveryContext | None
    comparison_contexts: tuple[RecoveryContext, ...]
    fallback_level: Literal["hero", "function", "role", "overall"]
    confidence_score: float
    limitations: tuple[str, ...]
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "strongest_context": self.strongest_context.as_dict() if self.strongest_context else None,
            "comparison_contexts": [item.as_dict() for item in self.comparison_contexts],
            "fallback_level": self.fallback_level,
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


@dataclass(frozen=True, slots=True)
class PerformanceSlideAction:
    action_type: Literal["performance_slide"]
    strongest_context: RecoveryContext | None
    comparison_contexts: tuple[RecoveryContext, ...]
    fallback_level: Literal["hero", "function", "role", "overall"]
    confidence_score: float
    limitations: tuple[str, ...]
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "strongest_context": self.strongest_context.as_dict() if self.strongest_context else None,
            "comparison_contexts": [item.as_dict() for item in self.comparison_contexts],
            "fallback_level": self.fallback_level,
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


@dataclass(frozen=True, slots=True)
class PresenceContext:
    label: str
    hero_id: int | None
    function_family: str | None
    role_context: str | None
    involvement_level: float
    death_exposure_level: float
    sample_size: int
    confidence_score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "hero_id": self.hero_id,
            "function_family": self.function_family,
            "role_context": self.role_context,
            "involvement_level": round(self.involvement_level, 6),
            "death_exposure_level": round(self.death_exposure_level, 6),
            "sample_size": self.sample_size,
            "confidence_score": round(self.confidence_score, 6),
        }


@dataclass(frozen=True, slots=True)
class ControlledPresenceAction:
    action_type: Literal["controlled_presence"]
    strongest_context: PresenceContext | None
    comparison_rows: tuple[PresenceContext, ...]
    finishing_flavor: str | None
    fallback_level: Literal["hero", "function", "role", "overall"]
    confidence_score: float
    limitations: tuple[str, ...] = ()
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "strongest_context": self.strongest_context.as_dict() if self.strongest_context else None,
            "comparison_rows": [item.as_dict() for item in self.comparison_rows],
            "finishing_flavor": self.finishing_flavor,
            "fallback_level": self.fallback_level,
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


@dataclass(frozen=True, slots=True)
class PresenceTaxAction:
    action_type: Literal["presence_tax"]
    shape: Literal["job_shaped", "hero_specific", "cross_context", "unresolved"]
    strongest_contexts: tuple[PresenceContext, ...]
    comparison_contexts: tuple[PresenceContext, ...]
    deep_analysis_candidate: bool
    confidence_score: float
    limitations: tuple[str, ...] = ()
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "shape": self.shape,
            "strongest_contexts": [item.as_dict() for item in self.strongest_contexts],
            "comparison_contexts": [item.as_dict() for item in self.comparison_contexts],
            "deep_analysis_candidate": self.deep_analysis_candidate,
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


@dataclass(frozen=True, slots=True)
class SessionCurvePoint:
    bucket: str
    relative_delta: float
    sample_size: int
    effective_sample_size: float
    supported: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "bucket": self.bucket,
            "relative_delta": round(self.relative_delta, 6),
            "sample_size": self.sample_size,
            "effective_sample_size": round(self.effective_sample_size, 6),
            "supported": self.supported,
        }


@dataclass(frozen=True, slots=True)
class SessionCurveAction:
    action_type: Literal["session_fade", "session_rise"]
    status: PatternActionResolutionStatus
    direction: Literal["fade", "rise"]
    curve: tuple[SessionCurvePoint, ...]
    breakpoint_state: Literal["stable_breakpoint", "gradual", "unresolved"]
    breakpoint_bucket: str | None
    companion_signals: tuple[str, ...]
    independent_session_count: int
    confidence_score: float
    limitations: tuple[str, ...]
    evidence_summary: PatternActionEvidence | None = None

    def __post_init__(self) -> None:
        if self.evidence_summary is None:
            object.__setattr__(self, "evidence_summary", _default_action_evidence(self))

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "status": self.status,
            "direction": self.direction,
            "curve": [item.as_dict() for item in self.curve],
            "breakpoint_state": self.breakpoint_state,
            "breakpoint_bucket": self.breakpoint_bucket,
            "companion_signals": list(self.companion_signals),
            "independent_session_count": self.independent_session_count,
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
            "evidence_summary": self.evidence_summary.as_dict() if self.evidence_summary else None,
        }


PatternAction = (
    SamePlaybookAction
    | ComfortEdgeAction
    | PartialTransferDiagnostic
    | VersatileCoreAction
    | ProvenFlexibilityAction
    | BouncebackAction
    | PerformanceSlideAction
    | ControlledPresenceAction
    | PresenceTaxAction
    | SessionCurveAction
)


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
    qualification_element_keys: tuple[str, ...] = ()
    qualification_clause_index: int | None = None
    effect_metrics: Mapping[str, float | int | str | bool | None] = field(default_factory=dict)
    confounders: tuple[str, ...] = ()
    blocking_confounders: tuple[str, ...] = ()
    suppression_reasons: tuple[str, ...] = ()
    methodology_version: str = "pattern-5.1.0"
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
            "qualification_element_keys": list(self.qualification_element_keys),
            "qualification_clause_index": self.qualification_clause_index,
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
    context_baseline: str = "context-baseline-0.0.0"

    def as_dict(self) -> dict[str, str]:
        return {
            "behavior_model": self.behavior_model,
            "dimension_registry": self.dimension_registry,
            "element_registry": self.element_registry,
            "pattern_registry": self.pattern_registry,
            "context_baseline": self.context_baseline,
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
