import type { V6InteractionState } from "../../../../../lib/v6/interaction-client";

/** Persisted V6 beat IDs. These indices are part of the resume contract. */
export const LEGACY_BEAT_IDS = [
  "self-estimate",
  "identity-reveal",
  "pool-evolution",
  "combat-expression",
  "strongest-finding",
  "secondary-finding",
  "recommendation",
  "hero-mirror",
  "deep-diagnostic",
] as const;

export type LegacyBeatId = (typeof LEGACY_BEAT_IDS)[number];

/** Canonical Story progress vocabulary. Micro-states share these segments. */
export const STORY_PROGRESS_SEGMENTS = [
  "arrival",
  "heroes",
  "pool-shape",
  "transfer",
  "post-loss",
  "combat-expression",
  "session-drift",
  "synthesis",
  "identity",
  "premium",
  "share-transition",
  "share-cards",
  "share-gallery",
  "end",
] as const;

export type StoryProgressSegment = (typeof STORY_PROGRESS_SEGMENTS)[number];

/** Legacy chapters map to the first stable segment they introduce. */
export const LEGACY_BEAT_TO_PROGRESS: readonly number[] = [0, 0, 2, 3, 4, 5, 6, 7, 10];

export function clampLegacyBeat(index: number): number {
  return Math.max(0, Math.min(LEGACY_BEAT_IDS.length - 1, Number.isFinite(index) ? Math.round(index) : 0));
}

export function legacyProgressCount(state: Pick<V6InteractionState, "completed_beats" | "skipped_beats">): number {
  return Math.min(LEGACY_BEAT_IDS.length, new Set([...(state.completed_beats ?? []), ...(state.skipped_beats ?? [])]).size);
}

export function beatLabel(id: LegacyBeatId): string {
  return {
    "self-estimate": "Start",
    "identity-reveal": "Shape",
    "pool-evolution": "Pool",
    "combat-expression": "Change",
    "strongest-finding": "After loss",
    "secondary-finding": "Match",
    recommendation: "Session",
    "hero-mirror": "Signature",
    "deep-diagnostic": "Share",
  }[id];
}

export function scrollToLegacyBeat(id: LegacyBeatId): void {
  if (typeof document === "undefined") return;
  const target = document.getElementById(`v6-beat-${LEGACY_BEAT_IDS.indexOf(id) + 1}`);
  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  target?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
}

export function stepIndexForLegacyBeat(sequence: readonly { legacyBeatIndex: number; phase: number }[], beat: number): number {
  const exact = sequence.findIndex((step) => step.legacyBeatIndex === beat && step.phase === 0);
  return exact >= 0 ? exact : 0;
}
