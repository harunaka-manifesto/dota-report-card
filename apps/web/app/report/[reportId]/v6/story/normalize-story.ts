/**
 * The story normalization boundary.
 *
 * Raw persisted JSON enters here once and leaves as a shape the composer can
 * trust.  Normalization may REPAIR STRUCTURE — drop a malformed row, demote a
 * module whose data contradicts its state, preserve a meaningful null.  It may
 * never FABRICATE ANALYTICAL MEANING: no sums, no ranks, no thresholds, no
 * tie-breaks, no substituted defaults.
 *
 * A module that cannot be trusted becomes `omitted`, which is the same
 * behaviour the whole experience already uses for absent data.
 */

import {
  COPY_VARIANTS,
  isKnownCopyVariant,
  type StoryDiagnostic,
} from "./copy-variants";
import {
  STORY_MODULE_KEYS,
  STORY_MODULE_PAGES,
  type StoryCard,
  type StoryCardModuleKey,
  type StoryEraHeroCount,
  type StoryHeroEra,
  type StoryModule,
  type StoryModuleKey,
  type StoryModules,
  type StoryPayload,
  type StoryProvenance,
  type StoryState,
  type StoryUniverse,
} from "./payload-types";

export type NormalizedStory = {
  payload: StoryPayload;
  diagnostics: StoryDiagnostic[];
};

type Rec = Record<string, unknown>;

function isRecord(value: unknown): value is Rec {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function nonEmptyString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function isOneOf<T extends string>(value: unknown, allowed: readonly T[]): value is T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value);
}

function hasNumbers(value: Rec, fields: readonly string[]): boolean {
  return fields.every((field) => finiteNumber(value[field]) !== null);
}

function hasStrings(value: Rec, fields: readonly string[]): boolean {
  return fields.every((field) => nonEmptyString(value[field]) !== null);
}

function hasBooleans(value: Rec, fields: readonly string[]): boolean {
  return fields.every((field) => typeof value[field] === "boolean");
}

function heroReference(value: unknown): value is Rec {
  return isRecord(value) && finiteNumber(value.hero_id) !== null && nonEmptyString(value.hero_name) !== null;
}

function periodDurationIsValid(value: Rec): boolean {
  if (typeof value.hours_available !== "boolean") return false;
  if (!value.hours_available) return true;
  return finiteNumber(value.display_value) !== null && isOneOf(value.display_unit, ["minutes", "hours"]);
}

function normalizeUniverse(raw: unknown): StoryUniverse | null {
  if (!isRecord(raw) || !isRecord(raw.mode_counts)) return null;
  if (
    !hasStrings(raw, ["key", "window_start", "window_end", "observed_from", "observed_to", "history_completeness"]) ||
    !hasNumbers(raw, [
      "requested_window_days",
      "observed_days",
      "match_count",
      "excluded_or_unknown_count",
      "duration_candidate_count",
      "duration_known_count",
      "duration_coverage",
    ]) ||
    !hasNumbers(raw.mode_counts, [
      "unranked_all_pick",
      "ranked_all_pick",
      "unranked_captains_mode",
      "ranked_captains_mode",
    ]) ||
    typeof raw.history_materially_short !== "boolean" ||
    raw.requested_window_days !== 365 ||
    !isOneOf(raw.volume_tier, ["limited", "normal"]) ||
    !isOneOf(raw.history_completeness, ["complete", "possibly_truncated", "unknown"])
  ) {
    return null;
  }
  return raw as unknown as StoryUniverse;
}

function normalizeProvenance(raw: unknown): StoryProvenance | null {
  if (!isRecord(raw)) return null;
  if (
    !hasStrings(raw, [
      "provider",
      "mode_map_version",
      "mode_map_checksum",
      "hero_taxonomy_version",
      "hero_taxonomy_factual_checksum",
      "hero_taxonomy_editorial_checksum",
      "story_input_sha256",
    ]) ||
    !hasNumbers(raw, ["physical_history_requests", "detail_requests", "parse_requests"])
  ) {
    return null;
  }
  return raw as unknown as StoryProvenance;
}

const VALID_STATES: ReadonlySet<string> = new Set<StoryState>([
  "available",
  "degraded",
  "omitted",
  "not_ready",
]);

/**
 * Reads `report.story_payload`.  Returns null when the block is absent or so
 * malformed that no page can be trusted — the caller then falls back to the
 * legacy compatibility renderer.
 */
export function normalizeStoryPayload(raw: unknown): NormalizedStory | null {
  const diagnostics: StoryDiagnostic[] = [];
  if (!isRecord(raw) || raw.version !== "free-story-payload-1.0.0") return null;

  const modulesRaw = raw.modules;
  const findingSlots = raw.finding_slots;
  const universe = normalizeUniverse(raw.universe);
  const provenance = normalizeProvenance(raw.provenance);
  const availability = raw.availability;
  const identity = raw.identity;
  if (
    !isRecord(modulesRaw) ||
    !isRecord(findingSlots) ||
    universe === null ||
    provenance === null ||
    !isRecord(availability) ||
    !isOneOf(availability.state, ["available", "degraded"]) ||
    !isRecord(identity)
  ) {
    return null;
  }

  const modules = {} as StoryModules;
  for (const key of STORY_MODULE_KEYS) {
    modules[key] = normalizeModule(key, modulesRaw[key], diagnostics) as never;
  }

  const payload: StoryPayload = {
    ...(raw as unknown as StoryPayload),
    universe,
    provenance,
    identity: { display_name: typeof identity.display_name === "string" ? identity.display_name : null },
    modules,
    finding_slots: {
      post_loss: normalizeSlot(findingSlots.post_loss, "post_loss_response"),
      transfer: normalizeSlot(findingSlots.transfer, "transfer"),
    },
    page_manifest: asArray(raw.page_manifest) as StoryPayload["page_manifest"],
    card_manifest: asArray(raw.card_manifest) as StoryPayload["card_manifest"],
  };

  return { payload, diagnostics };
}

function normalizeModule(
  key: StoryModuleKey,
  raw: unknown,
  diagnostics: StoryDiagnostic[],
): StoryModule<unknown> {
  const omitted = (detail: StoryDiagnostic | null): StoryModule<unknown> => {
    if (detail) diagnostics.push(detail);
    return { state: "omitted", reason: "normalization_rejected", copy_variant: null, data: null };
  };

  if (!isRecord(raw)) {
    // A structurally absent module is indistinguishable from an omitted one.
    return { state: "omitted", reason: "module_absent", copy_variant: null, data: null };
  }
  const state = typeof raw.state === "string" && VALID_STATES.has(raw.state) ? (raw.state as StoryState) : null;
  if (state === null) {
    return omitted({ code: "malformed_module_data", module: key, detail: "unknown module state" });
  }

  const variant = typeof raw.copy_variant === "string" ? raw.copy_variant : null;
  if (!isKnownCopyVariant(key, variant)) {
    // Risk 4: never render a default branch for an unknown variant.
    return omitted({
      code: "unrecognised_copy_variant",
      module: key,
      detail: `${variant} is not in {${[...COPY_VARIANTS[key]].join(", ")}}`,
    });
  }

  if ((state === "available" || state === "degraded") && !isRecord(raw.data)) {
    return omitted({ code: "malformed_module_data", module: key, detail: `${state} module carries no data` });
  }

  const data = isRecord(raw.data) ? normalizeModuleData(key, raw.data) : null;
  if (data === null && (state === "available" || state === "degraded")) {
    return omitted({ code: "malformed_module_data", module: key, detail: "module data failed normalization" });
  }

  return {
    state,
    reason: typeof raw.reason === "string" ? raw.reason : null,
    copy_variant: variant,
    data,
  };
}

/**
 * Per-module structural repair.  Row arrays lose malformed entries; a module
 * whose required scalar is missing returns null and is omitted upstream.
 */
function normalizeModuleData(key: StoryModuleKey, data: Rec): Rec | null {
  switch (key) {
    case "hello":
      return hasStrings(data, ["window_start", "window_end", "observed_from", "observed_to"]) &&
        data.requested_window_days === 365 &&
        typeof data.history_materially_short === "boolean"
        ? data
        : null;
    case "match_count":
      return finiteNumber(data.match_count) !== null && isOneOf(data.volume_variant, ["limited", "normal"])
        ? data
        : null;
    case "hours_in_matches":
      return periodDurationIsValid(data) && hasNumbers(data, ["coverage_numerator", "coverage_denominator", "coverage_ratio"])
        ? data
        : null;
    case "rank_points":
      return hasNumbers(data, ["points_absolute", "ranked_matches", "ranked_wins", "ranked_losses"]) &&
        isOneOf(data.direction, ["positive", "negative", "zero"])
        ? data
        : null;
    case "busiest_week":
      return hasStrings(data, ["date_start", "date_end"]) &&
        finiteNumber(data.match_count) !== null &&
        data.period_kind === "iso_calendar_week" &&
        periodDurationIsValid(data)
        ? data
        : null;
    case "busiest_day":
      return hasStrings(data, ["date"]) &&
        finiteNumber(data.match_count) !== null &&
        hasBooleans(data, ["inside_busiest_week", "also_longest_match_day"]) &&
        periodDurationIsValid(data)
        ? data
        : null;
    case "longest_match":
      return hasNumbers(data, ["duration_seconds", "hero_id"]) &&
        hasStrings(data, ["formatted_duration", "hero_name", "date"]) &&
        hasBooleans(data, ["refused_to_end", "on_busiest_day"]) &&
        isOneOf(data.outcome, ["win", "loss"])
        ? data
        : null;
    case "wins_bridge":
      return finiteNumber(data.wins) !== null ? data : null;
    case "win_summary": {
      if (finiteNumber(data.wins) === null) return null;
      const day = data.winningest_day;
      if (day !== null && day !== undefined && (!isRecord(day) || !hasStrings(day, ["date"]) || !hasNumbers(day, ["daily_wins"]))) {
        return null;
      }
      return { ...data, winningest_day: isRecord(day) ? day : null };
    }
    case "winning_streak":
      return finiteNumber(data.length) !== null && hasStrings(data, ["start_date", "end_date"]) ? data : null;
    case "top_win_heroes": {
      const rows = rankedRows(data.rows, ["wins", "matches"]);
      return rows.length > 0 ? { ...data, rows } : null;
    }
    case "top_loss_heroes":
      if (typeof data.breaker_exists !== "boolean") return null;
      const lossRows = rankedRows(data.rows, ["losses", "matches"]);
      if (lossRows.length === 0) return null;
      if (
        data.roughest_day !== null &&
        data.roughest_day !== undefined &&
        (!isRecord(data.roughest_day) ||
          !hasStrings(data.roughest_day, ["date"]) ||
          !hasNumbers(data.roughest_day, ["daily_losses"]))
      ) return null;
      return {
        ...data,
        rows: lossRows,
        roughest_day: isRecord(data.roughest_day) ? data.roughest_day : null,
      };
    case "hero_pool": {
      const heroes = rankedRows(data.heroes, ["matches", "share"]);
      return heroes.length > 0 && hasNumbers(data, ["total_matches", "top_five_share"])
        ? { ...data, heroes }
        : null;
    }
    case "hero_eras": {
      const periods = asArray(data.periods)
        .map(normalizeHeroEra)
        .filter((period): period is StoryHeroEra => period !== null);
      return periods.length > 0 && typeof data.sparse_fallback === "boolean" && isOneOf(data.period_kind, ["calendar_month", "third"])
        ? { ...data, periods }
        : null;
    }
    case "hero_era_payoff": {
      if (typeof data.steady_pool !== "boolean") return null;
      const persistence = isRecord(data.persistence) && heroReference(data.persistence.hero) && finiteNumber(data.persistence.top_five_periods) !== null
        ? data.persistence
        : null;
      const takeover = isRecord(data.takeover) && heroReference(data.takeover.hero) && nonEmptyString(data.takeover.period) !== null
        ? data.takeover
        : null;
      return persistence || takeover || data.steady_pool ? { ...data, persistence, takeover } : null;
    }
    case "kills":
    case "assists":
    case "deaths": {
      if (finiteNumber(data.total) === null) return null;
      const leadingHero = isRecord(data.leading_hero) && heroReference(data.leading_hero) && finiteNumber(data.leading_hero.total) !== null
        ? data.leading_hero
        : null;
      return {
        ...data,
        leading_hero: leadingHero,
        individuals: asArray(data.individuals).filter(
          (row) =>
            isRecord(row) &&
            finiteNumber(row.rank) !== null &&
            (row.hero_id === null || row.hero_id === undefined || finiteNumber(row.hero_id) !== null) &&
            (row.hero_name === null || row.hero_name === undefined || nonEmptyString(row.hero_name) !== null),
        ),
      };
    }
    case "losing_streak": {
      if (
        finiteNumber(data.length) === null ||
        !hasStrings(data, ["start_date", "end_date"]) ||
        !isOneOf(data.terminal_state, ["broken_by_win", "observation_ended", "history_boundary"])
      ) return null;
      const breaker = data.breaker;
      if (breaker !== null && breaker !== undefined && (!heroReference(breaker) || !hasStrings(breaker, ["date"]) || !isOneOf(breaker.outcome, ["win", "loss"]))) {
        return null;
      }
      return { ...data, breaker: isRecord(breaker) ? breaker : null };
    }
    case "element_distinctiveness":
      return Array.isArray(data.rows) && typeof data.nothing_meaningfully_stands_out === "boolean" ? data : null;
    case "archetype":
      return data.production_ready === false && data.name === null && data.description === null ? data : null;
    case "card_collage": {
      const cards = asArray(data.cards).filter(
        (card): card is StoryCard =>
          isRecord(card) && nonEmptyString(card.id) !== null && normalizeCardModule(card.module) !== null,
      );
      return data.version === "free-story-cards-1.0.0" ? { ...data, cards } : null;
    }
    case "final_identity_card":
      return hasNumbers(data, ["story_match_count", "lookback_days"]) && hasStrings(data, ["window_start", "window_end"])
        ? data
        : null;
    case "deep":
      return typeof data.available === "boolean" ? data : null;
    default:
      return null;
  }
}

function normalizeHeroEra(raw: unknown): StoryHeroEra | null {
  if (!isRecord(raw)) return null;
  const id = nonEmptyString(raw.id);
  const matchCount = finiteNumber(raw.match_count);
  if (
    id === null ||
    matchCount === null ||
    typeof raw.empty !== "boolean" ||
    typeof raw.sparse !== "boolean" ||
    !isOneOf(raw.period_kind, ["calendar_month", "third"]) ||
    !hasStrings(raw, ["date_start", "date_end"])
  ) return null;
  const topHeroes = rankedRows<StoryEraHeroCount>(raw.top_heroes, ["matches"]);
  // The schema forbids an empty period from carrying rows.  A payload that
  // breaks that promise loses the rows rather than the period: we never carry
  // a previous period's ordering forward.
  if (!raw.empty && matchCount > 0 && topHeroes.length === 0) return null;
  return {
    ...(raw as unknown as StoryHeroEra),
    id,
    match_count: matchCount,
    top_heroes: raw.empty ? [] : topHeroes,
  };
}

/**
 * Keeps rows that carry a rank, a hero name, and every required numeric
 * field, in the order supplied.  It never reorders and never renumbers — the
 * backend owns ranking.
 */
function rankedRows<T>(raw: unknown, required: string[]): T[] {
  return asArray(raw).filter((row): row is T => {
    if (!isRecord(row)) return false;
    if (finiteNumber(row.rank) === null) return false;
    if (finiteNumber(row.hero_id) === null) return false;
    if (nonEmptyString(row.hero_name) === null) return false;
    return required.every((field) => finiteNumber(row[field]) !== null);
  });
}

function normalizeSlot(raw: unknown, family: "post_loss_response" | "transfer") {
  if (!isRecord(raw) || raw.available !== true || raw.family !== family || !isRecord(raw.content)) {
    return { available: false as const, family, content: null };
  }
  const content = raw.content;
  const claim = nonEmptyString(content.claim);
  const interpretation = nonEmptyString(content.interpretation);
  const confidence = content.confidence;
  if (
    claim === null ||
    interpretation === null ||
    content.family !== family ||
    !isRecord(content.claim_contract) ||
    !isOneOf(confidence, ["unavailable", "descriptive", "moderate", "high"]) ||
    content.cross_session_transitions !== false ||
    (family === "post_loss_response" && finiteNumber(content.comparable_opportunities) === null)
  ) {
    return { available: false as const, family, content: null };
  }
  return {
    available: true as const,
    family,
    content: {
      ...(content as unknown as StoryPayload["finding_slots"]["post_loss"]["content"]),
      claim,
      interpretation,
      evidence_refs: asArray(content.evidence_refs).filter((ref): ref is string => typeof ref === "string"),
      claim_contract: {
        ...(content.claim_contract as Rec),
        alternatives: asArray((content.claim_contract as Rec).alternatives).filter(
          (item): item is string => typeof item === "string",
        ),
      },
    },
  } as StoryPayload["finding_slots"]["post_loss"];
}

export function normalizeCardModule(value: unknown): StoryCardModuleKey | null {
  return typeof value === "string" && Object.prototype.hasOwnProperty.call(STORY_MODULE_PAGES, value)
    ? (value as StoryCardModuleKey)
    : null;
}
