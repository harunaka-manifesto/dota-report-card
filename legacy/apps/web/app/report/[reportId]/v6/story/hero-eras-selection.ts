import type { StoryHeroEra } from "./payload-types";

/**
 * Hero Eras opens on the most recent non-empty period.
 *
 * The payload supplies no initial index — `hero_eras.data` is only
 * `{periods, sparse_fallback, period_kind}` — so this is a documented
 * PRESENTATION default, not an analytical choice: it selects a starting view,
 * never a value.  It is a pure function of the ordered `periods` array and
 * nothing else: no match volume, no recency weighting, no tie-break.
 *
 * If every period is empty, it opens on the last one.  An empty array yields
 * 0, which the caller never reaches because the module is omitted first.
 */
export function initialHeroEraIndex(periods: readonly StoryHeroEra[]): number {
  for (let index = periods.length - 1; index >= 0; index -= 1) {
    if (!periods[index].empty) return index;
  }
  return Math.max(0, periods.length - 1);
}
