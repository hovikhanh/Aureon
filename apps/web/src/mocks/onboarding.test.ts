/** TC-M16-15 (mock part) — EP-ADM-13/14 state machine + EP-ORG-02/04 + EP-ADM-06 as the SCR-66 wizard uses them (10 §7.2.5). */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
const ADM = user("admin@abc.demo");
const MGR = user("manager@abc.demo");
type C = ReturnType<typeof user>;
type Json = { data: any; error?: { code: string; details: Record<string, any> } }; // eslint-disable-line @typescript-eslint/no-explicit-any -- test JSON

let n = 0;
async function call(path: string, claims: C, method = "GET", body?: unknown) {
  const headers = new Headers(method === "GET" ? {} : { "idempotency-key": `k-${++n}` });
  const res = await handleMock({ method, path, query: new URLSearchParams(), headers, body, claims });
  return { status: res.status, json: (await res.json()) as Json };
}
const patch = (claims: C, body: Record<string, unknown>) => call("/platform/onboarding", claims, "PATCH", body);

beforeEach(() => resetMockStore());

describe("EP-ADM-13/14 onboarding", () => {
  it("not_started with derived progress; MGR may not read, only platform:admin writes", async () => {
    const r = await call("/platform/onboarding", ADM);
    expect(r.json.data).toMatchObject({ status: "not_started", version: 0, progress: { organization_ready: true } });
    expect(r.json.data.progress.departments).toBeGreaterThan(0);
    expect((await call("/platform/onboarding", MGR)).status).toBe(403);
    expect((await patch(MGR, { action: "start" })).status).toBe(403);
  });

  it("start idempotent → steps with version (409 stale / 422 missing) → skip only goals_import → finish missing_steps", async () => {
    const s1 = (await patch(ADM, { action: "start" })).json.data;
    expect(s1).toMatchObject({ status: "in_progress", steps: { company: { status: "in_progress" } } });
    expect((await patch(ADM, { action: "start" })).json.data.version).toBe(s1.version);
    expect((await patch(ADM, { action: "complete_step", step: "company" })).status).toBe(422);
    expect((await patch(ADM, { action: "complete_step", step: "company", version: 99 })).status).toBe(409);
    const s2 = (await patch(ADM, { action: "complete_step", step: "company", refs: { organization_id: "org-1" }, version: s1.version })).json.data;
    expect(s2.steps.company).toMatchObject({ status: "done", refs: { organization_id: "org-1" } });
    expect(s2.steps.org_import.status).toBe("in_progress");
    expect((await patch(ADM, { action: "complete_step", step: "users", refs: { email: "a@b.c" }, version: s2.version })).status).toBe(422); // refs: codes only
    const skipUsers = await patch(ADM, { action: "skip_step", step: "users", version: s2.version });
    expect(skipUsers.json.error).toMatchObject({ code: "BUSINESS_RULE_VIOLATION", details: { reason: "step_required" } });
    const s3 = (await patch(ADM, { action: "skip_step", step: "goals_import", version: s2.version })).json.data;
    const fin = await patch(ADM, { action: "finish", version: s3.version });
    expect(fin.status).toBe(422);
    expect(fin.json.error!.details.missing_steps).toEqual(["org_import", "users"]);
  });

  it("all required steps done → completed; reset needs a reason", async () => {
    let s = (await patch(CEO, { action: "start" })).json.data;
    for (const step of ["company", "org_import", "review", "users"]) s = (await patch(CEO, { action: "complete_step", step, version: s.version })).json.data;
    s = (await patch(CEO, { action: "finish", version: s.version })).json.data;
    expect(s).toMatchObject({ status: "completed", steps: { finish: { status: "done" } } });
    expect(s.completed_at).toBeTruthy();
    expect((await patch(CEO, { action: "reset", version: s.version })).status).toBe(422);
    expect((await patch(CEO, { action: "reset", reason: "demo", version: s.version })).json.data.status).toBe("not_started");
  });
});

describe("wizard EPs: EP-ORG-02/04, EP-ADM-06", () => {
  it("org create 409 on duplicate code, PATCH needs version; user per employee once; ADM cannot grant CEO", async () => {
    const orgs = (await call("/org/organizations", ADM)).json.data as { id: string; code: string; version: number }[];
    expect((await call("/org/organizations", ADM, "POST", { code: orgs[0]!.code, name: "X" })).status).toBe(409);
    expect((await call(`/org/organizations/${orgs[0]!.id}`, ADM, "PATCH", { name: "ABC" })).status).toBe(422);
    expect((await call(`/org/organizations/${orgs[0]!.id}`, ADM, "PATCH", { name: "ABC mới", tax_code: "0312345678", version: orgs[0]!.version })).json.data).toMatchObject({ name: "ABC mới", version: orgs[0]!.version + 1 });
    const body = { email: "nv9@abc.demo", full_name: "NV 9", role_code: "EMP", employee_id: "emp-x", initial_password: "Abcdefgh1234" };
    expect((await call("/platform/users", ADM, "POST", body)).status).toBe(201);
    expect((await call("/platform/users", ADM, "POST", { ...body, email: "nv10@abc.demo" })).json.error).toMatchObject({ code: "DUPLICATE_RESOURCE", details: { field: "employee_id" } });
    expect((await call("/platform/users", ADM, "POST", { ...body, email: "c@abc.demo", employee_id: null, role_code: "CEO" })).status).toBe(403);
    const prog = (await call("/platform/onboarding", ADM)).json.data.progress;
    expect(prog.users_by_role.EMP).toBeGreaterThan(0);
  });
});
