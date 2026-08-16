import { test, expect } from "@playwright/test";

test("completed Free DNA report opens at the reveal and exposes all share cards", async ({ page }) => {
  await page.goto("/report/fixture-report");

  await expect(page.locator("[data-page-kind='reveal']")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your Dota DNA" })).toBeVisible();

  await page.locator("#final-card").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("Share your Dota DNA")).toBeVisible();
  const cardSelect = page.getByLabel("Card");
  await expect(cardSelect).toHaveValue("final");

  for (const card of ["dna", "heroes", "final"]) {
    await cardSelect.selectOption(card);
    await expect(page.locator(".share-preview img")).toHaveAttribute("src", new RegExp(`/share/${card}\\?`));
  }
});

test("dimension methodology is keyboard-dismissible and report progress is exposed", async ({ page }) => {
  await page.goto("/report/fixture-report");
  await page.locator("#breadth").scrollIntoViewIfNeeded();
  await page.locator("#breadth").getByRole("button", { name: "How is this read?" }).click();
  await expect(page.getByRole("dialog", { name: "breadth" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Report progress" })).toBeVisible();
});
