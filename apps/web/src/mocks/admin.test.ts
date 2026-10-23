/** T-617F — mock BFF for the M1.2 admin screens (EP-ORG / EP-ADM / EP-NTF on API_MODE=mock). */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor, mockId } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";
import { ORG_ID, eId } from "./org";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const ADM = user("admin@abc.demo");
const CEO = user("ceo@abc.demo");
const EMP = user("employee@abc.demo");
const MGR = user("manager@abc.demo");
const IDEM = { "idempotency-key": "k-1" };

async function call<T = unknown>(path: string, opts: { method?: string; claims?: ReturnType<typeof user>; body?: unknown; headers?: Record<string, string> } = {}) {
  const [p, q = ""] = path.split("?");
  const res = await handleMock({ method: opts.method ?? "GET", path: p!, query: new URLSearchParams(q), headers: new Headers(opts.headers), body: opts.body, claims: opts.claims ?? ADM });
  const json = res.status === 204 ? null : ((await res.json()) as { data: T; meta?: Record<string, unknown>; error?: { code: string; details: Record<string, unknown> } });
  return { status: res.status, json };
}

interface Tree { as_of: string; departments: { id: string; code: string; headcount: number; members: { employee_code: string }[] }[] }
const deptOf = (t: Tree, code: string) => t.departments.find((d) => d.members.some((m) => m.employee_code === code))?.code;

beforeEach(() => resetMockStore());

describe("mock org structure", () => {
  it("tree as_of shows the seeded transfer history (T-617)", async () => {
    const past = await call<Tree>("/org/tree?as_of=2023-06-01", { claims: CEO });
    const now = await call<Tree>("/org/tree", { claims: CEO });
    expect(deptOf(past.json!.data, "NV-0049")).toBe("SAL");
    expect(deptOf(now.json!.data, "NV-0049")).toBe("SVC");
    expect((await call("/org/tree?as_of=2023-13-40")).status).toBe(400);
  });

  it("EMP → 403, MGR sees only the own department", async () => {
    expect((await call("/org/tree", { claims: EMP })).status).toBe(403);
    const t = await call<Tree>("/org/tree", { claims: MGR });
    expect(t.json!.data.departments.map((d) => d.code)).toEqual(["SVC"]);
  });

  it("ADM creates a department + assigns an employee; the CEO sees it; archive is blocked", async () => {
    const d = await call<{ id: string }>("/hr/departments", { method: "POST", headers: IDEM, body: { organization_id: ORG_ID, code: "QA", name: "Chất lượng" } });
    expect(d.status).toBe(201);
    const today = new Date().toISOString().slice(0, 10);
    const a = await call("/org/assignments", { method: "POST", headers: IDEM, body: { employee_id: eId("NV-0049"), department_id: d.json!.data.id, valid_from: today } });
    expect(a.status).toBe(201);
    const tree = await call<Tree>("/org/tree", { claims: CEO });
    expect(deptOf(tree.json!.data, "NV-0049")).toBe("QA");
    const blocked = await call(`/hr/departments/${d.json!.data.id}`, { method: "DELETE" });
    expect(blocked.status).toBe(422);
    expect(blocked.json!.error!.details.reason).toBe("has_live_children");
    expect((await call("/hr/departments", { method: "POST", body: { organization_id: ORG_ID, code: "X", name: "X" } })).status).toBe(400);
    expect((await call("/hr/departments", { method: "POST", headers: IDEM, claims: MGR, body: {} })).status).toBe(403);
    const audit = await call<{ action: string }[]>("/platform/audit-logs?action=hr.department_create");
    expect(audit.json!.data).toHaveLength(1);
  });

  it("positions compute filled / vacant", async () => {
    const p = await call<{ vacant: number }>("/org/positions", { method: "POST", headers: IDEM, body: { department_id: mockId("department", "SAL"), code: "SAL-AM", title: "Account Manager", headcount_budget: 3 } });
    expect(p.status).toBe(201);
    expect(p.json!.data.vacant).toBe(3);
  });
});

describe("mock user admin", () => {
  const target = mockId("user", "employee@abc.demo");

  it("locks with a reason, refuses self-lock and AI role", async () => {
    expect((await call(`/platform/users/${target}/deactivate`, { method: "POST", headers: IDEM, body: { reason: "nghỉ phép dài" } })).status).toBe(200);
    expect((await call(`/platform/users/${ADM.sub}/deactivate`, { method: "POST", headers: IDEM, body: { reason: "x" } })).status).toBe(422);
    expect((await call(`/platform/users/${target}`, { method: "PATCH", body: { role_code: "AI" } })).status).toBe(422);
    const list = await call<{ is_active: boolean }[]>("/platform/users?is_active=false");
    expect(list.json!.data).toHaveLength(1);
  });

  it("roles matrix lists the 7 roles", async () => {
    const r = await call<{ code: string; permissions: string[] }[]>("/platform/roles", { claims: CEO });
    expect(r.json!.data.map((x) => x.code).sort()).toEqual(["ADM", "AI", "CEO", "DIR", "EMP", "MGR", "REV"]);
  });
});

describe("mock notifications", () => {
  it("unread_count + read-all, token-only (EMP allowed)", async () => {
    const inbox = await call<{ id: string }[]>("/notifications?unread_only=true&limit=10", { claims: EMP });
    expect(inbox.status).toBe(200);
    expect(inbox.json!.meta!.unread_count).toBe(3);
    // EP-NTF-02/03 require an Idempotency-Key like the real API (missing → 400)
    expect((await call("/notifications/read-all", { method: "POST", claims: EMP, body: {} })).status).toBe(400);
    const one = await call(`/notifications/${inbox.json!.data[0]!.id}/read`, { method: "POST", claims: EMP, headers: IDEM });
    expect(one.status).toBe(200);
    const all = await call<{ updated: number }>("/notifications/read-all", { method: "POST", claims: EMP, headers: IDEM, body: {} });
    expect(all.json!.data.updated).toBe(2);
    const prefs = await call<{ kind: string; email_enabled: boolean }[]>("/notifications/preferences", { method: "PATCH", claims: EMP, body: { items: [{ kind: "alert", email_enabled: true }] } });
    expect(prefs.json!.data.find((p) => p.kind === "alert")?.email_enabled).toBe(true);
  });
});
