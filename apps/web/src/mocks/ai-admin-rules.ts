/**
 * Mock autonomy resolution + policy validation (10 §7.2.5 EP-AI-14/17/19/20, 04 §9.1): default →
 * matching policy (role, no agent/amount) → min(agent max) → min(ceiling L2) → kill switch
 * (`WRITE_OFF` ≤ L2, `L0` → L0). 422 `details.reason` codes are the spec ones.
 */
import { MockHttpError } from "./http";
import type { MockRequest } from "./router";
import { CEILING, CRITICAL_ACTS, minLevel, rank, rootDefault, toolByName, type Level, type MTool } from "./ai-admin-catalog";
import { aiStore, type MAgent } from "./ai-admin-store";

export const rule = (reason: string, extra: Record<string, unknown> = {}) =>
  new MockHttpError(422, "BUSINESS_RULE_VIOLATION", reason, { reason, ...extra });
export const invalid = (field: string) => new MockHttpError(422, "VALIDATION_ERROR", `${field} is invalid`, { field });

export function killApplies(code: string): boolean {
  const k = aiStore().kill;
  return k.enabled && (k.agents.length === 0 || k.agents.includes(code));
}

export function agentEffectiveMax(a: MAgent): Level {
  let l = minLevel(a.max_autonomy_level, CEILING);
  if (killApplies(a.code)) l = aiStore().kill.mode === "L0" ? "L0" : minLevel(l, "L2");
  return a.is_enabled ? l : "L0";
}

/** Effective level of a tool for a role (EP-AI-14 `effective_level`); READ/APPROVAL → L0. */
export function effectiveLevel(tool: MTool, role: string, agentCode = "ceo"): Level {
  if (tool.kind === "READ" || tool.kind === "APPROVAL") return "L0";
  const s = aiStore();
  const p = s.policies.find((x) => !x.deleted && x.is_active && x.tool_name === tool.name && x.role_code === role && !x.agent_profile_code && x.max_amount === null)
    ?? s.policies.find((x) => !x.deleted && x.is_active && x.tool_name === tool.name && x.agent_profile_code === agentCode && x.max_amount === null);
  let l = p?.level ?? rootDefault(tool);
  const agent = s.agents.find((a) => a.code === agentCode);
  if (agent) l = minLevel(l, agent.max_autonomy_level);
  l = minLevel(l, CEILING);
  if (killApplies(agentCode)) l = s.kill.mode === "L0" ? "L0" : minLevel(l, "L2");
  return l;
}

const LEVELS = ["L0", "L1", "L2", "L3"];
/** EP-AI-19/20 rules, in the spec order. */
export function checkPolicy(toolName: string, level: unknown, maxLevel: unknown, maxAmount: unknown, currency: unknown): MTool {
  const tool = toolByName(toolName);
  if (!tool) throw invalid("tool_name");
  if (!LEVELS.includes(String(level))) throw invalid("level");
  if (!LEVELS.includes(String(maxLevel))) throw invalid("max_level");
  if (tool.kind === "READ" || tool.kind === "APPROVAL") throw rule("not_configurable");
  const l = String(level) as Level;
  const m = String(maxLevel) as Level;
  if (rank(l) > rank(m) || rank(m) > rank(tool.autonomy_max)) throw rule("above_tool_max", { tool_max: tool.autonomy_max });
  if (rank(l) > rank(CEILING) || rank(m) > rank(CEILING)) throw rule("above_ceiling", { ceiling: CEILING });
  if (tool.kind === "EXECUTION" && rank(m) > rank("L2")) throw rule("execution_max_l2");
  if (tool.action_name && CRITICAL_ACTS.has(tool.action_name) && rank(l) > rank("L2")) throw rule("critical_field");
  if (maxAmount !== null && maxAmount !== undefined) {
    if (!Number.isInteger(maxAmount) || (maxAmount as number) < 0) throw invalid("max_amount");
    if (!currency) throw invalid("currency");
  }
  return tool;
}

export const body = (req: MockRequest) => (req.body && typeof req.body === "object" ? req.body : {}) as Record<string, unknown>;
export function idem(req: MockRequest): void {
  if (!req.headers.get("idempotency-key")) throw new MockHttpError(400, "BAD_REQUEST", "Idempotency-Key header is required", { header: "Idempotency-Key" });
}
export const reasonOf = (b: Record<string, unknown>) => {
  if (typeof b.reason !== "string" || !b.reason.trim()) throw invalid("reason");
  return b.reason.trim();
};
export const expectVersion = (b: Record<string, unknown>, v: number) => {
  if (typeof b.version !== "number") throw invalid("version");
  if (b.version !== v) throw new MockHttpError(409, "CONFLICT_STATE", "version mismatch", { current_version: v });
};
