"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { AlertTriangle, Lock, RefreshCw, Eye, CheckCircle2 } from "lucide-react";
import type { ReviewQueueItemOut, RoleCode } from "@aureon/shared-types";
import { AIStateBadge } from "@/components/ai/AIStateBadge";
import { MaskedValue } from "@/components/metric/MaskedValue";
import { cn } from "@/lib/utils";

export interface QueueTableProps {
  items: ReviewQueueItemOut[];
  role: RoleCode;
  onRetry?: (documentId: string) => void;
  className?: string;
}

function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, "0");
    const mins = String(d.getMinutes()).padStart(2, "0");
    return `${day}/${month}/${year} ${hours}:${mins}`;
  } catch {
    return isoString;
  }
}

export function QueueTable({ items, role, onRetry, className }: QueueTableProps) {
  const t = useTranslations("inbox");
  const tDocTypes = useTranslations("inbox.docTypes");
  const tStatuses = useTranslations("inbox.statuses");

  const canReviewDocument = (item: ReviewQueueItemOut): boolean => {
    const { document } = item;
    if (document.status === "FAILED") return false;

    // ROLE-01 (CEO): Read-only view, cannot open/review documents containing personal salary (02 §3.4)
    if (role === "ROLE-01") {
      return !document.contains_salary;
    }

    // ROLE-05 (Reviewer): Can review all documents
    if (role === "ROLE-05") {
      return true;
    }

    // ROLE-02 (CFO): Only FIN pillar
    if (role === "ROLE-02") {
      return document.pillars.includes("FIN");
    }

    // ROLE-04 (HR): Only HR pillar
    if (role === "ROLE-04") {
      return document.pillars.includes("HR");
    }

    return false;
  };

  return (
    <div className={cn("overflow-x-auto rounded-lg border border-border bg-card", className)}>
      <table className="w-full text-left text-sm" aria-label={t("title")}>
        <thead className="border-b border-border bg-muted/50 text-xs font-medium text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-3">{t("table.filename")}</th>
            <th scope="col" className="px-3 py-3">{t("table.docType")}</th>
            <th scope="col" className="px-2 py-3">{t("table.pillar")}</th>
            <th scope="col" className="px-3 py-3">{t("table.status")}</th>
            <th scope="col" className="px-3 py-3 text-right">{t("table.confidence")}</th>
            <th scope="col" className="px-3 py-3 text-right">{t("table.fieldsToCheck")}</th>
            <th scope="col" className="px-3 py-3">{t("table.uploader")}</th>
            <th scope="col" className="px-3 py-3">{t("table.uploadedAt")}</th>
            <th scope="col" className="px-4 py-3 text-right">{t("table.actions")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((item) => {
            const doc = item.document;
            const hasConflict = item.has_conflict;
            const isLocked = Boolean(item.locked_by);
            const isFailed = doc.status === "FAILED";
            const isSalaryMasked = role === "ROLE-01" && doc.contains_salary;
            const canReview = canReviewDocument(item);

            let confidenceColorClass = "text-muted-foreground";
            if (item.avg_confidence !== null && item.avg_confidence !== undefined) {
              if (item.avg_confidence >= 0.90) {
                confidenceColorClass = "text-emerald-600 dark:text-emerald-400 font-medium";
              } else if (item.avg_confidence >= 0.70) {
                confidenceColorClass = "text-amber-600 dark:text-amber-400 font-medium";
              } else {
                confidenceColorClass = "text-rose-600 dark:text-rose-400 font-medium";
              }
            }

            return (
              <tr
                key={doc.id}
                className={cn(
                  "hover:bg-muted/30 transition-colors",
                  hasConflict && "bg-amber-500/5",
                  isLocked && "opacity-90",
                )}
                data-testid={`queue-row-${doc.id}`}
              >
                {/* File name & conflict */}
                <td className="px-4 py-3 font-medium text-foreground">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-1.5">
                      {hasConflict && (
                        <span
                          title={t("table.unresolvedConflict")}
                          className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400"
                        >
                          <AlertTriangle className="h-4 w-4 shrink-0" aria-label={t("table.unresolvedConflict")} />
                        </span>
                      )}
                      {canReview && !isFailed ? (
                        <Link
                          href={`/review/${doc.id}`}
                          className="hover:text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 rounded"
                        >
                          {doc.original_filename}
                        </Link>
                      ) : (
                        <span className={cn(isSalaryMasked && "text-muted-foreground")}>
                          {doc.original_filename}
                        </span>
                      )}
                    </div>
                    {item.routing_reason && (
                      <span className="text-xs text-muted-foreground truncate max-w-xs">
                        {item.routing_reason}
                      </span>
                    )}
                  </div>
                </td>

                {/* Doc type */}
                <td className="px-3 py-3 text-muted-foreground text-xs whitespace-nowrap">
                  {doc.doc_type ? tDocTypes(doc.doc_type) : "—"}
                </td>

                {/* Pillars */}
                <td className="px-2 py-3">
                  <div className="flex flex-wrap gap-1">
                    {doc.pillars.map((p) => (
                      <span
                        key={p}
                        className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-semibold bg-secondary text-secondary-foreground"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </td>

                {/* Status + AI badge */}
                <td className="px-3 py-3">
                  <div className="flex flex-col gap-1 items-start">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                        doc.status === "NEEDS_REVIEW" && "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
                        doc.status === "IN_REVIEW" && "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
                        doc.status === "FAILED" && "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
                        doc.status === "COMMITTED" && "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
                      )}
                    >
                      {tStatuses(doc.status)}
                    </span>
                    <AIStateBadge level={doc.ai_state || "L2"} />
                  </div>
                </td>

                {/* Avg confidence */}
                <td className={cn("px-3 py-3 text-right tabular-nums", confidenceColorClass)}>
                  {item.avg_confidence !== null && item.avg_confidence !== undefined
                    ? `${(item.avg_confidence * 100).toFixed(1)}%`
                    : "—"}
                </td>

                {/* Fields to check */}
                <td className="px-3 py-3 text-right tabular-nums text-muted-foreground">
                  {item.fields_to_check > 0 ? (
                    <span className="font-medium text-foreground">
                      {t("table.fieldsCount", { count: item.fields_to_check })}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>

                {/* Uploader */}
                <td className="px-3 py-3 text-muted-foreground text-xs whitespace-nowrap">
                  {doc.uploaded_by?.full_name || "—"}
                </td>

                {/* Uploaded at */}
                <td className="px-3 py-3 text-muted-foreground text-xs tabular-nums whitespace-nowrap">
                  {formatDate(doc.uploaded_at)}
                </td>

                {/* Actions & Lock */}
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  {isLocked && item.locked_by ? (
                    <div
                      className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400"
                      title={t("table.lockedBy", { name: item.locked_by.full_name })}
                    >
                      <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                      <span>{t("table.lockedBy", { name: item.locked_by.full_name })}</span>
                    </div>
                  ) : isFailed ? (
                    <div className="flex items-center justify-end gap-2">
                      {onRetry && (
                        <button
                          type="button"
                          onClick={() => onRetry(doc.id)}
                          className="inline-flex items-center gap-1 rounded bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground hover:bg-secondary/80 focus:outline-none focus:ring-2 focus:ring-ring"
                          aria-label={`${t("table.retryButton")} ${doc.original_filename}`}
                        >
                          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                          <span>{t("table.retryButton")}</span>
                        </button>
                      )}
                      <Link
                        href={`/documents/${doc.id}`}
                        className="inline-flex items-center gap-1 rounded border border-border px-2.5 py-1 text-xs font-medium text-foreground hover:bg-muted"
                      >
                        {t("table.manualButton")}
                      </Link>
                    </div>
                  ) : isSalaryMasked ? (
                    <div className="inline-flex items-center gap-1">
                      <MaskedValue value={{ masked: true }} />
                    </div>
                  ) : canReview ? (
                    <Link
                      href={`/review/${doc.id}`}
                      className="inline-flex items-center gap-1 rounded bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1"
                      aria-label={`${role === "ROLE-01" ? t("table.viewButton") : t("table.reviewButton")} ${doc.original_filename}`}
                    >
                      {role === "ROLE-01" ? (
                        <>
                          <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                          <span>{t("table.viewButton")}</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                          <span>{t("table.reviewButton")}</span>
                        </>
                      )}
                    </Link>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
