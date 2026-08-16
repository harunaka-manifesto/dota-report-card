import { test, expect } from "@playwright/test";

test("completed Free DNA report opens at the reveal and exposes finding share cards", async ({ page }) => {
  await page.goto("/report/fixture-report");

  await expect(page.locator("[data-page-kind='reveal']")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your Dota DNA" })).toBeVisible();
  await expect(page.locator("[data-page-kind='finding']").first()).toBeVisible();
  await expect(page.getByText("What this means").first()).toBeVisible();

  await page.locator("#identity-card").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("Share your Dota DNA")).toBeVisible();
  const cardSelect = page.getByLabel("Card");
  await expect(cardSelect).toHaveValue("identity");

  for (const card of ["identity", "exposed", "strength"]) {
    await cardSelect.selectOption(card);
    await expect(page.locator(".share-preview img")).toHaveAttribute("src", new RegExp(`/share/${card}\\?`));
  }
});

test("finding evidence and DNA X-ray methodology are accessible", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await page.locator("[data-page-kind='finding']").first().scrollIntoViewIfNeeded();
  await page.getByText("See why").first().click();
  await expect(
    page.locator("[data-page-kind='finding']").first().getByText("Receipts use deterministic summary-history evidence.")
  ).toBeVisible();
  await page.locator("#dna-xray").scrollIntoViewIfNeeded();
  await page.locator("#dna-xray").getByRole("button", { name: "How is this read?" }).first().click();
  await expect(page.getByRole("dialog", { name: "breadth" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Report progress" })).toBeVisible();
});
