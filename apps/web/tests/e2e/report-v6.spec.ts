import { expect, test, type Page } from "@playwright/test";

async function currentPageId(page: Page): Promise<string> {
  return (await page.locator("[data-page-id]").getAttribute("data-page-id")) ?? "";
}

async function goTo(page: Page, target: string): Promise<void> {
  for (let index = 0; index < 20; index += 1) {
    const current = await currentPageId(page);
    if (current === target) return;
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect.poll(() => currentPageId(page)).not.toBe(current);
  }
  throw new Error(`Page ${target} was not reached`);
}

async function pageIds(page: Page): Promise<string[]> {
  const progress = page.getByRole("progressbar");
  const total = Number(await progress.getAttribute("aria-valuemax"));
  const ids: string[] = [];
  for (let index = 0; index < total; index += 1) {
    const current = await currentPageId(page);
    ids.push(current);
    if (index < total - 1) {
      await page.getByRole("button", { name: "Next", exact: true }).click();
      await expect.poll(() => currentPageId(page)).not.toBe(current);
    }
  }
  return ids;
}

test.describe("Free Dota DNA v6.1 story", () => {
  for (const findingCount of [0, 1, 2, 3]) {
    test(`${findingCount} published records compose only their eligible family pages`, async ({ page }) => {
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto(`/report/v61-${findingCount}-fixture`);
      const ids = await pageIds(page);
      expect(ids).toHaveLength(12 + Math.max(0, findingCount - 1));
      expect(ids.filter((id) => id.startsWith("finding-"))).toEqual(
        ["finding-transfer", "finding-post-loss"].slice(0, Math.max(0, findingCount - 1)),
      );
      await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuetext", `Page ${ids.length} of ${ids.length}`);
    });
  }

  test("keeps finding families in story order and caps conditional findings at three", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/report/v61-5-fixture");
    const ids = await pageIds(page);
    expect(ids.filter((id) => id.startsWith("finding-"))).toEqual(["finding-transfer", "finding-post-loss", "finding-combat"]);
    expect(ids).not.toContain("finding-session");

    await page.goto("/report/v61-session-fixture");
    expect(await pageIds(page)).toContain("finding-session");
  });

  test("places Pool Shape on exactly one eligible structure page", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/report/v61-movement-fixture");
    const claim = "Your hero names cover more ground than the jobs behind them.";
    await goTo(page, "pool-layers");
    await expect(page.locator("[data-page-id='pool-layers']")).not.toContainText(claim);
    await goTo(page, "pool-movement");
    await expect(page.locator("[data-page-id='pool-movement']")).toContainText(claim);
  });

  test("omits pages whose hero, band, chronology, coherence, or Signature gates fail", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    const cases: Array<[string, string[]]> = [
      ["v61-no-heroes-fixture", ["lead-hero", "hero-front-row", "pool-layers"]],
      ["v61-no-bands-fixture", ["pool-layers"]],
      ["v61-no-chronology-fixture", ["pool-movement"]],
      ["v61-no-identity-fixture", ["coherence", "signature-setup", "signature-reveal"]],
    ];
    for (const [fixture, omitted] of cases) {
      await page.goto(`/report/${fixture}`);
      const ids = await pageIds(page);
      for (const id of omitted) expect(ids).not.toContain(id);
    }
  });

  test("scope receipt, Back/Next, arrows, reduced motion, and Read again work", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/report/v61-2-fixture");
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.locator("[data-page-id='scope-receipt']")).toContainText("365 days");
    await expect(page.locator("[data-page-id='scope-receipt']")).toContainText("Death Exposure");
    await page.locator("[data-page-id] h1").focus();
    await page.keyboard.press("ArrowRight");
    await expect.poll(() => currentPageId(page)).toBe("lead-hero");
    await page.locator("[data-page-id] h1").focus();
    await page.keyboard.press("ArrowLeft");
    await expect.poll(() => currentPageId(page)).toBe("scope-receipt");
    await goTo(page, "end");
    await page.getByRole("button", { name: "Read again" }).click();
    await expect.poll(() => currentPageId(page)).toBe("arrival");
    await expect(page.getByRole("heading", { name: /a year of Dota left receipts/ })).toBeFocused();
  });

  test("historical persisted v6.1 reports render in the new story UI", async ({ page }) => {
    const pageErrors: Error[] = [];
    const consoleErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error));
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });

    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/report/v61-historical-production-fixture");
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("[data-page-id]")).toHaveAttribute("data-page-id", "arrival");

    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.locator("[data-page-id='scope-receipt']")).toContainText("365 days");
    await page.waitForTimeout(4_500);
    expect(pageErrors.map((error) => error.message), consoleErrors.join("\n")).toEqual([]);
    await expect(page.getByRole("heading", { name: /This report couldn’t load\./ })).toHaveCount(0);
    await page.getByRole("button", { name: "Back", exact: true }).click();
    await expect(page.locator("[data-page-id]")).toHaveAttribute("data-page-id", "arrival");

    const ids = await pageIds(page);
    expect(ids).toContain("share");
    expect(ids).toContain("end");
    expect(ids).not.toContain("pool-layers");

    await page.goto("/report/v61-historical-production-fixture");
    await goTo(page, "pool-width");
    const evidence = page.getByRole("button", { name: "Why this?" });
    if (await evidence.count()) {
      await evidence.click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).toBeHidden();
    }

    await goTo(page, "end");
    await page.getByRole("button", { name: "Back", exact: true }).click();
    await expect(page.locator("[data-page-id]")).not.toHaveAttribute("data-page-id", "end");
    await page.locator("[data-page-id] h1").focus();
    await page.keyboard.press("ArrowLeft");
    await expect(page.locator("[data-page-id]")).not.toHaveAttribute("data-page-id", "share");
    await goTo(page, "end");

    const methodology = page.getByRole("button", { name: "How this was measured" });
    await methodology.click();
    await expect(page.getByRole("dialog")).toContainText("365-day summary history");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();

    await page.getByRole("button", { name: "Read again" }).click();
    await expect(page.locator("[data-page-id]")).toHaveAttribute("data-page-id", "arrival");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);

    await page.setViewportSize({ width: 1440, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);

    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/report/v61-historical-production-fixture");
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.locator("[data-page-id='scope-receipt']")).toContainText("Death Exposure");
    expect(pageErrors.map((error) => error.message), consoleErrors.join("\n")).toEqual([]);
  });

  test("optional persisted v6.1 fields never white-screen", async ({ page }) => {
    // Fifteen full page loads in one test; it outruns the default budget on a
    // loaded machine.  Pre-existing, and load-sensitive rather than flaky.
    test.slow();
    await page.emulateMedia({ reducedMotion: "reduce" });
    const pageErrors: string[] = [];
    const consoleErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    const cases: Array<[string, string[]]> = [
      ["v61-5-fixture", []],
      ["v61-no-heroes-fixture", ["lead-hero", "hero-front-row", "pool-layers"]],
      ["v61-one-hero-fixture", ["hero-front-row", "pool-layers"]],
      ["v61-no-bands-fixture", ["pool-layers"]],
      ["v61-one-band-fixture", ["pool-layers"]],
      ["v61-qualified-fixture", []],
      ["v61-no-chronology-fixture", ["pool-movement"]],
      ["v61-one-point-fixture", ["pool-movement"]],
      ["v61-no-identity-fixture", ["coherence", "signature-setup", "signature-reveal"]],
      ["v61-neutral-fixture", ["signature-setup", "signature-reveal"]],
      ["v61-low-confidence-identity-fixture", ["signature-setup", "signature-reveal"]],
      ["v61-missing-comparison-fixture", []],
      ["v61-empty-comparison-fixture", []],
      ["v61-missing-evidence-fields-fixture", []],
      ["v61-missing-supporting-evidence-fixture", []],
    ];

    for (const [fixture, omitted] of cases) {
      pageErrors.length = 0;
      consoleErrors.length = 0;
      await page.goto(`/report/${fixture}`);
      await expect(page.locator("main")).toBeVisible();
      const ids = await pageIds(page);
      expect(ids).toContain("share");
      expect(ids).toContain("end");
      for (const id of omitted) expect(ids).not.toContain(id);
      expect(page.getByRole("heading", { name: /This report couldn’t load\./ })).toHaveCount(0);
      expect(pageErrors, consoleErrors.join("\n")).toEqual([]);
    }

    await page.goto("/report/v61-missing-supporting-evidence-fixture");
    await goTo(page, "pool-layers");
    const evidence = page.getByRole("button", { name: "Why this?" });
    expect(await evidence.count()).toBe(0);
  });

  test("Evidence, Methodology, and Exit dialogs close and restore focus", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/report/v61-2-fixture");
    await goTo(page, "pool-width");
    const evidence = page.getByRole("button", { name: "Why this?" });
    await evidence.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    const before = await currentPageId(page);
    await page.keyboard.press("ArrowRight");
    expect(await currentPageId(page)).toBe(before);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(evidence).toBeFocused();

    await goTo(page, "end");
    const methodology = page.getByRole("button", { name: "How this was measured" });
    await methodology.click();
    await expect(page.getByRole("dialog")).toContainText("365-day summary history");
    await page.keyboard.press("Escape");
    await expect(methodology).toBeFocused();

    const exit = page.getByRole("button", { name: "Exit", exact: true }).last();
    await exit.click();
    await expect(page.getByRole("dialog")).toContainText("Your place in this report won’t be saved.");
    await page.getByRole("button", { name: "Stay" }).click();
    await expect(exit).toBeFocused();
  });

  test("copies only origin and pathname and exposes a selected fallback", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async (value: string) => { (window as typeof window & { copied?: string }).copied = value; } } });
    });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/report/v61-2-fixture?secret=query#fragment");
    await goTo(page, "share");
    await page.getByRole("button", { name: "Copy report link" }).click();
    await expect(page.getByRole("status")).toHaveText("Report link copied.");
    expect(await page.evaluate(() => (window as typeof window & { copied?: string }).copied)).toBe("http://127.0.0.1:3000/report/v61-2-fixture");

    await page.evaluate(() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async () => { throw new Error("blocked"); } } }));
    await page.getByRole("button", { name: "Copy report link" }).click();
    const fallback = page.getByLabel("Report URL");
    await expect(fallback).toHaveValue("http://127.0.0.1:3000/report/v61-2-fixture");
    expect(await fallback.evaluate((input) => (input as HTMLInputElement).selectionEnd)).toBe((await fallback.inputValue()).length);
  });

  test("is responsive and emits identity-safe story analytics", async ({ page }) => {
    await page.addInitScript(() => {
      (window as typeof window & { events?: unknown[] }).events = [];
      window.addEventListener("dota-report-analytics", (event) => (window as typeof window & { events?: unknown[] }).events?.push((event as CustomEvent).detail));
    });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/report/v61-3-fixture#access_token=private");
    await page.getByRole("button", { name: "Next", exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    const encoded = JSON.stringify(await page.evaluate(() => (window as typeof window & { events?: unknown[] }).events ?? [])).toLowerCase();
    expect(encoded).toContain("report.story_page_viewed.v1");
    for (const forbidden of ["report_id", "account_id", "display_name", "access_token", "hero_id", "match_id", "cohort:v61:"]) expect(encoded).not.toContain(forbidden);
  });

  test("never renders removed UI or private analytical fields", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/report/v61-5-fixture");
    const text = (await page.locator("main").innerText()).toLowerCase();
    for (const forbidden of ["hero mirror", "p-value", "q-value", "protected:", "cohort:v61:"]) expect(text).not.toContain(forbidden);
    await expect(page.locator("img, svg, canvas")).toHaveCount(0);
  });
});
