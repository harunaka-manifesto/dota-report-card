/**
 * Motion tokens and the beat schedule.
 *
 * A page owns an ordered beat list. Ordinary gaps follow its semantic rhythm;
 * a dominant value settles (460ms) and then holds alone (700ms) before its
 * support arrives, and the final reveal holds for `identityHold` (1000ms).
 *
 * No page auto-advances.  Timers pause while the document is hidden or a
 * dialog is open, so a reader who tabs away does not lose a beat.
 */

export const MOTION = {
  tap: 140,
  swap: 220,
  page: 320,
  settle: 460,
  factHold: 700,
  identityHold: 1000,
  stagger: 70,
  collageStagger: 90,
  /** The Endstop resolves this long after the final factual beat. */
  endstop: 420,
} as const;

export type NarrativeRhythm =
  | "immediate"
  | "measured"
  | "question"
  | "accumulation"
  | "chronology"
  | "quiet"
  | "identity";

export const RHYTHM_GAPS: Record<NarrativeRhythm, number> = {
  immediate: 300,
  measured: 480,
  question: 650,
  accumulation: 320,
  chronology: 420,
  quiet: 700,
  identity: 560,
};

/** Semantic pacing for the fixed page IDs; omitted pages never get a tick. */
export const PAGE_RHYTHMS: Readonly<Record<number, NarrativeRhythm>> = {
  1: "measured",
  2: "immediate",
  3: "immediate",
  4: "measured",
  5: "question",
  6: "chronology",
  7: "question",
  8: "quiet",
  9: "immediate",
  10: "accumulation",
  11: "accumulation",
  12: "accumulation",
  13: "accumulation",
  14: "quiet",
  15: "question",
  16: "quiet",
  17: "accumulation",
  18: "chronology",
  19: "chronology",
  20: "question",
  21: "question",
  22: "immediate",
  23: "immediate",
  24: "measured",
  26: "quiet",
  27: "accumulation",
  29: "accumulation",
  30: "identity",
  32: "accumulation",
  33: "quiet",
  34: "quiet",
};

export function rhythmForPage(page: number): NarrativeRhythm {
  return PAGE_RHYTHMS[page] ?? "measured";
}

export type BeatPlan = {
  /** Number of beats the page reveals, including its optional dry line. */
  total: number;
  /**
   * Index of the beat carrying the dominant value, if any.  The beat after it
   * waits `settle + factHold` instead of one `beat`.
   */
  holdAfter?: number;
  /** Index after which the archetype holds alone for `identityHold`. */
  identityHoldAfter?: number;
  /** Semantic pacing for ordinary beat gaps; defaults to measured. */
  rhythm?: NarrativeRhythm;
};

/** Absolute offsets, in milliseconds, for every beat in a plan. */
export function beatOffsets(plan: BeatPlan): number[] {
  const offsets: number[] = [];
  for (let index = 0; index < plan.total; index += 1) {
    if (index === 0) {
      offsets.push(0);
      continue;
    }
    const previous = index - 1;
    const gap =
      previous === plan.holdAfter
        ? MOTION.settle + MOTION.factHold
        : previous === plan.identityHoldAfter
          ? MOTION.identityHold
          : RHYTHM_GAPS[plan.rhythm ?? "measured"];
    offsets.push(offsets[previous] + gap);
  }
  return offsets;
}
