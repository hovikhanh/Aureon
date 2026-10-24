/** T-626F..T-628F — mock `/goals/*`, `/kpis/*`, `/objectives/*`, `/key-results/*` mirror 10 §7.2.3 (scope R-DEC-57, 409/422, at-risk R-DEC-55). */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";
import { EMP_KR, UC04_KR, kpiId, krId, objId, iniId, soId, STRATEGY_ID } from "./goals-store";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
const EMP = user("employee@abc.demo");
const MGR = user("manager@abc.demo");
const SALES = user("sales@abc.demo");
const REV = user("reviewer@abc.demo");
const IDEM = { "idempotency-key": "k-1" };
type Err = { code: string; details: Record<string, unknown> };
type Json<T> = { data: T; meta?: Record<string, unknown>; error?: Err };

async function call<T = unknown>(path: string, opts: { method?: string; claims?: ReturnType<typeof user>; body?: unknown; headers?: Record<string, string> } = {}) {
  const [p, q = ""] = path.split("?");
  const res = await handleMock({ method: opts.method ?? "GET", path: p!, query: new URLSearchParams(q), headers: new Headers(opts.headers), body: opts.body, claims: opts.claims ?? CEO });
  const json = res.status === 204 ? null : ((await res.json()) as Json<T>);
  return { status: res.status, json };
}
interface Node { id: string; code?: string; title?: string; name?: string; restricted?: boolean; kpis?: Node[]; objectives?: Node[]; initiatives?: Node[]; key_results?: Node[]; children?: Node[]; strategic_objectives?: Node[]; latest_evaluation?: { band: string; period_key: string } | null; at_risk?: boolean; on_track?: boolean; projects?: unknown[]; progress_pct?: number }
interface Tree { strategies: Node[]; unaligned: { kpis: Node[]; objectives: Node[] } }
const flat = (n: Node): Node[] => [n, ...[...(n.strategic_objectives ?? []), ...(n.kpis ?? []), ...(n.objectives ?? []), ...(n.initiatives ?? []), ...(n.key_results ?? []), ...(n.children ?? [])].flatMap(flat)];
const all = (t: Tree) => [...t.strategies, ...t.unaligned.kpis, ...t.unaligned.objectives].flatMap(flat);

beforeEach(() => resetMockStore());

describe("EP-STR-01 /goals/tree", () => {
  it("CEO: Strategy → 4 SO → KPI/OKR/Initiative; UC-03 KPI CRITICAL; UC-04 KR at risk; projects under initiatives", async () => {
    const r = await call<Tree>("/goals/tree");
    expect(r.status).toBe(200);
    const st = r.json!.data.strategies;
    expect(st).toHaveLength(1);
    expect(st[0]!.strategic_objectives!.map((s) => s.code)).toEqual(["SO-01", "SO-02", "SO-03", "SO-04"]);
    const nodes = all(r.json!.data);
    const sal01 = nodes.find((n) => n.code === "KPI-SAL-01")!;
    expect(sal01.latest_evaluation).toMatchObject({ band: "CRITICAL", period_key: "2026-09" });
    expect(nodes.find((n) => n.id === krId(UC04_KR))?.at_risk).toBe(true);
    expect(nodes.filter((n) => n.at_risk === true)).toHaveLength(1);
    const ini3 = nodes.find((n) => n.id === iniId("INI-03"))!;
    expect(ini3.on_track).toBe(false);
    expect(ini3.projects).toHaveLength(2);
    expect(r.json!.data.unaligned).toEqual({ kpis: [], objectives: [] }); // seed: every root is aligned
  });

  it("EMP: only own KR/KPI + restricted ancestors (no initiatives, no other departments)", async () => {
    const r = await call<Tree>("/goals/tree", { claims: EMP });
    const nodes = all(r.json!.data);
    const open = nodes.filter((n) => n.restricted === false || n.restricted === undefined);
    expect(open.map((n) => n.id)).toEqual([krId(EMP_KR)]);
    expect(nodes.find((n) => n.id === soId("SO-04"))?.restricted).toBe(true);
    expect(nodes.find((n) => n.id === objId("OKR-SVC"))?.restricted).toBe(true);
    expect(nodes.find((n) => n.id === objId("OKR-SVC"))?.key_results).toHaveLength(1);
    expect(nodes.some((n) => n.code === "KPI-SAL-01")).toBe(false);
    expect(nodes.flatMap((n) => n.initiatives ?? [])).toHaveLength(0);
  });

  it("MGR SVC: own department + company rows; DIR {C}: pillar C + SAL; REV → 403; bad period → 400", async () => {
    const mgr = all((await call<Tree>("/goals/tree", { claims: MGR })).json!.data).filter((n) => !n.restricted);
    expect(mgr.some((n) => n.code === "KPI-SVC-01")).toBe(true);
    expect(mgr.some((n) => n.code === "KPI-CO-01")).toBe(true);
    expect(mgr.some((n) => n.code === "KPI-SAL-01")).toBe(false);
    const dir = all((await call<Tree>("/goals/tree", { claims: SALES })).json!.data).filter((n) => !n.restricted);
    expect(dir.some((n) => n.code === "KPI-SAL-01")).toBe(true);
    expect(dir.some((n) => n.code === "KPI-FIN-01")).toBe(false);
    expect((await call("/goals/tree", { claims: REV })).json!.error!.code).toBe("FORBIDDEN_ROLE");
    expect((await call("/goals/tree?period_key=2026-13")).status).toBe(400);
  });
});

describe("strategy / SO / initiative writes", () => {
  it("Strategy CEO-only; overlapping active → 422; duplicate code → 409; SO DIR only own pillar", async () => {
    const body = { code: "STR-X", name: "X", period_start: "2027-01-01", period_end: "2027-12-31", owner_id: CEO.sub, status: "active" };
    expect((await call("/goals/strategies", { method: "POST", body, claims: MGR, headers: IDEM })).json!.error!.code).toBe("FORBIDDEN_ROLE");
    expect((await call("/goals/strategies", { method: "POST", body })).status).toBe(400);
    const overlap = await call("/goals/strategies", { method: "POST", body, headers: IDEM });
    expect(overlap.json!.error).toMatchObject({ code: "BUSINESS_RULE_VIOLATION", details: { reason: "overlapping_active_strategy" } });
    expect((await call("/goals/strategies", { method: "POST", body: { ...body, code: "STR-2026-2027", status: "draft" }, headers: IDEM })).status).toBe(409);
    expect((await call(`/goals/strategies/${STRATEGY_ID}`, { method: "DELETE" })).json!.error!.details.reason).toBe("has_live_children");
    const so = { strategy_id: STRATEGY_ID, code: "SO-Z", title: "Z", owner_id: SALES.sub, pillar: "F" };
    expect((await call("/goals/strategic-objectives", { method: "POST", body: so, claims: SALES, headers: IDEM })).json!.error!.code).toBe("FORBIDDEN_SCOPE");
    expect((await call("/goals/strategic-objectives", { method: "POST", body: { ...so, pillar: "C" }, claims: SALES, headers: IDEM })).status).toBe(201);
    expect((await call(`/goals/strategic-objectives/${soId("SO-01")}`, { method: "DELETE" })).json!.error!.details.reason).toBe("has_live_links");
  });

  it("initiative: SO required (422), EMP 403, project-linked delete → 409, version conflict → 409", async () => {
    const b = { code: "INI-09", title: "Y", owner_id: MGR.sub, start_date: "2026-10-01", planned_end_date: "2026-12-31" };
    expect((await call("/goals/initiatives", { method: "POST", body: b, headers: IDEM })).json!.error).toMatchObject({ code: "BUSINESS_RULE_VIOLATION", details: { field: "strategic_objective_id" } });
    expect((await call("/goals/initiatives", { method: "POST", body: { ...b, strategic_objective_id: soId("SO-04") }, claims: EMP, headers: IDEM })).json!.error!.code).toBe("FORBIDDEN_ROLE");
    expect((await call("/goals/initiatives", { method: "POST", body: { ...b, strategic_objective_id: soId("SO-04") }, claims: MGR, headers: IDEM })).status).toBe(201);
    expect((await call(`/goals/initiatives/${iniId("INI-04")}`, { method: "DELETE" })).status).toBe(409);
    expect((await call(`/goals/initiatives/${iniId("INI-04")}`, { method: "PATCH", body: { version: 9, title: "n" } })).json!.error!.code).toBe("CONFLICT_STATE");
    expect((await call<unknown[]>(`/goals/initiatives/${iniId("INI-04")}/projects`)).json!.data).toHaveLength(2);
    expect((await call(`/goals/initiatives/${iniId("INI-01")}`, { claims: MGR })).json!.error!.code).toBe("FORBIDDEN_SCOPE");
  });
});

describe("KPI (EP-KPI-01..10, PRF-03/04)", () => {
  it("evaluations / targets history / measurement history; EMP 403 on other KPI", async () => {
    const id = kpiId("KPI-SAL-01");
    const ev = await call<{ period_key: string; band: string }[]>(`/kpis/${id}/evaluations`);
    expect(ev.json!.data.map((e) => [e.period_key, e.band])).toEqual([["2026-07", "NEAR"], ["2026-08", "BELOW"], ["2026-09", "CRITICAL"]]);
    const tg = await call<{ valid_to: string | null; target: number }[]>(`/kpis/${id}/targets?period_key=2026-09`);
    expect(tg.json!.data).toMatchObject([{ valid_to: null, target: 6 }]); // seed: one target version per period
    expect((await call(`/kpis/${id}`, { claims: EMP })).json!.error!.code).toBe("FORBIDDEN_SCOPE");
    expect((await call<unknown[]>("/kpis?band=CRITICAL")).json!.data).toHaveLength(1);
  });

  it("measurement: EMP other KPI 403, period/type mismatch 422, INSERT history, target-set EMP 403", async () => {
    const id = kpiId("KPI-SVC-02");
    expect((await call(`/kpis/${id}/measurements`, { method: "POST", body: { period_key: "2026-10", actual_value: 1.8 }, claims: EMP, headers: IDEM })).json!.error!.code).toBe("FORBIDDEN_SCOPE"); // seed: EMP owns no KPI
    expect((await call(`/kpis/${id}/measurements`, { method: "POST", body: { period_key: "2026-Q4", actual_value: 1 }, claims: MGR, headers: IDEM })).status).toBe(422);
    expect((await call(`/kpis/${id}/measurements`, { method: "POST", body: { period_key: "2026-10", actual_value: 1.8 }, claims: MGR, headers: IDEM })).status).toBe(201);
    await call(`/kpis/${id}/measurements`, { method: "POST", body: { period_key: "2026-10", actual_value: 1.7 }, claims: MGR, headers: IDEM });
    expect((await call<unknown[]>(`/kpis/${id}/measurements?period_key=2026-10`)).json!.data).toHaveLength(2);
    expect((await call(`/kpis/${id}/targets`, { method: "POST", body: { period_key: "2026-10", target: 1.5 }, claims: EMP, headers: IDEM })).json!.error!.code).toBe("FORBIDDEN_SCOPE");
    expect((await call("/kpis", { method: "POST", body: { code: "KPI-X", name: "x", unit: "x", target: 1, owner_id: EMP.sub }, claims: EMP, headers: IDEM })).json!.error!.code).toBe("FORBIDDEN_ROLE");
    const t = await call(`/kpis/${id}/targets`, { method: "POST", body: { period_key: "2026-10", target: 1.5, valid_from: "2026-10-20", reason: "Siết SLA" }, claims: MGR, headers: IDEM });
    expect(t.status).toBe(201);
    expect((await call(`/kpis/${id}/targets`, { method: "POST", body: { period_key: "2026-10", target: 1.4, valid_from: "2026-10-05" }, claims: MGR, headers: IDEM })).status).toBe(422);
    expect((await call(`/kpis/${kpiId("KPI-SVC-01")}/check-ins`, { method: "POST", body: { value: 97, confidence: "HIGH" }, claims: EMP, headers: IDEM })).json!.error!.code).toBe("FORBIDDEN_SCOPE");
  });

  it("KPI drops into BELOW → alert notification for owner / MGR (R-DEC-59)", async () => {
    const id = kpiId("KPI-SVC-01");
    expect((await call(`/kpis/${id}/check-ins`, { method: "POST", body: { value: 60, confidence: "LOW" }, claims: MGR, headers: IDEM })).status).toBe(201);
    const n = await call<{ kind: string; link: string }[]>("/notifications", { claims: MGR });
    expect(n.json!.data[0]).toMatchObject({ kind: "alert", link: `/goals/kpis/${id}` });
  });
});

describe("OKR + check-in (EP-OKR-*, EP-PRF-01/02/05/06)", () => {
  it("EMP F4: due cards (prefill null), check-in own KR, other KR 403, MGR sees it in the team feed", async () => {
    const due = await call<{ target_id: string; due: boolean; prefill: null }[]>("/goals/check-ins/due", { claims: EMP });
    expect(due.json!.data.map((d) => d.target_id)).toEqual([krId(EMP_KR)]);
    expect(due.json!.data.every((d) => d.prefill === null)).toBe(true);
    expect(due.json!.data[0]).toMatchObject({ target_type: "key_result", unit: "ngày", current_value: 1.9, target: 1.8, last_checked_in_at: "2026-10-16T02:00:00Z" });
    const r = await call<{ target_type: string; kr_measurement: { previous_progress_pct: number } }>(`/key-results/${krId(EMP_KR)}/check-ins`, {
      method: "POST", body: { value: 1.85, confidence: "MEDIUM", note: "ok" }, claims: EMP, headers: IDEM });
    expect(r.status).toBe(201);
    expect(r.json!.data.target_type).toBe("key_result");
    expect((await call<{ due: boolean; target_id: string }[]>("/goals/check-ins/due", { claims: EMP })).json!.data.find((d) => d.target_id === krId(EMP_KR))?.due).toBe(false);
    expect((await call(`/key-results/${krId("OKR-SVC:0")}/check-ins`, { method: "POST", body: { value: 96, confidence: "HIGH" }, claims: EMP, headers: IDEM })).json!.error!.code).toBe("FORBIDDEN_SCOPE");
    expect((await call(`/key-results/${krId(EMP_KR)}/check-ins`, { method: "POST", body: { value: 1.85 }, claims: EMP, headers: IDEM })).status).toBe(422);
    const feed = await call<{ user_id: string; target_title: string }[]>("/goals/check-ins", { claims: MGR });
    expect(feed.json!.data[0]).toMatchObject({ user_id: EMP.sub });
    expect((await call<{ department_id: string }[]>("/goals/check-ins", { claims: MGR })).json!.data.every((c) => c.department_id === MGR.department_id || c.department_id === null)).toBe(true);
  });

  it("check-in that makes a KR at risk → alert with SCR-59 link; objective not active → 409; PATCH confidence → 422", async () => {
    const kr = krId("OKR-SAL:0");
    await call(`/key-results/${kr}/check-ins`, { method: "POST", body: { value: 1, confidence: "MEDIUM" }, claims: SALES, headers: IDEM });
    const n = await call<{ kind: string; link: string }[]>("/notifications", { claims: SALES });
    expect(n.json!.data[0]).toMatchObject({ kind: "alert", link: `/goals/objectives/${objId("OKR-SAL")}?kr=${kr}` });
    const k = await call<{ at_risk: boolean; at_risk_reasons: string[] }>(`/key-results/${kr}`);
    expect(k.json!.data.at_risk_reasons).toContain("declining");
    expect((await call(`/key-results/${kr}`, { method: "PATCH", body: { confidence: "LOW" } })).status).toBe(422);
    await call(`/objectives/${objId("OKR-SAL")}`, { method: "PATCH", body: { status: "closed" } });
    expect((await call(`/key-results/${kr}/check-ins`, { method: "POST", body: { value: 2, confidence: "HIGH" }, headers: IDEM })).json!.error!.details.reason).toBe("objective_not_active");
  });

  it("history: PRF-01 desc with kr_measurement, OKR-11 measurements; >5 KR → 422; EMP cannot create", async () => {
    const h = await call<{ kr_measurement: { value: number } }[]>(`/key-results/${krId(UC04_KR)}/check-ins`);
    expect(h.json!.data.map((c) => c.kr_measurement.value)).toEqual([2.52, 2.58]);
    expect((await call<unknown[]>(`/key-results/${krId(UC04_KR)}/measurements`)).json!.data).toHaveLength(2);
    expect((await call(`/objectives/${objId("OKR-SAL")}/key-results`, { method: "POST", body: { title: "x", baseline: 0, target: 1, unit: "x", owner_id: CEO.sub }, claims: EMP, headers: IDEM })).status).toBe(403);
    for (let i = 0; i < 2; i++) await call(`/objectives/${objId("OKR-SAL")}/key-results`, { method: "POST", body: { title: `x${i}`, baseline: 0, target: 1, unit: "x", owner_id: CEO.sub }, headers: IDEM });
    expect((await call(`/objectives/${objId("OKR-SAL")}/key-results`, { method: "POST", body: { title: "x9", baseline: 0, target: 1, unit: "x", owner_id: CEO.sub }, headers: IDEM })).status).toBe(422);
    expect((await call<{ at_risk_kr_count: number }[]>("/objectives?at_risk=true")).json!.data).toHaveLength(1);
  });
});
