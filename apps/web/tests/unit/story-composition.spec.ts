import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ARCHETYPE_NOT_READY_RENDER_EXCEPTION } from "../../app/report/[reportId]/v6/story/archetype-placeholder";
import { buildCollageCards, collageSpans } from "../../app/report/[reportId]/v6/story/collage";
import { composeStory, moduleRenders } from "../../app/report/[reportId]/v6/story/compose";
import { COPY } from "../../app/report/[reportId]/v6/story/copy";
import { COPY_VARIANTS } from "../../app/report/[reportId]/v6/story/copy-variants";
import { formatPeriodLabel, formatStoryDate } from "../../app/report/[reportId]/v6/story/format";
import { initialHeroEraIndex } from "../../app/report/[reportId]/v6/story/hero-eras-selection";
import { normalizeStoryPayload } from "../../app/report/[reportId]/v6/story/normalize-story";
import { yearShape } from "../../app/report/[reportId]/v6/story/year-shape";
import { STORY_MODULE_KEYS } from "../../app/report/[reportId]/v6/story/payload-types";
import { beatOffsets, MOTION } from "../../app/report/[reportId]/v6/story/motion";
import type { StoryHeroEra, StoryPayload } from "../../app/report/[reportId]/v6/story/payload-types";

const FIXTURE_DIR = path.join(__dirname, "..", "fixtures", "persisted-reports");

function fixture(name: string): unknown {
  return JSON.parse(readFileSync(path.join(FIXTURE_DIR, `${name}.json`), "utf8"));
}

function compose(name: string) {
  const normalized = normalizeStoryPayload(fixture(name));
  expect(normalized).not.toBeNull();
  return composeStory(normalized!.payload, [], normalized!.diagnostics);
}

function pageNumbers(name: string): number[] {
  return compose(name).pages.map((page) => page.page);
}

// The elements array is supplied separately; page 27 only exists with it.
function composeWithElements(name: string) {
  const normalized = normalizeStoryPayload(fixture(name))!;
  const elements = [
    "breadth",
    "toolkit",
    "involvement",
    "finishing",
    "death_exposure",
    "transfer",
    "consistency",
  ].map((key) => ({ key, label: key, status: "available" }));
  return composeStory(normalized.payload, elements as never, normalized.diagnostics);
}

test.describe("hero era presentation default", () => {
  const era = (id: string, empty: boolean): StoryHeroEra => ({
    id,
    period_kind: "calendar_month",
    date_start: `2025-${id}-01`,
    date_end: `2025-${id}-28`,
    match_count: empty ? 0 : 4,
    empty,
    sparse: false,
    top_heroes: [],
  });

  test("opens on the most recent non-empty period", () => {
    expect(initialHeroEraIndex([era("01", false), era("02", false), era("03", false)])).toBe(2);
  });

  test("skips a trailing empty period", () => {
    expect(initialHeroEraIndex([era("01", false), era("02", false), era("03", true)])).toBe(1);
  });

  test("skips several trailing empty periods", () => {
    expect(initialHeroEraIndex([era("01", false), era("02", true), era("03", true)])).toBe(0);
  });

  test("falls back to the last period when every period is empty", () => {
    expect(initialHeroEraIndex([era("01", true), era("02", true)])).toBe(1);
  });
});

test.describe("the narrow archetype exception", () => {
  test("covers exactly two modules", () => {
    expect([...ARCHETYPE_NOT_READY_RENDER_EXCEPTION].sort()).toEqual(["archetype", "final_identity_card"]);
  });

  test("no other module renders while not_ready", () => {
    const normalized = normalizeStoryPayload(fixture("v61-story-payload-both"))!;
    for (const key of STORY_MODULE_KEYS) {
      const payload = {
        ...normalized.payload,
        modules: {
          ...normalized.payload.modules,
          [key]: { state: "not_ready", reason: "test", copy_variant: null, data: null },
        },
      } as StoryPayload;
      const expected = ARCHETYPE_NOT_READY_RENDER_EXCEPTION.has(key);
      expect(moduleRenders(payload, key), `${key} must not render on not_ready`).toBe(expected);
    }
  });
});

test.describe("copy_variant vocabulary", () => {
  test("an unrecognised variant omits the module and emits a diagnostic", () => {
    const raw = fixture("v61-story-payload-both") as { modules: Record<string, unknown> };
    raw.modules.hero_pool = {
      state: "available",
      reason: null,
      copy_variant: "sideways",
      data: { heroes: [], total_matches: 0, top_five_share: 0, concentration_band: null },
    };
    const normalized = normalizeStoryPayload(raw);
    expect(normalized).not.toBeNull();
    expect(normalized!.payload.modules.hero_pool.state).toBe("omitted");
    expect(normalized!.diagnostics.map((item) => item.code)).toContain("unrecognised_copy_variant");
    const story = composeStory(normalized!.payload, [], normalized!.diagnostics);
    expect(story.pages.map((page) => page.page)).not.toContain(17);
  });

  test("the registry covers every module key", () => {
    for (const key of STORY_MODULE_KEYS) {
      expect(COPY_VARIANTS[key].size, `${key} has no vocabulary`).toBeGreaterThan(0);
    }
  });

  test("the shipped fixtures only use known variants", () => {
    for (const name of [
      "v61-story-payload-both",
      "v61-story-payload-none",
      "v61-story-payload-post-loss",
      "v61-story-payload-transfer",
      "v61-story-payload-degraded",
      "v61-story-payload-long-streak",
    ]) {
      const normalized = normalizeStoryPayload(fixture(name))!;
      expect(
        normalized.diagnostics.filter((item) => item.code === "unrecognised_copy_variant"),
        `${name} produced an unknown variant`,
      ).toEqual([]);
    }
  });
});

test.describe("composed page arrays", () => {
  const descriptive = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 18, 19, 22, 23, 24, 26, 27, 32];

  test("both findings present", () => {
    const pages = composeWithElements("v61-story-payload-both").pages.map((page) => page.page);
    expect(pages).toEqual([...descriptive, 14, 15, 20, 21, 29, 30, 33].sort((a, b) => a - b));
  });

  test("post-loss only", () => {
    const pages = composeWithElements("v61-story-payload-post-loss").pages.map((page) => page.page);
    expect(pages).toContain(14);
    expect(pages).toContain(15);
    expect(pages).not.toContain(20);
    expect(pages).not.toContain(21);
  });

  test("transfer only", () => {
    const pages = composeWithElements("v61-story-payload-transfer").pages.map((page) => page.page);
    expect(pages).toContain(20);
    expect(pages).toContain(21);
    expect(pages).not.toContain(14);
    expect(pages).not.toContain(15);
  });

  test("neither finding still completes the descriptive spine", () => {
    const story = composeWithElements("v61-story-payload-none");
    const pages = story.pages.map((page) => page.page);
    expect(pages).not.toContain(14);
    expect(pages).not.toContain(20);
    expect(pages).toContain(16);
    expect(story.heroBridgeCombined).toBe(true);
    // Page 19 carries the fixed transition into combat.
    expect(story.pages.find((page) => page.page === 19)?.transitionLine).toBe(
      "The names changed. The scoreboard kept the count.",
    );
  });

  test("page 25, Death Context, and Chapter 8 never appear", () => {
    for (const name of [
      "v61-story-payload-both",
      "v61-story-payload-none",
      "v61-story-payload-degraded",
    ]) {
      const story = composeWithElements(name);
      expect(story.pages.map((page) => page.page)).not.toContain(25);
      expect(story.pages.map((page) => page.chapter)).not.toContain(8);
      expect(JSON.stringify(story.pages)).not.toMatch(/death[-_ ]context/i);
    }
  });

  test("page 28 stays absent — it has no exception", () => {
    expect(composeWithElements("v61-story-payload-both").pages.map((page) => page.page)).not.toContain(28);
  });

  test("page 34 is absent while the payload supplies no destination", () => {
    const story = composeWithElements("v61-story-payload-both");
    expect(story.deepDestination).toBeNull();
    expect(story.pages.map((page) => page.page)).not.toContain(34);
  });

  test("the degraded run still reaches an ending", () => {
    const story = composeWithElements("v61-story-payload-degraded");
    const pages = story.pages.map((page) => page.page);
    expect(pages).not.toContain(7);
    expect(pages).not.toContain(12);
    expect(pages).not.toContain(17);
    expect(pages).toContain(32);
    expect(pages[pages.length - 1]).toBe(33);
    // No qualified identity anchors: page 31 is omitted rather than inferred.
    expect(pages).not.toContain(31);
  });

  test("recap membership follows rendered pages only", () => {
    expect(composeWithElements("v61-story-payload-none").recapLines).not.toContain("What happened after losses.");
    expect(composeWithElements("v61-story-payload-both").recapLines).toContain(
      "And what followed you when they changed.",
    );
  });

  test("a zero-win summary never recaps how the player won", () => {
    const raw = fixture("v61-story-payload-both") as {
      modules: { win_summary: { copy_variant: string; data: { wins: number; winningest_day: unknown } } };
    };
    raw.modules.win_summary.copy_variant = "zero";
    raw.modules.win_summary.data = { wins: 0, winningest_day: null };
    const normalized = normalizeStoryPayload(raw)!;
    expect(composeStory(normalized.payload, [], normalized.diagnostics).recapLines).not.toContain("How you won.");
  });

  test("signal support copy uses the number that rendered", () => {
    expect(COPY.page27.support(1)).toBe("One signal. It is not the whole story.");
    expect(COPY.page27.support(3)).toBe("3 signals. None of them is the whole story.");
  });

  test("no bridge is orphaned", () => {
    for (const name of ["v61-story-payload-both", "v61-story-payload-none", "v61-story-payload-degraded"]) {
      const pages = new Set(composeWithElements(name).pages.map((page) => page.page));
      if (pages.has(14)) expect(pages.has(15)).toBe(true);
      if (pages.has(20)) expect(pages.has(21)).toBe(true);
      if (pages.has(16)) expect(pages.has(17) || pages.has(18) || pages.has(19)).toBe(true);
    }
  });

  test("rejects synthetic pages that are not connected to their source page", () => {
    const raw = fixture("v61-story-payload-both") as { page_manifest: unknown[] };
    raw.page_manifest = [
      { page: 26, module: null },
      { page: 31, module: null },
    ];
    const normalized = normalizeStoryPayload(raw)!;
    const story = composeStory(normalized.payload, [{ key: "breadth", label: "Breadth" }] as never, []);
    expect(story.pages.map((page) => page.page)).not.toEqual(expect.arrayContaining([26, 27, 31]));
  });

  test("keeps unimplemented analytical and Deep pages out of hand-edited manifests", () => {
    const raw = fixture("v61-story-payload-both") as {
      modules: Record<string, unknown>;
      page_manifest: unknown[];
    };
    raw.modules.element_distinctiveness = {
      state: "available",
      reason: null,
      copy_variant: "not_ready",
      data: { rows: [], nothing_meaningfully_stands_out: true },
    };
    raw.modules.deep = {
      state: "available",
      reason: null,
      copy_variant: "available",
      data: { available: true },
    };
    raw.page_manifest.push({ page: 28, module: "element_distinctiveness" }, { page: 34, module: "deep" });
    const normalized = normalizeStoryPayload(raw)!;
    const pages = composeStory(normalized.payload, [], []).pages.map((page) => page.page);
    expect(pages).not.toEqual(expect.arrayContaining([28, 34]));
  });
});

test.describe("curated closes and narrative rhythm", () => {
  test("only evidence-earned pages receive a dry close", () => {
    const dryPages = composeWithElements("v61-story-payload-both").pages
      .filter((page) => page.closesWithDryLine)
      .map((page) => page.page);
    expect(dryPages).toEqual([7, 10, 12, 18, 21]);
  });

  test("the longest-match close requires the supplied refused-and-win branch", () => {
    const raw = fixture("v61-story-payload-both") as {
      modules: { longest_match: { data: { refused_to_end: boolean; outcome: string } } };
    };
    raw.modules.longest_match.data.refused_to_end = false;
    const normalized = normalizeStoryPayload(raw)!;
    const page = composeStory(normalized.payload, [], normalized.diagnostics).pages.find((item) => item.page === 7);
    expect(page?.closesWithDryLine).toBe(false);
  });

  test("the breaker and non-sparse chronology gates stay conditional", () => {
    const raw = fixture("v61-story-payload-both") as {
      modules: {
        losing_streak: { data: { terminal_state: string; breaker: unknown } };
        hero_eras: { copy_variant: string; data: { sparse_fallback: boolean } };
      };
    };
    raw.modules.losing_streak.data.terminal_state = "observation_ended";
    raw.modules.losing_streak.data.breaker = null;
    raw.modules.hero_eras.copy_variant = "sparse_fallback";
    raw.modules.hero_eras.data.sparse_fallback = true;
    const normalized = normalizeStoryPayload(raw)!;
    const pages = composeStory(normalized.payload, [], normalized.diagnostics).pages;
    expect(pages.find((item) => item.page === 12)?.closesWithDryLine).toBe(false);
    expect(pages.find((item) => item.page === 18)?.closesWithDryLine).toBe(false);
  });

  test("question, accumulation, and hold timings remain distinct", () => {
    expect(beatOffsets({ total: 2, rhythm: "question" })[1]).toBeGreaterThan(
      beatOffsets({ total: 2, rhythm: "immediate" })[1],
    );
    expect(beatOffsets({ total: 4, rhythm: "accumulation" })).toEqual([0, 320, 640, 960]);
    expect(beatOffsets({ total: 3, rhythm: "immediate", holdAfter: 0 })).toEqual([
      0,
      MOTION.settle + MOTION.factHold,
      MOTION.settle + MOTION.factHold + 300,
    ]);
    expect(beatOffsets({ total: 3, rhythm: "quiet", identityHoldAfter: 0 })).toEqual([
      0,
      MOTION.identityHold,
      MOTION.identityHold + 700,
    ]);
  });
});

test.describe("collage geometry", () => {
  test("mirrors rendered manifest cards, minus the duplicate win total", () => {
    const normalized = normalizeStoryPayload(fixture("v61-story-payload-both"))!;
    const story = composeWithElements("v61-story-payload-both");
    const manifest = normalized.payload.modules.card_collage.data!.cards;
    const pages = new Set(story.pages.map((page) => page.page));
    const cards = buildCollageCards(normalized.payload, manifest, pages);

    // `wins_bridge` carries only `{wins}`, the same number `win_summary`
    // already shows, so mirroring it puts the identical card on the grid
    // twice. The manifest is still the source of membership; this is the one
    // module whose card is dropped, and only because it duplicates another.
    expect(cards.map((card) => card.module)).not.toContain("wins_bridge");
    expect(cards).toHaveLength(manifest.length - 1);
    expect(cards.filter((card) => card.module === "win_summary")).toHaveLength(1);

    // Page gating still governs every other card.
    pages.delete(22);
    expect(buildCollageCards(normalized.payload, manifest, pages).map((card) => card.module)).not.toContain("kills");
  });

  test("completes every row at any card count", () => {
    for (let total = 1; total <= 24; total += 1) {
      for (let index = 0; index < total; index += 1) {
        const spans = collageSpans(index, total);
        expect([2, 4]).toContain(spans.narrow);
        expect([2, 3, 6]).toContain(spans.wide);
      }
      const narrow = Array.from({ length: total }, (_item, index) => collageSpans(index, total).narrow);
      const wide = Array.from({ length: total }, (_item, index) => collageSpans(index, total).wide);
      expect(narrow.reduce((sum, value) => sum + value, 0) % 4, `narrow remainder at ${total}`).toBe(0);
      expect(wide.reduce((sum, value) => sum + value, 0) % 6, `wide remainder at ${total}`).toBe(0);
    }
  });
});

test.describe("normalization repairs structure without inventing meaning", () => {
  test("a malformed hero era row is dropped, not replaced", () => {
    const raw = fixture("v61-story-payload-both") as { modules: Record<string, { data: { periods: unknown[] } }> };
    const periods = raw.modules.hero_eras.data.periods as Array<{ top_heroes: unknown[] }>;
    periods[0].top_heroes = [
      { rank: 1, hero_id: 1, hero_name: "Kept", matches: 3 },
      { rank: 2, hero_id: 2, hero_name: null, matches: 2 },
    ];
    const normalized = normalizeStoryPayload(raw)!;
    expect(normalized.payload.modules.hero_eras.data?.periods[0].top_heroes).toHaveLength(1);
  });

  test("a report without a story payload does not compose", () => {
    expect(normalizeStoryPayload(undefined)).toBeNull();
    expect(normalizeStoryPayload({ modules: {} })).toBeNull();
  });

  test("an unknown payload version or malformed root falls back to legacy", () => {
    const future = fixture("v61-story-payload-both") as Record<string, unknown>;
    future.version = "free-story-payload-2.0.0";
    expect(normalizeStoryPayload(future)).toBeNull();

    const malformed = fixture("v61-story-payload-both") as { universe: Record<string, unknown> };
    delete malformed.universe.history_completeness;
    expect(normalizeStoryPayload(malformed)).toBeNull();
  });

  test("an available module with unusable data is omitted before composition", () => {
    const raw = fixture("v61-story-payload-both") as { modules: Record<string, unknown> };
    raw.modules.match_count = { state: "available", reason: null, copy_variant: "normal", data: {} };
    const normalized = normalizeStoryPayload(raw)!;
    expect(normalized.payload.modules.match_count.state).toBe("omitted");
    expect(composeStory(normalized.payload, [], []).pages.map((page) => page.page)).not.toContain(2);
  });

  test("invalid calendar values are never silently normalized", () => {
    expect(formatStoryDate("2025-02-31")).toBe("");
    expect(formatPeriodLabel("2025-13")).toBe("2025-13");
  });
});


test.describe("the shape of the year names itself only from supplied variants", () => {
  function withModules(overrides: Record<string, unknown>) {
    const normalized = normalizeStoryPayload(fixture("v61-story-payload-both"))!;
    return {
      ...normalized.payload,
      modules: { ...normalized.payload.modules, ...overrides },
    } as StoryPayload;
  }

  test("a supplied takeover names the year after that hero", () => {
    const shape = yearShape(normalizeStoryPayload(fixture("v61-story-payload-both"))!.payload);
    expect(shape?.title).toBe("The Hero Zeta Year");
    expect(shape?.source).toBe("hero_era_payoff:takeover");
  });

  test("a supplied persistence names the year after that hero", () => {
    const shape = yearShape(
      withModules({
        hero_era_payoff: {
          state: "available",
          reason: null,
          copy_variant: "persistence",
          data: { persistence: { hero: { hero_id: 4, hero_name: "Hero Delta" }, top_five_periods: 9 }, takeover: null, steady_pool: false },
        },
      }),
    );
    expect(shape?.title).toBe("The Hero Delta Year");
  });

  test("it falls back to the supplied concentration band", () => {
    const shape = yearShape(
      withModules({
        hero_era_payoff: { state: "omitted", reason: "unavailable", copy_variant: "unavailable", data: null },
      }),
    );
    expect(shape?.source).toBe("hero_pool:concentrated");
  });

  test("with neither variant supplied it names nothing", () => {
    const shape = yearShape(
      withModules({
        hero_era_payoff: { state: "omitted", reason: "unavailable", copy_variant: "unavailable", data: null },
        hero_pool: { state: "omitted", reason: "unavailable", copy_variant: "unavailable", data: null },
      }),
    );
    // Absence is never filled in; the caller uses the neutral constant.
    expect(shape).toBeNull();
  });

  test("a neutral band is not a shape", () => {
    const shape = yearShape(
      withModules({
        hero_era_payoff: { state: "omitted", reason: "unavailable", copy_variant: "unavailable", data: null },
        hero_pool: { state: "available", reason: null, copy_variant: "neutral", data: { heroes: [], total_matches: 0, top_five_share: 0, concentration_band: null } },
      }),
    );
    expect(shape).toBeNull();
  });

  test("the degraded fixture still reaches a shape or an honest null", () => {
    const normalized = normalizeStoryPayload(fixture("v61-story-payload-degraded"))!;
    const shape = yearShape(normalized.payload);
    // Whatever it returns, it may never invent a hero the payload did not name.
    if (shape) expect(shape.source).toMatch(/^(hero_era_payoff|hero_pool):/);
  });
});
