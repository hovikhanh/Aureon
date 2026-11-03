import { expect, test } from "./fixtures";
import { loginSettled } from "./helpers";

/**
 * TC-M5-07 (e2e) — SCR-65 shows model-call telemetry, not only tool calls (M5 issue 3):
 * month summary (calls · tokens · cost · errors) above every tab, and the model-call tab filters
 * by provider / model / status (EP-AI-23 query params).
 */
test.describe("M5 · AI Control Center telemetry", { tag: "@mock" }, () => {
  test("summary strip + provider / status filters on Model calls", async ({ page }) => {
    await loginSettled(page, "admin@abc.demo");
    await page.goto("/admin/ai/logs?tab=model");
    const summary = page.getByTestId("usage-summary");
    await expect(summary).toBeVisible();
    for (const k of ["calls", "tokens", "cost", "errors"]) await expect(summary.getByTestId(`usage-${k}`)).not.toContainText("…");

    await expect(page.getByTestId("model-calls")).toBeVisible();
    const rows = page.getByTestId("model-call-row");
    await expect(rows.first()).toBeVisible();

    const provider = page.getByTestId("mc-provider");
    const options = await provider.locator("option").allTextContents();
    expect(options.length).toBeGreaterThan(1); // "Tất cả" + real providers of this month
    const chosen = options[1];
    await provider.selectOption({ label: chosen });
    await expect(async () => {
      const providers = await rows.locator("td:nth-child(2) > div:first-child").allTextContents();
      expect(providers.length).toBeGreaterThan(0);
      expect(new Set(providers)).toEqual(new Set([chosen]));
    }).toPass();

    await provider.selectOption({ index: 0 }); // back to all providers
    // filter by a status that really exists in the data (mock: ok/error; real stack: ok/timeout…)
    await expect(rows.first()).toBeVisible();
    const present = (await rows.locator("td:nth-child(7)").allTextContents()).map((s) => s.trim());
    const rare = present.find((s) => s !== "ok") ?? "ok";
    await page.getByTestId("mc-status").selectOption(rare);
    await expect(async () => {
      const statuses = (await rows.locator("td:nth-child(7)").allTextContents()).map((s) => s.trim());
      expect(statuses.length).toBeGreaterThan(0);
      expect(new Set(statuses)).toEqual(new Set([rare]));
    }).toPass();
  });
});
