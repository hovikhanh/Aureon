import { apiFetch } from "@/lib/api-client";
import type { ReviewQueueResponse } from "@aureon/shared-types";
import type { QueueQueryParams } from "./types";

/**
 * EP-28 GET /api/v1/review/queue (10 EP-28).
 */
export async function getReviewQueueApi(
  params: QueueQueryParams = {},
  token?: string,
): Promise<ReviewQueueResponse> {
  const searchParams = new URLSearchParams();

  if (params.page !== undefined) {
    searchParams.set("page", params.page.toString());
  }
  if (params.pageSize !== undefined) {
    searchParams.set("page_size", params.pageSize.toString());
  }
  if (params.status && params.status !== "ALL") {
    searchParams.set("status", params.status);
  }
  if (params.docType && params.docType !== "ALL") {
    searchParams.set("doc_type", params.docType);
  }
  if (params.pillar && params.pillar !== "ALL") {
    searchParams.set("pillar", params.pillar);
  }
  if (params.batchId && params.batchId.trim() !== "") {
    searchParams.set("batch_id", params.batchId.trim());
  }

  const qs = searchParams.toString();
  const path = qs ? `review/queue?${qs}` : "review/queue";

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const envelope = await apiFetch<ReviewQueueResponse["data"], ReviewQueueResponse["meta"]>(
    path,
    {
      method: "GET",
      headers,
    },
  );

  return {
    data: envelope.data,
    meta: envelope.meta as ReviewQueueResponse["meta"],
  };
}

/**
 * EP-34 POST /api/v1/documents/{id}/retry
 */
export async function retryDocumentApi(
  documentId: string,
  mode: "RETRY" | "REOPEN" = "RETRY",
  token?: string,
): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  await apiFetch(`documents/${documentId}/retry`, {
    method: "POST",
    headers,
    json: { mode },
  });
}
