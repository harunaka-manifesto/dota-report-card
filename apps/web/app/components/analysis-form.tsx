"use client";

import { FormEvent, useState } from "react";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type AnalysisStatus = {
  job_id: string;
  status: string;
  stage: string;
  warnings: string[];
  report_id: string | null;
  failure_code: string | null;
  message: string | null;
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
      setError("Enter a public OpenDota profile or Steam32 account ID.");
      return;
    }
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const response = await fetch(API_BASE_URL + "/v1/analyses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player: value, refresh: false }),
        signal: controller.signal
      });
      const body = await readResponseBody(response);
      if (!response.ok) throw new Error(body.message ?? "The analysis could not be queued.");
      if (!body.job_id) throw new Error("The analysis did not return a job ID.");
      await poll(body.job_id, controller.signal);
    } catch (caught) {
      if (controller.signal.aborted || !mountedRef.current) return;
      setError(caught instanceof Error ? caught.message : "The analysis could not be queued.");
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }

  async function poll(jobId: string, signal: AbortSignal) {
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    let delay = INITIAL_POLL_DELAY_MS;
    while (Date.now() < deadline) {
      await waitUntilVisible(signal);
      const response = await fetch(API_BASE_URL + "/v1/analyses/" + jobId, {
        cache: "no-store",
        signal
      });
      const body = (await readResponseBody(response)) as Partial<AnalysisStatus>;
      if (!response.ok) {
        throw new Error(body.message ?? "The analysis status could not be loaded.");
      }
      if (typeof body.status !== "string" || typeof body.stage !== "string") {
        throw new Error("The analysis returned an invalid status response.");
      }
      const status = body as AnalysisStatus;
      setStatus(status);
      if (status.status === "completed" && status.report_id) {
        router.push("/report/" + status.report_id);
        return;
      }
      if (status.status === "failed") {
        throw new Error(status.message ?? status.failure_code ?? "The analysis failed.");
      }
      await wait(delay, signal);
      delay = Math.min(Math.round(delay * 1.5), MAX_POLL_DELAY_MS);
    }
    throw new Error("The analysis is taking longer than expected. Please try again.");
  }

  return (
    <form className="lookup" onSubmit={submit}>
      <label htmlFor="player">OpenDota profile or Steam32 ID</label>
      <div className="lookup-row">
        <input
          id="player"
          name="player"
          value={player}
          onChange={(event) => setPlayer(event.target.value)}
          placeholder="193875165"
          autoComplete="off"
          required
        />
        <button type="submit" disabled={busy}>
          {busy ? "Reading matches…" : "Build report"}
        </button>
      </div>
      <p className="hint">Try 193875165 for the recorded sample account.</p>
      {status && <p className="status" aria-live="polite">{status.stage.replaceAll("_", " ")}.</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  );
}

async function readResponseBody(response: Response): Promise<Record<string, any>> {
  try {
    const body = await response.json();
    return body && typeof body === "object" ? body as Record<string, any> : {};
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
