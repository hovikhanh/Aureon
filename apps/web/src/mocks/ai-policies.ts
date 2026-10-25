/**
 * Mock EP-AI-18..21 autonomy policies (10 §7.2.5): list + `meta.defaults[]` (after ceiling),
 * create (Idempotency-Key, 422 reason codes, 409 duplicate live key), patch (version → 409),
 * soft delete with mandatory `reason` query → 204.
 */
import { MockHttpError, ok, parsePage } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";
import { AGENT_CODES, CEILING, TOOLS, minLevel, rootDefault, type Level } from "./ai-admin-catalog";
import { aiStore, newAiId, nowIso, type MPolicy } from "./ai-admin-store";
import { body, checkPolicy, expectVersion, idem, invalid, reasonOf } from "./ai-admin-rules";

const ROLES = ["CEO", "DIR", "MGR", "EMP", "REV", "ADM", "AI"];
const out = (p: MPolicy) => {
  const copy: Partial<MPolicy> = { ...p };
  delete copy.deleted;
  return copy;
};

export function policyDefaults() {
  return TOOLS.filter((t) => t.kind === "WRITE" || t.kind === "EXECUTION").map((t) => ({
    tool_name: t.name, action_name: t.action_name, default_level: minLevel(rootDefault(t), CEILING), max_level: minLevel(t.autonomy_max, CEILING),
  }));
}

function list(req: MockRequest): Response {
  const q = req.query;
  const page = parsePage(q, ["tool_name", "updated_at"]);
  const [tool, agent, role, active] = ["tool_name", "agent_profile_code", "role_code", "is_active"].map((k) => q.get(k));
  const withDeleted = q.get("include_deleted") === "true";
  const rows = aiStore().policies.filter((p) => (withDeleted || !p.deleted) && (!tool || p.tool_name === tool) && (!agent || p.agent_profile_code === agent)
    && (!role || p.role_code === role) && (active === null || String(p.is_active) === active));
  const key = (page.sortBy ?? "tool_name") as "tool_name" | "updated_at";
  const sorted = [...rows].sort((a, b) => a[key].localeCompare(b[key]) * (page.order === "desc" ? -1 : 1));
  const data = sorted.slice(page.offset, page.offset + page.limit).map(out);
  return ok(data, 200, { pagination: { total: rows.length, limit: page.limit, offset: page.offset, has_next: page.offset + data.length < rows.length }, defaults: policyDefaults() });
}

function create(req: MockRequest): Response {
  idem(req);
  const b = body(req);
  const reason = reasonOf(b);
  const tool = checkPolicy(String(b.tool_name ?? ""), b.level, b.max_level, b.max_amount, b.currency);
  const agent = (b.agent_profile_code as string | null | undefined) ?? null;
  const role = (b.role_code as string | null | undefined) ?? null;
  if (agent && !AGENT_CODES.has(agent)) throw invalid("agent_profile_code");
  if (role && !ROLES.includes(role)) throw invalid("role_code");
  const amount = (b.max_amount as number | null | undefined) ?? null;
  const s = aiStore();
  if (s.policies.some((p) => !p.deleted && p.action_name === tool.action_name && p.agent_profile_code === agent && p.role_code === role && p.max_amount === amount)) {
    throw new MockHttpError(409, "DUPLICATE_RESOURCE", "policy exists", { fields: ["action_name", "agent_profile_code", "role_code", "max_amount"] });
  }
  const p: MPolicy = { id: newAiId("autonomy_policy"), tool_name: tool.name, action_name: tool.action_name!, agent_profile_code: agent, role_code: role, max_amount: amount,
    currency: amount === null ? null : String(b.currency), level: b.level as Level, max_level: b.max_level as Level, is_active: b.is_active !== false, reason,
    version: 1, updated_by: req.claims.sub, updated_at: nowIso(), deleted: false };
  s.policies.push(p);
  recordAudit(req.claims, "ai.autonomy_policy_create", "autonomy_policies", p.id, reason);
  return ok(out(p), 201);
}

const find = (id: string | undefined) => {
  const p = aiStore().policies.find((x) => x.id === id && !x.deleted);
  if (!p) throw new MockHttpError(404, "NOT_FOUND", "policy not found");
  return p;
};

function patch(req: MockRequest): Response {
  const p = find(req.params.id);
  const b = body(req);
  const reason = reasonOf(b);
  expectVersion(b, p.version);
  const next = { level: b.level ?? p.level, max_level: b.max_level ?? p.max_level, max_amount: b.max_amount !== undefined ? b.max_amount : p.max_amount, currency: b.currency !== undefined ? b.currency : p.currency };
  checkPolicy(p.tool_name, next.level, next.max_level, next.max_amount, next.currency);
  Object.assign(p, next, { is_active: typeof b.is_active === "boolean" ? b.is_active : p.is_active, reason, version: p.version + 1, updated_by: req.claims.sub, updated_at: nowIso() });
  recordAudit(req.claims, "ai.autonomy_policy_update", "autonomy_policies", p.id, reason);
  return ok(out(p));
}

function remove(req: MockRequest): Response {
  const p = find(req.params.id);
  const reason = req.query.get("reason");
  if (!reason?.trim()) throw invalid("reason");
  Object.assign(p, { deleted: true, updated_at: nowIso(), updated_by: req.claims.sub });
  recordAudit(req.claims, "ai.autonomy_policy_delete", "autonomy_policies", p.id, reason);
  return ok(null, 204);
}

export const AI_POLICY_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/ai/autonomy-policies", permission: "ai:admin", handler: list },
  { method: "POST", pattern: "/ai/autonomy-policies", permission: "ai:admin", handler: create },
  { method: "PATCH", pattern: "/ai/autonomy-policies/:id", permission: "ai:admin", handler: patch },
  { method: "DELETE", pattern: "/ai/autonomy-policies/:id", permission: "ai:admin", handler: remove },
];
