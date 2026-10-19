"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Eye, Undo2, FileText, Lock } from "lucide-react";
import type { DocumentOut, RoleCode } from "@aureon/shared-types";
import { AIStateBadge } from "@/components/ai/AIStateBadge";
import { MaskedValue } from "@/components/metric/MaskedValue";
import { cn } from "@/lib/utils";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                     */
/* -------------------------------------------------------------------------- */
function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return iso;
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Virtual documents (C1 MANUAL, C2 TRANSCRIPT) have no original_filename.
 * Synthesize a readable label from the doc type and kind so the table never
 * renders an empty cell (05 §4.3, 06 §4.4).
 */
function displayLabel(
  doc: DocumentOut,
  t: ReturnType<typeof useTranslations>,
): string {
  const kindText = t(`kindLabel.${doc.kind}` as Parameters<typeof t>[0]);
  return doc.doc_type ? `${kindText} · ${doc.doc_type}` : kindText;
}

type StatusVariant = "default" | "success" | "warning" | "danger" | "muted";

function statusVariant(status: string): StatusVariant {
  switch (status) {
    case "COMMITTED":
    case "AUTO_APPROVED":
    case "APPROVED":
      return "success";
    case "NEEDS_REVIEW":
    case "IN_REVIEW":
      return "warning";
    case "FAILED":
    case "REJECTED":
      return "danger";
    case "ROLLED_BACK":
    case "DUPLICATE":
      return "muted";
    default:
      return "default";
  }
}

const VARIANT_CLASSES: Record<StatusVariant, string> = {
  success:
    "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-900",
  warning:
    "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:border-amber-900",
  danger:
    "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:border-rose-900",
  muted: "bg-muted text-muted-foreground border-border",
  default:
    "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/30 dark:text-blue-300 dark:border-blue-900",
};

/* -------------------------------------------------------------------------- */
/* Component                                                                   */
/* -------------------------------------------------------------------------- */
export interface DocumentsTableProps {
  documents: DocumentOut[];
  role: RoleCode;
  onUndo?: (documentId: string) => void;
  className?: string;
}

export function DocumentsTable({ documents, role, onUndo, className }: DocumentsTableProps) {
  const t = useTranslations("documents.table");
  const tIdp = useTranslations("idp");

  const canViewSalary = role === "ROLE-04" || role === "ROLE-05";

  return (
    <div className={cn("overflow-x-auto rounded-lg border border-border bg-card", className)}>
      <table className="w-full min-w-[900px] text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <th className="px-4 py-3">{t("filename")}</th>
            <th className="px-4 py-3 hidden md:table-cell">{t("docType")}</th>
            <th className="px-4 py-3 hidden lg:table-cell">{t("pillar")}</th>
            <th className="px-4 py-3 hidden md:table-cell">{t("channel")}</th>
            <th className="px-4 py-3">{t("status")}</th>
            <th className="px-4 py-3 hidden lg:table-cell">{t("uploader")}</th>
            <th className="px-4 py-3 hidden xl:table-cell">{t("uploadedAt")}</th>
            <th className="px-4 py-3 text-right">{t("actions")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {documents.map((doc) => {
            const isSalaryRestricted = doc.contains_salary && !canViewSalary;
            const canUndo =
              doc.status === "COMMITTED" &&
              doc.undo_deadline != null &&
              new Date(doc.undo_deadline) > new Date() &&
              role !== "ROLE-01";

            return (
              <tr
                key={doc.id}
                data-testid={`doc-row-${doc.id}`}
                className="group transition-colors hover:bg-muted/30"
              >
                {/* Filename */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <FileText
                      className="h-4 w-4 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      {isSalaryRestricted ? (
                        <span className="flex items-center gap-1.5 font-medium text-foreground">
                          <Lock className="h-3.5 w-3.5 text-amber-500" aria-hidden="true" />
                          <MaskedValue value={{ masked: true }} />
                        </span>
                      ) : (
                        <span className="font-medium text-foreground line-clamp-1">
                          {doc.original_filename ?? displayLabel(doc, t)}
                        </span>
                      )}
                      <span className="mt-0.5 block text-[11px] text-muted-foreground">
                        {doc.size_bytes != null
                          ? formatBytes(doc.size_bytes)
                          : t(`kindLabel.${doc.kind}` as Parameters<typeof t>[0])}
                        {doc.page_count != null && doc.page_count > 1 && ` · ${doc.page_count}p`}
                      </span>
                    </div>
                    {doc.ai_state && (
                      <AIStateBadge
                        level={doc.ai_state}
                        className="shrink-0"
                        aria-label={`AI ${doc.ai_state}`}
                      />
                    )}
                  </div>
                </td>

                {/* Doc type */}
                <td className="px-4 py-3 hidden md:table-cell">
                  <span className="text-xs text-muted-foreground">
                    {doc.doc_type
                      ? tIdp(`docTypes.${doc.doc_type}` as Parameters<typeof tIdp>[0])
                      : "—"}
                  </span>
                </td>

                {/* Pillar */}
                <td className="px-4 py-3 hidden lg:table-cell">
                  <div className="flex flex-wrap gap-1">
                    {doc.pillars.map((p) => (
                      <span
                        key={p}
                        className="inline-block rounded-full bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground"
                      >
                        {tIdp(`pillars.${p}` as Parameters<typeof tIdp>[0])}
                      </span>
                    ))}
                  </div>
                </td>

                {/* Channel */}
                <td className="px-4 py-3 hidden md:table-cell">
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-mono text-muted-foreground">
                    {doc.channel}
                  </span>
                </td>

                {/* Status */}
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "inline-block rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
                      VARIANT_CLASSES[statusVariant(doc.status)],
                    )}
                    data-testid={`status-badge-${doc.id}`}
                  >
                    {tIdp(`docStatus.${doc.status}` as Parameters<typeof tIdp>[0])}
                  </span>
                  {doc.status === "FAILED" && doc.status_reason && (
                    <p
                      className="mt-0.5 text-[10px] text-rose-600 line-clamp-1"
                      title={doc.status_reason}
                    >
                      {doc.status_reason}
                    </p>
                  )}
                </td>

                {/* Uploader */}
                <td className="px-4 py-3 hidden lg:table-cell">
                  <span className="text-xs text-muted-foreground">
                    {doc.uploaded_by.full_name}
                  </span>
                </td>

                {/* Uploaded at */}
                <td className="px-4 py-3 hidden xl:table-cell">
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {formatDate(doc.uploaded_at)}
                  </span>
                </td>

                {/* Actions */}
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    {isSalaryRestricted ? (
                      <span
                        className="text-[11px] text-amber-600"
                        title={t("salaryRestricted")}
                      >
                        <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                      </span>
                    ) : (
                      <Link
                        href={`/documents/${doc.id}`}
                        className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        aria-label={t("viewDetail")}
                      >
                        <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                        <span className="hidden sm:inline">{t("viewDetail")}</span>
                      </Link>
                    )}
                    {canUndo && onUndo && (
                      <button
                        type="button"
                        onClick={() => onUndo(doc.id)}
                        className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium text-amber-600 hover:bg-amber-50 focus:outline-none focus:ring-2 focus:ring-amber-400 dark:hover:bg-amber-950/30"
                        aria-label={t("undo")}
                        data-testid={`undo-btn-${doc.id}`}
                      >
                        <Undo2 className="h-3.5 w-3.5" aria-hidden="true" />
                        <span className="hidden sm:inline">{t("undo")}</span>
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
