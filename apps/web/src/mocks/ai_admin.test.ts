/** TC-M16-16/19/20/21 (mock part) — mock M1.6 AI Control Center mirrors 10 §7.2.5 (403/409/410/422, ceiling L2, kill switch). */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";
import { proposeFromChat } from "./ai-actions";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
const ADM = user("admin@abc.demo");
const DIR = user("sales@abc.demo");
const MGR = user("manager@abc.demo");
const IDEM = { "idempotency-key": "k-1" };
type C = ReturnType<typeof user>;
type Json = { data: any; meta?: any; error?: { code: string; details: Record<string, any> } }; // eslint-disable-line @typescript-eslint/no-explicit-any -- test JSON

async function call(path: string, claims: C, method = "GET", body?: unknown, headers: Record<string, string> = method === "GET" ? {} : IDEM) {
  const [p, q = ""] = path.split("?");
  const res = await handleMock({ method, path: p!, query: new URLSearchParams(q), headers: new Headers(headers), body, claims });
  const json = res.status === 204 ? null : ((await res.json()) as Json);
  return { status: res.status, json: json as Json };
}

beforeEach(() => resetMockStore());

describe("EP-AI-12/13 kill switch", () => {
  it("everyone reads it with autonomy_ceiling L2; only ai:admin writes; reason + agents validated", async () => {
    const r = await call("/ai/kill-switch", user("employee@abc.demo"));
    expect(r.json.data).toMatchObject({ enabled: false, autonomy_ceiling: "L2" });
    expect((await call("/ai/kill-switch", DIR, "PUT", { enabled: true, reason: "x" })).status).toBe(403);
    expect((await call("/ai/kill-switch", ADM, "PUT", { enabled: true, reason: "x" }, {})).status).toBe(400);
    expect((await call("/ai/kill-switch", ADM, "PUT", { enabled: true, reason: " " })).status).toBe(422);
    const bad = await call("/ai/kill-switch", ADM, "PUT", { enabled: true, reason: "sự cố", agents: ["nope"] });
    expect(bad.json.error).toMatchObject({ code: "VALIDATION_ERROR", details: { field: "agents" } });
    const on = await call("/ai/kill-switch", ADM, "PUT", { enabled: true, mode: "L0", agents: ["task"], reason: "sự cố" });
    expect(on.json.data).toMatchObject({ enabled: true, mode: "L0", agents: ["task"], reason: "sự cố", changed_by: ADM.sub });
    const agents = (await call("/ai/agents", CEO)).json.data as { code: string; kill_switched: boolean; effective_max_level: string }[];
    expect(agents.find((a) => a.code === "task")).toMatchObject({ kill_switched: true, effective_max_level: "L0" });
    expect(agents.find((a) => a.code === "ceo")!.kill_switched).toBe(false);
  });
});

describe("EP-AI-14 tools", () => {
  it("53 tools with 13 metadata, agents[], filters; ceiling caps effective_level", async () => {
    const all = (await call("/ai/tools", CEO)).json.data as Record<string, any>[]; // eslint-disable-line @typescript-eslint/no-explicit-any -- test JSON
    expect(all).toHaveLength(53);
    for (const k of ["tool_id", "description", "domain", "endpoint_ref", "kind", "risk_level", "autonomy_default", "permission", "data_scope", "data_classification", "reversible", "cost_estimate", "input_schema", "output_schema", "approval_required", "audit_required", "owner"]) {
      expect(all[0]).toHaveProperty(k);
    }
    expect(all.find((t) => t.name === "TOOL-create_task")).toMatchObject({ autonomy_default: "L3", effective_level: "L2", agents: ["ceo", "task", "meeting"] });
    expect(all.filter((t) => t.kind === "APPROVAL").every((t) => !t.available)).toBe(true);
    expect((await call("/ai/tools?kind=EXECUTION", CEO)).json.data).toHaveLength(1);
    expect(((await call("/ai/tools?available_only=true", ADM)).json.data as { kind: string }[]).every((t) => t.kind === "READ")).toBe(true);
  });
});

describe("EP-AI-16/17 agents", () => {
  it("6 agents; month_spend only for ai:admin; patch rules 409/422", async () => {
    const list = (await call("/ai/agents", DIR)).json.data as Record<string, unknown>[];
    expect(list).toHaveLength(6);
    expect(list[0]).not.toHaveProperty("month_spend_usd");
    expect((await call("/ai/agents", ADM)).json.data[0]).toHaveProperty("month_spend_usd");
    expect((await call("/ai/agents/task", DIR, "PATCH", { reason: "x", version: 1 })).status).toBe(403);
    expect((await call("/ai/agents/nope", ADM, "PATCH", { reason: "x", version: 1 })).status).toBe(404);
    expect((await call("/ai/agents/task", ADM, "PATCH", { max_autonomy_level: "L3", reason: "x", version: 1 })).json.error!.details.reason).toBe("above_ceiling");
    expect((await call("/ai/agents/task", ADM, "PATCH", { allowed_tools: ["TOOL-approve_request"], reason: "x", version: 1 })).json.error!.details.reason).toBe("invalid_tool");
    expect((await call("/ai/agents/task", ADM, "PATCH", { is_enabled: false, version: 1 })).status).toBe(422);
    const ok = await call("/ai/agents/task", ADM, "PATCH", { is_enabled: false, monthly_budget_usd: 5, reason: "tạm dừng", version: 1 });
    expect(ok.json.data).toMatchObject({ is_enabled: false, monthly_budget_usd: "5.00", version: 2 });
    expect((await call("/ai/agents/task", ADM, "PATCH", { is_enabled: true, reason: "x", version: 1 })).json.error!.code).toBe("CONFLICT_STATE");
  });
});

describe("EP-AI-18..21 autonomy policies", () => {
  it("defaults after ceiling; 422 reasons; 409 duplicate / version; soft delete", async () => {
    const r = await call("/ai/autonomy-policies", CEO);
    expect(r.json.data).toHaveLength(2);
    expect(r.json.meta.defaults.find((d: { tool_name: string }) => d.tool_name === "TOOL-create_task")).toMatchObject({ default_level: "L2", max_level: "L2" });
    expect((await call("/ai/autonomy-policies", DIR)).status).toBe(403);
    const reason = async (b: Record<string, unknown>) => (await call("/ai/autonomy-policies", ADM, "POST", { reason: "r", ...b })).json.error?.details.reason;
    expect(await reason({ tool_name: "TOOL-get_metric", level: "L0", max_level: "L0" })).toBe("not_configurable");
    expect(await reason({ tool_name: "TOOL-upsert_deal", level: "L2", max_level: "L3" })).toBe("above_tool_max");
    expect(await reason({ tool_name: "TOOL-create_task", level: "L3", max_level: "L3" })).toBe("above_ceiling");
    const created = await call("/ai/autonomy-policies", ADM, "POST", { tool_name: "TOOL-create_task", role_code: "EMP", level: "L1", max_level: "L2", reason: "EMP chỉ gợi ý" });
    expect(created.status).toBe(201);
    expect(created.json.data.action_name).toBe("ACT-create_task");
    expect((await call("/ai/autonomy-policies", ADM, "POST", { tool_name: "TOOL-create_task", role_code: "EMP", level: "L2", max_level: "L2", reason: "x" })).status).toBe(409);
    expect((await call("/ai/autonomy-policies", ADM, "POST", { tool_name: "TOOL-create_invoice", max_amount: 5, level: "L1", max_level: "L2", reason: "x" })).status).toBe(422);
    const id = created.json.data.id;
    expect((await call(`/ai/autonomy-policies/${id}`, ADM, "PATCH", { level: "L2", reason: "x", version: 9 })).status).toBe(409);
    expect((await call(`/ai/autonomy-policies/${id}`, ADM, "PATCH", { level: "L2", reason: "x", version: 1 })).json.data.version).toBe(2);
    expect((await call(`/ai/autonomy-policies/${id}`, ADM, "DELETE")).status).toBe(422);
    expect((await call(`/ai/autonomy-policies/${id}?reason=bo`, ADM, "DELETE")).status).toBe(204);
    expect((await call("/ai/autonomy-policies", ADM)).json.data).toHaveLength(2);
  });
});

describe("EP-AI-07..11 actions", () => {
  it("own scope vs ai:admin tenant; only on_behalf_of confirms; undo; ADM lacks ai:write", async () => {
    const own = (await call("/ai/actions?status=proposed", MGR)).json.data as { on_behalf_of: string }[];
    expect(own.every((a) => a.on_behalf_of === MGR.sub)).toBe(true);
    expect(((await call("/ai/actions?status=proposed", ADM)).json.data as unknown[]).length).toBe(3);
    const ceoCard = ((await call("/ai/actions?status=proposed", CEO)).json.data as { id: string; action_name: string }[]).find((a) => a.action_name === "ACT-create_task")!;
    expect((await call(`/ai/actions/${ceoCard.id}/confirm`, ADM, "POST", {})).status).toBe(403);
    expect((await call(`/ai/actions/${ceoCard.id}/confirm`, MGR, "POST", {})).status).toBe(404);
    expect((await call(`/ai/actions/${ceoCard.id}/reject`, CEO, "POST", { reason: "" })).status).toBe(422);
    // kill switch WRITE_OFF does not block a human confirming an L2 card (R-DEC-78)
    await call("/ai/kill-switch", ADM, "PUT", { enabled: true, reason: "test" });
    const done = await call(`/ai/actions/${ceoCard.id}/confirm`, CEO, "POST", { edited_input: { title: "Gọi 3 khách" } });
    expect(done.json.data).toMatchObject({ status: "executed", can_undo: true });
    expect(done.json.data.input_preview.title).toBe("Gọi 3 khách");
    expect((await call(`/ai/actions/${ceoCard.id}/confirm`, CEO, "POST", {})).status).toBe(409);
    expect((await call(`/ai/actions/${ceoCard.id}/undo`, CEO, "POST", {})).json.data.status).toBe("undone");
    expect((await call(`/ai/actions/${ceoCard.id}/undo`, CEO, "POST", {})).status).toBe(409);
  });

  it("chat proposes L2 card, L1 under role policy, nothing under kill switch L0", async () => {
    expect(proposeFromChat(CEO, "Tạo task cho chị Lan gọi khách", "r1").actions[0]).toMatchObject({ autonomy_level: "L2", status: "proposed" });
    await call("/ai/autonomy-policies", ADM, "POST", { tool_name: "TOOL-create_task", role_code: "MGR", level: "L1", max_level: "L2", reason: "x" });
    const l1 = proposeFromChat(MGR, "tạo task kiểm kho", "r2").actions[0]!;
    expect(l1).toMatchObject({ autonomy_level: "L1" });
    expect(l1).not.toHaveProperty("id");
    await call("/ai/kill-switch", ADM, "PUT", { enabled: true, mode: "L0", reason: "test" });
    expect(proposeFromChat(CEO, "tạo task X", "r3")).toEqual({ actions: [], warnings: ["ai.warn.kill_switch"] });
    expect(proposeFromChat(CEO, "doanh thu tháng này?", "r4").actions).toEqual([]);
  });
});

describe("EP-AI-15/22/23 usage + logs", () => {
  it("ai:admin only; period / range validation; group_by agent; request_id filter", async () => {
    expect((await call("/ai/usage", DIR)).status).toBe(403);
    expect((await call("/ai/usage?period=2026-13", ADM)).status).toBe(400);
    const u = (await call("/ai/usage?group_by=agent", ADM)).json.data;
    expect(u).toMatchObject({ budget_usd: 50 });
    expect(u.rows.map((r: { key: string }) => r.key).sort()).toEqual(expect.arrayContaining(["ceo"]));
    expect((await call("/ai/tool-calls?from=2026-10-10T00:00:00Z&to=2026-10-01T00:00:00Z", ADM)).status).toBe(400);
    const tc = (await call("/ai/tool-calls", ADM)).json;
    expect(tc.meta.pagination.limit).toBe(20);
    const req = tc.data[0].request_id;
    const mc = (await call(`/ai/model-calls?request_id=${req}`, ADM)).json.data as { request_id: string; prompt_sha256: string }[];
    expect(mc.every((m) => m.request_id === req)).toBe(true);
    expect((await call("/ai/model-calls", MGR)).status).toBe(403);
  });
});
