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
  type StoryCard,
  type StoryCardModuleKey,
  type StoryEraHeroCount,
  type StoryHeroEra,
  type StoryModule,
  type StoryModuleKey,
  type StoryModules,
  type StoryPayload,
  type StoryState,
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
  if (!isRecord(raw)) return null;

  const modulesRaw = raw.modules;
  const universe = raw.universe;
  const findingSlots = raw.finding_slots;
  if (!isRecord(modulesRaw) || !isRecord(universe) || !isRecord(findingSlots)) return null;
  if (finiteNumber(universe.match_count) === null) return null;

  const modules = {} as StoryModules;
  for (const key of STORY_MODULE_KEYS) {
    modules[key] = normalizeModule(key, modulesRaw[key], diagnostics) as never;
  }

  const payload: StoryPayload = {
    ...(raw as unknown as StoryPayload),
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
    case "top_win_heroes":
      return { ...data, rows: rankedRows(data.rows, ["wins", "matches"]) };
    case "top_loss_heroes":
      return {
        ...data,
        rows: rankedRows(data.rows, ["losses", "matches"]),
        roughest_day: isRecord(data.roughest_day) ? data.roughest_day : null,
      };
    case "hero_pool": {
      const heroes = rankedRows(data.heroes, ["matches", "share"]);
      return { ...data, heroes };
    }
    case "hero_eras": {
      const periods = asArray(data.periods)
        .map(normalizeHeroEra)
        .filter((period): period is StoryHeroEra => period !== null);
      return { ...data, periods };
    }
    case "hero_era_payoff":
      return {
        ...data,
        persistence: isRecord(data.persistence) && isRecord(data.persistence.hero) ? data.persistence : null,
        takeover: isRecord(data.takeover) && isRecord(data.takeover.hero) ? data.takeover : null,
      };
    case "kills":
    case "assists":
    case "deaths": {
      if (finiteNumber(data.total) === null) return null;
      return {
        ...data,
        leading_hero: isRecord(data.leading_hero) ? data.leading_hero : null,
        individuals: asArray(data.individuals).filter(
          (row) => isRecord(row) && finiteNumber(row.rank) !== null,
        ),
      };
    }
    case "losing_streak":
      return { ...data, breaker: isRecord(data.breaker) ? data.breaker : null };
    case "win_summary":
      return { ...data, winningest_day: isRecord(data.winningest_day) ? data.winningest_day : null };
    case "card_collage": {
      const cards = asArray(data.cards).filter(
        (card): card is StoryCard =>
          isRecord(card) && nonEmptyString(card.id) !== null && typeof card.module === "string",
      );
      return { ...data, cards };
    }
    default:
      return data;
  }
}

function normalizeHeroEra(raw: unknown): StoryHeroEra | null {
  if (!isRecord(raw)) return null;
  const id = nonEmptyString(raw.id);
  const matchCount = finiteNumber(raw.match_count);
  if (id === null || matchCount === null || typeof raw.empty !== "boolean") return null;
  const topHeroes = rankedRows<StoryEraHeroCount>(raw.top_heroes, ["matches"]);
  // The schema forbids an empty period from carrying rows.  A payload that
  // breaks that promise loses the rows rather than the period: we never carry
  // a previous period's ordering forward.
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
    if (nonEmptyString(row.hero_name) === null) return false;
    return required.every((field) => finiteNumber(row[field]) !== null);
  });
}

function normalizeSlot(raw: unknown, family: "post_loss_response" | "transfer") {
  if (!isRecord(raw) || raw.available !== true || !isRecord(raw.content)) {
    return { available: false as const, family, content: null };
  }
  const content = raw.content;
  const claim = nonEmptyString(content.claim);
  const interpretation = nonEmptyString(content.interpretation);
  if (claim === null || interpretation === null || !isRecord(content.claim_contract)) {
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
  return typeof value === "string" ? (value as StoryCardModuleKey) : null;
}
