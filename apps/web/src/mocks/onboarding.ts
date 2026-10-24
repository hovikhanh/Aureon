/**
 * Mock EP-ADM-13/14 onboarding (T-648F, 10 §7.2.5, 05 `onboarding.state`, R-DEC-75): one state
 * object (no new table), `progress` derived from the org/user/goal stores (never trusted from the
 * client). Rules = BE `onboarding_service.py`: `start` idempotent (in progress / completed → current
 * state, no bump); `version` required except `start` (stale → 409 `details.version`); `finish` with
 * required steps not done → 422 `missing_steps`; `reset` needs `reason` (mock = DEMO_MODE, allowed);
 * `refs` whitelist (ids / non-negative ints); only `goals_import` skippable. Step `review` is derived
 * `done` once the `org_import` document is COMMITTED (05 §2.8) — like the BE GET.
 */
import { MockHttpError, ok } from "./http";
import { recordAudit } from "./audit";
import { userStore } from "./admin";
import { goalStore } from "./goals-store";
import { orgStore, today } from "./org";
import { captureStore } from "./capture-store";
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

const stateOut = () => ({ ...derived(onboardingStore()), progress: progress() });
const bad = (code: number, c: string, msg: string, details: Record<string, unknown> = {}): never => { throw new MockHttpError(code, c, msg, details); };

/** BE `REF_KEYS` whitelist (05 §2.8): ids (uuid-like strings) + non-negative integer counts, nothing else. */
const REF_KEYS: Record<string, "id" | "ids" | "int"> = { organization_id: "id", org_import_id: "id", goals_import_id: "id", document_ids: "ids", import_id: "id", document_id: "id", count: "int", rows: "int", users_created: "int" };
const TOP_REFS = ["organization_id", "org_import_id", "goals_import_id", "document_ids"];
const isId = (x: unknown) => typeof x === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(x);
function cleanRefs(v: unknown): Record<string, unknown> {
  if (v == null) return {};
  if (typeof v !== "object" || Array.isArray(v)) return bad(422, "VALIDATION_ERROR", "refs accept ids and counts only", { field: "refs" });
  for (const [k, x] of Object.entries(v)) {
    const kind = REF_KEYS[k];
    const okv = kind === "id" ? isId(x) : kind === "ids" ? Array.isArray(x) && x.every(isId) : kind === "int" ? Number.isInteger(x) && (x as number) >= 0 : false;
    if (!okv) bad(422, "VALIDATION_ERROR", "refs accept ids and counts only", { field: `refs.${k}` });
  }
  return v as Record<string, unknown>;
}

/** `review` pending + `org_import` document COMMITTED → `done` (derived, not stored — BE `_derive_review`). */
function derived(s: MOnboarding): MOnboarding {
  const out = structuredClone(s);
  if (out.status === "not_started" || out.steps.review.status !== "pending") return out;
  const refs = out.steps.org_import.refs;
  const c = captureStore();
  const docId = typeof refs.document_id === "string" ? refs.document_id : c.batches.find((b) => b.id === (refs.org_import_id ?? out.refs.org_import_id))?.document_id;
  const doc = docId ? c.docs.find((d) => d.id === docId) : undefined;
  if (doc?.status === "COMMITTED") out.steps.review = { ...out.steps.review, status: "done", updated_at: doc.committed_at };
  return out;
}

function patch(req: MockRequest): Response {
  const b = (req.body && typeof req.body === "object" ? req.body : {}) as { action?: string; step?: string | null; refs?: unknown; reason?: string | null; version?: number | null };
  const s = onboardingStore();
  const now = new Date().toISOString();
  const actions = ["start", "complete_step", "skip_step", "reopen_step", "finish", "reset"];
  if (!b.action || !actions.includes(b.action)) bad(422, "VALIDATION_ERROR", "invalid action", { field: "action" });
  const refs = cleanRefs(b.refs);
  if (b.action === "start") {
    if (s.status !== "not_started") return ok(stateOut()); // idempotent, no audit (BE)
    Object.assign(s, { status: "in_progress", started_at: now, started_by: req.claims.sub, version: s.version + 1 });
    recordAudit(req.claims, "platform.onboarding_start", "system_settings", "onboarding.state");
    return ok(stateOut());
  }
  if (b.version == null) bad(422, "VALIDATION_ERROR", "version is required", { field: "version" });
  if (b.action === "reset") {
    if (!b.reason?.trim()) bad(422, "VALIDATION_ERROR", "reason is required", { field: "reason" });
  } else if (s.status !== "in_progress") {
    bad(422, "BUSINESS_RULE_VIOLATION", `onboarding is ${s.status}`, { reason: "not_in_progress" });
  } else if (b.action === "finish") {
    const missing = REQUIRED_STEPS.filter((x) => s.steps[x].status !== "done");
    if (missing.length) bad(422, "BUSINESS_RULE_VIOLATION", "required steps are not done", { missing_steps: missing });
  } else {
    if (!b.step || !STEPS.includes(b.step as Step) || b.step === "finish") bad(422, "VALIDATION_ERROR", "a wizard step is required", { field: "step" });
    if (b.action === "skip_step" && b.step !== "goals_import") bad(422, "BUSINESS_RULE_VIOLATION", "step cannot be skipped", { reason: "not_skippable" });
  }
  if (b.version !== s.version) bad(409, "CONFLICT_STATE", "setting changed since it was read", { key: "onboarding.state", version: s.version });
  if (b.action === "reset") {
    G.__aureonMockOnboarding = { ...fresh(), version: s.version + 1 };
  } else if (b.action === "finish") {
    s.steps.finish = { status: "done", updated_at: now, refs: {} };
    Object.assign(s, { status: "completed", completed_at: now, version: s.version + 1 });
  } else {
    const step = b.step as Step;
    const status = b.action === "complete_step" ? "done" : b.action === "skip_step" ? "skipped" : "in_progress";
    s.steps[step] = { status, updated_at: now, refs: { ...s.steps[step].refs, ...refs } };
    s.version += 1;
  }
  const top = Object.fromEntries(Object.entries(refs).filter(([k]) => TOP_REFS.includes(k)));
  const cur = onboardingStore();
  cur.refs = { ...cur.refs, ...top };
  recordAudit(req.claims, `platform.onboarding_${b.action}`, "system_settings", "onboarding.state", b.reason ?? undefined);
  return ok(stateOut());
}

export const ONBOARDING_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/platform/onboarding", permission: "platform:read", handler: () => ok(stateOut()) },
  { method: "PATCH", pattern: "/platform/onboarding", permission: "platform:admin", handler: patch },
];
