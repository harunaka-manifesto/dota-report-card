/**
 * The frozen `copy_variant` vocabulary.
 *
 * `copy_variant` is typed `str | None` in the shipped schema, so this map is
 * the frontend's contract until the backend promotes it to a `Literal` union.
 * Values were read from `services/api/app/player_analysis_v61/story_payload.py`
 * at b261045, not from a plan document.
 *
 * Plan Appendix A lists `hello` as `anonymous | unavailable`.  That is wrong:
 * the producer emits `("named" | "anonymous") + ("_short" | "_full")` plus
 * `unavailable` on omission.  The source wins.
 *
 * On an unrecognised value the owning module is OMITTED and a diagnostic is
 * emitted.  We never throw and never fall through to a default copy branch —
 * a missing page is recoverable, a wrong claim is not.
 */

import type { StoryModuleKey } from "./payload-types";

export const STORY_CARD_VERSION = "free-story-cards-1.0.0";

export const COPY_VARIANTS: Record<StoryModuleKey, ReadonlySet<string>> = {
  hello: new Set(["named_full", "named_short", "anonymous_full", "anonymous_short", "unavailable"]),
  match_count: new Set(["limited", "normal", "unavailable"]),
  hours_in_matches: new Set(["minutes", "hours", "unavailable"]),
  rank_points: new Set(["positive", "negative", "zero", "unavailable"]),
  busiest_week: new Set(["hours", "match_count", "unavailable"]),
  busiest_day: new Set(["hours", "match_count", "unavailable"]),
  longest_match: new Set(["refused_to_end", "standard", "unavailable"]),
  wins_bridge: new Set(["wins", "zero"]),
  win_summary: new Set(["zero", "one", "many"]),
  winning_streak: new Set(["single_win", "streak", "unavailable"]),
  top_win_heroes: new Set(["ranked", "unavailable"]),
  losing_streak: new Set(["broken_by_win", "observation_ended", "history_boundary", "unavailable"]),
  top_loss_heroes: new Set(["ranked", "unavailable"]),
  hero_pool: new Set(["concentrated", "broad", "neutral", "unavailable"]),
  hero_eras: new Set(["calendar_month", "sparse_fallback", "unavailable"]),
  hero_era_payoff: new Set(["persistence", "takeover", "steady", "unavailable"]),
  kills: new Set(["available", "zero"]),
  assists: new Set(["available", "zero"]),
  deaths: new Set(["available", "zero"]),
  element_distinctiveness: new Set(["not_ready"]),
  archetype: new Set(["not_ready"]),
  card_collage: new Set([STORY_CARD_VERSION, "unavailable"]),
  final_identity_card: new Set(["not_ready"]),
  deep: new Set(["available", "unavailable"]),
};

export type StoryDiagnostic = {
  code: "unrecognised_copy_variant" | "malformed_module_data" | "malformed_manifest_entry";
  module: string;
  detail: string;
};

export function isKnownCopyVariant(module: StoryModuleKey, variant: string | null | undefined): boolean {
  if (variant === null || variant === undefined) return true;
  return COPY_VARIANTS[module].has(variant);
}
