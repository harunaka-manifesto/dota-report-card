/**
 * Runtime types for the optional `report.story_payload` block.
 *
 * These mirror `services/api/app/api/story_payload_schemas_v61.py` at commit
 * b261045e85856ad27ce0cb3661369d0bf58b3614.  They describe what the transport
 * may deliver, not what the renderer trusts: every optional section still
 * passes through `normalize-story.ts` before composition.
 */

export type StoryState = "available" | "degraded" | "omitted" | "not_ready";
export type StoryOutcome = "win" | "loss";
export type StoryFindingFamily = "post_loss_response" | "transfer";

export const STORY_MODULE_KEYS = [
  "hello",
  "match_count",
  "hours_in_matches",
  "rank_points",
  "busiest_week",
  "busiest_day",
  "longest_match",
  "wins_bridge",
  "win_summary",
  "winning_streak",
  "top_win_heroes",
  "losing_streak",
  "top_loss_heroes",
  "hero_pool",
  "hero_eras",
  "hero_era_payoff",
  "kills",
  "assists",
  "deaths",
  "element_distinctiveness",
  "archetype",
  "card_collage",
  "final_identity_card",
  "deep",
] as const;

export type StoryModuleKey = (typeof STORY_MODULE_KEYS)[number];
export type StoryCardModuleKey = StoryModuleKey | "post_loss" | "transfer";

/**
 * Page ownership as frozen by `STORY_MODULE_PAGES` in the shipped schema.
 * Transfer is page 21 (corrected at b261045); Post-Loss is page 15.
 */
export const STORY_MODULE_PAGES: Record<StoryCardModuleKey, number> = {
  hello: 1,
  match_count: 2,
  hours_in_matches: 3,
  rank_points: 4,
  busiest_week: 5,
  busiest_day: 6,
  longest_match: 7,
  wins_bridge: 8,
  win_summary: 9,
  winning_streak: 10,
  top_win_heroes: 11,
  losing_streak: 12,
  top_loss_heroes: 13,
  post_loss: 15,
  hero_pool: 17,
  hero_eras: 18,
  hero_era_payoff: 19,
  transfer: 21,
  kills: 22,
  assists: 23,
  deaths: 24,
  element_distinctiveness: 28,
  archetype: 29,
  card_collage: 32,
  final_identity_card: 33,
  deep: 34,
};

export type StoryModule<TData> = {
  state: StoryState;
  reason?: string | null;
  copy_variant?: string | null;
  data?: TData | null;
};

export type StoryHelloData = {
  display_name?: string | null;
  requested_window_days: 365;
  window_start: string;
  window_end: string;
  observed_from: string;
  observed_to: string;
  history_materially_short: boolean;
};

export type StoryMatchCountData = {
  match_count: number;
  volume_variant: "limited" | "normal";
};

export type StoryHoursData = {
  total_duration_seconds?: number | null;
  display_value?: number | null;
  display_unit?: "minutes" | "hours" | null;
  hours_available: boolean;
  coverage_numerator: number;
  coverage_denominator: number;
  coverage_ratio: number;
};

export type StoryRankPointsData = {
  points_absolute: number;
  direction: "positive" | "negative" | "zero";
  ranked_matches: number;
  ranked_wins: number;
  ranked_losses: number;
  points_per_match: 25;
  classification_reliable: true;
  formula_version: string;
};

type StoryPeriodDuration = {
  total_duration_seconds?: number | null;
  display_value?: number | null;
  display_unit?: "minutes" | "hours" | null;
  hours_available: boolean;
};

export type StoryBusiestWeekData = StoryPeriodDuration & {
  period_kind: "iso_calendar_week";
  date_start: string;
  date_end: string;
  match_count: number;
};

export type StoryBusiestDayData = StoryPeriodDuration & {
  date: string;
  match_count: number;
  inside_busiest_week: boolean;
  also_longest_match_day: boolean;
};

export type StoryLongestMatchData = {
  duration_seconds: number;
  formatted_duration: string;
  hero_id: number;
  hero_name: string;
  date: string;
  outcome: StoryOutcome;
  kills?: number | null;
  deaths?: number | null;
  assists?: number | null;
  refused_to_end: boolean;
  on_busiest_day: boolean;
};

export type StoryWinsBridgeData = { wins: number };

export type StoryWinSummaryData = {
  wins: number;
  winningest_day?: { date: string; daily_wins: number } | null;
};

export type StoryWinningStreakData = {
  length: number;
  start_date: string;
  end_date: string;
};

export type StoryWinHeroRow = {
  rank: number;
  hero_id: number;
  hero_name: string;
  wins: number;
  matches: number;
};

export type StoryTopWinHeroesData = { rows: StoryWinHeroRow[] };

export type StoryBreaker = {
  hero_id: number;
  hero_name: string;
  date: string;
  outcome: StoryOutcome;
  kills?: number | null;
  deaths?: number | null;
  assists?: number | null;
  duration_seconds?: number | null;
};

export type StoryLosingStreakData = {
  length: number;
  start_date: string;
  end_date: string;
  terminal_state: "broken_by_win" | "observation_ended" | "history_boundary";
  breaker?: StoryBreaker | null;
};

export type StoryLossHeroRow = {
  rank: number;
  hero_id: number;
  hero_name: string;
  losses: number;
  matches: number;
};

export type StoryTopLossHeroesData = {
  breaker_exists: boolean;
  rows: StoryLossHeroRow[];
  roughest_day?: { date: string; daily_losses: number } | null;
};

export type StoryPoolHeroRow = {
  rank: number;
  hero_id: number;
  hero_name: string;
  matches: number;
  share: number;
};

export type StoryHeroPoolData = {
  heroes: StoryPoolHeroRow[];
  total_matches: number;
  top_five_share: number;
  concentration_band?: "concentrated" | "broad" | null;
};

export type StoryEraHeroCount = {
  rank: number;
  hero_id: number;
  hero_name: string;
  matches: number;
};

export type StoryHeroEra = {
  id: string;
  period_kind: "calendar_month" | "third";
  date_start: string;
  date_end: string;
  match_count: number;
  empty: boolean;
  sparse: boolean;
  top_heroes: StoryEraHeroCount[];
};

export type StoryHeroErasData = {
  periods: StoryHeroEra[];
  sparse_fallback: boolean;
  period_kind: "calendar_month" | "third";
};

export type StoryHeroReference = { hero_id: number; hero_name: string };

export type StoryHeroEraPayoffData = {
  persistence?: { hero: StoryHeroReference; top_five_periods: number } | null;
  takeover?: { hero: StoryHeroReference; period: string } | null;
  steady_pool: boolean;
};

export type StoryCombatRow = {
  rank: number;
  hero_id?: number | null;
  hero_name?: string | null;
  date?: string | null;
  outcome?: StoryOutcome | null;
  kills?: number | null;
  deaths?: number | null;
  assists?: number | null;
  duration_seconds?: number | null;
  stat_value?: number | null;
};

export type StoryCombatData = {
  total: number;
  leading_hero?: { hero_id: number; hero_name: string; total: number } | null;
  individuals: StoryCombatRow[];
};

export type StoryElementDistinctivenessData = {
  rows: Array<{
    element_key: string;
    percentile: number;
    extremity_rank: number;
    direction: "positive" | "negative" | "zero";
  }>;
  nothing_meaningfully_stands_out: boolean;
};

/**
 * The archetype ships `production_ready: false` with null name/description.
 * Nothing in this release upgrades it — see `archetype-placeholder.ts`.
 */
export type StoryArchetypeData = {
  production_ready: false;
  name: null;
  description: null;
  evidence_anchors: null[];
  recap_available: false;
  share_card_available: false;
};

export type StoryFinalIdentityData = {
  display_name?: string | null;
  archetype: null;
  story_match_count: number;
  lookback_days: 365;
  window_start: string;
  window_end: string;
  share_card_available: false;
};

export type StoryDeepData = { available: boolean };

export type StoryCard = {
  id: string;
  module: StoryCardModuleKey;
  page?: number | null;
};

export type StoryCardCollageData = { version: string; cards: StoryCard[] };

export type StoryFindingClaimContract = {
  claim?: string | null;
  evidence?: string | null;
  interpretation?: string | null;
  recommendation?: Record<string, unknown> | null;
  alternatives: string[];
  verification?: Record<string, unknown> | null;
  interaction?: string | null;
  copy_version?: string | null;
};

export type StoryFindingContent = {
  family: StoryFindingFamily;
  claim?: string | null;
  interpretation?: string | null;
  claim_contract?: StoryFindingClaimContract | null;
  evidence_refs: string[];
  confidence: "unavailable" | "descriptive" | "moderate" | "high";
  semantic_outcome_key?: string | null;
  comparable_opportunities?: number | null;
  cross_session_transitions: false;
};

export type StoryFindingSlot = {
  available: boolean;
  family: StoryFindingFamily;
  content?: StoryFindingContent | null;
};

export type StoryFindingSlots = {
  post_loss: StoryFindingSlot;
  transfer: StoryFindingSlot;
};

export type StoryUniverse = {
  key: string;
  requested_window_days: 365;
  window_start: string;
  window_end: string;
  observed_from: string;
  observed_to: string;
  observed_days: number;
  history_materially_short: boolean;
  match_count: number;
  volume_tier: "limited" | "normal";
  mode_counts: {
    unranked_all_pick: number;
    ranked_all_pick: number;
    unranked_captains_mode: number;
    ranked_captains_mode: number;
  };
  excluded_or_unknown_count: number;
  duration_candidate_count: number;
  duration_known_count: number;
  duration_coverage: number;
  history_completeness: "complete" | "possibly_truncated" | "unknown";
};

export type StoryProvenance = {
  provider: string;
  physical_history_requests: number;
  detail_requests: number;
  parse_requests: number;
  mode_map_version: string;
  mode_map_checksum: string;
  hero_taxonomy_version: string;
  hero_taxonomy_factual_checksum: string;
  hero_taxonomy_editorial_checksum: string;
  story_input_sha256: string;
};

export type StoryModules = {
  hello: StoryModule<StoryHelloData>;
  match_count: StoryModule<StoryMatchCountData>;
  hours_in_matches: StoryModule<StoryHoursData>;
  rank_points: StoryModule<StoryRankPointsData>;
  busiest_week: StoryModule<StoryBusiestWeekData>;
  busiest_day: StoryModule<StoryBusiestDayData>;
  longest_match: StoryModule<StoryLongestMatchData>;
  wins_bridge: StoryModule<StoryWinsBridgeData>;
  win_summary: StoryModule<StoryWinSummaryData>;
  winning_streak: StoryModule<StoryWinningStreakData>;
  top_win_heroes: StoryModule<StoryTopWinHeroesData>;
  losing_streak: StoryModule<StoryLosingStreakData>;
  top_loss_heroes: StoryModule<StoryTopLossHeroesData>;
  hero_pool: StoryModule<StoryHeroPoolData>;
  hero_eras: StoryModule<StoryHeroErasData>;
  hero_era_payoff: StoryModule<StoryHeroEraPayoffData>;
  kills: StoryModule<StoryCombatData>;
  assists: StoryModule<StoryCombatData>;
  deaths: StoryModule<StoryCombatData>;
  element_distinctiveness: StoryModule<StoryElementDistinctivenessData>;
  archetype: StoryModule<StoryArchetypeData>;
  card_collage: StoryModule<StoryCardCollageData>;
  final_identity_card: StoryModule<StoryFinalIdentityData>;
  deep: StoryModule<StoryDeepData>;
};

export type StoryPageManifestEntry =
  | number
  | string
  | { id?: string | null; page?: number | null; module?: StoryCardModuleKey | null };

export type StoryPayload = {
  version: string;
  availability: { state: "available" | "degraded"; reason?: string | null };
  provenance: StoryProvenance;
  universe: StoryUniverse;
  identity: { display_name?: string | null };
  modules: StoryModules;
  finding_slots: StoryFindingSlots;
  page_manifest: StoryPageManifestEntry[];
  card_manifest: Array<string | StoryCard>;
};
