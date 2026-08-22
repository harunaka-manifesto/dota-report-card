"""Strict public schema for the immutable Free DNA v5 report."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.behavior.presentation import PATTERN_PRESENTATION_CONTRACT, PATTERN_PRESENTATION_VERSION


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class IdentitySchema(PublicModel):
    display_name: str
    avatar_url: str | None = None
    rank_tier: int | None = None


class MetadataSchema(PublicModel):
    created_at: str
    expires_at: str | None = None
    data_from: str | None = None
    data_to: str | None = None
    processed_matches: int = Field(ge=0)
    eligible_matches: int = Field(ge=0)
    # ``None`` means the product window was time-bounded without a product
    # match-count cap.  An explicit value is retained for compatibility with
    # deployments that apply an infrastructure guardrail.
    history_limit: int | None = Field(default=None, ge=1)
    raw_history_hash: str
    history_tier: Literal["limited", "normal"]


class VersionMapV5Schema(PublicModel):
    eligibility: str
    sessions: str
    features: str
    behavior_model: str
    element_registry: str
    pattern_registry: str
    pattern_ranking: str
    pattern_actions: str
    hero_taxonomy: str
    hero_relationships: str
    hero_expressions: str
    hero_reliability: str
    hero_matchups: str
    hero_synergies: str
    hero_situations: str
    hero_portfolio: str
    hero_mirror: str
    story: str
    copy_: str = Field(alias="copy")
    model: str
    template: str
    share_renderer: str
    analysis_version_fingerprint: str
    performance_proxy: str
    recency_weighting: str
    sessionization: str
    context_baseline: str = "context-baseline-0.0.0"
    presentation: str | None = None
    hero_knowledge: str | None = None
    semantic_outcomes: str | None = None
    semantic_recommendations: str | None = None


class ReproducibilityConfigSchema(PublicModel):
    half_life_days: float = Field(gt=0)
    version: str


class SessionGapConfigSchema(PublicModel):
    gap_minutes: int = Field(gt=0)
    clock_tolerance_seconds: int = Field(ge=0)


class ReproducibilitySchema(PublicModel):
    model_version: str
    element_registry_version: str
    pattern_registry_version: str
    hero_taxonomy_version: str
    hero_knowledge_version: str | None = None
    performance_proxy_version: str
    sessionization_version: str
    recency_weighting_version: str
    generated_at: str
    window_start: str | None = None
    window_end: str | None = None
    input_snapshot_hash: str
    raw_match_count: int = Field(ge=0)
    usable_match_count: int = Field(ge=0)
    deduplicated_match_count: int = Field(ge=0)
    session_count: int = Field(ge=0)
    completed_session_count: int = Field(ge=0)
    left_censored_session_count: int = Field(ge=0)
    right_censored_session_count: int = Field(ge=0)
    role_hint_coverage: float = Field(ge=0, le=1)
    hero_taxonomy_coverage: float = Field(ge=0, le=1)
    effective_sample_size: float = Field(ge=0)
    recency_config: ReproducibilityConfigSchema
    session_gap_config: SessionGapConfigSchema
    context_baseline_version: str = "context-baseline-0.0.0"


class QualitySchema(PublicModel):
    overall_confidence: Literal["low", "moderate", "high", "unavailable"]
    history_tier: Literal["limited", "normal"]
    missing_data_flags: list[str]
    partial: bool
    warnings: list[str]
    available_elements: int = Field(ge=0)
    limited_elements: int = Field(ge=0)
    unavailable_elements: int = Field(ge=0)
    qualified_patterns: int = Field(ge=0)


class BehaviorReceiptSchema(PublicModel):
    key: str
    value: float | int | str | bool | None
    unit: str
    denominator: int = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    comparison: str | None = None


BehaviorConfidence = Literal["low", "moderate", "high", "unavailable"]


class PatternActionEvidenceSchema(PublicModel):
    status: Literal["resolved", "fallback", "unresolved", "not_applicable"] = "unresolved"
    sample_size: int = Field(default=0, ge=0)
    effective_sample_size: float = Field(default=0.0, ge=0)
    coverage: float = Field(default=0.0, ge=0, le=1)
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    independent_group_count: int | None = Field(default=None, ge=0)
    evidence_keys: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance_versions: dict[str, str] = Field(default_factory=dict)


class PatternPresentationSchema(PublicModel):
    pattern_id: str
    outcome_id: str
    visual_variant: str
    proof_data: dict[str, Any]
    interpretation_id: str
    recommendation_id: str | None = None
    recommendation_context: dict[str, Any] | None = None
    deep_dive_id: str | None = None
    semantic_outcome_id: str | None = None
    semantic_recommendation_id: str | None = None
    semantic_outcome_version: str | None = None
    semantic_recommendation_version: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    raw_metrics: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    confidence: BehaviorConfidence
    presentation_version: str


class BehaviorElementSchema(PublicModel):
    key: str
    label: str
    dimension_key: str
    status: Literal["available", "limited", "unavailable"]
    score: float | None = Field(default=None, ge=0, le=1)
    centered_score: float | None = Field(default=None, ge=-1, le=1)
    axis: dict[str, str | None]
    zone: str | None = None
    confidence: BehaviorConfidence
    confidence_score: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=0)
    effective_sample_size: float = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    receipts: list[BehaviorReceiptSchema] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    blocking_confounders: list[str] = Field(default_factory=list)
    missing_reasons: list[str] = Field(default_factory=list)
    methodology_version: str


class HeroRecommendationRationaleSchema(PublicModel):
    hero_id: int = Field(gt=0)
    intent: Literal["double_down", "adjacent_move", "fill_gap", "change_angle", "specialist"]
    familiar_anchors: list[str]
    adds: list[str]
    new_demands: list[str]
    learning_distance: Literal["low", "moderate", "high"]
    role_fit: Literal["supported", "conditional", "unsupported"]
    empirical_support: Literal["high", "medium", "low", "unknown"]
    confidence: Literal["high", "medium", "low"]
    limitations: list[str]
    provenance_versions: dict[str, str]
    evidence_refs: list[str]
    eligible: bool


class PatternHeroRecommendationSchema(PublicModel):
    hero_id: int = Field(gt=0)
    hero_name: str
    direction: Literal["deepen", "stretch"]
    anchor_traits: list[str]
    added_traits: list[str]
    role_fit: list[str]
    similarity_score: float = Field(ge=0, le=1)
    novelty_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    why_it_fits: str
    what_stays_familiar: str
    what_changes: str
    provenance_versions: dict[str, str]
    semantic_rationale: HeroRecommendationRationaleSchema | None = None


class SamePlaybookActionSchema(PublicModel):
    action_type: Literal["same_playbook"]
    status: Literal["available", "limited", "unavailable"]
    dominant_traits: list[str]
    underrepresented_traits: list[str]
    deepen: list[PatternHeroRecommendationSchema]
    stretch: list[PatternHeroRecommendationSchema]
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    provenance_versions: dict[str, str]
    evidence_summary: PatternActionEvidenceSchema | None = None


class ComfortEdgeReliabilitySchema(PublicModel):
    hero_id: int = Field(gt=0)
    hero_name: str
    reliability_rank: int = Field(ge=1, le=5)
    reliability_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    matches: int = Field(ge=0)


class ComfortEdgeDevelopmentReasonSchema(PublicModel):
    hero_id: int = Field(gt=0)
    hero_name: str
    reliability_rank: int = Field(ge=3, le=5)
    reliability_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    reference_core_hero_ids: list[int] = Field(min_length=1)
    reference_core_hero_names: list[str] = Field(min_length=1)
    what_changes: list[str]
    useful_situations: list[str]
    teammate_examples: list[int]
    teammate_example_names: list[str]
    enemy_examples: list[int]
    enemy_example_names: list[str]
    tradeoffs: list[str]
    why_learn: str
    limitations: list[str]
    provenance_versions: dict[str, str]
    semantic_rationale: HeroRecommendationRationaleSchema | None = None


class ComfortEdgeActionSchema(PublicModel):
    action_type: Literal["comfort_edge"]
    status: Literal["available", "limited", "unavailable"]
    ranked_heroes: list[ComfortEdgeReliabilitySchema] = Field(max_length=5)
    reference_core_hero_ids: list[int]
    development: list[ComfortEdgeDevelopmentReasonSchema] = Field(max_length=3)
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    provenance_versions: dict[str, str]
    evidence_summary: PatternActionEvidenceSchema | None = None


class ObservedDifferenceSchema(PublicModel):
    signal_key: str
    core_value: float | None = None
    off_pool_value: float | None = None
    effect_size: float | None = None
    confidence_score: float = Field(ge=0, le=1)
    player_facing_claim: str
    coverage: float = Field(default=0.0, ge=0, le=1)


class CapabilityHypothesisSchema(PublicModel):
    capability_key: str
    core_prevalence: float = Field(ge=0, le=1)
    off_pool_prevalence: float = Field(ge=0, le=1)
    separation_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    player_facing_hypothesis: str


class PartialTransferDiagnosticSchema(PublicModel):
    action_type: Literal["partial_transfer"]
    status: Literal["direct_signal", "capability_hypothesis", "unresolved", "deep_candidate"]
    summary_differences: list[ObservedDifferenceSchema] = Field(max_length=3)
    capability_hypotheses: list[CapabilityHypothesisSchema] = Field(max_length=3)
    strongest_supported_lead: str | None = None
    core_hero_ids: list[int]
    off_pool_hero_ids: list[int]
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    deep_analysis_eligible: bool
    evidence_summary: PatternActionEvidenceSchema | None = None


class HeroJobMapSchema(PublicModel):
    hero_id: int = Field(gt=0)
    hero_name: str
    primary_jobs: list[str]
    expression_summary: str | None = None


class CoverageSummarySchema(PublicModel):
    strongly_covered: list[str]
    single_point_coverage: list[str]
    thin_coverage: list[str]
    missing: list[str]
    family_map: dict[str, str] = Field(default_factory=dict)
    family_descriptions: dict[str, str] = Field(default_factory=dict)
    primary_gap: str | None = None
    secondary_gaps: list[str] = Field(default_factory=list)
    semantic_coverage: float | None = Field(default=None, ge=0, le=1)
    role_adjusted_coverage: float | None = Field(default=None, ge=0, le=1)
    pairwise_functional_overlap: float | None = Field(default=None, ge=0, le=1)
    unique_contribution_count: int | None = Field(default=None, ge=0)


class HeroAdditionRecommendationSchema(PublicModel):
    hero_id: int = Field(gt=0)
    hero_name: str
    adds_jobs: list[str]
    shared_anchors: list[str]
    solves_gap: str
    player_facing_reason: str
    confidence_score: float = Field(ge=0, le=1)
    semantic_rationale: HeroRecommendationRationaleSchema | None = None


class VersatileCoreActionSchema(PublicModel):
    action_type: Literal["versatile_core"]
    status: Literal[
        "coverage_only",
        "coverage_plus_recommendation",
        "coverage_plus_alternatives",
        "no_obvious_gap",
    ]
    core_hero_ids: list[int]
    hero_job_maps: list[HeroJobMapSchema]
    coverage_summary: CoverageSummarySchema
    recommended_addition: HeroAdditionRecommendationSchema | None = None
    alternative_additions: list[HeroAdditionRecommendationSchema] = Field(max_length=2)
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    complementarity_qualified: bool = True
    semantic_confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_summary: PatternActionEvidenceSchema | None = None


class ProvenFlexibilityActionSchema(PublicModel):
    action_type: Literal["proven_flexibility"]
    status: Literal["peak_window", "distributed_flexibility"]
    window_start: str | None = None
    window_end: str | None = None
    total_games: int = Field(ge=0)
    hero_ids: list[int]
    hero_names: list[str]
    hero_game_counts: list[tuple[int, int]]
    meaningful_hero_count: int = Field(ge=0)
    functional_jobs: list[str]
    functional_job_count: int = Field(ge=0)
    repeated_hero_count: int = Field(ge=0)
    longest_same_hero_streak: int | None = Field(default=None, ge=0)
    secondary_proof: str | None = None
    flex_week_score: float | None = Field(default=None, ge=0, le=1)
    activity_confidence: float = Field(ge=0, le=1)
    distribution_quality: float | None = Field(default=None, ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    evidence_summary: PatternActionEvidenceSchema | None = None


class RecoveryContextSchema(PublicModel):
    label: str
    hero_id: int | None = Field(default=None, gt=0)
    function_family: str | None = None
    role_context: str | None = None
    performance_delta: float = Field(ge=-1, le=1)
    baseline_performance: float = Field(ge=0, le=1)
    observed_performance: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=0)
    session_count: int = Field(ge=0)
    primary_jobs: list[str]
    confidence_score: float = Field(ge=0, le=1)


class BouncebackActionSchema(PublicModel):
    action_type: Literal["bounceback"]
    strongest_context: RecoveryContextSchema | None = None
    comparison_contexts: list[RecoveryContextSchema]
    fallback_level: Literal["hero", "function", "role", "overall"]
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    evidence_summary: PatternActionEvidenceSchema | None = None


class PerformanceSlideActionSchema(PublicModel):
    action_type: Literal["performance_slide"]
    strongest_context: RecoveryContextSchema | None = None
    comparison_contexts: list[RecoveryContextSchema]
    fallback_level: Literal["hero", "function", "role", "overall"]
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    evidence_summary: PatternActionEvidenceSchema | None = None


class PresenceContextSchema(PublicModel):
    label: str
    hero_id: int | None = Field(default=None, gt=0)
    function_family: str | None = None
    role_context: str | None = None
    involvement_level: float = Field(ge=0, le=1)
    death_exposure_level: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=0)
    confidence_score: float = Field(ge=0, le=1)


class ControlledPresenceActionSchema(PublicModel):
    action_type: Literal["controlled_presence"]
    strongest_context: PresenceContextSchema | None = None
    comparison_rows: list[PresenceContextSchema]
    finishing_flavor: str | None = None
    fallback_level: Literal["hero", "function", "role", "overall"]
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    evidence_summary: PatternActionEvidenceSchema | None = None


class PresenceTaxActionSchema(PublicModel):
    action_type: Literal["presence_tax"]
    shape: Literal["job_shaped", "hero_specific", "cross_context", "unresolved"]
    strongest_contexts: list[PresenceContextSchema]
    comparison_contexts: list[PresenceContextSchema]
    deep_analysis_candidate: bool
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    evidence_summary: PatternActionEvidenceSchema | None = None


class SessionCurvePointSchema(PublicModel):
    bucket: Literal["G1", "G2", "G3", "G4", "G5+"]
    relative_delta: float = Field(ge=-1, le=1)
    sample_size: int = Field(ge=0)
    effective_sample_size: float = Field(ge=0)
    supported: bool


class SessionCurveActionSchema(PublicModel):
    action_type: Literal["session_fade", "session_rise"]
    status: Literal["resolved", "fallback", "unresolved", "not_applicable"]
    direction: Literal["fade", "rise"]
    curve: list[SessionCurvePointSchema] = Field(min_length=5, max_length=5)
    breakpoint_state: Literal["stable_breakpoint", "gradual", "unresolved"]
    breakpoint_bucket: Literal["G1", "G2", "G3", "G4", "G5+"] | None = None
    companion_signals: list[str]
    independent_session_count: int = Field(ge=0)
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]
    evidence_summary: PatternActionEvidenceSchema | None = None


PatternActionSchema = Annotated[
    SamePlaybookActionSchema
    | ComfortEdgeActionSchema
    | PartialTransferDiagnosticSchema
    | VersatileCoreActionSchema
    | ProvenFlexibilityActionSchema
    | BouncebackActionSchema
    | PerformanceSlideActionSchema
    | ControlledPresenceActionSchema
    | PresenceTaxActionSchema
    | SessionCurveActionSchema,
    Field(discriminator="action_type"),
]


class BehaviorPatternSchema(PublicModel):
    key: str
    label: str
    kind: Literal["identity", "contradiction", "edge", "leak", "trajectory", "style"]
    status: Literal["qualified", "suppressed", "unavailable"]
    direction: str | None = None
    strength: float = Field(ge=0, le=1)
    relationship_strength: float = Field(ge=0, le=1)
    confidence: BehaviorConfidence
    confidence_score: float = Field(ge=0, le=1)
    evidence_coverage: float = Field(ge=0, le=1)
    qualification_quality: float = Field(ge=0, le=1)
    element_keys: list[str] = Field(min_length=2)
    qualification_element_keys: list[str] = Field(default_factory=list)
    qualification_clause_index: int | None = Field(default=None, ge=0)
    modifier_element_keys: list[str] = Field(default_factory=list)
    family: str
    tier: Literal["A", "B"]
    receipts: list[BehaviorReceiptSchema] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    blocking_confounders: list[str] = Field(default_factory=list)
    story_eligibility: Literal["eligible", "blocked"]
    story_blockers: list[str] = Field(default_factory=list)
    suppression_reasons: list[str] = Field(default_factory=list)
    methodology_version: str
    action: PatternActionSchema | None = None
    presentation: PatternPresentationSchema | None = None


class HighlightsSchema(PublicModel):
    element_keys: list[str] = Field(max_length=3)
    pattern_keys: list[str] = Field(max_length=5)


class ChoiceOptionSchema(PublicModel):
    key: str
    label: str
    hero_id: int | None = Field(default=None, gt=0)
    feedback: str | None = None


class CommonThreadSchema(PublicModel):
    status: Literal["available", "unavailable"]
    trait_key: str | None = None
    trait_label: str | None = None
    weighted_coverage: float = Field(ge=0, le=1)
    hero_count: int = Field(ge=0)
    denominator: int = Field(ge=0)
    secondary_traits: list[str]
    options: list[ChoiceOptionSchema]
    correct_option_key: str | None = None
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]


class ExceptionSchema(PublicModel):
    status: Literal["available", "no_clear_exception", "unavailable"]
    hero_id: int | None = Field(default=None, gt=0)
    hero_name: str | None = None
    pool_traits: list[str]
    exception_traits: list[str]
    options: list[ChoiceOptionSchema]
    correct_option_key: str | None = None
    distance: float | None = Field(default=None, ge=0)
    margin: float | None = None
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]


class EvolutionSchema(PublicModel):
    status: Literal["available", "unavailable"]
    variant: Literal[
        "new_heroes_new_toolkit", "new_heroes_same_toolkit", "stable_core_new_branch", "broadly_stable"
    ] | None = None
    earlier_hero_ids: list[int]
    recent_hero_ids: list[int]
    earlier_traits: list[str]
    recent_traits: list[str]
    hero_distribution_shift: float | None = Field(default=None, ge=0, le=1)
    toolkit_distribution_shift: float | None = Field(default=None, ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    earlier_sample_size: int = Field(default=0, ge=0)
    recent_sample_size: int = Field(default=0, ge=0)
    earlier_taxonomy_coverage: float = Field(default=0, ge=0, le=1)
    recent_taxonomy_coverage: float = Field(default=0, ge=0, le=1)
    earlier_start: str | None = None
    earlier_end: str | None = None
    recent_start: str | None = None
    recent_end: str | None = None
    limitations: list[str]


class HeroMirrorSchema(PublicModel):
    status: Literal["available", "no_clear_mirror", "unavailable"]
    hero_id: int | None = Field(default=None, gt=0)
    hero_name: str | None = None
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    runner_up_hero_id: int | None = Field(default=None, gt=0)
    margin: float | None = None
    player_behavior: dict[str, str]
    hero_behavior: dict[str, str]
    confidence_score: float = Field(ge=0, le=1)
    limitations: list[str]


class HeroPortfolioSchema(PublicModel):
    common_thread: CommonThreadSchema
    exception: ExceptionSchema
    evolution: EvolutionSchema
    hero_mirror: HeroMirrorSchema
    version: str


class StorySchema(PublicModel):
    version: str
    ordered_pages: list[str]


StoryPageKindV4 = Literal[
    "element_scan",
    "element_highlight",
    "pattern_highlight",
    "hero_common_thread_question",
    "hero_exception_question",
    "pool_evolution_question",
    "pool_evolution_reveal",
    "hero_mirror_reveal",
    "final_card",
    "deep_dive",
]


class StoryPageV4Schema(PublicModel):
    id: str
    kind: StoryPageKindV4
    section: Literal["elements", "patterns", "hero_portfolio", "finale"]
    title: str
    body: str | None = None
    evidence_keys: list[str] = Field(default_factory=list)
    element_key: str | None = None
    pattern_key: str | None = None
    portfolio_key: str | None = None
    options: list[ChoiceOptionSchema] = Field(default_factory=list)
    content: dict[str, Any] = Field(default_factory=dict)
    presentation: PatternPresentationSchema | None = None


class ShareElementSchema(PublicModel):
    key: str
    label: str
    zone: str | None = None


class SharePatternSchema(PublicModel):
    key: str
    label: str


class SharePortfolioSchema(PublicModel):
    common_thread: str | None = None
    exception_hero: str | None = None
    pool_direction: str | None = None


class ShareMirrorSchema(PublicModel):
    hero_id: int = Field(gt=0)
    hero_name: str


class ShareV4Schema(PublicModel):
    display_name: str | None = None
    strongest_elements: list[ShareElementSchema]
    strongest_patterns: list[SharePatternSchema]
    hero_portfolio: SharePortfolioSchema
    hero_mirror: ShareMirrorSchema | None = None


class PrivacyDefaultsSchema(PublicModel):
    show_name: bool
    show_avatar: bool
    show_raw_id: Literal[False]


class SharesV4Schema(PublicModel):
    final: ShareV4Schema
    privacy_defaults: PrivacyDefaultsSchema


class DeepDiveSchema(PublicModel):
    available: bool
    cta_label: str
    href: str
    copy_: str = Field(alias="copy")


class MethodologySchema(PublicModel):
    free_summary_only: Literal[True]
    session_gap_minutes: int = Field(ge=1)
    session_policy_version: str
    notes: list[str]


class CostSchema(PublicModel):
    history_requests: int = Field(ge=0)
    detail_requests: Literal[0]
    parse_requests: Literal[0]
    parse_status_requests: Literal[0]
    cache_hits: int = Field(ge=0)
    estimated_cost_units: float = Field(ge=0)


class FreeDnaReportV4Schema(PublicModel):
    report_id: str | None = None
    schema_version: Literal["free-dna-report-5.0.0", "free-dna-report-5.1.0", "free-dna-report-5.2.0"]
    report_variant: Literal["free_dna_report"]
    noindex: Literal[True]
    identity: IdentitySchema
    metadata: MetadataSchema
    versions: VersionMapV5Schema
    reproducibility: ReproducibilitySchema
    quality: QualitySchema
    elements: list[BehaviorElementSchema] = Field(min_length=18, max_length=18)
    patterns: list[BehaviorPatternSchema] = Field(min_length=11, max_length=11)
    highlights: HighlightsSchema
    hero_portfolio: HeroPortfolioSchema
    story: StorySchema
    pages: list[StoryPageV4Schema]
    shares: SharesV4Schema
    deep_dive: DeepDiveSchema
    methodology: MethodologySchema
    cost: CostSchema

    @model_validator(mode="after")
    def validate_v5_contract(self) -> FreeDnaReportV4Schema:
        from app.behavior.elements.registry import ELEMENT_REGISTRY
        from app.behavior.patterns.registry import PATTERN_REGISTRY

        element_keys = [item.key for item in self.elements]
        if set(element_keys) != set(ELEMENT_REGISTRY) or len(element_keys) != len(set(element_keys)):
            raise ValueError("Free DNA v5 must contain each of the 18 registered Elements once")
        pattern_keys = [item.key for item in self.patterns]
        if set(pattern_keys) != set(PATTERN_REGISTRY) or len(pattern_keys) != len(set(pattern_keys)):
            raise ValueError("Free DNA v5 must contain each of the 11 registered Patterns once")
        if len(self.highlights.element_keys) != len(set(self.highlights.element_keys)):
            raise ValueError("Element highlights must be unique")
        if len(self.highlights.pattern_keys) != len(set(self.highlights.pattern_keys)):
            raise ValueError("Pattern highlights must be unique")
        if not set(self.highlights.element_keys).issubset(element_keys):
            raise ValueError("Element highlight references an unknown Element")
        if not set(self.highlights.pattern_keys).issubset(pattern_keys):
            raise ValueError("Pattern highlight references an unknown Pattern")
        eligible_element_keys = {
            item.key for item in self.elements if item.status != "unavailable" and item.score is not None
        }
        if len(eligible_element_keys) >= 3 and len(self.highlights.element_keys) != 3:
            raise ValueError("Free DNA must show exactly three Element highlights when three are eligible")
        if not set(self.highlights.element_keys).issubset(eligible_element_keys):
            raise ValueError("Element highlights must reference display-eligible Elements")
        eligible_pattern_keys = {
            item.key
            for item in self.patterns
            if item.status == "qualified"
            and item.story_eligibility == "eligible"
            and not item.story_blockers
        }
        if len(eligible_pattern_keys) >= 5 and len(self.highlights.pattern_keys) != 5:
            raise ValueError("Free DNA must show exactly five Pattern highlights when five are eligible")
        if len(eligible_pattern_keys) < 5 and len(self.highlights.pattern_keys) != len(eligible_pattern_keys):
            raise ValueError("Free DNA must preserve every eligible Pattern when fewer than five are available")
        if not set(self.highlights.pattern_keys).issubset(eligible_pattern_keys):
            raise ValueError("Pattern highlights must reference story-eligible qualified Patterns")
        for pattern in self.patterns:
            if not set(pattern.element_keys).issubset(element_keys):
                raise ValueError(f"Pattern {pattern.key} references an unknown required Element")
            if not set(pattern.qualification_element_keys).issubset(pattern.element_keys):
                raise ValueError(f"Pattern {pattern.key} exposes an unknown qualification Element")
            if not set(pattern.modifier_element_keys).issubset(element_keys):
                raise ValueError(f"Pattern {pattern.key} references an unknown modifier Element")
            if set(pattern.element_keys) & set(pattern.modifier_element_keys):
                raise ValueError(f"Pattern {pattern.key} overlaps required and modifier Elements")
            if pattern.story_eligibility == "blocked" and not pattern.story_blockers:
                raise ValueError(f"Blocked Pattern {pattern.key} must expose story blockers")
            if pattern.action is not None and pattern.action.action_type != pattern.key:
                raise ValueError(f"Pattern {pattern.key} carries the wrong action discriminator")
            if self.schema_version == "free-dna-report-5.2.0":
                presentation = pattern.presentation
                contract = PATTERN_PRESENTATION_CONTRACT[pattern.key]
                if presentation is None:
                    raise ValueError(f"v5.2 Pattern {pattern.key} is missing its presentation payload")
                if presentation.pattern_id != pattern.key:
                    raise ValueError(f"Pattern {pattern.key} presentation has the wrong pattern ID")
                if presentation.outcome_id != contract["outcome_id"]:
                    raise ValueError(f"Pattern {pattern.key} presentation has the wrong outcome ID")
                if presentation.visual_variant != contract["visual_variant"]:
                    raise ValueError(f"Pattern {pattern.key} presentation has the wrong visual variant")
                if presentation.presentation_version != PATTERN_PRESENTATION_VERSION:
                    raise ValueError(f"Pattern {pattern.key} presentation has the wrong version")
        if self.schema_version == "free-dna-report-5.2.0" and self.versions.presentation != PATTERN_PRESENTATION_VERSION:
            raise ValueError("v5.2 reports must identify the pattern presentation version")
        if self.schema_version == "free-dna-report-5.2.0":
            if self.versions.hero_knowledge is None or self.reproducibility.hero_knowledge_version is None:
                raise ValueError("v5.2 reports must identify the normalized hero-knowledge snapshot")
        common = self.hero_portfolio.common_thread
        if common.status == "available":
            if len(common.options) != 4 or common.correct_option_key is None:
                raise ValueError("Available Common Thread must contain four answer options")
            if len({option.key for option in common.options}) != 4 or any(not option.feedback for option in common.options):
                raise ValueError("Common Thread options must be unique and carry contextual feedback")
            if sum(option.key == common.correct_option_key for option in common.options) != 1:
                raise ValueError("Common Thread correct option must appear exactly once")
        exception = self.hero_portfolio.exception
        if exception.status in {"available", "no_clear_exception"}:
            if len(exception.options) != 4:
                raise ValueError("Resolved Exception states must contain four answer options")
            if len({option.key for option in exception.options}) != 4 or any(not option.feedback for option in exception.options):
                raise ValueError("Exception options must be unique and carry contextual feedback")
            if exception.correct_option_key is None or sum(option.key == exception.correct_option_key for option in exception.options) != 1:
                raise ValueError("Exception correct option must appear exactly once")
            if exception.status == "no_clear_exception" and exception.correct_option_key != "no_clear_exception":
                raise ValueError("No-clear Exception must use the no-clear option as truth")
        page_ids = [item.id for item in self.pages]
        if page_ids != self.story.ordered_pages or len(page_ids) != len(set(page_ids)):
            raise ValueError("Free DNA v5 story ordering must match unique public pages")
        for page in self.pages:
            if page.element_key is not None and page.element_key not in element_keys:
                raise ValueError(f"Story page references unknown Element: {page.element_key}")
            if page.pattern_key is not None and page.pattern_key not in pattern_keys:
                raise ValueError(f"Story page references unknown Pattern: {page.pattern_key}")
            if not set(page.evidence_keys).issubset(element_keys):
                raise ValueError(f"Story page {page.id} references an unknown Element")
            if self.schema_version == "free-dna-report-5.2.0" and page.kind == "pattern_highlight":
                if page.pattern_key is None:
                    if page.id != "pattern-read" or self.highlights.pattern_keys:
                        raise ValueError(f"v5.2 Pattern page {page.id} is missing its Pattern key")
                    continue
                if page.pattern_key is None or page.presentation is None:
                    raise ValueError(f"v5.2 Pattern page {page.id} is missing its presentation payload")
                if page.presentation.pattern_id != page.pattern_key:
                    raise ValueError(f"v5.2 Pattern page {page.id} has the wrong presentation Pattern")
                presentation_copy = page.content.get("presentation_copy")
                required_copy_keys = {"headline", "subheadline", "interpretation", "recommendation", "deep_dive", "fallback"}
                if not isinstance(presentation_copy, dict) or not required_copy_keys.issubset(presentation_copy):
                    raise ValueError(f"v5.2 Pattern page {page.id} is missing presentation copy")
        page_kinds = [page.kind for page in self.pages]
        expected_kinds = [
            "element_scan",
            *(["element_highlight"] * len(self.highlights.element_keys)),
            *(
                ["pattern_highlight"] * len(self.highlights.pattern_keys)
                if self.highlights.pattern_keys
                else ["pattern_highlight"]
            ),
            "hero_common_thread_question",
            "hero_exception_question",
            "pool_evolution_question",
            "pool_evolution_reveal",
            "hero_mirror_reveal",
            "final_card",
            "deep_dive",
        ]
        if page_kinds != expected_kinds:
            raise ValueError("Free DNA v5 story pages do not match the reviewed structure")
        share_pool_direction = self.shares.final.hero_portfolio.pool_direction
        if share_pool_direction in {
            "new_heroes_new_toolkit",
            "new_heroes_same_toolkit",
            "stable_core_new_branch",
            "broadly_stable",
        }:
            raise ValueError("Share cards must use human Pool Evolution copy, not enum labels")
        if self.shares.privacy_defaults.show_raw_id is not False:
            raise ValueError("Free DNA share cards cannot enable raw IDs")
        if self.cost.detail_requests != 0 or self.cost.parse_requests != 0:
            raise ValueError("Free DNA v5 cannot require match-detail or replay-parse requests")
        return self


FreeDnaReportV5Schema = FreeDnaReportV4Schema


def validate_free_dna_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate a new immutable v5 snapshot at the public API boundary."""

    return FreeDnaReportV4Schema.model_validate(report).model_dump(mode="json", by_alias=True)


__all__ = [
    "FreeDnaReportV4Schema",
    "FreeDnaReportV5Schema",
    "PatternPresentationSchema",
    "validate_free_dna_report",
]
