import { expect, test } from "./fixtures";
import { login } from "./helpers";

/**
 * UC-03 CEO Assistant on the real stack (M2.4 exit, TC-M24-11). `@real-only`: runs against the
 * compose `web → api` with the gateway in demo-replay — the CEO's canonical question answers from
 * the recorded intents, grounded in live tools (every number carries a `SourceChip` → lineage).
 * No model-gateway fixture file is needed; the backend replays deterministically (DEC-241).
 */
test.describe("UC-03 CEO Assistant (real)", { tag: "@real-only" }, () => {
  test("CEO asks a revenue question → grounded, cited answer with a lineage chip", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/ask");
    await page.getByTestId("chat-input").fill("Doanh thu Q3?");
    await page.getByTestId("chat-send").click();

    const answer = page.getByTestId("assistant-message").last().getByTestId("answer");
    await expect(answer).not.toBeEmpty({ timeout: 30_000 });
    // P05 grounding: the answer cites a source; the chip opens the metric lineage (P01)
    const chip = answer.getByTestId("citation").first();
    await expect(chip).toBeVisible();
    await chip.click();
    const pop = page.getByTestId("source-popover");
    await expect(pop).toBeVisible();
    await expect(pop).toContainText("METRIC-FIN");
  });

  test("Executive home renders the AI insights panel (empty or populated, no crash)", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await expect(page).toHaveURL(/\/home$/);
    // the panel is always present on the Executive home; data may be empty on a fresh seed
    await expect(page.getByTestId("insights-panel")).toBeVisible();
  });
});
