import { expect, test } from "@playwright/test";

for (const fixture of ["legacy-v4-fixture", "legacy-v5-fixture", "v6-fixture"]) {
  test(`${fixture} uses the unsupported-format surface`, async ({ page }) => {
    await page.goto(`/report/${fixture}`);
    await expect(page.getByRole("heading", { name: "This report can’t open here." })).toBeVisible();
    await expect(page.getByText("It uses an older Dota DNA format. Generate a new report to continue.")).toBeVisible();
    await expect(page.getByRole("link", { name: "Generate new report" })).toHaveAttribute("href", "/");
  });
}

test("missing reports use the new not-found surface", async ({ page }) => {
  await page.goto("/report/not-a-report");
  await expect(page.getByRole("heading", { name: "This report isn’t here." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Generate new report" })).toBeVisible();
});
