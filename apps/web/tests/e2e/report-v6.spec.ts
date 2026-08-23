import { test, expect } from "@playwright/test";

// The repository's default fixture is intentionally v5-only. Set V6_E2E=1
// with a v6 API fixture/report id to run these contract checks locally.
test.describe("Free DNA v6 renderer", () => {
  test.skip(!process.env.V6_E2E, "requires a v6 API fixture");

  const reportId = process.env.V6_REPORT_ID ?? "v6-fixture";

  test("renders the nine ordered, skippable beats", async ({ page }) => {
    await page.goto(`/report/${reportId}`);
    await expect(page.locator("section[id^='v6-beat-']")).toHaveCount(9);
    await expect(page.getByRole("button", { name: "Skip beat" })).toHaveCount(9);
    await expect(page.getByRole("progressbar", { name: "Story progress" })).toBeVisible();
  });

  test("keeps self-report controls separate and supports keyboard/reduced motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/report/${reportId}`);
    const firstRadio = page.locator("#v6-beat-1 input[type='radio']").first();
    if (await firstRadio.count()) {
      await firstRadio.focus();
      await page.keyboard.press("Space");
    }
    await expect(page.locator("#v6-beat-1")).toBeVisible();
    await expect(page.locator("main")).toContainText("user_reported");
    await expect(page.locator("#v6-beat-9").getByRole("button", { name: /Skip Deep/ })).toBeVisible();
  });
});
