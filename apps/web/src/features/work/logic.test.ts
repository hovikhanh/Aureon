/** T-625F — pure logic of the M1.3 work screens (TC-M13-12). */
import { describe, expect, it } from "vitest";
import {
  BOARD_COLUMNS, DEFAULT_STATUSES, approvalParams, approvalTitle, blockingTitles, boardColumns, canMove, dueGroup, groupByDue,
  groupByStatus, isTaskStatus, loadShade, parseMineFilters, rangeInvalid, shortId, workErrorKey, writeMineFilters,
} from "./logic";
import { reassignSchema, taskFormSchema, toTaskBody, type TaskFormValues } from "./task-form";

const TODAY = "2026-10-20"; // Tuesday; ISO week ends Sunday 2026-10-25

describe("DEC-147 transitions", () => {
  it.each([["todo", "done", true], ["backlog", "done", false], ["done", "in_progress", true], ["done", "todo", false], ["cancelled", "todo", true], ["bogus", "todo", false]] as const)(
    "%s → %s = %s", (from, to, ok) => expect(canMove(from, to)).toBe(ok));
  it("isTaskStatus", () => {
    expect(isTaskStatus("in_review")).toBe(true);
    expect(isTaskStatus("open")).toBe(false);
  });
});

describe("due groups (SCR-42)", () => {
  it.each([
    [{ due_date: "2026-10-18", overdue: true }, "overdue"], [{ due_date: TODAY }, "today"], [{ due_date: "2026-10-25" }, "week"],
    [{ due_date: "2026-10-26" }, "later"], [{ due_date: null }, "none"], [{ due_date: "2026-10-18", overdue: false }, "later"],
  ] as const)("%o → %s", (t, g) => expect(dueGroup(t, TODAY)).toBe(g));

  it("groups and sorts by due date, no-due last", () => {
    const g = groupByDue([{ id: "b", due_date: "2026-10-24" }, { id: "a", due_date: "2026-10-22" }, { id: "n", due_date: null }], TODAY);
    expect(g.week.map((x) => x.id)).toEqual(["a", "b"]);
    expect(g.none.map((x) => x.id)).toEqual(["n"]);
    expect(g.overdue).toEqual([]);
  });
});

describe("filters ⇄ query string", () => {
  it("defaults hide done/cancelled and keep the URL clean", () => {
    const f = parseMineFilters(new URLSearchParams(""));
    expect(f.statuses).toEqual([...DEFAULT_STATUSES]);
    expect(writeMineFilters(new URLSearchParams("task=x"), f).toString()).toBe("task=x");
  });
  it("round-trips statuses + due range; drops junk", () => {
    const f = parseMineFilters(new URLSearchParams("status=done,bogus&status=todo&due_from=2026-10-01&due_to=nope"));
    expect(f).toEqual({ statuses: ["todo", "done"], dueFrom: "2026-10-01", dueTo: null });
    const sp = writeMineFilters(new URLSearchParams("due_to=2026-12-01"), { ...f, dueTo: null });
    expect(sp.get("status")).toBe("todo,done");
    expect(sp.has("due_to")).toBe(false);
    expect(parseMineFilters(sp)).toEqual(f);
  });
  it("range validity", () => {
    expect(rangeInvalid({ dueFrom: "2026-10-02", dueTo: "2026-10-01" })).toBe(true);
    expect(rangeInvalid({ dueFrom: "2026-10-01", dueTo: null })).toBe(false);
  });
});

describe("kanban", () => {
  it("cancelled column behind the toggle", () => {
    expect(boardColumns(false)).toEqual([...BOARD_COLUMNS]);
    expect(boardColumns(true).at(-1)).toBe("cancelled");
  });
  it("groups by status, ignoring hidden columns", () => {
    const g = groupByStatus([{ status: "todo" }, { status: "cancelled" }, { status: "todo" }], boardColumns(false));
    expect(g.todo).toHaveLength(2);
    expect(g.cancelled).toBeUndefined();
  });
});

describe("workload shade", () => {
  it.each([[80, "low"], [80.1, "mid"], [110, "mid"], [112.5, "high"]] as const)("%s%% → %s", (p, s) => expect(loadShade(p, 110)).toBe(s));
  it("threshold comes from the response", () => expect(loadShade(105, 100)).toBe("high"));
});

describe("errors → i18n keys", () => {
  const e = (code: string, details: Record<string, unknown> = {}) => ({ code, details });
  it.each([
    [e("BUSINESS_RULE_VIOLATION", { rule: "FR-TASK-02", blocking: [] }), "dependencyOpen"], [e("BUSINESS_RULE_VIOLATION", { cycle: [] }), "cycle"],
    [e("BUSINESS_RULE_VIOLATION", { field: "blocked_reason" }), "blockedReason"], [e("BUSINESS_RULE_VIOLATION", { reason: "direct_reassign_allowed" }), "directReassign"],
    [e("BUSINESS_RULE_VIOLATION", { reason: "has_subtasks" }), "hasSubtasks"], [e("BUSINESS_RULE_VIOLATION", { rule: "R-DEC-42" }), "parent"],
    [e("BUSINESS_RULE_VIOLATION", { field: "due_date" }), "dueBeforeStart"], [e("BUSINESS_RULE_VIOLATION", { field: "reason" }), "reasonRequired"],
    [e("BUSINESS_RULE_VIOLATION", { reason: "self_approval" }), "selfApproval"],
    [e("BUSINESS_RULE_VIOLATION", { reason: "distinct_approvers" }), "distinctApprovers"],
    [e("BUSINESS_RULE_VIOLATION", { field: "to_assignee_id", reason: "same_assignee" }), "sameAssignee"],
    [e("BUSINESS_RULE_VIOLATION", { field: "to_assignee_id", reason: "not_found" }), "assigneeNotFound"], [e("BUSINESS_RULE_VIOLATION"), "rule"],
    [e("CONFLICT_STATE", { from_status: "done" }), "transition"], [e("CONFLICT_STATE"), "conflict"], [e("FORBIDDEN_SCOPE"), "FORBIDDEN_SCOPE"], [e("BOOM"), "generic"],
  ])("%o → %s", (err, key) => expect(workErrorKey(err)).toBe(key));
  it("blocking titles fall back to ids", () => {
    expect(blockingTitles(e("X", { blocking: [{ task_id: "t1", title: "A" }, { task_id: "t2" }] }))).toEqual(["A", "t2"]);
    expect(blockingTitles(e("X"))).toEqual([]);
  });
});

describe("approvals + misc", () => {
  it("title key → i18n key", () => {
    expect(approvalTitle("approval.task_reassign.title", "task")).toBe("task_reassign");
    expect(approvalTitle("approval.ai_action.title", "task_reassign")).toBe("ai_action");
    expect(approvalTitle("approval.task_reassign", "ai_action")).toBe("ai_action");
    expect(approvalTitle(null, "task_reassign")).toBe("task_reassign");
    expect(approvalTitle("approval.unknown", "ai_action")).toBe("ai_action");
  });
  it("params: names from members, else short id; bad shape → —", () => {
    const names = new Map([["0123456789abcdef", "Ngô Thị Lan"]]);
    expect(approvalParams({ from_assignee_id: "0123456789abcdef", to_assignee_id: "fedcba9876543210" }, (id) => names.get(id))).toEqual({ from: "Ngô Thị Lan", to: "fedcba98" });
    expect(approvalParams({ from_assignee_id: 3, to_assignee_id: { x: 1 } })).toEqual({ from: "—", to: "—" });
    expect(approvalParams(undefined)).toEqual({ from: "—", to: "—" });
  });
  it("shortId", () => expect(shortId("0123456789abcdef")).toBe("01234567"));
});

describe("task forms (zod)", () => {
  const schema = taskFormSchema({ titleRequired: "T", dueBeforeStart: "D", estimateInvalid: "E" });
  const base: TaskFormValues = { title: "Việc", description: "", start_date: "", due_date: "", priority: "medium", estimate_hours: "", assignee_id: "" };
  it("validates title, estimate and date order", () => {
    expect(schema.safeParse(base).success).toBe(true);
    const bad = schema.safeParse({ ...base, title: " ", estimate_hours: "-1", start_date: "2026-10-10", due_date: "2026-10-01" });
    expect(bad.success).toBe(false);
    expect(bad.error?.issues.map((i) => i.message).sort()).toEqual(["D", "E", "T"]);
    expect(schema.safeParse({ ...base, start_date: "2026-10-10", due_date: "2026-10-01" }).error?.issues[0]?.message).toBe("D");
  });
  it("body: empty → null, edit keeps only changed fields", () => {
    expect(toTaskBody({ ...base, estimate_hours: "2.5" })).toMatchObject({ title: "Việc", due_date: null, estimate_hours: 2.5, assignee_id: null });
    expect(toTaskBody({ ...base, due_date: "2026-11-01" }, toTaskBody(base))).toEqual({ due_date: "2026-11-01" });
  });
  it("reassign request needs a UUID and a reason", () => {
    const s = reassignSchema({ toInvalid: "I", reasonRequired: "R" });
    expect(s.safeParse({ to_assignee_id: "NV-0046", reason: "" }).error?.issues.map((i) => i.message)).toEqual(["I", "R"]);
    expect(s.safeParse({ to_assignee_id: "3f0c6b2e-1d2a-4c3b-9a8d-1234567890ab", reason: "Quá tải" }).success).toBe(true);
  });
});

describe("EP-TASK-01 query", () => {
  it("repeats status, drops empties, default limit 100", async () => {
    const { taskPath } = await import("./use-work");
    expect(taskPath({ mine: true, status: ["todo", "done"], due_from: null, project_id: "" })).toBe("/work/tasks?limit=100&mine=true&status=todo&status=done");
    expect(taskPath({ limit: 20 })).toBe("/work/tasks?limit=20");
  });
});
