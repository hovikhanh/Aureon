import { expect, test } from "./fixtures";
import { login } from "./helpers";

/**
 * TC-M11-11 (T-606): project `mock` runs green with no backend — the BFF answers from
 * `src/mocks` (API_MODE=mock). Tagged `@mock-only`: the `real` project excludes it via
 * `grepInvert` (it asserts the mock marker header).
 */
test.describe("mock harness (no backend)", { tag: "@mock-only" }, () => {
  test("BFF serves seeded metrics in the backend envelope", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    const res = await page.request.get("/api/backend/dashboard/metrics");
    expect(res.status()).toBe(200);
    expect(res.headers()["x-api-mode"]).toBe("mock");
    const body = (await res.json()) as { data: { metric_code: string; status: string }[] };
    expect(body.data.find((m) => m.metric_code === "METRIC-FIN-03")?.status).toBe("critical");
  });

  test("role claims: ADM is denied dashboard data with FORBIDDEN_ROLE", async ({ page }) => {
    await login(page, "admin@abc.demo", "unused-on-mock");
    const res = await page.request.get("/api/backend/dashboard/metrics");
    expect(res.status()).toBe(403);
    expect(((await res.json()) as { error: { code: string } }).error.code).toBe("FORBIDDEN_ROLE");
  });

  test("chat streams through the mock SSE end to end", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/ask");
    await page.getByTestId("chat-input").fill("Tình hình công ty?");
    await page.getByTestId("chat-send").click();
    await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-streaming", "false");
    await expect(page.getByTestId("answer")).toContainText("METRIC-FIN-03");
    await expect(page.getByTestId("tool-call")).toContainText("get_metric_values");
  });
});
