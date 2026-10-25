"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, apiRequest, buildUrl } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { ReviewDetail } from "./types";

/**
 * Review detail (EP-DC-05). Optimistic lock = `document.version` (R-DEC-60bis), echoed in the
 * approve / commit body; the earlier ETag / If-Match fallback is gone.
 */
export function useReview(documentId: string) {
  return useQuery({
    queryKey: qk.reviewDetail(documentId),
    queryFn: ({ signal }) => api.get<ReviewDetail>(`/idp/documents/${documentId}/review`, undefined, signal),
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  });
}

/** EP-29 soft lock on mount; EP-35 release when leaving without a decision. */
export function useReviewLock(documentId: string, enabled: boolean) {
  const [lockError, setLockError] = React.useState<string | null>(null);
  const decided = React.useRef(false);
  React.useEffect(() => {
    if (!enabled) return;
    let alive = true;
    apiRequest(`/idp/documents/${documentId}/review/open`, { method: "POST", body: {}, idempotent: true }).catch((e: { code?: string }) => {
      if (alive) setLockError(e.code ?? "INTERNAL_ERROR");
    });
    return () => {
      alive = false;
      if (!decided.current) {
        void fetch(buildUrl(`/idp/documents/${documentId}/review/release`), { method: "POST", keepalive: true }).catch(() => undefined);
      }
    };
  }, [documentId, enabled]);
  return { lockError, markDecided: () => { decided.current = true; } };
}
