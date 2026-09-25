export type AnalyticsPayload = Record<string, string | number | boolean | null | undefined>;
export type AnalyticsEvent = AnalyticsPayload & { event: string; schema_version: "1" };

const forbiddenKeys = new Set([
  "account_id",
  "report_id",
  "player",
  "name",
  "personaname",
  "raw_id",
  "url",
  "access_token",
  "hero_id",
  "match_id",
  "protected_cohort_reference",
]);
let collector: ((event: AnalyticsEvent) => void) | null = null;

export function setAnalyticsCollector(next: ((event: AnalyticsEvent) => void) | null): void {
  collector = next;
}

// Vendor-neutral by design.  A provider can be attached at this seam without
// making the report story aware of analytics transport or identity.
export function track(eventName: string, payload: AnalyticsPayload = {}): void {
  if (typeof window === "undefined") return;
  const safePayload = Object.fromEntries(
    Object.entries(payload).filter(([key]) => !forbiddenKeys.has(key.toLowerCase()))
  );
  const detail = { event: eventName, schema_version: "1" as const, ...safePayload };
  collector?.(detail);
  window.dispatchEvent(new CustomEvent("dota-report-analytics", { detail }));
}
