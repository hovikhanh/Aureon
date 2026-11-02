"use client";
/**
 * MVP acceptance snapshot hook (M3.5, EP-RPT-08, R-DEC-145) — read-only G1–G4 gates. CEO/DIR with
 * `dashboard:read`; the `/admin` prefix guard is in middleware.
 */
import { useQuery } from "@tanstack/react-query";
import type { Api } from "@aureon/shared-types";
import { apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";

export function useAcceptance(weeks = 4) {
  const query = { weeks: String(weeks) };
  return useQuery({
    queryKey: qk.acceptance(query),
    queryFn: ({ signal }) =>
      apiRequest<Api.AcceptanceSnapshotOut>("/reporting/acceptance", { query, signal }),
    staleTime: 60_000,
  });
}
