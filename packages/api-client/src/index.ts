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

export type DnaDimension = {
  key: "breadth" | "role" | "adaptability" | "activity" | "orientation" | "resilience" | "endurance" | "rhythm";
  status: "available" | "limited" | "unavailable";
  score: number | null;
  centered_score: number | null;
  label: string | null;
  confidence: "high" | "moderate" | "low" | "unavailable";
  confidence_score: number;
  sample_size: number;
  effective_sample_size: number;
  coverage: number;
  evidence: Array<{ key: string; value: number | string; unit: string; denominator: number; source_match_ids?: number[] }>;
  confounders: string[];
  missing_reasons: string[];
  source_match_ids: number[];
};

export type FreeDnaReport = {
  schema_version: "free-dna-report-1.0.0";
  report_variant: "free_player_dna" | "free_dna_report";
  dna_report_variant?: "free_dna_report";
  identity: { display_name: string | null; account_id_masked: string; avatar_url: string | null };
  metadata: { processed_matches: number; eligible_matches: number; raw_payload_hash: string; data_from: string | null; data_to: string | null };
  versions: Record<string, string | null>;
  quality: { overall_confidence: "high" | "moderate" | "low"; partial: boolean; missing_data_flags: string[]; warnings: string[] };
  dimensions: DnaDimension[];
  archetype: { key: string; label: string; fit: number; confidence: string; descriptors: Array<{ key: string; label: string; dimension: string }> };
  heroes: { signature: Record<string, unknown> | null; comfort_picks: Record<string, unknown>[]; patterns: Record<string, unknown>[]; recommendations: Record<string, unknown>[] };
  pages: Array<{ id: string; kind: string; section: string; title: string; body?: string }>;
  shares: Record<string, unknown>;
  deep_dive: { available: boolean; href: string | null; cta_label: string };
  evidence_scope?: Record<string, unknown>;
  cost?: Record<string, unknown>;
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
