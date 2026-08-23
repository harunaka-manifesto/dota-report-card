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
    await expect(page.locator("main")).toContainText("user_reported");
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
