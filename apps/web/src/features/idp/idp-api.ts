import { apiFetch, getApiBaseUrl, parseEnvelope } from "@/lib/api-client";
import type { ReviewQueueResponse } from "@aureon/shared-types";
import type { QueueQueryParams } from "./types";

/**
 * EP-28 GET /api/v1/review-queue (10 EP-28).
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
  const path = qs ? `review-queue?${qs}` : "review-queue";

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
 * EP-33 POST /api/v1/documents/{id}/rollback  (Undo commit, 10 §EP-33).
 * Request `{ reason }`; `Idempotency-Key` required. Returns DocumentOut (ROLLED_BACK).
 */
export async function rollbackDocumentApi(
  documentId: string,
  reason: string,
  idempotencyKey: string,
  token?: string,
): Promise<import("@aureon/shared-types").DocumentOut> {
  const headers: Record<string, string> = { "Idempotency-Key": idempotencyKey };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const envelope = await apiFetch<import("@aureon/shared-types").DocumentOut>(
    `documents/${documentId}/rollback`,
    { method: "POST", headers, json: { reason } },
  );
  return envelope.data;
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

/**
 * EP-24 GET /api/v1/documents
 */
export async function getDocumentsApi(
  params: {
    page?: number;
    pageSize?: number;
    status?: string;
    pillar?: string;
    docType?: string;
    search?: string;
  } = {},
  token?: string,
): Promise<{
  data: import("@aureon/shared-types").DocumentOut[];
  meta: { total: number; page: number; page_size: number; total_pages: number };
}> {
  const sp = new URLSearchParams();
  if (params.page !== undefined) sp.set("page", params.page.toString());
  if (params.pageSize !== undefined) sp.set("page_size", params.pageSize.toString());
  if (params.status && params.status !== "ALL") sp.set("status", params.status);
  if (params.pillar && params.pillar !== "ALL") sp.set("pillar", params.pillar);
  if (params.docType && params.docType !== "ALL") sp.set("doc_type", params.docType);
  if (params.search?.trim()) sp.set("search", params.search.trim());

  const qs = sp.toString();
  const path = qs ? `documents?${qs}` : "documents";
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const envelope = await apiFetch<
    import("@aureon/shared-types").DocumentOut[],
    { total: number; page: number; page_size: number; total_pages: number }
  >(path, { method: "GET", headers });

  return { data: envelope.data, meta: envelope.meta! };
}

/**
 * EP-25 GET /api/v1/documents/{id} — document detail + jobs + status timeline
 * + reviews + affected (10 §EP-25). Returns 403 FORBIDDEN_SCOPE if out of scope.
 */
export async function getDocumentApi(
  documentId: string,
  token?: string,
): Promise<import("@aureon/shared-types").DocumentDetailOut> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const envelope = await apiFetch<import("@aureon/shared-types").DocumentDetailOut>(
    `documents/${documentId}`,
    { method: "GET", headers },
  );
  return envelope.data;
}

/**
 * EP-20 POST /api/v1/documents  (C3 file upload)
 */
export async function uploadFileApi(
  file: File,
  opts: {
    docTypeHint?: string;
    batchId?: string;
    idempotencyKey: string;
    /** Input channel (10 §EP-20). C3 = file upload (default), C4 = mobile camera photo. */
    channel?: "C3" | "C4";
  },
  token?: string,
): Promise<import("@aureon/shared-types").DocumentOut> {
  const form = new FormData();
  form.append("file", file);
  form.append("channel", opts.channel ?? "C3");
  if (opts.docTypeHint) form.append("doc_type_hint", opts.docTypeHint);
  if (opts.batchId) form.append("batch_id", opts.batchId);

  const headers: Record<string, string> = { "Idempotency-Key": opts.idempotencyKey };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  // Use native fetch: apiFetch omits FormData body (EP-20 multipart/form-data).
  const url = `${getApiBaseUrl()}/documents`;
  const response = await fetch(url, { method: "POST", headers, body: form, cache: "no-store" });
  const body = await response.json().catch(() => null);
  const envelope = parseEnvelope<import("@aureon/shared-types").DocumentOut>(response.status, body);
  return envelope.data;
}

/**
 * EP-21 POST /api/v1/documents/manual  (C1 manual entry)
 * Spec 10 §EP-21: request body is `{ doc_type, fields, batch_id? }`; `Idempotency-Key` required.
 */
export async function uploadManualApi(
  payload: { doc_type: string; fields: Record<string, unknown>; batchId?: string },
  idempotencyKey: string,
  token?: string,
): Promise<import("@aureon/shared-types").DocumentOut> {
  const headers: Record<string, string> = { "Idempotency-Key": idempotencyKey };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const body: { doc_type: string; fields: Record<string, unknown>; batch_id?: string } = {
    doc_type: payload.doc_type,
    fields: payload.fields,
  };
  if (payload.batchId) body.batch_id = payload.batchId;

  const envelope = await apiFetch<import("@aureon/shared-types").DocumentOut>(
    "documents/manual",
    { method: "POST", headers, json: body },
  );
  return envelope.data;
}

/**
 * EP-22 POST /api/v1/documents/natural-language  (C2)
 * Spec 10 §EP-22: request body is `{ text, batch_id? }`; `Idempotency-Key` required.
 */
export async function uploadNlApi(
  payload: { text: string; batchId?: string },
  idempotencyKey: string,
  token?: string,
): Promise<import("@aureon/shared-types").DocumentOut> {
  const headers: Record<string, string> = { "Idempotency-Key": idempotencyKey };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const body: { text: string; batch_id?: string } = { text: payload.text };
  if (payload.batchId) body.batch_id = payload.batchId;

  const envelope = await apiFetch<import("@aureon/shared-types").DocumentOut>(
    "documents/natural-language",
    { method: "POST", headers, json: body },
  );
  return envelope.data;
}

/**
 * EP-50 GET /api/v1/extraction-schemas
 */
export async function getSchemasApi(
  docType?: string,
  token?: string,
): Promise<
  {
    doc_type: string;
    field_set_version: string;
    fields: {
      field_key: string;
      table_key: string | null;
      value_type: string;
      required: boolean;
      sensitivity: string;
      validation_rules: string[];
    }[];
  }[]
> {
  const sp = new URLSearchParams();
  if (docType) sp.set("doc_type", docType);
  const qs = sp.toString();
  const path = qs ? `extraction-schemas?${qs}` : "extraction-schemas";
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const envelope = await apiFetch<
    {
      doc_type: string;
      field_set_version: string;
      fields: {
        field_key: string;
        table_key: string | null;
        value_type: string;
        required: boolean;
        sensitivity: string;
        validation_rules: string[];
      }[];
    }[]
  >(path, { method: "GET", headers });
  return envelope.data;
}
