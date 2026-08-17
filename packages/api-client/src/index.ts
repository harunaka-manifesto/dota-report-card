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

export type DimensionKey =
  | "breadth"
  | "role"
  | "adaptability"
  | "activity"
  | "orientation"
  | "resilience"
  | "endurance"
  | "rhythm";

export type Confidence = "low" | "moderate" | "high" | "unavailable";
export type DimensionStatus = "available" | "limited" | "unavailable";

export type Evidence = {
  key: string;
  value: number | string | null;
  unit: string;
  denominator: number;
};

export type DimensionCopy = {
  headline_key: string;
  receipt_key: string;
  receipt_params: Record<string, string | number | boolean>;
  left_label: string | null;
  right_label: string | null;
};

export type DnaDimension = {
  key: DimensionKey;
  status: DimensionStatus;
  score: number | null;
  centered_score: number | null;
  label: string | null;
  confidence: Confidence;
  confidence_score: number;
  sample_size: number;
  effective_sample_size: number;
  coverage: number;
  evidence: Evidence[];
  confounders: string[];
  missing_reasons: string[];
  copy: DimensionCopy | null;
  methodology_version: string;
  descriptor_eligible: boolean;
};

export type Descriptor = {
  key: string;
  label: string;
  dimension: string;
};

export type Archetype = {
  key: string;
  label: string;
  fit: number;
  runner_up: { key: string; fit: number } | null;
  descriptors: [Descriptor, Descriptor, Descriptor];
  contributing_dimensions: Array<{ key: string; weight: number; contribution: number }>;
  confidence: "low" | "moderate" | "high";
  explanation_evidence: string[];
  classifier_version: string;
};

export type HeroCard = {
  hero_id: number;
  name: string;
  portrait_url: string | null;
  score: number;
  component_scores: Record<string, number>;
  matches: number;
  roles: string[];
  traits: string[];
  receipts: string[];
  reason_key: string;
  confidence: "low" | "moderate" | "high";
  portrait_asset_version: string;
};

export type HeroPattern = {
  key: string;
  label: string;
  copy_key: string;
  traits: string[];
  role_traits: string[];
  contributors: string[];
  scores?: Record<string, number>;
};

export type HeroRecommendation = {
  hero_id: number;
  name: string;
  portrait_url: string | null;
  portrait_asset_version: string;
  fit_band: "strong" | "good" | "exploratory";
  score: number;
  familiar_traits: string[];
  new_traits: string[];
  plausible_roles: string[];
  role_change: boolean;
  reason_key: string;
  recommendation_version: string;
};

export type Heroes = {
  signature: HeroCard | null;
  comfort_picks: HeroCard[];
  patterns: HeroPattern[];
  recommendations: HeroRecommendation[];
  taxonomy_version: string | null;
  limitations: string[];
  identity_version: string;
};

export type FindingKind =
  | "thesis"
  | "strength"
  | "contradiction"
  | "edge"
  | "leak"
  | "trajectory"
  | "identity";

export type FindingConfidence = "limited" | "moderate" | "high";

export type FindingReceipt = {
  key: string;
  label: string;
  value: string;
  context: string | null;
  confidence: FindingConfidence;
};

export type FindingExperiment = {
  key: string;
  title: string;
  instruction: string;
  hypothesis: string;
  measurement: string;
  window: string;
};

export type PublicFinding = {
  key: string;
  kind: FindingKind;
  headline: string;
  body: string;
  interpretation: string | null;
  confidence: FindingConfidence;
  receipts: FindingReceipt[];
  related_dimensions: DimensionKey[];
  related_heroes: number[];
  experiment: FindingExperiment | null;
  share_copy: string | null;
};

export type StoryPageV1 = {
  id: string;
  kind:
    | "input"
    | "player_found"
    | "analysis"
    | "reveal"
    | "section_intro"
    | "dimension"
    | "archetype"
    | "summary"
    | "signature_hero"
    | "comfort"
    | "hero_pattern"
    | "recommendations"
    | "final_card"
    | "deep_dive";
  section: "intro" | "dna" | "heroes" | "finale";
  title: string;
  body: string | null;
  evidence_keys: string[];
};

export type StoryPageV2 = {
  id: string;
  kind:
    | "input"
    | "player_found"
    | "analysis"
    | "reveal"
    | "finding"
    | "experiment"
    | "identity_card"
    | "dna_xray"
    | "deep_dive";
  section: "intro" | "findings" | "dna" | "finale";
  title: string;
  body: string | null;
  evidence_keys: string[];
  finding_key?: string | null;
  experiment_key?: string | null;
};

export type StoryPage = StoryPageV1 | StoryPageV2;

export type ShareDimension = {
  key: DimensionKey;
  label: string | null;
  score: number | null;
  centered_score: number | null;
  confidence: Confidence;
};

export type ShareCommon = {
  archetype: string;
  descriptors: Descriptor[];
  match_count: number;
};

export type FindingShare = {
  finding_key: string | null;
  headline: string;
  archetype: string | null;
  receipts: string[];
};

export type SharesV1 = {
  dna: ShareCommon & { spectra: ShareDimension[] };
  heroes: {
    signature: HeroCard | null;
    comfort: HeroCard[];
    pattern: HeroPattern | null;
    recommendations: HeroRecommendation[];
  };
  final: ShareCommon & {
    display_name: string;
    signature: string | null;
    pattern: string | null;
    rhythm: string | null;
  };
  privacy_defaults: {
    show_name: boolean;
    show_avatar: boolean;
    show_raw_id: false;
  };
};

export type Shares = SharesV1 & {
  identity?: FindingShare;
  exposed?: FindingShare;
  strength?: FindingShare;
};

export type ReportVersionsV1 = {
  eligibility: string;
  sessions: string;
  features: string;
  dna_scoring: string;
  baselines: string;
  archetype: string;
  hero_identity: string;
  hero_taxonomy: string;
  recommendations: string;
  copy: string;
  model: string;
  template: string;
  share_renderer: string;
  analysis_version_fingerprint: string;
};

export type ReportVersionsV2 = ReportVersionsV1 & {
  findings: string;
  finding_ranking: string;
  story: string;
};

export type FreeDnaReportBase = {
  report_id?: string;
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
  versions: ReportVersionsV1 | ReportVersionsV2;
  quality: {
    overall_confidence: "low" | "moderate" | "high";
    history_tier: "limited" | "normal";
    missing_data_flags: string[];
    partial: boolean;
    warnings: string[];
  };
  dimensions: DnaDimension[];
  archetype: Archetype;
  heroes: Heroes;
  shares: Shares;
  deep_dive: {
    available: boolean;
    cta_label: string;
    href: string;
    copy: string;
  };
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

export type FreeDnaReportV1 = FreeDnaReportBase & {
  schema_version: "free-dna-report-1.0.0";
  versions: ReportVersionsV1;
  pages: StoryPageV1[];
  shares: SharesV1;
};

export type StoryDefinition = {
  version: string;
  thesis_key: string | null;
  strength_key: string | null;
  contradiction_key: string | null;
  edge_key: string | null;
  leak_key: string | null;
  experiment_key: string | null;
  ordered_pages: string[];
};

export type FreeDnaReportV2 = FreeDnaReportBase & {
  schema_version: "free-dna-report-2.0.0";
  versions: ReportVersionsV2;
  findings: PublicFinding[];
  story: StoryDefinition;
  pages: StoryPageV2[];
  shares: SharesV1 & {
    identity: FindingShare;
    exposed: FindingShare;
    strength: FindingShare;
  };
};

export type BehaviorDimensionKey =
  | "hero_identity"
  | "role_identity"
  | "combat_expression"
  | "economy"
  | "map_objectives"
  | "risk_survival"
  | "adaptability"
  | "consistency_form"
  | "session_response"
  | "progression";

export type BehaviorConfidence = "low" | "moderate" | "high" | "unavailable";

export type BehaviorDimension = {
  key: BehaviorDimensionKey;
  label: string;
  element_keys: string[];
  qualified_pattern_keys: string[];
  available_elements: number;
  total_free_elements: number;
  confidence: BehaviorConfidence;
};

export type BehaviorElementReceipt = {
  key: string;
  value: string;
  unit: string;
  denominator: number;
  coverage: number;
  confidence_score: number;
  comparison: string | null;
};

export type BehaviorElement = {
  key: string;
  label: string;
  dimension_key: BehaviorDimensionKey;
  status: "available" | "limited" | "unavailable";
  score: number | null;
  centered_score: number | null;
  axis: { left: string | null; right: string | null };
  confidence: BehaviorConfidence;
  confidence_score: number;
  sample_size: number;
  effective_sample_size: number;
  coverage: number;
  receipts: BehaviorElementReceipt[];
  confounders: string[];
  missing_reasons: string[];
  methodology_version: string;
};

export type BehaviorPattern = {
  key: string;
  label: string;
  kind: "identity" | "contradiction" | "edge" | "leak" | "trajectory" | "style";
  strength: number;
  confidence: BehaviorConfidence;
  confidence_score: number;
  element_keys: string[];
  receipts: BehaviorElementReceipt[];
  confounders: string[];
};

export type ContextArchetype = {
  group_key: string;
  group_label: string;
  key: string;
  label: string;
  fit: number;
  confidence: BehaviorConfidence;
  runner_up: { key: string; fit: number } | null;
  descriptors: Descriptor[];
  contributing_element_keys: string[];
  contributing_pattern_keys: string[];
  explanation_evidence: string[];
  classifier_version: string;
};

export type BehaviorFinding = {
  key: string;
  kind: "identity" | "contradiction" | "edge" | "leak" | "trajectory" | "style" | "strength";
  headline: string;
  body: string;
  interpretation: string;
  confidence: "low" | "moderate" | "high";
  confidence_score: number;
  source_pattern_keys: string[];
  supporting_element_keys: string[];
  archetype_group_keys: string[];
  receipts: FindingReceipt[];
  experiment: FindingExperiment | null;
  share_copy: string | null;
  limitations: string[];
};

export type StoryPageV3 = {
  id: string;
  kind: "reveal" | "summary" | "finding" | "experiment" | "archetypes" | "dna_xray" | "heroes" | "deep_dive";
  section: "intro" | "findings" | "dna" | "heroes" | "finale";
  title: string;
  body: string | null;
  evidence_keys: string[];
  finding_key?: string | null;
  experiment_key?: string | null;
};

export type ReportVersionsV3 = ReportVersionsV2 & {
  behavior_model: string;
  dimension_registry: string;
  element_registry: string;
  pattern_registry: string;
  archetype_registry: string;
  finding_registry: string;
};

export type FreeDnaReportV3 = Omit<FreeDnaReportBase, "versions" | "quality" | "dimensions" | "archetype" | "shares"> & {
  schema_version: "free-dna-report-3.0.0";
  versions: ReportVersionsV3;
  quality: {
    overall_confidence: BehaviorConfidence;
    history_tier: "limited" | "normal";
    missing_data_flags: string[];
    partial: boolean;
    warnings: string[];
    available_elements: number;
    limited_elements: number;
    unavailable_elements: number;
    qualified_patterns: number;
  };
  dimensions: BehaviorDimension[];
  elements: BehaviorElement[];
  patterns: BehaviorPattern[];
  archetypes: ContextArchetype[];
  findings: BehaviorFinding[];
  story: {
    version: string;
    thesis_key: string | null;
    strongest_key: string | null;
    experiment_key: string | null;
    ordered_pages: string[];
  };
  pages: StoryPageV3[];
  shares: {
    identity: { finding_key: string | null; headline: string; archetype_groups: string[]; receipts: string[] };
    strongest: { finding_key: string | null; headline: string; archetype_groups: string[]; receipts: string[] };
    pattern: { finding_key: string | null; headline: string; archetype_groups: string[]; receipts: string[] };
    archetypes: ContextArchetype[];
    privacy_defaults: { show_name: boolean; show_avatar: boolean; show_raw_id: false };
  };
};

export type FreeDnaReport = FreeDnaReportV1 | FreeDnaReportV2 | FreeDnaReportV3;

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
