"use client";
/**
 * Knowledge data hooks (M3.3) — Decision Log (EP-43 `/execution/decisions`) + Reports catalog
 * (`/reporting/reports`). One query per widget (FR-DSH-07). `downloadReport` streams an export file
 * (CSV/XLSX) straight to a browser download — not through the JSON api-client.
 */
import { useQuery } from "@tanstack/react-query";
import type { Api } from "@aureon/shared-types";
import { api, apiRequest, buildUrl, toApiError } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";

export interface DecisionsParams {
  status?: string;
  reviewDue?: boolean;
  initiativeId?: string;
}

/** Map UI params to the EP-43 query (`review_due=true`, `status`, `initiative_id`). */
function decisionsQuery(p: DecisionsParams): Record<string, string | undefined> {
  return {
    status: p.status || undefined,
    review_due: p.reviewDue ? "true" : undefined,
    initiative_id: p.initiativeId || undefined,
  };
}

export function useDecisions(params: DecisionsParams = {}) {
  const query = decisionsQuery(params);
  return useQuery({
    queryKey: qk.decisions(query),
    queryFn: ({ signal }) => apiRequest<Api.DecisionOut[]>("/execution/decisions", { query, signal }),
    staleTime: 30_000,
  });
}

export function useReports() {
  return useQuery({
    queryKey: qk.reports(),
    queryFn: ({ signal }) => api.get<Api.ReportCatalogOut[]>("/reporting/reports", undefined, signal),
    staleTime: 5 * 60_000,
  });
}

/**
 * EP-24 `GET /idp/documents/search` (M3.4) — Knowledge/RAG over document pages. Disabled until the
 * query is non-empty (TanStack `enabled`), so no request fires on an empty search box.
 */
export function useDocumentSearch(q: string) {
  const query = { q: q.trim() };
  return useQuery({
    queryKey: qk.documentSearch(query),
    queryFn: ({ signal }) => apiRequest<Api.DocumentSearchHit[]>("/idp/documents/search", { query, signal }),
    enabled: q.trim().length > 0,
    staleTime: 30_000,
  });
}

/**
 * Stream `GET /reporting/reports/{code}/export?format=…` to a file download. Same-origin BFF
 * (credentials forward the httpOnly session), blob → temporary `<a download>`, filename taken from
 * Content-Disposition. Throws an ApiError on failure so the caller can toast it.
 */
export async function downloadReport(code: string, format: "csv" | "xlsx"): Promise<void> {
  const res = await fetch(buildUrl(`/reporting/reports/${code}/export`, { format }), {
    credentials: "same-origin",
  });
  if (!res.ok) throw await toApiError(res);
  const name =
    /filename="?([^";]+)"?/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? `${code}.${format}`;
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}
