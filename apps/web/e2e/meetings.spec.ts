import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * M2.3 `/meetings` (SCR-44, UC-02/UC-06). The chair pastes a transcript → EP-DC-38 returns a
 * NOT-committed preview with the MEETING_MINUTES doc type + predicted `ACT-create_action_item`
 * rows (L2 "AI soạn"); a Task is created ONLY after the chair approves and the owner is
 * unambiguously matched (R-DEC-103, autonomy ≤ L2). Meeting AUDIO recording is blocked
 * (R-DEC-22): `context=meeting` → 422 meeting-blocked message. Runs the `mock` project (the
 * `real` project builds the stack separately).
 */
test.describe("Meetings — UC-02 transcript → action items", { tag: "@mock" }, () => {
  test("CEO pastes transcript → MEETING_MINUTES preview + L2 action cards", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/meetings");
    await expect(page.getByTestId("meetings-view")).toBeVisible();

    await page.getByTestId("transcript-input").fill(
      "Biên bản họp giao ban. Quyết định tập trung Q4. Việc cần làm: soạn báo cáo — " +
        "người phụ trách Nguyễn Văn An — hạn 05/11/2026.",
    );
    await page.getByTestId("transcript-submit").click();

    await expect(page.getByTestId("meetings-preview")).toBeVisible();
    await expect(page.getByTestId("preview-doctype")).toHaveText("MEETING_MINUTES");
    await expect(page.getByTestId("predicted-actions")).toBeVisible();
    // L2 autonomy label (AI soạn) + at least one predicted action item.
    await expect(page.getByTestId("autonomy-label")).toBeVisible();
    await expect(page.getByTestId("action-item").first()).toBeVisible();
  });

  test("predicted action items render as L2 cards with owner-match gating", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/meetings");
    await page.getByTestId("transcript-input").fill(
      "Biên bản họp giao ban. Quyết định tập trung Q4. Việc cần làm: chốt báo giá — " +
        "người phụ trách Nguyễn Văn An — hạn 06/11/2026.",
    );
    await page.getByTestId("transcript-submit").click();
    await expect(page.getByTestId("meetings-preview")).toBeVisible();
    await expect(page.getByTestId("predicted-actions")).toBeVisible();

    // Each item carries an owner-match status; a matched owner enables approve (chair → task),
    // an ambiguous/unmatched owner keeps approve disabled until a human resolves it (R-DEC-103).
    const item = page.getByTestId("action-item").first();
    await expect(item).toBeVisible();
    await expect(item.getByTestId("owner-match")).toBeVisible();
    const matched = page.locator('[data-testid="action-item"][data-match="matched"]').first();
    if (await matched.count()) {
      await matched.getByTestId("action-approve").click();
      await expect(matched.getByTestId("action-approved")).toBeVisible();
    }
    const unmatched = page.locator('[data-testid="action-item"][data-match="unmatched"]').first();
    if (await unmatched.count()) {
      await expect(unmatched.getByTestId("action-approve")).toBeDisabled();
    }
  });
});

test.describe("Meetings — UC-06 guards", { tag: "@mock" }, () => {
  test("meeting audio recording is blocked (R-DEC-22)", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/meetings");
    // Drive the guard through the BFF directly: context=meeting → 422 meeting_audio_blocked.
    // The real API requires a UUID Idempotency-Key (the mock is lenient) — use a UUID for both.
    const res = await page.request.post("/api/backend/data-capture/natural-language", {
      headers: { "Idempotency-Key": crypto.randomUUID() },
      data: { text: "họp", channel: "C2", context: "meeting" },
    });
    expect(res.status()).toBe(422);
    const body = await res.json();
    expect(body.error.code).toBe("BUSINESS_RULE_VIOLATION");
    expect(body.error.details?.reason).toBe("meeting_audio_blocked");
  });

  test("missing Idempotency-Key → 400", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/meetings");
    const res = await page.request.post("/api/backend/data-capture/natural-language", {
      data: { text: "họp", channel: "C2" },
    });
    expect(res.status()).toBe(400);
  });
});
