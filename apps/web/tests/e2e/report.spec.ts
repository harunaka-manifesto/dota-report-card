import { test, expect } from "@playwright/test";

test("completed Free DNA report opens with the full Element and Portfolio story", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await expect(page.locator("[data-page-kind='element_scan']")).toBeVisible();
  await expect(page.getByRole("heading", { name: "The pieces of your Dota pattern" })).toBeVisible();
  await expect(page.locator(".element-tile")).toHaveCount(18);
  await expect(page.locator("[data-page-kind='pattern_highlight']")).toHaveCount(5);
  await page.locator("#hero-common-thread").scrollIntoViewIfNeeded();
  const common = page.locator("#hero-common-thread");
  await expect(common.getByText("What keeps showing up across your established heroes?")).toBeVisible();
  await expect(common.getByRole("button", { name: "Reveal" })).toBeDisabled();
  await common.getByRole("radio", { name: "Mobility" }).click();
  await expect(common.getByRole("radio", { name: "Mobility" })).toHaveAttribute("aria-checked", "true");
  await common.getByRole("button", { name: "Reveal" }).click();
  await expect(common.getByText("Mobility is the strongest recurring way of helping across the established pool.")).toBeVisible();

  const pattern = page.locator("#pattern-same_playbook");
  await pattern.scrollIntoViewIfNeeded();
  await expect(pattern.locator(".pattern-story-screen")).toBeVisible();
  await expect(pattern.getByRole("heading", { name: "What this actually means" })).toBeVisible();
  const methodology = pattern.locator(".pattern-story-evidence");
  await methodology.locator("summary").focus();
  await methodology.locator("summary").press("Enter");
  await expect(methodology).toHaveAttribute("open", "");
  await expect(methodology.getByText(/Confidence:/)).toBeVisible();
});

test("wrong Portfolio choices receive contextual correction", async ({ page }) => {
  await page.goto("/report/fixture-report");
  const common = page.locator("#hero-common-thread");
  await common.getByRole("radio", { name: "Durability" }).click();
  const commonReveal = common.getByRole("button", { name: "Reveal" });
  await expect(commonReveal).toBeEnabled();
  await commonReveal.click();
  await expect(common.getByText("Not quite.", { exact: true })).toBeVisible();
  await expect(common.getByText("Mobility has the stronger cross-hero coverage.")).toBeVisible();

  const exception = page.locator("#hero-exception");
  await exception.getByRole("radio", { name: "Axe" }).click();
  const exceptionReveal = exception.getByRole("button", { name: "Reveal" });
  await expect(exceptionReveal).toBeEnabled();
  await exceptionReveal.click();
  await expect(exception.getByText("Good guess — but not this one.", { exact: true })).toBeVisible();
  await expect(exception.getByText("Anti-Mage stands apart more clearly.")).toBeVisible();
});

test("Hero Mirror and final share controls are keyboard accessible", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await page.locator("#hero-mirror").scrollIntoViewIfNeeded();
  const mirror = page.locator("#hero-mirror");
  const reveal = mirror.getByRole("button", { name: "Reveal Hero Mirror" });
  await expect(reveal).toBeVisible();
  await reveal.focus();
  await reveal.press("Enter");
  await expect(mirror.getByText("Of the heroes you've played enough for us to trust, Anti-Mage is where your usual Dota shows up most clearly.")).toBeVisible();
  await page.locator("#final-card").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("Share your Dota DNA")).toBeVisible();
  await expect(page.locator(".share-preview img")).toHaveAttribute("src", /\/share\/final\?/);
  await expect(page.getByText("Include name")).toBeVisible();
});

test("Pool Evolution stays locked until the self-assessment is revealed", async ({ page }) => {
  await page.goto("/report/fixture-report");
  const question = page.locator("#pool-evolution-question");
  const reveal = question.getByRole("button", { name: "Reveal" });
  await expect(reveal).toBeDisabled();
  await page.locator("#pool-evolution-reveal").scrollIntoViewIfNeeded();
  await expect(page.getByText("Complete the self-assessment above to see the report read.")).toBeVisible();

  await question.scrollIntoViewIfNeeded();
  await question.getByRole("radio", { name: "My heroes changed, but my style didn’t" }).click();
  await reveal.click();
  await page.locator("#pool-evolution-reveal").scrollIntoViewIfNeeded();
  await expect(page.getByText("New heroes. Same taste.", { exact: true })).toBeVisible();
  await expect(page.getByText("new_heroes_same_toolkit")).toHaveCount(0);
});

test("Hero Mirror can be opened with a horizontal drag", async ({ page }) => {
  await page.goto("/report/fixture-report");
  const mirror = page.locator("#hero-mirror .mirror-card");
  await mirror.scrollIntoViewIfNeeded();
  const box = await mirror.boundingBox();
  expect(box).not.toBeNull();
  if (!box) return;
  await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.5);
  await page.mouse.up();
  await expect(mirror.getByText("Of the heroes you've played enough for us to trust, Anti-Mage is where your usual Dota shows up most clearly.")).toBeVisible();
});

test("Element scan honors reduced motion and report content survives a narrow viewport", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/report/fixture-report");
  await expect(page.locator(".element-scan")).toHaveAttribute("data-scan-state", "ready");
  await page.locator("#pattern-same_playbook").scrollIntoViewIfNeeded();
  await expect(page.getByText("Same Playbook · reveal", { exact: true })).toBeVisible();
  await page.locator("#final-card").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("Share your Dota DNA")).toBeVisible();
});

test("report analytics use canonical names once and omit identity fields", async ({ page }) => {
  await page.addInitScript(() => {
    (window as typeof window & { __dotaEvents?: unknown[] }).__dotaEvents = [];
    window.addEventListener("dota-report-analytics", (event) => {
      const target = window as typeof window & { __dotaEvents?: unknown[] };
      target.__dotaEvents?.push((event as CustomEvent).detail);
    });
  });
  await page.goto("/report/fixture-report");
  const common = page.locator("#hero-common-thread");
  await common.getByRole("radio", { name: "Mobility" }).click();
  const reveal = common.getByRole("button", { name: "Reveal" });
  await expect(reveal).toBeEnabled();
  await reveal.click();
  const events = await page.evaluate(() => (window as typeof window & { __dotaEvents?: Array<Record<string, unknown>> }).__dotaEvents ?? []);
  const names = events.map((event) => event.event);
  expect(names.filter((name) => name === "hero_portfolio.answer_selected.v1")).toHaveLength(1);
  expect(names.filter((name) => name === "hero_portfolio.reveal_viewed.v1")).toHaveLength(1);
  expect(events.every((event) => !("report_id" in event) && !("account_id" in event) && !("name" in event))).toBeTruthy();
});
