"use client";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { MetricDetail } from "./types";

/**
 * EP-12 `GET /dashboard/metrics/{code}` — one query per open panel (FR-DSH-07).
 * Backend localizes `name`/`formula_display` from the request `Accept-Language`.
 * `enabled` is false until a metric row is actually clicked (P01 drill-down).
 */
export function useMetricDetail(code: string | null) {
  const q = useQuery({
    queryKey: qk.metricDetail(code ?? ""),
    enabled: Boolean(code),
    queryFn: ({ signal }) => api.get<MetricDetail>(`/dashboard/metrics/${code}`, undefined, signal),
    staleTime: 60_000,
    retry: false,
  });
  return {
    detail: q.data ?? null,
    loading: q.isLoading,
    error: q.isError,
    /** `FORBIDDEN_*` / `NOT_FOUND` let the page say *why* instead of a generic retry. */
    errorCode: q.error instanceof ApiError ? q.error.code : q.isError ? "NETWORK_ERROR" : null,
    refetch: () => void q.refetch(),
  };
}
