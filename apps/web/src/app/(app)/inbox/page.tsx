"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/auth-context";
import {
  InboxView,
  getReviewQueueApi,
  retryDocumentApi,
  DEMO_REVIEW_QUEUE_RESPONSE,
} from "@/features/idp";

// SCR-05 Inbox (ROLE-05 home route; 06 §2.3, §4.2). Built out in T-218.
export default function InboxPage() {
  const { role, session } = useAuth();
  const queryClient = useQueryClient();

  const { data, isLoading, isError, refetch, isStale } = useQuery({
    queryKey: ["review-queue", role],
    queryFn: async () => {
      try {
        const res = await getReviewQueueApi({}, session?.accessToken);
        return res;
      } catch {
        // Fallback to demo fixture if offline/demo
        return DEMO_REVIEW_QUEUE_RESPONSE;
      }
    },
    enabled: role !== "ROLE-03",
  });

  const retryMutation = useMutation({
    mutationFn: (documentId: string) =>
      retryDocumentApi(documentId, "RETRY", session?.accessToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
    },
  });

  const items = data?.data ?? DEMO_REVIEW_QUEUE_RESPONSE.data;
  const counts = data?.meta?.counts ?? DEMO_REVIEW_QUEUE_RESPONSE.meta.counts;

  return (
    <InboxView
      items={items}
      counts={counts}
      role={role}
      isLoading={isLoading}
      isError={isError}
      isStale={isStale}
      onRetry={() => refetch()}
      onItemRetry={(docId) => retryMutation.mutate(docId)}
    />
  );
}

