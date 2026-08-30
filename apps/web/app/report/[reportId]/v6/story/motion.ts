/**
 * Motion tokens and the beat schedule.
 *
 * A page owns an ordered beat list.  Beats separate by `beat` (560ms), except
 * that a dominant value settles (460ms) and then holds alone (700ms) before
 * its support arrives, and the archetype holds for `identityHold` (1000ms).
 *
 * No page auto-advances.  Timers pause while the document is hidden or a
 * dialog is open, so a reader who tabs away does not lose a beat.
 */

export const MOTION = {
  tap: 140,
  swap: 220,
  page: 320,
  settle: 460,
  beat: 560,
  factHold: 700,
  identityHold: 1000,
  stagger: 70,
  collageStagger: 90,
  /** The Endstop resolves this long after the final factual beat. */
  endstop: 420,
} as const;

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
          : MOTION.beat;
    offsets.push(offsets[previous] + gap);
  }
  return offsets;
}
