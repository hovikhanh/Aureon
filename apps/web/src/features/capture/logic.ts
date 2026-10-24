/**
 * Pure D03 Capture FE logic (TC-M15-16, node-testable): DropZone limits (FR-DC-01: ≤ 100 files,
 * ≤ 50 MB/file, accepted extensions), VN number/date formats (P04), zod schema generated from
 * `FormOut.fields[]` (SCR-61), unmapped required fields (SCR-62), 422 → field errors.
 */
import { z } from "zod";
import type { Api } from "@aureon/shared-types";

export const MAX_FILES = 100;
export const MAX_FILE_BYTES = 50 * 1024 * 1024;
export const ACCEPT_EXT = [".pdf", ".png", ".jpg", ".jpeg", ".webp", ".heic", ".docx", ".xlsx", ".csv"] as const;
export const TABLE_EXT = [".xlsx", ".csv"] as const;

export type FileIssue = "too_many" | "too_large" | "type" | "empty";
export interface FileCheck { name: string; ok: boolean; issue: FileIssue | null }
const ext = (name: string) => name.slice(name.lastIndexOf(".")).toLowerCase();

/** Per-file inline errors; files past the 100th are refused with `too_many`. */
export function checkFiles(files: readonly { name: string; size: number }[]): FileCheck[] {
  return files.map((f, i) => {
    const issue: FileIssue | null = i >= MAX_FILES ? "too_many" : !(ACCEPT_EXT as readonly string[]).includes(ext(f.name)) ? "type" : f.size > MAX_FILE_BYTES ? "too_large" : f.size === 0 ? "empty" : null;
    return { name: f.name, ok: issue === null, issue };
  });
}
export const isTable = (name: string) => (TABLE_EXT as readonly string[]).includes(ext(name));

/** `1.250.000` / `1250000,5` / `-3,2` → number; invalid → null. */
export function parseVnNumber(s: string): number | null {
  const t = s.trim().replace(/\s/g, "");
  if (!/^-?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?$/.test(t)) return null;
  return Number(t.replace(/\./g, "").replace(",", "."));
}
export function formatVnNumber(n: number): string {
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 6 }).format(n);
}
/** `dd/mm/yyyy` → `yyyy-mm-dd`; invalid → null. */
export function parseVnDate(s: string): string | null {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s.trim());
  if (!m) return null;
  const iso = `${m[3]}-${m[2]!.padStart(2, "0")}-${m[1]!.padStart(2, "0")}`;
  const d = new Date(`${iso}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === iso ? iso : null;
}
export const isoToVn = (iso: string) => (/^\d{4}-\d{2}-\d{2}$/.test(iso) ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : iso);

/** One field → zod (string input from the form; value conversion in `toApiValue`). Error messages are i18n keys. */
export function fieldSchema(f: Api.FormFieldOut): z.ZodType<string, string> {
  const base = z.string().trim();
  const typed = base.refine((v) => v === "" || (f.value_type === "date" ? parseVnDate(v) !== null : ["number", "money"].includes(f.value_type) ? parseVnNumber(v) !== null : f.enum ? f.enum.includes(v) : true),
    { message: f.value_type === "date" ? "date_format" : ["number", "money"].includes(f.value_type) ? "number_format" : "in" });
  return f.required ? typed.refine((v) => v !== "", { message: "required" }) : typed;
}

export interface FormModel { values: Record<string, string>; rows: Record<string, string>[] }
type Shape = Record<string, z.ZodType<string, string>>;
export const headerFields = (fields: readonly Api.FormFieldOut[]) => fields.filter((f) => !f.repeatable_group);
export const rowFields = (fields: readonly Api.FormFieldOut[]) => fields.filter((f) => Boolean(f.repeatable_group));

/** zod schema for the whole SCR-61 form: header values + repeatable rows. */
export function formSchema(fields: readonly Api.FormFieldOut[]): z.ZodType<FormModel, FormModel> {
  const obj = (fs: readonly Api.FormFieldOut[]) => z.object(Object.fromEntries(fs.map((f) => [f.name, fieldSchema(f)])) as Shape) as unknown as z.ZodType<Record<string, string>, Record<string, string>>;
  return z.object({ values: obj(headerFields(fields)), rows: z.array(obj(rowFields(fields))) });
}

export function toApiValue(f: Api.FormFieldOut, v: string): unknown {
  if (v.trim() === "") return null;
  if (f.value_type === "date") return parseVnDate(v);
  if (["number", "money"].includes(f.value_type)) return parseVnNumber(v);
  return v.trim();
}
/** Form model → EP-DC-16 body (empty rows dropped). */
export function toManualBody(form: Api.FormOut, m: FormModel): Api.ManualSubmitIn {
  const conv = (fs: readonly Api.FormFieldOut[], o: Record<string, string>) => Object.fromEntries(fs.map((f) => [f.name, toApiValue(f, o[f.name] ?? "")]));
  const rows = m.rows.filter((r) => Object.values(r).some((v) => v.trim() !== "")).map((r) => conv(rowFields(form.fields), r));
  return { document_type: form.document_type, schema_version: form.schema_version, values: conv(headerFields(form.fields), m.values), rows };
}

export interface FieldErrorDetail { field: string | null; rule_code: string; row_index?: number | null; params?: Record<string, unknown> }
/** 422 `details.fields[]` → rhf paths (`values.x` / `rows.2.x`). */
export function errorPaths(details: Record<string, unknown> | undefined): { path: string; rule_code: string }[] {
  const fs = (Array.isArray(details?.fields) ? details.fields : []) as FieldErrorDetail[];
  return fs.filter((e) => e.field).map((e) => ({ path: e.row_index === null || e.row_index === undefined ? `values.${e.field}` : `rows.${e.row_index}.${e.field}`, rule_code: e.rule_code }));
}

/** SCR-62 step 1: required row fields (EP-DC-15 `repeatable_group`) that no column maps to. */
export function unmappedRequired(fields: readonly Pick<Api.FormFieldOut, "name" | "required" | "repeatable_group">[], mapping: Record<string, string | null>): string[] {
  const mapped = new Set(Object.values(mapping).filter(Boolean));
  return fields.filter((f) => f.repeatable_group && f.required && !mapped.has(f.name)).map((f) => f.name);
}
/** Field used by two columns at once (the mapping must stay 1 field ↔ 1 column). */
export function duplicateTargets(mapping: Record<string, string | null>): string[] {
  const seen = new Map<string, number>();
  for (const v of Object.values(mapping)) if (v) seen.set(v, (seen.get(v) ?? 0) + 1);
  return [...seen].filter(([, n]) => n > 1).map(([k]) => k);
}
