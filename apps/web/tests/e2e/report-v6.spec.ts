import { test, expect } from "@playwright/test";

test.describe("Free DNA v6 renderer", () => {
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
    await expect(page.locator("main")).toContainText("Your answer is saved as your own reflection.");
    await expect(page.locator("#v6-beat-9").getByRole("button", { name: /Skip Deep/ })).toBeVisible();
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
    expect((await followUp.json()).comparison).toMatchObject({ label: "what_changed_in_these_five_games", causal: false, identity_updated: false });

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
      await expect(page.locator("section[id^='v6-beat-']")).toHaveCount(9);
      await expect(page.getByRole("button", { name: "Skip beat" })).toHaveCount(9);
      if (findingCount < 3) {
        await expect(page.locator("#v6-beat-5")).toContainText("Your next-choice movement stays about the same across the supported result states.");
      } else {
        await expect(page.locator("#v6-beat-5")).toContainText("After one loss, your next choice stays closer to your prior path.");
      }
      if (findingCount === 0) {
        await expect(page.locator("#v6-beat-9")).toContainText("No evidence-qualified Deep question was offered");
      } else {
        await expect(page.locator("#v6-beat-3")).toContainText("Your hero names cover more ground than the jobs behind them.");
      }
    });
  }

  test("covers V6.1 state, pool-width, Signature, and 375px fixtures", async ({ page }) => {
    for (const [fixture, text] of [
      ["v61-qualified-fixture", "Your hero names cover more ground than the jobs behind them."],
      ["v61-neutral-fixture", "No single pool shape separated cleanly."],
      ["v61-insufficient-fixture", "Not enough signal to call this one."],
      ["v61-mixed-fixture", "Your pool has two valid layers: the names move, while the jobs hold."],
      ["v61-narrow-fixture", "Narrow pool:"],
      ["v61-broad-fixture", "Broad pool:"],
      ["v61-signature-fixture", "Your Dota Signature."],
    ] as const) {
      await page.goto(`/report/${fixture}`);
      await expect(page.locator("main")).toContainText(text);
    }
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/report/v61-375-fixture");
    await expect(page.locator("#v6-beat-3")).toContainText("Narrow pool:");
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
    expect((await followUp.json()).comparison).toMatchObject({ causal: false, identity_updated: false });
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
    await page.locator("#v6-beat-5").getByRole("button", { name: "Skip beat" }).focus();
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
