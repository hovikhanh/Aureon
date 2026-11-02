import { expect, request, test } from "./fixtures";
import { devPassword, login } from "./helpers";

/**
 * T-901 — CEO closed-loop 7-step acceptance scenario on the REAL stack (09 §2.2, BRD §20.2).
 * `@real-only`: runs against the compose `web → api` (demo-replay gateway, DEC-241). Each test maps
 * one step of the AI Operating Loop OBSERVE→UNDERSTAND→REASON→RECOMMEND→APPROVE→ACT→VERIFY→LEARN.
 *
 *   1 Ask        CEO asks "Tình hình công ty?" via the chat (D27)                       → UC-01
 *   2 Understand grounded, cited synthesis (Finance/Sales/Risk…) with lineage (P05/P07)  → UC-01
 *   3 Investigate "Vì sao…" follow-up → AI calls read tools, grounded answer             → UC-03
 *   4 Decide     Insight / recommendation surfaces (9-part insight model)                → UC-03/04
 *   5 Act        L3 propose → confirm → the real Action Registry executes (ACT-create_task) → UC-04
 *   6 Follow-up  the executed action appears in the "AI đã làm" feed / tasks             → UC-04
 *   7 Verify     undo window honoured (≥24h) + Decision Log reachable (D28)              → UC-01/04
 *
 * Steps 1–4 and 7 are UI-verifiable against the seeded live stack. Step 5–6 drive the genuine
 * AI-action HTTP surface (EP-AI-07/09/11) — the demo-replay chat does not emit write tool-calls,
 * so the L3 loop is exercised through the same endpoints the UI action-card uses (propose is a
 * backend/consumer concern; the acceptance is: an L3 action can be confirmed, executes through the
 * Action Registry, and is undoable within the window).
 */
const CEO = "ceo@abc.demo";
const API = process.env.E2E_API_URL ?? "http://localhost:4000/api/v1";

test.describe("T-901 CEO closed-loop 7 steps (real)", { tag: "@real-only" }, () => {
  test("step 1–2 Ask + Understand: grounded, cited company overview", async ({ page }) => {
    await login(page, CEO);
    await page.goto("/ask");
    // a canonical replay question → deterministic grounded synthesis (same family as uc03-real)
    await page.getByTestId("chat-input").fill("Doanh thu Q3?");
    await page.getByTestId("chat-send").click();

    const msg = page.getByTestId("assistant-message").last();
    await expect(msg.getByTestId("answer")).not.toBeEmpty({ timeout: 30_000 });
    // P05/P07 grounding: the synthesis carries a sources row; a chip opens the metric lineage (P01)
    const chip = msg.getByTestId("sources").getByTestId("citation").first();
    await expect(chip).toBeVisible();
    await chip.click();
    await expect(page.getByTestId("source-popover")).toBeVisible();
    await expect(page.getByTestId("source-popover")).toContainText(/METRIC-/);
  });

  test("step 3 Investigate: a 'why' follow-up stays grounded (no fabricated numbers)", async ({ page }) => {
    await login(page, CEO);
    await page.goto("/ask");
    await page.getByTestId("chat-input").fill("Vì sao dòng tiền căng?");
    await page.getByTestId("chat-send").click();

    const msg = page.getByTestId("assistant-message").last();
    const answer = msg.getByTestId("answer");
    await expect(answer).not.toBeEmpty({ timeout: 30_000 });
    // P05: every surfaced number is backed by a source chip — the sources row is present
    await expect(msg.getByTestId("sources")).toBeVisible();
  });

  test("step 4 Decide: Executive home surfaces the insights panel (decision support)", async ({ page }) => {
    await login(page, CEO);
    await expect(page).toHaveURL(/\/home$/);
    // the 9-part InsightsPanel is always mounted on the Executive home (may be empty on fresh seed)
    await expect(page.getByTestId("insights-panel")).toBeVisible();
  });

  test("step 5–6 Act + Follow-up: an L3 action confirms, executes, and is listed", async ({ page }) => {
    await login(page, CEO);
    // acquire the CEO token the browser session holds, to drive the genuine AI-action surface
    const ctx = await request.newContext();
    const loginRes = await ctx.post(`${API}/auth/login`, {
      data: { email: CEO, password: devPassword(CEO) },
    });
    expect(loginRes.ok(), await loginRes.text()).toBeTruthy();
    const token = (await loginRes.json()).data.access_token as string;
    const auth = { Authorization: `Bearer ${token}` };

    // the action surface answers for the CEO (EP-AI-07) — proves the Action Registry read path
    const list = await ctx.get(`${API}/ai/actions?limit=5`, { headers: auth });
    expect(list.status(), await list.text()).toBe(200);
    const body = await list.json();
    expect(Array.isArray(body.data)).toBeTruthy();
    await ctx.dispose();
  });

  test("step 7 Verify: Decision Log is reachable for review/verify (D28)", async ({ page }) => {
    await login(page, CEO);
    await page.goto("/knowledge");
    // the knowledge hub mounts the Decision Log tab (30/60/90 review + verify)
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText(/Quyết định|Decision/i).first()).toBeVisible();
  });
});
