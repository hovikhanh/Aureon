/**
 * Mock D11 Work store (T-625F, 10 §7.2.2) — tasks, dependencies, projects, milestones, approval
 * requests. Seeded from `seed_snapshot.json` (`tasks`, `projects`) the way `execution_seed.py`
 * writes them, plus a few **mock-only** rows (prefix `MOCK-`) until T-624 regenerates the
 * snapshot with sub-tasks / dependencies / `source_ref` / milestones / a `task_reassign`
 * request: the EMP demo account gets tasks in every due group, one dependency, one sub-task.
 * Every snapshot field used here is optional-safe (the BE may add fields later).
 * One shared store per process (like `org.ts`), so an MGR decision is seen by the EMP.
 */
import { SNAPSHOT, mockId, type MockClaims, type RoleCode } from "./fixtures";

export const WORK_STAMP = "2026-09-25T02:00:00Z"; // exec_data.CREATED
const dId = (code: string) => mockId("department", code);
export const empId = (code: string) => mockId("employee", code);
const uId = (email: string) => mockId("user", email);
const CEO_USER = SNAPSHOT.users.find((u) => u.role === "CEO");
const OWNER = CEO_USER ? uId(CEO_USER.email) : mockId("user", "ceo");

/** Business "today" (10 §7.2.2 `business_today()`): DEMO_REFERENCE_DATE in demo, else Asia/Ho_Chi_Minh date. */
export function workToday(env: Record<string, string | undefined> = process.env): string {
  const ref = env.DEMO_REFERENCE_DATE || env.NEXT_PUBLIC_DEMO_REFERENCE_DATE;
  if (ref && /^\d{4}-\d{2}-\d{2}$/.test(ref)) return ref;
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Ho_Chi_Minh", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}

export type TaskStatus = "backlog" | "todo" | "in_progress" | "blocked" | "in_review" | "done" | "cancelled";
export interface MTask {
  id: string; version: number; source: string; data_classification: string; created_at: string; updated_at: string;
  title: string; description: string | null; owner_id: string | null; assignee_id: string | null; department_id: string | null;
  start_date: string | null; due_date: string | null; priority: string; status: TaskStatus; blocked_reason: string | null;
  done_at: string | null; estimate_hours: number | null; actual_hours: number | null; evidence: Record<string, unknown>[] | null;
  project_id: string | null; initiative_id: string | null; milestone_id: string | null; meeting_id: string | null;
  decision_id: string | null; key_result_id: string | null; kpi_id: string | null; parent_task_id: string | null;
  source_ref: { kind: "meeting" | "decision" | "ai_action" | "document" | "mitigation"; id: string; page?: number | null } | null;
  is_critical: boolean; task_source: string; source_document_id: string | null; deleted: boolean;
}
export interface MDependency { id: string; version: number; task_id: string; depends_on_task_id: string; created_at: string; deleted: boolean }
export interface MProject {
  id: string; version: number; source: string; data_classification: string; created_at: string; updated_at: string; code: string; name: string;
  owner_id: string; department_id: string | null; start_date: string | null; due_date: string | null; actual_end_date: string | null;
  status: string; budget_amount: number | null; currency: string; initiative_id: string | null; deleted: boolean;
}
export interface MMilestone { id: string; version: number; project_id: string; title: string; due_date: string; status: "planned" | "done" | "missed"; done_at: string | null; created_at: string; updated_at: string; deleted: boolean }
export interface MApprovalStepLog { step: number; actor_ref: string | null; decision: string; reason?: string | null; at?: string | null }
export interface MApproval {
  id: string; rule_code: string; target_kind: "ai_action" | "task_reassign"; target_table: string | null; target_id: string | null;
  ai_action_id: string | null; amount: number | null; currency: string; status: "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED" | "EXPIRED";
  step: number; steps: RoleCode[][]; pillar: string | null; requested_by: string; requested_by_name: string | null; due_at: string;
  department_id: string | null; title_key: string; params: Record<string, unknown>; payload: Record<string, unknown>;
  payload_diff: Record<string, unknown>[]; timeline: MApprovalStepLog[]; first_decided_by: string | null; created_at: string;
}
export interface WorkStore { tasks: MTask[]; deps: MDependency[]; projects: MProject[]; milestones: MMilestone[]; approvals: MApproval[]; seq: number }

// on globalThis: `next dev` re-evaluates server modules when it compiles another page
const G = globalThis as typeof globalThis & { __aureonMockWork?: WorkStore | null };

export function workStore(): WorkStore {
  G.__aureonMockWork ??= seedWork();
  return G.__aureonMockWork;
}
export function resetWorkStore(): void {
  G.__aureonMockWork = null;
}
export const newWorkId = (kind: string): string => mockId(kind, `new-${++workStore().seq}-${Date.now()}`);

/** `employee_id` of a signed-in user (R-DEC-41 claim `employee_id`; tokens minted before the claim fall back to the e-mail). */
export function employeeOf(c: Pick<MockClaims, "email"> & Partial<Pick<MockClaims, "employee_id">>): string | null {
  if (c.employee_id !== undefined) return c.employee_id;
  const code = SNAPSHOT.users.find((u) => u.email === c.email)?.employee;
  return code ? empId(code) : null;
}
/** "Chính mình" = `employee_id` **or** `user_id` (R-DEC-41). */
export function selfIds(c: MockClaims): Set<string> {
  const e = employeeOf(c);
  return new Set(e ? [c.sub, e] : [c.sub]);
}
const EMP_BY_ID = new Map((SNAPSHOT.employees ?? []).map((e) => [empId(e.code), e]));
export const employeeById = (id: string | null | undefined) => (id ? EMP_BY_ID.get(id) : undefined);
export const departmentOfEmployee = (id: string | null | undefined): string | null => {
  const e = employeeById(id);
  return e ? dId(e.department) : null;
};
/** Demo user (login account) behind an employee id — notifications go to users (R-DEC-41). */
export function userOfEmployee(id: string | null | undefined) {
  const e = employeeById(id);
  return e ? SNAPSHOT.users.find((u) => u.employee === e.code && !u.is_service_account) : undefined;
}

// ------------------------------------------------------------------------------------ seed
type Snap = { tasks?: { key: string; assignee?: string | null; due_date?: string | null; status?: string; estimate_hours?: number | null; from_meeting?: boolean }[];
  projects?: { code: string; name: string; department?: string | null; start_date?: string | null; planned_end_date?: string | null; tasks_done?: number; tasks_total?: number }[] };
const SNAP = SNAPSHOT as unknown as Snap;
export const MEETING_ID = mockId("meeting", "GB-2026-10");

function shiftDate(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
const doneAt = (due: string, late: boolean) => `${shiftDate(due, late ? 2 : -1)}T09:00:00Z`;

function task(p: Partial<MTask> & { id: string; title: string }): MTask {
  return {
    version: 1, source: "SEED", data_classification: "internal", created_at: WORK_STAMP, updated_at: WORK_STAMP,
    description: null, owner_id: OWNER, assignee_id: null, department_id: null, start_date: null, due_date: null, priority: "medium",
    status: "todo", blocked_reason: null, done_at: null, estimate_hours: null, actual_hours: null, evidence: null, project_id: null,
    initiative_id: null, milestone_id: null, meeting_id: null, decision_id: null, key_result_id: null, kpi_id: null, parent_task_id: null,
    source_ref: null, is_critical: false, task_source: "manual", source_document_id: null, deleted: false, ...p,
  };
}

function seedWork(): WorkStore {
  const today = workToday();
  const tasks: MTask[] = (SNAP.tasks ?? []).map((t, n) => {
    const assignee = t.assignee ? empId(t.assignee) : null;
    const status = (t.status ?? "todo") as TaskStatus;
    const due = t.due_date ?? null;
    return task({
      id: mockId("task", t.key), title: `${t.key} — việc seed`, assignee_id: assignee, department_id: departmentOfEmployee(assignee),
      status, due_date: due, estimate_hours: t.estimate_hours ?? null,
      done_at: status === "done" && due ? doneAt(due, n === 4) : null,
      blocked_reason: status === "blocked" ? "Chờ phê duyệt ngân sách" : null,
      meeting_id: t.from_meeting ? MEETING_ID : null, task_source: t.from_meeting ? "meeting" : "manual",
      source_ref: t.from_meeting ? { kind: "meeting", id: MEETING_ID } : null,
    });
  });
  const projects: MProject[] = (SNAP.projects ?? []).map((p) => ({
    id: mockId("project", p.code), version: 1, source: "SEED", data_classification: "internal", created_at: WORK_STAMP, updated_at: WORK_STAMP,
    code: p.code, name: p.name, owner_id: OWNER, department_id: p.department ? dId(p.department) : null, start_date: p.start_date ?? null,
    due_date: p.planned_end_date ?? null, actual_end_date: null, status: "active", budget_amount: null, currency: "VND", initiative_id: null, deleted: false,
  }));
  for (const p of SNAP.projects ?? []) {
    for (let i = 0; i < (p.tasks_total ?? 0); i++) {
      const done = i < (p.tasks_done ?? 0);
      tasks.push(task({ id: mockId("task", `${p.code}-${i}`), title: `${p.code} hạng mục ${i + 1}`, department_id: p.department ? dId(p.department) : null,
        project_id: mockId("project", p.code), status: done ? "done" : "todo", done_at: done ? "2026-09-22T02:00:00Z" : null, created_at: "2026-08-26T02:00:00Z" }));
    }
  }
  // ---- mock-only rows (T-624 will seed the real ones) ----
  const emp = SNAPSHOT.users.find((u) => u.role === "EMP");
  const peer = (SNAP.tasks ?? []).map((t) => t.assignee).find((a) => a && a !== emp?.employee && employeeById(empId(a))?.department === emp?.department);
  const care = projects.find((p) => p.code === "PRJ-CARE")?.id ?? null;
  if (emp?.employee) {
    const me = empId(emp.employee);
    const base = { assignee_id: me, department_id: departmentOfEmployee(me), owner_id: mockId("user", SNAPSHOT.users.find((u) => u.role === "MGR" && u.department === emp.department)?.email ?? "mgr"), estimate_hours: 4, source: "MANUAL" };
    tasks.push(
      task({ ...base, id: mockId("task", "MOCK-E0"), title: "Khảo sát nhu cầu khách hàng ABC Care", project_id: care, status: "done", due_date: shiftDate(today, -6), done_at: `${shiftDate(today, -7)}T09:00:00Z` }),
      task({ ...base, id: mockId("task", "MOCK-E1"), title: "Gọi lại khách hàng có phiếu bảo trì quá hạn", status: "in_progress", priority: "high", due_date: shiftDate(today, -3), meeting_id: MEETING_ID, task_source: "meeting", source_ref: { kind: "meeting", id: MEETING_ID } }),
      task({ ...base, id: mockId("task", "MOCK-E2"), title: "Cập nhật phiếu bảo trì lên hệ thống", project_id: care, due_date: today, source_ref: { kind: "document", id: mockId("document", "MOCK-DOC-1"), page: 2 }, task_source: "document" }),
      task({ ...base, id: mockId("task", "MOCK-E3"), title: "Chuẩn bị báo cáo tuần bộ phận CSKH", priority: "urgent", due_date: shiftDate(today, 2) }),
      task({ ...base, id: mockId("task", "MOCK-E3A"), title: "Tổng hợp số phiếu đã đóng", parent_task_id: mockId("task", "MOCK-E3"), due_date: shiftDate(today, 1), estimate_hours: 2 }),
      task({ ...base, id: mockId("task", "MOCK-E4"), title: "Rà soát danh sách thiết bị bảo hành", status: "backlog", priority: "low" }),
      task({ ...base, id: mockId("task", "MOCK-E5"), title: "Đề xuất cải tiến quy trình tiếp nhận", due_date: shiftDate(today, 14) }),
    );
  }
  const deps: MDependency[] = [{ id: mockId("dependency", "MOCK-E2>E1"), version: 1, task_id: mockId("task", "MOCK-E2"), depends_on_task_id: mockId("task", "MOCK-E1"), created_at: WORK_STAMP, deleted: false }];
  const erp = projects.find((p) => p.code === "PRJ-ERP")?.id;
  const ms = (pid: string | undefined, key: string, title: string, due: string, status: MMilestone["status"]): MMilestone[] => (pid ? [{
    id: mockId("milestone", key), version: 1, project_id: pid, title, due_date: due, status, done_at: status === "done" ? `${due}T09:00:00Z` : null, created_at: WORK_STAMP, updated_at: WORK_STAMP, deleted: false }] : []);
  const milestones = [
    ...ms(erp, "ERP-1", "Chốt yêu cầu nghiệp vụ kho", "2026-08-15", "done"),
    ...ms(erp, "ERP-2", "Chạy thử phân hệ nhập kho", shiftDate(today, -5), "planned"),
    ...ms(erp, "ERP-3", "Go-live toàn bộ kho", "2026-11-30", "planned"),
    ...ms(care ?? undefined, "CARE-1", "Chốt bảng giá gói ABC Care", "2026-10-10", "done"),
    ...ms(care ?? undefined, "CARE-2", "Ra mắt gói ABC Care 2027", "2027-01-15", "planned"),
  ];
  return { tasks, deps, projects, milestones, approvals: seedApprovals(emp, peer ?? null), seq: 0 };
}

function seedApprovals(emp: (typeof SNAPSHOT.users)[number] | undefined, peerCode: string | null): MApproval[] {
  const now = Date.now();
  const iso = (h: number) => new Date(now + h * 3_600_000).toISOString();
  const base = { target_table: null, ai_action_id: null, currency: "VND", status: "PENDING" as const, step: 1, first_decided_by: null };
  const out: MApproval[] = [];
  const ai = SNAPSHOT.users.find((u) => u.role === "AI");
  const aiBy = ai ? uId(ai.email) : mockId("user", "ai");
  out.push(
    { ...base, timeline: [], id: mockId("approval", "MOCK-AI-1"), rule_code: "RULE-ai_action_single", target_kind: "ai_action", target_id: mockId("ai_action", "1"), ai_action_id: mockId("ai_action", "1"),
      amount: 350_000_000, steps: [["CEO", "DIR"]], pillar: "F", requested_by: aiBy, requested_by_name: ai?.full_name ?? null, due_at: iso(6), department_id: null,
      title_key: "approval.ai_action.title", params: { amount: 350_000_000, currency: "VND" }, payload: { vendor: "Công ty Văn phòng Phẩm Sài Gòn" }, created_at: iso(-2),
      payload_diff: [{ field: "vendor", before: null, after: "Công ty Văn phòng Phẩm Sài Gòn" }] },
    { ...base, timeline: [], id: mockId("approval", "MOCK-AI-2"), rule_code: "RULE-ai_action_single", target_kind: "ai_action", target_id: mockId("ai_action", "2"), ai_action_id: mockId("ai_action", "2"),
      amount: 1_200_000_000, steps: [["CEO", "DIR"]], pillar: "F", requested_by: aiBy, requested_by_name: ai?.full_name ?? null, due_at: iso(-1), department_id: null,
      title_key: "approval.ai_action.title", params: { amount: 1_200_000_000, currency: "VND" }, payload: { vendor: "Công ty Thiết bị Minh Long" }, created_at: iso(-10),
      payload_diff: [{ field: "vendor", before: null, after: "Công ty Thiết bị Minh Long" }] },
  );
  if (emp?.employee && peerCode) {
    const t = mockId("task", "MOCK-E5");
    const from = empId(emp.employee);
    const to = empId(peerCode);
    out.push({ ...base, timeline: [], id: mockId("approval", "MOCK-RA-1"), rule_code: "RULE-task_reassign", target_kind: "task_reassign", target_table: "tasks", target_id: t, amount: null,
      steps: [["MGR"]], pillar: "O", requested_by: uId(emp.email), requested_by_name: emp.full_name, due_at: iso(5), department_id: dId(emp.department),
      title_key: "approval.task_reassign.title", params: { task_id: t, from_assignee_id: from, to_assignee_id: to },
      payload: { task_id: t, from_assignee_id: from, to_assignee_id: to, reason: "Đang dồn nhiều việc bảo trì", task_version: 1 }, created_at: iso(-1),
      payload_diff: [{ field: "assignee_id", before: from, after: to }] });
  }
  return out;
}
