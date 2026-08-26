"use client";

/**
 * Token-protected state transport for the v6 story.
 *
 * The access token is intentionally never returned from this module's public
 * state, never included in an analytics payload, and never put in a request
 * URL.  A resume link may contain it in the browser fragment; browsers do not
 * send fragments to the server.
 */

export const V6_INTERACTION_SCHEMA = "report-interactions-1.0.0";

export type V6UserReportedState = {
  identity_estimate?: string;
  hero_pool_prediction?: string;
  combat_expression_estimate?: string;
  recommendation_id?: string;
  commitment?: {
    recommendation_id: string;
    target_games: 5;
    started_at: string;
  };
};

export type V6UiState = {
  identity_revealed?: boolean;
  pool_evolution_position?: number;
  combat_expression_revealed?: boolean;
  strongest_finding_comparison?: string;
  claim_layer?: "claim" | "evidence" | "interpretation" | "recommendation";
  hero_mirror_revealed?: boolean;
  selected_share_candidate?: string;
  diagnostic_question_id?: string;
  follow_up?: {
    cutoff?: string | null;
    eligible_games?: number;
    target_games?: 5;
    status?: string;
  };
};

export type V6InteractionState = {
  schema_version: typeof V6_INTERACTION_SCHEMA;
  current_beat: number;
  completed_beats: number[];
  skipped_beats: number[];
  user_reported: V6UserReportedState;
  /** Presentation progress only; computed observations stay server-owned. */
  ui_state: V6UiState;
};

export type V6InteractionSession = {
  session_id: string;
  revision: number;
  state: V6InteractionState;
  expires_at?: string | null;
  recommendation_baseline?: Record<string, unknown> | null;
  history_cutoff?: number | null;
};

export type V6FollowUpResponse = {
  revision: number;
  status: "progress" | "ready" | "abstained";
  eligible_new_matches: number;
  context_matching_matches: number;
  progress: { completed: number; required: 5; remaining: number };
  comparison: {
    label: "what_changed_in_these_five_games";
    metric: string;
    baseline: number;
    follow_up: number;
    delta: number;
    causal: false;
    identity_updated: false;
  } | null;
  message: string;
  guardrail: "This compares the next five matching games. It does not claim causality or change your Signature.";
  stop_reason: string;
};

type SessionEnvelope = Partial<V6InteractionSession> & {
  access_token?: string;
  token?: string;
  interaction_token?: string;
  accessToken?: string;
  session?: Partial<V6InteractionSession>;
};

export type V6ResumeFragment = {
  sessionId: string;
  token: string;
};

export class V6InteractionError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown = null) {
    super(message);
    this.name = "V6InteractionError";
    this.status = status;
    this.body = body;
  }
}

export class V6RevisionConflictError extends V6InteractionError {
  readonly latest: V6InteractionSession | null;

  constructor(latest: V6InteractionSession | null, body: unknown = null) {
    super("This journey was updated somewhere else.", 412, body);
    this.name = "V6RevisionConflictError";
    this.latest = latest;
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function endpoint(path: string): string {
  return `${API_BASE.replace(/\/$/, "")}${path}`;
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return null;
  return response.json().catch(() => null);
}

function asSession(value: unknown): V6InteractionSession | null {
  if (!value || typeof value !== "object") return null;
  const envelope = value as SessionEnvelope;
  const candidate = envelope.session && typeof envelope.session === "object" ? envelope.session : envelope;
  if (typeof candidate.session_id !== "string" || typeof candidate.revision !== "number" || !candidate.state) return null;
  return {
    session_id: candidate.session_id,
    revision: candidate.revision,
    state: candidate.state as V6InteractionState,
    expires_at: candidate.expires_at ?? null,
    recommendation_baseline: candidate.recommendation_baseline ?? null,
    history_cutoff: candidate.history_cutoff ?? null,
  };
}

function accessToken(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const envelope = value as SessionEnvelope;
  const token = envelope.access_token ?? envelope.token ?? envelope.interaction_token ?? envelope.accessToken;
  return typeof token === "string" && token.length > 0 ? token : null;
}

function authorization(token: string): Record<string, string> {
  // Do not interpolate a token into a URL.  The only transport is this header.
  return { Authorization: `Bearer ${token}` };
}

async function request(path: string, init: RequestInit = {}): Promise<unknown> {
  const response = await fetch(endpoint(path), {
    ...init,
    headers: { Accept: "application/json", ...(init.headers ?? {}) },
    credentials: "omit",
  });
  const body = await parseBody(response);
  if (!response.ok) throw new V6InteractionError("The saved journey could not be updated.", response.status, body);
  return body;
}

export function initialInteractionState(): V6InteractionState {
  return {
    schema_version: V6_INTERACTION_SCHEMA,
    current_beat: 0,
    completed_beats: [],
    skipped_beats: [],
    user_reported: {},
    ui_state: {},
  };
}

export function readResumeFragment(input?: string): V6ResumeFragment | null {
  if (typeof window === "undefined" && input === undefined) return null;
  const hash = input ?? window.location.hash;
  if (!hash || hash === "#") return null;
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const sessionId = params.get("session_id") ?? params.get("interaction_session_id") ?? params.get("session");
  const token = params.get("access_token") ?? params.get("interaction_token") ?? params.get("token");
  if (!sessionId || !token || sessionId.length > 256 || token.length > 1024) return null;
  return { sessionId, token };
}

export function resumeFragment(sessionId: string, token: string): string {
  const params = new URLSearchParams({ session_id: sessionId, access_token: token });
  return `#${params.toString()}`;
}

export function withoutResumeFragment(): void {
  if (typeof window === "undefined") return;
  // Never preserve the access token in the URL after explicit deletion.
  window.history.replaceState(null, document.title, `${window.location.pathname}${window.location.search}`);
}

export async function createInteractionSession(reportId: string, state: V6InteractionState): Promise<{ session: V6InteractionSession; token: string }> {
  const body = await request(`/v1/reports/${encodeURIComponent(reportId)}/interaction-sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state, state_schema_version: V6_INTERACTION_SCHEMA }),
  });
  const session = asSession(body);
  const token = accessToken(body);
  if (!session || !token) throw new V6InteractionError("The saved journey response was incomplete.", 502, body);
  return { session, token };
}

export async function getInteractionSession(sessionId: string, token: string): Promise<V6InteractionSession> {
  const body = await request(`/v1/report-interactions/${encodeURIComponent(sessionId)}`, { headers: authorization(token) });
  const session = asSession(body);
  if (!session) throw new V6InteractionError("The saved journey response was incomplete.", 502, body);
  return session;
}

export async function patchInteractionSession(sessionId: string, token: string, state: V6InteractionState, revision: number): Promise<V6InteractionSession> {
  const response = await fetch(endpoint(`/v1/report-interactions/${encodeURIComponent(sessionId)}`), {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...authorization(token),
      // The API accepts a quoted ETag or a plain revision.  Plain keeps the
      // client compatible with the initial implementation and proxies.
      "If-Match": String(revision),
    },
    credentials: "omit",
    body: JSON.stringify({ state, state_schema_version: V6_INTERACTION_SCHEMA }),
  });
  const body = await parseBody(response);
  if (response.status === 409 || response.status === 412) {
    throw new V6RevisionConflictError(asSession(body), body);
  }
  if (!response.ok) throw new V6InteractionError("The saved journey could not be updated.", response.status, body);
  const session = asSession(body);
  if (!session) throw new V6InteractionError("The saved journey response was incomplete.", 502, body);
  return session;
}

export async function deleteInteractionSession(sessionId: string, token: string): Promise<void> {
  await request(`/v1/report-interactions/${encodeURIComponent(sessionId)}`, { method: "DELETE", headers: authorization(token) });
}

export async function followUpInteractionSession(sessionId: string, token: string): Promise<V6FollowUpResponse> {
  return request(`/v1/report-interactions/${encodeURIComponent(sessionId)}/follow-up`, { method: "POST", headers: authorization(token) }) as Promise<V6FollowUpResponse>;
}

export async function startDeepAnalysis(reportId: string, diagnosticQuestionId: string, sessionId?: string, token?: string | null): Promise<unknown> {
  return request(`/v1/reports/${encodeURIComponent(reportId)}/deep-analyses`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? authorization(token) : {}) },
    body: JSON.stringify({ diagnostic_question_id: diagnosticQuestionId, interaction_session_id: sessionId ?? null }),
  });
}
