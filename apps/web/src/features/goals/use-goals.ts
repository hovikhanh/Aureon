"use client";
/** TanStack Query hooks of the goals screens (10 §7.2.3) — one query per widget. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Api } from "@aureon/shared-types";
import { apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";

export type KpiOut = Api.KpiOut;
export type KpiTargetOut = Api.KpiTargetOut;
export type KpiEvaluationOut = Api.KpiEvaluationOut;
export type MeasurementOut = Api.MeasurementOut;
export type ObjectiveOut = Api.ObjectiveOut;
export type KeyResultOut = Api.KeyResultOut;
export type CheckInOut = Api.CheckInOut;
export type CheckInDueOut = Api.CheckInDueOut;
export type StrategyOut = Api.StrategyOut;

const get = <T,>(path: string, query?: Record<string, string | number | boolean | undefined>) =>
  ({ signal }: { signal: AbortSignal }) => apiRequest<T>(path, { query, signal }).then((r) => r.data);

export interface TreeParams { period_key: string; strategy_id?: string; department_id?: string }
export const useGoalTree = (p: TreeParams) => useQuery({ queryKey: qk.goalTree({ ...p }), queryFn: get<Api.GoalTreeOut>("/goals/tree", { ...p }) });
export const useStrategies = () => useQuery({ queryKey: qk.strategies(), queryFn: get<StrategyOut[]>("/goals/strategies", { limit: 100 }) });

export const useKpi = (id: string) => useQuery({ queryKey: qk.kpi(id), queryFn: get<KpiOut>(`/kpis/${id}`), retry: false });
export const useKpiEvaluations = (id: string) => useQuery({ queryKey: qk.kpiPart(id, "evaluations"), queryFn: get<KpiEvaluationOut[]>(`/kpis/${id}/evaluations`) });
export const useKpiTargets = (id: string) => useQuery({ queryKey: qk.kpiPart(id, "targets"), queryFn: get<KpiTargetOut[]>(`/kpis/${id}/targets`, { limit: 100 }) });
export const useKpiMeasurements = (id: string) => useQuery({ queryKey: qk.kpiPart(id, "measurements"), queryFn: get<MeasurementOut[]>(`/kpis/${id}/measurements`, { limit: 100, sort_by: "measured_at", order: "desc" }) });
export const useKpiCheckIns = (id: string) => useQuery({ queryKey: qk.kpiPart(id, "check-ins"), queryFn: get<CheckInOut[]>(`/kpis/${id}/check-ins`, { limit: 50 }) });

export const useObjective = (id: string) => useQuery({ queryKey: qk.objective(id), queryFn: get<ObjectiveOut>(`/objectives/${id}`), retry: false });
export const useObjectiveKrs = (id: string) => useQuery({ queryKey: qk.objectiveKrs(id), queryFn: get<KeyResultOut[]>(`/objectives/${id}/key-results`) });
export const useKrCheckIns = (id: string | null) => useQuery({ queryKey: qk.krCheckIns(id ?? ""), enabled: Boolean(id), queryFn: get<CheckInOut[]>(`/key-results/${id}/check-ins`, { limit: 50 }) });

export const useCheckInsDue = () => useQuery({ queryKey: qk.checkInsDue(), queryFn: get<CheckInDueOut[]>("/goals/check-ins/due") });
export interface FeedParams { from?: string; to?: string; department_id?: string; confidence?: string }
export const useCheckInFeed = (p: FeedParams, enabled = true) =>
  useQuery({ queryKey: qk.checkInFeed({ ...p }), enabled, queryFn: get<CheckInOut[]>("/goals/check-ins", { ...p, limit: 100 }) });

/** Any goals mutation → refetch every goals query + notifications (alert). */
export function useGoalMutation<TVars, TOut = unknown>(fn: (v: TVars) => Promise<TOut>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSettled: () => Promise.all([qc.invalidateQueries({ queryKey: ["goals"] }), qc.invalidateQueries({ queryKey: qk.notifications() })]),
  });
}

const post = <T,>(path: string, body: unknown) => apiRequest<T>(path, { method: "POST", body, idempotent: true }).then((r) => r.data);
export const postCheckIn = (targetType: "key_result" | "kpi", id: string, body: Api.CheckInCreate) =>
  post<CheckInOut>(targetType === "kpi" ? `/kpis/${id}/check-ins` : `/key-results/${id}/check-ins`, body);
export const postMeasurement = (kpiId: string, body: Api.MeasurementCreate) => post<MeasurementOut>(`/kpis/${kpiId}/measurements`, body);
export const postTarget = (kpiId: string, body: Api.KpiTargetCreate) => post<KpiTargetOut>(`/kpis/${kpiId}/targets`, body);

// ---- KPI / OKR editors (EP-KPI-02/04/05, EP-OKR-02/04/05/07/09/10) -------------------------
const patch = <T,>(path: string, body: unknown) => apiRequest<T>(path, { method: "PATCH", body }).then((r) => r.data);
const del = (path: string) => apiRequest<void>(path, { method: "DELETE" }).then(() => undefined);

export const createKpi = (body: Api.KpiCreate) => post<KpiOut>("/kpis", body);
export const updateKpi = (id: string, body: Api.KpiUpdate) => patch<KpiOut>(`/kpis/${id}`, body);
/** Archive = soft delete (`deleted_at`); a KPI with child KPIs / tasks → `409 CONFLICT_STATE`. */
export const archiveKpi = (id: string) => del(`/kpis/${id}`);

export const createObjective = (body: Api.ObjectiveCreate) => post<ObjectiveOut>("/objectives", body);
export const updateObjective = (id: string, body: Api.ObjectiveUpdate) => patch<ObjectiveOut>(`/objectives/${id}`, body);
export const archiveObjective = (id: string) => del(`/objectives/${id}`);

export const createKeyResult = (objectiveId: string, body: Api.KeyResultCreate) => post<KeyResultOut>(`/objectives/${objectiveId}/key-results`, body);
export const updateKeyResult = (id: string, body: Api.KeyResultUpdate) => patch<KeyResultOut>(`/key-results/${id}`, body);
export const archiveKeyResult = (id: string) => del(`/key-results/${id}`);
