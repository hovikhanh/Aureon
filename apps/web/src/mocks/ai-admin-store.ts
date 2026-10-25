/**
 * Mock state of the M1.6 AI Control Center: kill switch (EP-AI-12/13), agents (EP-AI-16/17),
 * autonomy policies (EP-AI-18..21), AI actions (EP-AI-07..11), tool/model call logs (EP-AI-22/23).
 * On globalThis like the other mock stores; `resetAiAdminStore()` is called by `resetMockStore()`.
 */
import { mockId } from "./fixtures";
import { AGENTS, TOOLS, type Level } from "./ai-admin-catalog";

export interface MKill { enabled: boolean; mode: "WRITE_OFF" | "L0"; agents: string[]; changed_by: string | null; changed_at: string | null; reason: string | null }
export interface MAgent { code: string; allowed_tools: string[]; max_autonomy_level: Level; monthly_budget_usd: string | null; is_enabled: boolean; prompt_version: string; version: number; updated_at: string }
export interface MPolicy { id: string; tool_name: string; action_name: string; agent_profile_code: string | null; role_code: string | null; max_amount: number | null; currency: string | null;
  level: Level; max_level: Level; is_active: boolean; reason: string; version: number; updated_by: string | null; updated_at: string; deleted: boolean }
export interface MAction { id: string; action_name: string; tool_name: string; autonomy_level: Level; status: "proposed" | "confirmed" | "executed" | "rejected" | "undone" | "failed";
  input_preview: Record<string, unknown>; result_refs: Record<string, unknown>[]; on_behalf_of: string; executed_at: string | null; undo_deadline: string | null;
  agent_profile_code: string; request_id: string; created_at: string }
export interface MToolCall { id: string; created_at: string; request_id: string; user_id: string; agent_profile_code: string; tool_name: string; tool_kind: string; status: string;
  error_code: string | null; latency_ms: number; autonomy_level: Level | null; ai_action_id: string | null; message_id: string | null; arguments: Record<string, unknown>; result_refs: Record<string, unknown>[] }
export interface MModelCall { id: string; created_at: string; request_id: string; caller_module: string; task_kind: string; provider: string; model: string; fallback_from: string | null;
  agent_profile_code: string | null; user_id: string; tokens_in: number; tokens_out: number; cost_usd: number; latency_ms: number; status: string; error_code: string | null; prompt_sha256: string }
export interface AiAdminStore { kill: MKill; agents: MAgent[]; policies: MPolicy[]; actions: MAction[]; toolCalls: MToolCall[]; modelCalls: MModelCall[]; seq: number }

export const BUDGET_USD = 50; // AI_MONTHLY_BUDGET_USD (.env.example)
export const uid = (email: string) => mockId("user", email);
export const CEO = uid("ceo@abc.demo");
export const MGR = uid("manager@abc.demo");
const STAMP = "2026-10-01T02:00:00Z";
const HOUR = 3_600_000;
export const nowIso = () => new Date().toISOString();
const ago = (h: number) => new Date(Date.now() - h * HOUR).toISOString();

function action(key: string, p: Partial<MAction> & Pick<MAction, "action_name" | "tool_name" | "input_preview" | "on_behalf_of">, hoursAgo: number): MAction {
  return { id: mockId("ai_action", key), autonomy_level: "L2", status: "proposed", result_refs: [], executed_at: null, undo_deadline: null,
    agent_profile_code: "ceo", request_id: mockId("req", key), created_at: ago(hoursAgo), ...p };
}

function seedLogs(actions: MAction[]): Pick<AiAdminStore, "toolCalls" | "modelCalls"> {
  const users = ["ceo@abc.demo", "manager@abc.demo", "sales@abc.demo", "employee@abc.demo"].map(uid);
  const reads = ["TOOL-get_kpi_status", "TOOL-get_metric", "TOOL-list_tasks", "TOOL-get_finance_dashboard", "TOOL-get_overdue_tasks", "TOOL-list_alerts"];
  const agents = ["ceo", "task", "performance", "reporting", "meeting", "data_capture"];
  const toolCalls: MToolCall[] = [];
  const modelCalls: MModelCall[] = [];
  for (let i = 0; i < 36; i++) {
    const req = mockId("req", `log-${i}`);
    const user = users[i % users.length]!;
    const agent = agents[i % agents.length]!;
    const status = i % 11 === 5 ? "error" : i % 13 === 7 ? "forbidden" : "ok";
    const at = ago(2 + i * 4.5);
    const fallback = i % 9 === 4;
    modelCalls.push({ id: mockId("model_call", String(i)), created_at: at, request_id: req, caller_module: "ai_core", task_kind: i % 6 === 3 ? "report" : "chat",
      provider: fallback ? "openrouter" : "omniroute", model: fallback ? "openai/gpt-4o-mini" : "cc/claude-opus-5-5", fallback_from: fallback ? "omniroute" : null,
      agent_profile_code: agent, user_id: user, tokens_in: 1800 + i * 37, tokens_out: 320 + i * 11, cost_usd: Number((0.0125 + i * 0.0031).toFixed(4)),
      latency_ms: 900 + i * 53, status: status === "forbidden" ? "ok" : status, error_code: status === "error" ? "AI_PROVIDER_TIMEOUT" : null,
      prompt_sha256: `${(i * 2654435761).toString(16).padStart(8, "0")}${"ab12cd34".repeat(7)}` });
    const tool = reads[i % reads.length]!;
    toolCalls.push({ id: mockId("tool_call", String(i)), created_at: at, request_id: req, user_id: user, agent_profile_code: agent, tool_name: tool, tool_kind: "READ",
      status, error_code: status === "forbidden" ? "FORBIDDEN_SCOPE" : status === "error" ? "AI_TOOL_TIMEOUT" : null, latency_ms: 40 + i * 7, autonomy_level: "L0",
      ai_action_id: null, message_id: mockId("message", String(i)), arguments: { period: "2026-10", employee: "EMP-0046" },
      result_refs: status === "ok" ? [{ type: "metric_value", id: "METRIC-EXE-01", label: "METRIC-EXE-01" }] : [] });
  }
  for (const a of actions) {
    toolCalls.push({ id: mockId("tool_call", a.id), created_at: a.created_at, request_id: a.request_id, user_id: a.on_behalf_of, agent_profile_code: a.agent_profile_code,
      tool_name: a.tool_name, tool_kind: TOOLS.find((x) => x.name === a.tool_name)?.kind ?? "WRITE", status: "ok", error_code: null, latency_ms: 120,
      autonomy_level: a.autonomy_level, ai_action_id: a.id, message_id: null, arguments: a.input_preview, result_refs: [] });
  }
  return { toolCalls, modelCalls };
}

function seed(): AiAdminStore {
  const agents: MAgent[] = AGENTS.map((a) => ({ code: a.code, allowed_tools: a.tools.filter((n) => TOOLS.some((x) => x.name === n && x.kind !== "APPROVAL" && !x.p1_frozen)),
    max_autonomy_level: "L2", monthly_budget_usd: a.code === "ceo" ? "20.00" : null, is_enabled: true, prompt_version: "v3.0", version: 1, updated_at: STAMP }));
  const pol = (key: string, p: Omit<MPolicy, "id" | "version" | "updated_by" | "updated_at" | "deleted" | "is_active" | "currency"> & { currency?: string | null }): MPolicy =>
    ({ id: mockId("autonomy_policy", key), version: 1, updated_by: CEO, updated_at: STAMP, deleted: false, is_active: true, currency: null, ...p });
  const policies = [
    pol("kpi-mgr", { tool_name: "TOOL-record_kpi_measurement", action_name: "ACT-record_kpi_measurement", agent_profile_code: null, role_code: "MGR", max_amount: null, level: "L1", max_level: "L2", reason: "Quản lý tự nhập số đo KPI trong giai đoạn đầu" }),
    pol("invoice-50m", { tool_name: "TOOL-create_invoice", action_name: "ACT-create_invoice", agent_profile_code: null, role_code: null, max_amount: 50_000_000, currency: "VND", level: "L1", max_level: "L2", reason: "Hóa đơn ≤ 50 triệu: AI chỉ gợi ý" }),
  ];
  const actions = [
    action("ceo-task", { action_name: "ACT-create_task", tool_name: "TOOL-create_task", on_behalf_of: CEO,
      input_preview: { title: "Gọi lại 3 khách hàng chậm thanh toán", assignee: "EMP-0004", due_date: "2026-10-27", priority: "high" } }, 3),
    action("mgr-update", { action_name: "ACT-update_task", tool_name: "TOOL-update_task", agent_profile_code: "task", on_behalf_of: MGR,
      input_preview: { task: "T-SEED-03", due_date: "2026-10-30", status: "in_progress" } }, 6),
    action("ceo-invoice", { action_name: "ACT-create_invoice", tool_name: "TOOL-create_invoice", on_behalf_of: CEO,
      input_preview: { client: "CLI-0012", total_amount: 1_250_000, currency: "VND", due_date: "2026-11-15" } }, 9),
    action("ceo-done", { action_name: "ACT-record_decision", tool_name: "TOOL-record_decision", agent_profile_code: "meeting", on_behalf_of: CEO, status: "executed",
      executed_at: ago(20), undo_deadline: new Date(Date.now() + 4 * HOUR).toISOString(), input_preview: { title: "Chốt ngân sách marketing Q4" } }, 20),
  ];
  return { kill: { enabled: false, mode: "WRITE_OFF", agents: [], changed_by: null, changed_at: null, reason: null }, agents, policies, actions, ...seedLogs(actions), seq: 0 };
}

const G = globalThis as typeof globalThis & { __aureonMockAiAdmin?: AiAdminStore | null };
export function aiStore(): AiAdminStore {
  G.__aureonMockAiAdmin ??= seed();
  return G.__aureonMockAiAdmin;
}
export function resetAiAdminStore(): void {
  G.__aureonMockAiAdmin = null;
}
export const newAiId = (kind: string) => mockId(kind, `new-${++aiStore().seq}-${Date.now()}`);
