"use client";
/** Queries / mutations of the CRM views — existing endpoints only (10 EP-SAL-01..08, EP-FIN). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { apiRequest } from "@/lib/api-client";

export interface DealOut {
  id: string; version: number; name: string; client_id: string; deal_value: number; currency: string; stage: string;
  probability_pct: number; weighted_value: number; expected_close_date: string; closed_at: string | null;
  lost_reason: string | null; owner_id: string; description: string | null; created_at: string; updated_at: string;
}
export interface ClientOut {
  id: string; version: number; name: string; tax_code: string | null; industry: string | null; size: string | null;
  status: string; address: string | null; website: string | null; account_owner_id: string | null; notes: string | null;
  contacts: { name?: string | null; email?: string | null; phone?: string | null }[];
}
export interface ContractOut {
  id: string; contract_number: string; client_id: string; deal_id: string | null; contract_value: number; currency: string;
  signed_at: string; effective_date: string; expiry_date: string | null; status: string;
}
export interface StageCount { stage: string; count: number; value: number; weighted_value: number; avg_days_in_stage: number | null }
export interface PerformanceRow { owner_ref: string; closed_value: number; quota: number | null; attainment_pct: number | null; win_rate_pct: number | null }
export interface StageHistory { from_stage: string | null; to_stage: string; changed_by: string | null; changed_at: string }

const get = <T,>(path: string, query?: Record<string, string | number | undefined>) =>
  ({ signal }: { signal: AbortSignal }) => apiRequest<T>(path, { query, signal }).then((r) => r.data);

export const crmKeys = { all: ["crm"] as const };

export function useDeals(query: Record<string, string | number | undefined>, enabled = true) {
  return useQuery({ queryKey: [...crmKeys.all, "deals", query], enabled, queryFn: get<DealOut[]>("/sales/deals", { limit: 100, ...query }) });
}
export function useDeal(id: string) {
  return useQuery({ queryKey: [...crmKeys.all, "deal", id], queryFn: get<DealOut>(`/sales/deals/${id}`) });
}
export function useStageHistory(id: string) {
  return useQuery({ queryKey: [...crmKeys.all, "history", id], queryFn: get<StageHistory[]>(`/sales/deals/${id}/stage-history`) });
}
export function useClients(enabled = true) {
  return useQuery({ queryKey: [...crmKeys.all, "clients"], enabled, staleTime: 120_000, queryFn: get<ClientOut[]>("/sales/clients", { limit: 100, sort_by: "name", order: "asc" }) });
}
export function useClient(id: string) {
  return useQuery({ queryKey: [...crmKeys.all, "client", id], enabled: Boolean(id), queryFn: get<ClientOut>(`/sales/clients/${id}`) });
}
export function useContracts(query: Record<string, string | number | undefined>) {
  return useQuery({ queryKey: [...crmKeys.all, "contracts", query], queryFn: get<ContractOut[]>("/sales/contracts", { limit: 100, ...query }) });
}
export function usePipeline(period?: string) {
  return useQuery({ queryKey: [...crmKeys.all, "pipeline", period ?? ""], queryFn: get<{ stages: StageCount[]; coverage_ratio: number | null }>("/sales/pipeline", { period }) });
}
export function usePerformance(period: string, enabled: boolean) {
  return useQuery({ queryKey: [...crmKeys.all, "performance", period], enabled, queryFn: get<PerformanceRow[]>("/sales/performance", { period, group_by: "owner" }) });
}

/** EP-SAL-03 stage change (forward only, Closed Lost needs a reason — the API enforces both). */
export function useMoveStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; to_stage: string; lost_reason?: string }) =>
      apiRequest<DealOut>(`/sales/deals/${v.id}/stage`, { method: "POST", body: { to_stage: v.to_stage, lost_reason: v.lost_reason || null }, idempotent: true }),
    onSettled: () => qc.invalidateQueries({ queryKey: crmKeys.all }),
  });
}

/** Owner label for a user id: "Tôi", the name when `/platform/users` is readable, else a plain label (never the id). */
export function useOwnerLabel(userId: string, canReadUsers: boolean): (ownerId: string) => string {
  const t = useTranslations();
  const users = useQuery({
    queryKey: [...crmKeys.all, "users"],
    enabled: canReadUsers,
    staleTime: 300_000,
    queryFn: ({ signal }) => apiRequest<{ id: string; full_name: string }[]>("/platform/users", { query: { limit: 100 }, signal }).then((r) => r.data),
  });
  return (ownerId) => (ownerId === userId ? t("crm.me") : users.data?.find((u) => u.id === ownerId)?.full_name ?? t("common.otherPerson"));
}
