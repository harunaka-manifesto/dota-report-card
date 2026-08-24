"use client";

import { FormEvent, useState } from "react";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { track } from "../lib/analytics";

// Browser requests stay on the web origin. The Next.js server proxies /v1 to
// the private API_BASE_URL, so the OpenDota credential and API topology never
// become browser configuration.
const API_BASE_URL = "";

type AnalysisStatus = {
  job_id: string;
  status: string;
  stage: string;
  warnings: string[];
  report_id: string | null;
  failure_code: string | null;
  message: string | null;
  completed_stages?: string[];
};

const POLL_TIMEOUT_MS = 5 * 60 * 1000;
const INITIAL_POLL_DELAY_MS = 1200;
const MAX_POLL_DELAY_MS = 10_000;

export default function AnalysisForm() {
  const router = useRouter();
  const [player, setPlayer] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      controllerRef.current?.abort();
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = player.trim();
    if (!value) {
      setError("Enter a public OpenDota profile, Steam ID, or Steam profile URL.");
      return;
    }
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setBusy(true);
    setError(null);
    setStatus(null);
    track("identity.input_submitted.v1", { input_type: classifyInput(value) });
    try {
      const response = await fetch(API_BASE_URL + "/v1/analyses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player: value, refresh: false, mode: "free" }),
        signal: controller.signal
      });
      const body = await readResponseBody(response);
      if (!response.ok) {
        throw new Error(
          typeof body.message === "string" ? body.message : "The analysis could not be queued."
        );
      }
      const jobId = typeof body.job_id === "string" ? body.job_id : null;
      if (!jobId) throw new Error("The analysis did not return a job ID.");
      track("analysis.started.v1", { reused: body.reused === true, input_type: classifyInput(value), mode: "free" });
      const events = streamEvents(jobId, controller.signal, (event) => {
        if (!mountedRef.current || !event.stage) return;
        const stage = event.stage;
        setStatus((current) => ({
          ...(current ?? {
            job_id: jobId,
            status: event.status ?? "running",
            stage,
            warnings: [],
            report_id: null,
            failure_code: null,
            message: null
          }),
          status: event.status ?? current?.status ?? "running",
          stage
        }));
        track("analysis.stage.v1", { stage: event.stage, status: event.status ?? "running" });
      });
      let pollError: unknown = null;
      try {
        try {
          await poll(jobId, controller.signal);
        } catch (caught) {
          pollError = caught;
          throw caught;
        }
      } finally {
        controller.abort();
        try {
          await events;
        } catch (caught) {
          if (!pollError && !(caught instanceof DOMException && caught.name === "AbortError")) throw caught;
        }
      }
    } catch (caught) {
      if (!mountedRef.current || (caught instanceof DOMException && caught.name === "AbortError")) return;
      setError(caught instanceof Error ? caught.message : "The analysis could not be queued.");
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }

  async function poll(jobId: string, signal: AbortSignal) {
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    let delay = INITIAL_POLL_DELAY_MS;
    let firstRequest = true;
    while (Date.now() < deadline) {
      await waitUntilVisible(signal);
      if (!firstRequest) await wait(delay, signal);
      firstRequest = false;
      const response = await fetch(API_BASE_URL + "/v1/analyses/" + jobId, {
        cache: "no-store",
        signal
      });
      const body = await readResponseBody(response);
      if (!response.ok) {
        throw new Error(
          typeof body.message === "string" ? body.message : "The analysis status could not be loaded."
        );
      }
      if (typeof body.status !== "string" || typeof body.stage !== "string") {
        throw new Error("The analysis returned an invalid status response.");
      }
      const status = body as unknown as AnalysisStatus;
      setStatus(status);
      track("analysis.stage.v1", { stage: status.stage, status: status.status });
      if (status.status === "completed" && status.report_id) {
        router.push("/report/" + status.report_id);
        return;
      }
      if (status.status === "failed") {
        throw new Error(status.message ?? status.failure_code ?? "The analysis failed.");
      }
      delay = Math.min(Math.round(delay * 1.5), MAX_POLL_DELAY_MS);
    }
    throw new Error("The analysis is taking longer than expected. Please try again.");
  }

  const statusMessage = status ? stageCopy(status.stage) : "Opening your public profile.";

  return (
    <form className={`lookup${busy ? " is-busy" : ""}`} onSubmit={submit} aria-busy={busy}>
      <label className="lookup-label" htmlFor="player">
        Public profile, Steam ID, or Steam profile URL
      </label>
      <div className="lookup-row">
        <input
          id="player"
          name="player"
          aria-label="OpenDota profile or Steam32 ID"
          aria-describedby="player-hint"
          value={player}
          onChange={(event) => setPlayer(event.target.value)}
          placeholder="193875165"
          autoComplete="off"
          required
        />
        <button className="lookup-submit" type="submit" disabled={busy}>
          {busy ? "Reading your pattern…" : "Build report"}
        </button>
      </div>
      <p className="lookup-hint" id="player-hint">
        Try 193875165 if you want to take it for a spin.
      </p>
      {busy && (
        <section className="lookup-status" aria-live="polite" aria-atomic="true">
          <span className="lookup-status-kicker">Free DNA / Reading</span>
          <h2>Finding the shape in your matches.</h2>
          <div className="lookup-status-track" aria-hidden="true"><span /></div>
          <p className="lookup-status-message">
            <span className="lookup-status-pulse" aria-hidden="true" />
            {statusMessage}
          </p>
        </section>
      )}
      {status && !busy && <p className="status lookup-stage-status" aria-live="polite">{statusMessage}</p>}
      {error && <p className="error lookup-error" role="alert">{error}</p>}
    </form>
  );
}

async function streamEvents(
  jobId: string,
  signal: AbortSignal,
  onEvent: (event: { stage: string; status?: string }) => void
): Promise<void> {
  try {
    const response = await fetch(API_BASE_URL + "/v1/analyses/" + jobId + "/events", {
      cache: "no-store",
      signal,
      headers: { Accept: "text/event-stream" }
    });
    if (!response.ok || !response.body) return;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() ?? "";
      for (const chunk of chunks) {
        const line = chunk.split("\n").find((item) => item.startsWith("data:"));
        if (!line) continue;
        try {
          const event = JSON.parse(line.slice(5).trim()) as { stage?: string; status?: string };
          if (event.stage) {
            onEvent({ stage: event.stage, status: event.status });
            window.dispatchEvent(new CustomEvent("dota-report-analysis-stage", { detail: event }));
          }
        } catch {
          // Polling remains the authoritative fallback when an event chunk is partial.
        }
      }
    }
  } catch {
    // The visibility-aware status poll below is the supported fallback.
  }
}

function stageCopy(stage: string): string {
  const copy: Record<string, string> = {
    resolving_player: "Finding your public profile.",
    player_found: "Your player is in view.",
    fetching_history: "Looking through your recent matches.",
    filtering_matches: "Finding the moments that repeat.",
    normalizing_history: "Finding the moments that repeat.",
    feature_extraction: "Turning match history into habits.",
    hero_features: "Looking for the heroes that feel like you.",
    role_features: "Reading how you show up in a role.",
    session_inference: "Noticing how your sessions change shape.",
    dimension_scoring: "Giving your Elements a name.",
    behavior_elements: "Arranging your Elements.",
    behavior_patterns: "Connecting the Patterns.",
    hero_portfolio: "Building your Hero Portfolio.",
    rendering_report: "Putting your Dota shape together.",
    completed: "Your pattern is ready.",
    failed: "Analysis failed. We couldn't finish the read."
  };
  return copy[stage] ?? "Reading the next part of your pattern.";
}

function classifyInput(value: string): string {
  if (/^\d+$/.test(value)) return value.length > 10 ? "steam64" : "steam32";
  if (value.includes("/id/")) return "steam_vanity_url";
  if (value.includes("/profiles/")) return "steam_profile_url";
  if (value.includes("opendota")) return "opendota_url";
  return "other_url";
}

async function readResponseBody(response: Response): Promise<Record<string, unknown>> {
  try {
    const body = await response.json();
    return body && typeof body === "object" ? body as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

function wait(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, milliseconds);
    const abort = () => {
      window.clearTimeout(timer);
      reject(new DOMException("The request was aborted.", "AbortError"));
    };
    if (signal.aborted) {
      abort();
      return;
    }
    signal.addEventListener("abort", abort, { once: true });
    window.setTimeout(() => signal.removeEventListener("abort", abort), milliseconds);
  });
}

function waitUntilVisible(signal: AbortSignal): Promise<void> {
  if (!document.hidden) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const onVisibility = () => {
      if (!document.hidden) {
        document.removeEventListener("visibilitychange", onVisibility);
        signal.removeEventListener("abort", onAbort);
        resolve();
      }
    };
    const onAbort = () => {
      document.removeEventListener("visibilitychange", onVisibility);
      reject(new DOMException("The request was aborted.", "AbortError"));
    };
    document.addEventListener("visibilitychange", onVisibility);
    signal.addEventListener("abort", onAbort, { once: true });
    if (signal.aborted) onAbort();
    onVisibility();
  });
}
