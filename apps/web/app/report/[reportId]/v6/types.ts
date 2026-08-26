/**
 * The v6 renderer deliberately owns its contract instead of widening the v4
 * client type.  The API can add fields to these records without requiring a
 * v5 snapshot or renderer migration.
 */

export type V6ConfidenceTier = "high" | "moderate" | "descriptive" | "suppressed" | "unavailable" | string;
export type V6Availability = "available" | "limited" | "suppressed" | "unavailable" | string;

export type V6Interval = {
  lower?: number | null;
  upper?: number | null;
  confidence?: number | null;
  level?: number | null;
};

export type V6Metric = {
  estimate?: number | V6Metric | null;
  value?: number | null;
  unit?: string | null;
  interval_95?: V6Interval | [number | null, number | null] | null;
  interval?: V6Interval | [number | null, number | null] | null;
  zone?: string | null;
  direction?: string | null;
  stability?: number | null;
  bootstrap_stability?: number | null;
  sample_size?: number | null;
  independent_sessions?: number | null;
  independent_session_count?: number | null;
  coverage?: number | null;
  confidence?: V6ConfidenceTier | null;
  evidence_refs?: string[];
  limitations?: string[];
};

export type V6EvidenceReference = {
  id?: string;
  key?: string;
  label?: string;
  observation?: string | null;
  metric?: V6Metric | null;
  source?: string | null;
  references?: string[];
};

export type V6Recommendation = {
  recommendation_id?: string;
  id?: string;
  title?: string | null;
  label?: string | null;
  instruction?: string | null;
  rationale?: string | null;
  body?: string | null;
  action?: string | null;
  context?: Record<string, unknown> | string | null;
  family?: string | null;
  supported_metric_keys?: string[];
  evidence_refs?: string[];
  causal?: boolean;
  identity_updated?: boolean;
  baseline_locked_on_commit?: boolean;
  version?: string | null;
  evidence_requirement?: string | null;
  verification_rule?: string | null;
  target?: string | null;
  options?: V6Choice[];
};

export type V6Choice = {
  id?: string;
  key?: string;
  label: string;
  description?: string | null;
  value?: string | null;
};

export type V6Element = {
  key: string;
  label: string;
  description?: string | null;
  status?: V6Availability;
  metric?: V6Metric | null;
  estimate?: number | V6Metric | null;
  value?: number | null;
  unit?: string | null;
  interval_95?: V6Interval | [number | null, number | null] | null;
  interval?: V6Interval | [number | null, number | null] | null;
  zone?: string | null;
  direction?: string | null;
  confidence?: V6ConfidenceTier | null;
  bootstrap_stability?: number | null;
  sample_size?: number | null;
  independent_sessions?: number | null;
  independent_session_count?: number | null;
  coverage?: number | null;
  evidence_refs?: string[];
  evidence?: V6EvidenceReference[];
  limitations?: string[];
  supported_claims?: string[];
  forbidden_claims?: string[];
};

export type V6ComparisonRow = {
  key?: string;
  label: string;
  value?: string | number | null;
  estimate?: number | null;
  unit?: string | null;
  interval_95?: V6Interval | [number | null, number | null] | null;
  evidence_ref?: string | null;
  direction?: string | null;
};

export type V6Comparison = {
  title?: string | null;
  context_label?: string | null;
  contexts?: V6ComparisonRow[];
  rows?: V6ComparisonRow[];
  positive?: V6ComparisonRow[];
  negative?: V6ComparisonRow[];
  control?: V6ComparisonRow[];
  note?: string | null;
};

export type V6ClaimLayers = {
  claim?: string | null;
  observation?: string | null;
  evidence?: string | null;
  interpretation?: string | null;
  recommendation?: string | V6Recommendation | null;
  recommendation_detail?: V6Recommendation | null;
  alternatives?: string[];
  verification?: {
    eligibility_games?: number;
    primary_metric?: string;
    guardrail_metric?: string;
    causal?: boolean;
    abstention?: string;
  } | null;
  interaction?: string | null;
  deep_handoff?: {
    cohort_reference?: string;
    unanswered_alternatives?: string[];
  } | null;
};

export type V6Finding = {
  id?: string;
  key?: string;
  family: string;
  label?: string | null;
  title?: string | null;
  status?: V6Availability;
  direction?: string | null;
  confidence?: V6ConfidenceTier | null;
  metric?: V6Metric | null;
  estimate?: number | V6Metric | null;
  value?: number | null;
  unit?: string | null;
  interval_95?: V6Interval | [number | null, number | null] | null;
  interval?: V6Interval | [number | null, number | null] | null;
  zone?: string | null;
  sample_size?: number | null;
  independent_sessions?: number | null;
  independent_session_count?: number | null;
  coverage?: number | null;
  bootstrap_stability?: number | null;
  stability?: number | null;
  claim?: string | null;
  observation?: string | null;
  evidence?: string | V6EvidenceReference[] | null;
  evidence_text?: string | null;
  interpretation?: string | null;
  recommendation?: string | V6Recommendation | null;
  outcome_key?: string | null;
  raw_p_value?: number | null;
  adjusted_q_value?: number | null;
  claim_contract?: V6ClaimLayers | null;
  layers?: V6ClaimLayers | null;
  evidence_refs?: string[];
  evidence_items?: V6EvidenceReference[];
  comparison?: V6Comparison | null;
  limitations?: string[];
  diagnostic_question_id?: string | null;
  share_eligible?: boolean;
  share_blockers?: string[];
  published?: boolean;
  blocking_confounders?: string[];
  semantic_outcome_key?: string | null;
  hypothesis_branch?: string | null;
  branch_adjusted_q_value?: number | null;
  estimator_version?: string | null;
  interaction?: {
    kind?: V61InteractionKind | null;
    enabled?: boolean;
    fallback?: string | null;
  } | null;
};

export type V6IdentitySummary = {
  status?: V6Availability;
  state?: V6Availability;
  headline?: string | null;
  title?: string | null;
  supporting_lines?: string[];
  support?: string[];
  body?: string | null;
  confidence?: V6ConfidenceTier | null;
  evidence_refs?: string[];
  common_thread?: string | null;
  options?: V6Choice[];
  slots?: {
    version?: string;
    primary?: V61IdentitySlot | null;
    twist?: V61IdentitySlot | null;
    anchor?: V61IdentitySlot | null;
    compatibility?: string;
    compatibility_checks?: Record<string, boolean>;
  } | null;
};

export type V61IdentitySlot = {
  kind?: "PRIMARY" | "TWIST" | "ANCHOR";
  scope?: string | null;
  text?: string | null;
  family?: string | null;
  semantic_outcome_key?: string | null;
  evidence_refs?: string[];
};

export type V61InteractionKind =
  | "core_boundary"
  | "after_x"
  | "two_versions"
  | "contradiction_reveal"
  | "session_curve"
  | "variance_decomposition"
  | "identity_eras"
  | "hero_lifecycle"
  | "behavioral_loop";

export type V6TimelinePoint = {
  id?: string;
  label: string;
  period?: string | null;
  start?: string | null;
  end?: string | null;
  position?: number | null;
  summary?: string | null;
  evidence?: string | null;
  observed?: Record<string, unknown> | null;
};

export type V6HeroMirror = {
  status?: V6Availability;
  hero_id?: number | null;
  hero_name?: string | null;
  title?: string | null;
  headline?: string | null;
  body?: string | null;
  similarity?: V6Metric | null;
  similarity_score?: number | null;
  player_behavior?: Record<string, string>;
  hero_behavior?: Record<string, string>;
  evidence_refs?: string[];
  limitations?: string[];
  share_eligible?: boolean;
};

export type V6HeroRow = {
  id?: number | null;
  hero_id?: number | null;
  name?: string | null;
  hero_name?: string | null;
  display_name?: string | null;
  match_count?: number | null;
  share?: number | null;
  functional_jobs?: string[];
  jobs?: string[];
  band?: string | null;
  layer?: string | null;
};

export type V6HeroPortfolio = {
  prediction?: {
    prompt?: string | null;
    options?: V6Choice[];
    answer?: string | null;
    reveal?: string | null;
    observed?: string | null;
  } | null;
  evolution?: {
    title?: string | null;
    body?: string | null;
    points?: V6TimelinePoint[];
    timeline?: V6TimelinePoint[];
    selected?: V6TimelinePoint | null;
    evidence_refs?: string[];
    limitations?: string[];
  } | null;
  timeline?: V6TimelinePoint[];
  mirror?: V6HeroMirror | null;
  hero_mirror?: V6HeroMirror | null;
  heroes?: V6HeroRow[];
  share_candidates?: V6ShareCandidate[];
};

export type V6StoryBeat = {
  id?: string;
  key?: string;
  index?: number;
  kind?: string;
  status?: V6Availability;
  title?: string | null;
  eyebrow?: string | null;
  body?: string | null;
  prompt?: string | null;
  interaction?: string | null;
  order?: number;
  available?: boolean;
  payload_refs?: string[];
  content?: Record<string, unknown> | null;
  options?: V6Choice[];
  copy?: Record<string, string | null> | null;
  evidence_refs?: string[];
  skippable?: boolean;
};

export type V6Story = {
  version?: string;
  ordered_beats?: string[];
  beats?: V6StoryBeat[];
};

export type V6ShareCandidate = {
  id?: string;
  candidate_id?: string;
  kind?: string;
  title?: string | null;
  headline?: string | null;
  body?: string | null;
  reason?: string | null;
  status?: V6Availability;
  eligible?: boolean;
  blockers?: string[];
  blocking_reasons?: string[];
  blocking_confounders?: string[];
  payload?: Record<string, unknown>;
  evidence_refs?: string[];
  image_url?: string | null;
};

export type V6DiagnosticQuestion = {
  id?: string;
  question_id?: string;
  label?: string;
  question?: string | null;
  prompt?: string | null;
  body?: string | null;
  context?: string | null;
  family?: string;
  finding_family?: string;
  evidence_refs?: string[];
  eligibility?: V6Availability;
  statement?: string | null;
  primary_hypothesis?: Record<string, unknown> | null;
  secondary_hypothesis?: Record<string, unknown> | null;
  required_summary_metrics?: string[];
  required_detail_metrics?: string[];
  required_parse_metrics?: string[];
  options?: V6Choice[];
  observed?: Record<string, unknown> | null;
  available?: boolean;
  offered?: boolean;
  confidence?: V6ConfidenceTier;
  blocking_confounders?: string[];
  skippable?: boolean;
  question_spec?: Record<string, unknown> | null;
};

export type V6Report = {
  report_id?: string | null;
  schema_version: "free-dna-report-6.0.0";
  report_variant: "free_dna_report";
  noindex?: true;
  identity: {
    display_name?: string | null;
    avatar_url?: string | null;
  };
  metadata?: {
    created_at?: string;
    expires_at?: string | null;
    data_from?: string | null;
    data_to?: string | null;
    processed_matches?: number;
    eligible_matches?: number;
    history_tier?: string;
  };
  versions?: Record<string, string | null | undefined>;
  reproducibility?: Record<string, unknown>;
  quality?: {
    overall_confidence?: V6ConfidenceTier;
    history_tier?: string;
    missing_data_flags?: string[];
    partial?: boolean;
    warnings?: string[];
    available_elements?: number;
    limited_elements?: number;
    unavailable_elements?: number;
    published_findings?: number;
  };
  elements: V6Element[];
  findings: V6Finding[];
  identity_summary: V6IdentitySummary;
  hero_portfolio: V6HeroPortfolio;
  diagnostic_questions: V6DiagnosticQuestion[];
  story: V6Story | V6StoryBeat[];
  pages?: V6StoryBeat[];
  share_candidates: V6ShareCandidate[];
  methodology?: {
    notes?: string[];
    limitations?: string[];
    free_summary_only?: boolean;
    claims?: Record<string, unknown>;
  };
  cost?: {
    history_requests?: number;
    detail_requests?: number;
    parse_requests?: number;
    estimated_cost_units?: number;
  };
};

export type V61Report = Omit<V6Report, "schema_version" | "versions" | "reproducibility" | "methodology"> & {
  schema_version: "free-dna-report-6.1.0";
  versions?: Record<string, string | null | undefined>;
  reproducibility?: Record<string, unknown> & {
    history_contract?: Record<string, unknown>;
    request_manifest?: Record<string, unknown>;
    artifact_checksums?: Record<string, string>;
  };
  supporting_evidence: {
    portfolio_shape?: Record<string, unknown>;
    involvement?: Record<string, unknown>;
    finishing?: Record<string, unknown>;
    death_exposure?: Record<string, unknown>;
    transfer_frontier?: Record<string, unknown>;
    consistency?: Record<string, unknown>;
    result_response?: Record<string, unknown>;
    session_curve?: Record<string, unknown>;
  };
  selection_audit: Record<string, unknown>;
  methodology?: Record<string, unknown> & { notes?: string[] };
};

export type V6StoryReport = V6Report | V61Report;

export function isFreeDnaReportV6(value: unknown): value is V6Report {
  if (!value || typeof value !== "object") return false;
  const candidate = value as { schema_version?: unknown; report_variant?: unknown };
  return candidate.schema_version === "free-dna-report-6.0.0" && candidate.report_variant === "free_dna_report";
}

export function isFreeDnaReportV61(value: unknown): value is V61Report {
  if (!value || typeof value !== "object") return false;
  const candidate = value as { schema_version?: unknown; report_variant?: unknown };
  return candidate.schema_version === "free-dna-report-6.1.0" && candidate.report_variant === "free_dna_report";
}

export function reportBeats(report: V6StoryReport): V6StoryBeat[] {
  const source = (Array.isArray(report.story) ? report.story : report.story.beats ?? report.pages ?? []).map((beat, index) => ({
    ...beat,
    id: beat.id ?? beat.key ?? `beat-${index + 1}`,
  }));
  const byId = new Map(source.map((beat) => [beat.id as string, beat]));
  const ordered = Array.isArray(report.story) ? [] : report.story.ordered_beats ?? [];
  const beats = ordered.length > 0 ? ordered.map((id, index) => byId.get(id) ?? { id, index }) : source;
  if (beats.length > 0) return beats.slice(0, 9).map((beat, index) => ({ ...beat, index: beat.index ?? index }));
  return Array.from({ length: 9 }, (_, index) => ({ id: `beat-${index + 1}`, index }));
}

export function firstNonEmpty(...values: Array<string | null | undefined>): string {
  return values.find((value) => typeof value === "string" && value.trim().length > 0)?.trim() ?? "";
}

export function metricFor(item: V6Metric | V6Element | V6Finding | null | undefined): V6Metric {
  if (!item) return {};
  if ("metric" in item && item.metric) return item.metric;
  if ("estimate" in item && item.estimate && typeof item.estimate === "object") return item.estimate;
  const value = item as V6Element | V6Finding;
  return {
    estimate: value.estimate,
    value: value.value,
    unit: value.unit,
    interval_95: value.interval_95 ?? value.interval,
    zone: value.zone,
    direction: value.direction,
    bootstrap_stability: value.bootstrap_stability,
    stability: "stability" in value ? value.stability : undefined,
    sample_size: value.sample_size,
    independent_sessions: value.independent_sessions ?? value.independent_session_count,
    coverage: value.coverage,
    confidence: value.confidence,
    evidence_refs: value.evidence_refs,
    limitations: value.limitations,
  };
}

export function metricInterval(metric: V6Metric | null | undefined): V6Interval | null {
  const interval = metric?.interval_95 ?? metric?.interval;
  if (!interval) return null;
  if (Array.isArray(interval)) return { lower: interval[0], upper: interval[1] };
  return interval;
}

export function metricValue(metric: V6Metric | null | undefined): number | null {
  if (!metric) return null;
  return typeof metric.estimate === "number" ? metric.estimate : typeof metric.value === "number" ? metric.value : null;
}

export function displayConfidence(value: V6ConfidenceTier | null | undefined): string {
  if (!value) return "Not available";
  return value.charAt(0).toUpperCase() + value.slice(1);
}
