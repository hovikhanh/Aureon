"use client";
/**
 * CEO Daily Briefing data hooks (M3.3, 03 §3.1) — one query per widget (FR-DSH-07).
 * `useBriefingToday` fetches/generates today's briefing (EP-AI, `/ai/briefings/today`; CEO/DIR
 * only, EMP → 403). `useOpenBriefing` flips it to `opened` once for the G1 "read today" metric.
 */
import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Api } from "@aureon/shared-types";
import { api } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { isOpened } from "./briefing";

/** Today's briefing (generate-if-missing on the backend). `retry: false` so a 403 fails fast. */
export function useBriefingToday() {
  return useQuery({
    queryKey: qk.briefingToday(),
    queryFn: ({ signal }) => api.get<Api.BriefingOut>("/ai/briefings/today", undefined, signal),
    retry: false,
    staleTime: 60_000,
  });
}

/** POST `/ai/briefings/{id}/open` (the api.post helper attaches an Idempotency-Key). */
export function openBriefing(id: string) {
  return api.post<Api.BriefingOut>(`/ai/briefings/${id}/open`, {});
}

/**
 * Fire-and-forget "mark opened" for the banner: runs once per mount when a briefing exists and is
 * not already opened, never blocks render, and refreshes the today key on success (G1 tracking).
 */
export function useOpenBriefing(b: Api.BriefingOut | undefined) {
  const client = useQueryClient();
  const firedFor = React.useRef<string | null>(null);
  const mutation = useMutation({
    mutationFn: (id: string) => openBriefing(id),
    onSuccess: () => void client.invalidateQueries({ queryKey: qk.briefingToday() }),
  });
  // Hold the latest `mutate` in a ref so the effect need not depend on the mutation object (whose
  // identity changes every render) — the effect then re-runs only when the briefing itself changes.
  const mutateRef = React.useRef(mutation.mutate);
  mutateRef.current = mutation.mutate;
  React.useEffect(() => {
    if (!b || isOpened(b)) return;
    if (firedFor.current === b.id) return;
    firedFor.current = b.id;
    mutateRef.current(b.id);
  }, [b]);
}
