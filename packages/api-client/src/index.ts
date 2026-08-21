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
};

export type PatternAction = SamePlaybookAction | ComfortEdgeAction;

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

export type FreeDnaReportV4 = {
  report_id: string | null;
  schema_version: "free-dna-report-4.0.0";
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
    history_limit: number;
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
  };
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
