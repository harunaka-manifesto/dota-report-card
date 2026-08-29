import { expect, test, type ConsoleMessage, type Page } from "@playwright/test";

const FULL = "/report/v61-story-full-fixture";
const NONE = "/report/v61-story-finding-none-fixture";
const POST_LOSS = "/report/v61-story-finding-post-loss-fixture";
const TRANSFER = "/report/v61-story-finding-transfer-fixture";
const DEGRADED = "/report/v61-story-degraded-fixture";
const LONG_STREAK = "/report/v61-story-long-streak-fixture";
const HISTORICAL = "/report/v61-historical-production-fixture";

const FORBIDDEN_STORY_TEXT = [
  /death[-_ ]context/i,
  /page[-_ ]?25/i,
  /session drift/i,
  /coming soon/i,
  /not enough data/i,
  /\bMMR\b/i,
  /\bmedal\b/i,
];

/** Reduced motion composes every page instantly, which makes traversal exact. */
async function openStory(page: Page, path: string) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(path);
  await expect(page.locator("article[data-page]")).toBeVisible();
}

/** The legacy compatibility path renders no page manifest. */
async function openLegacy(page: Page, path: string) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(path);
  await expect(page.locator("main")).toBeVisible();
}

function watchForErrors(page: Page): { errors: string[] } {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message: ConsoleMessage) => {
    if (message.type() !== "error") return;
    // Next's dev overlay repeats hydration failures as console errors too.
    errors.push(`console: ${message.text()}`);
  });
  return { errors };
}

async function currentPage(page: Page): Promise<number> {
  return Number(await page.locator("article[data-page]").getAttribute("data-page"));
}

/**
 * Clicks once and waits for the composed page to change AND for focus to land
 * on the destination heading, which is the contracted navigation behaviour.
 */
async function step(page: Page, direction: "Next" | "Back"): Promise<number> {
  const article = page.locator("article[data-page]");
  const from = await article.getAttribute("data-page");
  await page.getByRole("button", { name: direction, exact: true }).click();
  await expect(article).not.toHaveAttribute("data-page", from!);
  await expect(article.locator("h1")).toBeFocused();
  return currentPage(page);
}

async function traverseForward(page: Page): Promise<number[]> {
  const next = page.getByRole("button", { name: "Next", exact: true });
  const seen: number[] = [await currentPage(page)];
  for (let index = 0; index < 40; index += 1) {
    if (await next.isDisabled()) break;
    seen.push(await step(page, "Next"));
  }
  return seen;
}

async function advanceTo(page: Page, target: number): Promise<void> {
  for (let index = 0; index < 40 && (await currentPage(page)) < target; index += 1) {
    await step(page, "Next");
  }
  expect(await currentPage(page)).toBe(target);
}

test.describe("story composition in the browser", () => {
  test("the full report runs first to last and back again", async ({ page }) => {
    const watcher = watchForErrors(page);
    await openStory(page, FULL);

    const forward = await traverseForward(page);
    expect(forward).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 29, 30, 31, 32, 33]);
    expect(forward).not.toContain(25);
    expect(forward).not.toContain(28);
    expect(forward).not.toContain(34);

    const back = page.getByRole("button", { name: "Back", exact: true });
    const backward: number[] = [];
    for (let index = 0; index < 40; index += 1) {
      if (await back.isDisabled()) break;
      backward.push(await step(page, "Back"));
    }
    expect(backward).toEqual([...forward].reverse().slice(1));
    expect(watcher.errors).toEqual([]);
  });

  test("each finding combination composes its own sequence", async ({ page }) => {
    await openStory(page, POST_LOSS);
    let pages = await traverseForward(page);
    expect(pages).toContain(14);
    expect(pages).toContain(15);
    expect(pages).not.toContain(20);

    await openStory(page, TRANSFER);
    pages = await traverseForward(page);
    expect(pages).toContain(20);
    expect(pages).toContain(21);
    expect(pages).not.toContain(14);

    await openStory(page, NONE);
    pages = await traverseForward(page);
    expect(pages).not.toContain(14);
    expect(pages).not.toContain(20);
    expect(pages).toContain(16);
    expect(pages[pages.length - 1]).toBe(33);
  });

  test("a long losing streak shows all three microcopy lines", async ({ page }) => {
    await openStory(page, LONG_STREAK);
    await advanceTo(page, 12);
    const text = await page.locator("article[data-page]").innerText();
    expect(text).toContain("You lost 4 matches in a row.");
    expect(text).toContain("One more.");
    expect(text).toContain("And another.");
    // Frozen minimum streak of three.
    expect(text).toContain("And… yeah.");
  });

  test("a two-match streak stops before the frozen minimum", async ({ page }) => {
    await openStory(page, FULL);
    await advanceTo(page, 12);
    const text = await page.locator("article[data-page]").innerText();
    expect(text).toContain("You lost 2 matches in a row.");
    expect(text).toContain("One more.");
    expect(text).not.toContain("And another.");
    expect(text).not.toContain("And… yeah.");
  });

  test("rank points read flat at exactly zero", async ({ page }) => {
    await openStory(page, LONG_STREAK);
    await advanceTo(page, 4);
    const text = await page.locator("article[data-page]").innerText();
    expect(text).toContain("You ended the year exactly where you started.");
    expect(text).not.toContain("-");
  });

  test("the degraded run still ends on the final card", async ({ page }) => {
    await openStory(page, DEGRADED);
    const pages = await traverseForward(page);
    expect(pages).not.toContain(12);
    expect(pages).not.toContain(17);
    expect(pages).not.toContain(31);
    expect(pages[pages.length - 1]).toBe(33);
  });

  test("a historical report without a story payload still renders", async ({ page }) => {
    const watcher = watchForErrors(page);
    await openLegacy(page, HISTORICAL);
    await expect(page.locator("h1").first()).toBeVisible();
    // No story payload, so the new composer never runs for it.
    await expect(page.locator("article[data-page]")).toHaveCount(0);
    expect(watcher.errors).toEqual([]);
  });

  test("no removed surface reaches the reader", async ({ page }) => {
    await openStory(page, FULL);
    const next = page.getByRole("button", { name: "Next", exact: true });
    for (let index = 0; index < 40; index += 1) {
      const text = (await page.locator("main").innerText()).replace(/\s+/g, " ");
      expect(text.trim().length, `page ${await currentPage(page)} rendered blank`).toBeGreaterThan(0);
      for (const pattern of FORBIDDEN_STORY_TEXT) {
        expect(text, `page ${await currentPage(page)} leaked ${pattern}`).not.toMatch(pattern);
      }
      if (await next.isDisabled()) break;
      await step(page, "Next");
    }
    expect(await page.locator("main img, main canvas, main svg, main picture, main video").count()).toBe(0);
  });
});

test.describe("navigation", () => {
  test("keyboard, edge taps, and bounds behave", async ({ page }) => {
    await openStory(page, FULL);
    const article = page.locator("article[data-page]");
    // Tap the middle of the stage so the click lands outside both edge zones
    // and outside any control.
    await article.click({ position: { x: ((await article.boundingBox())!.width) / 2, y: 200 } });
    await page.keyboard.press("ArrowRight");
    await expect(article).toHaveAttribute("data-page", "2");
    await page.keyboard.press("PageDown");
    await expect(article).toHaveAttribute("data-page", "3");
    await page.keyboard.press("ArrowLeft");
    await expect(article).toHaveAttribute("data-page", "2");

    // Edge tap zones: 56px from either edge of the stage, which spans the
    // full frame width rather than the inset story column.
    const stage = page.locator("article[data-page]").locator("xpath=..");
    const box = (await stage.boundingBox())!;
    await stage.click({ position: { x: 20, y: box.height / 2 } });
    await expect(article).toHaveAttribute("data-page", "1");
    await expect(page.getByRole("button", { name: "Back", exact: true })).toBeDisabled();
  });

  test("mid-reveal: the first forward action completes the page, the second advances", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto(FULL);
    await expect(page.locator("article[data-page]")).toBeVisible();
    const next = page.getByRole("button", { name: "Next" });
    // Page 1's dry line is still hidden while the page is revealing.
    await expect(page.locator('[data-revealed="false"]').first()).toBeVisible();
    await next.click();
    expect(await currentPage(page)).toBe(1);
    await expect(page.locator('[data-revealed="false"]')).toHaveCount(0);
    await next.click();
    expect(await currentPage(page)).toBe(2);
  });

  test("progress reports the composed total", async ({ page }) => {
    await openStory(page, FULL);
    const progress = page.getByRole("progressbar");
    await expect(progress).toHaveAttribute("aria-valuetext", "Page 1 of 31");
    await expect(progress).toHaveAttribute("aria-valuemax", "31");
  });
});

test.describe("hero eras", () => {
  async function gotoHeroEras(page: Page) {
    await openStory(page, FULL);
    await advanceTo(page, 18);
  }

  test("opens on the most recent non-empty period and clears an empty one", async ({ page }) => {
    await gotoHeroEras(page);
    const range = page.getByLabel("Hero era period");
    await expect(range).toHaveValue("11");
    await expect(page.locator("article li").filter({ hasText: "Hero" }).first()).toBeVisible();

    // April is the empty period in the fixture.
    await range.fill("3");
    await expect(page.getByText("No recorded matches in this period.", { exact: true })).toBeVisible();
    // Every previous row is cleared: nothing carries forward into an empty period.
    await expect(page.getByText("Hero Zeta", { exact: true })).toHaveCount(0);
  });

  test("keyboard moves periods without changing story pages", async ({ page }) => {
    await gotoHeroEras(page);
    const range = page.getByLabel("Hero era period");
    await range.focus();
    await page.keyboard.press("ArrowLeft");
    await expect(range).toHaveValue("10");
    await page.keyboard.press("Home");
    await expect(range).toHaveValue("0");
    await page.keyboard.press("End");
    await expect(range).toHaveValue("11");
    expect(await currentPage(page)).toBe(18);
  });
});

test.describe("the archetype card", () => {
  async function gotoArchetype(page: Page) {
    await openStory(page, FULL);
    await advanceTo(page, 30);
  }

  test("reduced motion shows the card face-up with no trigger", async ({ page }) => {
    await gotoArchetype(page);
    await expect(page.getByRole("heading", { level: 1, name: "THE RECURRING PLAYER" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Reveal your archetype/i })).toHaveCount(0);
  });

  test("the turn happens on a real button and back returns face-up", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto(FULL);
    const next = page.getByRole("button", { name: "Next", exact: true });
    // Two actions per page: the first completes it, the second advances.
    while ((await currentPage(page)) < 30) {
      await next.click();
      if ((await currentPage(page)) === 30) break;
      await next.click();
      await page.waitForTimeout(50);
    }
    const trigger = page.getByRole("button", { name: /Reveal your archetype/i });
    await expect(trigger).toBeVisible();
    await trigger.click();
    await expect(page.getByRole("button", { name: /Reveal your archetype/i })).toHaveCount(0);
    await page.getByRole("button", { name: "Back", exact: true }).click();
    await page.getByRole("button", { name: "Next" }).click();
    expect(await currentPage(page)).toBe(30);
    await expect(page.getByRole("button", { name: /Reveal your archetype/i })).toHaveCount(0);
  });

  test("the turn is the only reveal interaction in the whole story", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto(FULL);
    const article = page.locator("article[data-page]");
    const next = page.getByRole("button", { name: "Next", exact: true });
    const trigger = page.getByRole("button", { name: /Reveal your archetype/i });
    for (let index = 0; index < 60; index += 1) {
      const current = Number(await article.getAttribute("data-page"));
      // Only Page 30 may offer the turn.
      expect(await trigger.count(), `page ${current} offered a reveal control`).toBe(current === 30 ? 1 : 0);
      if (current === 30) await trigger.click();
      if (await next.isDisabled()) break;
      await next.click();
      await page.waitForTimeout(30);
    }
  });

  test("page 31 shows only anchors backed by rendered pages", async ({ page }) => {
    await openStory(page, FULL);
    await advanceTo(page, 31);
    await expect(page.getByRole("heading", { name: "Your hero pool." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "After losses." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Outside your usual heroes." })).toBeVisible();
    // The scripted closing line is suppressed while the archetype is a constant.
    await expect(page.getByText("Not a personality test")).toHaveCount(0);
  });
});

test.describe("collage, share, and the ending", () => {
  async function gotoEnd(page: Page) {
    await openStory(page, FULL);
    const next = page.getByRole("button", { name: "Next", exact: true });
    while (!(await next.isDisabled())) await step(page, "Next");
  }

  test("combat rows all belong to the leading hero named above them", async ({ page }) => {
    await openStory(page, FULL);
    await advanceTo(page, 22);
    await expect(page.getByText("Hero Zeta contributed more than any other hero: 93.")).toBeVisible();
    await expect(page.getByText("The three games where Hero Zeta really got involved:")).toBeVisible();
    const names = await page.locator("article ol li span:nth-child(2)").allInnerTexts();
    expect(names.length).toBe(3);
    for (const name of names) expect(name).toBe("Hero Zeta");
  });

  test("the collage completes its rows and closes the chapter", async ({ page }) => {
    await openStory(page, FULL);
    await advanceTo(page, 32);
    const cards = page.locator("article ul li");
    expect(await cards.count()).toBeGreaterThan(0);
    await expect(page.getByRole("heading", { name: "Well. That was your year." })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });

  test("share falls back to copy, then to selectable text", async ({ page, context, browserName }) => {
    // Only Chromium exposes the clipboard permission needed to read back.
    test.skip(browserName !== "chromium", "clipboard permissions are Chromium-only");
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await gotoEnd(page);
    expect(await currentPage(page)).toBe(33);
    await page.evaluate(() => {
      // No Web Share in this environment: exercise the copy path.  `share`
      // lives on Navigator.prototype in some engines, so shadow it rather
      // than deleting it.
      Object.defineProperty(navigator, "share", { configurable: true, value: undefined });
    });
    await page.getByRole("button", { name: "Share your Dota DNA." }).click();
    await expect(page.getByText("Report link copied.")).toBeVisible();
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    expect(copied).toBe(`${new URL(page.url()).origin}/report/v61-story-full-fixture`);
    expect(copied).not.toContain("?");
    expect(copied).not.toContain("#");
  });

  test("a cancelled native share returns silently", async ({ page }) => {
    await gotoEnd(page);
    await page.evaluate(() => {
      (navigator as unknown as { share: () => Promise<void> }).share = () =>
        Promise.reject(new DOMException("cancelled", "AbortError"));
    });
    await page.getByRole("button", { name: "Share your Dota DNA." }).click();
    await expect(page.getByText("Report link copied.")).toHaveCount(0);
    await expect(page.getByText("The link is below.")).toHaveCount(0);
  });

  test("clipboard failure exposes the URL as selectable text", async ({ page }) => {
    await gotoEnd(page);
    await page.evaluate(() => {
      Object.defineProperty(navigator, "share", { configurable: true, value: undefined });
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: { writeText: () => Promise.reject(new Error("denied")) },
      });
    });
    await page.getByRole("button", { name: "Share your Dota DNA." }).click();
    await expect(page.getByText("The link is below.")).toBeVisible();
    await expect(page.getByLabel("Report link")).toBeVisible();
  });

  test("run it back returns to page one", async ({ page }) => {
    await gotoEnd(page);
    await page.getByRole("button", { name: "Run it back." }).click();
    expect(await currentPage(page)).toBe(1);
    await expect(page.getByRole("button", { name: "Back", exact: true })).toBeDisabled();
  });

  test("there is no Deep CTA and no Save control", async ({ page }) => {
    await gotoEnd(page);
    await expect(page.getByRole("link", { name: "Go deeper." })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /save/i })).toHaveCount(0);
  });
});

test.describe("evidence, methodology, and focus", () => {
  test("inline evidence opens in place and returns focus", async ({ page }) => {
    await openStory(page, FULL);
    await advanceTo(page, 15);
    const toggle = page.getByRole("button", { name: "Why this?" });
    await expect(page.getByRole("region", { name: /Observed post loss/ })).toBeHidden();
    await toggle.click();
    await expect(page.getByRole("region", { name: /Observed post loss/ })).toBeVisible();
    const opened = page.getByRole("button", { name: "Hide evidence" });
    await expect(opened).toHaveAttribute("aria-expanded", "true");
    await opened.click();
    await expect(page.getByRole("region", { name: /Observed post loss/ })).toBeHidden();
  });

  test("methodology is a native dialog with focus restoration", async ({ page }) => {
    await openStory(page, FULL);
    const opener = page.getByRole("button", { name: "How this was measured" });
    await opener.click();
    const dialog = page.locator("dialog[open]");
    await expect(dialog).toBeVisible();
    // Mode scope stays backstage: one combined total, and no per-mode split.
    await expect(dialog.getByText("both ranked and unranked matches", { exact: false })).toBeVisible();
    await expect(dialog.getByText("ranked matches only", { exact: false })).toBeVisible();
    const body = await dialog.innerText();
    expect(body).not.toMatch(/Captain’s Mode|All Pick/);
    expect(body).not.toMatch(/\bMMR\b|\bmedal\b|\bbracket\b|\btier\b/i);
    await page.keyboard.press("Escape");
    await expect(page.locator("dialog[open]")).toHaveCount(0);
    await expect(opener).toBeFocused();
  });

  test("every page keeps exactly one h1 and moves focus to it", async ({ page }) => {
    await openStory(page, FULL);
    const next = page.getByRole("button", { name: "Next", exact: true });
    for (let index = 0; index < 40; index += 1) {
      await expect(page.locator("article h1")).toHaveCount(1);
      if (await next.isDisabled()) break;
      await step(page, "Next");
    }
  });
});

test.describe("responsive and privacy", () => {
  for (const viewport of [
    { width: 320, height: 640 },
    { width: 375, height: 812 },
    { width: 768, height: 500 },
    { width: 1440, height: 900 },
  ]) {
    test(`no horizontal overflow at ${viewport.width}x${viewport.height}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await openStory(page, FULL);
      const next = page.getByRole("button", { name: "Next", exact: true });
      for (let index = 0; index < 40; index += 1) {
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow, `overflow on page ${await currentPage(page)}`).toBeLessThanOrEqual(1);
        if (await next.isDisabled()) break;
        await step(page, "Next");
      }
    });
  }

  test("analytics never carry an identifier", async ({ page }) => {
    await openStory(page, FULL);
    await page.evaluate(() => {
      (window as unknown as { __events: unknown[] }).__events = [];
      window.addEventListener("dota-report-analytics", (event) => {
        (window as unknown as { __events: unknown[] }).__events.push((event as CustomEvent).detail);
      });
    });
    for (let index = 0; index < 8; index += 1) await step(page, "Next");
    const serialized = JSON.stringify(await page.evaluate(() => (window as unknown as { __events: unknown[] }).__events));
    for (const pattern of [/account_id/i, /steam/i, /match_id/i, /report_id/i, /token/i, /cohort/i, /\?/, /#/]) {
      expect(serialized).not.toMatch(pattern);
    }
  });
});
