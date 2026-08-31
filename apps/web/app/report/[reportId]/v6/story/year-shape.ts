/**
 * The shape of the year.
 *
 * The archetype engine is `not_ready` and this file does NOT stand in for it.
 * It never assigns a type, a personality, a tier, or a trait. It restates, in
 * one line, facts the backend has already asserted — a supplied
 * `copy_variant` and a supplied hero name — so the ending is about the reader's
 * own year instead of a constant shown to everyone.
 *
 * THE BOUNDARY, precisely:
 *  - every branch below is selected by a supplied `copy_variant` or a supplied
 *    enum; nothing is summed, ranked, compared, or thresholded here;
 *  - every hero name comes from the module that already named it;
 *  - no branch adds a claim its source variant does not already make.
 *
 * If a required variant is missing, the title is null and the caller falls
 * back to the neutral constant. Absence is never filled in.
 */

import type { StoryPayload } from "./payload-types";

export type YearShape = {
  /** Short, descriptive, screenshot-sized. Never a personality label. */
  title: string;
  /** One supporting clause, restating the same supplied fact. */
  line: string;
  /** Which supplied variant selected this branch, for the docs and tests. */
  source: string;
};

/**
 * Priority order is fixed and documented, so the same payload always produces
 * the same shape. Era payoff wins over pool concentration because the backend
 * only emits a persistence/takeover hero when it has one to name.
 */
export function yearShape(payload: StoryPayload): YearShape | null {
  const eras = payload.modules.hero_era_payoff;
  const pool = payload.modules.hero_pool;

  if (eras.state === "available" || eras.state === "degraded") {
    const data = eras.data;
    // `takeover` — the backend named a hero and the period it led.
    if (eras.copy_variant === "takeover" && data?.takeover) {
      return {
        title: `The ${data.takeover.hero.hero_name} Year`,
        line: "One name took the front of the list and kept it.",
        source: "hero_era_payoff:takeover",
      };
    }
    // `persistence` — the backend named a hero and how many periods it held.
    if (eras.copy_variant === "persistence" && data?.persistence) {
      return {
        title: `The ${data.persistence.hero.hero_name} Year`,
        line: "One name stayed on the list while the rest moved around it.",
        source: "hero_era_payoff:persistence",
      };
    }
    // `steady` — the backend asserted the pool did not reorder.
    if (eras.copy_variant === "steady" && data?.steady_pool) {
      return {
        title: "The Year That Held Its Shape",
        line: "The names at the top stayed the names at the top.",
        source: "hero_era_payoff:steady",
      };
    }
  }

  if (pool.state === "available" || pool.state === "degraded") {
    // `concentrated` / `broad` are the supplied concentration band.
    if (pool.copy_variant === "concentrated") {
      return {
        title: "The Short List Year",
        line: "A small group of names carried most of the queue.",
        source: "hero_pool:concentrated",
      };
    }
    if (pool.copy_variant === "broad") {
      return {
        title: "The Wide Year",
        line: "The names kept changing and the queue kept going.",
        source: "hero_pool:broad",
      };
    }
  }

  return null;
}
