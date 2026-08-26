import { test, expect, type Page } from "@playwright/test";

const STORY_STATE_COUNT = 103;

async function advanceToStep(page: Page, stepId: string): Promise<void> {
  for (let attempt = 0; attempt <= STORY_STATE_COUNT; attempt += 1) {
    if (await page.locator(`[data-story-step="${stepId}"]`).count()) return;
    const next = page.getByRole("button", { name: /^(Continue|Reveal observed shape|Finish)$/ }).last();
    await next.focus();
    await page.keyboard.press("Enter");
  }
  throw new Error(`Story step ${stepId} was not reached within ${STORY_STATE_COUNT} states`);
}

test.describe("Free DNA v6 renderer", () => {
  const reportId = process.env.V6_REPORT_ID ?? "v6-fixture";

  test("renders the complete narrative with 14-segment progress", async ({ page }) => {
    await page.goto(`/report/${reportId}`);
    await expect(page.getByRole("main", { name: /Free DNA V6 identity report/ })).toBeVisible();
    await expect(page.locator("[data-story-step='arrival.0']")).toBeVisible();
    await expect(page.getByRole("heading", { name: "We sequenced your Dota." })).toBeInViewport();
    await expect(page.getByRole("progressbar", { name: "Story progress" })).toHaveAttribute("aria-valuemax", "14");
    await expect(page.getByRole("progressbar", { name: "Story progress" })).toHaveAttribute("aria-valuetext", "Step 1 of 14");
    await expect(page.getByText(`Step 1 of ${STORY_STATE_COUNT}`, { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Skip chapter" })).toBeVisible();

    await page.getByRole("button", { name: "Continue" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("[data-story-step='arrival.1']")).toBeVisible();
    await expect(page.getByText(`Step 2 of ${STORY_STATE_COUNT}`, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Previous" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("[data-story-step='arrival.0']")).toBeVisible();
  });

  test("keeps self-report controls separate and supports keyboard/reduced motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/report/${reportId}`);
    const firstRadio = page.locator("input[type='radio']").first();
    if (await firstRadio.count()) {
      await firstRadio.focus();
      await page.keyboard.press("Space");
    }
    await expect(page.locator("[data-story-step='arrival.0']")).toBeVisible();
    await expect(page.locator("main")).toContainText("Your answer is saved as your own reflection.");
    await advanceToStep(page, "premium.3");
    await expect(page.getByRole("button", { name: "Explore with Deep" })).toBeVisible();
  });

  test("persists a server-owned baseline and routes the stored Deep specification", async ({ request }) => {
    const created = await request.post(`/v1/reports/${reportId}/interaction-sessions`, {
      data: { state: { user_reported: { identity_estimate: "focused_repeat" } } },
    });
    expect(created.status()).toBe(201);
    const session = await created.json();
    const token = session.access_token as string;
    const authorization = { Authorization: `Bearer ${token}` };

    const committed = await request.patch(`/v1/report-interactions/${session.session_id}`, {
      headers: { ...authorization, "If-Match": '"1"' },
      data: {
        state: {
          user_reported: {
            commitment: { recommendation_id: "REC_POOL_SHAPE", target_games: 5 },
          },
        },
      },
    });
    expect(committed.status()).toBe(200);
    const committedBody = await committed.json();
    expect(committedBody.recommendation_baseline).toMatchObject({ metric: "win_rate", value: 0.5 });

    const followUp = await request.post(`/v1/report-interactions/${session.session_id}/follow-up`, { headers: authorization });
    expect(followUp.status()).toBe(200);
    const followUpBody = await followUp.json();
    expect(followUpBody.comparison).toMatchObject({ label: "what_changed_in_these_five_games", causal: false, identity_updated: false });
    expect(followUpBody).not.toHaveProperty("session_id");
    expect(followUpBody.comparison).not.toHaveProperty("match_ids");

    const deep = await request.post(`/v1/reports/${reportId}/deep-analyses`, {
      headers: authorization,
      data: { diagnostic_question_id: "deep-v6-transfer", interaction_session_id: session.session_id },
    });
    expect(deep.status()).toBe(202);
    const deepBody = await deep.json();
    expect(deepBody.selection_plan.question_spec.family).toBe("transfer");
    expect(deepBody.selection_plan.question_spec.primary_hypothesis.positive_definition).toMatchObject({ name: "hero_set", params: { hero_ids: [3, 4] } });

    const deleted = await request.delete(`/v1/report-interactions/${session.session_id}`, { headers: authorization });
    expect(deleted.status()).toBe(204);
  });
});

test.describe("Free DNA V6.1 renderer", () => {
  for (const findingCount of [0, 1, 2, 3]) {
    test(`renders the ${findingCount}-finding story without synthesizing branches`, async ({ page }) => {
      await page.goto(`/report/v61-${findingCount}-fixture`);
      await expect(page.locator("[data-story-step='arrival.0']")).toBeVisible();
      await advanceToStep(page, "pool-shape.0");
      if (findingCount === 0) await expect(page.locator("[data-outcome-key]")).toHaveCount(0);
      else await expect(page.locator("[data-outcome-key]")).toHaveAttribute("data-outcome-key", "names_wide_jobs_narrow");
    });
  }

  test("covers V6.1 state, pool-width, Signature, and 375px fixtures", async ({ page }) => {
    for (const [fixture, hasOutcome] of [
      ["v61-qualified-fixture", true],
      ["v61-neutral-fixture", false],
      ["v61-insufficient-fixture", false],
      ["v61-mixed-fixture", true],
      ["v61-narrow-fixture", true],
      ["v61-broad-fixture", true],
      ["v61-signature-fixture", true],
    ] as const) {
      await page.goto(`/report/${fixture}`);
      await advanceToStep(page, "pool-shape.0");
      if (hasOutcome) await expect(page.locator("[data-outcome-key]")).toHaveCount(1);
      else await expect(page.locator("[data-outcome-key]")).toHaveCount(0);
    }
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/report/v61-375-fixture");
    await expect(page.locator("[data-story-step='arrival.0']")).toBeVisible();
    await expect(page.getByRole("progressbar", { name: "Story progress" })).toHaveAttribute("aria-valuemax", "14");
    expect(await page.locator("main.dnaStory").evaluate((element) => element.getBoundingClientRect().width)).toBeLessThanOrEqual(375);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
  });

  test("keeps resume transport and analytics identity-safe across accessible controls", async ({ page, request }) => {
    const created = await request.post("/v1/reports/v61-1-fixture/interaction-sessions", {
      data: {
        state: {
          schema_version: "report-interactions-1.0.0",
          current_beat: 4,
          completed_beats: [0, 1, 2, 3],
          skipped_beats: [],
          user_reported: { identity_estimate: "focused_repeat" },
          ui_state: { identity_revealed: true },
        },
      },
    });
    expect(created.status()).toBe(201);
    const session = await created.json();
    const followUpSessionResponse = await request.post("/v1/reports/v61-1-fixture/interaction-sessions", {
      data: { state: { schema_version: "report-interactions-1.0.0", current_beat: 0, completed_beats: [], skipped_beats: [], user_reported: {}, ui_state: {} } },
    });
    const followUpSession = await followUpSessionResponse.json();
    const followUpAuthorization = { Authorization: `Bearer ${followUpSession.access_token}` };
    const committed = await request.patch(`/v1/report-interactions/${followUpSession.session_id}`, {
      headers: { ...followUpAuthorization, "If-Match": '"1"' },
      data: {
        state: {
          schema_version: "report-interactions-1.0.0", current_beat: 6, completed_beats: [0, 1, 2, 3, 4, 5], skipped_beats: [], ui_state: {},
          user_reported: { commitment: { recommendation_id: "REC_POOL_SHAPE", target_games: 5, started_at: "2026-08-24T00:00:00Z" } },
        },
      },
    });
    expect(committed.status()).toBe(200);
    const followUp = await request.post(`/v1/report-interactions/${followUpSession.session_id}/follow-up`, { headers: followUpAuthorization });
    expect(followUp.status()).toBe(200);
    const followUpBody = await followUp.json();
    expect(followUpBody.comparison).toMatchObject({ causal: false, identity_updated: false });
    expect(followUpBody).not.toHaveProperty("session_id");
    expect(followUpBody.comparison).not.toHaveProperty("match_ids");
    const requestedUrls: string[] = [];
    page.on("request", (outgoing) => requestedUrls.push(outgoing.url()));
    await page.addInitScript(() => {
      (window as typeof window & { __v61Events?: unknown[] }).__v61Events = [];
      window.addEventListener("dota-report-analytics", (event) => {
        (window as typeof window & { __v61Events?: unknown[] }).__v61Events?.push((event as CustomEvent).detail);
      });
    });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/report/v61-1-fixture#session_id=${session.session_id}&access_token=${session.access_token}`);

    await expect(page.getByRole("main", { name: "Free DNA V6.1 identity report" })).toBeVisible();
    await expect(page.getByText("Saved journey resumed.", { exact: true })).toBeVisible();
    await expect(page.getByRole("progressbar", { name: "Story progress" })).toBeVisible();
    await expect(page.locator("[data-story-step='post-loss.0']")).toBeVisible();
    await expect(page.getByText(/^Step \d+ of \d+$/, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Skip chapter" }).focus();
    await page.keyboard.press("Enter");
    const events = await page.evaluate(() => (window as typeof window & { __v61Events?: Array<Record<string, unknown>> }).__v61Events ?? []);
    const encodedEvents = JSON.stringify(events).toLowerCase();
    expect(events.some((event) => event.event === "report.v6.beat_skipped.v1")).toBeTruthy();
    for (const forbidden of ["account_id", "report_id", "personaname", "access_token", "cohort:v61:"]) {
      expect(encodedEvents).not.toContain(forbidden);
    }
    expect(requestedUrls.every((url) => !url.includes(session.access_token))).toBeTruthy();

    await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
    const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(horizontalOverflow).toBeLessThanOrEqual(2);
  });
});
