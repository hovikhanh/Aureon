"use client";
/**
 * AI Evaluation data hooks (M3.4, EP-AI-27/28, R-DEC-140) — read-only. Runs are produced by the
 * `run_eval` CLI (never over HTTP, to avoid arbitrary LLM calls); this view only lists/reads them.
 */
import { useQuery } from "@tanstack/react-query";
import type { Api } from "@aureon/shared-types";
import { apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";

export interface EvaluationsParams {
  suite?: string;
  model?: string;
  provider?: string;
}

export function useEvaluations(params: EvaluationsParams = {}) {
  const query = {
    suite: params.suite || undefined,
    model: params.model || undefined,
    provider: params.provider || undefined,
    limit: "50",
  };
  return useQuery({
    queryKey: qk.aiEvaluations(query),
    queryFn: ({ signal }) => apiRequest<Api.AIEvaluationOut[]>("/ai/evaluations", { query, signal }),
    staleTime: 30_000,
  });
}

export function useEvaluation(id: string | null) {
  return useQuery({
    queryKey: qk.aiEvaluation(id ?? ""),
    queryFn: ({ signal }) => apiRequest<Api.AIEvaluationOut>(`/ai/evaluations/${id}`, { signal }),
    enabled: !!id,
    staleTime: 30_000,
  });
}
