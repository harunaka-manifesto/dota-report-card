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
