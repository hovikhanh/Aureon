/**
 * Mock D03 Data Capture store (M1.5, 10 §7.2.4) — documents of every channel (C1/C3/C5),
 * extracted fields (header + `row_index` rows), import batches, document actions, lineage,
 * doc types / schemas / rules / incidents. One shared store per process (like `work-store.ts`).
 */
import { SNAPSHOT, mockId } from "./fixtures";
import type { FieldDef } from "./capture-schemas";
import { seedCapture } from "./capture-seed";

export interface MField {
  id: string; field_name: string; row_index: number | null; value_type: string; ai_value: unknown; corrected_value: unknown;
  confidence: number; is_critical: boolean; is_confirmed: boolean; sensitivity_level: number; source_location: Record<string, unknown>;
  validation: { rule: string; status: "pass" | "fail" | "warn"; message: string }[]; correction_reason: string | null;
}
export interface MResultRef { schema: string; table: string; id: string; reused: boolean; snapshot?: Record<string, unknown> }
export interface MAction { seq: number; action_name: string; result_refs: MResultRef[]; status: "applied" | "reverted"; reverted_at: string | null }
export interface MDoc {
  id: string; version: number; original_filename: string | null; mime_type: string | null; size_bytes: number | null; page_count: number | null;
  channel: "C1" | "C3" | "C5"; kind: "FILE" | "MANUAL"; status: string; status_reason: string | null; pillars: string[]; sensitivity_level: number;
  submitted_at: string; document_type: string | null; committed_at: string | null; undo_deadline: string | null; rolled_back_at: string | null;
  submitted_by: string; submitted_by_name: string; department_id: string; assigned_to: string | null; approved_by: string | null;
  locked_by: string | null; locked_until: string | null; batch_id: string | null; sheet_name: string | null; schema_version: number;
  fields: MField[]; actions: MAction[]; document_confidence: number | null; routing_reasons: string[];
}
export interface MBatch {
  id: string; document_id: string; version: number; submitted_by: string; status: "VALIDATING" | "SUBMITTED"; filename: string;
  sheets: { name: string; rows: string[][] }[]; sheet: string; header_row: number; document_type: string | null; suggested: { code: string; confidence: number } | null;
  mapping: Record<string, { field: string | null; confidence: number }>;
}
export interface MLineage { entity: string; record_id: string; document_id: string; action_name: string; row_index: number | null; field_name: string; target_column: string; raw_text: string; confidence: number; committed_at: string; revoked_at: string | null; sensitivity_level: number }
export interface MDocType { id: string; version: number; code: string; name_vi: string; name_en: string; pillars: string[]; is_active: boolean; channels_supported: string[]; classifier_keywords: string[] }
export interface MSchema { id: string; version: number; document_type: string; schema_version: number; status: "draft" | "published" | "retired"; fields: FieldDef[]; thresholds: { classification_confidence_min: number; required_field_min: number }; action_names: string[]; published_at: string | null }
export interface MRule { id: string; version: number; extraction_schema_id: string | null; code: string; kind: string; expression: Record<string, unknown>; severity: string; tolerance: number | null; is_active: boolean }
export interface MIncident { id: string; source_document_id: string; extracted_field_id: string | null; field_name: string; is_critical: boolean; detected_by: "review" | "post_commit" | "undo"; undetected: boolean; target_table: string | null; target_id: string | null; description: string; reported_by: string; reported_at: string }
export interface CaptureStore { docs: MDoc[]; batches: MBatch[]; lineage: MLineage[]; docTypes: MDocType[]; schemas: MSchema[]; rules: MRule[]; incidents: MIncident[]; idem: Map<string, string>; seq: number }

const G = globalThis as typeof globalThis & { __aureonMockCapture?: CaptureStore | null };
export function captureStore(): CaptureStore {
  G.__aureonMockCapture ??= seedCapture();
  return G.__aureonMockCapture;
}
export function resetCaptureStore(): void {
  G.__aureonMockCapture = null;
}
export const newCaptureId = (kind: string): string => mockId(kind, `new-${++captureStore().seq}-${Date.now()}`);
export const nowIso = (): string => new Date().toISOString();
export const UNDO_DAYS = 7;
export const addDays = (iso: string, days: number) => new Date(Date.parse(iso) + days * 86_400_000).toISOString();

export const userId = (email: string) => mockId("user", email);
const userBy = (email: string) => SNAPSHOT.users.find((u) => u.email === email)!;
export const nameOfUser = (sub: string) => SNAPSHOT.users.find((u) => mockId("user", u.email) === sub)?.full_name ?? null;
export const deptOfUser = (email: string) => mockId("department", userBy(email).department);
export const REVIEWER = "reviewer@abc.demo";

/** EP-DC-13 status groups. */
export const GROUPS: Record<string, readonly string[]> = {
  processing: ["UPLOADED", "PREPROCESSING", "CLASSIFYING", "EXTRACTING", "VALIDATING"],
  needs_review: ["NEEDS_REVIEW", "IN_REVIEW"], approved: ["APPROVED"], committed: ["AUTO_APPROVED", "COMMITTED"],
  rejected: ["REJECTED"], failed: ["FAILED", "DUPLICATE"], rolled_back: ["ROLLED_BACK"],
};
export const groupOf = (status: string) => Object.entries(GROUPS).find(([, s]) => s.includes(status))?.[0] ?? null;

