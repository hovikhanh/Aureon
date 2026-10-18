"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import type { DocType } from "@aureon/shared-types";
import { LoadingState } from "@/components/states";
import { ErrorState } from "@/components/states/ErrorState";
import { ForbiddenState } from "@/components/states/ForbiddenState";
import { useAuth } from "@/features/auth/auth-context";
import {
  approveReviewApi,
  openReviewApi,
  patchFieldsApi,
  rejectReviewApi,
  releaseReviewApi,
} from "@/features/idp/idp-api";
import { ReviewView } from "@/features/idp/review/ReviewView";

/**
 * SCR-06 Review Detail (06 §4.3, T-219).
 * Route: /review/[documentId]
 * Accessible by ROLE-02 (FIN), ROLE-04 (HR), ROLE-05 (all).
 * ROLE-01 may navigate here but only in view-only mode (no Approve/Reject buttons).
 * ROLE-03 sees ForbiddenState.
 */
export default function ReviewDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { role, session } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  // All hooks must run unconditionally before any early returns
  const {
    data: reviewOpenData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["review-open", documentId],
    queryFn: () => openReviewApi(documentId, session?.accessToken),
    retry: 1,
    staleTime: 0,
    enabled: role !== "ROLE-03",
  });

  const approveM = useMutation({
    mutationFn: ({
      reviewId,
      acceptedConflicts,
    }: {
      reviewId: string;
      acceptedConflicts: { rule: string; note: string }[];
    }) =>
      approveReviewApi(
        documentId,
        { review_id: reviewId, accepted_conflicts: acceptedConflicts },
        `approve-${documentId}-${Date.now()}`,
        session?.accessToken,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      router.push("/inbox");
    },
  });

  const rejectM = useMutation({
    mutationFn: ({
      reviewId,
      reasonCode,
      note,
    }: {
      reviewId: string;
      reasonCode: string;
      note?: string;
    }) =>
      rejectReviewApi(
        documentId,
        { review_id: reviewId, reject_reason_code: reasonCode, reject_note: note },
        `reject-${documentId}-${Date.now()}`,
        session?.accessToken,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      router.push("/inbox");
    },
  });

  const releaseM = useMutation({
    mutationFn: () => releaseReviewApi(documentId, session?.accessToken),
  });

  const changeDocTypeM = useMutation({
    mutationFn: (docType: DocType) =>
      patchFieldsApi(
        documentId,
        { doc_type: docType },
        `doctype-${documentId}-${Date.now()}`,
        session?.accessToken,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-open", documentId] });
    },
  });

  // ROLE-03 has no access to review queue
  if (role === "ROLE-03") {
    return (
      <div className="p-6">
        <ForbiddenState />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <LoadingState rows={6} />
      </div>
    );
  }

  if (isError || !reviewOpenData) {
    return (
      <div className="p-6">
        <ErrorState onRetry={() => refetch()} />
      </div>
    );
  }

  const { document, review_id: reviewId, extraction } = reviewOpenData;

  return (
    <ReviewView
      document={document}
      reviewId={reviewId}
      extraction={extraction}
      role={role}
      onApprove={async (acceptedConflicts) => {
        await approveM.mutateAsync({ reviewId, acceptedConflicts });
      }}
      onReject={async (reasonCode, note) => {
        await rejectM.mutateAsync({ reviewId, reasonCode, note });
      }}
      onRelease={async () => {
        await releaseM.mutateAsync();
      }}
      onChangeDocType={async (docType) => {
        await changeDocTypeM.mutateAsync(docType);
      }}
    />
  );
}
