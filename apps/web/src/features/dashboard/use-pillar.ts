"use client";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { worstStatus, type PillarDef } from "./pillars";
import type { CardStatus, DomainDashboard, MetricValue } from "./types";

export interface PillarView {
  status: CardStatus;
  loading: boolean;
  metrics: MetricValue[];
  openAlerts: number;
  periodKey: string | null;
  series: number[];
  refetch: () => void;
}

/** One query per source endpoint, refetch every 60 s; a failing source → card `unavailable` (FR-DSH-07). */
export function usePillar(def: PillarDef, period: string, permissions: readonly string[]): PillarView {
  const sources = def.sources.filter((s) => permissions.includes(s.permission));
  const results = useQueries({
    queries: sources.map((s) => ({
      queryKey: qk.pillar(s.domain, period),
      queryFn: ({ signal }: { signal: AbortSignal }) => api.get<DomainDashboard>(`/${s.domain}/dashboard`, { period }, signal),
      refetchInterval: 60_000,
      staleTime: 60_000,
    })),
  });
  const loading = results.some((r) => r.isPending);
  const failed = results.length === 0 || results.some((r) => r.isError);
  const data = results.map((r) => r.data).filter((d): d is DomainDashboard => !!d);
  const metrics = data.flatMap((d) => d.metrics);
  const primary = sources[0];
  const trend = primary && data[0] ? (data[0] as unknown as Record<string, unknown>)[primary.trend] : undefined;
  const series = primary && Array.isArray(trend)
    ? (trend as Array<Record<string, unknown>>).map((p) => p[primary.series]).filter((v): v is number => typeof v === "number")
    : [];
  return {
    status: loading ? "no_data" : failed ? "unavailable" : worstStatus(data.map((d) => d.status)),
    loading,
    metrics,
    openAlerts: data.reduce((n, d) => n + (d.open_alerts ?? 0), 0),
    periodKey: data[0]?.period.key ?? null,
    series,
    refetch: () => results.forEach((r) => void r.refetch()),
  };
}
