/** zod schemas of the goals forms (F4 check-in, "Ghi số đo", "Đặt target kỳ") — messages passed in, schema stays pure. */
import { z } from "zod";
import { CONFIDENCES } from "./logic";

const number = (msg: string) => z.string().trim().refine((v) => v !== "" && Number.isFinite(Number(v.replace(",", "."))), msg);
export const toNumber = (v: string) => Number(v.trim().replace(",", "."));
const optText = (max: number, msg: string) => z.string().max(max, msg);

export interface CheckInMessages { valueRequired: string; tooLong: string }
export function checkInSchema(m: CheckInMessages) {
  return z.object({
    value: number(m.valueRequired),
    confidence: z.enum(CONFIDENCES as unknown as ["HIGH", "MEDIUM", "LOW"]),
    note: optText(2000, m.tooLong),
    blocker: optText(300, m.tooLong),
  });
}
export type CheckInValues = z.infer<ReturnType<typeof checkInSchema>>;
/** → `CheckInCreate` (EP-PRF-02/04); empty text → null. */
export const toCheckInBody = (v: CheckInValues) => ({ value: toNumber(v.value), confidence: v.confidence, note: v.note.trim() || null, blocker: v.blocker.trim() || null });

export interface MeasureMessages { valueRequired: string; periodInvalid: string; tooLong: string }
export function measureSchema(m: MeasureMessages) {
  return z.object({
    period_key: z.string().trim().regex(/^\d{4}(-(0[1-9]|1[0-2]|Q[1-4]))?$/, m.periodInvalid),
    actual_value: number(m.valueRequired),
    note: optText(2000, m.tooLong),
  });
}
export type MeasureValues = z.infer<ReturnType<typeof measureSchema>>;
export const toMeasureBody = (v: MeasureValues) => ({ period_key: v.period_key.trim(), actual_value: toNumber(v.actual_value), note: v.note.trim() || null, data_source: "manual" as const });

export interface TargetMessages { valueRequired: string; periodInvalid: string; dateInvalid: string; tooLong: string }
export function targetSchema(m: TargetMessages) {
  return z.object({
    period_key: z.string().trim().regex(/^\d{4}(-(0[1-9]|1[0-2]|Q[1-4]))?$/, m.periodInvalid),
    target: number(m.valueRequired),
    valid_from: z.string().regex(/^(\d{4}-\d{2}-\d{2})?$/, m.dateInvalid),
    reason: optText(1000, m.tooLong),
  });
}
export type TargetValues = z.infer<ReturnType<typeof targetSchema>>;
export const toTargetBody = (v: TargetValues) => ({ period_key: v.period_key.trim(), target: toNumber(v.target), valid_from: v.valid_from || null, reason: v.reason.trim() || null });
