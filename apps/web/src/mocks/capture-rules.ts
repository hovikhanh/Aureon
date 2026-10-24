/**
 * Mock row validator for C1/C5 (mirror of `idp/services/validator.py` ops `required` / `in` +
 * type checks). Row errors use `{field, rule_code, message_key, params}` (RowErrorOut); the FE
 * renders `capture.errors.<rule_code>`.
 */
import { SNAPSHOT } from "./fixtures";
import type { FieldDef } from "./capture-schemas";

export interface RowError { field: string | null; rule_code: string; message_key: string; params: Record<string, unknown> }

/** BE `capture_common.row_error`: UPPERCASE rule code + `idp.import.error.<lower>` message key. */
const err = (field: string, rule_code: string, params: Record<string, unknown> = {}): RowError => ({ field, rule_code, message_key: `idp.import.error.${rule_code.toLowerCase()}`, params });

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
const EMP_CODES = new Set(SNAPSHOT.employees.map((e) => e.code));
const KPI_CODES = new Set(((SNAPSHOT as unknown as { kpis?: { code: string }[] }).kpis ?? []).map((k) => k.code));
/** `master_ref` lookups (BE `_master_exists`): department / employee / KPI codes of the seed. */
export function masterKnown(ref: string, value: string, extra: ReadonlySet<string> = new Set()): boolean {
  if (extra.has(value)) return true;
  if (ref === "hr.department_code") return DEPT_CODES.has(value);
  if (ref === "hr.employee_code") return EMP_CODES.has(value);
  if (ref === "execution.kpi_code") return KPI_CODES.has(value);
  return true;
}
/** A field whose master_ref is the natural key of its own ACT (BE `_creates_master`): new codes are created, not looked up. */
export const createsMaster = (fd: FieldDef) => !!fd.master_ref && ["code", "employee_code"].includes(fd.target?.param ?? "");

/**
 * Validate + normalise one row (or the header values of a C1 form) like BE `normalize` +
 * `required_errors` + `_check_masters`; `inFile` = master codes created by the same file
 * (`null` = skip the master pass; C5 runs it after every row is normalised).
 */
export function validateValues(fields: readonly FieldDef[], raw: Record<string, unknown>, inFile: Record<string, ReadonlySet<string>> | null = {}): { values: Record<string, unknown>; errors: RowError[] } {
  const values: Record<string, unknown> = {};
  const errors: RowError[] = [];
  for (const fd of fields) {
    const v = raw[fd.name];
    const empty = v === undefined || v === null || String(v).trim() === "";
    if (empty) {
      if (fd.required) errors.push(err(fd.name, "REQUIRED"));
      values[fd.name] = null;
      continue;
    }
    const s = String(v).trim();
    if (fd.value_type === "date") {
      const d = parseVnDate(s);
      if (!d) errors.push(err(fd.name, "DATE_FORMAT", { value: s }));
      values[fd.name] = d;
    } else if (["number", "money", "percent"].includes(fd.value_type)) {
      const n = parseVnNumber(v);
      if (n === null) errors.push(err(fd.name, "NUMBER_FORMAT", { value: s }));
      values[fd.name] = n === null ? null : fd.value_type === "money" ? Math.round(n) : n;
    } else if (fd.value_type === "enum" && fd.enum) {
      const hit = fd.enum.find((e) => e.toLowerCase() === s.toLowerCase());
      if (!hit) errors.push(err(fd.name, "ENUM", { value: s, allowed: fd.enum }));
      values[fd.name] = hit ?? null;
    } else {
      values[fd.name] = s;
    }
  }
  if (inFile !== null) errors.push(...masterErrors(fields, values, inFile));
  return { values, errors };
}

/** `MASTER_NOT_FOUND` for referenced codes unknown to the seed and not created in the same file. */
export function masterErrors(fields: readonly FieldDef[], values: Record<string, unknown>, inFile: Record<string, ReadonlySet<string>> = {}): RowError[] {
  return fields.flatMap((fd) => {
    const code = values[fd.name];
    if (!fd.master_ref || createsMaster(fd) || code === null || code === undefined) return [];
    return masterKnown(fd.master_ref, String(code), inFile[fd.master_ref]) ? [] : [err(fd.name, "MASTER_NOT_FOUND", { value: String(code) })];
  });
}
