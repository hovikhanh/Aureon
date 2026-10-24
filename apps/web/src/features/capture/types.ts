/**
 * D03 Capture DTOs (10 §7.2.4) — re-exported from the generated OpenAPI types, plus the
 * R-DEC-60bis `version` on DocumentOut / DocumentTypeOut (optional until shared-types regenerate).
 */
import type { Api } from "@aureon/shared-types";

export type CaptureDocument = Api.DocumentOut & { version?: number };
export type InboxItem = Omit<Api.InboxItemOut, "document"> & { document: CaptureDocument };
export type DocumentType = Api.DocumentTypeOut & { version?: number };
export type FormOut = Api.FormOut;
export type FormField = Api.FormFieldOut;
export type ImportPreview = Api.ImportPreviewOut;
export type ImportRow = Api.ImportRowOut;
export type RowError = Api.RowErrorOut;
export type DocumentAction = Api.DocumentActionOut;
export type LineageOut = Api.LineageOut;
export type LineageLink = Api.LineageLinkOut;
export type SourceView = Api.SourceViewOut;
export type ExtractionSchema = Api.ExtractionSchemaOut;
export type SchemaField = Api.SchemaFieldDef;
export type ValidationRule = Api.ValidationRuleOut;
export type Incident = Api.IncidentOut;
export interface ActionRef { action_name: string; ids: string[]; table?: string }
export interface CommitOut { document: CaptureDocument; actions: ActionRef[]; undo_deadline: string | null }
export interface ManualOut { document: CaptureDocument; status: string; actions: ActionRef[]; validation_errors: Record<string, unknown>[]; undo_deadline: string | null }
export interface UndoOut { document: CaptureDocument; reverted_actions: ActionRef[] }

export const INBOX_GROUPS = ["processing", "needs_review", "approved", "committed", "rejected", "failed", "rolled_back"] as const;
export type InboxGroup = (typeof INBOX_GROUPS)[number];
export const CHANNELS = ["C1", "C3", "C5"] as const;
export const UNDO_REASONS = ["mistake", "critical_field_wrong", "duplicate", "other"] as const;
export type UndoReason = (typeof UNDO_REASONS)[number];
/** Statuses still moving through the pipeline — the inbox polls while any is visible. */
export const ACTIVE_STATUSES = ["UPLOADED", "PREPROCESSING", "CLASSIFYING", "EXTRACTING", "VALIDATING"];
/** Masked level-4 value (CLAUDE §5.3). */
export const isMasked = (v: unknown): v is { masked: true } => typeof v === "object" && v !== null && (v as { masked?: unknown }).masked === true;
