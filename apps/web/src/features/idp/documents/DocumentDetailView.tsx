"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  FileText,
  Clock,
  History,
  CheckCircle2,
  XCircle,
  ExternalLink,
  TrendingUp,
} from "lucide-react";
import type { AIStateLevel, DocumentStatus } from "@aureon/shared-types";
import { AIStateBadge } from "@/components/ai/AIStateBadge";
import { LoadingState } from "@/components/states/LoadingState";
import { ErrorState } from "@/components/states/ErrorState";
import { ForbiddenState } from "@/components/states/ForbiddenState";
import { useAuth } from "@/features/auth/auth-context";
import { getDocumentApi } from "@/features/idp/idp-api";
import { cn } from "@/lib/utils";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                     */
/* -------------------------------------------------------------------------- */

// Statuses that are still being processed → poll EP-25 every few seconds.
const IN_PROGRESS_STATUSES = new Set<DocumentStatus>([
  "UPLOADED",
  "PREPROCESSING",
  "CLASSIFYING",
  "EXTRACTING",
  "VALIDATING",
  "AUTO_APPROVED",
  "APPROVED",
]);

// The backend ai_state field may carry non-autonomy strings (e.g. status
// mirrors); only L0–L3 render as an AI autonomy badge.
function isAiStateLevel(value: string | null): value is AIStateLevel {
  return value === "L0" || value === "L1" || value === "L2" || value === "L3";
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return iso;
  }
}

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
  default: "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/30 dark:text-sky-300 dark:border-sky-900",
};

/* -------------------------------------------------------------------------- */
/* DocumentDetailView                                                          */
/* -------------------------------------------------------------------------- */
export function DocumentDetailView({ documentId }: { documentId: string }) {
  const t = useTranslations("documentDetail");
  const tIdp = useTranslations("idp");
  const { session, isLoading: isAuthLoading } = useAuth();

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["document-detail", documentId],
    queryFn: () => getDocumentApi(documentId, session?.accessToken),
    enabled: !!session?.accessToken,
    retry: 1,
    refetchInterval: (query) => {
      const status = query.state.data?.document.status;
      return status && IN_PROGRESS_STATUSES.has(status) ? 3000 : false;
    },
  });

  if (isAuthLoading || isLoading) {
    return (
      <div className="p-4 sm:p-6">
        <LoadingState rows={6} />
      </div>
    );
  }

  // 403 FORBIDDEN_SCOPE → show forbidden state (document out of role scope).
  const message = error instanceof Error ? error.message : "";
  if (isError && /403|forbidden|scope/i.test(message)) {
    return (
      <div className="p-4 sm:p-6">
        <BackLink label={t("backToList")} />
        <ForbiddenState title={t("forbidden")} />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-4 sm:p-6">
        <BackLink label={t("backToList")} />
        <ErrorState title={t("notFound")} onRetry={() => refetch()} />
      </div>
    );
  }

  const { document: doc, jobs, status_timeline, affected, reviews } = data;
  const isProcessing = IN_PROGRESS_STATUSES.has(doc.status);

  return (
    <div className="flex flex-col gap-5 p-4 sm:p-6" data-testid="document-detail-view">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3">
        <BackLink label={t("backToList")} />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <FileText className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
            <div>
              <h1 className="text-xl font-bold text-foreground">
                {doc.original_filename ??
                  (doc.doc_type
                    ? tIdp(`docTypes.${doc.doc_type}` as Parameters<typeof tIdp>[0])
                    : t("title"))}
              </h1>
              <p className="mt-0.5 font-mono text-xs text-muted-foreground">{doc.id}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium",
                VARIANT_CLASSES[statusVariant(doc.status)],
              )}
            >
              {tIdp(`docStatus.${doc.status}` as Parameters<typeof tIdp>[0])}
            </span>
            {isAiStateLevel(doc.ai_state) && <AIStateBadge level={doc.ai_state} />}
          </div>
        </div>
        {isProcessing && (
          <p
            className="inline-flex w-fit items-center gap-1.5 rounded-md bg-sky-50 px-2.5 py-1 text-xs text-sky-700 dark:bg-sky-950/30 dark:text-sky-300"
            role="status"
          >
            <Clock className="h-3.5 w-3.5 animate-pulse" aria-hidden="true" />
            {t("processing")}
          </p>
        )}
      </div>

      {/* ── Action buttons ──────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2">
        {(doc.status === "NEEDS_REVIEW" || doc.status === "IN_REVIEW") && (
          <Link
            href={`/review/${doc.id}`}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            {t("openReview")}
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        )}
        {doc.kind === "FILE" && (
          <Link
            href={`/documents/${doc.id}/source`}
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted"
          >
            {t("viewSource")}
          </Link>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* ── Metadata ──────────────────────────────────────────── */}
        <section className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold text-foreground">{t("metadata")}</h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <MetaRow label={t("fields.docType")}>
              {doc.doc_type
                ? tIdp(`docTypes.${doc.doc_type}` as Parameters<typeof tIdp>[0])
                : "—"}
            </MetaRow>
            <MetaRow label={t("fields.channel")}>{doc.channel}</MetaRow>
            <MetaRow label={t("fields.pillars")}>
              {doc.pillars.length > 0 ? doc.pillars.join(", ") : "—"}
            </MetaRow>
            <MetaRow label={t("fields.uploader")}>{doc.uploaded_by.full_name}</MetaRow>
            <MetaRow label={t("fields.uploadedAt")}>{formatDateTime(doc.uploaded_at)}</MetaRow>
            {doc.committed_at && (
              <MetaRow label={t("fields.committedAt")}>
                {formatDateTime(doc.committed_at)}
              </MetaRow>
            )}
            {doc.mime_type && <MetaRow label={t("fields.mimeType")}>{doc.mime_type}</MetaRow>}
            {doc.size_bytes != null && (
              <MetaRow label={t("fields.size")}>{formatBytes(doc.size_bytes)}</MetaRow>
            )}
            {doc.page_count != null && (
              <MetaRow label={t("fields.pages")}>{doc.page_count}</MetaRow>
            )}
          </dl>
        </section>

        {/* ── Status timeline ───────────────────────────────────── */}
        <section className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <Clock className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            {t("timeline")}
          </h2>
          {status_timeline.length === 0 ? (
            <p className="text-sm text-muted-foreground">—</p>
          ) : (
            <ol className="relative ml-2 border-l border-border">
              {status_timeline.map((item, i) => (
                <li key={`${item.status}-${i}`} className="mb-3 ml-4 last:mb-0">
                  <span
                    className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full border border-background bg-primary"
                    aria-hidden="true"
                  />
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <span className="text-sm font-medium text-foreground">
                      {tIdp(`docStatus.${item.status}` as Parameters<typeof tIdp>[0])}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(item.at)}
                      {" · "}
                      {t(`actorType.${item.actor_type}` as Parameters<typeof t>[0])}
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        {/* ── Processing jobs ───────────────────────────────────── */}
        <section className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <History className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            {t("jobs")}
          </h2>
          {jobs.length === 0 ? (
            <p className="text-sm text-muted-foreground">—</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {jobs.map((job) => (
                <li
                  key={job.id}
                  className="rounded-md border border-border/60 bg-muted/30 px-3 py-2 text-sm"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <span className="font-medium text-foreground">
                      {t("jobAttempt")} #{job.attempt_no} · {job.status}
                    </span>
                    {job.avg_confidence != null && (
                      <span className="text-xs text-muted-foreground">
                        {t("jobConfidence")}: {(job.avg_confidence * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  {job.routing_decision && (
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {t("jobRouting")}: {job.routing_decision}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* ── Reviews ───────────────────────────────────────────── */}
        <section className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold text-foreground">{t("reviews")}</h2>
          {reviews.length === 0 ? (
            <p className="text-sm text-muted-foreground">—</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {reviews.map((rev, i) => (
                <li
                  key={`${rev.reviewer_full_name}-${i}`}
                  className="flex items-start gap-2 rounded-md border border-border/60 bg-muted/30 px-3 py-2 text-sm"
                >
                  {rev.decision === "APPROVED" || rev.decision === "APPROVE" ? (
                    <CheckCircle2
                      className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500"
                      aria-hidden="true"
                    />
                  ) : rev.decision ? (
                    <XCircle
                      className="mt-0.5 h-4 w-4 shrink-0 text-rose-500"
                      aria-hidden="true"
                    />
                  ) : null}
                  <div>
                    <span className="font-medium text-foreground">{rev.reviewer_full_name}</span>
                    <span className="text-muted-foreground">
                      {rev.decision ? ` · ${rev.decision}` : ""}
                      {rev.reject_reason_code ? ` (${rev.reject_reason_code})` : ""}
                    </span>
                    {rev.decided_at && (
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(rev.decided_at)}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* ── Affected data (P01 drill-through to metrics) ────────── */}
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-foreground">
          <TrendingUp className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          {t("affected")}
        </h2>
        {affected.metric_codes.length === 0 && affected.business_record_ids.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("noAffected")}</p>
        ) : (
          <div className="flex flex-col gap-3 text-sm">
            {affected.metric_codes.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium text-muted-foreground">
                  {t("affectedMetrics")}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {affected.metric_codes.map((code) => (
                    <Link
                      key={code}
                      href={`/dashboard?metric=${encodeURIComponent(code)}`}
                      className="inline-flex items-center gap-1 rounded-md border border-primary/30 bg-primary/5 px-2 py-0.5 font-mono text-xs text-primary hover:bg-primary/10"
                    >
                      {code}
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                    </Link>
                  ))}
                </div>
              </div>
            )}
            {affected.business_record_ids.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium text-muted-foreground">
                  {t("affectedRecords")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {affected.business_record_ids.length}
                </p>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Sub-components                                                              */
/* -------------------------------------------------------------------------- */
function BackLink({ label }: { label: string }) {
  return (
    <Link
      href="/documents"
      className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      {label}
    </Link>
  );
}

function MetaRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-foreground">{children}</dd>
    </>
  );
}
