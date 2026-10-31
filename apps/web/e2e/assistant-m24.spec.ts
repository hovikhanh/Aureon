import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * M2.4 CEO Assistant surfaces (R-DEC-112, SCR-40 / SCR-16). `@mock`: the Executive home serves a
 * seeded 9-part insight (EP-AI-05) and the ⌘K palette routes to /ask. The SSE answer is
 * fixture-stubbed at the browser boundary — AI tests never hit a live provider (CLAUDE §6.6 #7).
 */
const frame = (id: number, event: string, data: unknown) => `id: ${id}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
const SOURCE = { type: "metric_value", id: "METRIC-FIN-01", label: "Doanh thu Q3/2026", period_key: "2026-Q3", value: 45200000000, lineage_url: "/dashboard/metrics/METRIC-FIN-01" };
const ANSWER = "Doanh thu Q3/2026 đạt 45,2 tỷ đồng [1].";

function stubChat(page: import("@playwright/test").Page) {
  return page.route("**/api/backend/ai/chat/stream", async (route) => {
    let id = 0;
    const body = [
      frame(++id, "start", { conversation_id: "22222222-2222-2222-2222-222222222222", message_id: "m-1" }),
      frame(++id, "tool_result", { call_id: "c1", tool: "get_finance_dashboard", status: "ok", latency_ms: 12, sources: [SOURCE] }),
      ...(ANSWER.match(/.{1,8}/g) ?? []).map((delta) => frame(++id, "token", { delta })),
      frame(++id, "done", { message_id: "m-1", answer: ANSWER, sources: [SOURCE], function_calls: [], truncated: false, warnings: [] }),
    ].join("");
    await route.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body });
  });
}

test.describe("M2.4 CEO Assistant", { tag: "@mock" }, () => {
  test("⌘K palette opens and routes to /ask with the question prefilled + auto-sent", async ({ page }) => {
    await stubChat(page);
    await loginAs(page, "ceo@abc.demo");
    await expect(page).toHaveURL(/\/home$/);

    await page.keyboard.press("Control+k");
    const palette = page.getByTestId("command-palette");
    await expect(palette).toBeVisible();
    await palette.getByTestId("palette-input").fill("Doanh thu Q3?");
    await palette.getByTestId("palette-ask").click();

    await expect(page).toHaveURL(/\/ask\?q=/);
    // the question auto-sends once on mount → user bubble + grounded, cited answer
    await expect(page.getByTestId("user-message")).toContainText("Doanh thu Q3?");
    await expect(page.getByTestId("answer")).toContainText("45,2 tỷ");
    await expect(page.getByTestId("citation").first()).toBeVisible();
  });

  test("Escape closes the palette", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.keyboard.press("Meta+k");
    await expect(page.getByTestId("command-palette")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("command-palette")).toHaveCount(0);
  });

  test("Executive home shows a 9-part InsightCard with grounded evidence and 'Tại sao?'", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await expect(page).toHaveURL(/\/home$/);
    const panel = page.getByTestId("insights-panel");
    await expect(panel).toBeVisible();
    const card = panel.getByTestId("insight-card").first();
    await expect(card).toHaveAttribute("data-kind", "recommendation");
    await expect(card).toHaveAttribute("data-severity", "critical");
    await expect(card.getByTestId("insight-observation")).toContainText("42,5%");
    await expect(card.getByTestId("insight-evidence").getByTestId("citation")).toBeVisible();
    await expect(card.getByTestId("confidence-badge")).toHaveAttribute("data-band", "MEDIUM");

    // reasoning parts hidden until "Tại sao?"
    await expect(card.getByTestId("insight-reasoning")).toHaveCount(0);
    await card.getByTestId("insight-why").click();
    await expect(card.getByTestId("insight-reasoning")).toBeVisible();
    await expect(card.getByTestId("insight-root-cause")).toBeVisible();
    await expect(card.getByTestId("insight-risk")).toBeVisible();
    await expect(card.getByTestId("insight-recommendation")).toBeVisible();
  });

  test("Evidence citation opens the lineage popover (P01/P05)", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    const card = page.getByTestId("insights-panel").getByTestId("insight-card").first();
    await card.getByTestId("insight-evidence").getByTestId("citation").click();
    const pop = page.getByTestId("source-popover");
    await expect(pop).toBeVisible();
    await expect(pop).toContainText("METRIC-HR-04");
    await expect(pop).toContainText("/goals/kpis/kpi-hr-04"); // lineage link (P01)
  });
});
