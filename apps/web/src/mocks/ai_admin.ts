/**
 * Mock BFF M1.6 AI Control Center (T-644F/T-646F/T-647F, 10 §7.2.5): EP-AI-12/13 kill switch,
 * EP-AI-14 tools, EP-AI-15 usage, EP-AI-16/17 agents, EP-AI-18..21 autonomy policies, EP-AI-22/23
 * logs. Actions EP-AI-07..11 live in `ai-actions.ts`. Same permission/409/422 rules as the spec.
 */
import { ok, MockHttpError } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";
import { AGENT_CODES, AGENTS, CEILING, TOOLS, assignable, rank } from "./ai-admin-catalog";
import { aiStore, nowIso, type MAgent } from "./ai-admin-store";
import { agentEffectiveMax, body, effectiveLevel, idem, invalid, killApplies, reasonOf, rule, expectVersion } from "./ai-admin-rules";
import { AI_POLICY_ROUTES } from "./ai-policies";
import { AI_ACTION_ROUTES } from "./ai-actions";
import { AI_LOG_ROUTES } from "./ai-logs";

const killOut = () => ({ ...aiStore().kill, autonomy_ceiling: CEILING });
function putKill(req: MockRequest): Response {
  idem(req);
  const b = body(req);
  if (typeof b.enabled !== "boolean") throw invalid("enabled");
  const reason = reasonOf(b);
  const mode = b.mode ?? "WRITE_OFF";
  if (mode !== "WRITE_OFF" && mode !== "L0") throw invalid("mode");
  const agents = Array.isArray(b.agents) ? b.agents.map(String) : [];
  const unknown = agents.filter((a) => !AGENT_CODES.has(a));
  if (unknown.length) throw new MockHttpError(422, "VALIDATION_ERROR", "unknown agent", { field: "agents", agents: unknown });
  Object.assign(aiStore().kill, { enabled: b.enabled, mode, agents: b.enabled ? agents : [], changed_by: req.claims.sub, changed_at: nowIso(), reason });
  recordAudit(req.claims, "ai.kill_switch", "kill_switch", "ai.kill_switch", reason);
  return ok(killOut());
}

function tools(req: MockRequest): Response {
  const q = req.query;
  const [kind, domain, agent] = ["kind", "domain", "agent"].map((k) => q.get(k));
  const only = q.get("available_only") === "true";
  const perms = req.claims.permissions;
  const out = TOOLS.map((t) => {
    const agents = aiStore().agents.filter((a) => a.allowed_tools.includes(t.name)).map((a) => a.code);
    const available = t.permission.every((p) => perms.includes(p)) && t.kind !== "APPROVAL" && !t.p1_frozen;
    return { ...t, agents, available, effective_level: effectiveLevel(t, req.claims.role, agents[0] ?? "ceo") };
  }).filter((t) => (!kind || t.kind === kind) && (!domain || t.domain === domain) && (!agent || t.agents.includes(agent)) && (!only || t.available));
  return ok(out);
}

export function agentOut(a: MAgent, admin: boolean) {
  const spec = AGENTS.find((x) => x.code === a.code)!;
  const spend = aiStore().modelCalls.filter((m) => m.agent_profile_code === a.code && m.created_at.slice(0, 7) === nowIso().slice(0, 7)).reduce((s, m) => s + m.cost_usd, 0);
  const { tools: _tools, ...rest } = spec;
  void _tools;
  return { ...rest, agent_ref: `AGT-${a.code.toUpperCase()}`, allowed_tools: a.allowed_tools, max_autonomy_level: a.max_autonomy_level, effective_max_level: agentEffectiveMax(a),
    prompt_version: a.prompt_version, monthly_budget_usd: a.monthly_budget_usd, ...(admin ? { month_spend_usd: Number(spend.toFixed(4)) } : {}),
    is_enabled: a.is_enabled, kill_switched: killApplies(a.code), version: a.version, updated_at: a.updated_at };
}
const isAdmin = (req: MockRequest) => req.claims.permissions.includes("ai:admin");
const findAgent = (code: string) => {
  const a = aiStore().agents.find((x) => x.code === code);
  if (!a) throw new MockHttpError(404, "NOT_FOUND", "agent not found", { code });
  return a;
};

function patchAgent(req: MockRequest): Response {
  const a = findAgent(req.params.code!);
  const b = body(req);
  const reason = reasonOf(b);
  expectVersion(b, a.version);
  if (b.max_autonomy_level != null) {
    if (!["L0", "L1", "L2", "L3"].includes(String(b.max_autonomy_level))) throw invalid("max_autonomy_level");
    if (rank(String(b.max_autonomy_level)) > rank(CEILING)) throw rule("above_ceiling", { ceiling: CEILING });
  }
  if (b.allowed_tools != null) {
    if (!Array.isArray(b.allowed_tools)) throw invalid("allowed_tools");
    const bad = b.allowed_tools.map(String).filter((n) => !assignable(n));
    if (bad.length) throw rule("invalid_tool", { tools: bad });
  }
  if (b.monthly_budget_usd != null && !(Number(b.monthly_budget_usd) >= 0)) throw invalid("monthly_budget_usd");
  if (typeof b.is_enabled === "boolean") a.is_enabled = b.is_enabled;
  if (b.max_autonomy_level != null) a.max_autonomy_level = b.max_autonomy_level as MAgent["max_autonomy_level"];
  if (b.monthly_budget_usd !== undefined) a.monthly_budget_usd = b.monthly_budget_usd === null ? null : Number(b.monthly_budget_usd).toFixed(2);
  if (Array.isArray(b.allowed_tools)) a.allowed_tools = b.allowed_tools.map(String);
  Object.assign(a, { version: a.version + 1, updated_at: nowIso() });
  recordAudit(req.claims, "ai.agent_update", "agent_profiles", a.code, reason);
  return ok(agentOut(a, true));
}

export const AI_ADMIN_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/ai/kill-switch", permission: "ai:query", handler: () => ok(killOut()) },
  { method: "PUT", pattern: "/ai/kill-switch", permission: "ai:admin", handler: putKill },
  { method: "GET", pattern: "/ai/tools", permission: "ai:query", handler: tools },
  { method: "GET", pattern: "/ai/agents", permission: "ai:query", handler: (req) => ok(aiStore().agents.map((a) => agentOut(a, isAdmin(req)))) },
  { method: "PATCH", pattern: "/ai/agents/:code", permission: "ai:admin", handler: patchAgent },
  ...AI_POLICY_ROUTES,
  ...AI_ACTION_ROUTES,
  ...AI_LOG_ROUTES,
];
