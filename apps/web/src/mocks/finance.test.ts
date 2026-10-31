/** T-715F — mock BFF `/finance/*` + `/sales/*` (M2.2): envelope shape + aggregate `:query` gate.
 *
 * These endpoints (dashboard, budgets/status, what-if, pipeline) are AGGREGATE `finance:query` /
 * `sales:query` in 10 §7.2.7 — open to every DIR/MGR/CEO regardless of pillar (R-DEC-89, verified
 * against the live backend). Pillar scoping (F vs C) applies only to the detailed `:read` lists.
 * EMP/REV lack `:query` → 403. The mock must not be stricter than the real backend. */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
const CFO = user("cfo@abc.demo"); // DIR, pillar {F}
const VP_SALES = user("sales@abc.demo"); // DIR, pillar {C}
const HR_DIR = user("hr@abc.demo"); // DIR, pillar {O} — still has finance:query/sales:query (aggregate)
const EMP = user("employee@abc.demo"); // no :query → blocked from aggregates

async function call<T = unknown>(path: string, claims: ReturnType<typeof user>) {
  const [p, q = ""] = path.split("?");
  const res = await handleMock({ method: "GET", path: p!, query: new URLSearchParams(q), headers: new Headers(), body: undefined, claims });
  const json = (await res.json()) as { data?: T; meta?: Record<string, unknown>; error?: { code: string; details: Record<string, unknown> } };
  return { status: res.status, json };
}

beforeEach(() => resetMockStore());

describe("EP-60 finance dashboard", () => {
  it("CEO: 200 + FinanceDashboardOut envelope", async () => {
    const r = await call<{ pillar: string; status: string; summary: { currency: string; runway_months: number | null }; metrics: unknown[]; revenue_trend: unknown[]; open_alerts: number }>("/finance/dashboard", CEO);
    expect(r.status).toBe(200);
    expect(r.json.data!.pillar).toBe("F");
    expect(r.json.data!.summary.currency).toBe("VND");
    expect(Array.isArray(r.json.data!.metrics)).toBe(true);
    expect(r.json.data!.revenue_trend.length).toBe(6);
    expect(typeof r.json.data!.open_alerts).toBe("number");
  });

  it("any DIR reads the aggregate dashboard (CFO + HR-DIR): 200", async () => {
    expect((await call("/finance/dashboard", CFO)).status).toBe(200);
    expect((await call("/finance/dashboard", HR_DIR)).status).toBe(200); // aggregate, pillar-agnostic
  });

  it("EMP (no finance:query): 403 FORBIDDEN_ROLE", async () => {
    const r = await call("/finance/dashboard", EMP);
    expect(r.status).toBe(403);
    expect(r.json.error!.code).toBe("FORBIDDEN_ROLE");
  });
});

describe("EP-64 budget status / EP-69 what-if", () => {
  it("CEO: budget rows carry status ok|warning|critical", async () => {
    const r = await call<{ status: string; budget_utilization_pct: number; currency: string }[]>("/finance/budgets/status", CEO);
    expect(r.status).toBe(200);
    expect(r.json.data!.length).toBeGreaterThan(0);
    for (const b of r.json.data!) {
      expect(["ok", "warning", "critical"]).toContain(b.status);
      expect(b.currency).toBe("VND");
    }
  });

  it("CEO: what-if returns runway + sources; EMP (no :query) → 403", async () => {
    const r = await call<{ runway_months: number | null; sources: unknown[]; currency: string }>("/finance/what-if/runway", CEO);
    expect(r.status).toBe(200);
    expect(Array.isArray(r.json.data!.sources)).toBe(true);
    expect(r.json.data!.currency).toBe("VND");
    expect((await call("/finance/what-if/runway", EMP)).status).toBe(403);
  });
});

describe("EP-75 sales pipeline / EP-70 dashboard", () => {
  it("CEO: 200 + PipelineOut with 6 stages in canonical order", async () => {
    const r = await call<{ stages: { stage: string }[]; coverage_ratio: number | null; currency: string }>("/sales/pipeline", CEO);
    expect(r.status).toBe(200);
    expect(r.json.data!.stages.map((s) => s.stage)).toEqual(["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]);
    expect(r.json.data!.currency).toBe("VND");
  });

  it("any DIR reads the aggregate pipeline (VP_SALES + HR-DIR): 200; EMP → 403", async () => {
    expect((await call("/sales/pipeline", VP_SALES)).status).toBe(200);
    expect((await call("/sales/pipeline", HR_DIR)).status).toBe(200); // aggregate, pillar-agnostic
    const r = await call("/sales/pipeline", EMP);
    expect(r.status).toBe(403);
    expect(r.json.error!.code).toBe("FORBIDDEN_ROLE");
  });

  it("CEO: sales dashboard win_rate_pct = 100 (METRIC-CUS-02)", async () => {
    const r = await call<{ summary: { win_rate_pct: number | null } }>("/sales/dashboard", CEO);
    expect(r.status).toBe(200);
    expect(r.json.data!.summary.win_rate_pct).toBe(100);
  });
});
