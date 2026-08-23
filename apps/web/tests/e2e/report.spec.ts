import { test, expect } from "@playwright/test";

const chapters = ["summary", "elements", "patterns", "heroes", "you"];
const analyticalScaffolding = /confidence|coverage|provenance|sample size|evidence count|cohort|methodology|denominator|source match|played enough|\btrust\b/i;

test("Free DNA opens as five identity chapters", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await expect(page.locator(".report-chapter")).toHaveCount(5);
  for (const chapter of chapters) await expect(page.locator(`#${chapter}`)).toBeVisible();
  await expect(page.locator(".chapter-dock button")).toHaveCount(5);
  await expect(page.locator(".story-progress")).toHaveCount(0);
  await expect(page.locator(".story-page-number")).toHaveCount(0);
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollSnapType)).toBe("none");
  await expect(page.locator(".report-story")).toHaveAttribute("data-glyph-registry-size", "29");
  await expect(page.locator(".report-story")).toHaveAttribute("data-glyph-registry-unique", "true");
  const geometries = (await page.locator(".report-story").getAttribute("data-glyph-registry-geometries"))?.split(",") ?? [];
  expect(geometries).toHaveLength(29);
  expect(new Set(geometries).size).toBe(29);
});

test("Summary leads with the identity and Elements/Patterns expose readable glyph tiles", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await expect(page.locator("#summary h1")).toBeVisible();
  await page.locator("#elements").scrollIntoViewIfNeeded();
  await expect(page.locator("#elements .element-grid .glyph-tile")).toHaveCount(18);
  await expect(page.locator("#elements .glyph-tile").first().locator("svg")).toBeVisible();
  await expect(page.locator("#elements .glyph-tile").first().locator("svg")).toHaveAttribute("aria-hidden", "true");
  await page.locator("#patterns").scrollIntoViewIfNeeded();
  await expect(page.locator("#patterns .pattern-grid .glyph-tile")).toHaveCount(5);
  await page.locator("#patterns .pattern-grid .glyph-tile").first().click();
  await expect(page.locator("#patterns .pattern-detail")).toBeVisible();
  await expect(page.locator("#patterns .pattern-grid .glyph-tile").first()).toContainText("Your hero names change. The job keeps coming back.");
});

test("Free DNA hides analytical scaffolding from the reader", async ({ page }) => {
  await page.goto("/report/fixture-report");
  const visibleText = await page.locator(".report-story").innerText();
  expect(visibleText).not.toMatch(analyticalScaffolding);
  await expect(page.locator(".methodology-button, .pattern-story-evidence, .story-progress")).toHaveCount(0);
});

test("Hero Portfolio keeps its self-assessment interactions together", async ({ page }) => {
  await page.goto("/report/fixture-report");
  const common = page.locator("#hero-common-thread");
  await common.scrollIntoViewIfNeeded();
  const commonReveal = common.getByRole("button", { name: "Reveal the read" });
  await expect(commonReveal).toBeDisabled();
  await common.getByRole("radio", { name: "Mobility" }).click();
  await expect(commonReveal).toBeEnabled();
  await commonReveal.click();
  await expect(common.getByText("Mobility is the strongest recurring way of helping across the established pool.")).toBeVisible();

  const evolution = page.locator("#pool-evolution-question");
  await evolution.getByRole("radio", { name: "My heroes changed, but my style didn’t" }).click();
  await evolution.getByRole("button", { name: "Reveal the read" }).click();
  await expect(evolution.getByText("New heroes. Same taste.", { exact: true })).toBeVisible();
});

test("Hero Mirror stays in You and share follows it", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await expect(page.locator("#hero-mirror .mirror-cover")).toBeVisible();
  await expect(page.locator("#hero-mirror .mirror-result")).toHaveCount(0);
  await page.locator("#hero-mirror").getByRole("button", { name: "Reveal Hero Mirror" }).click();
  await expect(page.locator("#hero-mirror .mirror-result")).toBeVisible();
  await expect(page.locator("#hero-mirror .mirror-result h3")).toHaveText("Anti-Mage is where your usual Dota shows up most clearly.");
  await expect(page.locator("#hero-mirror .mirror-result")).not.toContainText(/played enough|\btrust\b/i);
  await expect(page.locator("#final-card")).toBeVisible();
  await expect(page.locator("#hero-mirror").locator("xpath=following-sibling::*[1]")).toHaveAttribute("id", "final-card");
  await expect(page.getByLabel("Share your Dota DNA")).toBeVisible();
  await expect(page.locator(".share-preview img")).toHaveAttribute("src", /\/share\/final\?/);
});

test("unavailable portfolio findings become short human states", async ({ page }) => {
  await page.goto("/report/no-clear-report");
  const exception = page.locator("#hero-exception");
  await expect(exception.getByText("Your pool has no odd one out.", { exact: true })).toBeVisible();
  await expect(exception.getByText("USEFUL ANSWER", { exact: true })).toBeVisible();
  await expect(exception.getByRole("radio")).toHaveCount(0);
  await expect(exception.getByRole("button", { name: /Reveal/ })).toHaveCount(0);
});

test("report supports reduced motion, narrow layouts, keyboard, and identity-safe chapter events", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    (window as typeof window & { __dotaEvents?: unknown[] }).__dotaEvents = [];
    window.addEventListener("dota-report-analytics", (event) => {
      const target = window as typeof window & { __dotaEvents?: unknown[] };
      target.__dotaEvents?.push((event as CustomEvent).detail);
    });
  });
  await page.goto("/report/fixture-report");
  await expect(page.locator(".chapter-dock")).toBeVisible();
  await page.locator("#hero-mirror").getByRole("button", { name: "Reveal Hero Mirror" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#hero-mirror .mirror-result")).toBeVisible();
  await page.locator(".chapter-dock button", { hasText: "Patterns" }).click();
  const events = await page.evaluate(() => (window as typeof window & { __dotaEvents?: Array<Record<string, unknown>> }).__dotaEvents ?? []);
  expect(events.some((event) => event.event === "report.chapter_navigation.v1" && event.chapter === "patterns")).toBeTruthy();
  expect(events.every((event) => !("report_id" in event) && !("account_id" in event) && !("name" in event))).toBeTruthy();
});
