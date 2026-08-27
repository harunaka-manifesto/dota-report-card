import { expect, test, type Page } from "@playwright/test";

async function currentPageId(page: Page): Promise<string> {
  return (await page.locator("[data-page-id]").getAttribute("data-page-id")) ?? "";
}

async function useStoryControl(page: Page, name: "Back" | "Next"): Promise<void> {
  await page.getByRole("button", { name, exact: true }).evaluate((button: HTMLButtonElement) => button.click());
}

async function goTo(page: Page, target: string): Promise<void> {
  for (let index = 0; index < 20; index += 1) {
    const current = await currentPageId(page);
    if (current === target) return;
    await useStoryControl(page, "Next");
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
      await useStoryControl(page, "Next");
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
    await useStoryControl(page, "Next");
    await expect(page.locator("[data-page-id='scope-receipt']")).toContainText("365 days");
    await expect(page.locator("[data-page-id='scope-receipt']")).toContainText("Death Exposure");
    const staticReceipt = page.getByRole("group");
    await staticReceipt.focus();
    await page.keyboard.down("Space");
    await expect(staticReceipt).toHaveAttribute("data-paused", "true");
    await page.keyboard.up("Space");
    await expect(staticReceipt).toHaveAttribute("data-paused", "false");
    await page.locator("[data-page-id] h1").focus();
    await page.keyboard.press("ArrowRight");
    await expect.poll(() => currentPageId(page)).toBe("lead-hero");
    await expect(page.getByLabel("24 matches")).toHaveAttribute("data-odometer-value", "24");
    await expect(page.getByLabel("33% of the year")).toHaveAttribute("data-odometer-value", "33");
    await page.locator("[data-page-id] h1").focus();
    await page.keyboard.press("ArrowLeft");
    await expect.poll(() => currentPageId(page)).toBe("scope-receipt");
    await goTo(page, "end");
    await page.getByRole("button", { name: "Read again" }).click();
    await expect.poll(() => currentPageId(page)).toBe("arrival");
    await expect(page.getByRole("heading", { name: /a year of Dota left receipts/ })).toBeFocused();
  });

  test("receipt follows the paced sequence, settles once, and restarts on return", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "Timing boundaries are covered once in Chromium.");
    test.setTimeout(30_000);
    await page.addInitScript(() => {
      (window as typeof window & { events?: Array<{ event?: string }> }).events = [];
      window.addEventListener("dota-report-analytics", (event) => (window as typeof window & { events?: Array<{ event?: string }> }).events?.push((event as CustomEvent).detail));
    });
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto("/report/v61-2-fixture");
    await useStoryControl(page, "Next");
    const receipt = page.locator("[data-receipt-stage]");
    await expect(receipt).toHaveAttribute("data-receipt-stage", "0");
    await expect(receipt.getByLabel("365 days")).toHaveAttribute("data-odometer-value", "365");
    await page.waitForTimeout(1_650);
    await expect(receipt).toHaveAttribute("data-receipt-stage", "0");
    await expect(receipt).toHaveAttribute("data-receipt-stage", "1", { timeout: 1_000 });
    await expect(receipt).toHaveAttribute("data-receipt-stage", "2", { timeout: 2_200 });
    await expect(receipt).toContainText("Death Exposure");
    await expect(receipt).toHaveAttribute("data-receipt-stage", "3", { timeout: 3_200 });
    await expect(receipt.getByLabel(/most-played heroes/)).toHaveAttribute("data-odometer-value", "5");
    await page.waitForTimeout(2_100);
    await expect(receipt).toHaveAttribute("data-receipt-stage", "3");
    const completed = await page.evaluate(() => ((window as typeof window & { events?: Array<{ event?: string }> }).events ?? []).filter((item) => item.event === "report.scope_sequence_completed.v1").length);
    expect(completed).toBe(1);

    await page.mouse.click(8, 400);
    await expect.poll(() => currentPageId(page)).toBe("arrival");
    await page.mouse.click(1272, 400);
    await expect.poll(() => currentPageId(page)).toBe("scope-receipt");
    await expect(page.locator("[data-receipt-stage]")).toHaveAttribute("data-receipt-stage", "0");

    await page.goto("/report/v61-no-heroes-fixture");
    await useStoryControl(page, "Next");
    const signalEnding = page.locator("[data-receipt-stage]");
    await expect(signalEnding).toHaveAttribute("data-receipt-stage", "2", { timeout: 6_000 });
    await page.waitForTimeout(3_000);
    await expect(signalEnding).toHaveAttribute("data-receipt-stage", "2");
  });

  test("holding the receipt pauses pointer and keyboard timelines exactly where they are", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "Hold timing is covered once in Chromium.");
    test.setTimeout(20_000);
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto("/report/v61-2-fixture");
    await useStoryControl(page, "Next");
    const receipt = page.locator("[data-receipt-stage]");
    const box = await receipt.boundingBox();
    if (!box) throw new Error("Receipt did not render");
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await expect(receipt).toHaveAttribute("data-paused", "true");
    await page.waitForTimeout(2_500);
    await expect(receipt).toHaveAttribute("data-receipt-stage", "0");
    await page.mouse.up();
    await expect(receipt).toHaveAttribute("data-paused", "false");
    await expect(receipt).toHaveAttribute("data-receipt-stage", "1", { timeout: 2_600 });

    await page.mouse.click(8, 400);
    await expect.poll(() => currentPageId(page)).toBe("arrival");
    await page.mouse.click(1272, 400);
    await expect.poll(() => currentPageId(page)).toBe("scope-receipt");
    const restarted = page.locator("[data-receipt-stage]");
    await restarted.focus();
    await page.keyboard.down("Space");
    await page.waitForTimeout(2_500);
    await expect(restarted).toHaveAttribute("data-receipt-stage", "0");
    await page.keyboard.up("Space");
    await expect(restarted).toHaveAttribute("data-receipt-stage", "1", { timeout: 2_600 });
  });

  test("narrow edge taps navigate while drags, selections, and semantic controls remain safe", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/report/v61-2-fixture");
    const next = page.getByRole("button", { name: "Next", exact: true });
    await next.focus();
    await expect(next).toHaveCSS("opacity", "1");
    await page.keyboard.press("Enter");
    await expect.poll(() => currentPageId(page)).toBe("scope-receipt");

    await page.mouse.click(8, 400);
    await expect.poll(() => currentPageId(page)).toBe("arrival");
    await page.mouse.move(367, 400);
    await page.mouse.down();
    await page.mouse.move(340, 400);
    await page.mouse.up();
    expect(await currentPageId(page)).toBe("arrival");

    await page.locator("[data-page-id] h1").evaluate((heading) => {
      const range = document.createRange();
      range.selectNodeContents(heading);
      window.getSelection()?.removeAllRanges();
      window.getSelection()?.addRange(range);
    });
    await page.mouse.click(367, 400);
    expect(await currentPageId(page)).toBe("arrival");
    await page.evaluate(() => window.getSelection()?.removeAllRanges());
    await page.mouse.click(367, 400);
    await expect.poll(() => currentPageId(page)).toBe("scope-receipt");
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

    await useStoryControl(page, "Next");
    await expect(page.locator("[data-page-id='scope-receipt']")).toContainText("365 days");
    await page.waitForTimeout(4_500);
    expect(pageErrors.map((error) => error.message), consoleErrors.join("\n")).toEqual([]);
    await expect(page.getByRole("heading", { name: /This report couldn’t load\./ })).toHaveCount(0);
    await useStoryControl(page, "Back");
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
    await useStoryControl(page, "Back");
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
    await useStoryControl(page, "Next");
    await expect(page.locator("[data-page-id='scope-receipt']")).toContainText("Death Exposure");
    expect(pageErrors.map((error) => error.message), consoleErrors.join("\n")).toEqual([]);
  });

  test("optional persisted v6.1 fields never white-screen", async ({ page }) => {
    test.setTimeout(60_000);
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
    await expect(page.getByLabel("72 comparable matches")).toHaveAttribute("data-odometer-value", "72");
    await expect(page.getByLabel("18 sessions")).toHaveAttribute("data-odometer-value", "18");
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
    await useStoryControl(page, "Next");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    const encoded = JSON.stringify(await page.evaluate(() => (window as typeof window & { events?: unknown[] }).events ?? [])).toLowerCase();
    expect(encoded).toContain("report.story_page_viewed.v1");
    for (const forbidden of ["report_id", "account_id", "display_name", "access_token", "hero_id", "match_id", "cohort:v61:"]) expect(encoded).not.toContain(forbidden);
  });

  test("the scope receipt never renders text outside the viewport", async ({ page }) => {
    for (const [width, height] of [[375, 812], [768, 500], [320, 640]] as const) {
      await page.setViewportSize({ width, height });
      await page.goto("/report/v61-2-fixture");
      await useStoryControl(page, "Next");
      // Animated receipts reach the hero fact last; the reduced-motion receipt
      // renders every fact at once. Waiting on the text covers both.
      const receipt = page.locator("[data-page-id='scope-receipt']");
      await expect(receipt).toContainText("most-played heroes", { timeout: 12_000 });
      await expect(receipt).toContainText("give us somewhere familiar to start");
      // scrollWidth cannot see this: the viewport clips overflow, so a truncated
      // line reads as zero document overflow. Measure the text itself.
      const clipped = await page.evaluate(() => {
        const root = document.querySelector("[data-page-id]");
        if (!root) return ["no page"];
        const outside: string[] = [];
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
        let node = walker.currentNode as Element | null;
        while (node) {
          if (node.childElementCount === 0 && node.textContent?.trim()) {
            const box = node.getBoundingClientRect();
            if (box.width > 0 && (box.right > window.innerWidth + 1 || box.left < -1)) {
              outside.push(`${node.textContent.trim().slice(0, 32)} @ ${Math.round(box.left)}..${Math.round(box.right)}`);
            }
          }
          node = walker.nextNode() as Element | null;
        }
        return outside;
      });
      expect(clipped, `clipped at ${width}x${height}`).toEqual([]);
    }
  });

  test("presses faster than the transition still advance one page each", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "Press cadence is covered once in Chromium.");
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/report/v61-3-fixture");
    const progress = page.getByRole("progressbar");
    await expect(progress).toHaveAttribute("aria-valuenow", "1");
    for (let index = 0; index < 8; index += 1) {
      await page.mouse.click(1435, 450);
      await page.waitForTimeout(60);
    }
    await expect(progress).toHaveAttribute("aria-valuenow", "9", { timeout: 5_000 });
    for (let index = 0; index < 4; index += 1) {
      await page.mouse.click(8, 450);
      await page.waitForTimeout(60);
    }
    await expect(progress).toHaveAttribute("aria-valuenow", "5", { timeout: 5_000 });
  });

  test("animated numbers only ever display their settled value", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "Frame sampling is covered once in Chromium.");
    test.setTimeout(40_000);
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto("/report/v61-2-fixture");
    await useStoryControl(page, "Next");
    const wrong: string[] = [];
    const values = new Set<string>();
    const deadline = Date.now() + 11_000;
    while (Date.now() < deadline) {
      const sample = await page.evaluate(() => {
        const odometer = document.querySelector("[data-page-id] h1 [data-odometer-value]");
        if (!odometer) return null;
        const settled = odometer.getAttribute("data-odometer-value") ?? "";
        const painted = [...odometer.querySelectorAll("[class*=odometerColumn]")].map((column) => column.textContent).join("");
        return { settled, painted };
      });
      if (sample) {
        values.add(sample.settled);
        if (sample.painted !== sample.settled) wrong.push(`${sample.painted} shown while settled value is ${sample.settled}`);
      }
      await page.waitForTimeout(40);
    }
    expect(values.size).toBeGreaterThanOrEqual(4);
    expect(wrong).toEqual([]);
  });

  test("the Signature setup bridge never overlaps its headline", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const [width, height] of [[1440, 900], [375, 812], [1000, 700]] as const) {
      await page.setViewportSize({ width, height });
      await page.goto("/report/v61-3-fixture");
      await goTo(page, "signature-setup");
      const gap = await page.evaluate(() => {
        const composed = document.querySelector("[data-page-id='signature-setup']");
        const bridge = composed?.querySelector("[class*=bridge]");
        const headline = composed?.querySelector("h1");
        if (!bridge || !headline) return null;
        return Math.round(headline.getBoundingClientRect().top - bridge.getBoundingClientRect().bottom);
      });
      expect(gap, `bridge/headline gap at ${width}x${height}`).not.toBeNull();
      expect(gap!, `bridge/headline gap at ${width}x${height}`).toBeGreaterThanOrEqual(8);
    }
  });

  test("the headline focus ring follows the navigation source", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/report/v61-3-fixture");

    await page.mouse.click(1435, 450);
    await expect.poll(() => currentPageId(page)).toBe("scope-receipt");
    const afterPointer = await page.evaluate(() => ({
      source: document.querySelector("main")?.getAttribute("data-nav-source"),
      focused: document.activeElement?.tagName,
      outline: document.activeElement instanceof Element ? getComputedStyle(document.activeElement).outlineStyle : null,
    }));
    expect(afterPointer.source).toBe("pointer");
    expect(afterPointer.focused).toBe("H1");
    expect(afterPointer.outline).toBe("none");

    await page.locator("[data-page-id] h1").focus();
    await page.keyboard.press("ArrowRight");
    await expect.poll(() => currentPageId(page)).toBe("lead-hero");
    const afterKeyboard = await page.evaluate(() => ({
      source: document.querySelector("main")?.getAttribute("data-nav-source"),
      focused: document.activeElement?.tagName,
      outline: document.activeElement instanceof Element ? getComputedStyle(document.activeElement).outlineStyle : null,
    }));
    expect(afterKeyboard.source).toBe("keyboard");
    expect(afterKeyboard.focused).toBe("H1");
    expect(afterKeyboard.outline).not.toBe("none");
  });

  test("never renders removed UI or private analytical fields", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/report/v61-5-fixture");
    const text = (await page.locator("main").innerText()).toLowerCase();
    for (const forbidden of ["hero mirror", "p-value", "q-value", "protected:", "cohort:v61:"]) expect(text).not.toContain(forbidden);
    await expect(page.locator("img, svg, canvas")).toHaveCount(0);
  });
});
