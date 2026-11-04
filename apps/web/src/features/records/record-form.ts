/**
 * Pure form engine of the business-record editors (M7): one field list per resource drives the zod
 * schema, the initial values, the create body (POST) and the PATCH body (changed fields + the
 * optimistic `version`, a stale one → `409 CONFLICT_STATE`). Money is BIGINT in the smallest unit
 * (VND, CLAUDE.md §5.2), percentages are 0–100. No I/O, no React — unit-tested.
 */
import { z } from "zod";

export type FieldType =
  | "text" | "textarea" | "number" | "money" | "pct" | "date" | "month" | "select" | "boolean" | "ref" | "lines";
/** Reference pickers resolved by the UI from the existing list endpoints (no new API). */
export type RefKind = "client" | "department" | "user" | "employee";

export interface FieldSpec {
  name: string;
  type: FieldType;
  required?: boolean;
  options?: readonly string[];
  ref?: RefKind;
  /** Sent on create only (the API's Update schema has no such field) — shown read-only on edit. */
  createOnly?: boolean;
  max?: number;
}

export interface LineValues { description: string; quantity: string; unit_price: string; vat_pct: string }
export type FormValues = Record<string, string | boolean | LineValues[]>;
export interface FormMessages { required: string; number: string; tooLong: string; range: string; period: string; lines: string }

export const VAT_RATES = ["0", "5", "8", "10"] as const;
export const emptyLine = (): LineValues => ({ description: "", quantity: "1", unit_price: "", vat_pct: "10" });

const num = (v: string) => Number(v.trim().replace(/\s/g, "").replace(",", "."));
const isNum = (v: string) => v.trim() !== "" && Number.isFinite(num(v));

function scalar(f: FieldSpec, m: FormMessages): z.ZodType<unknown> {
  const opt = (s: z.ZodString) => (f.required ? s.trim().min(1, m.required) : s);
  switch (f.type) {
    case "boolean":
      return z.boolean();
    case "number":
    case "money":
    case "pct":
      return z.string().superRefine((v, ctx) => {
        if (!v.trim()) {
          if (f.required) ctx.addIssue({ code: "custom", message: m.required });
          return;
        }
        if (!isNum(v)) return void ctx.addIssue({ code: "custom", message: m.number });
        const n = num(v);
        // money = BIGINT smallest unit; every `number` field here is a count / year → integers
        if (n < 0 || (f.type === "pct" ? n > 100 : !Number.isInteger(n)))
          ctx.addIssue({ code: "custom", message: m.range });
      });
    case "month":
      return opt(z.string()).refine((v) => !v || /^\d{4}-(0[1-9]|1[0-2])$/.test(v.trim()), m.period);
    case "textarea":
      return opt(z.string()).pipe(z.string().max(f.max ?? 2000, m.tooLong));
    default:
      return opt(z.string()).pipe(z.string().max(f.max ?? 200, m.tooLong));
  }
}

export function recordSchema(fields: readonly FieldSpec[], m: FormMessages) {
  const shape: Record<string, z.ZodType<unknown>> = {};
  for (const f of fields) {
    shape[f.name] = f.type === "lines"
      ? z.array(z.object({
          description: z.string().trim().min(1, m.required).max(500, m.tooLong),
          quantity: z.string().refine((v) => isNum(v) && num(v) > 0, m.number),
          unit_price: z.string().refine((v) => isNum(v) && num(v) >= 0 && Number.isInteger(num(v)), m.number),
          vat_pct: z.enum(VAT_RATES),
        })).min(1, m.lines)
      : scalar(f, m);
  }
  return z.object(shape);
}

/** Form value → API value (`null` for an empty optional field). */
export function toApi(f: FieldSpec, raw: FormValues[string]): unknown {
  if (f.type === "boolean") return Boolean(raw);
  if (f.type === "lines") {
    return (raw as LineValues[]).map((l) => ({
      description: l.description.trim(), quantity: num(l.quantity), unit_price: Math.round(num(l.unit_price)), vat_pct: Number(l.vat_pct),
    }));
  }
  const v = String(raw ?? "").trim();
  if (!v) return null;
  if (f.type === "money") return Math.round(num(v));
  if (f.type === "number" || f.type === "pct") return num(v);
  return v;
}

/** API value → form value. */
export function fromApi(f: FieldSpec, value: unknown): FormValues[string] {
  if (f.type === "boolean") return Boolean(value);
  if (f.type === "lines") {
    return Array.isArray(value) && value.length
      ? value.map((l: Record<string, unknown>) => ({
          description: String(l.description ?? ""), quantity: String(l.quantity ?? "1"),
          unit_price: String(l.unit_price ?? ""), vat_pct: String(l.vat_pct ?? "10"),
        }))
      : [emptyLine()];
  }
  if (value === null || value === undefined) return "";
  if (f.type === "date" && typeof value === "string") return value.slice(0, 10);
  return String(value);
}

export function initialValues(fields: readonly FieldSpec[], row?: Record<string, unknown>, defaults: Record<string, string | boolean> = {}): FormValues {
  const out: FormValues = {};
  for (const f of fields) {
    out[f.name] = row ? fromApi(f, row[f.name]) : f.name in defaults ? defaults[f.name]! : f.type === "boolean" ? false : f.type === "lines" ? [emptyLine()] : "";
  }
  return out;
}

/** POST body: every field with a value (required ones are guaranteed by the schema). */
export function createBody(fields: readonly FieldSpec[], v: FormValues): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const f of fields) {
    const val = toApi(f, v[f.name]!);
    if (val !== null) body[f.name] = val;
  }
  return body;
}

/** PATCH body: only the fields whose value changed (create-only fields never), plus `version`. */
export function updateBody(fields: readonly FieldSpec[], v: FormValues, row: Record<string, unknown>): Record<string, unknown> {
  const body: Record<string, unknown> = { version: row.version };
  for (const f of fields) {
    if (f.createOnly) continue;
    const next = toApi(f, v[f.name]!);
    const prev = toApi(f, fromApi(f, row[f.name]));
    if (JSON.stringify(next) !== JSON.stringify(prev)) body[f.name] = next;
  }
  return body;
}
