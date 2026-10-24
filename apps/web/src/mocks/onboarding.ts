/**
 * Mock EP-ADM-13/14 onboarding (T-648F, 10 §7.2.5, 05 `onboarding.state`, R-DEC-75): one state
 * object (no new table), `progress` derived from the org/user/goal stores (never trusted from the
 * client). Rules: `start` idempotent; `version` required except `start` (stale → 409); `finish` with
 * required steps not done → 422 `missing_steps`; `reset` needs `reason` (mock = DEMO_MODE, allowed).
 */
import { MockHttpError, ok } from "./http";
import { recordAudit } from "./audit";
import { userStore } from "./admin";
import { goalStore } from "./goals-store";
import { orgStore, today } from "./org";
import type { MockRequest, Route } from "./router";

export const STEPS = ["company", "org_import", "review", "users", "goals_import", "finish"] as const;
export type Step = (typeof STEPS)[number];
export const REQUIRED_STEPS: readonly Step[] = ["company", "org_import", "users"];
type StepState = { status: "pending" | "in_progress" | "done" | "skipped"; updated_at: string | null; refs: Record<string, unknown> };
export interface MOnboarding {
  status: "not_started" | "in_progress" | "completed"; started_at: string | null; completed_at: string | null; started_by: string | null;
  steps: Record<Step, StepState>; refs: Record<string, unknown>; version: number;
}

const G = globalThis as typeof globalThis & { __aureonMockOnboarding?: MOnboarding | null };
const fresh = (): MOnboarding => ({ status: "not_started", started_at: null, completed_at: null, started_by: null, version: 0, refs: {},
  steps: Object.fromEntries(STEPS.map((s) => [s, { status: "pending", updated_at: null, refs: {} }])) as Record<Step, StepState> });
export function onboardingStore(): MOnboarding {
  G.__aureonMockOnboarding ??= fresh();
  return G.__aureonMockOnboarding;
}
export function resetOnboardingStore(): void {
  G.__aureonMockOnboarding = null;
}

export function progress() {
  const org = orgStore();
  const at = today();
  const live = org.assignments.filter((a) => a.valid_from <= at && (a.valid_to === null || a.valid_to > at));
  const employees = new Set(live.map((a) => a.employee_id));
  const users = userStore().filter((u) => u.is_active && !u.is_service_account);
  const linked = new Set(users.map((u) => u.employee_id).filter(Boolean));
  const byRole: Record<string, number> = {};
  for (const u of users) byRole[u.role_code] = (byRole[u.role_code] ?? 0) + 1;
  const g = goalStore();
  return { organization_ready: org.orgs.some((o) => Boolean(o.name)), departments: org.depts.filter((d) => !d.archived).length, employees: employees.size,
    employees_without_user: [...employees].filter((e) => !linked.has(e)).length, users_by_role: byRole,
    kpis: g.kpis.filter((k) => !k.deleted).length, objectives: g.objectives.filter((o) => !o.deleted).length };
}

const stateOut = () => ({ ...structuredClone(onboardingStore()), progress: progress() });
const bad = (code: number, c: string, msg: string, details: Record<string, unknown> = {}): never => { throw new MockHttpError(code, c, msg, details); };

/** `refs` keeps only ids / codes / counts (no PII): strings ≤ 64 chars without spaces/@, numbers, arrays of those. */
function cleanRefs(v: unknown): Record<string, unknown> {
  if (v == null) return {};
  if (typeof v !== "object" || Array.isArray(v)) return bad(422, "VALIDATION_ERROR", "refs must be an object", { fields: ["refs"] });
  const okVal = (x: unknown): boolean => typeof x === "number" || (typeof x === "string" && x.length <= 64 && !/[\s@]/.test(x)) || (Array.isArray(x) && x.every(okVal));
  for (const [k, x] of Object.entries(v)) if (!okVal(x)) bad(422, "VALIDATION_ERROR", "refs only accept codes", { fields: [`refs.${k}`] });
  return v as Record<string, unknown>;
}

function patch(req: MockRequest): Response {
  const b = (req.body && typeof req.body === "object" ? req.body : {}) as { action?: string; step?: string | null; refs?: unknown; reason?: string | null; version?: number | null };
  const s = onboardingStore();
  const now = new Date().toISOString();
  const actions = ["start", "complete_step", "skip_step", "reopen_step", "finish", "reset"];
  if (!b.action || !actions.includes(b.action)) bad(422, "VALIDATION_ERROR", "invalid action", { fields: ["action"] });
  if (b.action === "start") {
    if (s.status === "in_progress") return ok(stateOut());
    if (s.status === "completed") bad(422, "BUSINESS_RULE_VIOLATION", "onboarding already completed", { reason: "already_completed" });
    Object.assign(s, { status: "in_progress", started_at: now, started_by: req.claims.sub, version: s.version + 1 });
    s.steps.company = { ...s.steps.company, status: "in_progress", updated_at: now };
    recordAudit(req.claims, "platform.onboarding_start", "system_settings", "onboarding.state");
    return ok(stateOut());
  }
  if (b.version == null) bad(422, "VALIDATION_ERROR", "version is required", { fields: ["version"] });
  if (b.version !== s.version) bad(409, "CONFLICT_STATE", "stale onboarding version", { expected: s.version });
  const refs = cleanRefs(b.refs);
  if (b.action === "reset") {
    if (!b.reason?.trim()) bad(422, "VALIDATION_ERROR", "reason is required", { fields: ["reason"] });
    G.__aureonMockOnboarding = { ...fresh(), version: s.version + 1 };
  } else if (b.action === "finish") {
    if (s.status !== "in_progress") bad(422, "BUSINESS_RULE_VIOLATION", "onboarding not in progress", { reason: "not_in_progress" });
    const missing = REQUIRED_STEPS.filter((x) => s.steps[x].status !== "done");
    if (missing.length) bad(422, "BUSINESS_RULE_VIOLATION", "required steps not done", { missing_steps: missing });
    s.steps.finish = { status: "done", updated_at: now, refs: {} };
    Object.assign(s, { status: "completed", completed_at: now, version: s.version + 1 });
  } else {
    if (s.status !== "in_progress") bad(422, "BUSINESS_RULE_VIOLATION", "onboarding not in progress", { reason: "not_in_progress" });
    const step = b.step as Step;
    if (!STEPS.includes(step) || step === "finish") bad(422, "VALIDATION_ERROR", "invalid step", { fields: ["step"] });
    if (b.action === "skip_step" && step !== "goals_import") bad(422, "BUSINESS_RULE_VIOLATION", "only goals_import is optional", { reason: "step_required" });
    const status = b.action === "complete_step" ? "done" : b.action === "skip_step" ? "skipped" : "in_progress";
    s.steps[step] = { status, updated_at: now, refs: { ...s.steps[step].refs, ...refs } };
    s.refs = { ...s.refs, ...refs };
    const next = STEPS[STEPS.indexOf(step) + 1];
    if (status !== "in_progress" && next && s.steps[next].status === "pending") s.steps[next] = { ...s.steps[next], status: "in_progress", updated_at: now };
    s.version += 1;
  }
  recordAudit(req.claims, `platform.onboarding_${b.action}`, "system_settings", "onboarding.state", b.reason ?? undefined);
  return ok(stateOut());
}

export const ONBOARDING_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/platform/onboarding", permission: "platform:read", handler: () => ok(stateOut()) },
  { method: "PATCH", pattern: "/platform/onboarding", permission: "platform:admin", handler: patch },
];
