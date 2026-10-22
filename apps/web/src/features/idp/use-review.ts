"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest, buildUrl, toApiError } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { ReviewDetail } from "./types";

/**
 * Review detail + optimistic-lock token. EP review detail does not expose `version` today
 * (DEC-237): if the backend ever sends an `ETag`, it is captured here and echoed as
 * `If-Match` on approve/patch; otherwise concurrency relies on the EP-29 soft lock + 409.
 */
export function useReview(documentId: string) {
  const etag = React.useRef<string | null>(null);
  const query = useQuery({
    queryKey: qk.reviewDetail(documentId),
    queryFn: async ({ signal }) => {
      const res = await fetch(buildUrl(`/idp/documents/${documentId}/review`), { signal, cache: "no-store" });
      if (!res.ok) throw await toApiError(res);
      etag.current = res.headers.get("etag");
      return ((await res.json()) as { data: ReviewDetail }).data;
    },
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  });
  const ifMatch = (): Record<string, string> => (etag.current ? { "if-match": etag.current } : {});
  return { ...query, ifMatch };
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
