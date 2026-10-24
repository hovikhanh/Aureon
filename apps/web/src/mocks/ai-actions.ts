/**
 * Mock EP-AI-07..11 AI actions (10 §7.2.5, R-DEC-78): list (own `on_behalf_of`, `ai:admin` → whole
 * tenant), detail, confirm (only the served user, needs the ACT `<domain>:write`, allowed under kill
 * switch), reject (reason), undo 24h (410 / 409). `proposeFromChat` = the chat "tạo task" scenario.
 */
import { MockHttpError, ok } from "./http";
import { recordAudit } from "./audit";
import type { MockClaims } from "./fixtures";
import type { MockRequest, Route } from "./router";
import { toolByName } from "./ai-admin-catalog";
import { aiStore, newAiId, nowIso, type MAction } from "./ai-admin-store";
import { body, effectiveLevel, idem, invalid, killApplies } from "./ai-admin-rules";
import { task, workStore } from "./work-store";

const UNDO_MS = 24 * 3_600_000;
const out = (a: MAction) => ({ ...a, approval_request_id: null, can_undo: a.status === "executed" && !!a.undo_deadline && a.undo_deadline > nowIso() });
const sees = (c: MockClaims, a: MAction) => a.on_behalf_of === c.sub || c.permissions.includes("ai:admin");

function list(req: MockRequest): Response {
  const q = req.query;
  const [status, level, agent] = ["status", "autonomy_level", "agent_profile_code"].map((k) => q.get(k));
  const rows = aiStore().actions.filter((a) => sees(req.claims, a) && (!status || a.status === status) && (!level || a.autonomy_level === level) && (!agent || a.agent_profile_code === agent))
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
  return ok(rows.map(out));
}
function find(req: MockRequest, own = false): MAction {
  const a = aiStore().actions.find((x) => x.id === req.params.id);
  if (!a || !sees(req.claims, a)) throw new MockHttpError(404, "NOT_FOUND", "action not found");
  if (own && a.on_behalf_of !== req.claims.sub) throw new MockHttpError(403, "FORBIDDEN_SCOPE", "only the served user may act on this card");
  return a;
}

function execute(a: MAction, c: MockClaims): void {
  if (a.action_name === "ACT-create_task") {
    const p = a.input_preview;
    const t = task({ id: newAiId("task"), title: String(p.title ?? "Task"), due_date: (p.due_date as string) ?? null, priority: String(p.priority ?? "medium"), owner_id: c.sub, task_source: "ai", source_ref: { kind: "ai_action", id: a.id } });
    workStore().tasks.push(t);
    a.result_refs = [{ type: "record", entity: "task", id: t.id, label: t.title }];
  } else {
    a.result_refs = [{ type: "record", entity: a.action_name.replace("ACT-", ""), id: newAiId("record"), label: a.action_name }];
  }
}

function confirm(req: MockRequest): Response {
  idem(req);
  const a = find(req, true);
  if (a.status !== "proposed") throw new MockHttpError(409, "CONFLICT_STATE", "action is not proposed", { status: a.status });
  const tool = toolByName(a.tool_name);
  const missing = (tool?.permission ?? []).filter((p) => !req.claims.permissions.includes(p));
  if (missing.length) throw new MockHttpError(403, "FORBIDDEN_ROLE", "missing target permission", { missing });
  const edited = body(req).edited_input;
  if (edited && typeof edited === "object") a.input_preview = { ...a.input_preview, ...(edited as Record<string, unknown>) };
  execute(a, req.claims);
  const at = nowIso();
  Object.assign(a, { status: "executed", executed_at: at, undo_deadline: new Date(Date.now() + UNDO_MS).toISOString() });
  recordAudit(req.claims, "ai.action_confirm", "ai_actions", a.id);
  return ok(out(a));
}

function reject(req: MockRequest): Response {
  idem(req);
  const a = find(req, true);
  const reason = body(req).reason;
  if (typeof reason !== "string" || !reason.trim()) throw invalid("reason");
  if (a.status !== "proposed") throw new MockHttpError(409, "CONFLICT_STATE", "action is not proposed", { status: a.status });
  a.status = "rejected";
  recordAudit(req.claims, "ai.action_reject", "ai_actions", a.id, reason);
  return ok(out(a));
}

function undo(req: MockRequest): Response {
  idem(req);
  const a = find(req, true);
  if (a.status !== "executed") throw new MockHttpError(409, "CONFLICT_STATE", "action is not executed", { status: a.status });
  if (!a.undo_deadline || a.undo_deadline <= nowIso()) throw new MockHttpError(410, "UNDO_EXPIRED", "undo window expired", { undo_deadline: a.undo_deadline });
  for (const r of a.result_refs) {
    const t = r.entity === "task" ? workStore().tasks.find((x) => x.id === r.id) : undefined;
    if (t) t.deleted = true;
  }
  a.status = "undone";
  recordAudit(req.claims, "ai.action_undo", "ai_actions", a.id);
  return ok(out(a));
}

/** Chat scenario "tạo task …" → L2 card (stored) / L1 suggestion (not stored) / none under kill switch L0. */
export function proposeFromChat(c: MockClaims, message: string, requestId: string): { actions: Record<string, unknown>[]; warnings: string[] } {
  if (!/t[aạ]o (task|vi[eệ]c)|create (a )?task/i.test(message) || !c.permissions.includes("ai:write")) return { actions: [], warnings: [] };
  const tool = toolByName("TOOL-create_task")!;
  if (killApplies("ceo") && aiStore().kill.mode === "L0") return { actions: [], warnings: ["ai.warn.kill_switch"] };
  const title = message.replace(/^.*?(t[aạ]o (task|vi[eệ]c)|create (a )?task)\s*(cho|for)?\s*/i, "").trim() || "Theo dõi khách hàng chậm thanh toán";
  const preview = { title: title.slice(0, 120), due_date: new Date(Date.now() + 3 * 86_400_000).toISOString().slice(0, 10), priority: "high" };
  const level = effectiveLevel(tool, c.role, "ceo");
  if (level === "L1") return { actions: [{ action_name: tool.action_name, tool_name: tool.name, autonomy_level: "L1", input_preview: preview }], warnings: [] };
  if (level === "L0") return { actions: [], warnings: ["ai.warn.kill_switch"] };
  const a: MAction = { id: newAiId("ai_action"), action_name: tool.action_name!, tool_name: tool.name, autonomy_level: "L2", status: "proposed", input_preview: preview, result_refs: [],
    on_behalf_of: c.sub, executed_at: null, undo_deadline: null, agent_profile_code: "ceo", request_id: requestId, created_at: nowIso() };
  aiStore().actions.push(a);
  return { actions: [out(a)], warnings: [] };
}

export const AI_ACTION_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/ai/actions", permission: "ai:query", handler: list },
  { method: "GET", pattern: "/ai/actions/:id", permission: "ai:query", handler: (req) => ok(out(find(req))) },
  { method: "POST", pattern: "/ai/actions/:id/confirm", permission: "ai:write", handler: confirm },
  { method: "POST", pattern: "/ai/actions/:id/reject", permission: "ai:write", handler: reject },
  { method: "POST", pattern: "/ai/actions/:id/undo", permission: "ai:write", handler: undo },
];
