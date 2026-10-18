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

/**
 * EP-29 POST /api/v1/documents/{id}/review/open
 */
export async function openReviewApi(
  documentId: string,
  token?: string,
): Promise<import("@aureon/shared-types").ReviewOpenOut> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const envelope = await apiFetch<import("@aureon/shared-types").ReviewOpenOut>(
    `documents/${documentId}/review/open`,
    {
      method: "POST",
      headers,
    },
  );

  return envelope.data;
}

/**
 * EP-35 POST /api/v1/documents/{id}/review/release
 */
export async function releaseReviewApi(
  documentId: string,
  token?: string,
): Promise<import("@aureon/shared-types").DocumentOut> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const envelope = await apiFetch<import("@aureon/shared-types").DocumentOut>(
    `documents/${documentId}/review/release`,
    {
      method: "POST",
      headers,
    },
  );

  return envelope.data;
}

/**
 * EP-30 PATCH /api/v1/documents/{id}/fields
 */
export async function patchFieldsApi(
  documentId: string,
  payload: import("@aureon/shared-types").UpdateDocumentFieldsRequest,
  idempotencyKey?: string,
  token?: string,
): Promise<import("@aureon/shared-types").ExtractedFieldOut[]> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }

  const envelope = await apiFetch<{ fields: import("@aureon/shared-types").ExtractedFieldOut[] }>(
    `documents/${documentId}/fields`,
    {
      method: "PATCH",
      headers,
      json: payload,
    },
  );

  return envelope.data.fields;
}

/**
 * EP-31 POST /api/v1/documents/{id}/review/approve
 */
export async function approveReviewApi(
  documentId: string,
  payload: import("@aureon/shared-types").ReviewApproveRequest,
  idempotencyKey?: string,
  token?: string,
): Promise<import("@aureon/shared-types").ReviewApproveOut> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }

  const envelope = await apiFetch<import("@aureon/shared-types").ReviewApproveOut>(
    `documents/${documentId}/review/approve`,
    {
      method: "POST",
      headers,
      json: payload,
    },
  );

  return envelope.data;
}

/**
 * EP-32 POST /api/v1/documents/{id}/review/reject
 */
export async function rejectReviewApi(
  documentId: string,
  payload: import("@aureon/shared-types").ReviewRejectRequest,
  idempotencyKey?: string,
  token?: string,
): Promise<import("@aureon/shared-types").DocumentOut> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }

  const envelope = await apiFetch<import("@aureon/shared-types").DocumentOut>(
    `documents/${documentId}/review/reject`,
    {
      method: "POST",
      headers,
      json: payload,
    },
  );

  return envelope.data;
}

