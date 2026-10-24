"use client";
/** TanStack Query hooks for SCR-64/65 + KillSwitchBanner + ActionCard (10 §7.2.5) — one query per widget. */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { Agent, AiAction, CostSummary, KillSwitch, ModelCallLog, Policy, PolicyDefault, Tool, ToolCallLog } from "./types";

type Q = Record<string, string | number | boolean | null | undefined>;
export const KILL_POLL_MS = 60_000;

export const useKillSwitch = (poll = false) =>
  useQuery({ queryKey: qk.aiKillSwitch(), queryFn: () => api.get<KillSwitch>("/ai/kill-switch"), refetchInterval: poll ? KILL_POLL_MS : false, refetchOnWindowFocus: poll, staleTime: poll ? 0 : 30_000 });
export const useTools = () => useQuery({ queryKey: qk.aiTools(), queryFn: () => api.get<Tool[]>("/ai/tools") });
export const useAgents = () => useQuery({ queryKey: qk.aiAgents(), queryFn: () => api.get<Agent[]>("/ai/agents") });
export const useUsage = (params: Q) => useQuery({ queryKey: qk.aiUsage(params), queryFn: () => api.get<CostSummary>("/ai/usage", params) });
export const useActions = (params: Q) => useQuery({ queryKey: qk.aiActions(params), queryFn: () => api.get<AiAction[]>("/ai/actions", params) });

export function usePolicies() {
  return useQuery({
    queryKey: qk.aiPolicies(),
    queryFn: async () => {
      const r = await apiRequest<Policy[]>("/ai/autonomy-policies", { query: { limit: 100 } });
      return { rows: r.data, defaults: ((r.meta as { defaults?: PolicyDefault[] } | undefined)?.defaults ?? []) };
    },
  });
}

export function useLogs<T extends ToolCallLog | ModelCallLog>(kind: "tool-calls" | "model-calls", params: Q) {
  return useQuery({ queryKey: qk.aiLogs(kind, params), queryFn: () => apiRequest<T[]>(`/ai/${kind}`, { query: params }), placeholderData: (p) => p });
}

/** After any AI admin mutation: refresh the whole `["ai-admin"]` subtree (banner included). */
export function useInvalidateAi() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: ["ai-admin"] });
}

export const putKillSwitch = (body: { enabled: boolean; mode: "WRITE_OFF" | "L0"; agents: string[]; reason: string }) =>
  apiRequest<KillSwitch>("/ai/kill-switch", { method: "PUT", body, idempotent: true }).then((r) => r.data);
export const patchAgent = (code: string, body: Record<string, unknown>) => api.patch<Agent>(`/ai/agents/${code}`, body);
export const createPolicy = (body: Record<string, unknown>) => api.post<Policy>("/ai/autonomy-policies", body);
export const patchPolicy = (id: string, body: Record<string, unknown>) => api.patch<Policy>(`/ai/autonomy-policies/${id}`, body);
export const deletePolicy = (id: string, reason: string) => apiRequest<null>(`/ai/autonomy-policies/${id}`, { method: "DELETE", query: { reason } });
export const confirmAction = (id: string, edited_input?: Record<string, unknown>) => api.post<AiAction>(`/ai/actions/${id}/confirm`, edited_input ? { edited_input } : {});
export const rejectAction = (id: string, reason: string) => api.post<AiAction>(`/ai/actions/${id}/reject`, { reason });
export const undoAction = (id: string) => api.post<AiAction>(`/ai/actions/${id}/undo`, {});
