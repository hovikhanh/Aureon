import { request } from "@playwright/test";
import { expect, test } from "./fixtures";
import { devPassword, isMockProject, loginSettled } from "./helpers";

const API = process.env.E2E_API_URL ?? "http://localhost:4000/api/v1";

/**
 * D-19 precondition on the real stack: a clean DB has no model-call log yet, so the test makes one
 * real chat turn first (EP-AI-01 as the CEO → the local model through the ModelGateway → an
 * `ai.model_call_logs` row, `ok` or — if the model times out — `timeout`). Nothing is inserted by
 * hand. Budget: a cold 3B load + one CPU-only turn measured 20–60 s on the demo host (D-19).
 */
async function makeRealModelCall(): Promise<void> {
  const ctx = await request.newContext();
  const auth = await ctx.post(`${API}/auth/login`, { data: { email: "ceo@abc.demo", password: devPassword("ceo@abc.demo") } });
  expect(auth.ok(), await auth.text()).toBeTruthy();
  const token = (await auth.json()).data.access_token as string;
  const res = await ctx.post(`${API}/ai/chat`, {
    headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() },
    data: { message: "Doanh thu Q3?", locale: "vi" },
    timeout: 150_000,
  });
  // 200 = answered; 504/502 = the provider failed — both are logged model calls (R-DEC-154)
  expect([200, 502, 504], await res.text()).toContain(res.status());
  await ctx.dispose();
}

/**
 * TC-M5-07 (e2e) — SCR-65 shows model-call telemetry, not only tool calls (M5 issue 3):
 * month summary (calls · tokens · cost · errors) above every tab, and the model-call tab filters
 * by provider / model / status (EP-AI-23 query params).
 */
test.describe("M5 · AI Control Center telemetry", { tag: "@mock" }, () => {
  test("summary strip + provider / status filters on Model calls", async ({ page }) => {
    if (!isMockProject()) {
      test.setTimeout(240_000); // one real CPU-only model turn first (D-19 measured, see above)
      await makeRealModelCall();
    }
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
