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

export type StoryPage = {
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

export type Shares = {
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

export type FreeDnaReport = {
  report_id?: string;
  schema_version: "free-dna-report-1.0.0";
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
  pages: StoryPage[];
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
