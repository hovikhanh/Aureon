"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Search, Upload, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { DocumentOut, DocumentStatus, DocType, Pillar, RoleCode } from "@aureon/shared-types";
import { LoadingState } from "@/components/states";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { useAuth } from "@/features/auth/auth-context";
import { getDocumentsApi } from "@/features/idp/idp-api";
import { DocumentsTable } from "./DocumentsTable";
import { DEMO_DOCUMENTS } from "./demo-fixtures";

/* -------------------------------------------------------------------------- */
/* Filter types                                                                */
/* -------------------------------------------------------------------------- */
type FilterStatus = DocumentStatus | "ALL";
type FilterPillar = Pillar | "ALL";
type FilterDocType = DocType | "ALL";

const PILLAR_OPTIONS: FilterPillar[] = ["ALL", "FIN", "CUS", "OPS", "HR"];
const DOC_TYPE_OPTIONS: FilterDocType[] = [
  "ALL", "INVOICE", "SALES_REPORT", "KPI_OKR", "MEETING_MINUTES",
  "FINANCIAL_REPORT", "CONTRACT", "EMPLOYEE_LIST",
];
const STATUS_OPTIONS: FilterStatus[] = [
  "ALL", "UPLOADED", "NEEDS_REVIEW", "IN_REVIEW", "COMMITTED",
  "APPROVED", "REJECTED", "FAILED",
];

/* -------------------------------------------------------------------------- */
/* DocumentsView                                                               */
/* -------------------------------------------------------------------------- */
export function DocumentsView() {
  const t = useTranslations("documents");
  const { role, session } = useAuth();

  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("ALL");
  const [filterPillar, setFilterPillar] = useState<FilterPillar>("ALL");
  const [filterDocType, setFilterDocType] = useState<FilterDocType>("ALL");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["documents", filterStatus, filterPillar, filterDocType, search],
    queryFn: () =>
      getDocumentsApi(
        {
          status: filterStatus !== "ALL" ? filterStatus : undefined,
          pillar: filterPillar !== "ALL" ? filterPillar : undefined,
          docType: filterDocType !== "ALL" ? filterDocType : undefined,
          search: search || undefined,
        },
        session?.accessToken,
      ),
    retry: 1,
    staleTime: 30_000,
    placeholderData: {
      data: DEMO_DOCUMENTS,
      meta: { total: DEMO_DOCUMENTS.length, page: 1, page_size: 50, total_pages: 1 },
    },
  });

  // Client-side filter on demo data (no-op when real API is available)
  const documents = useMemo<DocumentOut[]>(() => {
    if (!data?.data) return [];
    return data.data.filter((doc) => {
      if (search && !doc.original_filename.toLowerCase().includes(search.toLowerCase())) return false;
      if (filterStatus !== "ALL" && doc.status !== filterStatus) return false;
      if (filterPillar !== "ALL" && !doc.pillars.includes(filterPillar as Pillar)) return false;
      if (filterDocType !== "ALL" && doc.doc_type !== filterDocType) return false;
      return true;
    });
  }, [data, search, filterStatus, filterPillar, filterDocType]);

  const selectClass =
    "h-9 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50";

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6" data-testid="documents-view">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">{t("title")}</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Link
          href="/upload"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          {t("uploadButton")}
        </Link>
      </div>

      {/* ── Filter bar ─────────────────────────────────────────── */}
      <div
        className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card p-3"
        role="search"
        aria-label="Document filters"
      >
        <div className="relative flex-1 min-w-[180px]">
          <Search
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("search")}
            className="h-9 w-full rounded-md border border-border bg-background py-1.5 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={t("search")}
          />
        </div>

        <div className="flex items-center gap-1 text-muted-foreground">
          <Filter className="h-3.5 w-3.5" aria-hidden="true" />
        </div>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
          className={selectClass}
          aria-label={t("filters.statusAll")}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? t("filters.statusAll") : s}
            </option>
          ))}
        </select>

        <select
          value={filterPillar}
          onChange={(e) => setFilterPillar(e.target.value as FilterPillar)}
          className={selectClass}
          aria-label={t("filters.pillarAll")}
        >
          {PILLAR_OPTIONS.map((p) => (
            <option key={p} value={p}>
              {p === "ALL" ? t("filters.pillarAll") : p}
            </option>
          ))}
        </select>

        <select
          value={filterDocType}
          onChange={(e) => setFilterDocType(e.target.value as FilterDocType)}
          className={selectClass}
          aria-label={t("filters.docTypeAll")}
        >
          {DOC_TYPE_OPTIONS.map((d) => (
            <option key={d} value={d}>
              {d === "ALL" ? t("filters.docTypeAll") : d}
            </option>
          ))}
        </select>
      </div>

      {/* ── Stats row ──────────────────────────────────────────── */}
      {data && (
        <p className="text-xs text-muted-foreground">
          {documents.length} / {data.meta.total}
        </p>
      )}

      {/* ── Content ────────────────────────────────────────────── */}
      {isLoading ? (
        <LoadingState rows={8} />
      ) : isError ? (
        <ErrorState onRetry={() => refetch()} />
      ) : documents.length === 0 ? (
        <EmptyState
          title={t("empty.title")}
          description={t("empty.description")}
          action={
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              {t("empty.action")}
            </Link>
          }
        />
      ) : (
        <DocumentsTable
          documents={documents}
          role={role as RoleCode}
          onUndo={(id) => console.log("undo", id)}
        />
      )}
    </div>
  );
}
