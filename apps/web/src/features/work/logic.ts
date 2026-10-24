/**
 * Pure SCR-42/55/57/43 logic (T-625F, 06 §3.4 Spec lock M1.3) — due-group bucketing, filter ⇄
 * query string, DEC-147 transitions, kanban columns, heatmap shade, error → i18n key. No React.
 */
import { addDays, isIsoDate, weekStart } from "@/lib/work-dates";

export const TASK_STATUSES = ["backlog", "todo", "in_progress", "blocked", "in_review", "done", "cancelled"] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];
export const PRIORITIES = ["low", "medium", "high", "urgent"] as const;
export type Priority = (typeof PRIORITIES)[number];

/** DEC-147 (`execution/services/task_rules.TRANSITIONS`) — menu "Chuyển sang…". */
export const TRANSITIONS: Record<TaskStatus, readonly TaskStatus[]> = {
  backlog: ["todo", "in_progress", "blocked", "cancelled"],
  todo: ["backlog", "in_progress", "blocked", "done", "cancelled"],
  in_progress: ["todo", "blocked", "in_review", "done", "cancelled"],
  blocked: ["todo", "in_progress", "cancelled"],
  in_review: ["in_progress", "blocked", "done", "cancelled"],
  done: ["in_progress"],
  cancelled: ["backlog", "todo"],
};
export const isTaskStatus = (v: unknown): v is TaskStatus => (TASK_STATUSES as readonly string[]).includes(String(v));
export const canMove = (from: string, to: TaskStatus): boolean => isTaskStatus(from) && TRANSITIONS[from].includes(to);

// ------------------------------------------------------------------ "Task của tôi" due groups
export const DUE_GROUPS = ["overdue", "today", "week", "later", "none"] as const;
export type DueGroup = (typeof DUE_GROUPS)[number];

/** Overdue (API `overdue`) · today · rest of this ISO week · later · no due date. A closed task
 *  whose due date is past is not overdue (API) → "later" (shown only when done/cancelled are filtered in). */
export function dueGroup(t: { due_date: string | null; overdue?: boolean | null }, today: string): DueGroup {
  if (t.overdue) return "overdue";
  if (!t.due_date) return "none";
  if (t.due_date === today) return "today";
  const sunday = addDays(weekStart(today), 6);
  if (t.due_date > today && t.due_date <= sunday) return "week";
  return "later";
}

export function groupByDue<T extends { due_date: string | null; overdue?: boolean | null }>(rows: readonly T[], today: string): Record<DueGroup, T[]> {
  const out = Object.fromEntries(DUE_GROUPS.map((g) => [g, [] as T[]])) as Record<DueGroup, T[]>;
  for (const r of rows) out[dueGroup(r, today)].push(r);
  for (const g of DUE_GROUPS) out[g].sort((a, b) => (a.due_date ?? "9999").localeCompare(b.due_date ?? "9999"));
  return out;
}

// ------------------------------------------------------------------ filters ⇄ query string
export const DEFAULT_STATUSES: readonly TaskStatus[] = TASK_STATUSES.filter((s) => s !== "done" && s !== "cancelled");
export interface MineFilters { statuses: TaskStatus[]; dueFrom: string | null; dueTo: string | null }

export function parseMineFilters(sp: URLSearchParams): MineFilters {
  const raw = sp.getAll("status").flatMap((s) => s.split(",")).filter(isTaskStatus);
  const statuses = raw.length ? TASK_STATUSES.filter((s) => raw.includes(s)) : [...DEFAULT_STATUSES];
  const dueFrom = sp.get("due_from");
  const dueTo = sp.get("due_to");
  return { statuses, dueFrom: isIsoDate(dueFrom) ? dueFrom : null, dueTo: isIsoDate(dueTo) ? dueTo : null };
}

/** Writes the filters into `sp` (defaults omitted so `/work` stays clean); other params are kept. */
export function writeMineFilters(sp: URLSearchParams, f: MineFilters): URLSearchParams {
  const out = new URLSearchParams(sp);
  out.delete("status");
  const isDefault = f.statuses.length === DEFAULT_STATUSES.length && DEFAULT_STATUSES.every((s) => f.statuses.includes(s));
  if (!isDefault) out.set("status", f.statuses.join(","));
  for (const [k, v] of [["due_from", f.dueFrom], ["due_to", f.dueTo]] as const) {
    if (v) out.set(k, v);
    else out.delete(k);
  }
  return out;
}
export const rangeInvalid = (f: Pick<MineFilters, "dueFrom" | "dueTo">) => Boolean(f.dueFrom && f.dueTo && f.dueFrom > f.dueTo);

// ------------------------------------------------------------------ kanban
export const BOARD_COLUMNS: readonly TaskStatus[] = ["backlog", "todo", "in_progress", "blocked", "in_review", "done"];
export const BOARD_COLUMN_LIMIT = 50;
export function boardColumns(showCancelled: boolean): TaskStatus[] {
  return showCancelled ? [...BOARD_COLUMNS, "cancelled"] : [...BOARD_COLUMNS];
}
export function groupByStatus<T extends { status: string }>(rows: readonly T[], cols: readonly TaskStatus[]): Record<string, T[]> {
  const out: Record<string, T[]> = Object.fromEntries(cols.map((c) => [c, [] as T[]]));
  for (const r of rows) out[r.status]?.push(r);
  return out;
}

// ------------------------------------------------------------------ workload heatmap (06 §3.4)
export type Shade = "low" | "mid" | "high";
/** ≤ 80 light · 80–threshold medium · > threshold orange/red (threshold from the response). */
export function loadShade(pct: number, thresholdPct: number): Shade {
  if (pct > thresholdPct) return "high";
  return pct > 80 ? "mid" : "low";
}

// ------------------------------------------------------------------ errors → i18n key
export interface ErrorLike { code: string; details: Record<string, unknown> }
/** `work.errors.<key>` for an ApiError (refined by `details.rule` / `details.reason`). */
export function workErrorKey(e: ErrorLike): string {
  if (e.code === "BUSINESS_RULE_VIOLATION") {
    if (e.details.rule === "FR-TASK-02" && Array.isArray(e.details.blocking)) return "dependencyOpen";
    if (Array.isArray(e.details.cycle)) return "cycle";
    if (e.details.field === "blocked_reason") return "blockedReason";
    if (e.details.reason === "direct_reassign_allowed") return "directReassign";
    if (e.details.reason === "has_subtasks") return "hasSubtasks";
    if (e.details.rule === "R-DEC-42") return "parent";
    if (e.details.field === "due_date") return "dueBeforeStart";
    if (e.details.field === "reason") return "reasonRequired";
    if (e.details.reason === "self_approval") return "selfApproval";
    return "rule";
  }
  if (e.code === "CONFLICT_STATE") return e.details.from_status ? "transition" : "conflict";
  if (["FORBIDDEN_ROLE", "FORBIDDEN_SCOPE", "DUPLICATE_RESOURCE", "NOT_FOUND", "VALIDATION_ERROR", "BAD_REQUEST"].includes(e.code)) return e.code;
  return "generic";
}

/** Titles of the open blockers in a FR-TASK-02 error (for the toast). */
export function blockingTitles(e: ErrorLike): string[] {
  const b = e.details.blocking;
  return Array.isArray(b) ? b.map((x) => String((x as { title?: unknown }).title ?? (x as { task_id?: unknown }).task_id ?? "")).filter(Boolean) : [];
}

/** Short display id when no name is readable (R-DEC-44: workload has no names). */
export const shortId = (id: string) => id.slice(0, 8);

// ------------------------------------------------------------------ approvals (SCR-43)
const APPROVAL_TITLES = ["task_reassign", "payment", "ai_action"] as const;
export type ApprovalTitle = (typeof APPROVAL_TITLES)[number];
/** `title_key` (`approval.<x>`, EP-WF-01) → `work.approvalTitle.<x>`; unknown → by `target_kind`. */
export function approvalTitle(titleKey: string | null | undefined, targetKind: string): ApprovalTitle {
  const k = titleKey?.split(".").pop() as ApprovalTitle | undefined;
  if (k && APPROVAL_TITLES.includes(k)) return k;
  return targetKind === "task_reassign" ? "task_reassign" : "ai_action";
}
/** i18n params of a title: API `params` with string values only (never trust shape). */
export function approvalParams(params: Record<string, unknown> | undefined): Record<string, string> {
  const p = params ?? {};
  const s = (v: unknown) => (typeof v === "string" || typeof v === "number" ? String(v) : "—");
  return { task: s(p.task_title), to: s(p.to_name), vendor: s(p.vendor) };
}
