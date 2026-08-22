import type { PatternVisualVariant } from "../../../../../../packages/api-client/src";

export type PatternVisualProps = {
  patternId: string;
  variant: PatternVisualVariant;
  proof: Record<string, unknown>;
};

export function stringValue(value: unknown, fallback = "Not available"): string {
  if (typeof value === "string" && value.length > 0) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return fallback;
}

export function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

export function numberValue(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function recordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];
}
