/**
 * Mock row validator for C1/C5 (mirror of `idp/services/validator.py` ops `required` / `in` +
 * type checks). Row errors use `{field, rule_code, message_key, params}` (RowErrorOut); the FE
 * renders `capture.errors.<rule_code>`.
 */
import { SNAPSHOT } from "./fixtures";
import type { FieldDef } from "./capture-schemas";

export interface RowError { field: string | null; rule_code: string; message_key: string; params: Record<string, unknown> }

const err = (field: string, rule_code: string, params: Record<string, unknown> = {}): RowError => ({ field, rule_code, message_key: `capture.errors.${rule_code}`, params });

/** `dd/mm/yyyy` or ISO `yyyy-mm-dd` → ISO; null when not a real date. */
export function parseVnDate(v: string): string | null {
  const s = v.trim();
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s) ?? null;
  const iso = m ? `${m[3]}-${m[2]!.padStart(2, "0")}-${m[1]!.padStart(2, "0")}` : /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null;
  if (!iso) return null;
  const d = new Date(`${iso}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === iso ? iso : null;
}

/** VN number (`1.250.000`, `18,5`, `≥ 9,0 tháng`) → number; null when no numeric token. */
export function parseVnNumber(v: unknown): number | null {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  const tok = /-?\d[\d.]*(,\d+)?/.exec(String(v).replace(/\s/g, ""));
  if (!tok) return null;
  const n = Number(tok[0].replace(/\./g, "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

const DEPT_CODES = new Set(SNAPSHOT.departments.map((d) => d.code));
const KPI_CODES = new Set(((SNAPSHOT as unknown as { kpis?: { code: string }[] }).kpis ?? []).map((k) => k.code));
/** `master_ref` lookups the mock can resolve (hr.departments codes; KPI codes or METRIC-* codes). */
export function masterKnown(ref: string, value: string): boolean {
  if (ref === "hr.departments") return DEPT_CODES.has(value);
  if (ref === "execution.kpis") return KPI_CODES.has(value);
  return true;
}

/** Validate + normalise one row (or the header values of a C1 form). */
export function validateValues(fields: readonly FieldDef[], raw: Record<string, unknown>): { values: Record<string, unknown>; errors: RowError[] } {
  const values: Record<string, unknown> = {};
  const errors: RowError[] = [];
  for (const fd of fields) {
    const v = raw[fd.name];
    const empty = v === undefined || v === null || String(v).trim() === "";
    if (empty) {
      if (fd.required) errors.push(err(fd.name, "required"));
      values[fd.name] = null;
      continue;
    }
    const s = String(v).trim();
    if (fd.value_type === "date") {
      const d = parseVnDate(s);
      if (!d) errors.push(err(fd.name, "date_format", { value: s }));
      values[fd.name] = d ?? s;
    } else if (["number", "money"].includes(fd.value_type)) {
      const n = parseVnNumber(v);
      if (n === null) errors.push(err(fd.name, "number_format", { value: s }));
      values[fd.name] = n ?? s;
    } else if (fd.value_type === "enum") {
      if (fd.enum && !fd.enum.includes(s)) errors.push(err(fd.name, "in", { allowed: fd.enum.join(", ") }));
      values[fd.name] = s;
    } else {
      if (fd.master_ref && !masterKnown(fd.master_ref, s)) errors.push(err(fd.name, "master_not_found", { value: s }));
      values[fd.name] = s;
    }
  }
  return { values, errors };
}

