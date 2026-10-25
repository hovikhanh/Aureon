/**
 * Mock `/workflow/approval-requests*` (T-625F, EP-WF-01..03, R-DEC-45) + the `task_reassign`
 * flow of EP-TASK-19. Inbox `assigned_to=me` = PENDING ∩ caller role in the **current step** ∩
 * scope (CEO all · DIR pillar of the rule · MGR own department) — CEO is exempt from scope, not
 * from the step role; DIR (escalate role) stands in when the department has no MGR. Never the
 * caller's own request. Same `verdict` for inbox, detail, decide and notifications (R-DEC-45).
 * Decide: not PENDING / expired → 409; requester = approver or reject without reason → 422;
 * role not in step → 403 FORBIDDEN_ROLE; outside scope → 403 FORBIDDEN_SCOPE. Final approve of a
 * `task_reassign` reassigns the task (version changed since the request → 409, stays PENDING).
 */
import { SNAPSHOT, claimsFor, type MockClaims, type RoleCode } from "./fixtures";
import { ok, paginate, parsePage } from "./http";
import { recordAudit } from "./audit";
import { pushNotification } from "./admin";
import type { MockRequest, Route } from "./router";
import { employeeById, newWorkId, userOfEmployee, workStore, type MApproval, type MTask } from "./work-store";
import { biz, err, requireIdem } from "./work";

const SLA_HOURS = 8;
const STATUSES = ["PENDING", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED"];
const nowIso = () => new Date().toISOString();

// `escalate_to_role_code` per rule (05 §2.5): stands in for a department-scoped step role (MGR).
const ESCALATE: Record<string, RoleCode> = { "RULE-task_reassign": "DIR" };
const stepRoles = (a: MApproval) => a.steps[a.step - 1] ?? [];
const staffed = (dept: string | null) => dept !== null && SNAPSHOT.users.some((u) => u.role === "MGR" && claimsFor(u).department_id === dept);

function inScope(c: Pick<MockClaims, "role" | "scope_pillars" | "department_id">, a: MApproval): boolean {
  if (c.role === "CEO") return true;
  if (c.role === "DIR") return a.pillar === null || c.scope_pillars.length === 0 || c.scope_pillars.includes(a.pillar);
  if (c.role === "MGR") return a.department_id !== null && a.department_id === c.department_id;
  return false;
}
/** BE `approval_service.decide_verdict` (R-DEC-45 §3) — shared by inbox, detail, decide and the
 *  approval_requested recipients: role ∈ current step (CEO exempt from scope, not from role) ∩
 *  scope; else the rule's escalate role (DIR, any pillar) when the department has no MGR / is null. */
function verdict(c: Pick<MockClaims, "role" | "scope_pillars" | "department_id">, a: MApproval): "ok" | "role" | "scope" {
  const roles = stepRoles(a);
  if (roles.includes(c.role)) return inScope(c, a) ? "ok" : "scope";
  const fb = roles.includes("MGR") ? ESCALATE[a.rule_code] : undefined;
  if (fb && c.role === fb && !staffed(a.department_id)) return "ok";
  return "role";
}
const canDecide = (c: Pick<MockClaims, "role" | "scope_pillars" | "department_id">, a: MApproval) => verdict(c, a) === "ok";
const overdue = (a: MApproval) => a.status === "PENDING" && a.due_at < nowIso();

function out(a: MApproval) {
  return {
    id: a.id, rule_code: a.rule_code, target_kind: a.target_kind, target_table: a.target_table, target_id: a.target_id, ai_action_id: a.ai_action_id,
    amount: a.amount, currency: a.currency, status: a.status, step: a.step, requested_by: a.requested_by, due_at: a.due_at, escalated_at: null,
    department_id: a.department_id, title_key: a.title_key, params: a.params, requested_by_name: a.requested_by_name, overdue: overdue(a), created_at: a.created_at,
  };
}
const detailOut = (a: MApproval) => ({ ...out(a), payload_diff: a.payload_diff, timeline: a.timeline });

async function list(req: MockRequest): Promise<Response> {
  const c = req.claims;
  const q = req.query;
  const page = parsePage(q, ["due_at", "created_at"]);
  const status = q.get("status") || "PENDING";
  if (!STATUSES.includes(status)) throw err(422, "VALIDATION_ERROR", "invalid status", { field: "status" });
  const assigned = q.get("assigned_to") ?? "me";
  if (assigned !== "me") throw err(422, "VALIDATION_ERROR", "assigned_to must be me", { field: "assigned_to" });
  const mine = (a: MApproval) => a.requested_by !== c.sub && canDecide(c, a);
  const pending = workStore().approvals.filter((a) => a.status === "PENDING" && mine(a)).length;
  const rows = workStore().approvals.filter((a) => a.status === status && mine(a)
    && (!q.get("rule_code") || a.rule_code === q.get("rule_code")) && (!q.get("target_kind") || a.target_kind === q.get("target_kind")))
    .sort((a, b) => a.due_at.localeCompare(b.due_at));
  const res = paginate(rows.map(out) as unknown as Record<string, unknown>[], page);
  return withMeta(res, { pending_count: pending });
}

async function withMeta(res: Response, extra: Record<string, unknown>): Promise<Response> {
  const body = (await res.json()) as { data: unknown; meta?: Record<string, unknown> };
  return ok(body.data, res.status, { ...(body.meta ?? {}), ...extra });
}

function find(c: MockClaims, id: string): MApproval {
  const a = workStore().approvals.find((x) => x.id === id);
  if (!a || !(canDecide(c, a) || a.requested_by === c.sub)) throw err(404, "NOT_FOUND", "approval request not found");
  return a;
}

function decide(req: MockRequest): Response {
  requireIdem(req);
  const c = req.claims;
  const a = workStore().approvals.find((x) => x.id === req.params.id);
  if (!a) throw err(404, "NOT_FOUND", "approval request not found");
  const b = (req.body ?? {}) as { decision?: string; reason?: string | null };
  if (b.decision !== "approve" && b.decision !== "reject") throw err(422, "VALIDATION_ERROR", "decision must be approve|reject", { field: "decision" });
  if (a.status !== "PENDING") throw err(409, "CONFLICT_STATE", "request already decided or expired", { status: a.status });
  if (a.due_at < nowIso()) {
    a.status = "EXPIRED";
    throw err(409, "CONFLICT_STATE", "request expired", { status: "EXPIRED" });
  }
  const v = verdict(c, a);
  if (v === "role") throw err(403, "FORBIDDEN_ROLE", `role ${c.role} not an approver for step ${a.step}`, { step: a.step });
  if (v === "scope") throw err(403, "FORBIDDEN_SCOPE", "approval outside your scope", { department_id: String(a.department_id) });
  if (a.requested_by === c.sub) throw biz("approver must differ from requester", { reason: "self_approval" });
  const reason = typeof b.reason === "string" ? b.reason.trim() : "";
  if (b.decision === "reject") {
    if (!reason) throw biz("reason required to reject", { field: "reason" });
    a.status = "REJECTED";
  } else {
    if (a.step === 2 && a.first_decided_by === c.sub) throw biz("second approver must be distinct (DEC-155)", { reason: "distinct_approvers" });
    if (a.step < a.steps.length) {
      a.first_decided_by = c.sub;
      a.step += 1;
    } else {
      if (a.target_kind === "task_reassign") applyReassign(c, a); // throws 409 → stays PENDING
      a.status = "APPROVED";
    }
  }
  a.timeline.push({ step: a.step, actor_ref: c.sub, decision: b.decision, reason: reason || null, at: nowIso() });
  recordAudit(c, "platform.approval_decided", "approval_requests", a.id, reason || null);
  const requester = SNAPSHOT.users.find((u) => claimsFor(u).sub === a.requested_by);
  if (requester && a.status !== "PENDING") {
    pushNotification(claimsFor(requester), { kind: "approval_decided", title: a.status, body: "", link: `/work/approvals?id=${a.id}`, ref_schema: "platform", ref_table: "approval_requests", ref_id: a.id });
  }
  return ok(out(a));
}

function applyReassign(c: MockClaims, a: MApproval): void {
  const p = a.payload as { task_id?: string; to_assignee_id?: string; task_version?: number };
  const t = workStore().tasks.find((x) => x.id === p.task_id && !x.deleted);
  if (!t) throw err(409, "CONFLICT_STATE", "task no longer exists", { task_id: String(p.task_id) });
  if (t.version !== p.task_version) throw err(409, "CONFLICT_STATE", "task changed since the request", { expected: p.task_version, current: t.version });
  t.assignee_id = p.to_assignee_id ?? t.assignee_id;
  t.version += 1;
  t.updated_at = nowIso();
  recordAudit(c, "execution.task_update", "tasks", t.id);
  const u = userOfEmployee(t.assignee_id);
  if (u) pushNotification(claimsFor(u), { kind: "task_assigned", title: t.title, body: "", link: `/work?task=${t.id}`, ref_schema: "execution", ref_table: "tasks", ref_id: t.id });
}

/** BE `approval_service` shape of a `task_reassign`: `title_key` `approval.<kind>.title`, ids-only
 *  `params` + `payload` (`task_version`), `payload_diff` on `assignee_id` (employee ids). */
export function reassignShape(taskId: string, from: string | null, to: string, reason: string, version: number) {
  return {
    title_key: "approval.task_reassign.title", params: { task_id: taskId, from_assignee_id: from, to_assignee_id: to },
    payload: { task_id: taskId, from_assignee_id: from, to_assignee_id: to, reason, task_version: version },
    payload_diff: [{ field: "assignee_id", before: from, after: to }],
  };
}

/** EP-TASK-19 body (validated by the caller in `work.ts`). */
export function createReassignRequest(c: MockClaims, t: MTask, to: string, reason: string) {
  if (workStore().approvals.some((a) => a.status === "PENDING" && a.target_kind === "task_reassign" && a.target_id === t.id)) {
    throw err(409, "CONFLICT_STATE", "a reassign request is already pending", { task_id: t.id });
  }
  const target = employeeById(to);
  if (to === t.assignee_id) throw biz("to_assignee_id is already the assignee", { field: "to_assignee_id", reason: "same_assignee" });
  if (!target) throw biz("assignee not found", { field: "to_assignee_id", reason: "not_found" });
  const stamp = nowIso();
  const a: MApproval = {
    id: newWorkId("approval"), rule_code: "RULE-task_reassign", target_kind: "task_reassign", target_table: "tasks", target_id: t.id, ai_action_id: null,
    amount: null, currency: "VND", status: "PENDING", step: 1, steps: [["MGR"]], pillar: "O", requested_by: c.sub, requested_by_name: c.name,
    due_at: new Date(Date.now() + SLA_HOURS * 3_600_000).toISOString(), department_id: t.department_id, ...reassignShape(t.id, t.assignee_id, to, reason, t.version),
    timeline: [{ step: 0, actor_ref: c.sub, decision: "requested", reason, at: stamp }], first_decided_by: null, created_at: stamp,
  };
  workStore().approvals.push(a);
  recordAudit(c, "platform.approval_requested", "approval_requests", a.id, reason);
  for (const u of SNAPSHOT.users) {
    const uc = claimsFor(u);
    if (uc.sub !== c.sub && !u.is_service_account && canDecide(uc, a)) {
      pushNotification(uc, { kind: "approval_requested", title: t.title, body: "", link: `/work/approvals?id=${a.id}`, ref_schema: "platform", ref_table: "approval_requests", ref_id: a.id });
    }
  }
  return out(a);
}

export const WORKFLOW_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/workflow/approval-requests", permission: "platform:approve", handler: list },
  { method: "GET", pattern: "/workflow/approval-requests/:id", permission: "platform:approve", handler: (req) => ok(detailOut(find(req.claims, req.params.id ?? ""))) },
  { method: "POST", pattern: "/workflow/approval-requests/:id/decide", permission: "platform:approve", handler: decide },
];
