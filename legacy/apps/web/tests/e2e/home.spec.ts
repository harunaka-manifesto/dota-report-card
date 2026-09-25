import { test, expect } from "@playwright/test";

test("home page asks for a player identifier", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel("Start with a public identifier")).toBeVisible();
  await expect(page.getByRole("button", { name: "Build report" })).toBeVisible();
  await expect(page.getByLabel("Start with a public identifier")).toHaveValue("");
});

test("home page explains the bounded input to evidence path", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /with the receipts/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "One input. Three kinds of clarity." })).toBeVisible();
  await expect(page.locator("[data-landing-step]")).toHaveCount(3);
  await expect(page.getByText(/Public data only\. No account connection/)).toBeVisible();
  await expect(page.getByText(/What is missing stays missing/)).toBeVisible();
  await expect(page.locator("#how-it-works")).toBeVisible();
  const startLink = page.getByRole("link", { name: "Start a report" });
  await expect(startLink).toHaveAttribute("href", "#start");
  expect((await startLink.boundingBox())?.height).toBeGreaterThanOrEqual(44);
  await startLink.click();
  await expect(page).toHaveURL(/#start$/);
  await expect(page.getByLabel("Start with a public identifier")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("identity dashboard");
  await expect(page.locator("body")).not.toContainText("useful experiment");
});

test("empty submission is rejected without an API request", async ({ page }) => {
  let requests = 0;
  await page.route("**/v1/analyses", async (route) => {
    requests += 1;
    await route.continue();
  });
  await page.goto("/");
  await page.getByLabel("Start with a public identifier").fill(" ");
  await page.getByRole("button", { name: "Build report" }).click();
  await expect(page.locator("p.error")).toContainText("Enter a public OpenDota profile");
  expect(requests).toBe(0);
});

test("queued analysis surfaces a safe failure message", async ({ page }) => {
  await page.route("**/v1/analyses", async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "job-failed",
        status: "queued",
        reused: false,
        events_url: "/v1/analyses/job-failed/events"
      })
    });
  });
  await page.route("**/v1/analyses/job-failed", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "job-failed",
        account_id: 42,
        status: "failed",
        stage: "failed",
        processed_matches: 0,
        eligible_matches: 0,
        warnings: [],
        failure_code: "PROFILE_PRIVATE_OR_UNAVAILABLE",
        message: "This profile is private or unavailable. Check the ID and privacy settings.",
        report_id: null,
        events_url: "/v1/analyses/job-failed/events"
      })
    });
  });
  await page.goto("/");
  await page.getByLabel("Start with a public identifier").fill("42");
  await page.getByRole("button", { name: "Build report" }).click();
  await expect(page.locator("[aria-live='polite']")).toContainText("failed");
  await expect(page.locator("p.error")).toContainText("private or unavailable");
  await expect(page.getByLabel("Start with a public identifier")).toBeFocused();
});

test("loading moves focus to the live status", async ({ page }) => {
  await page.route("**/v1/analyses", async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ job_id: "job-running", status: "queued", reused: false })
    });
  });
  await page.route("**/v1/analyses/job-running", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "job-running",
        status: "running",
        stage: "fetching_history",
        warnings: [],
        report_id: null,
        failure_code: null,
        message: null
      })
    });
  });
  await page.goto("/");
  await page.getByLabel("Start with a public identifier").fill("42");
  await page.getByRole("button", { name: "Build report" }).click();
  await expect(page.locator(".lookup-status")).toBeFocused();
});

test("non-2xx queue responses become actionable errors", async ({ page }) => {
  await page.route("**/v1/analyses", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        code: "ANALYSIS_UNAVAILABLE",
        message: "Analysis is temporarily unavailable. Please try again."
      })
    });
  });
  await page.goto("/");
  await page.getByLabel("Start with a public identifier").fill("42");
  await page.getByRole("button", { name: "Build report" }).click();
  await expect(page.locator("p.error")).toContainText("temporarily unavailable");
});

test("missing server API configuration becomes an actionable error", async ({ page }) => {
  await page.route("**/v1/analyses", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        code: "API_NOT_CONFIGURED",
        message: "The report service is not configured. Set API_BASE_URL on the web deployment."
      })
    });
  });
  await page.goto("/");
  await page.getByLabel("Start with a public identifier").fill("193875165");
  await page.getByRole("button", { name: "Build report" }).click();
  await expect(page.locator("p.error")).toContainText("Set API_BASE_URL");
});

test("completed analysis navigates to its report", async ({ page }) => {
  await page.route("**/v1/analyses", async (route) => {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "job-complete",
        status: "queued",
        reused: false,
        events_url: "/v1/analyses/job-complete/events"
      })
    });
  });
  await page.route("**/v1/analyses/job-complete", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "job-complete",
        account_id: 42,
        status: "completed",
        stage: "completed",
        processed_matches: 50,
        eligible_matches: 20,
        warnings: [],
        failure_code: null,
        message: null,
        report_id: "report-complete",
        events_url: "/v1/analyses/job-complete/events"
      })
    });
  });
  await page.goto("/");
  await page.getByLabel("Start with a public identifier").fill("42");
  await page.getByRole("button", { name: "Build report" }).click();
  await expect(page).toHaveURL(/\/report\/report-complete$/);
});

test("home form remains usable on a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Build report" })).toBeVisible();
  await expect(page.getByLabel("Start with a public identifier")).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});
