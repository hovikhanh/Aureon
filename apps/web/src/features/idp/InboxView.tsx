"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  FileText,
  Clock,
  CheckCircle,
  AlertOctagon,
  Filter,
  Search,
} from "lucide-react";
import type {
  DocType,
  DocumentStatus,
  Pillar,
  ReviewQueueCountsOut,
  ReviewQueueItemOut,
  RoleCode,
} from "@aureon/shared-types";
import { LoadingState, EmptyState, ErrorState, ForbiddenState } from "@/components/states";
import { QueueTable } from "./QueueTable";
import type { ConfidenceFilter, QueueFiltersState } from "./types";

export interface InboxViewProps {
  items: ReviewQueueItemOut[];
  counts: ReviewQueueCountsOut;
  role: RoleCode;
  isLoading?: boolean;
  isError?: boolean;
  isStale?: boolean;
  onRetry?: () => void;
  onItemRetry?: (documentId: string) => void;
}

const DEFAULT_FILTERS: QueueFiltersState = {
  pillar: "ALL",
  docType: "ALL",
  status: "ALL",
  confidence: "ALL",
  batchId: "",
  hasConflictOnly: false,
};

export function InboxView({
  items,
  counts,
  role,
  isLoading = false,
  isError = false,
  isStale = false,
  onRetry,
  onItemRetry,
}: InboxViewProps) {
  const t = useTranslations("inbox");
  const [filters, setFilters] = useState<QueueFiltersState>(DEFAULT_FILTERS);

  // Filter items based on active filter state
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const doc = item.document;

      // Filter by pillar
      if (filters.pillar !== "ALL" && !doc.pillars.includes(filters.pillar)) {
        return false;
      }

      // Filter by doc type
      if (filters.docType !== "ALL" && doc.doc_type !== filters.docType) {
        return false;
      }

      // Filter by status
      if (filters.status !== "ALL" && doc.status !== filters.status) {
        return false;
      }

      // Filter by confidence
      if (filters.confidence !== "ALL") {
        if (item.avg_confidence === null || item.avg_confidence === undefined) {
          if (filters.confidence !== "LOW") return false;
        } else if (filters.confidence === "HIGH" && item.avg_confidence < 0.90) {
          return false;
        } else if (
          filters.confidence === "MEDIUM" &&
          (item.avg_confidence < 0.70 || item.avg_confidence >= 0.90)
        ) {
          return false;
        } else if (filters.confidence === "LOW" && item.avg_confidence >= 0.70) {
          return false;
        }
      }

      // Filter by batch ID
      if (
        filters.batchId.trim() !== "" &&
        (!doc.batch_id || !doc.batch_id.toLowerCase().includes(filters.batchId.trim().toLowerCase()))
      ) {
        return false;
      }

      // Filter by conflict
      if (filters.hasConflictOnly && !item.has_conflict) {
        return false;
      }

      return true;
    });
  }, [items, filters]);

  // ROLE-03 (Sales Director) has no access to IDP Review Queue (02 §3.4)
  if (role === "ROLE-03") {
    return (
      <div className="p-6">
        <ForbiddenState
          title={t("forbidden.title")}
          description={t("forbidden.description")}
          action={
            <Link
              href="/dashboard"
              className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              {t("forbidden.backToDashboard")}
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {t("title")}
        </h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <FileText className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">{t("stats.total")}</p>
              <p className="text-2xl font-bold tabular-nums text-foreground">{counts.total}</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
              <Clock className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">{t("stats.needsReview")}</p>
              <p className="text-2xl font-bold tabular-nums text-blue-700 dark:text-blue-300">
                {counts.needs_review}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
              <CheckCircle className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">{t("stats.inReview")}</p>
              <p className="text-2xl font-bold tabular-nums text-purple-700 dark:text-purple-300">
                {counts.in_review}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
              <AlertOctagon className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">{t("stats.failed")}</p>
              <p className="text-2xl font-bold tabular-nums text-red-700 dark:text-red-300">
                {counts.failed}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border bg-card p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <Filter className="h-4 w-4" aria-hidden="true" />
            <span>{t("filters.pillar")}:</span>
          </div>

          {/* Pillar filter */}
          <select
            value={filters.pillar}
            onChange={(e) =>
              setFilters((prev) => ({ ...prev, pillar: e.target.value as Pillar | "ALL" }))
            }
            className="h-8 rounded-md border border-input bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={t("filters.pillar")}
          >
            <option value="ALL">{t("filters.pillarAll")}</option>
            <option value="FIN">{t("pillars.FIN")}</option>
            <option value="CUS">{t("pillars.CUS")}</option>
            <option value="OPS">{t("pillars.OPS")}</option>
            <option value="HR">{t("pillars.HR")}</option>
          </select>

          {/* DocType filter */}
          <select
            value={filters.docType}
            onChange={(e) =>
              setFilters((prev) => ({ ...prev, docType: e.target.value as DocType | "ALL" }))
            }
            className="h-8 rounded-md border border-input bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={t("filters.docType")}
          >
            <option value="ALL">{t("filters.docTypeAll")}</option>
            <option value="INVOICE">{t("docTypes.INVOICE")}</option>
            <option value="SALES_REPORT">{t("docTypes.SALES_REPORT")}</option>
            <option value="KPI_OKR">{t("docTypes.KPI_OKR")}</option>
            <option value="MEETING_MINUTES">{t("docTypes.MEETING_MINUTES")}</option>
            <option value="FINANCIAL_REPORT">{t("docTypes.FINANCIAL_REPORT")}</option>
            <option value="CONTRACT">{t("docTypes.CONTRACT")}</option>
            <option value="EMPLOYEE_LIST">{t("docTypes.EMPLOYEE_LIST")}</option>
            <option value="OTHER">{t("docTypes.OTHER")}</option>
          </select>

          {/* Status filter */}
          <select
            value={filters.status}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                status: e.target.value as DocumentStatus | "ALL",
              }))
            }
            className="h-8 rounded-md border border-input bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={t("filters.status")}
          >
            <option value="ALL">{t("filters.statusAll")}</option>
            <option value="NEEDS_REVIEW">{t("statuses.NEEDS_REVIEW")}</option>
            <option value="IN_REVIEW">{t("statuses.IN_REVIEW")}</option>
            <option value="FAILED">{t("statuses.FAILED")}</option>
          </select>

          {/* Confidence filter */}
          <select
            value={filters.confidence}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                confidence: e.target.value as ConfidenceFilter,
              }))
            }
            className="h-8 rounded-md border border-input bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={t("filters.confidence")}
          >
            <option value="ALL">{t("filters.confidenceAll")}</option>
            <option value="HIGH">{t("filters.confidenceHigh")}</option>
            <option value="MEDIUM">{t("filters.confidenceMedium")}</option>
            <option value="LOW">{t("filters.confidenceLow")}</option>
          </select>

          {/* Conflict only checkbox */}
          <label className="flex items-center gap-1.5 text-xs text-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={filters.hasConflictOnly}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, hasConflictOnly: e.target.checked }))
              }
              className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
            />
            <span>{t("table.unresolvedConflict")}</span>
          </label>
        </div>

        {/* Batch search */}
        <div className="relative flex items-center">
          <Search className="absolute left-2.5 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder={t("filters.batchPlaceholder")}
            value={filters.batchId}
            onChange={(e) => setFilters((prev) => ({ ...prev, batchId: e.target.value }))}
            className="h-8 w-44 rounded-md border border-input bg-background pl-8 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={t("filters.batch")}
          />
        </div>
      </div>

      {/* Main Content States */}
      {isLoading ? (
        <LoadingState rows={8} label={t("loading.label")} />
      ) : isError && !filteredItems.length ? (
        <ErrorState
          title={t("error.title")}
          description={t("error.description")}
          onRetry={onRetry}
        />
      ) : filteredItems.length === 0 ? (
        <EmptyState
          title={t("empty.title")}
          description={t("empty.description")}
          action={
            <Link
              href="/documents"
              className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              {t("empty.action")}
            </Link>
          }
        />
      ) : (
        <div className="flex flex-col gap-2">
          {isStale && (
            <div className="rounded-md bg-amber-500/10 border border-amber-500/20 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
              {t("error.stale")}
            </div>
          )}
          <QueueTable
            items={filteredItems}
            role={role}
            onRetry={onItemRetry}
          />
        </div>
      )}
    </div>
  );
}
