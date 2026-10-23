import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

/**
 * SCR-16 chat (T-506). The EP-111 SSE body is fixture-stubbed at the browser boundary: AI tests
 * never call a live provider (CLAUDE §6.6 #7, MODEL_GATEWAY_MODE=fixture). The event sequence
 * mirrors the backend contract `start → tool_call → tool_result → token… → done` (10 §4.8).
 */
const frame = (id: number, event: string, data: unknown) => `id: ${id}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
const SOURCE = { type: "metric_value", id: "revenue_q3", label: "Doanh thu Q3/2026", period_key: "2026-Q3", value: 45200000000, lineage_url: "/dashboard/metrics/METRIC-FIN-01" };
const ANSWER = "Doanh thu Q3/2026 đạt 45,2 tỷ đồng [1], đạt 98,1% kế hoạch.";

test("streams answer token-by-token with tool call and citation", { tag: "@mock" }, async ({ page }) => {
  await page.route("**/api/backend/ai/chat/stream", async (route) => {
    const req = route.request();
    expect(req.headers()["idempotency-key"]).toBeTruthy();
    expect(req.postDataJSON()).toMatchObject({ message: "Doanh thu Q3?", locale: "vi" });
    const tokens = ANSWER.match(/.{1,8}/g) ?? [];
    let id = 0;
    const body = [
      frame(++id, "start", { conversation_id: "11111111-1111-1111-1111-111111111111", message_id: "m-1" }),
      frame(++id, "tool_call", { call_id: "get_finance_metric", tool: "get_finance_metric" }),
      frame(++id, "tool_result", { call_id: "get_finance_metric", tool: "get_finance_metric", status: "ok", latency_ms: 42, sources: [SOURCE] }),
      ...tokens.map((delta) => frame(++id, "token", { delta })),
      frame(++id, "done", { message_id: "m-1", answer: ANSWER, sources: [SOURCE], function_calls: [], truncated: false, warnings: [] }),
    ].join("");
    await route.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body });
  });
  await loginAs(page, "ceo@abc.demo");
  await page.getByTestId("nav-ai").click();
  await expect(page).toHaveURL(/\/ai$/);
  await page.getByTestId("chat-input").fill("Doanh thu Q3?");
  await page.getByTestId("chat-send").click();

  await expect(page.getByTestId("user-message")).toContainText("Doanh thu Q3?");
  const answer = page.getByTestId("answer");
  await expect(answer).toContainText("45,2 tỷ");
  await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-streaming", "false");
  await expect(page.getByTestId("tool-call")).toContainText("get_finance_metric");

  await answer.getByTestId("citation").first().click();
  await expect(page.getByTestId("source-popover")).toContainText("revenue_q3");
  await expect(page.getByTestId("source-popover")).toContainText("Doanh thu Q3/2026");
});

test("shows API error from the stream", { tag: "@mock" }, async ({ page }) => {
  await page.route("**/api/backend/ai/chat/stream", (route) =>
    route.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body: frame(1, "start", {}) + frame(2, "error", { code: "AI_DISABLED", message: "x" }) }),
  );
  await loginAs(page, "ceo@abc.demo");
  await page.goto("/ai");
  await page.getByTestId("chat-input").fill("Lương của A?");
  await page.getByTestId("chat-input").press("Enter");
  await expect(page.getByTestId("chat-error")).toContainText("không xử lý");
});

/**
 * T-509 demo replay through the real stack (BFF → API, DEMO_MODE=true): no model call, the
 * recorded intent replays with live tool numbers. Requires the dev API with DEMO_MODE=true.
 */
test("demo mode: recorded question answers fast with citation [1]", async ({ page }) => {
  await loginAs(page, "ceo@abc.demo");
  await page.goto("/ai");
  await page.getByTestId("chat-input").fill("Doanh thu Q3?");
  const started = Date.now();
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("assistant-message")).toHaveAttribute("data-streaming", "false", { timeout: 10_000 });
  expect(Date.now() - started).toBeLessThan(5_000);
  const answer = page.getByTestId("answer");
  await expect(answer).toContainText("98,1%");
  await answer.getByTestId("citation").first().click();
  await expect(page.getByTestId("source-popover")).toContainText("METRIC-FIN-01");
});

test("long wait shows progressive hints", { tag: "@mock" }, async ({ page }) => {
  await page.clock.install();
  await page.route("**/api/backend/ai/chat/stream", () => new Promise(() => {})); // never answers
  await loginAs(page, "ceo@abc.demo");
  await page.goto("/ai");
  await page.getByTestId("chat-input").fill("Câu hỏi khó");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("thinking")).toBeVisible();
  await page.clock.runFor(11_000);
  await expect(page.getByTestId("wait-hint")).toHaveAttribute("data-phase", "thinking");
  await page.clock.runFor(20_000);
  await expect(page.getByTestId("wait-hint")).toContainText("Đang xử lý phức tạp");
  await page.clock.runFor(60_000);
  await expect(page.getByTestId("wait-hint")).toContainText("thử lại sau");
});
