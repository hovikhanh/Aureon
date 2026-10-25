/**
 * zod schemas of the SCR-42 forms (task edit/create, reassign request) — messages are i18n texts
 * passed in by the component so the schema stays pure/testable.
 */
import { z } from "zod";
import { PRIORITIES } from "./logic";

export interface TaskFormMessages { titleRequired: string; dueBeforeStart: string; estimateInvalid: string }

const date = z.string().regex(/^(\d{4}-\d{2}-\d{2})?$/);

export function taskFormSchema(m: TaskFormMessages) {
  return z.object({
    title: z.string().trim().min(1, m.titleRequired).max(500, m.titleRequired),
    description: z.string().max(5000),
    start_date: date,
    due_date: date,
    priority: z.enum(PRIORITIES),
    estimate_hours: z.string().trim().refine((v) => v === "" || (/^\d+(\.\d+)?$/.test(v) && Number(v) >= 0), m.estimateInvalid),
    assignee_id: z.string(),
  }).refine((v) => !v.start_date || !v.due_date || v.due_date >= v.start_date, { path: ["due_date"], message: m.dueBeforeStart });
}
export type TaskFormValues = z.infer<ReturnType<typeof taskFormSchema>>;

/** Form values → `TaskUpdate`/`TaskCreate` body (empty → null; unchanged fields omitted on edit). */
export function toTaskBody(v: TaskFormValues, before?: Partial<Record<keyof TaskFormValues, unknown>>): Record<string, unknown> {
  const out: Record<string, unknown> = {
    title: v.title.trim(),
    description: v.description.trim() || null,
    start_date: v.start_date || null,
    due_date: v.due_date || null,
    priority: v.priority,
    estimate_hours: v.estimate_hours === "" ? null : Number(v.estimate_hours),
    assignee_id: v.assignee_id || null,
  };
  if (!before) return out;
  return Object.fromEntries(Object.entries(out).filter(([k, val]) => (before[k as keyof TaskFormValues] ?? null) !== val));
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function reassignSchema(m: { toInvalid: string; reasonRequired: string }) {
  return z.object({
    to_assignee_id: z.string().trim().regex(UUID, m.toInvalid),
    reason: z.string().trim().min(1, m.reasonRequired).max(500, m.reasonRequired),
  });
}
export type ReassignValues = z.infer<ReturnType<typeof reassignSchema>>;
