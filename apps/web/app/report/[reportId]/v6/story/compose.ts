/**
 * The composer.
 *
 * One `renderedPages` array is built here from `story_payload.page_manifest`
 * and then drives traversal, progress, the Page 29 recap, collage eligibility,
 * analytics indices, and navigation bounds.  There is no parallel page-count
 * logic anywhere else.
 *
 * Thirty-four numbered narrative slots, at most thirty-three renderable pages.
 * Page 25 and Chapter 8 do not exist: they get no entry here, no renderer, no
 * progress position, and no collage card.
 */

import {
  ARCHETYPE_NOT_READY_RENDER_EXCEPTION,
  ARCHETYPE_PLACEHOLDER,
  type ArchetypeAnchorKey,
} from "./archetype-placeholder";
import { ALWAYS_SILENT_PAGES, CHAPTERS, COPY, PAGE_CHAPTER, transferClosingLine } from "./copy";
import type { StoryDiagnostic } from "./copy-variants";
import type {
  StoryCardModuleKey,
  StoryModuleKey,
  StoryPayload,
  StoryState,
} from "./payload-types";
import { STORY_MODULE_KEYS, STORY_MODULE_PAGES } from "./payload-types";
import type { V6Element } from "../types";

/** Canonical Element keys, frozen in `player_analysis_v6/constants.py`. */
export const CANONICAL_ELEMENT_KEYS = [
  "breadth",
  "toolkit",
  "involvement",
  "finishing",
  "death_exposure",
  "transfer",
  "consistency",
] as const;

const CENTERED_PAGES: ReadonlySet<number> = new Set([1, 8, 14, 16, 20, 26, 29, 30, 33, 34]);

export type RenderedPage = {
  /** Stable across renders; also the analytics page id. */
  id: string;
  page: number;
  chapter: number;
  chapterName: string;
  module: StoryCardModuleKey | null;
  alignment: "center" | "left";
  /** Set by the frozen cadence pass, never by a per-page taste decision. */
  closesWithDryLine: boolean;
  /** Fixed transition copy appended when the following page was omitted. */
  transitionLine: string | null;
};

export type FinalIdentity = {
  displayName: string | null;
  storyMatchCount: number;
  lookbackDays: number;
  windowStart: string;
  windowEnd: string;
};

export type ComposedStory = {
  pages: RenderedPage[];
  payload: StoryPayload;
  elements: V6Element[];
  diagnostics: StoryDiagnostic[];
  /** Page 16 uses the combined transition when Post-Loss did not render. */
  heroBridgeCombined: boolean;
  /** Page 29 recap membership, gated on pages that actually rendered. */
  recapLines: string[];
  /** Page 31 anchor membership, gated on pages that actually rendered. */
  archetypeAnchors: ArchetypeAnchorKey[];
  finalIdentity: FinalIdentity | null;
  deepDestination: string | null;
};

type ManifestEntry = { page: number; module: StoryCardModuleKey | null };

function moduleState(payload: StoryPayload, key: StoryModuleKey): StoryState {
  return payload.modules[key]?.state ?? "omitted";
}

/**
 * A module renders on `available` or `degraded` — and, for exactly the two
 * keys in `ARCHETYPE_NOT_READY_RENDER_EXCEPTION`, on `not_ready`.  Any other
 * `not_ready` or `omitted` module stays absent.  See archetype-placeholder.ts.
 */
export function moduleRenders(payload: StoryPayload, key: StoryModuleKey): boolean {
  const state = moduleState(payload, key);
  if (state === "available" || state === "degraded") return true;
  return state === "not_ready" && ARCHETYPE_NOT_READY_RENDER_EXCEPTION.has(key);
}

function parseManifest(payload: StoryPayload, diagnostics: StoryDiagnostic[]): ManifestEntry[] {
  const seen = new Set<number>();
  const entries: ManifestEntry[] = [];
  for (const item of payload.page_manifest) {
    const entry = readManifestItem(item);
    if (entry === null) {
      diagnostics.push({
        code: "malformed_manifest_entry",
        module: "page_manifest",
        detail: JSON.stringify(item),
      });
      continue;
    }
    // Page 25 is structurally unrepresentable upstream.  Enforce it here too
    // so a hand-edited payload cannot introduce it.
    if (entry.page === 25 || entry.page === 28 || entry.page < 1 || entry.page > 34) continue;
    if (seen.has(entry.page)) continue;
    if (!manifestEntryIsShippable(payload, entry)) continue;
    seen.add(entry.page);
    entries.push(entry);
  }
  return entries
    .filter((entry) => entry.page !== 26 || seen.has(24))
    .sort((left, right) => left.page - right.page);
}

function readManifestItem(item: StoryPayload["page_manifest"][number]): ManifestEntry | null {
  if (typeof item === "number") {
    return { page: item, module: moduleForPage(item) };
  }
  if (typeof item === "string") {
    const page = STORY_MODULE_PAGES[item as StoryCardModuleKey];
    if (typeof page === "number") return { page, module: item as StoryCardModuleKey };
    const match = /(?:page|p)[-_ ]?(\d+)/i.exec(item);
    return match ? { page: Number(match[1]), module: moduleForPage(Number(match[1])) } : null;
  }
  if (item && typeof item === "object") {
    const declared = typeof item.module === "string" ? (item.module as StoryCardModuleKey) : null;
    const explicit = typeof item.page === "number" ? item.page : null;
    const fromModule = declared ? STORY_MODULE_PAGES[declared] : undefined;
    const idMatch = typeof item.id === "string" ? /^(?:page|p)[-_ ]?(\d+)$/i.exec(item.id) : null;
    const page = explicit ?? fromModule ?? (idMatch ? Number(idMatch[1]) : null);
    if (page === null || !Number.isFinite(page)) return null;
    // A module whose declared page contradicts the frozen map is not trusted.
    if (declared && fromModule !== undefined && fromModule !== page) return null;
    return { page, module: declared ?? moduleForPage(page) };
  }
  return null;
}

function moduleForPage(page: number): StoryCardModuleKey | null {
  const found = (Object.keys(STORY_MODULE_PAGES) as StoryCardModuleKey[]).find(
    (key) => STORY_MODULE_PAGES[key] === page,
  );
  return found ?? null;
}

function manifestEntryIsShippable(payload: StoryPayload, entry: ManifestEntry): boolean {
  const key = entry.module;
  if (key === null) return entry.page === 26;
  if (key === "post_loss") return payload.finding_slots.post_loss.available;
  if (key === "transfer") return payload.finding_slots.transfer.available;
  // No validated destination ships in this release, so Page 34 cannot be a
  // usable manifest entry even if hand-edited JSON marks Deep available.
  if (key === "deep") return false;
  if (!(STORY_MODULE_KEYS as readonly string[]).includes(key)) return false;
  // Normalization may have demoted this module (unknown copy_variant,
  // unusable data).  Omission propagates from there to here.
  return moduleRenders(payload, key as StoryModuleKey);
}

/**
 * Page 33's data.  `modules.final_identity_card.data` is null in the shipped
 * payload — the plan states otherwise, and the code wins.  Rather than drop
 * the ending, the non-archetype values are read from the fields the schema
 * already binds them to: `universe.match_count` is validator-forced to equal
 * `modules.match_count.data.match_count`, and the window is the same window.
 * This is a documented deviation, scoped to this one function, and it is
 * deleted together with the exception when the module ships real data.
 */
function resolveFinalIdentity(payload: StoryPayload): FinalIdentity | null {
  const supplied = payload.modules.final_identity_card.data;
  if (supplied) {
    return {
      displayName: supplied.display_name ?? null,
      storyMatchCount: supplied.story_match_count,
      lookbackDays: supplied.lookback_days,
      windowStart: supplied.window_start,
      windowEnd: supplied.window_end,
    };
  }
  const universe = payload.universe;
  if (!universe || typeof universe.match_count !== "number") return null;
  return {
    displayName: payload.modules.hello.data?.display_name ?? payload.identity?.display_name ?? null,
    storyMatchCount: universe.match_count,
    lookbackDays: universe.requested_window_days,
    windowStart: universe.window_start,
    windowEnd: universe.window_end,
  };
}

/**
 * Page 34 needs BOTH availability and a valid destination.  The payload ships
 * `modules.deep.data.available` and no destination field, and no validated
 * frontend route contract supplies one, so the page is composed out.  A
 * disabled or dead CTA is never rendered.  Plan Risk 9.
 */
export function resolveDeepDestination(payload: StoryPayload): string | null {
  const available = payload.modules.deep.state === "available" && payload.modules.deep.data?.available === true;
  if (!available) return null;
  return null;
}

/** Which pages own a dry line before the frozen cadence rule is applied. */
function pageOwnsDryLine(payload: StoryPayload, page: number, present: ReadonlySet<number>): boolean {
  if (ALWAYS_SILENT_PAGES.has(page)) return false;
  const modules = payload.modules;
  switch (page) {
    case 1:
      // "Yes. All of it." claims completeness the short-history branch declines.
      return modules.hello.data?.history_materially_short === false;
    case 2:
    case 3:
    case 5:
    case 11:
    case 13:
    case 18:
    case 32:
      return true;
    case 6:
      // Optional; dropped when volume is low or hours were unavailable.
      return modules.busiest_day.copy_variant === "hours" && payload.universe.volume_tier !== "limited";
    case 7:
      return modules.longest_match.data?.refused_to_end === true && modules.longest_match.data?.outcome === "win";
    case 8:
      // Page-specific scripted second line.  See plan Risk 11 — no further
      // bridge humour is added anywhere.
      return modules.wins_bridge.copy_variant === "wins";
    case 10:
      return modules.winning_streak.copy_variant === "streak";
    case 12:
      return modules.losing_streak.data?.terminal_state === "broken_by_win";
    case 17:
      return modules.hero_pool.copy_variant === "concentrated" || modules.hero_pool.copy_variant === "broad";
    case 19:
      return modules.hero_era_payoff.copy_variant === "takeover" || modules.hero_era_payoff.copy_variant === "persistence";
    case 21:
      return transferClosingLine(payload.finding_slots.transfer.content?.semantic_outcome_key) !== null;
    case 23:
    case 24:
      return (page === 23 ? modules.assists.data?.total : modules.deaths.data?.total) !== 0;
    case 34:
      return present.has(34);
    default:
      return false;
  }
}

/**
 * The frozen cadence rule: no more than two consecutive rendered pages may
 * close with a dry line.  Applied over the composed sequence, so a report that
 * omits pages does not accidentally stack three jokes.
 */
function applyDryLineCadence(pages: RenderedPage[]): void {
  let run = 0;
  for (const page of pages) {
    if (!page.closesWithDryLine) {
      run = 0;
      continue;
    }
    if (run >= 2) {
      page.closesWithDryLine = false;
      run = 0;
      continue;
    }
    run += 1;
  }
}

export function composeStory(payload: StoryPayload, elements: V6Element[], diagnostics: StoryDiagnostic[]): ComposedStory {
  const manifest = parseManifest(payload, diagnostics);
  const pageNumbers = new Set(manifest.map((entry) => entry.page));
  const moduleByPage = new Map(manifest.map((entry) => [entry.page, entry.module]));

  const usableElements = elements.filter(
    (element) => typeof element?.key === "string" && typeof element?.label === "string",
  );

  const has = (page: number) => pageNumbers.has(page);
  const add = (page: number, module: StoryCardModuleKey | null = null) => {
    if (pageNumbers.has(page)) return;
    pageNumbers.add(page);
    moduleByPage.set(page, module);
  };

  // Frontend-owned bridges and pages that carry no backend module.  Each is
  // gated on the page it introduces, so no bridge is ever orphaned.
  if (has(15)) add(14);
  if (has(17) || has(18) || has(19)) add(16);
  if (has(21)) add(20);
  if (has(26) && usableElements.length > 0) add(27);

  // THE NARROW EXCEPTION — archetype pages only.  Nothing else consults
  // `not_ready` state, and `moduleRenders` is the only gate that knows about it.
  const archetypeRenders = moduleRenders(payload, "archetype");
  const finalIdentity = moduleRenders(payload, "final_identity_card") ? resolveFinalIdentity(payload) : null;

  const recapLines: string[] = [];
  if (has(2)) recapLines.push(COPY.page29.lines.played);
  if (has(9) || has(10) || has(11)) recapLines.push(COPY.page29.lines.won);
  if (has(15)) recapLines.push(COPY.page29.lines.losses);
  if (has(17) || has(18) || has(19)) recapLines.push(COPY.page29.lines.stayed);
  if (has(21)) recapLines.push(COPY.page29.lines.changed);

  const archetypeAnchors: ArchetypeAnchorKey[] = [];
  if (has(17)) archetypeAnchors.push("hero_pool");
  if (has(15)) archetypeAnchors.push("post_loss");
  if (has(21)) archetypeAnchors.push("transfer");

  if (archetypeRenders) {
    add(29, "archetype");
    add(30, "archetype");
    // Page 31 explains the archetype from evidence that actually rendered.
    // With fewer than two defensible anchors there is nothing to explain, and
    // the script forbids inventing one for layout symmetry.
    if (archetypeAnchors.length >= 2) add(31, "archetype");
  }
  if (finalIdentity) add(33, "final_identity_card");

  const deepDestination = resolveDeepDestination(payload);
  if (deepDestination) add(34, "deep");

  const ordered = [...pageNumbers].sort((left, right) => left - right);
  const pages: RenderedPage[] = ordered.map((page) => {
    const chapter = PAGE_CHAPTER[page] ?? 1;
    return {
      id: `page-${page}`,
      page,
      chapter,
      chapterName: CHAPTERS[chapter] ?? "",
      module: moduleByPage.get(page) ?? null,
      alignment: CENTERED_PAGES.has(page) ? "center" : "left",
      closesWithDryLine: pageOwnsDryLine(payload, page, pageNumbers),
      transitionLine: null,
    };
  });

  // Transfer absent: Page 19, or Page 18 if 19 is absent, carries the fixed
  // direct transition into combat.
  if (!has(21) && has(22)) {
    const carrier = pages.find((item) => item.page === 19) ?? pages.find((item) => item.page === 18);
    if (carrier) carrier.transitionLine = COPY.page20.directToCombat;
  }

  applyDryLineCadence(pages);

  return {
    pages,
    payload,
    elements: usableElements,
    diagnostics,
    heroBridgeCombined: !has(15),
    recapLines,
    archetypeAnchors,
    finalIdentity,
    deepDestination,
  };
}

export { ARCHETYPE_PLACEHOLDER };
export type { ArchetypeAnchorKey };
