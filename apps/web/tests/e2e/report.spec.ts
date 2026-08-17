import { test, expect } from "@playwright/test";

test("completed Free DNA report opens with the full Element and Portfolio story", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await expect(page.locator("[data-page-kind='element_scan']")).toBeVisible();
  await expect(page.getByRole("heading", { name: "The pieces of your Dota pattern" })).toBeVisible();
  await expect(page.locator(".element-tile")).toHaveCount(17);
  await page.locator("#hero-common-thread").scrollIntoViewIfNeeded();
  await expect(page.getByText("What keeps showing up across your established heroes?")).toBeVisible();
  await page.getByRole("button", { name: "Mobility" }).click();
  await page.locator("#hero-common-thread").getByRole("button", { name: "Reveal" }).click();
  await expect(page.getByText("Mobility is the strongest recurring functional trait across 5 established heroes.")).toBeVisible();
});

test("Hero Mirror and final share controls are keyboard accessible", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await page.locator("#hero-mirror").scrollIntoViewIfNeeded();
  await expect(page.getByRole("button", { name: "Reveal Hero Mirror" })).toBeVisible();
  await page.getByRole("button", { name: "Reveal Hero Mirror" }).click();
  await expect(page.getByText("The closest sufficiently sampled match is Anti-Mage.")).toBeVisible();
  await page.locator("#final-card").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("Share your Dota DNA")).toBeVisible();
  await expect(page.locator(".share-preview img")).toHaveAttribute("src", /\/share\/final\?/);
  await expect(page.getByText("Include name")).toBeVisible();
});
