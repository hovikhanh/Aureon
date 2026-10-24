/**
 * Mock C5 parsing (FR-DC-101, mock-only): the BFF passes file metadata, so `.xlsx` content is the
 * demo file picked by name (`DOC-07` / `kpi` / `okr` → KPI sheet, otherwise the HR roster DOC-06);
 * `.csv` is parsed from text. Limits 5000 rows / 20 sheets / 60 columns → 413 `details.limit`.
 * Header → field mapping by `header_aliases` (the BE uses the classifier LLM; same output shape).
 */
import data from "./capture-data.json";
import { SCHEMA_FIELDS, type FieldDef } from "./capture-schemas";
import { validateValues, type RowError } from "./capture-rules";
import type { MBatch } from "./capture-store";
import { err } from "./capture-out";

export const LIMITS = { rows: 5000, sheets: 20, columns: 60 };
export interface UploadMeta { name: string; size: number; type: string; text?: string }

function parseCsv(text: string): string[][] {
  return text.replace(/\r/g, "").split("\n").filter((l) => l.trim() !== "").map((l) => l.split(l.includes(";") && !l.includes(",") ? ";" : ",").map((c) => c.trim().replace(/^"|"$/g, "")));
}

export function loadSheets(f: UploadMeta): { name: string; rows: string[][] }[] {
  const lower = f.name.toLowerCase();
  if (lower.endsWith(".xls")) throw err(415, "UNSUPPORTED_MEDIA_TYPE", ".xls is not supported, save as .xlsx", { filename: f.name });
  if (!lower.endsWith(".xlsx") && !lower.endsWith(".csv")) throw err(415, "UNSUPPORTED_MEDIA_TYPE", "only .xlsx / .csv can be imported", { filename: f.name });
  let sheets: { name: string; rows: string[][] }[];
  if (lower.endsWith(".csv")) {
    const text = f.text ?? "";
    if (text.includes("\uFFFD")) throw err(422, "VALIDATION_ERROR", "CSV must be UTF-8", { field: "file", reason: "encoding" });
    sheets = [{ name: f.name.replace(/\.csv$/i, ""), rows: parseCsv(text) }];
  } else {
    const src = /doc-07|kpi|okr/.test(lower) ? data.kpi : data.hr;
    sheets = [{ name: src.sheet, rows: src.rows.map((r) => [...r]) }];
  }
  if (sheets.length > LIMITS.sheets) throw err(413, "FILE_TOO_LARGE", "too many sheets", { limit: "sheets", max: LIMITS.sheets });
  for (const s of sheets) {
    if (s.rows.length - 1 > LIMITS.rows) throw err(413, "FILE_TOO_LARGE", "too many rows", { limit: "rows", max: LIMITS.rows });
    if (Math.max(0, ...s.rows.map((r) => r.length)) > LIMITS.columns) throw err(413, "FILE_TOO_LARGE", "too many columns", { limit: "columns", max: LIMITS.columns });
  }
  return sheets;
}

const norm = (s: string) => s.trim().toLowerCase();
export const rowFields = (type: string | null): FieldDef[] => (SCHEMA_FIELDS[type ?? ""] ?? []).filter((f) => f.group === "row");

export function headersOf(b: MBatch): string[] {
  const s = b.sheets.find((x) => x.name === b.sheet) ?? b.sheets[0]!;
  return (s.rows[b.header_row - 1] ?? []).map((h) => String(h ?? "").trim());
}

export function suggest(headers: readonly string[]): { code: string; confidence: number } | null {
  let best: { code: string; confidence: number } | null = null;
  for (const code of Object.keys(SCHEMA_FIELDS)) {
    const hits = headers.filter((h) => rowFields(code).some((f) => f.header_aliases.some((a) => norm(a) === norm(h)))).length;
    const conf = headers.length ? Math.round((hits / headers.length) * 100) / 100 : 0;
    if (hits > 0 && (!best || conf > best.confidence)) best = { code, confidence: conf };
  }
  return best;
}

export function autoMap(type: string | null, headers: readonly string[]): MBatch["mapping"] {
  return Object.fromEntries(headers.filter(Boolean).map((h) => {
    const f = rowFields(type).find((x) => x.header_aliases.some((a) => norm(a) === norm(h)));
    return [h, { field: f?.name ?? null, confidence: f ? 0.92 : 0 }];
  }));
}

export interface EvalRow { row_number: number; values: Record<string, unknown>; errors: RowError[] }
/** Data rows under the header (blank rows skipped) → validated values keyed by field. */
export function evaluate(b: MBatch): EvalRow[] {
  const s = b.sheets.find((x) => x.name === b.sheet) ?? b.sheets[0]!;
  const headers = headersOf(b);
  const defs = rowFields(b.document_type).filter((f) => Object.values(b.mapping).some((m) => m.field === f.name) || f.required);
  const out: EvalRow[] = [];
  s.rows.forEach((r, i) => {
    if (i < b.header_row || r.every((c) => String(c ?? "").trim() === "")) return;
    const raw: Record<string, unknown> = {};
    headers.forEach((h, j) => { const fld = b.mapping[h]?.field; if (fld) raw[fld] = r[j]; });
    const v = validateValues(defs, raw);
    out.push({ row_number: i + 1, values: v.values, errors: v.errors });
  });
  return out;
}

export const unmappedRequired = (type: string | null, mapping: MBatch["mapping"]) =>
  rowFields(type).filter((f) => f.required && !Object.values(mapping).some((m) => m.field === f.name)).map((f) => f.name);
