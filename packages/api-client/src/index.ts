export type CreateAnalysisRequest = {
  player: string;
  refresh?: boolean;
  mode?: "free" | "deep_scan";
};

export type CreateAnalysisResponse = {
  job_id: string;
  status: string;
  analysis_mode: string;
  reused: boolean;
  events_url: string;
};

export type AnalysisStatus = {
  job_id: string;
  account_id: number;
  analysis_mode: "free" | "deep_scan";
  status: string;
  stage: string;
  processed_matches: number;
  eligible_matches: number;
  warnings: string[];
  failure_code: string | null;
  message: string | null;
  report_id: string | null;
  events_url: string;
  completed_stages: string[];
};

export type Confidence = "low" | "moderate" | "high" | "unavailable";
export type ElementStatus = "available" | "limited" | "unavailable";
export type PatternStatus = "qualified" | "suppressed" | "unavailable";

export type PatternActionEvidence = {
  status: "resolved" | "fallback" | "unresolved" | "not_applicable";
  sample_size: number;
  effective_sample_size: number;
  coverage: number;
  confidence_score: number;
  independent_group_count: number | null;
  evidence_keys: string[];
  limitations: string[];
  provenance_versions: Record<string, string>;
};

export type BehaviorElementReceipt = {
  key: string;
  value: number | string | boolean | null;
  unit: string;
  denominator: number;
  coverage: number;
  confidence_score: number;
  comparison: string | null;
};

export type BehaviorElement = {
  key: string;
  label: string;
  dimension_key: string;
  status: ElementStatus;
  score: number | null;
  centered_score: number | null;
  axis: { left: string | null; right: string | null };
  zone: string | null;
  confidence: Confidence;
  confidence_score: number;
  sample_size: number;
  effective_sample_size: number;
  coverage: number;
  receipts: BehaviorElementReceipt[];
  confounders: string[];
  blocking_confounders: string[];
  missing_reasons: string[];
  methodology_version: string;
};

export type PatternHeroRecommendation = {
  hero_id: number;
  hero_name: string;
  direction: "deepen" | "stretch";
  anchor_traits: string[];
  added_traits: string[];
  role_fit: string[];
  similarity_score: number;
  novelty_score: number;
  confidence_score: number;
  why_it_fits: string;
  what_stays_familiar: string;
  what_changes: string;
  provenance_versions: Record<string, string>;
};

export type SamePlaybookAction = {
  action_type: "same_playbook";
  status: "available" | "limited" | "unavailable";
  dominant_traits: string[];
  underrepresented_traits: string[];
  deepen: PatternHeroRecommendation[];
  stretch: PatternHeroRecommendation[];
  confidence_score: number;
  limitations: string[];
  provenance_versions: Record<string, string>;
  evidence_summary?: PatternActionEvidence | null;
};

export type ComfortEdgeReliability = {
  hero_id: number;
  hero_name: string;
  reliability_rank: number;
  reliability_score: number;
  confidence_score: number;
  matches: number;
};

export type ComfortEdgeDevelopmentReason = {
  hero_id: number;
  hero_name: string;
  reliability_rank: number;
  reliability_score: number;
  confidence_score: number;
  reference_core_hero_ids: number[];
  reference_core_hero_names: string[];
  what_changes: string[];
  useful_situations: string[];
  teammate_examples: number[];
  teammate_example_names: string[];
  enemy_examples: number[];
  enemy_example_names: string[];
  tradeoffs: string[];
  why_learn: string;
  limitations: string[];
  provenance_versions: Record<string, string>;
};

export type ComfortEdgeAction = {
  action_type: "comfort_edge";
  status: "available" | "limited" | "unavailable";
  ranked_heroes: ComfortEdgeReliability[];
  reference_core_hero_ids: number[];
  development: ComfortEdgeDevelopmentReason[];
  confidence_score: number;
  limitations: string[];
  provenance_versions: Record<string, string>;
  evidence_summary?: PatternActionEvidence | null;
};

export type ObservedDifference = {
  signal_key: string;
  core_value: number | null;
  off_pool_value: number | null;
  effect_size: number | null;
  confidence_score: number;
  player_facing_claim: string;
  coverage?: number;
};

export type CapabilityHypothesis = {
  capability_key: string;
  core_prevalence: number;
  off_pool_prevalence: number;
  separation_score: number;
  confidence_score: number;
  player_facing_hypothesis: string;
};

export type PartialTransferDiagnostic = {
  action_type: "partial_transfer";
  status: "direct_signal" | "capability_hypothesis" | "unresolved" | "deep_candidate";
  summary_differences: ObservedDifference[];
  capability_hypotheses: CapabilityHypothesis[];
  strongest_supported_lead: string | null;
  core_hero_ids: number[];
  off_pool_hero_ids: number[];
  confidence_score: number;
  limitations: string[];
  deep_analysis_eligible: boolean;
  evidence_summary?: PatternActionEvidence | null;
};

export type HeroJobMap = {
  hero_id: number;
  hero_name: string;
  primary_jobs: string[];
  expression_summary: string | null;
};

export type CoverageSummary = {
  strongly_covered: string[];
  single_point_coverage: string[];
  thin_coverage: string[];
  missing: string[];
};

export type HeroAdditionRecommendation = {
  hero_id: number;
  hero_name: string;
  adds_jobs: string[];
  shared_anchors: string[];
  solves_gap: string;
  player_facing_reason: string;
  confidence_score: number;
};

export type VersatileCoreAction = {
  action_type: "versatile_core";
  status: "coverage_only" | "coverage_plus_recommendation" | "coverage_plus_alternatives" | "no_obvious_gap";
  core_hero_ids: number[];
  hero_job_maps: HeroJobMap[];
  coverage_summary: CoverageSummary;
  recommended_addition: HeroAdditionRecommendation | null;
  alternative_additions: HeroAdditionRecommendation[];
  confidence_score: number;
  limitations: string[];
  evidence_summary?: PatternActionEvidence | null;
};

export type ProvenFlexibilityAction = {
  action_type: "proven_flexibility";
  status: "peak_window" | "distributed_flexibility";
  window_start: string | null;
  window_end: string | null;
  total_games: number;
  hero_ids: number[];
  hero_names: string[];
  hero_game_counts: [number, number][];
  meaningful_hero_count: number;
  functional_jobs: string[];
  functional_job_count: number;
  repeated_hero_count: number;
  longest_same_hero_streak: number | null;
  secondary_proof: string | null;
  flex_week_score: number | null;
  activity_confidence: number;
  distribution_quality: number | null;
  confidence_score: number;
  limitations: string[];
  evidence_summary?: PatternActionEvidence | null;
};

export type RecoveryContext = {
  label: string;
  hero_id: number | null;
  function_family: string | null;
  role_context: string | null;
  performance_delta: number;
  baseline_performance: number;
  observed_performance: number;
  sample_size: number;
  session_count: number;
  primary_jobs: string[];
  confidence_score: number;
};

export type BouncebackAction = {
  action_type: "bounceback";
  strongest_context: RecoveryContext | null;
  comparison_contexts: RecoveryContext[];
  fallback_level: "hero" | "function" | "role" | "overall";
  confidence_score: number;
  limitations: string[];
  evidence_summary?: PatternActionEvidence | null;
};

export type PerformanceSlideAction = {
  action_type: "performance_slide";
  strongest_context: RecoveryContext | null;
  comparison_contexts: RecoveryContext[];
  fallback_level: "hero" | "function" | "role" | "overall";
  confidence_score: number;
  limitations: string[];
  evidence_summary?: PatternActionEvidence | null;
};

export type PresenceContext = {
  label: string;
  hero_id: number | null;
  function_family: string | null;
  role_context: string | null;
  involvement_level: number;
  death_exposure_level: number;
  sample_size: number;
  confidence_score: number;
};

export type ControlledPresenceAction = {
  action_type: "controlled_presence";
  strongest_context: PresenceContext | null;
  comparison_rows: PresenceContext[];
  finishing_flavor: string | null;
  fallback_level: "hero" | "function" | "role" | "overall";
  confidence_score: number;
  limitations: string[];
  evidence_summary?: PatternActionEvidence | null;
};

export type PresenceTaxAction = {
  action_type: "presence_tax";
  shape: "job_shaped" | "hero_specific" | "cross_context" | "unresolved";
  strongest_contexts: PresenceContext[];
  comparison_contexts: PresenceContext[];
  deep_analysis_candidate: boolean;
  confidence_score: number;
  limitations: string[];
  evidence_summary?: PatternActionEvidence | null;
};

export type SessionCurvePoint = {
  bucket: "G1" | "G2" | "G3" | "G4" | "G5+";
  relative_delta: number;
  sample_size: number;
  effective_sample_size: number;
  supported: boolean;
};

export type SessionCurveAction = {
  action_type: "session_fade" | "session_rise";
  status: "resolved" | "fallback" | "unresolved" | "not_applicable";
  direction: "fade" | "rise";
  curve: SessionCurvePoint[];
  breakpoint_state: "stable_breakpoint" | "gradual" | "unresolved";
  breakpoint_bucket: "G1" | "G2" | "G3" | "G4" | "G5+" | null;
  companion_signals: string[];
  independent_session_count: number;
  confidence_score: number;
  limitations: string[];
  evidence_summary?: PatternActionEvidence | null;
};

export type PatternAction = SamePlaybookAction | ComfortEdgeAction | PartialTransferDiagnostic | VersatileCoreAction | ProvenFlexibilityAction | BouncebackAction | PerformanceSlideAction | ControlledPresenceAction | PresenceTaxAction | SessionCurveAction;

export type PatternVisualVariant =
  | "hero_job_cluster"
  | "hero_reliability_ladder"
  | "transfer_split"
  | "toolkit_orbit"
  | "flex_window_grid"
  | "post_loss_transition"
  | "presence_exposure_map"
  | "session_curve";

export type PatternPresentation = {
  pattern_id: string;
  outcome_id: string;
  visual_variant: PatternVisualVariant;
  proof_data: Record<string, unknown>;
  interpretation_id: string;
  recommendation_id: string | null;
  recommendation_context: Record<string, unknown> | null;
  deep_dive_id: string | null;
  evidence_refs: string[];
  raw_metrics: Record<string, number | string | boolean | null>;
  confidence: Confidence;
  presentation_version: string;
};

export type BehaviorPattern = {
  key: string;
  label: string;
  kind: "identity" | "contradiction" | "edge" | "leak" | "trajectory" | "style";
  status: PatternStatus;
  direction: string | null;
  strength: number;
  relationship_strength: number;
  confidence: Confidence;
  confidence_score: number;
  evidence_coverage: number;
  qualification_quality: number;
  element_keys: string[];
  qualification_element_keys?: string[];
  qualification_clause_index?: number | null;
  modifier_element_keys: string[];
  family: string;
  tier: "A" | "B";
  receipts: BehaviorElementReceipt[];
  confounders: string[];
  blocking_confounders: string[];
  story_eligibility: "eligible" | "blocked";
  story_blockers: string[];
  suppression_reasons: string[];
  methodology_version: string;
  action: PatternAction | null;
  presentation?: PatternPresentation | null;
};

export type ChoiceOption = {
  key: string;
  label: string;
  hero_id: number | null;
  feedback?: string | null;
};

export type CommonThread = {
  status: "available" | "unavailable";
  trait_key: string | null;
  trait_label: string | null;
  weighted_coverage: number;
  hero_count: number;
  denominator: number;
  secondary_traits: string[];
  options: ChoiceOption[];
  correct_option_key: string | null;
  confidence_score: number;
  limitations: string[];
};

export type HeroException = {
  status: "available" | "no_clear_exception" | "unavailable";
  hero_id: number | null;
  hero_name: string | null;
  pool_traits: string[];
  exception_traits: string[];
  options: ChoiceOption[];
  correct_option_key: string | null;
  distance: number | null;
  margin: number | null;
  confidence_score: number;
  limitations: string[];
};

export type PoolEvolution = {
  status: "available" | "unavailable";
  variant: "new_heroes_new_toolkit" | "new_heroes_same_toolkit" | "stable_core_new_branch" | "broadly_stable" | null;
  earlier_hero_ids: number[];
  recent_hero_ids: number[];
  earlier_traits: string[];
  recent_traits: string[];
  hero_distribution_shift: number | null;
  toolkit_distribution_shift: number | null;
  confidence_score: number;
  earlier_sample_size: number;
  recent_sample_size: number;
  earlier_taxonomy_coverage: number;
  recent_taxonomy_coverage: number;
  limitations: string[];
};

export type HeroMirror = {
  status: "available" | "no_clear_mirror" | "unavailable";
  hero_id: number | null;
  hero_name: string | null;
  similarity_score: number | null;
  runner_up_hero_id: number | null;
  margin: number | null;
  player_behavior: Record<string, string>;
  hero_behavior: Record<string, string>;
  confidence_score: number;
  limitations: string[];
};

export type HeroPortfolio = {
  common_thread: CommonThread;
  exception: HeroException;
  evolution: PoolEvolution;
  hero_mirror: HeroMirror;
  version: string;
};

export type StoryPageKind =
  | "element_scan"
  | "element_highlight"
  | "pattern_highlight"
  | "hero_common_thread_question"
  | "hero_exception_question"
  | "pool_evolution_question"
  | "pool_evolution_reveal"
  | "hero_mirror_reveal"
  | "final_card"
  | "deep_dive";

export type StoryPage = {
  id: string;
  kind: StoryPageKind;
  section: "elements" | "patterns" | "hero_portfolio" | "finale";
  title: string;
  body: string | null;
  evidence_keys: string[];
  element_key?: string | null;
  pattern_key?: string | null;
  portfolio_key?: string | null;
  options: ChoiceOption[];
  content: StoryPageContent;
  presentation?: PatternPresentation | null;
};

export type PatternActionCopy = {
  same_playbook_kicker?: string;
  same_playbook_heading?: string;
  same_playbook_intro?: string;
  same_playbook_deepen_label?: string;
  same_playbook_deepen_description?: string;
  same_playbook_stretch_label?: string;
  same_playbook_stretch_description?: string;
  same_playbook_recurring_core_label?: string;
  same_playbook_familiar_label?: string;
  same_playbook_changes_label?: string;
  same_playbook_empty_direction?: string;
  comfort_edge_kicker?: string;
  comfort_edge_heading?: string;
  comfort_edge_intro?: string;
  comfort_edge_reliability_label?: string;
  comfort_edge_why_learn_label?: string;
  comfort_edge_useful_when_label?: string;
  comfort_edge_enemy_examples_label?: string;
  comfort_edge_teammate_examples_label?: string;
  comfort_edge_tradeoff_label?: string;
  partial_transfer_kicker?: string;
  partial_transfer_heading?: string;
  partial_transfer_direct_label?: string;
  partial_transfer_hypothesis_label?: string;
  partial_transfer_unresolved_heading?: string;
  partial_transfer_deep_label?: string;
  versatile_core_kicker?: string;
  versatile_core_heading?: string;
  versatile_core_jobs_label?: string;
  versatile_core_coverage_label?: string;
  versatile_core_next_tool_label?: string;
  versatile_core_alternatives_label?: string;
  versatile_core_no_gap_heading?: string;
  proven_flexibility_kicker?: string;
  proven_flexibility_heading?: string;
  proven_flexibility_roster_label?: string;
  proven_flexibility_proof_label?: string;
  proven_flexibility_distributed_heading?: string;
  controlled_presence_kicker?: string;
  controlled_presence_heading?: string;
  controlled_presence_context_label?: string;
  controlled_presence_finishing_label?: string;
  presence_tax_kicker?: string;
  presence_tax_heading?: string;
  presence_tax_deep_label?: string;
  presence_tax_unresolved_body?: string;
  bounceback_kicker?: string;
  bounceback_heading?: string;
  performance_slide_kicker?: string;
  performance_slide_heading?: string;
  recovery_context_label?: string;
  recovery_delta_label?: string;
  session_fade_kicker?: string;
  session_fade_heading?: string;
  session_fade_breakpoint_label?: string;
  session_fade_gradual_label?: string;
  session_rise_kicker?: string;
  session_rise_heading?: string;
  session_rise_breakpoint_label?: string;
  session_rise_gradual_label?: string;
};

export type PatternPresentationCopy = {
  headline: string;
  subheadline: string;
  interpretation: { title: string; body: string };
  recommendation: { eyebrow: string; title: string; body: string } | null;
  deep_dive: { title: string; body: string } | null;
  fallback: { title?: string; body?: string };
};

export type StoryPageContent = {
  scanning_body?: string;
  ready_body?: string;
  meaning?: string;
  observation?: string;
  observations?: string[];
  why_highlight?: string;
  evidence?: string;
  what_to_notice?: string;
  worthwhile?: string;
  worth_noticing?: string;
  player_read?: string;
  example?: string;
  takeaway?: string;
  guardrail?: string;
  presentation_copy?: PatternPresentationCopy;
  required_element_keys?: string[];
  modifier_element_keys?: string[];
  boundary?: string;
  correct_label?: string;
  incorrect_label?: string;
  locked_copy?: string;
  copy?: string;
  closed?: string;
  available?: string;
  qualifier?: string;
  action_copy?: PatternActionCopy | null;
};

export type ShareElement = { key: string; label: string; zone: string | null };
export type SharePattern = { key: string; label: string };

export type Reproducibility = {
  model_version: string;
  element_registry_version: string;
  pattern_registry_version: string;
  hero_taxonomy_version: string;
  hero_knowledge_version?: string | null;
  performance_proxy_version: string;
  sessionization_version: string;
  recency_weighting_version: string;
  generated_at: string;
  window_start: string | null;
  window_end: string | null;
  input_snapshot_hash: string;
  raw_match_count: number;
  usable_match_count: number;
  deduplicated_match_count: number;
  session_count: number;
  completed_session_count: number;
  left_censored_session_count: number;
  right_censored_session_count: number;
  role_hint_coverage: number;
  hero_taxonomy_coverage: number;
  effective_sample_size: number;
  recency_config: { half_life_days: number; version: string };
  session_gap_config: { gap_minutes: number; clock_tolerance_seconds: number };
  context_baseline_version?: string;
};

export type FreeDnaReportV4 = {
  report_id: string | null;
  // v4 remains readable for already-persisted reports; new reports are v5.
  schema_version: "free-dna-report-4.0.0" | "free-dna-report-5.0.0" | "free-dna-report-5.1.0" | "free-dna-report-5.2.0";
  report_variant: "free_dna_report";
  noindex: true;
  identity: {
    display_name: string;
    avatar_url: string | null;
    rank_tier: number | null;
  };
  metadata: {
    created_at: string;
    expires_at: string | null;
    data_from: string | null;
    data_to: string | null;
    processed_matches: number;
    eligible_matches: number;
    history_limit: number | null;
    raw_history_hash: string;
    history_tier: "limited" | "normal";
  };
  versions: {
    eligibility: string;
    sessions: string;
    features: string;
    behavior_model: string;
    element_registry: string;
    pattern_registry: string;
    pattern_ranking: string;
    pattern_actions: string;
    hero_taxonomy: string;
    hero_knowledge?: string | null;
    hero_relationships: string;
    hero_expressions: string;
    hero_reliability: string;
    hero_matchups: string;
    hero_synergies: string;
    hero_situations: string;
    hero_portfolio: string;
    hero_mirror: string;
    story: string;
    copy: string;
    model: string;
    template: string;
    share_renderer: string;
    analysis_version_fingerprint: string;
    performance_proxy?: string;
    recency_weighting?: string;
    sessionization?: string;
    context_baseline?: string;
    presentation?: string | null;
  };
  reproducibility?: Reproducibility;
  quality: {
    overall_confidence: Confidence;
    history_tier: "limited" | "normal";
    missing_data_flags: string[];
    partial: boolean;
    warnings: string[];
    available_elements: number;
    limited_elements: number;
    unavailable_elements: number;
    qualified_patterns: number;
  };
  elements: BehaviorElement[];
  patterns: BehaviorPattern[];
  highlights: { element_keys: string[]; pattern_keys: string[] };
  hero_portfolio: HeroPortfolio;
  story: { version: string; ordered_pages: string[] };
  pages: StoryPage[];
  shares: {
    final: {
      display_name: string | null;
      strongest_elements: ShareElement[];
      strongest_patterns: SharePattern[];
      hero_portfolio: {
        common_thread: string | null;
        exception_hero: string | null;
        pool_direction: string | null;
      };
      hero_mirror: { hero_id: number; hero_name: string } | null;
    };
    privacy_defaults: { show_name: boolean; show_avatar: boolean; show_raw_id: false };
  };
  deep_dive: { available: boolean; cta_label: string; href: string; copy: string };
  methodology: {
    free_summary_only: true;
    session_gap_minutes: number;
    session_policy_version: string;
    notes: string[];
  };
  cost: {
    history_requests: number;
    detail_requests: 0;
    parse_requests: 0;
    parse_status_requests: number;
    cache_hits: number;
    estimated_cost_units: number;
  };
};

export type FreeDnaReport = FreeDnaReportV4;
export type FreeDnaReportV5 = FreeDnaReportV4;

export async function createAnalysis(
  baseUrl: string,
  input: CreateAnalysisRequest
): Promise<CreateAnalysisResponse> {
  const response = await fetch(baseUrl + "/v1/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { message?: string };
    throw new Error(body.message ?? "Unable to create analysis");
  }
  return response.json() as Promise<CreateAnalysisResponse>;
}
