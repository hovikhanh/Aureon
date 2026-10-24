/** T-643 (mock part) — mock `/data-capture/*`, `/idp/*`, `/lineage/*` mirror 10 §7.2.4 (scope, 403/409/410/413/415/422). */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";
import { SEED_DOC } from "./capture-seed";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
const EMP = user("employee@abc.demo");
const MGR = user("manager@abc.demo");
const REV = user("reviewer@abc.demo");
const ADM = user("admin@abc.demo");
const IDEM = { "idempotency-key": "k-1" };
type Err = { code: string; details: Record<string, unknown> };
type Json<T> = { data: T; meta?: Record<string, unknown>; error?: Err };
type C = ReturnType<typeof user>;

async function call<T = unknown>(path: string, opts: { method?: string; claims?: C; body?: unknown; headers?: Record<string, string> } = {}) {
  const [p, q = ""] = path.split("?");
  const res = await handleMock({ method: opts.method ?? "GET", path: p!, query: new URLSearchParams(q), headers: new Headers(opts.headers), body: opts.body, claims: opts.claims ?? CEO });
  const json = res.status === 204 || !(res.headers.get("content-type") ?? "").includes("json") ? null : ((await res.json()) as Json<T>);
  return { status: res.status, json, res };
}
const post = <T = unknown>(path: string, claims: C, body: unknown = {}) => call<T>(path, { method: "POST", claims, body, headers: IDEM });

beforeEach(() => resetMockStore());

describe("EP-DC-13 inbox", () => {
  it("returns groups + meta.counts scoped per role; ADM = own #4 only (R-DEC-76)", async () => {
    const ceo = await call<{ document: { id: string } }[]>("/data-capture/inbox");
    expect(ceo.status).toBe(200);
    const counts = ceo.json!.meta!.counts as Record<string, number>;
    expect(Object.keys(counts).sort()).toEqual(["approved", "committed", "failed", "needs_review", "processing", "rejected", "rolled_back"]);
    expect(counts.committed).toBe(2);
    expect(Object.values(counts).reduce((a, b) => a + b, 0)).toBe((ceo.json!.meta!.pagination as { total: number }).total);
    const emp = await call<{ document: { id: string } }[]>("/data-capture/inbox", { claims: EMP });
    expect(emp.json!.data.map((r) => r.document.id)).toEqual([SEED_DOC.empTask]);
    const rev = await call<{ document: { id: string } }[]>("/data-capture/inbox", { claims: REV });
    expect(rev.json!.data.map((r) => r.document.id)).toEqual([SEED_DOC.roster]);
    const mgr = await call<{ document: { id: string } }[]>("/data-capture/inbox?group=failed", { claims: MGR });
    expect(mgr.json!.data.map((r) => r.document.id)).toEqual([SEED_DOC.failed]);
    expect((await call("/data-capture/inbox", { claims: ADM })).json!.data).toEqual([]);
    const own = await post<{ document_id: string }>("/data-capture/imports", ADM, { file: { name: "DOC-06-danh-sach-nhan-su.xlsx", size: 1, type: "" }, document_type: "HR_ROSTER" });
    expect((await call<{ document: { id: string } }[]>("/data-capture/inbox", { claims: ADM })).json!.data.map((r) => r.document.id)).toEqual([own.json!.data.document_id]);
    expect((await call("/data-capture/inbox?group=nope")).status).toBe(422);
  });

  it("source view: MANUAL → 422 no_file; file doc → url", async () => {
    const m = await call(`/data-capture/documents/${SEED_DOC.kpi}/source`);
    expect([m.status, m.json!.error!.details.reason]).toEqual([422, "no_file"]);
    const f = await call<{ url: string; page: number }>(`/data-capture/documents/${SEED_DOC.invoice}/source?page=1`);
    expect(f.json!.data.page).toBe(1);
    expect(decodeURIComponent(f.json!.data.url)).toContain(SEED_DOC.invoice);
  });
});

describe("EP-DC-15/16 manual (C1)", () => {
  it("EMP creates a task → COMMITTED, visible in /work/tasks, undoable", async () => {
    const form = await call<{ permitted: boolean; fields: { name: string }[] }>("/data-capture/forms/PLAN_KPI_OKR", { claims: CEO });
    expect(form.json!.data.permitted).toBe(true);
    expect(form.json!.data.fields.map((f) => f.name)).toContain("task_title");
    const r = await post<{ status: string; actions: { table: string; ids: string[] }[] }>("/data-capture/manual", EMP, { document_type: "PLAN_KPI_OKR", schema_version: 1, values: {}, rows: [{ period_key: "2026-Q4", owner_code: "NV-0046", task_title: "Gọi lại khách hàng X", task_due_date: "30/10/2026" }] });
    expect(r.status).toBe(201);
    expect(r.json!.data.status).toBe("COMMITTED");
    const taskId = r.json!.data.actions[0]!.ids[0]!;
    const tasks = await call<{ id: string; source_document_id: string }[]>("/work/tasks?limit=100", { claims: EMP });
    expect(tasks.json!.data.find((t) => t.id === taskId)?.source_document_id).toBeTruthy();
  });

  it("422 maps errors to fields; missing target permission → NEEDS_REVIEW", async () => {
    const bad = await post("/data-capture/manual", EMP, { document_type: "PERIOD_REPORT", schema_version: 1, values: {}, rows: [{ kpi_code: "NOPE", actual_value: "abc" }] });
    expect(bad.status).toBe(422);
    expect((bad.json!.error!.details.fields as { field: string; rule_code: string }[]).map((f) => `${f.field}:${f.rule_code}`).sort()).toEqual(["actual_value:NUMBER_FORMAT", "kpi_code:MASTER_NOT_FOUND"]);
    const rev = await post<{ status: string }>("/data-capture/manual", REV, { document_type: "PLAN_KPI_OKR", schema_version: 1, values: {}, rows: [{ period_key: "2026-Q4", owner_code: "NV-0001", task_title: "Việc A" }] });
    expect(rev.json!.data.status).toBe("NEEDS_REVIEW");
    expect((await call("/data-capture/manual", { method: "POST", claims: EMP, body: {} })).status).toBe(400);
  });
});
