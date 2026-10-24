/** T-625F — mock BFF `/work/*` + `/workflow/*` mirrors the BE rules (scope, 409/422, workload, approvals). */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor, mockId } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";
import { empId } from "./work-store";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
const EMP = user("employee@abc.demo");
const MGR = user("manager@abc.demo");
const REV = user("reviewer@abc.demo");
const CFO = user("cfo@abc.demo");
const IDEM = { "idempotency-key": "k-1" };
const tid = (k: string) => mockId("task", k);
type Err = { code: string; details: Record<string, unknown> };

async function call<T = unknown>(path: string, opts: { method?: string; claims?: ReturnType<typeof user>; body?: unknown; headers?: Record<string, string> } = {}) {
  const [p, q = ""] = path.split("?");
  const res = await handleMock({ method: opts.method ?? "GET", path: p!, query: new URLSearchParams(q), headers: new Headers(opts.headers), body: opts.body, claims: opts.claims ?? CEO });
  const json = res.status === 204 ? null : ((await res.json()) as { data: T; meta?: Record<string, unknown>; error?: Err });
  return { status: res.status, json };
}
interface Task { id: string; version: number; status: string; assignee_id: string | null; overdue: boolean; subtask_count?: number; depends_on_open?: number; title: string }

beforeEach(() => resetMockStore());

describe("mock tasks", () => {
  it("EMP mine=true: own tasks, filters, derived counters", async () => {
    const r = await call<Task[]>("/work/tasks?mine=true&status=in_progress&status=todo&limit=100", { claims: EMP });
    expect(r.status).toBe(200);
    const ids = r.json!.data.map((t) => t.id);
    expect(ids).toEqual(expect.arrayContaining([tid("MOCK-E1"), tid("MOCK-E2"), tid("MOCK-E3")]));
    expect(ids).not.toContain(tid("MOCK-E4"));
    const byId = new Map(r.json!.data.map((t) => [t.id, t]));
    expect(byId.get(tid("MOCK-E1"))?.overdue).toBe(true);
    expect(byId.get(tid("MOCK-E2"))?.depends_on_open).toBe(1);
    expect(byId.get(tid("MOCK-E3"))?.subtask_count).toBe(1);
    expect((await call("/work/tasks?due_from=2026-10-10&due_to=2026-10-01", { claims: EMP })).status).toBe(400);
  });

  it("REV has no execution:read → 403; EMP cannot read a peer task", async () => {
    expect((await call("/work/tasks", { claims: REV })).status).toBe(403);
    const all = await call<Task[]>("/work/tasks?limit=100", { claims: MGR });
    const peer = all.json!.data.find((t) => t.assignee_id && t.assignee_id !== empId("NV-0046"));
    expect(peer).toBeDefined();
    expect((await call(`/work/tasks/${peer!.id}`, { claims: EMP })).status).toBe(404);
  });

  it("PATCH: missing version 422, stale 409, bad transition 409, FR-TASK-02 422, blocked needs reason", async () => {
    const path = `/work/tasks/${tid("MOCK-E2")}`;
    expect((await call(path, { method: "PATCH", claims: EMP, body: { status: "in_progress" } })).status).toBe(422);
    expect((await call(path, { method: "PATCH", claims: EMP, body: { status: "in_progress", version: 99 } })).status).toBe(409);
    const done = await call(path, { method: "PATCH", claims: EMP, body: { status: "done", version: 1 } });
    expect(done.status).toBe(422);
    expect(done.json!.error!.details).toMatchObject({ rule: "FR-TASK-02" });
    expect((await call(path, { method: "PATCH", claims: EMP, body: { status: "blocked", version: 1 } })).status).toBe(422);
    const back = await call(`/work/tasks/${tid("MOCK-E4")}`, { method: "PATCH", claims: EMP, body: { status: "done", version: 1 } });
    expect(back.status).toBe(409);
    expect(back.json!.error!.details).toMatchObject({ from_status: "backlog", to_status: "done" });
    const ok = await call<Task>(path, { method: "PATCH", claims: EMP, body: { status: "in_progress", version: 1 } });
    expect(ok.json!.data).toMatchObject({ status: "in_progress", version: 2 });
  });

  it("dependencies: cycle 422, duplicate 409", async () => {
    const e1 = `/work/tasks/${tid("MOCK-E1")}/dependencies`;
    const cyc = await call(e1, { method: "POST", claims: EMP, headers: IDEM, body: { depends_on_task_id: tid("MOCK-E2") } });
    expect(cyc.status).toBe(422);
    const dup = await call(`/work/tasks/${tid("MOCK-E2")}/dependencies`, { method: "POST", claims: EMP, headers: IDEM, body: { depends_on_task_id: tid("MOCK-E1") } });
    expect(dup.status).toBe(409);
  });

  it("reassign request: non-EMP 422; EMP → MGR approves → task reassigned", async () => {
    const path = `/work/tasks/${tid("MOCK-E3")}/reassign-requests`;
    const to = empId("NV-0049");
    expect((await call(path, { method: "POST", claims: MGR, headers: IDEM, body: { to_assignee_id: to, reason: "x" } })).status).toBe(422);
    const req = await call<{ id: string }>(path, { method: "POST", claims: EMP, headers: IDEM, body: { to_assignee_id: to, reason: "Quá tải" } });
    expect(req.status).toBe(201);
    expect((await call(path, { method: "POST", claims: EMP, headers: IDEM, body: { to_assignee_id: to, reason: "again" } })).status).toBe(409);
    const id = req.json!.data.id;
    const ok = await call(`/workflow/approval-requests/${id}/decide`, { method: "POST", claims: MGR, headers: IDEM, body: { decision: "approve" } });
    expect(ok.status).toBe(200);
    expect((await call<Task>(`/work/tasks/${tid("MOCK-E3")}`, { claims: MGR })).json!.data.assignee_id).toBe(to);
  });
});

describe("mock projects + workload", () => {
  it("late flag + filter; detail has milestones and counts", async () => {
    const all = await call<{ code: string; late: boolean }[]>("/work/projects?limit=100");
    const late = await call<{ code: string }[]>("/work/projects?late=true&limit=100");
    expect(late.json!.data.length).toBeGreaterThan(0);
    expect(late.json!.data.length).toBeLessThan(all.json!.data.length);
    const erp = await call<{ milestones: { late: boolean }[]; task_counts: { by_status: Record<string, number> } }>(`/work/projects/${mockId("project", "PRJ-ERP")}`);
    expect(erp.status).toBe(200);
    expect(erp.json!.data.milestones.some((m) => m.late)).toBe(true);
    expect(Object.values(erp.json!.data.task_counts.by_status).reduce((a, b) => a + b, 0)).toBeGreaterThan(0);
  });

  it("workload: 3 people overloaded company-wide, overloaded first; EMP 403; bad week 400", async () => {
    const w = await call<{ rows: { overloaded: boolean }[]; summary: { overloaded_count: number }; threshold_pct: number }>("/work/workload");
    expect(w.status).toBe(200);
    expect(w.json!.data.summary.overloaded_count).toBe(3);
    expect(w.json!.data.rows.slice(0, 3).every((r) => r.overloaded)).toBe(true);
    expect(w.json!.data.threshold_pct).toBe(110);
    expect((await call("/work/workload", { claims: EMP })).status).toBe(403);
    expect((await call("/work/workload?week=2026-W99")).status).toBe(400);
  });
});

describe("mock approvals inbox", () => {
  it("MGR sees the reassign request with pending_count; EMP 403", async () => {
    const r = await call<{ id: string; target_kind: string }[]>("/workflow/approval-requests?status=PENDING", { claims: MGR });
    expect(r.json!.data.map((a) => a.target_kind)).toContain("task_reassign");
    expect(Number(r.json!.meta?.pending_count)).toBeGreaterThan(0);
    expect((await call("/workflow/approval-requests", { claims: EMP })).status).toBe(403);
  });

  it("reject needs a reason; decided twice → 409; stale task version keeps it PENDING", async () => {
    const path = `/workflow/approval-requests/${mockId("approval", "MOCK-RA-1")}/decide`;
    expect((await call(path, { method: "POST", claims: MGR, headers: IDEM, body: { decision: "reject" } })).status).toBe(422);
    await call(`/work/tasks/${tid("MOCK-E5")}`, { method: "PATCH", claims: EMP, body: { title: "đổi", version: 1 } });
    expect((await call(path, { method: "POST", claims: MGR, headers: IDEM, body: { decision: "approve" } })).status).toBe(409);
    expect((await call<{ status: string }>(path.replace("/decide", ""), { claims: MGR })).json!.data.status).toBe("PENDING");
    expect((await call(path, { method: "POST", claims: MGR, headers: IDEM, body: { decision: "reject", reason: "Không phù hợp" } })).status).toBe(200);
    expect((await call(path, { method: "POST", claims: MGR, headers: IDEM, body: { decision: "approve" } })).status).toBe(409);
  });

  it("can_decide (R-DEC-45): CEO not in a MGR step; DIR other pillar not on ai_action; inbox ↔ detail ↔ decide agree", async () => {
    const ra = mockId("approval", "MOCK-RA-1");
    const inbox = async (c: ReturnType<typeof user>) => (await call<{ id: string }[]>("/workflow/approval-requests?limit=100", { claims: c })).json!.data.map((a) => a.id);
    expect(await inbox(CEO)).not.toContain(ra); // SVC has a MGR → CEO/DIR not approvers
    expect((await call(`/workflow/approval-requests/${ra}`, { claims: CEO })).status).toBe(404);
    const ceo = await call(`/workflow/approval-requests/${ra}/decide`, { method: "POST", claims: CEO, headers: IDEM, body: { decision: "approve" } });
    expect([ceo.status, ceo.json!.error?.code]).toEqual([403, "FORBIDDEN_ROLE"]);
    const SALES = user("sales@abc.demo");
    const ai = mockId("approval", "MOCK-AI-1");
    expect(await inbox(SALES)).not.toContain(ai);
    expect((await call(`/workflow/approval-requests/${ai}`, { claims: SALES })).status).toBe(404);
    const s = await call(`/workflow/approval-requests/${ai}/decide`, { method: "POST", claims: SALES, headers: IDEM, body: { decision: "approve" } });
    expect([s.status, s.json!.error?.code]).toEqual([403, "FORBIDDEN_SCOPE"]);
    expect(await inbox(CFO)).toContain(ai);
  });

  it("DIR fallback: department without MGR → DIR (any pillar) sees and decides", async () => {
    const t = await call<Task>("/work/tasks", { method: "POST", claims: CEO, headers: IDEM, body: { title: "Không có quản lý", department_id: mockId("department", "BOD"), assignee_id: empId("NV-0046") } });
    expect(t.status).toBe(201);
    const id = t.json!.data.id;
    const empSelf = { ...EMP, department_id: mockId("department", "BOD") };
    const r = await call<{ id: string }>(`/work/tasks/${id}/reassign-requests`, { method: "POST", claims: empSelf, headers: IDEM, body: { to_assignee_id: empId("NV-0041"), reason: "quá tải" } });
    expect(r.status).toBe(201);
    const rid = r.json!.data.id;
    const SALES = user("sales@abc.demo");
    expect((await call<{ id: string }[]>("/workflow/approval-requests?limit=100", { claims: SALES })).json!.data.map((a) => a.id)).toContain(rid);
    expect((await call<{ id: string }[]>("/workflow/approval-requests?limit=100", { claims: CEO })).json!.data.map((a) => a.id)).not.toContain(rid);
    expect((await call(`/workflow/approval-requests/${rid}/decide`, { method: "POST", claims: SALES, headers: IDEM, body: { decision: "approve" } })).status).toBe(200);
  });

  it("reassign to_assignee_id same / unknown → 422 field=to_assignee_id", async () => {
    const path = `/work/tasks/${tid("MOCK-E3")}/reassign-requests`;
    const same = await call(path, { method: "POST", claims: EMP, headers: IDEM, body: { to_assignee_id: empId("NV-0046"), reason: "x" } });
    expect([same.status, same.json!.error?.details]).toEqual([422, { field: "to_assignee_id", reason: "same_assignee" }]);
    const bad = await call(path, { method: "POST", claims: EMP, headers: IDEM, body: { to_assignee_id: "nope", reason: "x" } });
    expect(bad.json!.error?.details).toEqual({ field: "to_assignee_id", reason: "not_found" });
  });

  it("DIR finance sees ai_action requests (pillar F); missing Idempotency-Key → 400", async () => {
    const r = await call<{ id: string; target_kind: string; overdue: boolean }[]>("/workflow/approval-requests", { claims: CFO });
    expect(r.json!.data.filter((a) => a.target_kind === "ai_action")).toHaveLength(2);
    expect(r.json!.data.some((a) => a.overdue)).toBe(true);
    expect((await call(`/workflow/approval-requests/${r.json!.data[0]!.id}/decide`, { method: "POST", claims: CFO, body: { decision: "approve" } })).status).toBe(400);
  });
});
