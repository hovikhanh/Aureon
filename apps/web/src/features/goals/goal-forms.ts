/**
 * zod schemas + body mappers of the KPI / Objective / Key Result editors (EP-KPI-02/04,
 * EP-OKR-02/04/07/09 — 10 §7.2.3). Messages are passed in so the schemas stay pure (unit-tested).
 * Enum values mirror `KpiCreate` / `ObjectiveCreate` / `KeyResultCreate` of the API.
 */
import { z } from "zod";
import { toNumber } from "./forms";

export const PERIOD_TYPES = ["MONTH", "QUARTER", "YEAR", "ROLLING_12M"] as const;
export const DIRECTIONS = ["HIGHER_IS_BETTER", "LOWER_IS_BETTER", "WITHIN_RANGE", "BINARY"] as const;
export const VALUE_TYPES = ["numeric", "percentage", "ratio", "currency", "duration", "count"] as const;
export const GOAL_STATUSES = ["draft", "active", "closed"] as const;
export const OBJECTIVE_LEVELS = ["company", "department", "team", "individual"] as const;
export const OKR_TYPES = ["committed", "aspirational"] as const;

const isNumber = (v: string) => v.trim() !== "" && Number.isFinite(Number(v.trim().replace(",", ".")));

export interface GoalFormMessages { required: string; number: string; tooLong: string; periodInvalid: string; codeInvalid: string }

export function kpiSchema(m: GoalFormMessages, { creating }: { creating: boolean }) {
  return z.object({
    // the code is the KPI's stable key (unique, referenced by IDP imports and the AI) — not editable
    code: creating ? z.string().trim().min(1, m.required).max(50, m.tooLong).regex(/^[A-Za-z0-9._-]+$/, m.codeInvalid) : z.string(),
    name: z.string().trim().min(1, m.required).max(200, m.tooLong),
    unit: z.string().trim().min(1, m.required).max(50, m.tooLong),
    target: z.string().refine(isNumber, m.number),
    period_type: z.enum(PERIOD_TYPES),
    direction: z.enum(DIRECTIONS),
    value_type: z.enum(VALUE_TYPES),
    status: z.enum(GOAL_STATUSES),
    owner_id: z.string().min(1, m.required),
    department_id: z.string(),
  });
}
export type KpiValues = z.infer<ReturnType<typeof kpiSchema>>;

/**
 * `department_id` ("" = none picked): on create an empty pick is left out, so the API pins it
 * (`goal_scope.pin_department`: CEO → company level, DIR/MGR → their own department). On update it is
 * sent only when changed — re-sending `null` would make the API re-pin a DIR/MGR goal.
 */
const deptCreate = (d: string) => (d ? { department_id: d } : {});
const deptUpdate = (d: string, prev: string | null | undefined) => (d !== (prev ?? "") ? { department_id: d || null } : {});

/** → `KpiCreate` (EP-KPI-02). */
export const toKpiCreate = (v: KpiValues) => ({
  code: v.code.trim(), name: v.name.trim(), unit: v.unit.trim(), target: toNumber(v.target),
  period_type: v.period_type, direction: v.direction, value_type: v.value_type, status: v.status, owner_id: v.owner_id,
  ...deptCreate(v.department_id),
});
/** → `KpiUpdate` (EP-KPI-04): `version` is the optimistic lock (a stale one → `409 CONFLICT_STATE`). */
export const toKpiUpdate = (v: KpiValues, version: number, prevDepartment?: string | null) => ({
  version, name: v.name.trim(), unit: v.unit.trim(), target: toNumber(v.target),
  direction: v.direction, value_type: v.value_type, status: v.status, owner_id: v.owner_id,
  ...deptUpdate(v.department_id, prevDepartment),
});

export function objectiveSchema(m: GoalFormMessages) {
  return z.object({
    title: z.string().trim().min(1, m.required).max(500, m.tooLong),
    period_key: z.string().trim().regex(/^\d{4}(-(0[1-9]|1[0-2]|Q[1-4]))?$/, m.periodInvalid),
    level: z.enum(OBJECTIVE_LEVELS),
    okr_type: z.enum(OKR_TYPES),
    status: z.enum(GOAL_STATUSES),
    owner_id: z.string().min(1, m.required),
    department_id: z.string(),
  });
}
export type ObjectiveValues = z.infer<ReturnType<typeof objectiveSchema>>;
/** → `ObjectiveCreate` (EP-OKR-02). A new OKR starts `draft`: activating needs 2..5 KRs (server rule). */
const objectiveBody = (v: ObjectiveValues) => ({
  title: v.title.trim(), period_key: v.period_key.trim(), level: v.level, okr_type: v.okr_type, status: v.status, owner_id: v.owner_id,
});
export const toObjectiveCreate = (v: ObjectiveValues) => ({ ...objectiveBody(v), ...deptCreate(v.department_id) });
export const toObjectiveUpdate = (v: ObjectiveValues, version: number, prevDepartment?: string | null) => ({
  version, ...objectiveBody(v), ...deptUpdate(v.department_id, prevDepartment),
});

export function keyResultSchema(m: GoalFormMessages) {
  return z.object({
    title: z.string().trim().min(1, m.required).max(500, m.tooLong),
    baseline: z.string().refine(isNumber, m.number),
    target: z.string().refine(isNumber, m.number),
    unit: z.string().trim().min(1, m.required).max(50, m.tooLong),
    status: z.enum(GOAL_STATUSES),
    owner_id: z.string().min(1, m.required),
  });
}
export type KeyResultValues = z.infer<ReturnType<typeof keyResultSchema>>;
/** → `KeyResultCreate` (EP-OKR-07). `current_value` / `confidence` only move through a check-in. */
export const toKeyResultCreate = (v: KeyResultValues) => ({
  title: v.title.trim(), baseline: toNumber(v.baseline), target: toNumber(v.target), unit: v.unit.trim(), status: v.status, owner_id: v.owner_id,
});
export const toKeyResultUpdate = (v: KeyResultValues, version: number) => ({ version, ...toKeyResultCreate(v) });

/** Owner choices: CEO/ADM (`platform:read`) pick any active user; everyone else owns what they create. */
export function ownerOptions(
  self: { id: string; label: string },
  users: readonly { id: string; full_name: string; email: string; is_active?: boolean }[] | undefined,
  canPick: boolean,
  current?: string | null,
): { id: string; label: string }[] {
  const base = [self];
  if (canPick) for (const u of users ?? []) if (u.is_active !== false && u.id !== self.id) base.push({ id: u.id, label: `${u.full_name} · ${u.email}` });
  if (current && !base.some((o) => o.id === current)) base.push({ id: current, label: `${current.slice(0, 8)}…` }); // keep an existing owner
  return base;
}
