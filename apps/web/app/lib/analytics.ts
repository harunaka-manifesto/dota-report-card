export type AnalyticsPayload = Record<string, string | number | boolean | null | undefined>;

// Vendor-neutral by design.  A provider can be attached at this seam without
// making the report story aware of analytics transport or identity.
export function track(eventName: string, payload: AnalyticsPayload = {}): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("dota-report-analytics", {
    detail: { event: eventName, schema_version: "1", ...payload }
  }));
}
